"""
Sample season data for a fictional league of 8 teams.

Each entry in SEASON_RESULTS: (home_team, away_team, home_goals, away_goals)
TEAM_STATS: pre-computed season totals used to derive attack/defense indices.
"""

from dataclasses import dataclass
from typing import List, Tuple

# fmt: off
SEASON_RESULTS: List[Tuple[str, str, int, int]] = [
    ("Atletico Norte",  "Deportivo Sur",   2, 1),
    ("Real Capital",    "Union FC",        3, 0),
    ("Olimpia",         "Tigres",          1, 1),
    ("Juventud",        "Maritimo",        2, 2),
    ("Deportivo Sur",   "Real Capital",    0, 2),
    ("Union FC",        "Olimpia",         1, 2),
    ("Tigres",          "Atletico Norte",  3, 2),
    ("Maritimo",        "Juventud",        1, 0),
    ("Atletico Norte",  "Real Capital",    1, 3),
    ("Deportivo Sur",   "Olimpia",         2, 0),
    ("Union FC",        "Tigres",          0, 1),
    ("Juventud",        "Atletico Norte",  2, 1),
    ("Real Capital",    "Olimpia",         2, 1),
    ("Tigres",          "Maritimo",        4, 1),
    ("Atletico Norte",  "Union FC",        3, 1),
    ("Deportivo Sur",   "Juventud",        1, 2),
    ("Olimpia",         "Maritimo",        0, 0),
    ("Real Capital",    "Tigres",          2, 2),
    ("Union FC",        "Deportivo Sur",   2, 1),
    ("Maritimo",        "Atletico Norte",  0, 1),
    ("Juventud",        "Real Capital",    1, 2),
    ("Tigres",          "Deportivo Sur",   3, 0),
    ("Atletico Norte",  "Olimpia",         2, 0),
    ("Maritimo",        "Union FC",        1, 1),
    ("Deportivo Sur",   "Tigres",          1, 2),
    ("Olimpia",         "Juventud",        1, 1),
    ("Real Capital",    "Maritimo",        3, 1),
    ("Union FC",        "Atletico Norte",  0, 2),
]
# fmt: on

TEAMS = [
    "Atletico Norte",
    "Real Capital",
    "Olimpia",
    "Tigres",
    "Juventud",
    "Deportivo Sur",
    "Union FC",
    "Maritimo",
]


@dataclass
class TeamStats:
    name: str
    played: int = 0
    goals_scored: int = 0
    goals_conceded: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def avg_scored(self) -> float:
        return self.goals_scored / self.played if self.played else 0.0

    @property
    def avg_conceded(self) -> float:
        return self.goals_conceded / self.played if self.played else 0.0


def compute_stats() -> dict:
    stats = {t: TeamStats(name=t) for t in TEAMS}
    for home, away, hg, ag in SEASON_RESULTS:
        stats[home].played += 1
        stats[away].played += 1
        stats[home].goals_scored += hg
        stats[away].goals_scored += ag
        stats[home].goals_conceded += ag
        stats[away].goals_conceded += hg
        if hg > ag:
            stats[home].wins += 1
            stats[away].losses += 1
        elif hg == ag:
            stats[home].draws += 1
            stats[away].draws += 1
        else:
            stats[away].wins += 1
            stats[home].losses += 1
    return stats


def league_averages(stats: dict) -> Tuple[float, float]:
    """Returns (avg_goals_home_per_match, avg_goals_away_per_match)."""
    home_goals = sum(hg for _, _, hg, _ in SEASON_RESULTS)
    away_goals = sum(ag for _, _, _, ag in SEASON_RESULTS)
    n = len(SEASON_RESULTS)
    return home_goals / n, away_goals / n
