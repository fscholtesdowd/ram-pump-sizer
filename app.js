(() => {
  "use strict";

  const el = (id) => document.getElementById(id);

  const supplyFlow = el("supplyFlow");
  const supplyFlowUnit = el("supplyFlowUnit");
  const driveHead = el("driveHead");
  const driveHeadUnit = el("driveHeadUnit");
  const deliveryHead = el("deliveryHead");
  const deliveryHeadUnit = el("deliveryHeadUnit");
  const efficiency = el("efficiency");
  const efficiencyValue = el("efficiencyValue");
  const effSuggestLabel = el("effSuggestLabel");

  const deliveredFlowEl = el("deliveredFlow");
  const deliveredPerDayEl = el("deliveredPerDay");
  const wasteFlowEl = el("wasteFlow");
  const ratioValueEl = el("ratioValue");
  const ratioWarningEl = el("ratioWarning");

  // --- unit conversion helpers (base units: L/min for flow, m for length) ---
  const FLOW_TO_LPM = { Lpm: 1, Lps: 60, m3h: 1000 / 60, gpm: 3.785411784 };
  const LPM_TO_FLOW = { Lpm: 1, Lps: 1 / 60, m3h: 60 / 1000, gpm: 1 / 3.785411784 };
  const LENGTH_TO_M = { m: 1, ft: 0.3048 };

  const FLOW_UNIT_LABEL = { Lpm: "L/min", Lps: "L/s", m3h: "m³/hr", gpm: "gal/min" };
  const DAILY_UNIT_LABEL = { Lpm: "L/day", Lps: "L/day", m3h: "m³/day", gpm: "gal/day" };

  function toLpm(value, unit) {
    return value * FLOW_TO_LPM[unit];
  }
  function fromLpm(valueLpm, unit) {
    return valueLpm * LPM_TO_FLOW[unit];
  }
  function toMeters(value, unit) {
    return value * LENGTH_TO_M[unit];
  }

  // Piecewise-linear efficiency suggestion vs h/H ratio, based on published
  // single-stage hydraulic ram pump performance data (D'Aubuisson efficiency).
  const EFF_CURVE = [
    [1, 0.85],
    [10, 0.75],
    [20, 0.65],
    [30, 0.55],
    [50, 0.35],
    [80, 0.20],
  ];

  function suggestEfficiency(ratio) {
    if (ratio <= EFF_CURVE[0][0]) return EFF_CURVE[0][1];
    for (let i = 0; i < EFF_CURVE.length - 1; i++) {
      const [r0, e0] = EFF_CURVE[i];
      const [r1, e1] = EFF_CURVE[i + 1];
      if (ratio <= r1) {
        const t = (ratio - r0) / (r1 - r0);
        return e0 + t * (e1 - e0);
      }
    }
    return EFF_CURVE[EFF_CURVE.length - 1][1];
  }

  function fmt(n, digits = 2) {
    if (!isFinite(n)) return "—";
    return n.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: 0 });
  }

  let userOverrodeEfficiency = false;
  efficiency.addEventListener("input", () => {
    userOverrodeEfficiency = true;
    efficiencyValue.textContent = `${efficiency.value}%`;
    calculate();
  });

  function updateSuggestedEfficiency(ratio) {
    const suggested = Math.round(suggestEfficiency(ratio) * 100);
    effSuggestLabel.textContent = isFinite(ratio) ? `(suggested ${suggested}%)` : "";
    if (!userOverrodeEfficiency && isFinite(ratio)) {
      efficiency.value = String(suggested);
      efficiencyValue.textContent = `${suggested}%`;
    }
  }

  function setWarning(message, level) {
    if (!message) {
      ratioWarningEl.hidden = true;
      ratioWarningEl.textContent = "";
      ratioWarningEl.classList.remove("danger");
      return;
    }
    ratioWarningEl.hidden = false;
    ratioWarningEl.textContent = message;
    ratioWarningEl.classList.toggle("danger", level === "danger");
  }

  function calculate() {
    const qRaw = parseFloat(supplyFlow.value);
    const HRaw = parseFloat(driveHead.value);
    const hRaw = parseFloat(deliveryHead.value);
    const eFrac = parseFloat(efficiency.value) / 100;

    const haveInputs = supplyFlow.value !== "" && driveHead.value !== "" && deliveryHead.value !== "";

    if (!haveInputs || isNaN(qRaw) || isNaN(HRaw) || isNaN(hRaw)) {
      deliveredFlowEl.textContent = "—";
      deliveredPerDayEl.textContent = "—";
      wasteFlowEl.textContent = "—";
      ratioValueEl.textContent = "—";
      effSuggestLabel.textContent = "";
      setWarning(null);
      return;
    }

    const Q_lpm = toLpm(qRaw, supplyFlowUnit.value);
    const H_m = toMeters(HRaw, driveHeadUnit.value);
    const h_m = toMeters(hRaw, deliveryHeadUnit.value);

    if (H_m <= 0) {
      setWarning("Drive head (fall) must be greater than 0.", "danger");
      deliveredFlowEl.textContent = "—";
      deliveredPerDayEl.textContent = "—";
      wasteFlowEl.textContent = "—";
      ratioValueEl.textContent = "—";
      return;
    }
    if (h_m <= 0) {
      setWarning("Delivery head (lift) must be greater than 0.", "danger");
      deliveredFlowEl.textContent = "—";
      deliveredPerDayEl.textContent = "—";
      wasteFlowEl.textContent = "—";
      ratioValueEl.textContent = "—";
      return;
    }

    const ratio = h_m / H_m;
    updateSuggestedEfficiency(ratio);

    const eNow = parseFloat(efficiency.value) / 100;
    const q_lpm = eNow * Q_lpm * H_m / h_m;
    const waste_lpm = Math.max(Q_lpm - q_lpm, 0);

    const flowUnit = supplyFlowUnit.value;
    deliveredFlowEl.textContent = `${fmt(fromLpm(q_lpm, flowUnit))} ${FLOW_UNIT_LABEL[flowUnit]}`;
    wasteFlowEl.textContent = `${fmt(fromLpm(waste_lpm, flowUnit))} ${FLOW_UNIT_LABEL[flowUnit]}`;

    const perDayBase = q_lpm * 1440; // L/day
    let perDayDisplay;
    if (flowUnit === "gpm") {
      perDayDisplay = `${fmt(fromLpm(q_lpm, "gpm") * 1440, 0)} ${DAILY_UNIT_LABEL[flowUnit]}`;
    } else if (flowUnit === "m3h") {
      perDayDisplay = `${fmt(perDayBase / 1000, 1)} ${DAILY_UNIT_LABEL[flowUnit]}`;
    } else {
      perDayDisplay = `${fmt(perDayBase, 0)} ${DAILY_UNIT_LABEL[flowUnit]}`;
    }
    deliveredPerDayEl.textContent = perDayDisplay;

    ratioValueEl.textContent = `${fmt(ratio, 1)} : 1`;

    if (ratio < 2) {
      setWarning("Fall is large relative to lift. A ram pump will work, but a simpler gravity-fed pipe might cover this without a pump.", null);
    } else if (ratio <= 30) {
      setWarning(null);
    } else if (ratio <= 50) {
      setWarning("h/H ratio is high (>30:1). Efficiency drops and a well-tuned, quality ram pump becomes important for reliable delivery.", "warning");
    } else {
      setWarning("h/H ratio is very high (>50:1). A single-stage ram pump is unlikely to deliver well at this ratio — consider increasing the drive head, reducing the lift, or staging two ram pumps.", "danger");
    }

    saveState();
  }

  [supplyFlow, driveHead, deliveryHead].forEach((elm) => {
    elm.addEventListener("input", calculate);
  });

  // Unit selects: convert the existing value to preserve the physical
  // quantity, rather than silently reinterpreting the number.
  function wireUnitConversion(inputEl, selectEl, toBase, fromBase) {
    let prevUnit = selectEl.value;
    selectEl.addEventListener("change", () => {
      const raw = parseFloat(inputEl.value);
      if (!isNaN(raw)) {
        const base = toBase(raw, prevUnit);
        inputEl.value = round(fromBase(base, selectEl.value));
      }
      prevUnit = selectEl.value;
      calculate();
    });
  }
  function round(n) {
    // Round to 3 significant decimals for a clean, editable input value.
    return Math.round(n * 1000) / 1000;
  }

  // --- persistence ---
  const STORAGE_KEY = "ram-pump-sizer-state-v1";
  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        supplyFlow: supplyFlow.value,
        supplyFlowUnit: supplyFlowUnit.value,
        driveHead: driveHead.value,
        driveHeadUnit: driveHeadUnit.value,
        deliveryHead: deliveryHead.value,
        deliveryHeadUnit: deliveryHeadUnit.value,
        efficiency: efficiency.value,
        userOverrodeEfficiency,
      }));
    } catch (e) { /* localStorage unavailable, ignore */ }
  }

  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const s = JSON.parse(raw);
      supplyFlow.value = s.supplyFlow ?? "";
      supplyFlowUnit.value = s.supplyFlowUnit ?? "Lpm";
      driveHead.value = s.driveHead ?? "";
      driveHeadUnit.value = s.driveHeadUnit ?? "m";
      deliveryHead.value = s.deliveryHead ?? "";
      deliveryHeadUnit.value = s.deliveryHeadUnit ?? "m";
      efficiency.value = s.efficiency ?? "60";
      efficiencyValue.textContent = `${efficiency.value}%`;
      userOverrodeEfficiency = !!s.userOverrodeEfficiency;
    } catch (e) { /* ignore */ }
  }

  loadState();

  // Wire unit-conversion listeners after state has loaded so the
  // "previous unit" baseline matches what's actually on screen.
  wireUnitConversion(supplyFlow, supplyFlowUnit, toLpm, fromLpm);
  wireUnitConversion(driveHead, driveHeadUnit, toMeters, (v, u) => v / LENGTH_TO_M[u]);
  wireUnitConversion(deliveryHead, deliveryHeadUnit, toMeters, (v, u) => v / LENGTH_TO_M[u]);

  calculate();

  // --- PWA install prompt ---
  const installBtn = el("installBtn");
  let deferredPrompt = null;
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    installBtn.hidden = false;
  });
  installBtn.addEventListener("click", async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    deferredPrompt = null;
    installBtn.hidden = true;
  });
  window.addEventListener("appinstalled", () => {
    installBtn.hidden = true;
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("sw.js").catch(() => { /* ignore */ });
    });
  }
})();
