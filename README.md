# NFL Derby 26-27

**Open it: https://jasondchew.github.io/nfl-derby-26-27/**

Follow the 2026-27 NFL season as a horse race. All 32 teams run week by week, and you can watch who pulls ahead, who fades, and how each game moved them.

## What you can do

- **Play the race** from Week 1, or drag the slider to any week.
- **Choose what "best" means.** Rank teams by wins or by point differential (points scored minus points allowed). The leader often changes depending on which you pick.
- **Follow your team.** Their lane lights up and the highlights switch to their season so far.
- **See who moved.** Each week, a strip above the race shows the biggest climber, the biggest drop, and who's on top.
- **Read the highlights.** Every game gets its biggest moments, like a turnover that set up a touchdown or the play that turned the game. Each one shows how much it changed the team's chance of winning (for example 38% → 71%) and links to a search for the clip and to the full game recap.
- **Look ahead.** "Games to watch" lists the next week's matchups with kickoff times and the betting-line favorite, closest games first.
- **New to football?** Terms like *turnover*, *interception* and *4th down* are underlined. Hover or tap for a plain-English explanation.
- **Hover or tap any team** for its record, point differential and last result.

## Always current

The page updates itself every morning during the season. A scheduled GitHub Action pulls the latest results and play-by-play from [nflverse](https://github.com/nflverse), rebuilds the page, and publishes it. No one has to touch it.

## Run it yourself

```
pip install -r requirements.txt
python fetch_data.py
python build_race.py
```

Then open `docs/index.html`. To track a different season, change `SEASON` at the top of both scripts.

| File | Job |
|---|---|
| `fetch_data.py` | Downloads the schedule, team colors and player names into `data/` |
| `build_race.py` | Works out each week's standings, writes highlights from play-by-play, and fills `race_template.html` into `docs/index.html` |
| `.github/workflows/refresh.yml` | Runs both scripts every morning and publishes any changes |

Highlights are built from recorded play data (players, yards, how much each play changed the odds of winning), so every sentence traces back to a real play.

Data: [nflverse](https://github.com/nflverse), CC-BY 4.0. Not affiliated with the NFL.

Built with [Claude Code](https://claude.com/claude-code) as a fun way to follow the season.
