"""
Dixon-Coles model (1997) — correction for the independent Poisson model.

Dixon & Coles showed that the basic Poisson model systematically underestimates
the frequency of low-scoring matches (0-0, 1-0, 0-1, 1-1). Their fix introduces
a correlation parameter rho (ρ) that adjusts the joint probability of those
four score combinations.

Correction factor τ(x, y, λ, μ, ρ):
    (x=0, y=0): 1 - λ·μ·ρ
    (x=1, y=0): 1 + μ·ρ
    (x=0, y=1): 1 + λ·ρ
    (x=1, y=1): 1 - ρ
    otherwise : 1

Typical fitted value of ρ is around -0.10 to -0.13 for top European leagues.
A negative ρ means 0-0 and 1-1 draws are more likely than pure Poisson predicts.
"""

import math
from typing import Dict, Tuple

from .poisson import MatchProbabilities, _poisson_pmf


def _tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    if x == 0 and y == 0:
        return 1.0 - lam * mu * rho
    if x == 1 and y == 0:
        return 1.0 + mu * rho
    if x == 0 and y == 1:
        return 1.0 + lam * rho
    if x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


class DixonColesModel:
    """
    Dixon-Coles corrected Poisson model.

    Inherits the same attack/defense/advantage parametrization as PoissonModel
    but applies τ correction to (0-0), (1-0), (0-1), (1-1) scorelines.
    """

    HOME_ADVANTAGE = 1.35
    MAX_GOALS = 10

    def __init__(
        self,
        rho: float = -0.10,
        league_avg_home: float = 1.52,
        league_avg_away: float = 1.15,
        home_advantage: float = HOME_ADVANTAGE,
    ):
        self.rho = rho
        self.league_avg_home = league_avg_home
        self.league_avg_away = league_avg_away
        self.home_advantage = home_advantage

    def predict(
        self,
        home_attack: float,
        home_defense: float,
        away_attack: float,
        away_defense: float,
    ) -> MatchProbabilities:
        lam = home_attack * away_defense * self.home_advantage * self.league_avg_home
        mu = away_attack * home_defense * self.league_avg_away

        score_matrix: Dict[Tuple[int, int], float] = {}
        home_win = draw = away_win = 0.0

        for h in range(self.MAX_GOALS + 1):
            p_h = _poisson_pmf(h, lam)
            for a in range(self.MAX_GOALS + 1):
                p_a = _poisson_pmf(a, mu)
                correction = _tau(h, a, lam, mu, self.rho)
                p = p_h * p_a * correction
                score_matrix[(h, a)] = p
                if h > a:
                    home_win += p
                elif h == a:
                    draw += p
                else:
                    away_win += p

        # Normalize to account for floating-point drift from τ corrections
        total = home_win + draw + away_win
        return MatchProbabilities(
            home_win=home_win / total,
            draw=draw / total,
            away_win=away_win / total,
            expected_home_goals=lam,
            expected_away_goals=mu,
            score_matrix={k: v / total for k, v in score_matrix.items()},
        )
