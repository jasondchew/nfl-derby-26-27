"""Download the season's schedule, teams and roster names from nflverse into data/.

    python fetch_data.py
"""
from pathlib import Path

import pandas as pd

SEASON = 2026
OUT = Path(__file__).parent / "data"
RELEASES = "https://github.com/nflverse/nflverse-data/releases/download"
GAMES_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"


def main():
    OUT.mkdir(exist_ok=True)

    games = pd.read_csv(GAMES_URL)
    games = games[games.season == SEASON].rename(columns={"espn": "espn_game_id"})
    games = games[[
        "game_id", "week", "game_type", "gameday", "away_team", "home_team",
        "away_score", "home_score", "espn_game_id",
    ]]

    abbrs = set(games.home_team) | set(games.away_team)
    teams = pd.read_csv(f"{RELEASES}/teams/teams_colors_logos.csv")
    teams = teams[teams.team_abbr.isin(abbrs)].rename(columns={"team_division": "division"})[
        ["team_abbr", "team_name", "team_nick", "division", "team_color", "team_color2", "team_color3"]
    ]

    # full names for highlight text (play-by-play only has abbreviations like "P.Mahomes")
    players = pd.read_csv(f"{RELEASES}/rosters/roster_{SEASON}.csv").dropna(subset=["gsis_id"])
    players = players.rename(columns={"gsis_id": "player_id"})[["player_id", "full_name"]]

    for name, df in {"games": games, "teams": teams, "players": players}.items():
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"{name:8s} {len(df):5d} rows")


if __name__ == "__main__":
    main()
