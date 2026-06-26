// Default configuration — overridden by localStorage when admin edits are saved.
// Edit brands, factors, and floors from the admin panel without touching this file.
const DEFAULT_CONFIG = {
  version: "1.0.0",
  brands: [
    // ── Tier 1 · Premium ──────────────────────────────────────────────────────
    // FIGS: ~$100-130 USD/conjunto → ~1 700-2 200 MXN new
    { id: "figs",             name: "FIGS",                 tier: 1, basePrice: 850 },
    // Medelita: ~$130-160 USD/conjunto → ~2 200-2 700 MXN new
    { id: "medelita",         name: "Medelita",             tier: 1, basePrice: 820 },
    // Jaanuu: ~$100-120 USD/conjunto → ~1 700-2 000 MXN new
    { id: "jaanuu",           name: "Jaanuu",               tier: 1, basePrice: 780 },
    // Mandala: marca mexicana premium ~1 300-1 600 MXN new
    { id: "mandala",          name: "Mandala",              tier: 1, basePrice: 750 },
    // Barco One: ~$70-90 USD/conjunto → ~1 200-1 550 MXN new
    { id: "barco_one",        name: "Barco One",            tier: 1, basePrice: 740 },
    // Koi: ~$55-75 USD/conjunto → ~940-1 280 MXN new
    { id: "koi",              name: "Koi",                  tier: 1, basePrice: 720 },
    // Healing Hands: ~$50-70 USD/conjunto → ~850-1 200 MXN new
    { id: "healing_hands",    name: "Healing Hands",        tier: 1, basePrice: 710 },
    // Iguanamed: ~$50-70 USD/conjunto → ~850-1 200 MXN new
    { id: "iguanamed",        name: "Iguanamed",            tier: 1, basePrice: 700 },

    // ── Tier 2 · Intermedio ───────────────────────────────────────────────────
    // Grey's Anatomy (Barco): ~$60-100 USD/conjunto → ~1 020-1 700 MXN new
    { id: "greys_anatomy",    name: "Grey's Anatomy",       tier: 2, basePrice: 400 },
    // Cherokee: ~$50-80 USD/conjunto → ~850-1 360 MXN new
    { id: "cherokee",         name: "Cherokee",             tier: 2, basePrice: 380 },
    // Dickies Medical: ~$50-80 USD/conjunto → ~850-1 360 MXN new
    { id: "dickies",          name: "Dickies Medical",      tier: 2, basePrice: 380 },
    // Med Couture: ~$55-80 USD/conjunto → ~940-1 360 MXN new
    { id: "med_couture",      name: "Med Couture",          tier: 2, basePrice: 370 },
    // Carhartt Scrubs: ~$55-75 USD/conjunto → ~940-1 280 MXN new
    { id: "carhartt",         name: "Carhartt Scrubs",      tier: 2, basePrice: 370 },
    // Wonder Wink: ~$45-65 USD/conjunto → ~770-1 100 MXN new
    { id: "wonder_wink",      name: "Wonder Wink",          tier: 2, basePrice: 360 },
    // Butter Soft: ~$40-60 USD/conjunto → ~680-1 020 MXN new
    { id: "butter_soft",      name: "Butter Soft",          tier: 2, basePrice: 350 },
    // Scrubstar: ~$30-50 USD/conjunto → ~510-850 MXN new
    { id: "scrubstar",        name: "Scrubstar",            tier: 2, basePrice: 320 },

    // ── Tier 3 · Básico ───────────────────────────────────────────────────────
    // Landau: ~$30-45 USD/conjunto → ~510-770 MXN new
    { id: "landau",           name: "Landau",               tier: 3, basePrice: 310 },
    // Natural Uniforms: ~$25-40 USD/conjunto → ~430-680 MXN new
    { id: "natural_uniforms", name: "Natural Uniforms",     tier: 3, basePrice: 300 },
    // Panda Uniform: marca mexicana básica ~400-500 MXN new
    { id: "panda",            name: "Panda Uniform",        tier: 3, basePrice: 290 },
    // ProScrub: marca mexicana básica ~380-480 MXN new
    { id: "proscrub",         name: "ProScrub",             tier: 3, basePrice: 280 },
    // Sin marca / Genérico
    { id: "generic",          name: "Sin marca / Genérico", tier: 3, basePrice: 280 },
  ],

  factors: {
    // FM — descuento cuando las marcas no coinciden
    mixedBrands: 0.90,
    // FS — factor para pieza suelta (no es conjunto completo)
    loosePiece: 0.65,
    // FC — tabla de condición: el primer umbral que se cumpla aplica
    conditionThresholds: [
      { minScore: 3.5, factor: 1.00, label: "Excelente"   },
      { minScore: 3.0, factor: 0.95, label: "Muy bueno"   },
      { minScore: 2.5, factor: 0.88, label: "Bueno"       },
      { minScore: 2.0, factor: 0.80, label: "Regular"     },
      { minScore: 0.0, factor: 0.70, label: "Deteriorado" }
    ]
  },

  floors: {
    // Precio mínimo para conjunto completo
    set:   280,
    // Precio mínimo para pieza suelta
    piece: 160
  },

  // Redondeo al múltiplo más cercano
  roundTo: 10
};
