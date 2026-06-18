#!/usr/bin/env python3
"""
Demo: Mathematical Football Prediction System
=============================================

Three models, one truth: in football the outcome is uncertain, but the
*probability* of each outcome can be quantified with precision.

Models used:
  1. Poisson          — goals follow a rare-event distribution
  2. Dixon-Coles      — Poisson + correction for low-scoring matches
  3. Elo              — relative team strength updated after every match

Run with:
    python demo.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from engine import PredictionEngine


def section(title: str) -> None:
    print(f"\n{'═' * 55}")
    print(f"  {title}")
    print(f"{'═' * 55}")


def main():
    section("SISTEMA DE PREDICCIÓN MATEMÁTICA DE FÚTBOL")
    print(
        "\n  Modelos: Poisson | Dixon-Coles | Elo Rating\n"
        "  Fuente de verdad: matemáticas puras, sin intuición.\n"
    )

    # ------------------------------------------------------------------
    # 1. Build engine from historical data
    # ------------------------------------------------------------------
    section("PASO 1 — Cargar datos históricos de la liga")
    engine = PredictionEngine()
    engine.train_elo()  # replay historical results to calibrate Elo
    print("  Datos cargados: 28 partidos de liga históricos.")
    print("  Elo calibrado con resultados reales.\n")

    # ------------------------------------------------------------------
    # 2. League table
    # ------------------------------------------------------------------
    section("PASO 2 — Tabla de posiciones (con rating Elo)")
    print()
    print(engine.league_table())

    # ------------------------------------------------------------------
    # 3. Match predictions
    # ------------------------------------------------------------------
    section("PASO 3 — Predicciones de partidos")

    fixtures = [
        ("Real Capital",    "Atletico Norte"),
        ("Tigres",          "Olimpia"),
        ("Deportivo Sur",   "Maritimo"),
        ("Union FC",        "Juventud"),
    ]

    for home, away in fixtures:
        print()
        report = engine.predict(home, away)
        print(report)

    # ------------------------------------------------------------------
    # 4. Math explainer
    # ------------------------------------------------------------------
    section("PASO 4 — Por qué funciona la matemática")
    print("""
  ┌─ POISSON ──────────────────────────────────────────────┐
  │  P(k goles) = (λ^k · e^-λ) / k!                       │
  │  λ = fuerza_ataque × debilidad_defensa × ventaja_local │
  │  Se suma sobre todas las combinaciones (0-0 a 10-10)   │
  └────────────────────────────────────────────────────────┘

  ┌─ DIXON-COLES ───────────────────────────────────────────┐
  │  Corrección τ(x,y) para marcadores bajos (0-0, 1-0,    │
  │  0-1, 1-1). Parámetro ρ ≈ -0.10 (fitted en la liga).   │
  │  El Poisson puro subestima empates de bajo marcador.    │
  └─────────────────────────────────────────────────────────┘

  ┌─ ELO ───────────────────────────────────────────────────┐
  │  E_A = 1 / (1 + 10^((R_B - R_A) / 400))                │
  │  R_new = R_old + K · (S - E)                            │
  │  Ventaja local = +100 pts al equipo de casa.            │
  │  K escala con diferencia de goles: partidos abultados   │
  │  transfieren más rating que victorias mínimas.          │
  └─────────────────────────────────────────────────────────┘

  CONSENSO: promedio simple de los tres modelos.
  La convergencia entre modelos independientes aumenta
  la confianza en la predicción.
""")

    # ------------------------------------------------------------------
    # 5. Value bet detector (Kelly Criterion concept)
    # ------------------------------------------------------------------
    section("PASO 5 — Detector de valor matemático (Kelly Criterion)")
    print("""
  Si un modelo dice P(home win) = 60% pero las cuotas del
  mercado implican solo 50%, existe VALOR matemático.

  Cuota justa = 1 / P
  Cuota de mercado > cuota justa → apuesta con valor positivo

  Kelly fraction = (b·p - q) / b
    b = cuota decimal - 1
    p = probabilidad del modelo
    q = 1 - p

  Ejemplo: P=0.60, cuota mercado=2.10
    b = 1.10, p = 0.60, q = 0.40
    Kelly = (1.10 × 0.60 - 0.40) / 1.10 = 0.236
    → Apostar 23.6% del bankroll (fracción completa, muy agresivo)
    → En práctica se usa ¼ Kelly = 5.9% (gestión de riesgo)
  """)

    section("FIN DE LA DEMOSTRACIÓN")
    print("  El sistema está listo. Para predecir tu propio partido:")
    print("  engine.predict('Equipo Local', 'Equipo Visitante')\n")


if __name__ == "__main__":
    main()
