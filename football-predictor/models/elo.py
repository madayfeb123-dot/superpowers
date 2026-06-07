"""
Elo Rating System adapted for football.

Originally developed for chess by Arpad Elo (1960). The key idea: every team
has a numerical strength rating. After each match, points transfer between
teams — more points transfer when the result is an upset.

Expected score formula (same as chess):
    E_A = 1 / (1 + 10^((R_B - R_A) / 400))

Rating update:
    R_A_new = R_A + K * (S_A - E_A)

Where:
    K   = sensitivity constant (20 is common for club football)
    S_A = 1.0 (win), 0.5 (draw), 0.0 (loss)

Football adaptations vs chess:
    - Home advantage is modeled by adding a bonus (typically +100) to the
      home team's effective rating before computing E.
    - Draws are a real outcome and carry S = 0.5.
    - K can be scaled by goal difference to capture margin of victory.
"""

from dataclasses import dataclass, field
from typing import Dict, Literal, Optional, Tuple


@dataclass
class EloResult:
    home_team: str
    away_team: str
    home_rating_before: float
    away_rating_before: float
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    home_rating_after: Optional[float] = None
    away_rating_after: Optional[float] = None

    def __str__(self) -> str:
        lines = [
            f"{self.home_team} (Elo {self.home_rating_before:.0f})  vs  "
            f"{self.away_team} (Elo {self.away_rating_before:.0f})",
            f"Home Win: {self.home_win_prob*100:.1f}%  |  "
            f"Draw: {self.draw_prob*100:.1f}%  |  "
            f"Away Win: {self.away_win_prob*100:.1f}%",
        ]
        if self.home_rating_after is not None:
            lines.append(
                f"After match → {self.home_team}: {self.home_rating_after:.0f}  "
                f"{self.away_team}: {self.away_rating_after:.0f}"
            )
        return "\n".join(lines)


class EloRating:
    """
    Maintains an Elo rating table for a set of teams and provides:
        - win/draw/loss probability estimates
        - rating updates after match results
    """

    DEFAULT_RATING = 1500.0
    K = 20.0
    HOME_BONUS = 100.0  # effective rating added to home team's raw rating
    DRAW_BAND = 0.12    # fraction of [0,1] assigned to draw probability

    def __init__(
        self,
        k: float = K,
        home_bonus: float = HOME_BONUS,
        draw_band: float = DRAW_BAND,
    ):
        self.k = k
        self.home_bonus = home_bonus
        self.draw_band = draw_band
        self._ratings: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Team management
    # ------------------------------------------------------------------

    def add_team(self, name: str, initial_rating: float = DEFAULT_RATING) -> None:
        self._ratings[name] = initial_rating

    def rating(self, team: str) -> float:
        return self._ratings.get(team, self.DEFAULT_RATING)

    def standings(self) -> list:
        return sorted(self._ratings.items(), key=lambda x: x[1], reverse=True)

    # ------------------------------------------------------------------
    # Core math
    # ------------------------------------------------------------------

    def _expected_score(self, r_a: float, r_b: float) -> float:
        return 1.0 / (1.0 + 10.0 ** ((r_b - r_a) / 400.0))

    def _outcome_probabilities(
        self, home_team: str, away_team: str
    ) -> Tuple[float, float, float]:
        """Returns (P_home_win, P_draw, P_away_win)."""
        r_home = self.rating(home_team) + self.home_bonus
        r_away = self.rating(away_team)
        e_home = self._expected_score(r_home, r_away)

        # Draw band: a symmetric slice around the 0.5 equilibrium
        half_band = self.draw_band / 2.0
        draw = self.draw_band
        home_win = max(0.0, e_home - half_band)
        away_win = max(0.0, 1.0 - e_home - half_band)

        # Redistribute any clipped probability into draw to keep sum = 1
        total = home_win + draw + away_win
        return home_win / total, draw / total, away_win / total

    # ------------------------------------------------------------------
    # Prediction (no rating change)
    # ------------------------------------------------------------------

    def predict(self, home_team: str, away_team: str) -> EloResult:
        hw, d, aw = self._outcome_probabilities(home_team, away_team)
        return EloResult(
            home_team=home_team,
            away_team=away_team,
            home_rating_before=self.rating(home_team),
            away_rating_before=self.rating(away_team),
            home_win_prob=hw,
            draw_prob=d,
            away_win_prob=aw,
        )

    # ------------------------------------------------------------------
    # Update after a known result
    # ------------------------------------------------------------------

    def update(
        self,
        home_team: str,
        away_team: str,
        result: Literal["home", "draw", "away"],
        goal_diff: int = 0,
    ) -> EloResult:
        """
        Update ratings after a match.

        goal_diff is the absolute goal difference, used to scale K:
            multiplier = 1 + log(1 + goal_diff) * 0.5
        This means a 3-0 win shifts more rating than a 1-0 win.
        """
        r_h_before = self.rating(home_team)
        r_a_before = self.rating(away_team)

        r_h_eff = r_h_before + self.home_bonus
        e_home = self._expected_score(r_h_eff, r_a_before)

        score_map = {"home": (1.0, 0.0), "draw": (0.5, 0.5), "away": (0.0, 1.0)}
        s_home, s_away = score_map[result]

        import math
        k_scaled = self.k * (1.0 + math.log1p(goal_diff) * 0.5)

        r_h_new = r_h_before + k_scaled * (s_home - e_home)
        r_a_new = r_a_before + k_scaled * (s_away - (1.0 - e_home))

        self._ratings[home_team] = r_h_new
        self._ratings[away_team] = r_a_new

        hw2, d2, aw2 = self._compute_probs_from_ratings(r_h_before, r_a_before)

        return EloResult(
            home_team=home_team,
            away_team=away_team,
            home_rating_before=r_h_before,
            away_rating_before=r_a_before,
            home_win_prob=hw2,
            draw_prob=d2,
            away_win_prob=aw2,
            home_rating_after=r_h_new,
            away_rating_after=r_a_new,
        )

    def _compute_probs_from_ratings(
        self, r_home_raw: float, r_away: float
    ) -> Tuple[float, float, float]:
        r_home_eff = r_home_raw + self.home_bonus
        e_home = self._expected_score(r_home_eff, r_away)
        half_band = self.draw_band / 2.0
        draw = self.draw_band
        home_win = max(0.0, e_home - half_band)
        away_win = max(0.0, 1.0 - e_home - half_band)
        total = home_win + draw + away_win
        return home_win / total, draw / total, away_win / total
