#!/usr/bin/env python3
"""Build the patent-sourced content pages for the Ram Pump Sizer site.

Built 2026-08-23, patent-mining pass.

WHY THIS EXISTS
---------------
`index.html` is a bare calculator. The measured demand in this room is mostly NOT
"calculator" -- it is `hydraulic ram pump how it works`, `ram pump plans pdf free
download`, `hydraulic ram pump parts list`, `ram pump waste valve design`. A single
calculator page captures almost none of it.

The page-1 read for those queries (2026-08-23) is Scribd and SlideShare scans of
old extension PDFs, plus Clemson/Auburn/NC State publications. That is gate v2's
"scanned PDFs = real gap, BUILD ONLY IF WE CAN SOURCE REAL DATA" case. The real
data here is three expired hydraulic-ram patents, read directly off Google Patents.

FIX THE FACTORY, NOT THE ARTIFACT
----------------------------------
No patent number, date, status or inventor is typed in this file. Every one is read
from data/patents.json. If a fact is wrong, it is wrong in ONE place and every page
is regenerated. verify_patents.py enforces this by failing if a page prints a
patent id that the data file does not contain.

USAGE
    python build_patents.py            # writes how-it-works/index.html
    python build_patents.py --check    # print what would be written, write nothing
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data" / "patents.json"
OUT_DIR = ROOT / "how-it-works"
OUT = OUT_DIR / "index.html"


def load() -> dict:
    with DATA.open(encoding="utf-8") as fh:
        return json.load(fh)


def esc(s) -> str:
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------------------
# The cutaway diagram.
#
# Drawn from scratch as SVG rather than reproducing a scanned patent figure.
# Two reasons, both real: (1) an original vector drawing is legible at any size
# and in dark mode, which a 1904 raster scan is not; (2) it sidesteps the whole
# question of which scan is whose. The FIGURES in these three patents are public
# domain by publication date and could legally be reproduced -- this is a quality
# choice, not a legal one. Labels follow the component names used in the patents.
# ---------------------------------------------------------------------------
def diagram_svg() -> str:
    return """
<svg viewBox="0 0 720 380" role="img"
     aria-labelledby="ramDiagramTitle ramDiagramDesc" class="ram-diagram">
  <title id="ramDiagramTitle">Cutaway of a hydraulic ram pump</title>
  <desc id="ramDiagramDesc">Water falls from a source through a long drive pipe into the
  pump body. A waste valve lets water escape until it slams shut; the stopped water column
  forces a delivery check valve open, pushing water into an air chamber and up the delivery
  pipe to a tank above the pump.</desc>

  <!-- source -->
  <path d="M20 40 H150 V70 H20 Z" class="water"/>
  <text x="24" y="32" class="lbl">Source (spring or stream)</text>

  <!-- drive pipe -->
  <path d="M150 55 L150 250 L300 250" class="pipe"/>
  <text x="158" y="150" class="lbl">Drive pipe</text>
  <text x="158" y="166" class="sub">the long fall: H</text>

  <!-- fall dimension -->
  <path d="M120 55 L120 250" class="dim"/>
  <path d="M115 60 L120 50 L125 60" class="dimarrow"/>
  <path d="M115 245 L120 255 L125 245" class="dimarrow"/>
  <text x="74" y="158" class="dimlbl">H</text>

  <!-- pump body -->
  <rect x="300" y="228" width="150" height="44" rx="6" class="body"/>
  <text x="312" y="292" class="lbl">Pump body</text>

  <!-- waste valve -->
  <path d="M330 228 L330 200" class="stem"/>
  <circle cx="330" cy="196" r="11" class="valve"/>
  <text x="286" y="180" class="lbl">Waste valve</text>
  <path d="M352 210 q22 -14 44 0" class="spill"/>
  <text x="360" y="232" class="sub">spill</text>

  <!-- delivery check valve -->
  <path d="M420 228 L420 206" class="stem"/>
  <circle cx="420" cy="202" r="9" class="valve valve-check"/>
  <text x="432" y="196" class="lbl">Check valve</text>

  <!-- air chamber -->
  <rect x="470" y="120" width="70" height="120" rx="8" class="chamber"/>
  <rect x="470" y="180" width="70" height="60" rx="0" class="water"/>
  <path d="M450 250 H470" class="pipe"/>
  <path d="M470 240 L470 240" class="pipe"/>
  <text x="474" y="112" class="lbl">Air chamber</text>
  <text x="476" y="156" class="sub">trapped air</text>
  <text x="476" y="212" class="sub">water</text>

  <!-- delivery pipe -->
  <path d="M540 180 L620 180 L620 60 L690 60" class="pipe"/>
  <text x="556" y="172" class="lbl">Delivery pipe</text>

  <!-- tank -->
  <path d="M630 40 H710 V80 H630 Z" class="water"/>
  <text x="618" y="32" class="lbl">Tank (the lift: h)</text>

  <!-- lift dimension -->
  <path d="M670 100 L670 250" class="dim"/>
  <path d="M665 105 L670 95 L675 105" class="dimarrow"/>
  <path d="M665 245 L670 255 L675 245" class="dimarrow"/>
  <text x="682" y="180" class="dimlbl">h</text>
  <path d="M450 250 H670" class="datum"/>
</svg>
""".strip()


STAGES = [
    (
        "1",
        "The water gets moving",
        "Water runs down the drive pipe under nothing but its own fall and escapes "
        "through the open waste valve. Nothing is being pumped yet. All that happens "
        "in this stage is that a long column of water picks up speed.",
    ),
    (
        "2",
        "The waste valve slams",
        "Once the water is moving fast enough, the flow itself drags the waste valve "
        "shut. The valve does not close because of a timer or a spring setting -- it "
        "closes because the water it is passing pulls it closed.",
    ),
    (
        "3",
        "The shock does the lifting",
        "A moving column of water has real momentum, and stopping it suddenly has to "
        "put that energy somewhere. The pressure spikes far above what the fall alone "
        "could ever produce, and that spike is what shoves the check valve open and "
        "pushes water up the delivery pipe. This is the whole trick of the machine.",
    ),
    (
        "4",
        "Recoil, and around again",
        "Pressure drops, the check valve shuts so nothing falls back, the waste valve "
        "drops open, and the cycle restarts -- typically around once a second, all day, "
        "with no power and no attention. The air chamber's trapped air is what turns "
        "those separate shocks into a steady trickle out of the delivery pipe.",
    ),
]


def render(d: dict) -> str:
    pats = d["patents"]
    phys = d["physics"]

    stage_html = "\n".join(
        f"""      <li class="stage">
        <span class="stage-n" aria-hidden="true">{esc(n)}</span>
        <div>
          <h3>{esc(title)}</h3>
          <p>{esc(body)}</p>
        </div>
      </li>"""
        for n, title, body in STAGES
    )

    rows = []
    for p in pats:
        q = (
            f'<p class="pq">&ldquo;{esc(p["quote"])}&rdquo;</p>'
            if p.get("quote")
            else ""
        )
        rows.append(
            f"""      <article class="patent">
        <header>
          <h3><a href="{esc(p['url'])}" rel="noopener">{esc(p['id'])}</a>: {esc(p['title'])}</h3>
          <p class="meta">{esc(p['inventor'])} &middot; {esc(p['date_label'])}</p>
        </header>
        <p>{esc(p['contributes'])}</p>
        {q}
        <p class="status"><strong>{esc(p['status'])}</strong> &middot; term ran out {esc(p['anticipated_expiration'])}</p>
      </article>"""
        )
    patent_html = "\n".join(rows)

    ids = ", ".join(p["id"] for p in pats)
    newest_expiry = max(p["anticipated_expiration"] for p in pats)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>How a Hydraulic Ram Pump Works: The Four-Stage Cycle, From the Original Patents</title>
<meta name="description" content="A hydraulic ram pump lifts water uphill with no electricity, using the shock of stopping moving water. Here is the four-stage cycle, drawn and explained from three expired US patents ({esc(ids)}).">
<link rel="canonical" href="how-it-works/">
<meta name="theme-color" content="#1b4332">
<link rel="stylesheet" href="../styles.css">
<style>
  .prose {{ max-width: 46rem; margin: 0 auto; padding: 0 1rem 4rem; }}
  .prose h2 {{ margin-top: 2.4rem; }}
  .ram-diagram {{ width: 100%; height: auto; margin: 1.4rem 0; }}
  .ram-diagram .water {{ fill: #6aa9d8; opacity: .55; }}
  .ram-diagram .pipe {{ fill: none; stroke: #35506b; stroke-width: 9; stroke-linecap: round;
                        stroke-linejoin: round; }}
  .ram-diagram .body {{ fill: #d8dee6; stroke: #35506b; stroke-width: 3; }}
  .ram-diagram .chamber {{ fill: #eef2f6; stroke: #35506b; stroke-width: 3; }}
  .ram-diagram .valve {{ fill: #c0492f; stroke: #7a2c1b; stroke-width: 2.5; }}
  .ram-diagram .valve-check {{ fill: #2f7d4f; stroke: #1b4332; }}
  .ram-diagram .stem {{ stroke: #7a2c1b; stroke-width: 3; }}
  .ram-diagram .spill {{ fill: none; stroke: #6aa9d8; stroke-width: 3;
                         stroke-dasharray: 4 4; }}
  .ram-diagram .dim {{ stroke: #8a8f98; stroke-width: 1.4; stroke-dasharray: 5 4; }}
  .ram-diagram .dimarrow {{ fill: none; stroke: #8a8f98; stroke-width: 1.6; }}
  .ram-diagram .datum {{ stroke: #8a8f98; stroke-width: 1; stroke-dasharray: 3 5; }}
  .ram-diagram .lbl {{ font: 600 13px system-ui, sans-serif; fill: #22303f; }}
  .ram-diagram .sub {{ font: 400 11px system-ui, sans-serif; fill: #5a6675; }}
  .ram-diagram .dimlbl {{ font: 700 16px system-ui, sans-serif; fill: #5a6675; }}
  .stages {{ list-style: none; padding: 0; }}
  .stage {{ display: flex; gap: 1rem; margin: 1.3rem 0; }}
  .stage-n {{ flex: 0 0 2.1rem; height: 2.1rem; border-radius: 50%; background: #1b4332;
              color: #fff; display: grid; place-items: center; font-weight: 700; }}
  .stage h3 {{ margin: .15rem 0 .3rem; font-size: 1.03rem; }}
  .stage p {{ margin: 0; }}
  .patent {{ border-left: 3px solid #1b4332; padding: .1rem 0 .1rem 1rem; margin: 1.5rem 0; }}
  .patent h3 {{ margin: 0 0 .2rem; font-size: 1.02rem; }}
  .patent .meta {{ margin: 0 0 .55rem; font-size: .88rem; color: #5a6675; }}
  .patent .pq {{ font-style: italic; color: #35506b; border-left: 2px solid #c9d2dc;
                 padding-left: .8rem; margin: .55rem 0; }}
  .patent .status {{ font-size: .86rem; color: #5a6675; margin: .45rem 0 0; }}
  .callout {{ background: #f2f6f3; border: 1px solid #cfe0d5; border-radius: 8px;
              padding: 1rem 1.15rem; margin: 1.6rem 0; }}
  .callout h2 {{ margin-top: 0; font-size: 1.05rem; }}
  .formula {{ background: #22303f; color: #eef2f6; padding: .95rem 1.1rem;
              border-radius: 8px; font-family: ui-monospace, Menlo, Consolas, monospace;
              overflow-x: auto; }}
  .cta {{ display: inline-block; background: #1b4332; color: #fff; text-decoration: none;
          padding: .75rem 1.2rem; border-radius: 8px; font-weight: 600; }}
  .parts li {{ margin: .4rem 0; }}
  .nosrc {{ font-size: .9rem; color: #5a6675; }}
</style>
</head>
<body>
<header class="app-header">
  <h1>How a Hydraulic Ram Pump Works</h1>
  <p class="subtitle">The four-stage cycle, from the original patents</p>
</header>

<main class="prose">

  <p>A hydraulic ram pump moves water uphill using no electricity, no fuel and no motor.
  It runs on the one thing it already has: water falling a short distance. It wastes most
  of that water to lift a little of it a long way, and it will do that continuously for
  years with no moving part other than two valves.</p>

  <p>The mechanism is over two centuries old and every patent describing it has long since
  expired, so the design belongs to everybody. What follows is drawn from three of
  them ({esc(ids)}), the newest of which ran out of term in
  {esc(newest_expiry[:4])}.</p>

  {diagram_svg()}

  <h2>The four-stage cycle</h2>
  <ol class="stages">
{stage_html}
  </ol>

  <div class="callout">
    <h2>The counter-intuitive part</h2>
    <p>Most people assume the pump is powered by the <em>weight</em> of the falling water.
    It is not. It is powered by the <em>shock of stopping</em> it. That is why a ram needs
    a long drive pipe rather than a tall one: the pipe's job is to give a heavy
    column of water somewhere to build up speed before the waste valve stops it dead.</p>
  </div>

  <h2>Where each idea came from</h2>
  <p>These are not decoration. Each patent below contributed a specific piece of the
  machine that is still central to how rams are designed today.</p>

{patent_html}

  <h2>What &ldquo;expired&rdquo; actually means here</h2>
  <p>A US patent is a time-limited deal: the inventor publishes exactly how the thing works,
  and in exchange gets a limited monopoly on building it. When the term runs out the
  monopoly ends but the published instructions stay published, permanently, in
  full, free to read.</p>
  <p>{esc(d['_TERM_RULE'])}</p>
  <p>{esc(d['_PD_RULE'])}</p>
  <p><strong>Practical upshot:</strong> the three patents above stopped constraining
  anybody more than a century ago. Nobody needs a licence from them, and there is nobody
  left to ask.</p>
  <p class="nosrc">Said precisely, because the precise version is the useful one: an expired
  patent's claims stop binding people, but that is not a clearance opinion on whatever you
  personally go and build. A modern pump with modern refinements could still read on some
  other patent that is still in force. What is settled is that <em>these</em> designs, as
  published in <em>these</em> documents, are nobody's property any more.</p>

  <h2>The parts, by name</h2>
  <ul class="parts">
    <li><strong>Drive pipe</strong>: the long feed from the source. Where the water
      builds momentum. Rigid, never a soft hose.</li>
    <li><strong>Waste valve</strong>: the one that slams shut. Does the work of
      stopping the column, and spills the water the pump does not lift.</li>
    <li><strong>Delivery check valve</strong>: one-way gate into the air chamber.
      Opens on the pressure spike, shuts so nothing runs back.</li>
    <li><strong>Air chamber</strong>: a sealed pocket of trapped air. Absorbs each
      shock and pushes back between beats, converting hammer blows into steady flow.</li>
    <li><strong>Delivery pipe</strong>: the climb to the tank.</li>
  </ul>
  <p class="nosrc">Deliberately not listed: pipe diameters, drive-pipe length ratios and
  parts costs. Several rules of thumb circulate for these and none was traced to a primary
  source while writing this page, so none is printed. A number with no source is exactly
  what makes the scanned PDFs already on this topic hard to trust.</p>

  <h2>The arithmetic</h2>
  <p>How much water actually arrives is set by four numbers and one efficiency figure:</p>
  <div class="formula">{esc(phys['delivered_flow_formula'])}
&nbsp;
q = {esc(phys['symbols']['q'])}
Q = {esc(phys['symbols']['Q'])}
H = {esc(phys['symbols']['H'])}
h = {esc(phys['symbols']['h'])}</div>
  <p>That rearranges to the {esc(phys['efficiency_metric'])} efficiency,
  <code>{esc(phys['efficiency_formula'])}</code>. {esc(phys['note'])}</p>

  <div class="callout">
    <h2>Careful: the textbooks swap these two letters</h2>
    <p>{esc(phys['symbol_warning'])}</p>
  </div>

  <p>{esc(phys['losses_note'])} {esc(phys['rankine_note'])}</p>
  <p>For scale: {esc(phys['measured_efficiency_reference'])}
  <span class="nosrc">({esc(phys['measured_efficiency_source'])})</span></p>

  <p><a class="cta" href="../">Run your numbers in the sizer &rarr;</a></p>

</main>

<footer class="prose">
  <p class="nosrc">Patent facts on this page are read from
  <code>data/patents.json</code>, verified against each patent's own Google Patents record
  on {esc(d['verified_on'])}. No affiliate links appear anywhere on this site.</p>
  <p class="fine"><a href="https://fscholtesdowd.github.io/privacy/">Privacy policy</a> &middot; <a href="https://fscholtesdowd.github.io/terms/">Terms</a></p>
</footer>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report what would be written; write nothing")
    args = ap.parse_args()

    d = load()
    page = render(d)

    if args.check:
        print(f"would write {OUT} ({len(page):,} bytes)")
        print(f"patents cited: {', '.join(p['id'] for p in d['patents'])}")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} ({len(page):,} bytes)")
    print(f"patents cited: {', '.join(p['id'] for p in d['patents'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
