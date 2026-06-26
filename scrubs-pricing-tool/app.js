// ─────────────────────────────────────────────────────────────────────────────
// Config helpers
// ─────────────────────────────────────────────────────────────────────────────

function getConfig() {
  try {
    const saved = localStorage.getItem("scrubsConfig");
    if (saved) return JSON.parse(saved);
  } catch (_) {}
  return structuredClone(DEFAULT_CONFIG);
}

function saveConfig(cfg) {
  localStorage.setItem("scrubsConfig", JSON.stringify(cfg));
}

// ─────────────────────────────────────────────────────────────────────────────
// Scoring
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Calculates a condition score [1–4] for a single garment.
 *
 * Regular defects are capped at 3 before extra defects are added.
 * Score is then clamped to the [1, 4] range.
 *
 * Parameters reference:
 *  manchas         : 'ninguna' | 'pequeña' | 'varias'
 *  desgaste        : 'no' | 'ligero' | 'notable'
 *  pilling         : 'no' | 'leve' | 'notable'          ← fabric pilling
 *  estadoGeneral   : 'nuevo' | 'buen_uso' | 'uso_medio' | 'muy_usado'
 *  roturas         : 'no' | 'pequeñas' | 'si'
 *  deshilachados   : boolean
 *  faltaCordón     : boolean   (only relevant for pants)
 *  olor            : boolean   ← persistent odor
 *  elastico        : boolean   ← stretched waistband / deformed neckline
 *  costuras        : boolean   ← loose/open seams
 */
function calculateGarmentScore(d) {
  // Regular defects (capped at 3)
  let regular = 0;
  if (d.manchas === "pequeña")   regular += 1;
  if (d.manchas === "varias")    regular += 2;
  if (d.desgaste === "ligero")   regular += 1;
  if (d.desgaste === "notable")  regular += 2;
  if (d.pilling === "leve")      regular += 0.5;
  if (d.pilling === "notable")   regular += 1;
  if (d.estadoGeneral === "uso_medio") regular += 1;
  if (d.estadoGeneral === "muy_usado") regular += 2;
  regular = Math.min(regular, 3);

  // Extra defects (not subject to the cap)
  let extra = 0;
  if (d.roturas === "pequeñas")  extra += 0.5;
  if (d.roturas === "si")        extra += 1;
  if (d.deshilachados)           extra += 1;
  if (d.faltaCordón)             extra += 1;
  if (d.olor)                    extra += 1;
  if (d.elastico)                extra += 0.5;
  if (d.costuras)                extra += 0.5;

  const score = 4 - regular - extra;
  return Math.max(1, Math.round(score * 10) / 10);
}

function getConditionBand(score) {
  const cfg = getConfig();
  for (const t of cfg.factors.conditionThresholds) {
    if (score >= t.minScore) {
      return { factor: t.factor, label: t.label };
    }
  }
  const last = cfg.factors.conditionThresholds.at(-1);
  return { factor: last.factor, label: last.label };
}

// ─────────────────────────────────────────────────────────────────────────────
// Price calculation
// ─────────────────────────────────────────────────────────────────────────────

// Spec uses floor rounding: $765 → $760 (not $770)
function roundToNearest(value, multiple) {
  return Math.floor(value / multiple) * multiple;
}

/**
 * Main pricing engine.
 *
 * @param {object} params
 *   topBrandId, bottomBrandId — brand IDs from config
 *   topScore, bottomScore     — scores from calculateGarmentScore()
 *   isSet                     — true = conjunto completo
 *   activePiece               — 'top' | 'bottom' (used when !isSet)
 *
 * @returns {object} { price, breakdown }
 */
function calculatePrice(params) {
  const cfg = getConfig();
  const { topBrandId, bottomBrandId, topScore, bottomScore, isSet, activePiece } = params;

  const topBrand    = cfg.brands.find(b => b.id === topBrandId);
  const bottomBrand = cfg.brands.find(b => b.id === bottomBrandId);

  // Dominant brand, FM and avg score differ between set and single-piece mode.
  let dominantBrand, sameBrand, FM, fmLabel, avgScore;
  if (isSet) {
    // Dominant brand = lower tier number (more premium) → higher base price
    dominantBrand = topBrand.tier <= bottomBrand.tier ? topBrand : bottomBrand;
    sameBrand = topBrandId === bottomBrandId;
    FM = sameBrand ? 1.0 : cfg.factors.mixedBrands;
    fmLabel = sameBrand ? "Misma marca (×1.00)" : `Marcas distintas (×${FM.toFixed(2)})`;
    avgScore = Math.round(((topScore + bottomScore) / 2) * 10) / 10;
  } else {
    // Single piece: only the active garment's brand matters, no mixed penalty
    dominantBrand = activePiece === "top" ? topBrand : bottomBrand;
    sameBrand = true;
    FM = 1.0;
    fmLabel = "Pieza única (×1.00)";
    avgScore = activePiece === "top" ? topScore : bottomScore;
  }
  const basePrice = dominantBrand.basePrice;

  // FC — condition factor
  const condBand = getConditionBand(avgScore);
  const FC = condBand.factor;

  // FS — single-piece factor
  const FS = isSet ? 1.0 : cfg.factors.loosePiece;
  const fsLabel = isSet ? "Conjunto completo (×1.00)" : `Pieza suelta (×${FS.toFixed(2)})`;

  let rawPrice = basePrice * FM * FC * FS;

  // Ceiling: can never exceed base (for set) or base × FS (for piece)
  const ceiling = isSet ? basePrice : Math.round(basePrice * FS);
  const ceilingApplied = rawPrice > ceiling;
  if (ceilingApplied) rawPrice = ceiling;

  // Floor
  const floor = isSet ? cfg.floors.set : cfg.floors.piece;
  const floorApplied = rawPrice < floor;
  if (floorApplied) rawPrice = floor;

  const price = roundToNearest(rawPrice, cfg.roundTo);

  return {
    price,
    breakdown: {
      dominantBrandName: dominantBrand.name,
      dominantBrandTier: dominantBrand.tier,
      basePrice,
      topScore,
      bottomScore,
      avgScore,
      conditionLabel: condBand.label,
      FM, fmLabel,
      FC, fcLabel: `Condición ${condBand.label} (×${FC.toFixed(2)})`,
      FS, fsLabel,
      rawPrice: Math.round(rawPrice),
      floor,
      ceiling,
      floorApplied,
      ceilingApplied,
      isSet
    }
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// History
// ─────────────────────────────────────────────────────────────────────────────

function getHistory() {
  try {
    return JSON.parse(localStorage.getItem("scrubsHistory") || "[]");
  } catch (_) {
    return [];
  }
}

function saveToHistory(entry) {
  const history = getHistory();
  history.unshift({ ...entry, id: Date.now(), ts: new Date().toISOString() });
  // Keep at most 100 entries
  localStorage.setItem("scrubsHistory", JSON.stringify(history.slice(0, 100)));
}

function clearHistory() {
  localStorage.removeItem("scrubsHistory");
}

function deleteHistoryEntry(id) {
  const history = getHistory().filter(e => e.id !== id);
  localStorage.setItem("scrubsHistory", JSON.stringify(history));
}

// ─────────────────────────────────────────────────────────────────────────────
// DOM helpers
// ─────────────────────────────────────────────────────────────────────────────

function qs(sel, ctx = document) { return ctx.querySelector(sel); }
function qsa(sel, ctx = document) { return [...ctx.querySelectorAll(sel)]; }

function buildBrandOptions(selectEl, selectedId) {
  const cfg = getConfig();
  const tiers = [
    { num: 1, label: "Tier 1 — Premium" },
    { num: 2, label: "Tier 2 — Intermedio" },
    { num: 3, label: "Tier 3 — Básico" }
  ];
  selectEl.innerHTML = "";
  tiers.forEach(tier => {
    const brands = cfg.brands.filter(b => b.tier === tier.num);
    if (!brands.length) return;
    const group = document.createElement("optgroup");
    group.label = tier.label;
    brands.forEach(b => {
      const opt = document.createElement("option");
      opt.value = b.id;
      opt.textContent = `${b.name}  ($${b.basePrice})`;
      if (b.id === selectedId) opt.selected = true;
      group.appendChild(opt);
    });
    selectEl.appendChild(group);
  });
}

function readGarmentData(prefix) {
  return {
    manchas:       qs(`[name="${prefix}_manchas"]:checked`)?.value        || "ninguna",
    desgaste:      qs(`[name="${prefix}_desgaste"]:checked`)?.value       || "no",
    pilling:       qs(`[name="${prefix}_pilling"]:checked`)?.value        || "no",
    estadoGeneral: qs(`[name="${prefix}_estadoGeneral"]:checked`)?.value  || "nuevo",
    roturas:       qs(`[name="${prefix}_roturas"]:checked`)?.value        || "no",
    deshilachados: qs(`#${prefix}_deshilachados`)?.checked                || false,
    faltaCordón:   qs(`#${prefix}_faltaCordón`)?.checked                  || false,
    olor:          qs(`#${prefix}_olor`)?.checked                         || false,
    elastico:      qs(`#${prefix}_elastico`)?.checked                     || false,
    costuras:      qs(`#${prefix}_costuras`)?.checked                     || false,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Render results
// ─────────────────────────────────────────────────────────────────────────────

function renderResult(result, brandNames) {
  const { price, breakdown: b } = result;
  const section = qs("#result-section");

  // Big price
  qs("#result-price").textContent = `$${price.toLocaleString("es-MX")} MXN`;

  // Score bar visual
  const scoreVal = (b.avgScore / 4) * 100;
  qs("#score-fill").style.width = `${scoreVal}%`;
  qs("#score-fill").className = `score-fill ${getScoreClass(b.avgScore)}`;
  qs("#score-label").textContent = `${b.avgScore.toFixed(1)} / 4.0 — ${b.conditionLabel}`;

  // Breakdown table
  const rows = [
    ["Marca dominante",  `${b.dominantBrandName} (Tier ${b.dominantBrandTier})`],
    ["Precio base",      `$${b.basePrice} MXN`],
    ["Factor marca (FM)", b.fmLabel],
    ["Factor condición (FC)", b.fcLabel],
    ["Factor pieza (FS)", b.fsLabel],
    ["Precio calculado", `$${Math.round(b.FM * b.FC * b.FS * b.basePrice)} MXN`],
  ];
  if (b.floorApplied)   rows.push(["Ajuste", `Piso mínimo aplicado → $${b.floor} MXN`]);
  if (b.ceilingApplied) rows.push(["Ajuste", `Techo máximo aplicado → $${b.ceiling} MXN`]);
  rows.push(["Precio final redondeado", `$${price} MXN`]);

  qs("#breakdown-table tbody").innerHTML = rows.map(([k, v]) =>
    `<tr><th>${k}</th><td>${v}</td></tr>`
  ).join("");

  // Per-garment scores
  if (b.isSet) {
    qs("#score-top").textContent    = `Filipina: ${b.topScore.toFixed(1)}/4`;
    qs("#score-bottom").textContent = `Pantalón: ${b.bottomScore.toFixed(1)}/4`;
    qs("#score-detail").hidden = false;
  } else {
    qs("#score-detail").hidden = true;
  }

  section.hidden = false;
  section.scrollIntoView({ behavior: "smooth", block: "start" });

  // Return entry for history
  return {
    price,
    topBrand: brandNames.top,
    bottomBrand: brandNames.bottom,
    isSet: b.isSet,
    avgScore: b.avgScore,
    conditionLabel: b.conditionLabel,
    breakdown: b
  };
}

function getScoreClass(score) {
  if (score >= 3.5) return "score-excellent";
  if (score >= 3.0) return "score-good";
  if (score >= 2.5) return "score-fair";
  if (score >= 2.0) return "score-poor";
  return "score-bad";
}

// ─────────────────────────────────────────────────────────────────────────────
// History rendering
// ─────────────────────────────────────────────────────────────────────────────

function renderHistory() {
  const history = getHistory();
  const container = qs("#history-list");
  const emptyMsg  = qs("#history-empty");

  if (!history.length) {
    container.innerHTML = "";
    emptyMsg.hidden = false;
    return;
  }
  emptyMsg.hidden = true;

  container.innerHTML = history.map(e => {
    const date = new Date(e.ts).toLocaleDateString("es-MX", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit"
    });
    const typeLabel = e.isSet ? "Conjunto" : "Pieza suelta";
    const brandLabel = e.isSet
      ? `${e.topBrand} + ${e.bottomBrand}`
      : (e.topBrand || e.bottomBrand);
    return `
      <div class="history-card" data-id="${e.id}">
        <div class="history-info">
          <span class="history-brands">${brandLabel}</span>
          <span class="history-type">${typeLabel}</span>
          <span class="history-condition">${e.conditionLabel} (${e.avgScore.toFixed(1)})</span>
          <span class="history-date">${date}</span>
        </div>
        <div class="history-price">$${e.price.toLocaleString("es-MX")}</div>
        <button class="btn-delete-history" data-id="${e.id}" title="Eliminar">✕</button>
      </div>`;
  }).join("");

  // Delete buttons
  qsa(".btn-delete-history").forEach(btn => {
    btn.addEventListener("click", e => {
      e.stopPropagation();
      deleteHistoryEntry(Number(btn.dataset.id));
      renderHistory();
    });
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Set / single piece toggle
// ─────────────────────────────────────────────────────────────────────────────

function applyModeUI() {
  const mode = qs('input[name="mode"]:checked').value; // 'set' | 'top' | 'bottom'
  const topCard    = qs("#card-top");
  const bottomCard = qs("#card-bottom");

  topCard.classList.toggle("card-faded",    mode === "bottom");
  bottomCard.classList.toggle("card-faded", mode === "top");

  qs("#score-detail").hidden = true;
}

// ─────────────────────────────────────────────────────────────────────────────
// Main init
// ─────────────────────────────────────────────────────────────────────────────

let lastEntry = null;

function init() {
  const cfg = getConfig();

  // Build brand dropdowns
  buildBrandOptions(qs("#top-brand"), "cherokee");
  buildBrandOptions(qs("#bottom-brand"), "cherokee");

  // Mode toggle
  qsa('input[name="mode"]').forEach(r => r.addEventListener("change", applyModeUI));
  applyModeUI();

  // Auto-recalculate on any input change (live preview)
  document.addEventListener("change", e => {
    if (e.target.closest("#form-section")) {
      // Debounce the live recalc so it doesn't fire on every radio click storm
      clearTimeout(window._calcTimer);
      window._calcTimer = setTimeout(doCalculate, 150);
    }
  });

  // Cotizar button
  qs("#btn-calculate").addEventListener("click", doCalculate);

  // Save to history
  qs("#btn-save").addEventListener("click", () => {
    if (!lastEntry) return;
    saveToHistory(lastEntry);
    renderHistory();
    const btn = qs("#btn-save");
    btn.textContent = "¡Guardado!";
    btn.disabled = true;
    setTimeout(() => {
      btn.textContent = "Guardar en historial";
      btn.disabled = false;
    }, 2000);
  });

  // History accordion toggle
  qs("#history-toggle").addEventListener("click", () => {
    const body = qs("#history-body");
    const isOpen = !body.hidden;
    body.hidden = isOpen;
    qs("#history-toggle").textContent = isOpen ? "▸ Historial de cotizaciones" : "▾ Historial de cotizaciones";
  });

  // Clear history
  qs("#btn-clear-history").addEventListener("click", () => {
    if (confirm("¿Eliminar todo el historial?")) {
      clearHistory();
      renderHistory();
    }
  });

  // Initial history render
  renderHistory();

  // Reset button
  qs("#btn-reset").addEventListener("click", resetForm);
}

function doCalculate() {
  const mode = qs('input[name="mode"]:checked').value;
  const isSet = mode === "set";
  const activePiece = isSet ? null : mode; // 'top' | 'bottom'

  const topBrandId    = qs("#top-brand").value;
  const bottomBrandId = qs("#bottom-brand").value;

  const topData    = readGarmentData("top");
  const bottomData = readGarmentData("bottom");

  const topScore    = calculateGarmentScore(topData);
  const bottomScore = calculateGarmentScore(bottomData);

  const result = calculatePrice({
    topBrandId, bottomBrandId, topScore, bottomScore, isSet, activePiece
  });

  const cfg = getConfig();
  const topBrandName    = cfg.brands.find(b => b.id === topBrandId)?.name    || topBrandId;
  const bottomBrandName = cfg.brands.find(b => b.id === bottomBrandId)?.name || bottomBrandId;

  lastEntry = renderResult(result, { top: topBrandName, bottom: bottomBrandName });
  lastEntry.topBrand    = topBrandName;
  lastEntry.bottomBrand = bottomBrandName;

  // Re-enable save button for new calculation
  const btn = qs("#btn-save");
  btn.textContent = "Guardar en historial";
  btn.disabled = false;
}

function resetForm() {
  qsa('input[type="radio"]').forEach(r => {
    r.checked = r.dataset.default === "true";
  });
  qsa('input[type="checkbox"]').forEach(cb => { cb.checked = false; });
  qs('input[name="mode"][value="set"]').checked = true;
  applyModeUI();
  qs("#result-section").hidden = true;
  lastEntry = null;
}

document.addEventListener("DOMContentLoaded", init);
