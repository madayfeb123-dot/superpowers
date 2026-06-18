#!/usr/bin/env python3
"""
Complemento para mundial-agent MCP.

Qué añade este archivo:
  - Dixon-Coles: corrección τ para marcadores bajos (0-0, 1-0, 0-1, 1-1)
  - modelo_consenso: promedio ponderado de todos los modelos
  - Herramienta MCP: marcador_mas_probable (top-5 scorelines)
  - Herramienta MCP: estadisticas_bankroll (ROI, racha, tasa acierto)

Integración en tu archivo principal:
  1. Pega las dos funciones (dixon_coles_probabilidades, modelo_consenso)
     junto a las demás funciones de modelo.
  2. En analizar_partido, añade los elif para modelo 4 y 5.
  3. Pega los dos @server.tool() antes del bloque if __name__ == "__main__".
"""

import json
import math
from scipy.stats import poisson

# ──────────────────────────────────────────────────────────────────────────────
# 1. FUNCIÓN DIXON-COLES  →  añadir junto a modelo_ataque_defensa
# ──────────────────────────────────────────────────────────────────────────────
#
# Dixon & Coles (1997) probaron que el Poisson independiente subestima
# sistemáticamente los marcadores bajos. La corrección introduce el factor τ:
#
#   τ(0,0) = 1 − λ·μ·ρ
#   τ(1,0) = 1 + μ·ρ
#   τ(0,1) = 1 + λ·ρ
#   τ(1,1) = 1 − ρ
#   τ(x,y) = 1   para el resto
#
# ρ ≈ −0.10 (negativo → más empates de bajo marcador de lo que Poisson predice)

MEDIA_GOLES = 1.4   # mismo valor que en el archivo principal
MAX_GOLES   = 10


def _tau(x, y, lam, mu, rho=-0.10):
    if x == 0 and y == 0: return 1.0 - lam * mu * rho
    if x == 1 and y == 0: return 1.0 + mu * rho
    if x == 0 and y == 1: return 1.0 + lam * rho
    if x == 1 and y == 1: return 1.0 - rho
    return 1.0


def dixon_coles_probabilidades(lambda_local, lambda_visit, rho=-0.10, max_g=MAX_GOLES):
    """
    Calcula P(local, empate, visitante) y la matriz completa de marcadores
    usando la corrección Dixon-Coles.

    Retorna:
        p_local, p_empate, p_visit  — probabilidades de resultado
        matrix                      — dict {"h-a": probabilidad} para cada marcador
    """
    matrix = {}
    p_local = p_empate = p_visit = total = 0.0

    for h in range(max_g):
        ph = poisson.pmf(h, lambda_local)
        for a in range(max_g):
            p = ph * poisson.pmf(a, lambda_visit) * _tau(h, a, lambda_local, lambda_visit, rho)
            matrix[f"{h}-{a}"] = p
            total += p
            if   h > a: p_local += p
            elif h == a: p_empate += p
            else:        p_visit += p

    return p_local / total, p_empate / total, p_visit / total, \
           {k: v / total for k, v in matrix.items()}


# ──────────────────────────────────────────────────────────────────────────────
# 2. MODELO CONSENSO  →  añadir junto a las demás funciones de modelo
# ──────────────────────────────────────────────────────────────────────────────
#
# El consenso promedia cuatro modelos con pesos distintos:
#   - Elo-Poisson      30 %
#   - Ataque/Defensa   35 %
#   - Dixon-Coles      35 %
# (las cuotas implícitas se omiten porque contienen el margen de la casa)
#
# La convergencia entre modelos independientes aumenta la confianza;
# la divergencia indica incertidumbre alta → reducir tamaño de apuesta.

def modelo_consenso(elo_loc, elo_vis, atq_loc, def_loc, atq_vis, def_vis,
                    ventaja=100, factor_elo=0.004):
    """Promedio ponderado de Elo-Poisson, Ataque/Defensa y Dixon-Coles."""
    import numpy as np

    # Modelo 1: Elo-Poisson
    elo_adj = elo_loc + ventaja
    lam1 = MEDIA_GOLES * np.exp(factor_elo * (elo_adj - elo_vis) / 2)
    mu1  = MEDIA_GOLES * np.exp(factor_elo * (elo_vis - elo_adj) / 2)
    p1_l, p1_e, p1_v = _poisson_prob(lam1, mu1)

    # Modelo 2: Ataque/Defensa
    lam2 = MEDIA_GOLES * atq_loc * def_vis
    mu2  = MEDIA_GOLES * atq_vis * def_loc
    p2_l, p2_e, p2_v = _poisson_prob(lam2, mu2)

    # Modelo 4: Dixon-Coles (usando lambdas del modelo 2)
    p4_l, p4_e, p4_v, _ = dixon_coles_probabilidades(lam2, mu2)

    W = [0.30, 0.35, 0.35]
    p_l = W[0]*p1_l + W[1]*p2_l + W[2]*p4_l
    p_e = W[0]*p1_e + W[1]*p2_e + W[2]*p4_e
    p_v = W[0]*p1_v + W[1]*p2_v + W[2]*p4_v

    # Divergencia: desviación estándar entre los tres modelos (indicador de riesgo)
    import statistics
    divergencia = statistics.stdev([p1_l, p2_l, p4_l])
    return p_l, p_e, p_v, divergencia


def _poisson_prob(lam, mu, max_g=MAX_GOLES):
    """Poisson puro — función interna auxiliar."""
    pl = pe = pv = 0.0
    for h in range(max_g):
        ph = poisson.pmf(h, lam)
        for a in range(max_g):
            p = ph * poisson.pmf(a, mu)
            if h > a: pl += p
            elif h == a: pe += p
            else: pv += p
    t = pl + pe + pv
    return pl/t, pe/t, pv/t


# ──────────────────────────────────────────────────────────────────────────────
# 3. EXTENSIÓN DE analizar_partido  →  añadir los elif dentro de la función
# ──────────────────────────────────────────────────────────────────────────────
#
# Dentro del if/elif que selecciona modelo, añade:
#
#     elif modelo == 4:
#         lam = MEDIA_GOLES * atq_loc * def_vis
#         mu  = MEDIA_GOLES * atq_vis * def_loc
#         p_l, p_e, p_v, _ = dixon_coles_probabilidades(lam, mu)
#         nombre_modelo = "Dixon-Coles"
#
#     elif modelo == 5:
#         p_l, p_e, p_v, div = modelo_consenso(
#             elo_loc, elo_vis, atq_loc, def_loc, atq_vis, def_vis)
#         nombre_modelo = f"Consenso (divergencia={div:.3f})"
#
# Actualiza también el docstring de analizar_partido:
#     modelo: 1 (Elo-Poisson), 2 (Ataque/Defensa), 3 (Cuotas implícitas),
#             4 (Dixon-Coles), 5 (Consenso ponderado)


# ──────────────────────────────────────────────────────────────────────────────
# 4. NUEVA HERRAMIENTA MCP: marcador_mas_probable
# ──────────────────────────────────────────────────────────────────────────────
#
# Pega este @server.tool() en tu archivo principal antes de if __name__...

"""
@server.tool()
async def marcador_mas_probable(equipo_local: str, equipo_visitante: str,
                                top_n: int = 5) -> str:
    \"\"\"
    Devuelve los N marcadores más probables usando Dixon-Coles.
    Incluye goles esperados (lambda) y si el marcador favorece al local, empate o visitante.
    \"\"\"
    datos_loc = EQUIPOS_RATINGS.get(equipo_local, (1500, 1.0, 1.0))
    datos_vis = EQUIPOS_RATINGS.get(equipo_visitante, (1500, 1.0, 1.0))
    _, atq_loc, def_loc = datos_loc
    _, atq_vis, def_vis = datos_vis

    lam = MEDIA_GOLES * atq_loc * def_vis
    mu  = MEDIA_GOLES * atq_vis * def_loc

    p_l, p_e, p_v, matrix = dixon_coles_probabilidades(lam, mu)

    top = sorted(matrix.items(), key=lambda x: x[1], reverse=True)[:top_n]

    marcadores = []
    for marcador, prob in top:
        gl, ga = map(int, marcador.split("-"))
        tipo = "local" if gl > ga else ("empate" if gl == ga else "visitante")
        marcadores.append({
            "marcador": f"{equipo_local} {gl} - {ga} {equipo_visitante}",
            "probabilidad": f"{prob*100:.2f}%",
            "tipo": tipo,
        })

    return json.dumps({
        "partido": f"{equipo_local} vs {equipo_visitante}",
        "modelo": "Dixon-Coles",
        "goles_esperados": {
            equipo_local: round(lam, 2),
            equipo_visitante: round(mu, 2),
        },
        "probabilidades_resultado": {
            "local":     f"{p_l*100:.1f}%",
            "empate":    f"{p_e*100:.1f}%",
            "visitante": f"{p_v*100:.1f}%",
        },
        "top_marcadores": marcadores,
    }, ensure_ascii=False, indent=2)
"""


# ──────────────────────────────────────────────────────────────────────────────
# 5. NUEVA HERRAMIENTA MCP: estadisticas_bankroll
# ──────────────────────────────────────────────────────────────────────────────
#
# Pega este @server.tool() en tu archivo principal antes de if __name__...

"""
@server.tool()
async def estadisticas_bankroll() -> str:
    \"\"\"
    Estadísticas completas de gestión de banca:
    ROI, tasa de acierto, racha actual, mejor/peor apuesta.
    \"\"\"
    estado = cargar_estado()
    h = estado["historial"]

    if not h:
        return json.dumps({"bankroll": estado["bankroll"], "historial": "vacío"})

    total_invertido  = sum(e["monto"] for e in h)
    total_beneficio  = sum(e["beneficio"] for e in h)
    ganadas  = sum(1 for e in h if e["beneficio"] > 0)
    perdidas = sum(1 for e in h if e["beneficio"] <= 0)
    roi = (total_beneficio / total_invertido * 100) if total_invertido else 0

    # Racha actual (desde el final del historial hacia atrás)
    racha, tipo_racha = 0, None
    for e in reversed(h):
        tipo = "ganada" if e["beneficio"] > 0 else "perdida"
        if tipo_racha is None:
            tipo_racha, racha = tipo, 1
        elif tipo == tipo_racha:
            racha += 1
        else:
            break

    mejor  = max(h, key=lambda e: e["beneficio"])
    peor   = min(h, key=lambda e: e["beneficio"])

    return json.dumps({
        "bankroll_actual":   round(estado["bankroll"], 2),
        "bankroll_inicial":  1000.0,
        "beneficio_total":   round(total_beneficio, 2),
        "total_apostado":    round(total_invertido, 2),
        "roi":               f"{roi:.2f}%",
        "apuestas_totales":  len(h),
        "ganadas":           ganadas,
        "perdidas":          perdidas,
        "tasa_acierto":      f"{ganadas / len(h) * 100:.1f}%",
        "racha_actual":      f"{racha} {tipo_racha}s consecutivas",
        "mejor_apuesta":     {"partido": mejor["partido"], "beneficio": mejor["beneficio"]},
        "peor_apuesta":      {"partido": peor["partido"],  "beneficio": peor["beneficio"]},
    }, ensure_ascii=False, indent=2)
"""


if __name__ == "__main__":
    # Test rápido de las funciones nuevas sin necesidad de MCP
    print("=== TEST dixon_coles_probabilidades ===")
    p_l, p_e, p_v, matrix = dixon_coles_probabilidades(2.1, 0.9)
    top5 = sorted(matrix.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"  Local: {p_l:.1%}  Empate: {p_e:.1%}  Visitante: {p_v:.1%}")
    print("  Top-5 marcadores:")
    for k, v in top5:
        print(f"    {k}: {v:.2%}")

    print("\n=== TEST modelo_consenso ===")
    # Argentina (Elo 1900, 2.2 atq, 1.0 def) vs México (1750, 1.4 atq, 1.3 def)
    pl, pe, pv, div = modelo_consenso(1900, 1750, 2.2, 1.0, 1.4, 1.3)
    print(f"  Local: {pl:.1%}  Empate: {pe:.1%}  Visitante: {pv:.1%}")
    print(f"  Divergencia entre modelos: {div:.4f} {'(alta → cuidado)' if div > 0.05 else '(baja → confianza alta)'}")
