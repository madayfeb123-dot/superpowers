// ─────────────────────────────────────────────────────────────────────────────
// Admin panel logic
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

function qs(sel, ctx = document) { return ctx.querySelector(sel); }
function qsa(sel, ctx = document) { return [...ctx.querySelectorAll(sel)]; }

// ─────────────────────────────────────────────────────────────────────────────
// Tabs
// ─────────────────────────────────────────────────────────────────────────────

function initTabs() {
  qsa(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      qsa(".tab-btn").forEach(b => b.classList.remove("active"));
      qsa(".tab-panel").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      qs(`#panel-${btn.dataset.tab}`).classList.add("active");
    });
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Brand table
// ─────────────────────────────────────────────────────────────────────────────

function renderBrandTable() {
  const cfg = getConfig();
  const tbody = qs("#brand-tbody");

  tbody.innerHTML = cfg.brands.map((b, i) => `
    <tr data-index="${i}">
      <td>
        <input type="text" class="brand-id" value="${b.id}" placeholder="id_unico"
               style="width:130px">
      </td>
      <td>
        <input type="text" class="brand-name" value="${b.name}" placeholder="Nombre visible"
               style="width:180px">
      </td>
      <td>
        <select class="brand-tier">
          <option value="1" ${b.tier === 1 ? "selected" : ""}>1 — Premium</option>
          <option value="2" ${b.tier === 2 ? "selected" : ""}>2 — Intermedio</option>
          <option value="3" ${b.tier === 3 ? "selected" : ""}>3 — Básico</option>
        </select>
      </td>
      <td>
        <input type="number" class="brand-price" value="${b.basePrice}" min="0" step="10"
               style="width:90px"> MXN
      </td>
      <td>
        <button class="btn btn-danger btn-delete-brand" data-index="${i}"
                style="padding:4px 10px;font-size:.8rem">✕</button>
      </td>
    </tr>
  `).join("");

  // Delete buttons
  qsa(".btn-delete-brand").forEach(btn => {
    btn.addEventListener("click", () => {
      const cfg2 = getConfig();
      cfg2.brands.splice(Number(btn.dataset.index), 1);
      saveConfig(cfg2);
      renderBrandTable();
      showAlert("brand-alert", "Marca eliminada.", "success");
    });
  });
}

function collectBrandTable() {
  const rows = qsa("#brand-tbody tr");
  return rows.map(row => ({
    id:        row.querySelector(".brand-id").value.trim(),
    name:      row.querySelector(".brand-name").value.trim(),
    tier:      Number(row.querySelector(".brand-tier").value),
    basePrice: Number(row.querySelector(".brand-price").value),
  })).filter(b => b.id && b.name && b.basePrice > 0);
}

// ─────────────────────────────────────────────────────────────────────────────
// Condition thresholds table
// ─────────────────────────────────────────────────────────────────────────────

function renderThresholds() {
  const cfg = getConfig();
  const tbody = qs("#threshold-tbody");

  tbody.innerHTML = cfg.factors.conditionThresholds.map((t, i) => `
    <tr data-index="${i}">
      <td>
        <input type="number" class="thresh-min" value="${t.minScore}"
               min="0" max="4" step="0.1" style="width:70px">
      </td>
      <td>
        <input type="number" class="thresh-factor" value="${t.factor}"
               min="0" max="1" step="0.01" style="width:70px">
      </td>
      <td>
        <input type="text" class="thresh-label" value="${t.label}" style="width:120px">
      </td>
      <td>
        <button class="btn btn-danger btn-delete-thresh" data-index="${i}"
                style="padding:4px 10px;font-size:.8rem">✕</button>
      </td>
    </tr>
  `).join("");

  qsa(".btn-delete-thresh").forEach(btn => {
    btn.addEventListener("click", () => {
      const cfg2 = getConfig();
      cfg2.factors.conditionThresholds.splice(Number(btn.dataset.index), 1);
      saveConfig(cfg2);
      renderThresholds();
    });
  });
}

function collectThresholds() {
  return qsa("#threshold-tbody tr").map(row => ({
    minScore: Number(row.querySelector(".thresh-min").value),
    factor:   Number(row.querySelector(".thresh-factor").value),
    label:    row.querySelector(".thresh-label").value.trim(),
  }));
}

// ─────────────────────────────────────────────────────────────────────────────
// Alerts
// ─────────────────────────────────────────────────────────────────────────────

function showAlert(id, msg, type = "success") {
  const el = qs(`#${id}`);
  if (!el) return;
  el.textContent = msg;
  el.className = `alert alert-${type}`;
  el.hidden = false;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.hidden = true; }, 3000);
}

// ─────────────────────────────────────────────────────────────────────────────
// Render history
// ─────────────────────────────────────────────────────────────────────────────

function renderHistory() {
  let history = [];
  try {
    history = JSON.parse(localStorage.getItem("scrubsHistory") || "[]");
  } catch (_) {}

  const container = qs("#admin-history-list");
  if (!history.length) {
    container.innerHTML = '<p class="text-muted">No hay cotizaciones guardadas.</p>';
    return;
  }

  container.innerHTML = `
    <table class="brand-table" style="font-size:.83rem">
      <thead>
        <tr>
          <th>Fecha</th>
          <th>Marcas</th>
          <th>Tipo</th>
          <th>Condición</th>
          <th>Precio</th>
        </tr>
      </thead>
      <tbody>
        ${history.map(e => {
          const date = new Date(e.ts).toLocaleDateString("es-MX", {
            day: "2-digit", month: "short", year: "2-digit",
            hour: "2-digit", minute: "2-digit"
          });
          const brands = e.isSet
            ? `${e.topBrand} + ${e.bottomBrand}`
            : (e.topBrand || e.bottomBrand);
          return `<tr>
            <td>${date}</td>
            <td>${brands}</td>
            <td>${e.isSet ? "Conjunto" : "Pieza suelta"}</td>
            <td>${e.conditionLabel} (${Number(e.avgScore).toFixed(1)})</td>
            <td><strong>$${e.price}</strong></td>
          </tr>`;
        }).join("")}
      </tbody>
    </table>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Export / Import
// ─────────────────────────────────────────────────────────────────────────────

function exportConfig() {
  const cfg = getConfig();
  const blob = new Blob([JSON.stringify(cfg, null, 2)], { type: "application/json" });
  const url  = URL.createObjectURL(blob);
  const a    = Object.assign(document.createElement("a"), {
    href: url, download: "scrubs-config.json"
  });
  a.click();
  URL.revokeObjectURL(url);
}

function importConfig(file) {
  const reader = new FileReader();
  reader.onload = e => {
    try {
      const cfg = JSON.parse(e.target.result);
      if (!cfg.brands || !cfg.factors) throw new Error("Formato inválido");
      saveConfig(cfg);
      renderBrandTable();
      renderThresholds();
      loadFactorFields();
      showAlert("import-alert", "Configuración importada correctamente.", "success");
    } catch (err) {
      showAlert("import-alert", `Error: ${err.message}`, "danger");
    }
  };
  reader.readAsText(file);
}

// ─────────────────────────────────────────────────────────────────────────────
// Factor fields (simple multipliers)
// ─────────────────────────────────────────────────────────────────────────────

function loadFactorFields() {
  const cfg = getConfig();
  qs("#factor-mixed").value    = cfg.factors.mixedBrands;
  qs("#factor-loose").value    = cfg.factors.loosePiece;
  qs("#floor-set").value       = cfg.floors.set;
  qs("#floor-piece").value     = cfg.floors.piece;
  qs("#round-to").value        = cfg.roundTo;
}

function saveFactorFields() {
  const cfg = getConfig();
  cfg.factors.mixedBrands = Number(qs("#factor-mixed").value);
  cfg.factors.loosePiece  = Number(qs("#factor-loose").value);
  cfg.floors.set          = Number(qs("#floor-set").value);
  cfg.floors.piece        = Number(qs("#floor-piece").value);
  cfg.roundTo             = Number(qs("#round-to").value);
  cfg.factors.conditionThresholds = collectThresholds();
  saveConfig(cfg);
  showAlert("factors-alert", "Factores guardados.", "success");
}

// ─────────────────────────────────────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  renderBrandTable();
  renderThresholds();
  loadFactorFields();
  renderHistory();

  // Save brands button
  qs("#btn-save-brands").addEventListener("click", () => {
    const cfg = getConfig();
    const brands = collectBrandTable();
    if (!brands.length) {
      showAlert("brand-alert", "No hay marcas válidas para guardar.", "danger");
      return;
    }
    cfg.brands = brands;
    saveConfig(cfg);
    renderBrandTable();
    showAlert("brand-alert", "Marcas guardadas correctamente.", "success");
  });

  // Add brand row
  qs("#btn-add-brand").addEventListener("click", () => {
    const cfg = getConfig();
    cfg.brands.push({ id: "nueva_marca", name: "Nueva Marca", tier: 2, basePrice: 350 });
    saveConfig(cfg);
    renderBrandTable();
    // Scroll to last row
    qsa("#brand-tbody tr").at(-1)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    qsa("#brand-tbody tr").at(-1)?.querySelector("input")?.focus();
  });

  // Save factors
  qs("#btn-save-factors").addEventListener("click", saveFactorFields);

  // Add threshold row
  qs("#btn-add-threshold").addEventListener("click", () => {
    const cfg = getConfig();
    cfg.factors.conditionThresholds.push({ minScore: 0.0, factor: 0.60, label: "Muy deteriorado" });
    saveConfig(cfg);
    renderThresholds();
  });

  // Reset config
  qs("#btn-reset-config").addEventListener("click", () => {
    if (confirm("¿Restaurar la configuración por defecto? Se perderán todos los cambios.")) {
      localStorage.removeItem("scrubsConfig");
      renderBrandTable();
      renderThresholds();
      loadFactorFields();
      showAlert("factors-alert", "Configuración restaurada.", "success");
    }
  });

  // Export
  qs("#btn-export").addEventListener("click", exportConfig);

  // Import
  qs("#btn-import").addEventListener("click", () => qs("#import-file").click());
  qs("#import-file").addEventListener("change", e => {
    if (e.target.files[0]) importConfig(e.target.files[0]);
    e.target.value = "";
  });

  // Clear history
  qs("#btn-clear-admin-history").addEventListener("click", () => {
    if (confirm("¿Eliminar todo el historial de cotizaciones?")) {
      localStorage.removeItem("scrubsHistory");
      renderHistory();
    }
  });

  // Export history as CSV
  qs("#btn-export-history").addEventListener("click", () => {
    let history = [];
    try { history = JSON.parse(localStorage.getItem("scrubsHistory") || "[]"); } catch (_) {}
    if (!history.length) { alert("No hay historial."); return; }

    const rows = [
      ["Fecha", "Marca filipina", "Marca pantalón", "Tipo", "Condición", "Puntaje", "Precio MXN"],
      ...history.map(e => [
        new Date(e.ts).toLocaleString("es-MX"),
        e.topBrand || "",
        e.bottomBrand || "",
        e.isSet ? "Conjunto" : "Pieza suelta",
        e.conditionLabel || "",
        Number(e.avgScore).toFixed(1),
        e.price
      ])
    ];

    const csv  = rows.map(r => r.map(c => `"${c}"`).join(",")).join("\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const url  = URL.createObjectURL(blob);
    const a    = Object.assign(document.createElement("a"), {
      href: url, download: "historial-cotizaciones.csv"
    });
    a.click();
    URL.revokeObjectURL(url);
  });
});
