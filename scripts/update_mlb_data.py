#!/usr/bin/env python3
"""Fetch MLB data from ESPN public API and regenerate mlb_data.js."""

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
DEFAULT_OUTPUT = ROOT / "mlb_data.js"


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

API_STANDINGS  = "https://site.api.espn.com/apis/v2/sports/baseball/mlb/standings"
API_PLAYERS    = "https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/statistics/byathlete"
API_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
MLB_STATS_API  = "https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&season={year}&sportId=1&group={group}"

# Two-way players: name → MLB Stats API player ID
TWO_WAY_PLAYERS: dict[str, int] = {
    "Shohei Ohtani": 660271,
}

# Separate URL params for batters (uses isqualified) and pitchers (uses category=pitching)
PARAMS_BATTERS  = "season={year}&seasontype=2&limit=1000&isqualified=true"
PARAMS_PITCHERS = "season={year}&seasontype=2&limit=500&category=pitching"

# Static division assignments — MLB realignment is extremely rare
MLB_DIVISIONS: dict[str, list[str]] = {
    "AL East":    ["NYY", "BOS", "TOR", "TB",  "BAL"],
    "AL Central": ["CHW", "CLE", "DET", "KC",  "MIN"],
    "AL West":    ["HOU", "LAA", "ATH", "SEA", "TEX"],
    "NL East":    ["ATL", "MIA", "NYM", "PHI", "WSH"],
    "NL Central": ["CHC", "CIN", "MIL", "PIT", "STL"],
    "NL West":    ["LAD", "ARI", "COL", "SF",  "SD"],
}
# Reverse map: code → division name
_CODE_TO_DIV = {code: div for div, codes in MLB_DIVISIONS.items() for code in codes}

MLB_TEAM_COLORS = {
    "NYY": {"primary": "#003087", "secondary": "#e4002c"},
    "BOS": {"primary": "#bd3039", "secondary": "#0c2340"},
    "TOR": {"primary": "#134a8e", "secondary": "#e8291c"},
    "TB":  {"primary": "#092c5c", "secondary": "#8fbce6"},
    "BAL": {"primary": "#df4601", "secondary": "#000000"},
    "CHW": {"primary": "#27251f", "secondary": "#c4ced4"},
    "CLE": {"primary": "#e31937", "secondary": "#002b5c"},
    "DET": {"primary": "#0c2340", "secondary": "#fa4616"},
    "KC":  {"primary": "#004687", "secondary": "#c09a5b"},
    "MIN": {"primary": "#002b5c", "secondary": "#d31145"},
    "HOU": {"primary": "#eb6e1f", "secondary": "#002d62"},
    "LAA": {"primary": "#ba0021", "secondary": "#003263"},
    "OAK": {"primary": "#003831", "secondary": "#efb21e"},
    "ATH": {"primary": "#003831", "secondary": "#efb21e"},
    "SEA": {"primary": "#0c2c56", "secondary": "#005c5c"},
    "TEX": {"primary": "#c0111f", "secondary": "#003278"},
    "ATL": {"primary": "#ce1141", "secondary": "#13274f"},
    "MIA": {"primary": "#00a3e0", "secondary": "#ef3340"},
    "NYM": {"primary": "#002d72", "secondary": "#ff5910"},
    "PHI": {"primary": "#e81828", "secondary": "#002d72"},
    "WSH": {"primary": "#ab0003", "secondary": "#14225a"},
    "CHC": {"primary": "#0e3386", "secondary": "#cc3433"},
    "CIN": {"primary": "#c6011f", "secondary": "#000000"},
    "MIL": {"primary": "#ffc52f", "secondary": "#12284b"},
    "PIT": {"primary": "#fdb827", "secondary": "#27251f"},
    "STL": {"primary": "#c41e3a", "secondary": "#0c2340"},
    "LAD": {"primary": "#005a9c", "secondary": "#ef3e42"},
    "ARI": {"primary": "#a71930", "secondary": "#e3d4ad"},
    "COL": {"primary": "#333366", "secondary": "#c4ced4"},
    "SF":  {"primary": "#fd5a1e", "secondary": "#27251f"},
    "SD":  {"primary": "#2f241d", "secondary": "#ffc425"},
}

STATIC_HISTORY_TEAMS = [
    {"rank": 1,  "era": "1927",     "city": "New York Yankees",       "teamCode": "NYY", "conf": "AL", "titles": 1, "score": 100.0, "note": "Murderers' Row · 110-44 · Ruth/Gehrig · dominant sweep"},
    {"rank": 2,  "era": "1998",     "city": "New York Yankees",       "teamCode": "NYY", "conf": "AL", "titles": 1, "score": 98.5,  "note": "114 wins · greatest modern team · Torre/Jeter/Rivera"},
    {"rank": 3,  "era": "1975-76",  "city": "Cincinnati Reds",        "teamCode": "CIN", "conf": "NL", "titles": 2, "score": 97.0,  "note": "Big Red Machine · back-to-back WS · Rose/Bench/Morgan"},
    {"rank": 4,  "era": "1929-31",  "city": "Philadelphia Athletics",  "teamCode": "OAK", "conf": "AL", "titles": 2, "score": 95.8, "note": "Mack's dynasty · Grove/Foxx · 3 straight pennants"},
    {"rank": 5,  "era": "1955-56",  "city": "Brooklyn/LA Dodgers",    "teamCode": "LAD", "conf": "NL", "titles": 1, "score": 94.5,  "note": "Robinson/Koufax era · ended Yankees dominance"},
    {"rank": 6,  "era": "1969-71",  "city": "Baltimore Orioles",      "teamCode": "BAL", "conf": "AL", "titles": 2, "score": 93.2,  "note": "3 straight WS · Weaver/Palmer/Frank Robinson dynasty"},
    {"rank": 7,  "era": "1986",     "city": "New York Mets",          "teamCode": "NYM", "conf": "NL", "titles": 1, "score": 92.0,  "note": "108 wins · Gooden/Hernandez/Carter · legendary WS win"},
    {"rank": 8,  "era": "1988-90",  "city": "Oakland Athletics",      "teamCode": "OAK", "conf": "AL", "titles": 1, "score": 91.0,  "note": "3 straight pennants · Canseco/McGwire · one title"},
    {"rank": 9,  "era": "2004",     "city": "Boston Red Sox",         "teamCode": "BOS", "conf": "AL", "titles": 1, "score": 90.2,  "note": "Ended 86-year curse · ALCS comeback from 0-3 · Ortiz era"},
    {"rank": 10, "era": "2017",     "city": "Houston Astros",         "teamCode": "HOU", "conf": "AL", "titles": 1, "score": 89.5,  "note": "103 wins · Altuve/Springer/Correa · first WS title"},
]

STATIC_HISTORY_PLAYERS = [
    {"rank": 1,  "name": "Babe Ruth",      "pos": "RF", "teamCode": "NYY", "era": "1914-35", "tier": "A", "score": 100.0, "note": "714 HR · .342 AVG · also elite pitcher · greatest all-around player"},
    {"rank": 2,  "name": "Willie Mays",    "pos": "CF", "teamCode": "SF",  "era": "1951-73", "tier": "A", "score": 98.5,  "note": "660 HR · 12 Gold Gloves · 'The Say Hey Kid' · unmatched combination"},
    {"rank": 3,  "name": "Hank Aaron",     "pos": "RF", "teamCode": "ATL", "era": "1954-76", "tier": "A", "score": 97.8,  "note": "755 HR (career record) · 2,297 RBI · 23 seasons of consistent excellence"},
    {"rank": 4,  "name": "Ted Williams",   "pos": "LF", "teamCode": "BOS", "era": "1939-60", "tier": "A", "score": 97.0,  "note": "Last .400 hitter (.406 in 1941) · .482 OBP career · missed 5 seasons to military"},
    {"rank": 5,  "name": "Lou Gehrig",     "pos": "1B", "teamCode": "NYY", "era": "1923-39", "tier": "A", "score": 96.3,  "note": "2,130 consecutive games · .340 AVG · Iron Horse · 493 HR"},
    {"rank": 6,  "name": "Barry Bonds",    "pos": "LF", "teamCode": "SF",  "era": "1986-07", "tier": "A", "score": 95.5,  "note": "762 HR · 7 MVPs · .609 SLG · OPS+ 182 career"},
    {"rank": 7,  "name": "Mickey Mantle",  "pos": "CF", "teamCode": "NYY", "era": "1951-68", "tier": "A", "score": 94.8,  "note": "Triple Crown 1956 · 3 MVPs · switch-hitter · 536 HR"},
    {"rank": 8,  "name": "Walter Johnson", "pos": "SP", "teamCode": "WSH", "era": "1907-27", "tier": "B", "score": 94.0,  "note": "417 W · 3,509 K · Big Train · 2.17 career ERA over 21 seasons"},
    {"rank": 9,  "name": "Sandy Koufax",   "pos": "SP", "teamCode": "LAD", "era": "1955-66", "tier": "B", "score": 93.2,  "note": "4 no-hitters · 2.76 ERA · peak dominance · 3 Cy Young in 5 years"},
    {"rank": 10, "name": "Rogers Hornsby", "pos": "2B", "teamCode": "STL", "era": "1915-37", "tier": "B", "score": 92.5,  "note": ".358 career AVG (best right-handed hitter ever) · .424 in 1924 · 2 MVPs"},
]

MLB_ACTIVE_ERA_TEAMS = [
    {"teamCode": "LAD", "city": "Los Angeles Dodgers",   "era": "2017–present", "rings": 2, "note": "2020+2024 champions · Ohtani/Betts/Freeman era · highest payroll · dynasty contender"},
    {"teamCode": "HOU", "city": "Houston Astros",        "era": "2015–present", "rings": 2, "note": "2017+2022 champions · Alvarez era · model organization · sustained excellence"},
    {"teamCode": "NYY", "city": "New York Yankees",      "era": "2019–present", "rings": 0, "note": "2024 WS · Judge/Cole core · 27 all-time titles · perennial threat"},
    {"teamCode": "ATL", "city": "Atlanta Braves",        "era": "2019–present", "rings": 1, "note": "2021 champions · Acuña/Olson core · NL East powerhouse"},
    {"teamCode": "TEX", "city": "Texas Rangers",         "era": "2023–present", "rings": 1, "note": "2023 World Champions · Seager/García · historic first title"},
    {"teamCode": "PHI", "city": "Philadelphia Phillies", "era": "2022–present", "rings": 0, "note": "Back-to-back WS appearances · Harper/Nola/Turner · consistent NL contender"},
    {"teamCode": "NYM", "city": "New York Mets",         "era": "2024–present", "rings": 0, "note": "Soto/Alonso era · 2024 NLCS · rising NL East power"},
    {"teamCode": "BAL", "city": "Baltimore Orioles",     "era": "2022–present", "rings": 0, "note": "Gunnar Henderson era · homegrown rebuild · AL East rising force"},
    {"teamCode": "SEA", "city": "Seattle Mariners",      "era": "2022–present", "rings": 0, "note": "Julio Rodríguez era · pitching-first identity · long playoff drought ended"},
    {"teamCode": "SD",  "city": "San Diego Padres",      "era": "2022–present", "rings": 0, "note": "Tatis/Machado era · consistent NL West contender"},
]

WORLD_SERIES_CHAMPIONS = {
    2017: "HOU",
    2018: "BOS",
    2019: "WSH",
    2020: "LAD",
    2021: "ATL",
    2022: "HOU",
    2023: "TEX",
    2024: "LAD",
    2025: "LAD",
}

PLAYER_TEAM_WINDOWS = {
    "Mookie Betts":    [("BOS", 2014, 2019), ("LAD", 2020, None)],
    "Freddie Freeman": [("ATL", 2010, 2021), ("LAD", 2022, None)],
    "Corey Seager":    [("LAD", 2015, 2021), ("TEX", 2022, None)],
    "José Altuve":     [("HOU", 2011, None)],
    "Yordan Alvarez":  [("HOU", 2019, None)],
    "Shohei Ohtani":   [("LAD", 2024, None)],
    "Clayton Kershaw": [("LAD", 2008, None)],
    "Juan Soto":       [("WSH", 2018, 2022)],
}


def _player_rings(name: str, extra_champions: dict[int, str] | None = None) -> int:
    champions = {**WORLD_SERIES_CHAMPIONS, **(extra_champions or {})}
    total = 0
    for team_code, start, end in PLAYER_TEAM_WINDOWS.get(name, []):
        for year, champion_code in champions.items():
            if champion_code == team_code and start <= year <= (end or year):
                total += 1
    return total

ACTIVE_PLAYER_LEGACY = {
    "Mike Trout":      {"base": 89.0, "note": "3 MVPs · inner-circle peak · all-time CF bat"},
    "Clayton Kershaw": {"base": 88.0, "note": "3 Cy Young · MVP · generational pitcher"},
    "Shohei Ohtani":   {"base": 89.0, "note": "3 MVPs · two-way unicorn · 50/50 season · 2 World Series rings"},
    "Mookie Betts":    {"base": 82.0, "note": "MVP · 4 rings · elite two-way position player"},
    "Aaron Judge":     {"base": 78.0, "note": "2 MVPs · AL HR record · historic peak power"},
    "Freddie Freeman": {"base": 78.0, "note": "MVP · 3 rings · 3,000-hit track bat"},
    "José Altuve":     {"base": 74.0, "note": "MVP · 2 rings · postseason icon"},
    "Bryce Harper":    {"base": 73.0, "note": "2 MVPs · long elite run"},
    "Juan Soto":       {"base": 70.0, "note": "World Series ring · historic OBP start"},
    "Corey Seager":    {"base": 69.0, "note": "2 rings · 2 World Series MVPs"},
    "Yordan Alvarez":  {"base": 63.0, "note": "World Series ring · elite postseason bat"},
    "Paul Skenes":     {"base": 54.0, "note": "Cy Young-level early-career arm"},
}

ROAD_TO_GLORY_STARS = {
    "Shohei Ohtani",
    "Mike Trout",
    "Clayton Kershaw",
    "Aaron Judge",
    "Bryce Harper",
    "José Altuve",
    "Mookie Betts",
    "Freddie Freeman",
    "Juan Soto",
    "Yordan Alvarez",
    "Julio Rodríguez",
    "Gunnar Henderson",
    "Corbin Carroll",
    "Paul Skenes",
    "Jackson Holliday",
    "Elly De La Cruz",
}

PITCHER_POSITIONS = {"SP", "RP", "CP", "P", "LHP", "RHP"}

METHODOLOGY = {
    "player": {
        "formula": "Current MLB box-score percentile using ESPN regular-season statistics",
        "bullets": [
            "Batters: HR, RBI, AVG, SB, OPS weighted formula",
            "Pitchers: Wins, strikeouts, ERA, WHIP, innings pitched weighted formula",
            "Batters and pitchers normalized separately within their pool, then merged",
            "Scores normalized 0-100 using min-max percentile within qualified players",
            "Road to Glory career score uses current peak scaled to all-time equivalent",
        ],
    },
    "team": {
        "formula": "Win percentage and run differential blend",
        "bullets": [
            "Win% accounts for ~80% of the score — primary success metric in baseball",
            "Per-game run differential adds depth beyond raw wins",
            "Playoff bracket built from ESPN scoreboard data (postseason only)",
            "Generated data can be refreshed daily with scripts/update_mlb_data.py",
        ],
    },
    "confidence": [
        {"tier": "A", "years": "1969 -> present", "note": "Modern MLB statistical coverage (divisional era)"},
        {"tier": "B", "years": "1920 -> 1968",    "note": "Live ball era, rich statistical record"},
        {"tier": "C", "years": "1876 -> 1919",    "note": "Deadball/early era, limited game detail"},
    ],
}


def fetch_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "MLB Tracker local updater"})
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


def with_mlb_colors(item: dict, code_key: str = "teamCode") -> dict:
    code = item.get(code_key)
    item["colors"] = MLB_TEAM_COLORS.get(code, {"primary": "#666666", "secondary": "#d9d9d9"})
    return item


def build_teams(standings_data: dict) -> tuple[list[dict], dict[str, dict]]:
    teams = []
    team_by_id: dict[str, dict] = {}
    for league_data in standings_data.get("children", []):
        league_name = league_data.get("name", "")
        conf = "AL" if "American" in league_name else "NL"
        for div_data in league_data.get("children", [league_data]):
            div_name = div_data.get("name", conf)
            for entry in div_data.get("standings", {}).get("entries", []):
                t = entry["team"]
                stats = {s["name"]: s.get("value") for s in entry.get("stats", [])}
                code = t.get("abbreviation", "")
                wins   = int(stats.get("wins", 0) or 0)
                losses = int(stats.get("losses", 0) or 0)
                win_pct = float(stats.get("winPercent", 0) or 0)
                run_diff = float(stats.get("runDifferential", 0) or 0)
                runs_for = float(stats.get("runsFor", stats.get("pointsFor", 0)) or 0)
                runs_ag  = float(stats.get("runsAgainst", stats.get("pointsAgainst", 0)) or 0)
                gp = wins + losses
                rdpg = run_diff / max(1, gp)
                score = round(max(0, min(100, win_pct * 80 + rdpg * 2.5)))
                logos = t.get("logos", [])
                logo = logos[0].get("href", "") if logos else f"https://a.espncdn.com/i/teamlogos/mlb/500/{code.lower()}.png"
                team = {
                    "code":       code,
                    "city":       t.get("displayName", ""),
                    "shortName":  t.get("location", ""),
                    "commonName": t.get("name", ""),
                    "conf":       conf,
                    "div":        _CODE_TO_DIV.get(code, div_name),
                    "gp":         gp,
                    "w":          wins,
                    "l":          losses,
                    "winPct":     round(win_pct, 3),
                    "rf":         int(runs_for),
                    "ra":         int(runs_ag),
                    "rd":         int(run_diff),
                    "score":      score,
                    "logo":       logo,
                    "colors":     MLB_TEAM_COLORS.get(code, {"primary": "#666666", "secondary": "#d9d9d9"}),
                }
                teams.append(team)
                team_by_id[str(t.get("id", ""))] = team
    return sorted(teams, key=lambda t: (-t["w"], -t["rd"])), team_by_id


def _find_idx(labels: list[str], *abbrevs: str, default: int = 0) -> int:
    for abbrev in abbrevs:
        for i, l in enumerate(labels):
            if l == abbrev or l.upper() == abbrev.upper():
                return i
    return default


def build_players(batter_data: dict, pitcher_data: dict, team_by_id: dict) -> list[dict]:
    return _parse_athletes(batter_data, pitcher_data, team_by_id)


def _parse_athletes(batter_data: dict, pitcher_data: dict, team_by_id: dict) -> list[dict]:
    # ESPN MLB byathlete layout (confirmed from API):
    # batting:  [0=GP, 1=AB, 2=R, 3=H, 4=AVG, 5=2B, 6=3B, 7=HR, 8=RBI, 9=TB,
    #            10=BB, 11=K, 12=SB, 13=OBP, 14=SLG, 15=OPS, 16=WAR]
    # pitching: [0=G, 1=GS, 2=QS, 3=ERA, 4=W, 5=L, 6=SV, 7=HLD, 8=IP,
    #            9=H, 10=ER, 11=HR, 12=BB, 13=SO, 14=K9, 15=WHIP, 16=WAR]
    bi_gp = 0;  bi_ab = 1;  bi_avg = 4;  bi_hr = 7
    bi_rbi = 8; bi_sb = 12; bi_ops = 15

    pi_g = 0; pi_era = 3; pi_w = 4; pi_ip = 8; pi_so = 13; pi_whip = 15

    batters: list[dict] = []
    pitchers: list[dict] = []
    seen_pitcher_ids: set[int] = set()

    def _v(arr: list, i: int, default: float = 0.0) -> float:
        return float(arr[i]) if len(arr) > i and arr[i] is not None else default

    def _extract_base(entry: dict) -> tuple[dict, list, list, str]:
        ath = entry.get("athlete", {})
        cats = {c["name"]: c.get("values", []) for c in entry.get("categories", [])}
        bat = cats.get("batting", cats.get("hitting", cats.get("offensive", [])))
        pit = cats.get("pitching", [])
        pos_info = ath.get("position", {})
        pos = pos_info.get("abbreviation", "OF") if isinstance(pos_info, dict) else str(pos_info or "OF")
        teams_arr = ath.get("teams", [])
        if teams_arr:
            team_code = teams_arr[0].get("abbreviation", "")
        else:
            team_id = str(ath.get("teamId", ""))
            team_code = team_by_id.get(team_id, {}).get("code", "")
        hs = ath.get("headshot", {})
        headshot = hs.get("href", "") if isinstance(hs, dict) else str(hs or "")
        base = {
            "id":       int(ath.get("id", 0)),
            "name":     ath.get("displayName", ""),
            "first":    ath.get("firstName", ""),
            "last":     ath.get("lastName", ""),
            "pos":      pos,
            "teamCode": team_code,
            "age":      ath.get("age"),
            "headshot": headshot,
            "colors":   MLB_TEAM_COLORS.get(team_code, {"primary": "#666666", "secondary": "#d9d9d9"}),
            "score":    50,
        }
        return base, bat, pit, pos

    # Batters — from batting API; skip position pitchers
    for entry in batter_data.get("athletes", []):
        base, bat, pit, pos = _extract_base(entry)
        if pos in PITCHER_POSITIONS:
            continue
        bat_has_data = len(bat) > bi_ab and bat[bi_ab] is not None
        if not bat_has_data:
            continue
        ab = int(_v(bat, bi_ab))
        if ab < 20:
            continue
        hr  = _v(bat, bi_hr)
        rbi = _v(bat, bi_rbi)
        sb  = _v(bat, bi_sb)
        avg = _v(bat, bi_avg)
        ops = _v(bat, bi_ops)
        raw = hr * 3.5 + rbi * 1.2 + avg * 180 + sb * 1.8 + ops * 45
        batters.append({
            **base,
            "raw":   raw,
            "stats": {"type": "batting", "ab": ab, "hr": int(hr), "rbi": int(rbi), "avg": round(avg, 3), "sb": int(sb), "ops": round(ops, 3)},
        })

    # Pitchers — from pitching API; two-way players (e.g. Ohtani) appear here too
    for entry in pitcher_data.get("athletes", []):
        base, bat, pit, pos = _extract_base(entry)
        pid = base["id"]
        if pid in seen_pitcher_ids:
            continue
        pit_has_data = len(pit) > pi_era and pit[pi_era] is not None
        if not pit_has_data:
            continue
        g  = int(_v(pit, pi_g))
        if g < 3:
            continue
        ip = _v(pit, pi_ip)
        if ip < 5:
            continue
        w    = _v(pit, pi_w)
        era  = _v(pit, pi_era, 9.99)
        so   = _v(pit, pi_so)
        whip = _v(pit, pi_whip, 2.0)
        raw = w * 3 + so * 0.25 + (10 / max(0.5, era)) * 8 + ip * 0.05 - whip * 5
        seen_pitcher_ids.add(pid)
        pitchers.append({
            **base,
            "raw":   raw,
            "stats": {"type": "pitching", "g": g, "w": int(w), "era": round(era, 2), "ip": round(ip, 1), "so": int(so), "whip": round(whip, 2)},
        })

    b_scores = percentile_scores(batters,  lambda p: p["raw"])
    p_scores = percentile_scores(pitchers, lambda p: p["raw"])
    for p in batters:
        p["score"] = b_scores.get(p["id"], 50)
        del p["raw"]
    for p in pitchers:
        p["score"] = p_scores.get(p["id"], 50)
        del p["raw"]

    return sorted(batters + pitchers, key=lambda p: (-p["score"], p["name"]))


def _parse_round_conf_mlb(headline: str) -> tuple[str | None, str | None]:
    h = headline.lower()
    if "world series" in h:
        return "ws", "ws"
    if "american league" in h or " al " in h:
        conf = "al"
    elif "national league" in h or " nl " in h:
        conf = "nl"
    else:
        return None, None
    if "wild card" in h or "wildcard" in h:
        return "wc", conf
    if "division" in h or "alds" in h or "nlds" in h:
        return "ds", conf
    if "championship" in h or "alcs" in h or "nlcs" in h:
        return "lcs", conf
    return None, None


def build_bracket(season_year: int) -> dict:
    empty = {"hi": None, "lo": None, "winner": None, "seriesScore": "-"}
    bracket = {
        "al":  {"wc": [], "ds": [], "lcs": []},
        "nl":  {"wc": [], "ds": [], "lcs": []},
        "ws":  [empty.copy()],
    }
    try:
        # MLB postseason runs October of season_year
        start = f"{season_year}1001"
        today = date.today().strftime("%Y%m%d")
        if today < start:
            return bracket  # Regular season — no postseason data yet
        data = fetch_json(f"{API_SCOREBOARD}?seasontype=3&dates={start}-{today}&limit=300")
    except RuntimeError:
        return bracket

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
                "date":       e_date,
                "headline":   headline,
                "teams":      teams,
                "wins_by_id": wins_by_id,
                "team_id_map": team_id_map,
                "completed":  series.get("completed", False),
            }

    for s in series_latest.values():
        round_key, conf = _parse_round_conf_mlb(s["headline"])
        if round_key is None:
            continue
        t0, t1 = s["teams"][0], s["teams"][1]
        w0 = s["wins_by_id"].get(s["team_id_map"].get(t0, ""), 0)
        w1 = s["wins_by_id"].get(s["team_id_map"].get(t1, ""), 0)
        hi_code, lo_code, hi_w, lo_w = (t0, t1, w0, w1) if w0 >= w1 else (t1, t0, w1, w0)
        winner = (hi_code if hi_w > lo_w else lo_code) if s["completed"] else None
        match_obj = {"hi": hi_code, "lo": lo_code, "winner": winner, "seriesScore": f"{hi_w}-{lo_w}"}
        if round_key == "ws":
            bracket["ws"] = [match_obj]
        elif conf in ("al", "nl"):
            bracket[conf][round_key].append(match_obj)

    # Pad to fixed sizes
    for side in ("al", "nl"):
        bracket[side]["wc"]  = (bracket[side]["wc"]  + [empty.copy()] * 2)[:2]
        bracket[side]["ds"]  = (bracket[side]["ds"]  + [empty.copy()] * 2)[:2]
        bracket[side]["lcs"] = (bracket[side]["lcs"] + [empty.copy()])[:1]
    return bracket


MLB_CURRENT_TO_ALLTIME = 0.70

def _combined_player_rows(players: list[dict]) -> list[dict]:
    """Merge batting/pitching rows so two-way players get one legend profile."""
    grouped: dict[str, dict] = {}
    for p in players:
        key = p.get("name") or str(p.get("id"))
        stat_type = (p.get("stats") or {}).get("type")
        existing = grouped.get(key)
        if not existing:
            existing = {**p}
            existing["battingScore"] = None
            existing["pitchingScore"] = None
            grouped[key] = existing
        if stat_type == "batting":
            existing["battingScore"] = max(existing.get("battingScore") or 0, p.get("score", 0))
            if (p.get("score", 0) >= existing.get("score", 0)) or (existing.get("stats") or {}).get("type") != "batting":
                existing.update({k: v for k, v in p.items() if k not in {"battingScore", "pitchingScore"}})
        elif stat_type == "pitching":
            existing["pitchingScore"] = max(existing.get("pitchingScore") or 0, p.get("score", 0))
            if (p.get("score", 0) > existing.get("score", 0)) and existing.get("battingScore") is None:
                existing.update({k: v for k, v in p.items() if k not in {"battingScore", "pitchingScore"}})
    for p in grouped.values():
        b = p.get("battingScore") or 0
        q = p.get("pitchingScore") or 0
        primary = max(b, q, p.get("score", 0))
        secondary = min(b, q) if b and q else 0
        p["twoWayBonus"] = round(secondary * 0.22, 1) if secondary else 0
        p["combinedCurrentScore"] = round(min(100.0, primary + p["twoWayBonus"]), 1)
    return list(grouped.values())


def _mlb_legend_score(name: str, current_score: float, age: int | None, batting_score: float | None = None, pitching_score: float | None = None) -> float:
    """Project active players onto the same 0-100 legend scale as HISTORY_PLAYERS."""
    seasons_played = max(1, (age or 27) - 21)
    rings = _player_rings(name)
    legacy = ACTIVE_PLAYER_LEGACY.get(name, {})
    primary = max(batting_score or 0, pitching_score or 0, current_score or 0)
    secondary = min(batting_score or 0, pitching_score or 0) if batting_score and pitching_score else 0
    two_way_bonus = secondary * 0.22
    estimated_peak = min(100.0, primary + two_way_bonus)
    peak_component = estimated_peak * MLB_CURRENT_TO_ALLTIME
    longevity_bonus = min(1.0, seasons_played / 18) * 15.0
    rings_bonus = rings * 4.5
    two_way_legacy_bonus = min(8.0, two_way_bonus * 0.20)
    projection = peak_component * 0.78 + longevity_bonus + rings_bonus + two_way_legacy_bonus
    legacy_floor = float(legacy.get("base", 0))
    if legacy_floor:
        current_push = max(0.0, estimated_peak - 70.0) * 0.06
        legacy_floor = min(100.0, legacy_floor + current_push + two_way_legacy_bonus * 0.35)
    return round(min(100.0, max(projection, legacy_floor)), 1)


def _mlb_career_score(name: str, current_score: int, age: int | None) -> float:
    return _mlb_legend_score(name, current_score, age)


def _mlb_prospect_score(current_score: int, age: int) -> float:
    est = current_score * MLB_CURRENT_TO_ALLTIME
    peak_boost = 1.07 if age <= 22 else 1.04 if age <= 24 else 1.01
    top3 = min(100.0, est * peak_boost)
    top8 = est
    seasons_played = max(1, age - 21)
    seasons_remaining = max(0, 40 - age)
    length_bonus = min(1.0, (seasons_played + seasons_remaining) / 18) * 15.0
    ring_proj = 8.0 if age <= 22 else 5.0 if age <= 24 else 3.0
    return round(min(97.0, top3 * 0.55 + top8 * 0.20 + length_bonus + ring_proj), 1)


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
    if age <= 22 and score >= 85:
        return "Historic young season — all-time ceiling is possible"
    if age <= 23 and score >= 80:
        return "Elite start to career — ceiling is very high"
    if age <= 25 and score >= 75:
        return "Among the best players of their generation"
    if score >= 80:
        return "Elite current form — needs sustained peak + rings"
    if score >= 65:
        return "Strong pedigree — leap to elite level needed"
    return "Promising young talent — long road ahead"


def build_road_to_glory(players: list[dict], teams: list[dict]) -> dict:
    p_threshold = float(STATIC_HISTORY_PLAYERS[-1]["score"])  # Rogers Hornsby 92.5
    t_threshold = float(STATIC_HISTORY_TEAMS[-1]["score"])    # 2017 Astros 89.5
    team_by_code = {t["code"]: t for t in teams}
    combined_players = _combined_player_rows(players)

    top_ids = {p["id"] for p in sorted(combined_players, key=lambda p: -p["combinedCurrentScore"])[:30]}
    star_names = {p["name"] for p in combined_players if p["name"] in ROAD_TO_GLORY_STARS}
    candidates_p = []
    for p in combined_players:
        if p["id"] not in top_ids and p["name"] not in star_names:
            continue
        age = p.get("age")
        cs = _mlb_legend_score(
            p["name"],
            p["combinedCurrentScore"],
            age,
            p.get("battingScore"),
            p.get("pitchingScore"),
        )
        gap = round(max(0.0, p_threshold - cs), 1)
        rings = _player_rings(p["name"])
        candidates_p.append({
            "id":          p["id"],
            "name":        p["name"],
            "pos":         p["pos"],
            "teamCode":    p["teamCode"],
            "colors":      p["colors"],
            "age":         age,
            "careerScore": cs,
            "legendScore":  cs,
            "currentScore": p["combinedCurrentScore"],
            "battingScore": p.get("battingScore"),
            "pitchingScore": p.get("pitchingScore"),
            "twoWayBonus":  p.get("twoWayBonus", 0),
            "threshold":   p_threshold,
            "gap":         gap,
            "rings":       rings,
            "note":        ACTIVE_PLAYER_LEGACY.get(p["name"], {}).get("note") or _player_needs_hint(gap),
        })
    candidates_p.sort(key=lambda x: x["careerScore"], reverse=True)

    young = []
    for p in players:
        age = p.get("age")
        if not age or age > 25 or p["score"] < 45:
            continue
        proj = _mlb_prospect_score(p["score"], age)
        gap = round(max(0.0, p_threshold - proj), 1)
        young.append({
            "id":             p["id"],
            "name":           p["name"],
            "pos":            p["pos"],
            "teamCode":       p["teamCode"],
            "colors":         p["colors"],
            "age":            age,
            "currentScore":   p["score"],
            "projectedScore": proj,
            "threshold":      p_threshold,
            "gap":            gap,
            "note":           _prospect_note(age, p["score"]),
        })
    young.sort(key=lambda x: x["projectedScore"], reverse=True)

    rings_value = {0: 10, 1: 20, 2: 32, 3: 44, 4: 55}
    candidates_t = []
    for era in MLB_ACTIVE_ERA_TEAMS:
        current = team_by_code.get(era["teamCode"])
        current_score = current["score"] if current else 50
        ds = round(min(97.0, rings_value.get(era["rings"], 55) + current_score * 0.60), 1)
        gap = round(t_threshold - ds, 1)
        candidates_t.append({
            "teamCode":     era["teamCode"],
            "city":         era["city"],
            "era":          era["era"],
            "rings":        era["rings"],
            "dynastyScore": ds,
            "threshold":    t_threshold,
            "gap":          max(0.0, gap),
            "note":         era["note"],
            "needs":        _team_needs_hint(gap, era["rings"]),
            "colors":       MLB_TEAM_COLORS.get(era["teamCode"], {"primary": "#666666", "secondary": "#d9d9d9"}),
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
    combined_by_name = {p["name"]: p for p in _combined_player_rows(players)}
    for p in players:
        profile = combined_by_name.get(p["name"], p)
        legend_score = _mlb_legend_score(
            p["name"],
            profile.get("combinedCurrentScore", p.get("score", 0)),
            p.get("age"),
            profile.get("battingScore"),
            profile.get("pitchingScore"),
        )
        p["legendScore"] = legend_score
        p["currentScore"] = profile.get("combinedCurrentScore", p.get("score", 0))
        p["battingScore"] = profile.get("battingScore")
        p["pitchingScore"] = profile.get("pitchingScore")
        p["twoWayBonus"] = profile.get("twoWayBonus", 0)
        p["rings"] = _player_rings(p["name"])


def _add_two_way_pitchers(players: list[dict], season_year: int) -> list[dict]:
    """Fetch pitching stats from MLB Stats API for known two-way players and insert them."""
    existing_pitcher_ids = {p["id"] for p in players if p.get("stats", {}).get("type") == "pitching"}
    # Find batters that are two-way players
    batter_map = {p["name"]: p for p in players if p.get("stats", {}).get("type") == "batting"}

    new_pitchers: list[dict] = []
    for name, mlb_id in TWO_WAY_PLAYERS.items():
        if mlb_id in existing_pitcher_ids:
            continue
        batter = batter_map.get(name)
        if not batter:
            continue
        try:
            url = MLB_STATS_API.format(player_id=mlb_id, year=season_year, group="pitching")
            req = Request(url, headers={"User-Agent": "MLB Tracker local"})
            with urlopen(req, timeout=15) as resp:
                data = json.load(resp)
            splits = data.get("stats", [{}])[0].get("splits", [])
            if not splits:
                continue
            s = splits[0]["stat"]
            g    = int(s.get("gamesPitched", s.get("gamesPlayed", 0)))
            ip_raw = s.get("inningsPitched", "0")
            ip   = float(ip_raw) if ip_raw else 0.0
            if g < 3 or ip < 5:
                continue
            w    = int(s.get("wins", 0))
            era  = float(s.get("era", 9.99) or 9.99)
            so   = int(s.get("strikeOuts", 0))
            whip = float(s.get("whip", 2.0) or 2.0)
            raw  = w * 3 + so * 0.25 + (10 / max(0.5, era)) * 8 + ip * 0.05 - whip * 5
            new_pitchers.append({
                "id":       mlb_id,
                "name":     name,
                "first":    batter.get("first", ""),
                "last":     batter.get("last", ""),
                "pos":      "SP",
                "teamCode": batter["teamCode"],
                "age":      batter.get("age"),
                "headshot": batter.get("headshot", ""),
                "colors":   batter["colors"],
                "score":    50,
                "_raw":     raw,
                "stats":    {"type": "pitching", "g": g, "w": w, "era": round(era, 2), "ip": round(ip, 1), "so": so, "whip": round(whip, 2)},
            })
            print(f"  Fetched {name} pitching from MLB Stats API: {era} ERA, {ip} IP, {so} K")
        except Exception as exc:
            print(f"  Warning: could not fetch {name} pitching stats: {exc}", file=sys.stderr)

    if not new_pitchers:
        return players

    # Re-normalise pitchers including the new ones
    all_pitchers = [p for p in players if p.get("stats", {}).get("type") == "pitching"]
    batters      = [p for p in players if p.get("stats", {}).get("type") != "pitching"]

    # Recover raw values from existing pitchers' current scores for re-scaling
    # (simpler: just scale new pitchers into the existing range)
    scores = [p["score"] for p in all_pitchers]
    lo, hi = (min(scores), max(scores)) if scores else (35, 100)
    all_raw = [p.get("_raw", 0) for p in new_pitchers]
    max_raw = max(all_raw) if all_raw else 1
    for p in new_pitchers:
        norm_raw = p["_raw"] / max(1, max_raw)
        p["score"] = int(round(lo + norm_raw * (hi - lo)))
        del p["_raw"]
    all_pitchers.extend(new_pitchers)
    all_pitchers.sort(key=lambda p: (-p["score"], p["name"]))
    return sorted(batters + all_pitchers, key=lambda p: (-p["score"], p["name"]))


def _mlb_importance(bracket: dict) -> float:
    ws = (bracket.get("ws") or [{}])[0]
    if ws.get("hi"):
        return 10.0  # World Series
    for conf in ("al", "nl"):
        for rnd in ("lcs", "ds", "wc"):
            for s in bracket.get(conf, {}).get(rnd) or []:
                if s.get("hi"):
                    return 10.0  # Playoffs
    month = datetime.now(timezone.utc).month
    return 8.0 if 4 <= month <= 10 else 3.0


def write_data(output: Path) -> None:
    # ── Capturar rankings anteriores ANTES de sobreescribir ──────────────────
    # Pitchers y batters son sublistas del mismo PLAYERS array
    import re as _re2, json as _json2
    def _prev_typed_map(stat_type: str) -> "dict[str, int]":
        try:
            text = output.read_text(encoding="utf-8")
            text = _re2.sub(r"^window\.MLB_DATA\s*=\s*", "", text, flags=_re2.MULTILINE).rstrip().rstrip(";")
            items = _json2.loads(text).get("PLAYERS", [])
            filtered = [p for p in items if (p.get("stats") or {}).get("type") == stat_type]
            filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
            return {str(p.get("id") or p.get("name", "")): i + 1 for i, p in enumerate(filtered[:20])}
        except Exception:
            return {}

    prev_pitchers    = _prev_typed_map("pitching")
    prev_batters     = _prev_typed_map("batting")
    prev_rtg_players = _prev_rank_map(output, "MLB_DATA", "ROAD_TO_GLORY", "players")
    prev_rtg_young   = _prev_rank_map(output, "MLB_DATA", "ROAD_TO_GLORY", "youngProspects")
    prev_rtg_teams   = _prev_rank_map_teams(output, "MLB_DATA", "ROAD_TO_GLORY", "teams")

    print("Fetching MLB standings…")
    standings_raw = fetch_json(API_STANDINGS)
    teams, team_by_id = build_teams(standings_raw)

    now = datetime.now(timezone.utc)
    season_year = now.year  # MLB season runs April–October of same year

    print("Fetching MLB batter stats…")
    batter_raw = fetch_json(
        f"{API_PLAYERS}?{PARAMS_BATTERS.format(year=season_year)}"
    )
    print("Fetching MLB pitcher stats…")
    pitcher_raw = fetch_json(
        f"{API_PLAYERS}?{PARAMS_PITCHERS.format(year=season_year)}"
    )
    players = build_players(batter_raw, pitcher_raw, team_by_id)

    # Supplement two-way players missing from pitcher_data (e.g. Ohtani)
    players = _add_two_way_pitchers(players, season_year)
    annotate_player_legend_scores(players)

    print("Fetching MLB playoff bracket…")
    bracket = build_bracket(season_year)

    for item in STATIC_HISTORY_TEAMS:
        with_mlb_colors(item)
    for item in STATIC_HISTORY_PLAYERS:
        with_mlb_colors(item)

    road_to_glory = build_road_to_glory(players, teams)

    # ── Asignar prevRank ──────────────────────────────────────────────────────
    pitchers_top = sorted(
        [p for p in players if (p.get("stats") or {}).get("type") == "pitching"],
        key=lambda x: x["score"], reverse=True
    )[:10]
    batters_top = sorted(
        [p for p in players if (p.get("stats") or {}).get("type") == "batting"],
        key=lambda x: x["score"], reverse=True
    )[:10]
    for p in pitchers_top:
        p["prevRank"] = prev_pitchers.get(str(p.get("id") or p.get("name", "")))
    for p in batters_top:
        p["prevRank"] = prev_batters.get(str(p.get("id") or p.get("name", "")))
    for p in road_to_glory.get("players", [])[:10]:
        p["prevRank"] = prev_rtg_players.get(str(p.get("id") or p.get("name", "")))
    for p in road_to_glory.get("youngProspects", [])[:10]:
        p["prevRank"] = prev_rtg_young.get(str(p.get("id") or p.get("name", "")))
    for t in road_to_glory.get("teams", [])[:10]:
        t["prevRank"] = prev_rtg_teams.get(f"{t.get('teamCode','')}-{t.get('era','')}")

    importance = _mlb_importance(bracket)

    payload = {
        "TEAMS":           teams,
        "PLAYERS":         players,
        "BRACKET":         bracket,
        "DIVISIONS":       list(MLB_DIVISIONS.keys()),
        "HISTORY_TEAMS":   STATIC_HISTORY_TEAMS,
        "HISTORY_PLAYERS": STATIC_HISTORY_PLAYERS,
        "ROAD_TO_GLORY":   road_to_glory,
        "METHODOLOGY":     METHODOLOGY,
        "SEASON":          str(season_year),
        "IMPORTANCE":      importance,
        "LAST_UPDATE":     datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "SOURCE":          {"name": "ESPN API", "baseUrl": "sports.core.api.espn.com"},
    }
    text_payload = json.dumps(payload, ensure_ascii=False, indent=2)
    output.write_text(
        "// MLB Tracker - generated from ESPN public API data.\n"
        "// Run `python3 scripts/update_mlb_data.py` to refresh.\n"
        f"window.MLB_DATA = {text_payload};\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate MLB Tracker data from ESPN API.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        write_data(args.output)
    except Exception as exc:
        print(f"update_mlb_data.py: {exc}", file=sys.stderr)
        return 1
    print(f"Updated {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
