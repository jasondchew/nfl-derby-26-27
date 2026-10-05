"""Turn data/games.csv into the week-by-week standings the derby animation plays.

Run after fetch_data.py:
    python build_race.py
Writes docs/index.html (race_template.html with the data filled in), served by GitHub Pages.
"""
import json
from datetime import date
from urllib.parse import quote_plus
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
SEASON = 2026


def strength_ratings(played, abbrs):
    """Least-squares ratings: pick r so that r_home - r_away best matches each game's margin.

    One equation per game, plus sum(r) = 0 to pin the scale. Early in the season the
    system is underdetermined, so lstsq returns the smallest ratings that fit.
    """
    idx = {a: i for i, a in enumerate(abbrs)}
    rows, margins = [], []
    for g in played.itertuples():
        row = np.zeros(len(abbrs))
        row[idx[g.home_team]], row[idx[g.away_team]] = 1, -1
        rows.append(row)
        margins.append(g.home_score - g.away_score)
    rows.append(np.ones(len(abbrs)))
    margins.append(0)
    r, *_ = np.linalg.lstsq(np.array(rows), np.array(margins), rcond=None)
    return {a: round(float(r[idx[a]]), 2) for a in abbrs}


PBP_URL = f"https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{SEASON}.csv.gz"


def build_highlights(games, nick):
    """Up to 2 highlights per game, written from play-by-play fields (no free text invented).

    Kinds: a turnover the other team turned into a touchdown, a defensive return TD,
    the play with the biggest win-probability swing, and touchdowns of 40+ yards.
    """
    p = pd.read_csv(PBP_URL, low_memory=False)
    full = pd.read_csv(HERE / "data/players.csv").set_index("player_id").full_name.to_dict()

    def name(play, role):
        pid, abbr = play.get(f"{role}_player_id"), play.get(f"{role}_player_name")
        if pd.notna(pid) and pid in full:
            return full[pid]
        return abbr if pd.notna(abbr) else "a defender"

    def when(play):
        q = int(play["qtr"])
        return f"{'OT' if q == 5 else f'Q{q}'} {play['time']}"

    def star(play):
        """The player a video title would most likely name."""
        if play["interception"] == 1:
            return name(play, "interception")
        if play["fumble_lost"] == 1:
            return name(play, "fumble_recovery_1")
        if play["play_type"] == "field_goal":
            return name(play, "kicker")
        if play["play_type"] == "run":
            return name(play, "rusher")
        if play["complete_pass"] == 1:
            return name(play, "receiver")
        return name(play, "passer")

    def chance(helped, before_play, after_play, helped_had_ball):
        """Win chance for `helped` before before_play and after after_play, as whole percents."""
        b, a = before_play["wp"], after_play["wp"] + after_play["wpa"]
        if pd.isna(b) or pd.isna(a):
            return None
        if not helped_had_ball[0]:
            b = 1 - b
        if not helped_had_ball[1]:
            a = 1 - a
        return {"team": nick[helped], "before": round(b * 100), "after": round(min(max(a, 0), 1) * 100)}

    def single(play):
        """Win chance change for whichever team the play helped."""
        if pd.isna(play["wpa"]):
            return None
        off = play["wpa"] >= 0
        return chance(play["posteam"] if off else play["defteam"], play, play, (off, off))

    def describe(play):
        yds = int(play["yards_gained"]) if pd.notna(play["yards_gained"]) else 0
        td = play["touchdown"] == 1
        if play["play_type"] == "pass" and play["interception"] == 1:
            s = f"{name(play, 'interception')} intercepted {name(play, 'passer')}"
            return s + " and returned it for a touchdown" if play["return_touchdown"] == 1 else s
        if play["fumble_lost"] == 1:
            return f"{name(play, 'fumbled_1')} lost a fumble, recovered by {name(play, 'fumble_recovery_1')}"
        if play["play_type"] == "pass" and play["sack"] == 1:
            return f"{name(play, 'passer')} was sacked for a loss of {abs(yds)}"
        if play["play_type"] == "pass" and play["complete_pass"] == 1:
            return f"{name(play, 'passer')} hit {name(play, 'receiver')} for {yds} yards" + (" and a touchdown" if td else "")
        if play["play_type"] == "pass":
            return f"{name(play, 'passer')}'s pass fell incomplete" + (" on 4th down" if play["down"] == 4 else "")
        if play["play_type"] == "run" and yds <= 0:
            s = f"{name(play, 'rusher')} was stopped " + (f"for a loss of {-yds}" if yds else "for no gain")
            return s + (" on 4th down" if play["down"] == 4 else "")
        if play["play_type"] == "run":
            s = f"{name(play, 'rusher')} ran for {yds} yards" + (" and a touchdown" if td else "")
            return s + (" on 4th down" if play["down"] == 4 and not td else "")
        if play["play_type"] == "field_goal":
            res = "was good" if play["field_goal_result"] == "made" else "was no good"
            return f"{name(play, 'kicker')}'s {int(play['kick_distance'])}-yard field goal {res}"
        return None

    out = []
    gmeta = games.set_index("game_id")
    for gid, g in p.groupby("game_id"):
        if gid not in gmeta.index or pd.isna(gmeta.at[gid, "home_score"]):
            continue
        gm = gmeta.loc[gid]
        score = f"{gm.away_team} {int(gm.away_score)} @ {gm.home_team} {int(gm.home_score)}"
        recap = (f"https://www.espn.com/nfl/game/_/gameId/{int(gm.espn_game_id)}"
                 if pd.notna(gm.espn_game_id) else None)
        cands, used = [], set()
        scrimmage = g[g.play_type.isin(["pass", "run"])]

        # turnovers on offense: return TD, or the other team's next drive ends in a TD
        for idx, tp in scrimmage[(scrimmage.interception == 1) | (scrimmage.fumble_lost == 1)].iterrows():
            off, dfn = tp["posteam"], tp["defteam"]
            if tp["interception"] == 1:
                what = f"{name(tp, 'interception')} intercepted {name(tp, 'passer')}"
            else:
                what = f"{name(tp, 'fumble_recovery_1')} recovered a fumble by {name(tp, 'fumbled_1')}"
            if tp["return_touchdown"] == 1:
                cands.append((abs(tp["wpa"]) + 0.2, {idx}, tp, "Defensive TD",
                              f"{what} and took it back for a {nick[dfn]} touchdown.", [off, dfn],
                              chance(dfn, tp, tp, (False, False))))
                continue
            nxt = g[(g.fixed_drive == tp["fixed_drive"] + 1) & (g.posteam == dfn)]
            if nxt.empty or nxt.fixed_drive_result.iloc[0] != "Touchdown":
                continue
            tdp = nxt[(nxt.touchdown == 1) & (nxt.td_team == dfn)]
            if tdp.empty:
                continue
            tdp = tdp.iloc[0]
            snaps = len(nxt[nxt.play_type.isin(["pass", "run"])])
            start = int(nxt.yardline_100.dropna().iloc[0])
            later = "on the next play" if snaps <= 1 else f"{snaps} plays later"
            short = f" They started {start} yards from the end zone." if start <= 35 else ""
            cands.append((abs(tp["wpa"]) + abs(tdp["wpa"]) + 0.15, {idx, tdp.name}, tp, "Turnover → TD",
                          f"{nick[off]} turnover: {what}, and {later} {describe(tdp)}.{short}", [off, dfn],
                          chance(dfn, tp, tdp, (False, True))))

        # biggest win-probability swing in the game
        sw = scrimmage.dropna(subset=["wpa"])
        sw = pd.concat([sw, g[g.play_type == "field_goal"].dropna(subset=["wpa"])])
        if not sw.empty:
            idx = sw.wpa.abs().idxmax()
            bp = g.loc[idx]
            d = describe(bp)
            if d:
                diff = int(bp["score_differential"])
                sit = ("With the game tied" if diff == 0
                       else f"With the {nick[bp['posteam']]} {'up' if diff > 0 else 'down'} {abs(diff)}")
                cands.append((abs(bp["wpa"]), {idx}, bp, "Turning point",
                              f"{sit}, {d}.", [bp["posteam"], bp["defteam"]], single(bp)))

        # long touchdowns
        for idx, lp in scrimmage[(scrimmage.touchdown == 1) & (scrimmage.yards_gained >= 40)
                                 & (scrimmage.td_team == scrimmage.posteam)].iterrows():
            cands.append((lp["yards_gained"] / 250, {idx}, lp, "Long TD",
                          f"{nick[lp['posteam']]}: {describe(lp)}.",
                          [lp["posteam"], lp["defteam"]], single(lp)))

        picked = 0
        for sc, ids, play, kind, text, tms, wp in sorted(cands, key=lambda c: -c[0]):
            if ids & used or picked == 2:
                continue
            used |= ids
            picked += 1
            q = f"{star(play)} {nick[gm.away_team]} vs {nick[gm.home_team]} week {int(gm.week)} {SEASON}"
            out.append({"week": int(gm.week), "game": score, "teams": tms, "kind": kind,
                        "when": when(play), "text": text.replace("..", "."), "score": round(float(sc), 3),
                        "clip": "https://www.youtube.com/results?search_query=" + quote_plus(q),
                        "recap": recap, "wp": wp})
    return out


def build_upcoming(reg, nick):
    """Unplayed games in the next 8 days, with the favorite from the betting line.

    spread_line is from the home team's side: +3 means the home team is favored by 3.
    """
    today = pd.Timestamp(date.today())
    soon = reg[reg.home_score.isna()].copy()
    soon["day"] = pd.to_datetime(soon.gameday)
    soon = soon[(soon.day >= today) & (soon.day < today + pd.Timedelta(days=8))]
    out = []
    for g in soon.itertuples():
        h, m = map(int, str(g.gametime).split(":"))
        kick = f"{(h - 1) % 12 + 1}:{m:02d} {'PM' if h >= 12 else 'AM'} ET"
        line = None if pd.isna(g.spread_line) else float(g.spread_line)
        out.append({
            "week": int(g.week), "away": g.away_team, "home": g.home_team,
            "when": f"{g.day:%a %b} {g.day.day}, {kick}", "neutral": g.location == "Neutral",
            "fav": None if line is None else nick[g.home_team if line > 0 else g.away_team],
            "margin": None if line is None else abs(line),
        })
    return sorted(out, key=lambda x: (x["margin"] is None, x["margin"] or 0))


def main():
    games = pd.read_csv(HERE / "data/games.csv")
    teams = pd.read_csv(HERE / "data/teams.csv").sort_values("team_abbr")
    nick = dict(zip(teams.team_abbr, teams.team_nick))
    abbrs = list(teams.team_abbr)
    reg = games[games.game_type == "REG"]
    played = reg[reg.home_score.notna()]
    last_week = int(played.week.max())

    wins = {a: 0.0 for a in abbrs}
    pd_ = {a: 0 for a in abbrs}
    wlt = {a: [0, 0, 0] for a in abbrs}
    last = {a: "" for a in abbrs}
    frames = [{
        "wins": [0] * len(abbrs), "pd": [0] * len(abbrs), "srs": [0] * len(abbrs),
        "rec": ["0-0"] * len(abbrs), "last": ["Starting gate"] * len(abbrs),
    }]
    for wk in range(1, last_week + 1):
        played_now = set()
        for g in played[played.week == wk].itertuples():
            for us, them, pf, pa, at in [
                (g.home_team, g.away_team, g.home_score, g.away_score, "vs"),
                (g.away_team, g.home_team, g.away_score, g.home_score, "@"),
            ]:
                res = "W" if pf > pa else "L" if pf < pa else "T"
                wins[us] += {"W": 1, "L": 0, "T": 0.5}[res]
                wlt[us]["WLT".index(res)] += 1
                pd_[us] += int(pf - pa)
                last[us] = f"Wk {wk}: {res} {int(pf)}-{int(pa)} {at} {them}"
                played_now.add(us)
        srs = strength_ratings(played[played.week <= wk], abbrs)
        frames.append({
            "wins": [wins[a] for a in abbrs],
            "pd": [pd_[a] for a in abbrs],
            "srs": [srs[a] for a in abbrs],
            "rec": ["-".join(map(str, wlt[a][:2])) + (f"-{wlt[a][2]}" if wlt[a][2] else "") for a in abbrs],
            "last": [last[a] if a in played_now else f"Wk {wk}: bye" for a in abbrs],
        })

    wk_games = reg[reg.week == last_week]
    final = int(wk_games.home_score.notna().sum())
    status = (f"Through Week {last_week}" if final == len(wk_games)
              else f"Week {last_week}: {final} of {len(wk_games)} games final")
    data = {
        "updated": str(played.gameday.max()),
        "status": status,
        "teams": [{"abbr": t.team_abbr, "name": t.team_name, "nick": t.team_nick, "div": t.division,
                   # helmet shell + stripe; black stripes vanish on a dark shell, so fall back to color 3
                   "c1": t.team_color,
                   "c2": t.team_color3 if t.team_color2.lower() == "#000000" else t.team_color2}
                  for t in teams.itertuples()],
        "frames": frames,
        "highlights": build_highlights(games, nick),
        "upcoming": build_upcoming(reg, nick),
    }
    html = (HERE / "race_template.html").read_text(encoding="utf-8")
    (HERE / "docs").mkdir(exist_ok=True)
    (HERE / "docs/index.html").write_text(
        html.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":"))), encoding="utf-8")
    print(status, "| frames:", len(frames))


if __name__ == "__main__":
    main()
