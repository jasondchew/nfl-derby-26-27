"""Pull 2026 NFL season data from nflverse and write SQL-practice CSVs.

Re-run any time (e.g. Tuesday mornings) to pick up the latest completed week:
    python build_nfl_csvs.py
"""
from pathlib import Path

import pandas as pd

SEASON = 2026
OUT = Path(__file__).parent / "data"
RELEASES = "https://github.com/nflverse/nflverse-data/releases/download"
GAMES_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"


def build_games():
    g = pd.read_csv(GAMES_URL)
    g = g[g.season == SEASON]
    cols = [
        "game_id", "week", "game_type", "gameday", "weekday", "gametime",
        "away_team", "home_team", "away_score", "home_score", "overtime",
        "location", "div_game", "spread_line", "total_line",
        "away_qb_name", "home_qb_name", "away_coach", "home_coach",
        "roof", "surface", "temp", "wind", "stadium", "espn_game_id",
    ]
    g = g.rename(columns={"espn": "espn_game_id"})
    return g[cols], set(g.home_team) | set(g.away_team)


def build_teams(current_abbrs):
    t = pd.read_csv(f"{RELEASES}/teams/teams_colors_logos.csv")
    t = t[t.team_abbr.isin(current_abbrs)]  # drop relocated franchises (OAK, SD, STL, LAR dup)
    return t.rename(columns={"team_conf": "conference", "team_division": "division"})[
        ["team_abbr", "team_name", "team_nick", "conference", "division", "team_color", "team_color2", "team_color3"]
    ]


def build_players():
    r = pd.read_csv(f"{RELEASES}/rosters/roster_{SEASON}.csv")
    r = r.dropna(subset=["gsis_id"])
    r = r.rename(columns={"gsis_id": "player_id", "team": "team_abbr", "week": "as_of_week"})
    return r[[
        "player_id", "full_name", "position", "team_abbr", "jersey_number", "status",
        "birth_date", "height", "weight", "college", "years_exp", "rookie_year",
        "draft_club", "draft_number", "as_of_week",
    ]]


def build_player_game_stats():
    s = pd.read_csv(f"{RELEASES}/stats_player/stats_player_week_{SEASON}.csv", low_memory=False)
    s = s.rename(columns={"team": "team_abbr", "opponent_team": "opponent_abbr"})
    cols = [
        "player_id", "game_id", "week", "team_abbr", "opponent_abbr",
        # passing
        "completions", "attempts", "passing_yards", "passing_tds", "passing_interceptions",
        "sacks_suffered", "passing_epa",
        # rushing
        "carries", "rushing_yards", "rushing_tds", "rushing_fumbles_lost", "rushing_epa",
        # receiving
        "targets", "receptions", "receiving_yards", "receiving_tds", "receiving_yards_after_catch",
        "target_share",
        # defense
        "def_tackles_solo", "def_tackle_assists", "def_tackles_for_loss", "def_sacks",
        "def_qb_hits", "def_interceptions", "def_pass_defended", "def_fumbles_forced", "def_tds",
        # kicking
        "fg_made", "fg_att", "fg_long", "pat_made", "pat_att",
        # misc
        "penalties", "penalty_yards", "fantasy_points_ppr",
    ]
    return s[cols]


def build_injuries():
    i = pd.read_csv(f"{RELEASES}/injuries/injuries_{SEASON}.csv")
    i = i.rename(columns={"gsis_id": "player_id", "team": "team_abbr"})
    return i[[
        "week", "player_id", "team_abbr", "report_primary_injury",
        "report_status", "practice_primary_injury", "practice_status",
    ]]


def main():
    OUT.mkdir(exist_ok=True)
    games, abbrs = build_games()
    tables = {
        "teams": build_teams(abbrs),
        "games": games,
        "players": build_players(),
        "player_game_stats": build_player_game_stats(),
        "injury_reports": build_injuries(),
    }
    for name, df in tables.items():
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"{name:20s} {len(df):6d} rows  {df.shape[1]:3d} cols")
    played = games.home_score.notna()
    print(f"\nGames completed: {played.sum()} of {len(games)} "
          f"(through week {int(games[played].week.max())})")


if __name__ == "__main__":
    main()
