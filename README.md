# NFL Derby 26-27

**Live page: https://jasondchew.github.io/nfl-derby-26-27/**

An animated, week-by-week race of all 32 NFL teams in the 2026-27 season, plus game highlights generated from play-by-play data. You can rank teams three ways: wins, point differential, or a strength-adjusted rating (a least-squares fit where each game is one equation, `home rating − away rating = margin`).

The page updates itself. A GitHub Action runs every morning, pulls the latest data from [nflverse](https://github.com/nflverse), rebuilds the CSVs and the page, and commits only when something changed.

## How it works

| Step | File | What it does |
|---|---|---|
| 1 | `build_nfl_csvs.py` | Downloads schedule, rosters, player stats and injuries; trims them into 5 tidy CSVs in `data/` |
| 2 | `build_race.py` | Computes cumulative standings and ratings for each week, writes highlights from play-by-play, fills `race_template.html` into `docs/index.html` |
| 3 | `.github/workflows/refresh.yml` | Runs steps 1 and 2 daily; GitHub Pages serves `docs/` |

Run locally: `pip install -r requirements.txt`, then `python build_nfl_csvs.py && python build_race.py`.

Highlights are written from structured play fields (players, yards, win probability added) using templates, so every sentence traces back to a recorded play.

---

# SQL practice data

## Tables (`data/`)

| File | Grain (one row per...) | Key columns |
|---|---|---|
| `teams.csv` | team (32) | `team_abbr` |
| `games.csv` | game (all 272, including future ones) | `game_id`, `home_team`, `away_team` |
| `players.csv` | player on a 2026 roster | `player_id`, `team_abbr` |
| `player_game_stats.csv` | player per game they recorded a stat in | `player_id`, `game_id`, `team_abbr`, `opponent_abbr` |
| `injury_reports.csv` | player per week on the injury report | `player_id`, `week`, `team_abbr` |

## How they connect

- `games.home_team` / `games.away_team` → `teams.team_abbr` (two separate joins; you'll need to pick these manually in the Tutor since the names don't match)
- `player_game_stats.player_id` → `players.player_id`
- `player_game_stats.game_id` → `games.game_id`
- `injury_reports.player_id` → `players.player_id`

## Things to know (good SQL practice in themselves)

- **Future games have NULL scores.** Filter with `home_score IS NOT NULL` for completed games.
- **No winner column.** You derive it: `CASE WHEN home_score > away_score THEN home_team ...` (ties are possible).
- **`spread_line`** is from the home team's view: positive = home team favored by that many points. `total_line` is the over/under.
- **`location = 'Neutral'`** marks international/neutral-site games (e.g., the Week 1 SF-LA game in Melbourne).
- **`players.team_abbr` is the current team**, while `player_game_stats.team_abbr` is the team they played for *in that game*. A traded player shows the difference.
- **`players.status`**: ACT active, RES reserve/IR, DEV practice squad, CUT released, INA inactive, RET retired.
- **`injury_reports.report_status`** is NULL when a player was listed for practice but carried no game designation.
- **`passing_epa` / `rushing_epa`**: expected points added; above 0 means the play helped more than an average play would.
- `fantasy_points_ppr` uses standard PPR scoring.
