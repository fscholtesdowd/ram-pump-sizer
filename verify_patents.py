#!/usr/bin/env python3
"""Verify the patent-sourced pages on the Ram Pump Sizer site.

Built 2026-08-23.

Every check must be able to return the answer it exists to detect: before trusting a
check, make it fail on purpose.
`--selftest` runs a POSITIVE control first -- the real, unmodified site must PASS,
otherwise the sabotages below prove nothing -- and then breaks the site eight
different ways and demands that each break is caught.

The specific thing this guards, and the reason it exists: a wrong patent number or
a wrong date is the failure mode of patent mining. Google Patents' own transcription
of US281749A prints "Application filed September 11, 1832" for a patent granted in
1883 -- an OCR error in the scanned source. S4 below plants exactly that date on the
page and requires it to be caught, because it is the error most likely to be copied
in good faith by whoever next edits this page.

USAGE
    python verify_patents.py             # check the built site
    python verify_patents.py --selftest  # positive control + 8 sabotages
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data" / "patents.json"
PAGE = ROOT / "how-it-works" / "index.html"
APPJS = ROOT / "app.js"

# A patent id anywhere in the text: US followed by digits and a kind code.
PAT_ID = re.compile(r"\bUS\d{4,8}[AB]\d?\b")
# Anything that looks like an affiliate/referral tag.
AFFIL = re.compile(r"(amzn\.to|tag=[\w-]+-20|/dp/[A-Z0-9]{10}|ref=[\w]+|utm_medium=affiliate)", re.I)
# A bare four-digit year.
YEAR = re.compile(r"\b(1[6-9]\d{2}|20\d{2})\b")


class Result:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.notes: list[str] = []

    def fail(self, msg: str) -> None:
        self.failures.append(msg)

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    @property
    def ok(self) -> bool:
        return not self.failures


def check(data_text: str, page_text: str, appjs_text: str) -> Result:
    """All checks run against TEXT, not files, so the selftest can sabotage in memory."""
    r = Result()
    d = json.loads(data_text)
    known = {p["id"]: p for p in d["patents"]}
    adjacent = {p["id"]: p for p in d.get("adjacent_patents_not_used_on_this_site", [])}

    # C1 -- every patent id printed on the page is one we actually verified.
    printed = set(PAT_ID.findall(page_text))
    if not printed:
        r.fail("C1 no patent id appears on the page at all -- the page's whole premise is missing")
    for pid in sorted(printed):
        if pid not in known:
            where = " (it is in adjacent_patents, which belongs to another site)" if pid in adjacent else ""
            r.fail(f"C1 page cites {pid}, which is NOT in data/patents.json{where}")
    r.note(f"C1 {len(printed)} patent id(s) on page, all present in data: {', '.join(sorted(printed))}")

    # C2 -- every cited patent is EXPIRED. Never tell a reader to build a live patent.
    for pid in sorted(printed & set(known)):
        status = known[pid].get("status", "")
        if "Expired" not in status:
            r.fail(f"C2 {pid} is cited as buildable but its status is {status!r}")
    r.note(f"C2 all {len(printed & set(known))} cited patents carry an Expired status")

    # C3 -- every expiration date printed for a patent matches the data file.
    for pid, p in known.items():
        if pid not in printed:
            continue
        exp = p["anticipated_expiration"]
        if exp not in page_text:
            r.fail(f"C3 {pid} expiration {exp} from data is not printed on the page")
    r.note("C3 every cited patent's expiration date is printed and matches data")

    # C4 -- a date the data file explicitly flags as a transcription error must never
    # reach the page. US281749A's Google Patents scan says "filed September 11, 1832"
    # for a patent granted in 1883.
    #
    # NOTE: the first version of this check derived the bad year by regexing the
    # `filing_note` prose. It swept up 1900 -- the legitimate expiration -- and failed
    # the correct page. The positive control caught that. Forbidden values are now
    # declared in the data, never inferred from a sentence.
    forbidden_total = 0
    for pid, p in known.items():
        for badyear in p.get("forbidden_years", []):
            forbidden_total += 1
            if re.search(rf"\b{re.escape(str(badyear))}\b", page_text):
                r.fail(f"C4 page prints {badyear} for {pid} -- data flags that as a transcription error")
    r.note(f"C4 {forbidden_total} known-bad date(s) declared in data, none present on the page")

    # C5 -- every year printed on the page traces to the data file.
    data_years = set(YEAR.findall(data_text))
    for y in set(YEAR.findall(page_text)):
        if y not in data_years:
            r.fail(f"C5 page prints the year {y}, which appears nowhere in data/patents.json")
    r.note("C5 every year on the page traces back to the data file")

    # C6 -- no affiliate link. links are gated on traffic and require a human-owned account signup.
    hit = AFFIL.search(page_text)
    if hit:
        r.fail(f"C6 affiliate-shaped link on the page: {hit.group(0)!r}")
    r.note("C6 no affiliate-shaped link present")

    # C7 -- the formula printed must be the formula the shipped calculator runs.
    # app.js implements: q_lpm = eNow * Q_lpm * H_m / h_m
    shipped = re.search(r"=\s*eNow\s*\*\s*Q_lpm\s*\*\s*H_m\s*/\s*h_m", appjs_text)
    if not shipped:
        r.fail("C7 could not find the delivered-flow formula in app.js -- calculator changed?")
    stated = json.loads(data_text)["physics"]["delivered_flow_formula"]
    norm = stated.replace(" ", "").lower()
    if norm != "q=eta*q*h/h":
        r.fail(f"C7 data's delivered_flow_formula {stated!r} is not q = eta*Q*H/h")
    if stated not in page_text and stated.replace("*", "*") not in page_text:
        r.fail("C7 the formula in data is not printed on the page")
    r.note("C7 page formula == data formula == the formula app.js actually executes")

    # C8 -- the diagram must be present AND accessible (title + desc, not a bare picture).
    if "<svg" not in page_text:
        r.fail("C8 no diagram on the page")
    else:
        if "<title" not in page_text or "<desc" not in page_text:
            r.fail("C8 diagram has no <title>/<desc> -- unreadable to a screen reader and to Google")
        if 'role="img"' not in page_text:
            r.fail("C8 diagram is missing role=\"img\"")
    r.note("C8 diagram present with title, desc and role")

    return r


def read_all() -> tuple[str, str, str]:
    return (
        DATA.read_text(encoding="utf-8"),
        PAGE.read_text(encoding="utf-8"),
        APPJS.read_text(encoding="utf-8"),
    )


def selftest() -> int:
    data_t, page_t, app_t = read_all()

    print("POSITIVE CONTROL -- the real site must pass, or the sabotages below prove nothing")
    base = check(data_t, page_t, app_t)
    if not base.ok:
        print("  FAIL -- real site does not pass; sabotage results are meaningless")
        for f in base.failures:
            print(f"    {f}")
        return 1
    print(f"  PASS ({len(base.notes)} checks green)\n")

    # Each sabotage: (label, mutated data, mutated page, mutated app.js, which check should catch it)
    sabotages = [
        ("S1 cite a patent that is not in the data file",
         data_t, page_t.replace("US755467A", "US9999999B2", 1), app_t, "C1"),
        ("S2 cite a LIVE patent as buildable",
         data_t.replace('"status": "Expired - Lifetime"', '"status": "Active"', 1), page_t, app_t, "C2"),
        ("S3 change an expiration date without rebuilding the page",
         data_t.replace('"anticipated_expiration": "1921-03-22"',
                        '"anticipated_expiration": "1975-03-22"', 1), page_t, app_t, "C3"),
        ("S4 plant the known OCR-corrupted 1832 filing date on the page",
         data_t, page_t.replace("<h2>The four-stage cycle</h2>",
                                "<p>Application filed September 11, 1832.</p><h2>The four-stage cycle</h2>", 1),
         app_t, "C4/C5"),
        ("S5 invent an unsourced year on the page",
         data_t, page_t.replace("<h2>The parts, by name</h2>",
                                "<p>First commercialised in 1938.</p><h2>The parts, by name</h2>", 1),
         app_t, "C5"),
        ("S6 inject an affiliate link",
         data_t, page_t.replace('href="../"', 'href="https://amzn.to/xyz123?tag=storeid-20"', 1),
         app_t, "C6"),
        ("S7 invert the formula in the calculator so page and code disagree",
         data_t, page_t, app_t.replace("eNow * Q_lpm * H_m / h_m", "eNow * Q_lpm * h_m / H_m", 1), "C7"),
        ("S8 strip the diagram's accessible description",
         data_t, page_t.replace("<desc id=\"ramDiagramDesc\">", "<span hidden>", 1), app_t, "C8"),
    ]

    caught = 0
    for label, dt, pt, at, expect in sabotages:
        res = check(dt, pt, at)
        if res.ok:
            print(f"  MISSED  {label}  (expected {expect} to fire)")
        else:
            caught += 1
            print(f"  caught  {label}  -> {res.failures[0]}")

    print(f"\nSELFTEST {caught}/{len(sabotages)} sabotages caught")
    return 0 if caught == len(sabotages) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    r = check(*read_all())
    for n in r.notes:
        print(f"  ok  {n}")
    if r.ok:
        print("\nALL CHECKS PASSED")
        return 0
    print()
    for f in r.failures:
        print(f"  FAIL  {f}")
    print(f"\n{len(r.failures)} FAILURE(S)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
