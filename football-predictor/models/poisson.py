"""
Poisson Model for football score prediction.

Goals in a match follow a Poisson distribution: a rare, independent event
with a known average rate. The key insight is that a team's expected goals
(lambda) can be decomposed into attack strength, opponent defense weakness,
and home/away advantage — all derived from historical data.

P(X = k) = (lambda^k * e^(-lambda)) / k!

Match outcome probabilities are derived by summing over all (home, away)
scoreline combinations up to a realistic ceiling (e.g. 10 goals per side).
"""

import math
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class MatchProbabilities:
    home_win: float
    draw: float
    away_win: float
    expected_home_goals: float
    expected_away_goals: float
    score_matrix: Dict[Tuple[int, int], float]

    def most_likely_score(self) -> Tuple[int, int]:
        return max(self.score_matrix, key=self.score_matrix.get)

    def __str__(self) -> str:
        h, d, a = self.home_win * 100, self.draw * 100, self.away_win * 100
        best = self.most_likely_score()
        return (
            f"Home Win: {h:.1f}%  |  Draw: {d:.1f}%  |  Away Win: {a:.1f}%\n"
            f"Expected: {self.expected_home_goals:.2f} - {self.expected_away_goals:.2f}\n"
            f"Most likely score: {best[0]}-{best[1]} "
            f"({self.score_matrix[best]*100:.1f}%)"
        )


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


class PoissonModel:
    """
    Independent Poisson model.

    Assumes home and away goals are independent. Each team's lambda is:
        lambda_home = home_attack * away_defense * home_advantage * league_avg_goals_home
        lambda_away = away_attack * home_defense * league_avg_goals_away

    Attack and defense indices are relative to the league average (= 1.0).
    """

    # Typical home advantage in top leagues: ~1.35 extra goals rate at home
    HOME_ADVANTAGE = 1.35
    MAX_GOALS = 10  # ceiling for score matrix; P(X > 10) is negligible

    def __init__(
        self,
        league_avg_home: float = 1.52,
        league_avg_away: float = 1.15,
        home_advantage: float = HOME_ADVANTAGE,
    ):
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
        """
        Parameters
        ----------
        home_attack   : home team attack index   (goals_scored / league_avg)
        home_defense  : home team defense index  (goals_conceded / league_avg)
        away_attack   : away team attack index
        away_defense  : away team defense index
        """
        lambda_home = (
            home_attack * away_defense * self.home_advantage * self.league_avg_home
        )
        lambda_away = away_attack * home_defense * self.league_avg_away

        score_matrix: Dict[Tuple[int, int], float] = {}
        home_win = draw = away_win = 0.0

        for h in range(self.MAX_GOALS + 1):
            p_h = _poisson_pmf(h, lambda_home)
            for a in range(self.MAX_GOALS + 1):
                p_a = _poisson_pmf(a, lambda_away)
                p = p_h * p_a
                score_matrix[(h, a)] = p
                if h > a:
                    home_win += p
                elif h == a:
                    draw += p
                else:
                    away_win += p

        return MatchProbabilities(
            home_win=home_win,
            draw=draw,
            away_win=away_win,
            expected_home_goals=lambda_home,
            expected_away_goals=lambda_away,
            score_matrix=score_matrix,
        )
