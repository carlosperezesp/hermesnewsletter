#!/usr/bin/env python3
"""Fetch NBA data from ESPN public API and regenerate nba_data.js."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "nba_data.js"


# ── Prev-rank helpers ────────────────────────────────────────────────────────

def _prev_rank_map(filepath: Path, js_var: str, *path: str) -> "dict[str, int]":
    import re as _re, json as _json
    try:
        text = filepath.read_text(encoding="utf-8")
        text = _re.sub(
            r"^window\." + _re.escape(js_var) + r"\s*=\s*", "", text, flags=_re.MULTILINE
        ).rstrip().rstrip(";")
        obj = _json.loads(text)
        for key in path:
            obj = obj.get(key) if isinstance(obj, dict) else None
            if obj is None:
                return {}
        if not isinstance(obj, list):
            return {}
        result: dict[str, int] = {}
        for i, item in enumerate(obj[:20]):
            k = str(item.get("id") or item.get("name", ""))
            if k:
                result[k] = i + 1
        return result
    except Exception:
        return {}


def _prev_rank_map_teams(filepath: Path, js_var: str, *path: str) -> "dict[str, int]":
    import re as _re, json as _json
    try:
        text = filepath.read_text(encoding="utf-8")
        text = _re.sub(
            r"^window\." + _re.escape(js_var) + r"\s*=\s*", "", text, flags=_re.MULTILINE
        ).rstrip().rstrip(";")
        obj = _json.loads(text)
        for key in path:
            obj = obj.get(key) if isinstance(obj, dict) else None
            if obj is None:
                return {}
        if not isinstance(obj, list):
            return {}
        result: dict[str, int] = {}
        for i, item in enumerate(obj[:20]):
            k = f"{item.get('teamCode','')}-{item.get('era','')}"
            if k != "-":
                result[k] = i + 1
        return result
    except Exception:
        return {}

API_STANDINGS  = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"
API_PLAYERS    = "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/statistics/byathlete"
API_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

NBA_TEAM_COLORS = {
    "ATL":  {"primary": "#e03a3e", "secondary": "#c1d32f"},
    "BOS":  {"primary": "#007a33", "secondary": "#ba9653"},
    "BKN":  {"primary": "#000000", "secondary": "#ffffff"},
    "CHA":  {"primary": "#1d1160", "secondary": "#00788c"},
    "CHI":  {"primary": "#ce1141", "secondary": "#000000"},
    "CLE":  {"primary": "#860038", "secondary": "#fdbb30"},
    "DAL":  {"primary": "#00538c", "secondary": "#002b5e"},
    "DEN":  {"primary": "#0e2240", "secondary": "#fec524"},
    "DET":  {"primary": "#c8102e", "secondary": "#006bb6"},
    "GS":   {"primary": "#1d428a", "secondary": "#ffc72c"},
    "HOU":  {"primary": "#ce1141", "secondary": "#c4cdd2"},
    "IND":  {"primary": "#002d62", "secondary": "#fdbb30"},
    "LAC":  {"primary": "#c8102e", "secondary": "#1d428a"},
    "LAL":  {"primary": "#552583", "secondary": "#fdb927"},
    "MEM":  {"primary": "#5d76a9", "secondary": "#12173f"},
    "MIA":  {"primary": "#98002e", "secondary": "#f9a01b"},
    "MIL":  {"primary": "#00471b", "secondary": "#eee1c6"},
    "MIN":  {"primary": "#0c2340", "secondary": "#236192"},
    "NO":   {"primary": "#0c2340", "secondary": "#85714d"},
    "NY":   {"primary": "#006bb6", "secondary": "#f58426"},
    "OKC":  {"primary": "#007ac1", "secondary": "#ef3b24"},
    "ORL":  {"primary": "#0077c0", "secondary": "#c4ced4"},
    "PHI":  {"primary": "#006bb6", "secondary": "#ed174c"},
    "PHX":  {"primary": "#1d1160", "secondary": "#e56020"},
    "POR":  {"primary": "#e03a3e", "secondary": "#000000"},
    "SA":   {"primary": "#c4ced4", "secondary": "#000000"},
    "SAC":  {"primary": "#5a2d81", "secondary": "#63727a"},
    "TOR":  {"primary": "#ce1141", "secondary": "#000000"},
    "UTAH": {"primary": "#002b5e", "secondary": "#00471b"},
    "WSH":  {"primary": "#002b5e", "secondary": "#e31837"},
}

STATIC_HISTORY_TEAMS = [
    {"rank": 1, "era": "1995-98", "city": "Chicago Bulls",          "teamCode": "CHI", "country": "United States", "conf": "Central",   "titles": 3, "score": 99.0, "conf_tier": "A", "note": "72-10 season · second three-peat · Jordan at his peak"},
    {"rank": 2, "era": "1999-07", "city": "San Antonio Spurs",      "teamCode": "SA",  "country": "United States", "conf": "Southwest", "titles": 4, "score": 97.5, "conf_tier": "A", "note": "4 titles in 9 years · Duncan/Popovich dynasty"},
    {"rank": 3, "era": "1980-88", "city": "Los Angeles Lakers",     "teamCode": "LAL", "country": "United States", "conf": "Pacific",   "titles": 5, "score": 96.8, "conf_tier": "A", "note": "Showtime Lakers · Magic era · 5 championships"},
    {"rank": 4, "era": "2015-19", "city": "Golden State Warriors",  "teamCode": "GS",  "country": "United States", "conf": "Pacific",   "titles": 3, "score": 95.2, "conf_tier": "A", "note": "73-9 season · Splash Bros + Durant · 3 titles in 5 years"},
    {"rank": 5, "era": "1959-66", "city": "Boston Celtics",         "teamCode": "BOS", "country": "United States", "conf": "East",      "titles": 8, "score": 94.1, "conf_tier": "C", "note": "8 straight titles · Bill Russell era · unmatched winning"},
    {"rank": 6, "era": "2000-02", "city": "Los Angeles Lakers",     "teamCode": "LAL", "country": "United States", "conf": "Pacific",   "titles": 3, "score": 93.6, "conf_tier": "A", "note": "Shaq/Kobe three-peat · physically dominant run"},
    {"rank": 7, "era": "1991-93", "city": "Chicago Bulls",          "teamCode": "CHI", "country": "United States", "conf": "Central",   "titles": 3, "score": 92.8, "conf_tier": "A", "note": "First three-peat · Jordan/Pippen/Horace Grant"},
    {"rank": 8, "era": "2012-14", "city": "Miami Heat",             "teamCode": "MIA", "country": "United States", "conf": "Southeast", "titles": 2, "score": 91.5, "conf_tier": "A", "note": "LeBron/Wade/Bosh · 4 straight Finals appearances"},
    {"rank": 9, "era": "1986-90", "city": "Detroit Pistons",        "teamCode": "DET", "country": "United States", "conf": "Central",   "titles": 2, "score": 90.2, "conf_tier": "A", "note": "Bad Boys · back-to-back champions · defensive dynasty"},
    {"rank": 10,"era": "2007-08", "city": "Boston Celtics",         "teamCode": "BOS", "country": "United States", "conf": "Atlantic",  "titles": 1, "score": 89.4, "conf_tier": "A", "note": "KG/Pierce/Allen superteam · 66-16 regular season"},
]

STATIC_HISTORY_PLAYERS = [
    {"rank": 1,  "name": "Michael Jordan",       "pos": "SG", "teamCode": "CHI", "country": "United States", "era": "1984-03",       "tier": "A", "score": 100.0, "note": "6 titles · 6 Finals MVP · greatest scorer in NBA history"},
    {"rank": 2,  "name": "LeBron James",          "pos": "SF", "teamCode": "LAL", "country": "United States", "era": "2003-present",  "tier": "A", "score": 98.8,  "note": "4 titles · all-time points leader · generational longevity"},
    {"rank": 3,  "name": "Kareem Abdul-Jabbar",   "pos": "C",  "teamCode": "LAL", "country": "United States", "era": "1969-89",       "tier": "A", "score": 98.1,  "note": "6 titles · 6 regular-season MVP · skyhook pioneer"},
    {"rank": 4,  "name": "Magic Johnson",          "pos": "PG", "teamCode": "LAL", "country": "United States", "era": "1979-91",       "tier": "A", "score": 97.2,  "note": "5 titles · 3 MVP · redefined the point guard position"},
    {"rank": 5,  "name": "Bill Russell",           "pos": "C",  "teamCode": "BOS", "country": "United States", "era": "1956-69",       "tier": "B", "score": 96.4,  "note": "11 titles · 5 MVP · greatest winner in professional sports"},
    {"rank": 6,  "name": "Wilt Chamberlain",       "pos": "C",  "teamCode": "PHI", "country": "United States", "era": "1959-73",       "tier": "B", "score": 95.5,  "note": "100-point game · all-time scoring and rebounding dominance"},
    {"rank": 7,  "name": "Larry Bird",             "pos": "SF", "teamCode": "BOS", "country": "United States", "era": "1979-92",       "tier": "A", "score": 94.3,  "note": "3 titles · 3 MVP · clutch shooter of his era"},
    {"rank": 8,  "name": "Shaquille O'Neal",       "pos": "C",  "teamCode": "LAL", "country": "United States", "era": "1992-11",       "tier": "A", "score": 93.7,  "note": "4 titles · most physically dominant center ever"},
    {"rank": 9,  "name": "Kobe Bryant",            "pos": "SG", "teamCode": "LAL", "country": "United States", "era": "1996-16",       "tier": "A", "score": 93.0,  "note": "5 titles · 81-point game · Mamba mentality"},
    {"rank": 10, "name": "Tim Duncan",             "pos": "PF", "teamCode": "SA",  "country": "United States", "era": "1997-16",       "tier": "A", "score": 92.1,  "note": "5 titles · 2 MVP · greatest power forward of all time"},
]

NBA_ACTIVE_ERA_TEAMS = [
    {"teamCode": "OKC", "city": "Oklahoma City Thunder",      "era": "2023–present", "rings": 0, "note": "SGA era · 2025 #1 seed West · dynasty in the making"},
    {"teamCode": "BOS", "city": "Boston Celtics",             "era": "2022–present", "rings": 1, "note": "2024 Champions · Tatum/Brown core"},
    {"teamCode": "DEN", "city": "Denver Nuggets",             "era": "2019–present", "rings": 1, "note": "2023 Champions · Jokic 3× MVP era"},
    {"teamCode": "MIL", "city": "Milwaukee Bucks",            "era": "2019–present", "rings": 1, "note": "2021 Champions · Giannis 2× MVP era"},
    {"teamCode": "SA",  "city": "San Antonio Spurs",          "era": "2023–present", "rings": 0, "note": "Wembanyama era · generational rebuild underway"},
    {"teamCode": "NY",  "city": "New York Knicks",            "era": "2022–present", "rings": 0, "note": "2025 Eastern Conference Finals · resurgent era"},
    {"teamCode": "MIN", "city": "Minnesota Timberwolves",     "era": "2022–present", "rings": 0, "note": "2025 Western Conference Finals · Edwards era"},
    {"teamCode": "GS",  "city": "Golden State Warriors",      "era": "2021–present", "rings": 1, "note": "2022 Champions · Curry's final dynasty chapter"},
    {"teamCode": "IND", "city": "Indiana Pacers",             "era": "2024–present", "rings": 0, "note": "2025 Eastern Conference Finals · Haliburton era"},
    {"teamCode": "LAL", "city": "Los Angeles Lakers",         "era": "2020–present", "rings": 1, "note": "2020 Bubble Champions · LeBron/AD · finals ambitions"},
]

# Known rings for active/recent players — used for Road to Glory bonus
PLAYER_RINGS = {
    "LeBron James":           4,
    "Stephen Curry":          4,
    "Kevin Durant":           2,
    "Kawhi Leonard":          2,
    "Giannis Antetokounmpo":  1,
    "Nikola Jokic":           1,
    "Jayson Tatum":           1,
    "Jaylen Brown":           1,
}

# Active stars always included in Road to Glory tracking
ROAD_TO_GLORY_STARS = {
    "Nikola Jokic",
    "Giannis Antetokounmpo",
    "Shai Gilgeous-Alexander",
    "Jayson Tatum",
    "Luka Doncic",
    "Victor Wembanyama",
    "Anthony Edwards",
    "Donovan Mitchell",
    "Tyrese Haliburton",
    "Paolo Banchero",
    "LeBron James",
    "Stephen Curry",
}

METHODOLOGY = {
    "player": {
        "formula": "Current NBA box-score percentile using ESPN regular-season or playoff statistics, depending on active context",
        "bullets": [
            "Points, rebounds, assists, steals, blocks per game plus minutes played",
            "All positions (G, F, C) scored together — formula naturally rewards all-around play",
            "Scores normalized 0-100 using min-max percentile within qualified players",
            "Road to Glory career score uses current peak scaled to all-time equivalent",
            "This is a transparent tracker score, not an official NBA metric",
        ],
    },
    "team": {
        "formula": "Win percentage and point differential blend",
        "bullets": [
            "Win% accounts for ~82% of the score — it is the primary NBA success metric",
            "Per-game point differential adds depth beyond raw wins",
            "Playoff bracket is built from ESPN scoreboard series data",
            "Generated data can be refreshed daily with scripts/update_nba_data.py",
        ],
    },
    "confidence": [
        {"tier": "A", "years": "1980 -> present", "note": "Modern NBA statistical coverage"},
        {"tier": "B", "years": "1960 -> 1979",    "note": "Pre-merger era, less event detail"},
        {"tier": "C", "years": "1946 -> 1959",    "note": "Early BAA/NBA era, mostly box-score"},
    ],
}


def fetch_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "NBA Tracker local updater"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except HTTPError as exc:
        raise RuntimeError(f"{url} returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc


def percentile_scores(items: list[dict], value_fn) -> dict[int, int]:
    values = [(item["id"], value_fn(item)) for item in items]
    if not values:
        return {}
    nums = [v for _, v in values]
    lo, hi = min(nums), max(nums)
    if math.isclose(lo, hi):
        return {item_id: 65 for item_id, _ in values}
    return {
        item_id: int(round(35 + ((v - lo) / (hi - lo)) * 65))
        for item_id, v in values
    }


def with_nba_colors(item: dict, code_key: str = "teamCode") -> dict:
    code = item.get(code_key)
    item["colors"] = NBA_TEAM_COLORS.get(code, {"primary": "#666666", "secondary": "#d9d9d9"})
    return item


def build_teams(standings_data: dict) -> list[dict]:
    teams = []
    team_by_id: dict[str, dict] = {}
    for conf_data in standings_data.get("children", []):
        conf_name = conf_data.get("name", "")
        conf_abbrev = "E" if "Eastern" in conf_name else "W"
        for entry in conf_data.get("standings", {}).get("entries", []):
            t = entry["team"]
            stats = {s["name"]: s.get("value") for s in entry.get("stats", [])}
            code = t.get("abbreviation", "")
            wins = int(stats.get("wins", 0) or 0)
            losses = int(stats.get("losses", 0) or 0)
            win_pct = float(stats.get("winPercent", 0) or 0)
            pt_diff = float(stats.get("pointDifferential", 0) or 0)
            pts_for = float(stats.get("pointsFor", 0) or 0)
            pts_against = float(stats.get("pointsAgainst", 0) or 0)
            gp = wins + losses
            pt_diff_pg = pt_diff / max(1, gp)
            score = round(max(0, min(100, win_pct * 82 + pt_diff_pg * 1.8)))
            logos = t.get("logos", [])
            logo = logos[0].get("href", "") if logos else f"https://a.espncdn.com/i/teamlogos/nba/500/{code.lower()}.png"
            team = {
                "code": code,
                "city": t.get("displayName", ""),
                "shortName": t.get("location", ""),
                "commonName": t.get("name", ""),
                "conf": conf_abbrev,
                "gp": gp,
                "w": wins,
                "l": losses,
                "winPct": round(win_pct, 3),
                "gf": int(pts_for),
                "ga": int(pts_against),
                "gd": int(pt_diff),
                "score": score,
                "logo": logo,
                "colors": NBA_TEAM_COLORS.get(code, {"primary": "#666666", "secondary": "#d9d9d9"}),
            }
            teams.append(team)
            team_by_id[str(t.get("id", ""))] = team
    return sorted(teams, key=lambda t: (-t["w"], -t["gd"])), team_by_id


def nba_raw_score(stats: dict) -> float:
    pts = stats.get("pts", 0)
    reb = stats.get("reb", 0)
    ast = stats.get("ast", 0)
    stl = stats.get("stl", 0)
    blk = stats.get("blk", 0)
    min_pg = stats.get("min", 0)
    return pts * 3.5 + reb * 1.8 + ast * 2.0 + (stl + blk) * 2.5 + min_pg * 0.25


def build_players(player_data: dict, team_by_id: dict, min_gp: int = 10) -> list[dict]:
    # Map category labels from top-level categories definition
    cat_labels = {c["name"]: c.get("abbreviations", []) for c in player_data.get("categories", [])}
    gen_labels = cat_labels.get("general", [])
    off_labels = cat_labels.get("offensive", [])
    def_labels = cat_labels.get("defensive", [])

    def idx(labels: list, abbrev: str, default: int, last: bool = False) -> int:
        if last:
            positions = [i for i, l in enumerate(labels) if l == abbrev]
            return positions[-1] if positions else default
        return next((i for i, l in enumerate(labels) if l == abbrev), default)

    gp_idx  = idx(gen_labels, "GP",  0)
    min_idx = idx(gen_labels, "MIN", 1)
    reb_idx = idx(gen_labels, "REB", 11, last=True)
    pts_idx = idx(off_labels, "PTS", 0)
    ast_idx = idx(off_labels, "AST", 10)
    stl_idx = idx(def_labels, "STL", 0)
    blk_idx = idx(def_labels, "BLK", 1)

    players = []
    for entry in player_data.get("athletes", []):
        ath = entry.get("athlete", {})
        cats = {c["name"]: c.get("values", []) for c in entry.get("categories", [])}
        gen = cats.get("general", [])
        off = cats.get("offensive", [])
        def_ = cats.get("defensive", [])
        if not gen or not off:
            continue
        gp = int(gen[gp_idx]) if len(gen) > gp_idx else 0
        if gp < min_gp:
            continue

        # Team from `teams` array (more reliable than teamId mapping)
        teams_arr = ath.get("teams", [])
        if teams_arr:
            team_code = teams_arr[0].get("abbreviation", "")
        else:
            team_id = str(ath.get("teamId", ""))
            team_code = team_by_id.get(team_id, {}).get("code", ath.get("teamShortName", ""))

        pts     = float(off[pts_idx]) if len(off) > pts_idx else 0.0
        ast     = float(off[ast_idx]) if len(off) > ast_idx else 0.0
        reb     = float(gen[reb_idx]) if len(gen) > reb_idx else 0.0
        stl     = float(def_[stl_idx]) if def_ and len(def_) > stl_idx else 0.0
        blk     = float(def_[blk_idx]) if def_ and len(def_) > blk_idx else 0.0
        min_pg  = float(gen[min_idx]) if len(gen) > min_idx else 0.0

        hs = ath.get("headshot", {})
        headshot = hs.get("href", "") if isinstance(hs, dict) else str(hs or "")

        pos_info = ath.get("position", {})
        pos = pos_info.get("abbreviation", "F") if isinstance(pos_info, dict) else str(pos_info or "F")

        colors = NBA_TEAM_COLORS.get(team_code, {"primary": "#666666", "secondary": "#d9d9d9"})

        stats = {
            "gp":  gp,
            "pts": round(pts, 1),
            "reb": round(reb, 1),
            "ast": round(ast, 1),
            "stl": round(stl, 1),
            "blk": round(blk, 1),
            "min": round(min_pg, 1),
        }

        players.append({
            "id":       int(ath.get("id", 0)),
            "name":     ath.get("displayName", ""),
            "first":    ath.get("firstName", ""),
            "last":     ath.get("lastName", ""),
            "pos":      pos,
            "teamCode": team_code,
            "age":      ath.get("age"),
            "headshot": headshot,
            "colors":   colors,
            "score":    50,
            "raw":      nba_raw_score(stats),
            "stats":    stats,
        })

    if players:
        scores = percentile_scores(players, lambda p: p["raw"])
        for p in players:
            p["score"] = scores[p["id"]]
            del p["raw"]

    return sorted(players, key=lambda p: (-p["score"], p["name"]))


def fetch_players_for_context(season_year: int, team_by_id: dict, bracket: dict) -> tuple[list[dict], str]:
    playoff_active = _nba_importance(bracket) >= 7.0
    if playoff_active:
        print("Fetching NBA playoff player stats…")
        playoff_raw = fetch_json(
            f"{API_PLAYERS}?season={season_year}&seasontype=3&limit=500&isqualified=true"
        )
        playoff_players = build_players(playoff_raw, team_by_id, min_gp=1)
        if len(playoff_players) >= 10:
            return playoff_players, "playoffs"

    print("Fetching NBA regular-season player stats…")
    regular_raw = fetch_json(
        f"{API_PLAYERS}?season={season_year}&seasontype=2&limit=500&isqualified=true"
    )
    return build_players(regular_raw, team_by_id, min_gp=10), "regular season"


def _parse_round_conf(headline: str) -> tuple[str | None, str | None]:
    h = headline.lower()
    if "nba finals" in h:
        return "final", "final"
    if "1st round" in h or "first round" in h:
        round_key = "r1"
    elif "semi" in h:
        round_key = "r2"
    elif "final" in h or "finals" in h:
        round_key = "conf"
    else:
        return None, None
    conf = "east" if "east" in h else "west" if "west" in h else None
    return round_key, conf


def build_bracket(season_year: int) -> dict:
    empty = {"hi": None, "lo": None, "winner": None, "seriesScore": "-"}
    bracket = {
        "east":  {"r1": [], "r2": [], "conf": []},
        "west":  {"r1": [], "r2": [], "conf": []},
        "final": [empty.copy()],
    }
    try:
        # Playoffs happen in April–June of season_year (e.g. 2025-26 → April 2026)
        start = f"{season_year}0415"
        today = date.today().strftime("%Y%m%d")
        data = fetch_json(f"{API_SCOREBOARD}?seasontype=3&dates={start}-{today}&limit=300")
    except RuntimeError:
        return bracket

    # Keep the most-recent game per series (latest date = most current series state)
    series_latest: dict[frozenset, dict] = {}
    for event in data.get("events", []):
        comp = event.get("competitions", [{}])[0]
        series = comp.get("series", {})
        competitors = comp.get("competitors", [])
        teams = [c.get("team", {}).get("abbreviation", "") for c in competitors]
        if len(teams) != 2 or not all(teams) or not series:
            continue
        key = frozenset(teams)
        e_date = event.get("date", "")
        if key not in series_latest or e_date > series_latest[key]["date"]:
            notes = comp.get("notes", [])
            headline = notes[0].get("headline", "") if notes else ""
            sc = series.get("competitors", [])
            wins_by_id = {str(c.get("id")): c.get("wins", 0) for c in sc}
            team_id_map = {
                c.get("team", {}).get("abbreviation", ""): str(c.get("team", {}).get("id", ""))
                for c in competitors
            }
            series_latest[key] = {
                "date":      e_date,
                "headline":  headline,
                "teams":     teams,
                "wins_by_id": wins_by_id,
                "team_id_map": team_id_map,
                "completed": series.get("completed", False),
            }

    for s in series_latest.values():
        round_key, conf = _parse_round_conf(s["headline"])
        if round_key is None:
            continue
        t0, t1 = s["teams"][0], s["teams"][1]
        w0 = s["wins_by_id"].get(s["team_id_map"].get(t0, ""), 0)
        w1 = s["wins_by_id"].get(s["team_id_map"].get(t1, ""), 0)
        if w0 >= w1:
            hi_code, lo_code, hi_wins, lo_wins = t0, t1, w0, w1
        else:
            hi_code, lo_code, hi_wins, lo_wins = t1, t0, w1, w0
        winner = (hi_code if hi_wins > lo_wins else lo_code) if s["completed"] else None
        match_obj = {"hi": hi_code, "lo": lo_code, "winner": winner, "seriesScore": f"{hi_wins}-{lo_wins}"}
        if round_key == "final":
            bracket["final"] = [match_obj]
        elif conf in ("east", "west"):
            bracket[conf][round_key].append(match_obj)

    for side in ("east", "west"):
        bracket[side]["r1"]   = (bracket[side]["r1"]   + [empty.copy()] * 4)[:4]
        bracket[side]["r2"]   = (bracket[side]["r2"]   + [empty.copy()] * 2)[:2]
        bracket[side]["conf"] = (bracket[side]["conf"] + [empty.copy()])[:1]
    final = bracket["final"][0]
    east_winner = bracket["east"]["conf"][0].get("winner")
    west_winner = bracket["west"]["conf"][0].get("winner")
    if not final.get("hi") and east_winner and west_winner:
        bracket["final"] = [{
            "hi": west_winner,
            "lo": east_winner,
            "winner": None,
            "seriesScore": "0-0",
        }]
    return bracket


# Scaling factor: current-season percentile → all-time per-season equivalent
NBA_CURRENT_TO_ALLTIME = 0.72


def _nba_career_score(name: str, current_score: int, age: int | None) -> float:
    seasons_played = max(1, (age or 25) - 18)
    rings = PLAYER_RINGS.get(name, 0)
    est = current_score * NBA_CURRENT_TO_ALLTIME
    top3 = min(100.0, est * 1.05)
    top8 = est
    length_bonus = min(1.0, seasons_played / 15) * 15.0
    rings_bonus = rings * 5.0
    return round(min(100.0, top3 * 0.55 + top8 * 0.20 + length_bonus + rings_bonus), 1)


def _nba_prospect_score(current_score: int, age: int) -> float:
    est = current_score * NBA_CURRENT_TO_ALLTIME
    peak_boost = 1.06 if age <= 21 else 1.03 if age <= 23 else 1.0
    top3 = min(100.0, est * peak_boost)
    top8 = est
    seasons_played = max(1, age - 18)
    seasons_remaining = max(0, 38 - age)
    length_bonus = min(1.0, (seasons_played + seasons_remaining) / 15) * 15.0
    cup_proj = 8.0 if age <= 20 else 5.0 if age <= 22 else 3.0
    return round(min(97.0, top3 * 0.55 + top8 * 0.20 + length_bonus + cup_proj), 1)


def _player_needs_hint(gap: float) -> str:
    if gap <= 6:
        return "One ring + elite season could close the gap"
    if gap <= 13:
        return "1–2 more elite seasons + a championship needed"
    if gap <= 22:
        return "2–3 peak years + multiple rings needed"
    return "Multiple elite seasons + several titles needed"


def _team_needs_hint(gap: float, rings: int) -> str:
    if rings == 0:
        return "Needs at least one title + sustained dominance"
    if gap > 25:
        return "2–3 more titles + another dominant era needed"
    if gap > 14:
        return "1–2 more titles + sustained regular-season excellence"
    return "One more championship run could reach the threshold"


def _prospect_note(age: int, score: int) -> str:
    if age <= 20 and score >= 85:
        return "Historic young season — all-time ceiling is possible"
    if age <= 21 and score >= 80:
        return "Elite start to career — ceiling is very high"
    if age <= 23 and score >= 78:
        return "Among the best players of their generation"
    if score >= 80:
        return "Elite current form — needs sustained peak + rings"
    if score >= 70:
        return "Strong pedigree — leap to elite level needed"
    return "Promising young talent — long road ahead"


def build_road_to_glory(players: list[dict], teams: list[dict]) -> dict:
    p_threshold = float(STATIC_HISTORY_PLAYERS[-1]["score"])  # Tim Duncan 92.1
    t_threshold = float(STATIC_HISTORY_TEAMS[-1]["score"])     # Celtics 07-08  89.4
    team_by_code = {t["code"]: t for t in teams}

    # Player Road to Glory — top scorers + tracked stars
    top_ids = {p["id"] for p in sorted(players, key=lambda p: -p["score"])[:30]}
    star_names = {p["name"] for p in players if p["name"] in ROAD_TO_GLORY_STARS}
    candidates_p = []
    for p in players:
        if p["id"] not in top_ids and p["name"] not in star_names:
            continue
        age = p.get("age")
        cs = _nba_career_score(p["name"], p["score"], age)
        gap = round(max(0.0, p_threshold - cs), 1)
        rings = PLAYER_RINGS.get(p["name"], 0)
        candidates_p.append({
            "id":          p["id"],
            "name":        p["name"],
            "pos":         p["pos"],
            "teamCode":    p["teamCode"],
            "colors":      p["colors"],
            "age":         age,
            "careerScore": cs,
            "threshold":   p_threshold,
            "gap":         gap,
            "rings":       rings,
            "note":        _player_needs_hint(gap),
        })
    candidates_p.sort(key=lambda x: x["careerScore"], reverse=True)

    # Young prospects (≤25, score ≥50, not in historical list)
    young = []
    for p in players:
        age = p.get("age")
        if not age or age > 25 or p["score"] < 50:
            continue
        proj = _nba_prospect_score(p["score"], age)
        gap = round(max(0.0, p_threshold - proj), 1)
        young.append({
            "id":            p["id"],
            "name":          p["name"],
            "pos":           p["pos"],
            "teamCode":      p["teamCode"],
            "colors":        p["colors"],
            "age":           age,
            "currentScore":  p["score"],
            "projectedScore": proj,
            "threshold":     p_threshold,
            "gap":           gap,
            "note":          _prospect_note(age, p["score"]),
        })
    young.sort(key=lambda x: x["projectedScore"], reverse=True)

    # Team Road to Glory
    rings_value = {0: 10, 1: 22, 2: 35, 3: 48, 4: 58}
    candidates_t = []
    for era in NBA_ACTIVE_ERA_TEAMS:
        current = team_by_code.get(era["teamCode"])
        current_score = current["score"] if current else 50
        ds = round(min(97.0, rings_value.get(era["rings"], 58) + current_score * 0.55), 1)
        gap = round(t_threshold - ds, 1)
        candidates_t.append({
            "teamCode":    era["teamCode"],
            "city":        era["city"],
            "era":         era["era"],
            "rings":       era["rings"],
            "dynastyScore": ds,
            "threshold":   t_threshold,
            "gap":         max(0.0, gap),
            "note":        era["note"],
            "needs":       _team_needs_hint(gap, era["rings"]),
            "colors":      NBA_TEAM_COLORS.get(era["teamCode"], {"primary": "#666666", "secondary": "#d9d9d9"}),
        })
    candidates_t.sort(key=lambda x: x["dynastyScore"], reverse=True)

    return {
        "playerThreshold": p_threshold,
        "teamThreshold":   t_threshold,
        "players":         candidates_p[:10],
        "teams":           candidates_t[:10],
        "youngProspects":  young[:10],
    }


def annotate_player_legend_scores(players: list[dict]) -> None:
    for p in players:
        p["legendScore"] = _nba_career_score(p["name"], p["score"], p.get("age"))


def _nba_importance(bracket: dict) -> float:
    final = (bracket.get("final") or [{}])[0]
    if final.get("hi"):
        return 9.0  # NBA Finals
    for conf in ("east", "west"):
        for rnd in ("r3", "r2", "r1"):
            for s in bracket.get(conf, {}).get(rnd) or []:
                if s.get("hi"):
                    return 7.0  # Playoffs
    month = datetime.now(timezone.utc).month
    return 6.0 if (month >= 10 or month <= 6) else 3.0


def write_data(output: Path) -> None:
    # ── Capturar rankings anteriores ANTES de sobreescribir ──────────────────
    prev_players     = _prev_rank_map(output, "NBA_DATA", "PLAYERS")
    prev_rtg_players = _prev_rank_map(output, "NBA_DATA", "ROAD_TO_GLORY", "players")
    prev_rtg_young   = _prev_rank_map(output, "NBA_DATA", "ROAD_TO_GLORY", "youngProspects")
    prev_rtg_teams   = _prev_rank_map_teams(output, "NBA_DATA", "ROAD_TO_GLORY", "teams")

    print("Fetching NBA standings…")
    standings_raw = fetch_json(API_STANDINGS)
    teams, team_by_id = build_teams(standings_raw)

    now = datetime.now(timezone.utc)
    # NBA season spans two years: Oct 2025–Jun 2026 → season_year 2026
    season_year = now.year + 1 if now.month >= 10 else now.year

    print("Fetching NBA playoff bracket…")
    bracket = build_bracket(season_year)

    players, stats_scope = fetch_players_for_context(season_year, team_by_id, bracket)
    annotate_player_legend_scores(players)

    for item in STATIC_HISTORY_TEAMS:
        with_nba_colors(item)
    for item in STATIC_HISTORY_PLAYERS:
        with_nba_colors(item)

    road_to_glory = build_road_to_glory(players, teams)

    # ── Asignar prevRank ──────────────────────────────────────────────────────
    for p in sorted(players, key=lambda x: x["score"], reverse=True)[:10]:
        p["prevRank"] = prev_players.get(str(p["id"]))
    for p in road_to_glory.get("players", [])[:10]:
        p["prevRank"] = prev_rtg_players.get(str(p["id"]))
    for p in road_to_glory.get("youngProspects", [])[:10]:
        p["prevRank"] = prev_rtg_young.get(str(p["id"]))
    for t in road_to_glory.get("teams", [])[:10]:
        t["prevRank"] = prev_rtg_teams.get(f"{t.get('teamCode','')}-{t.get('era','')}")

    season_label = f"{season_year - 1}-{str(season_year)[2:]}"

    importance = _nba_importance(bracket)

    payload = {
        "TEAMS":           teams,
        "PLAYERS":         players,
        "BRACKET":         bracket,
        "HISTORY_TEAMS":   STATIC_HISTORY_TEAMS,
        "HISTORY_PLAYERS": STATIC_HISTORY_PLAYERS,
        "ROAD_TO_GLORY":   road_to_glory,
        "METHODOLOGY":     METHODOLOGY,
        "SEASON":          season_label,
        "STATS_SCOPE":     stats_scope,
        "IMPORTANCE":      importance,
        "LAST_UPDATE":     datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "SOURCE":          {"name": "ESPN API", "baseUrl": "sports.core.api.espn.com"},
    }
    text_payload = json.dumps(payload, ensure_ascii=False, indent=2)
    output.write_text(
        "// NBA Tracker - generated from ESPN public API data.\n"
        "// Run `python3 scripts/update_nba_data.py` to refresh.\n"
        f"window.NBA_DATA = {text_payload};\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate NBA Tracker data from ESPN API.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        write_data(args.output)
    except Exception as exc:
        print(f"update_nba_data.py: {exc}", file=sys.stderr)
        return 1
    print(f"Updated {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
