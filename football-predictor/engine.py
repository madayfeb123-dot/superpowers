"""
Prediction Engine — ties together Poisson, Dixon-Coles, and Elo models.

Usage:
    engine = PredictionEngine(stats, league_avg_home, league_avg_away)
    result = engine.predict("Real Capital", "Tigres")
    print(result)
"""

from dataclasses import dataclass
from typing import Optional

from data.sample_league import TeamStats, compute_stats, league_averages
from models.dixon_coles import DixonColesModel
from models.elo import EloRating, EloResult
from models.poisson import MatchProbabilities, PoissonModel


@dataclass
class PredictionReport:
    home_team: str
    away_team: str
    poisson: MatchProbabilities
    dixon_coles: MatchProbabilities
    elo: EloResult

    def __str__(self) -> str:
        sep = "─" * 55
        lines = [
            sep,
            f"  MATCH PREDICTION: {self.home_team}  vs  {self.away_team}",
            sep,
            "",
            "[ 1 ] Poisson Model (independent goals)",
            str(self.poisson),
            "",
            "[ 2 ] Dixon-Coles Model (low-score correction, ρ = -0.10)",
            str(self.dixon_coles),
            "",
            "[ 3 ] Elo Rating",
            str(self.elo),
            "",
            "[ CONSENSUS ]",
            _consensus_line(self.poisson, self.dixon_coles, self.elo),
            sep,
        ]
        return "\n".join(lines)


def _consensus_line(
    p: MatchProbabilities, dc: MatchProbabilities, elo: EloResult
) -> str:
    hw = (p.home_win + dc.home_win + elo.home_win_prob) / 3
    d = (p.draw + dc.draw + elo.draw_prob) / 3
    aw = (p.away_win + dc.away_win + elo.away_win_prob) / 3
    outcomes = {"Home Win": hw, "Draw": d, "Away Win": aw}
    best = max(outcomes, key=outcomes.get)
    return (
        f"Avg Home Win: {hw*100:.1f}%  |  Avg Draw: {d*100:.1f}%  "
        f"|  Avg Away Win: {aw*100:.1f}%\n"
        f"→ Most likely outcome: {best} ({outcomes[best]*100:.1f}%)"
    )


class PredictionEngine:
    def __init__(
        self,
        stats: Optional[dict] = None,
        league_avg_home: float = 1.52,
        league_avg_away: float = 1.15,
        elo_ratings: Optional[dict] = None,
    ):
        if stats is None:
            stats = compute_stats()
            league_avg_home, league_avg_away = league_averages(stats)

        self._stats = stats
        self._poisson = PoissonModel(league_avg_home, league_avg_away)
        self._dc = DixonColesModel(
            rho=-0.10,
            league_avg_home=league_avg_home,
            league_avg_away=league_avg_away,
        )
        self._elo = EloRating()

        # Seed Elo from initial ratings or defaults
        for name in stats:
            initial = elo_ratings.get(name, 1500.0) if elo_ratings else 1500.0
            self._elo.add_team(name, initial)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _league_avg_scored(self) -> float:
        all_stats = list(self._stats.values())
        total = sum(s.goals_scored for s in all_stats)
        played = sum(s.played for s in all_stats)
        return total / played if played else 1.0

    def _league_avg_conceded(self) -> float:
        return self._league_avg_scored()  # symmetrical by definition

    def _indices(self, team: str) -> tuple:
        """Returns (attack_index, defense_index) relative to league average."""
        s: TeamStats = self._stats[team]
        avg = self._league_avg_scored()
        attack = s.avg_scored / avg if avg else 1.0
        defense = s.avg_conceded / avg if avg else 1.0
        return attack, defense

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def train_elo(self) -> None:
        """Replay historical results to calibrate Elo ratings."""
        from data.sample_league import SEASON_RESULTS

        for home, away, hg, ag in SEASON_RESULTS:
            if hg > ag:
                result = "home"
            elif hg == ag:
                result = "draw"
            else:
                result = "away"
            self._elo.update(home, away, result, goal_diff=abs(hg - ag))

    def predict(self, home_team: str, away_team: str) -> PredictionReport:
        ha, hd = self._indices(home_team)
        aa, ad = self._indices(away_team)

        p_result = self._poisson.predict(ha, hd, aa, ad)
        dc_result = self._dc.predict(ha, hd, aa, ad)
        elo_result = self._elo.predict(home_team, away_team)

        return PredictionReport(
            home_team=home_team,
            away_team=away_team,
            poisson=p_result,
            dixon_coles=dc_result,
            elo=elo_result,
        )

    def league_table(self) -> str:
        rows = sorted(
            self._stats.values(),
            key=lambda s: (s.points, s.goals_scored - s.goals_conceded),
            reverse=True,
        )
        header = f"{'#':>2}  {'Team':<18} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>4} {'GA':>4} {'GD':>4} {'Pts':>4} {'Elo':>6}"
        sep = "─" * len(header)
        lines = [sep, header, sep]
        for i, s in enumerate(rows, 1):
            gd = s.goals_scored - s.goals_conceded
            elo_r = self._elo.rating(s.name)
            lines.append(
                f"{i:>2}  {s.name:<18} {s.played:>3} {s.wins:>3} "
                f"{s.draws:>3} {s.losses:>3} {s.goals_scored:>4} "
                f"{s.goals_conceded:>4} {gd:>+4} {s.points:>4} {elo_r:>6.0f}"
            )
        lines.append(sep)
        return "\n".join(lines)
