#!/usr/bin/env python3
"""Fetch real NHL data and regenerate data.js for the tracker."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API = "https://api-web.nhle.com/v1"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data.js"


# ── Prev-rank helper ─────────────────────────────────────────────────────────

def _prev_rank_map(filepath: Path, js_var: str, *path: str) -> "dict[str, int]":
    """Read the existing JS data file and return {str(id_key): 1-based-rank}.

    *path: sequence of dict keys to navigate from root to the list, e.g.
        _prev_rank_map(fp, "NHL_DATA", "PLAYERS")
        _prev_rank_map(fp, "NHL_DATA", "ROAD_TO_GLORY", "players")
    Uses 'id' as the key; falls back to 'name'.
    """
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
        for i, item in enumerate(obj[:20]):          # track up to top-20
            k = str(item.get("id") or item.get("name", ""))
            if k:
                result[k] = i + 1
        return result
    except Exception:
        return {}


def _prev_rank_map_teams(filepath: Path, js_var: str, *path: str) -> "dict[str, int]":
    """Like _prev_rank_map but uses 'teamCode-era' as key (for RTG team lists)."""
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

DIVISIONS = {
    "A": "Atlantic",
    "M": "Metro",
    "C": "Central",
    "P": "Pacific",
}

TEAM_COLORS = {
    "ANA": {"primary": "#f47a38", "secondary": "#b9975b"},
    "BOS": {"primary": "#ffb81c", "secondary": "#111111"},
    "BUF": {"primary": "#003087", "secondary": "#ffb81c"},
    "CAR": {"primary": "#cc0000", "secondary": "#111111"},
    "CBJ": {"primary": "#002654", "secondary": "#ce1126"},
    "CGY": {"primary": "#c8102e", "secondary": "#f1be48"},
    "CHI": {"primary": "#cf0a2c", "secondary": "#111111"},
    "COL": {"primary": "#6f263d", "secondary": "#236192"},
    "DAL": {"primary": "#006847", "secondary": "#8f8f8c"},
    "DET": {"primary": "#ce1126", "secondary": "#ffffff"},
    "EDM": {"primary": "#041e42", "secondary": "#ff4c00"},
    "FLA": {"primary": "#041e42", "secondary": "#c8102e"},
    "LAK": {"primary": "#111111", "secondary": "#a2aaad"},
    "MIN": {"primary": "#154734", "secondary": "#a6192e"},
    "MTL": {"primary": "#af1e2d", "secondary": "#192168"},
    "NJD": {"primary": "#ce1126", "secondary": "#111111"},
    "NSH": {"primary": "#ffb81c", "secondary": "#041e42"},
    "NYI": {"primary": "#00539b", "secondary": "#f47d30"},
    "NYR": {"primary": "#0038a8", "secondary": "#ce1126"},
    "OTT": {"primary": "#c52032", "secondary": "#c2912c"},
    "PHI": {"primary": "#f74902", "secondary": "#111111"},
    "PIT": {"primary": "#111111", "secondary": "#cfc493"},
    "SEA": {"primary": "#001628", "secondary": "#99d9d9"},
    "SJS": {"primary": "#006d75", "secondary": "#ea7200"},
    "STL": {"primary": "#002f87", "secondary": "#fcb514"},
    "TBL": {"primary": "#002868", "secondary": "#ffffff"},
    "TOR": {"primary": "#00205b", "secondary": "#ffffff"},
    "UTA": {"primary": "#69b3e7", "secondary": "#010101"},
    "VAN": {"primary": "#00205b", "secondary": "#00843d"},
    "VGK": {"primary": "#b4975a", "secondary": "#333f48"},
    "WPG": {"primary": "#041e42", "secondary": "#7b303e"},
    "WSH": {"primary": "#041e42", "secondary": "#c8102e"},
    "QUE": {"primary": "#005eb8", "secondary": "#c8102e"},
}

COUNTRIES = {
    "CAN": "Canada",
    "USA": "United States",
    "SWE": "Sweden",
    "FIN": "Finland",
    "CZE": "Czechia",
    "RUS": "Russia",
    "SVK": "Slovakia",
    "DEU": "Germany",
    "CHE": "Switzerland",
    "DNK": "Denmark",
    "NOR": "Norway",
    "FRA": "France",
    "AUT": "Austria",
    "LVA": "Latvia",
    "BLR": "Belarus",
}

LEGEND_IDS = {
    8447400: "EDM",  # Wayne Gretzky
    8448782: "PIT",  # Mario Lemieux
    8450070: "BOS",  # Bobby Orr
    8448000: "DET",  # Gordie Howe
    8471675: "PIT",  # Sidney Crosby
    8471214: "WSH",  # Alex Ovechkin
    8457063: "DET",  # Nicklas Lidstrom
    8448208: "PIT",  # Jaromir Jagr
    8451033: "COL",  # Patrick Roy
    8447687: "BUF",  # Dominik Hasek
}

# Active stars always fetched for PLAYER_COMPARISONS regardless of current-season rank
ROAD_TO_GLORY_PLAYER_IDS = {
    8478402: "EDM",  # Connor McDavid
    8477492: "COL",  # Nathan MacKinnon
    8476453: "TBL",  # Nikita Kucherov
    8480069: "COL",  # Cale Makar
    8477934: "EDM",  # Leon Draisaitl
    8484144: "CHI",  # Connor Bedard
}

# Known Stanley Cup wins for active/recent players
PLAYER_CUPS = {
    8471675: 3,  # Sidney Crosby — 2009, 2016, 2017
    8471214: 1,  # Alex Ovechkin — 2018
    8477492: 1,  # Nathan MacKinnon — 2022
    8476453: 2,  # Nikita Kucherov — 2020, 2021
    8480069: 1,  # Cale Makar — 2022
    8476346: 2,  # Brayden Point — 2020, 2021
}

# Current-era franchises building toward all-time dynasty status
ACTIVE_ERA_TEAMS = [
    {"teamCode": "COL", "city": "Colorado Avalanche", "era": "2020–present", "cups": 1, "note": "2022 Cup · MacKinnon era"},
    {"teamCode": "FLA", "city": "Florida Panthers", "era": "2022–present", "cups": 1, "note": "2024 Cup · 2022–present contender"},
    {"teamCode": "VGK", "city": "Vegas Golden Knights", "era": "2018–present", "cups": 2, "note": "2023 & 2025 Cups · fastest expansion dynasty · 2026 Finals"},
    {"teamCode": "STL", "city": "St. Louis Blues", "era": "2017–present", "cups": 1, "note": "2019 Cup · first in franchise history"},
    {"teamCode": "EDM", "city": "Edmonton Oilers", "era": "2021–present", "cups": 0, "note": "McDavid era · 2024 & 2025 Stanley Cup Finals"},
    {"teamCode": "CAR", "city": "Carolina Hurricanes", "era": "2019–present", "cups": 0, "note": "6 straight playoff runs · no Cup yet"},
    {"teamCode": "DAL", "city": "Dallas Stars", "era": "2022–present", "cups": 0, "note": "Back-to-back Conference Finals"},
    {"teamCode": "BOS", "city": "Boston Bruins", "era": "2019–present", "cups": 0, "note": "Consistent 100+ point seasons"},
    {"teamCode": "NYR", "city": "New York Rangers", "era": "2022–present", "cups": 0, "note": "2024 Conference Finals · Panarin–Fox era"},
    {"teamCode": "MIN", "city": "Minnesota Wild", "era": "2020–present", "cups": 0, "note": "5 straight playoffs · Kaprizov era"},
]

STATIC_HISTORY_TEAMS = [
    {"rank": 1, "era": "1976-79", "city": "Montreal Canadiens", "teamCode": "MTL", "country": "Canada", "conf": "WHA/NHL expansion era", "titles": 4, "score": 99.0, "conf_tier": "B"},
    {"rank": 2, "era": "1983-88", "city": "Edmonton Oilers", "teamCode": "EDM", "country": "Canada", "conf": "Smythe", "titles": 4, "score": 97.8, "conf_tier": "A"},
    {"rank": 3, "era": "1980-83", "city": "New York Islanders", "teamCode": "NYI", "country": "United States", "conf": "Patrick", "titles": 4, "score": 96.5, "conf_tier": "A"},
    {"rank": 4, "era": "1946-60", "city": "Montreal Canadiens", "teamCode": "MTL", "country": "Canada", "conf": "Original Six", "titles": 10, "score": 95.4, "conf_tier": "C"},
    {"rank": 5, "era": "1996-02", "city": "Detroit Red Wings", "teamCode": "DET", "country": "United States", "conf": "Central", "titles": 3, "score": 94.3, "conf_tier": "A"},
    {"rank": 6, "era": "2009-17", "city": "Chicago Blackhawks", "teamCode": "CHI", "country": "United States", "conf": "Central", "titles": 3, "score": 92.4, "conf_tier": "A"},
    {"rank": 7, "era": "2019-22", "city": "Tampa Bay Lightning", "teamCode": "TBL", "country": "United States", "conf": "Atlantic", "titles": 2, "score": 91.8, "conf_tier": "A"},
    {"rank": 8, "era": "1969-72", "city": "Boston Bruins", "teamCode": "BOS", "country": "United States", "conf": "East", "titles": 2, "score": 91.1, "conf_tier": "B"},
    {"rank": 9, "era": "1951-55", "city": "Detroit Red Wings", "teamCode": "DET", "country": "United States", "conf": "Original Six", "titles": 4, "score": 90.5, "conf_tier": "C"},
    {"rank": 10, "era": "1991-92", "city": "Pittsburgh Penguins", "teamCode": "PIT", "country": "United States", "conf": "Patrick", "titles": 2, "score": 89.7, "conf_tier": "A"},
]

STATIC_HISTORY_PLAYERS = [
    {"rank": 1, "id": 8447400, "name": "Wayne Gretzky", "pos": "C", "teamCode": "EDM", "country": "Canada", "era": "1979-99", "tier": "A", "score": 100.0, "note": "NHL career leader in points"},
    {"rank": 2, "id": 8448782, "name": "Mario Lemieux", "pos": "C", "teamCode": "PIT", "country": "Canada", "era": "1984-06", "tier": "A", "score": 98.6, "note": "Highest peak scoring rate of the modern era"},
    {"rank": 3, "id": 8450070, "name": "Bobby Orr", "pos": "D", "teamCode": "BOS", "country": "Canada", "era": "1966-78", "tier": "B", "score": 98.1, "note": "Transformational offensive defenseman"},
    {"rank": 4, "id": 8448000, "name": "Gordie Howe", "pos": "RW", "teamCode": "DET", "country": "Canada", "era": "1946-80", "tier": "C", "score": 97.4, "note": "Elite longevity and scoring"},
    {"rank": 5, "id": 8471675, "name": "Sidney Crosby", "pos": "C", "teamCode": "PIT", "country": "Canada", "era": "2005-present", "tier": "A", "score": 96.2, "note": "Era-adjusted two-way center"},
    {"rank": 6, "id": 8471214, "name": "Alex Ovechkin", "pos": "LW", "teamCode": "WSH", "country": "Russia", "era": "2005-present", "tier": "A", "score": 95.8, "note": "All-time goals benchmark"},
    {"rank": 7, "id": 8457063, "name": "Nicklas Lidstrom", "pos": "D", "teamCode": "DET", "country": "Sweden", "era": "1991-12", "tier": "A", "score": 94.5, "note": "Modern defense standard"},
    {"rank": 8, "id": 8448208, "name": "Jaromir Jagr", "pos": "RW", "teamCode": "PIT", "country": "Czechia", "era": "1990-18", "tier": "A", "score": 94.0, "note": "NHL career points leader among European players"},
    {"rank": 9, "id": 8451033, "name": "Patrick Roy", "pos": "G", "teamCode": "COL", "country": "Canada", "era": "1984-03", "tier": "A", "score": 93.4, "note": "Playoff and peak goaltending resume"},
    {"rank": 10, "id": 8447687, "name": "Dominik Hasek", "pos": "G", "teamCode": "BUF", "country": "Czechia", "era": "1990-08", "tier": "A", "score": 93.1, "note": "Save percentage dominance at peak"},
]

METHODOLOGY = {
    "player": {
        "formula": "Current NHL box-score percentile by position using live skater and goalie statistics",
        "bullets": [
            "Skaters: points, goals, assists, plus-minus, shots, games played and average ice time",
            "Goalies: save percentage, goals-against average, wins, starts and shutouts",
            "Scores are normalized within forwards, defensemen and goalies, then scaled 0-100",
            "Player comparison seasons use NHL regular-season totals and age on October 1 of that season",
            "This is a transparent tracker score, not an official NHL metric",
        ],
    },
    "team": {
        "formula": "Blend of current standings strength and roster player scores",
        "bullets": [
            "Standings inputs include points percentage, goal differential and regulation wins",
            "Roster input uses the average of the top skaters and goalies available from club stats",
            "Playoff bracket is pulled from the NHL playoff bracket endpoint when available",
            "Generated data can be refreshed daily with scripts/update_data.py",
        ],
    },
    "confidence": [
        {"tier": "A", "years": "1980 -> present", "note": "Modern NHL statistical coverage"},
        {"tier": "B", "years": "1967 -> 1979", "note": "Expansion era, less complete event detail"},
        {"tier": "C", "years": "1942 -> 1966", "note": "Original Six era, mostly box-score context"},
        {"tier": "D", "years": "1917 -> 1941", "note": "Sparse early-era context"},
    ],
}


def fetch_json(path: str) -> dict:
    url = path if path.startswith("http") else f"{API}{path}"
    req = Request(url, headers={"User-Agent": "NHL Tracker local updater"})
    try:
        with urlopen(req, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"{url} returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc


def text(value: object, fallback: str = "") -> str:
    if isinstance(value, dict):
        return str(value.get("default") or fallback)
    return str(value or fallback)


def season_label(season_id: int | str) -> str:
    raw = str(season_id)
    return f"{raw[:4]}-{raw[6:]}"


def age_from_birthdate(birthdate: str | None) -> int | None:
    if not birthdate:
        return None
    born = date.fromisoformat(birthdate)
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def age_on_october_first(birthdate: str | None, season: int | str) -> int | None:
    if not birthdate:
        return None
    born = date.fromisoformat(birthdate)
    target = date(int(str(season)[:4]), 10, 1)
    return target.year - born.year - ((target.month, target.day) < (born.month, born.day))


def position_code(code: str) -> str:
    return {"L": "LW", "R": "RW"}.get(code, code)


def country_name(code: str | None) -> str:
    if not code:
        return ""
    return COUNTRIES.get(code, code)


def with_colors(item: dict, code_key: str = "teamCode") -> dict:
    code = item.get(code_key)
    item["colors"] = TEAM_COLORS.get(code, {"primary": "#666666", "secondary": "#d9d9d9"})
    return item


def percentile_scores(items: list[dict], value_fn) -> dict[int, int]:
    values = [(item["id"], value_fn(item)) for item in items]
    if not values:
        return {}
    nums = [value for _, value in values]
    lo = min(nums)
    hi = max(nums)
    if math.isclose(lo, hi):
        return {item_id: 65 for item_id, _ in values}
    return {
        item_id: int(round(35 + ((value - lo) / (hi - lo)) * 65))
        for item_id, value in values
    }


def build_teams(standings: list[dict]) -> list[dict]:
    teams = []
    for row in standings:
        gd = int(row.get("goalDifferential") or 0)
        pct = float(row.get("pointPctg") or 0)
        reg_wins = int(row.get("regulationWins") or 0)
        score = round(max(0, min(100, pct * 86 + gd * 0.15 + reg_wins * 0.22)))
        teams.append({
            "code": text(row.get("teamAbbrev")),
            "city": text(row.get("teamName")),
            "shortName": text(row.get("placeName"), text(row.get("teamName"))),
            "commonName": text(row.get("teamCommonName")),
            "conf": text(row.get("conferenceAbbrev")),
            "div": DIVISIONS.get(text(row.get("divisionAbbrev")), text(row.get("divisionName"))),
            "gp": int(row.get("gamesPlayed") or 0),
            "w": int(row.get("wins") or 0),
            "l": int(row.get("losses") or 0),
            "ot": int(row.get("otLosses") or 0),
            "pts": int(row.get("points") or 0),
            "gf": int(row.get("goalFor") or 0),
            "ga": int(row.get("goalAgainst") or 0),
            "gd": gd,
            "score": score,
            "logo": row.get("teamLogo"),
            "colors": TEAM_COLORS.get(text(row.get("teamAbbrev")), {"primary": "#666666", "secondary": "#d9d9d9"}),
        })
    return sorted(teams, key=lambda t: (-t["pts"], -t["gd"], t["city"]))


def skater_score(player: dict) -> float:
    gp = max(1, player["stats"]["gp"])
    points = player["stats"]["p"]
    goals = player["stats"]["g"]
    assists = player["stats"]["a"]
    plus_minus = player["stats"].get("pm", 0)
    toi = player["stats"].get("toi", 0)
    shots = player["stats"].get("shots", 0)
    return (points / gp) * 48 + (goals / gp) * 16 + (assists / gp) * 8 + plus_minus * 0.18 + toi * 1.4 + shots / gp


def goalie_score(player: dict) -> float:
    stats = player["stats"]
    gp = max(1, stats["gp"])
    svpct = stats.get("svpct") or 0
    gaa = stats.get("gaa") or 4
    # Regress SV% toward league average for small samples (full weight at 25+ GP)
    reliability = min(1.0, gp / 25)
    adj_svpct = svpct * reliability + 0.910 * (1 - reliability)
    adj_gaa = gaa * reliability + 3.0 * (1 - reliability)
    return (adj_svpct - 0.86) * 1100 - adj_gaa * 8 + stats.get("w", 0) * 0.9 + stats.get("so", 0) * 3 + gp * 0.15


def toi_minutes(value: str | None) -> float:
    if not value or ":" not in value:
        return 0.0
    minutes, seconds = value.split(":", 1)
    return int(minutes) + int(seconds) / 60


def season_raw_score(row: dict, pos: str) -> float:
    gp = max(1, int(row.get("gamesPlayed") or 0))
    if pos == "G":
        svpct = float(row.get("savePctg") or row.get("savePercentage") or 0)
        gaa = float(row.get("goalsAgainstAverage") or row.get("gaa") or 3.5)
        return (svpct - 0.86) * 900 - gaa * 7 + int(row.get("wins") or 0) * 1.7 + int(row.get("shutouts") or 0) * 3 + gp * 0.35
    points = int(row.get("points") or 0)
    goals = int(row.get("goals") or 0)
    assists = int(row.get("assists") or 0)
    plus_minus = int(row.get("plusMinus") or 0)
    shots = int(row.get("shots") or 0)
    toi = toi_minutes(row.get("avgToi"))
    return (points / gp) * 55 + (goals / gp) * 15 + (assists / gp) * 8 + (plus_minus / gp) * 12 + (shots / gp) * 1.2 + toi * 0.5


def _young_prospect_ids(players: list[dict]) -> list[int]:
    candidates = [
        p for p in players
        if p["pos"] != "G" and p.get("age") and p["age"] <= 25 and p["score"] >= 50
    ]
    candidates.sort(key=lambda p: p["score"], reverse=True)
    return [p["id"] for p in candidates[:15]]


def build_player_comparisons(players: list[dict], extra_ids: list[int] | None = None) -> list[dict]:
    current_ids = [p["id"] for p in sorted((p for p in players if p["pos"] != "G"), key=lambda p: p["score"], reverse=True)[:36]]
    wanted_ids = list(dict.fromkeys(current_ids + list(LEGEND_IDS.keys()) + list(ROAD_TO_GLORY_PLAYER_IDS.keys()) + (extra_ids or [])))
    comparisons = []
    all_seasons = []

    for player_id in wanted_ids:
        try:
            landing = fetch_json(f"/player/{player_id}/landing")
        except RuntimeError:
            continue
        first = text(landing.get("firstName"))
        last = text(landing.get("lastName"))
        pos = position_code(landing.get("position") or "")
        team_code = landing.get("currentTeamAbbrev") or LEGEND_IDS.get(player_id) or ROAD_TO_GLORY_PLAYER_IDS.get(player_id)
        if not team_code:
            featured = landing.get("featuredStats", {}).get("regularSeason", {}).get("subSeason", {})
            team_code = featured.get("teamAbbrev")
        seasons = []
        for row in landing.get("seasonTotals", []):
            if row.get("leagueAbbrev") != "NHL" or int(row.get("gameTypeId") or 0) != 2:
                continue
            gp = int(row.get("gamesPlayed") or 0)
            if gp < 10:
                continue
            season = int(row.get("season"))
            item = {
                "season": season_label(season),
                "seasonId": season,
                "age": age_on_october_first(landing.get("birthDate"), season),
                "team": text(row.get("teamCommonName"), text(row.get("teamName"))),
                "teamName": text(row.get("teamName")),
                "gp": gp,
                "g": int(row.get("goals") or 0),
                "a": int(row.get("assists") or 0),
                "p": int(row.get("points") or 0),
                "pm": int(row.get("plusMinus") or 0),
                "raw": season_raw_score(row, pos),
                "score": 50,
            }
            seasons.append(item)
            all_seasons.append(item)
        if not seasons:
            continue
        current_match = next((p for p in players if p["id"] == player_id), None)
        comparison = {
            "id": player_id,
            "name": f"{first} {last}".strip(),
            "pos": pos,
            "active": bool(landing.get("isActive")),
            "teamCode": team_code,
            "country": country_name(landing.get("birthCountry")),
            "birthCountry": landing.get("birthCountry"),
            "birthDate": landing.get("birthDate"),
            "headshot": landing.get("headshot"),
            "currentScore": current_match.get("score") if current_match else None,
            "legendScore": next((p["score"] for p in STATIC_HISTORY_PLAYERS if p.get("id") == player_id), None),
            "colors": TEAM_COLORS.get(team_code, {"primary": "#666666", "secondary": "#d9d9d9"}),
            "seasons": seasons,
        }
        comparisons.append(comparison)

    if all_seasons:
        raw_values = [s["raw"] for s in all_seasons]
        lo = min(raw_values)
        hi = max(raw_values)
        for season in all_seasons:
            season["score"] = 65 if math.isclose(lo, hi) else round(35 + ((season["raw"] - lo) / (hi - lo)) * 65)
            del season["raw"]

    for comparison in comparisons:
        comparison["bestSeason"] = max(comparison["seasons"], key=lambda s: s["score"])
        comparison["age22Season"] = next((s for s in comparison["seasons"] if s["age"] == 22), None)

    return sorted(comparisons, key=lambda p: (-(p["age22Season"] or p["bestSeason"])["score"], p["name"]))


def _fetch_club_stats(code: str, season_id: int | str | None, game_type: int) -> dict:
    if season_id:
        try:
            return fetch_json(f"/club-stats/{code}/{season_id}/{game_type}")
        except RuntimeError:
            pass
    if game_type == 2:
        return fetch_json(f"/club-stats/{code}/now")
    return {}


def build_players(teams: list[dict], season_id: int | str | None = None) -> list[dict]:
    players = []
    next_id = 1
    # Collect playoff stats keyed by player id for merging after scoring
    po_by_id: dict[int, dict] = {}

    for team in teams:
        roster_meta = {}
        try:
            roster = fetch_json(f"/roster/{team['code']}/current")
            for group in ("forwards", "defensemen", "goalies"):
                for person in roster.get(group, []):
                    roster_meta[int(person.get("id"))] = person
        except RuntimeError:
            roster_meta = {}

        club = _fetch_club_stats(team["code"], season_id, 2)

        # Stash playoff stats for later merging
        club_po = _fetch_club_stats(team["code"], season_id, 3)
        for r in club_po.get("skaters", []):
            pid = int(r.get("playerId") or 0)
            if pid:
                po_by_id[pid] = {
                    "gp": int(r.get("gamesPlayed") or 0),
                    "g":  int(r.get("goals") or 0),
                    "a":  int(r.get("assists") or 0),
                    "p":  int(r.get("points") or 0),
                    "pm": int(r.get("plusMinus") or 0),
                }
        for r in club_po.get("goalies", []):
            pid = int(r.get("playerId") or 0)
            if pid:
                po_by_id[pid] = {
                    "gp":    int(r.get("gamesPlayed") or 0),
                    "w":     int(r.get("wins") or 0),
                    "so":    int(r.get("shutouts") or 0),
                    "svpct": float(r.get("savePercentage") or 0),
                    "gaa":   float(r.get("goalsAgainstAverage") or 0),
                }

        for raw in club.get("skaters", []):
            gp = int(raw.get("gamesPlayed") or 0)
            if gp <= 0:
                continue
            pos = position_code(raw.get("positionCode") or "")
            first = text(raw.get("firstName"))
            last = text(raw.get("lastName"))
            points = int(raw.get("points") or 0)
            meta = roster_meta.get(int(raw.get("playerId") or 0), {})
            player = {
                "id": int(raw.get("playerId") or next_id),
                "first": first,
                "last": last,
                "name": f"{first} {last}".strip(),
                "pos": pos,
                "teamCode": team["code"],
                "age": age_from_birthdate(meta.get("birthDate")),
                "country": country_name(meta.get("birthCountry")),
                "birthCountry": meta.get("birthCountry"),
                "colors": team["colors"],
                "headshot": raw.get("headshot"),
                "score": 50,
                "stats": {
                    "gp": gp,
                    "g": int(raw.get("goals") or 0),
                    "a": int(raw.get("assists") or 0),
                    "p": points,
                    "pm": int(raw.get("plusMinus") or 0),
                    "toi": round(float(raw.get("avgTimeOnIcePerGame") or 0) / 60, 1),
                    "shots": int(raw.get("shots") or 0),
                },
            }
            player["trajectory"] = [
                max(20, round(45 + points * 0.18 - 8)),
                max(20, round(45 + points * 0.18 - 5)),
                max(20, round(45 + points * 0.18 - 3)),
                max(20, round(45 + points * 0.18 - 1)),
                max(20, round(45 + points * 0.18)),
            ]
            players.append(player)
            next_id += 1

        for raw in club.get("goalies", []):
            gp = int(raw.get("gamesPlayed") or 0)
            if gp <= 0:
                continue
            first = text(raw.get("firstName"))
            last = text(raw.get("lastName"))
            svpct = float(raw.get("savePercentage") or 0)
            gaa = float(raw.get("goalsAgainstAverage") or 0)
            meta = roster_meta.get(int(raw.get("playerId") or 0), {})
            player = {
                "id": int(raw.get("playerId") or next_id),
                "first": first,
                "last": last,
                "name": f"{first} {last}".strip(),
                "pos": "G",
                "teamCode": team["code"],
                "age": age_from_birthdate(meta.get("birthDate")),
                "country": country_name(meta.get("birthCountry")),
                "birthCountry": meta.get("birthCountry"),
                "colors": team["colors"],
                "headshot": raw.get("headshot"),
                "score": 50,
                "stats": {
                    "gp": gp,
                    "w": int(raw.get("wins") or 0),
                    "svpct": round(svpct, 3),
                    "gaa": round(gaa, 2),
                    "so": int(raw.get("shutouts") or 0),
                },
            }
            player["trajectory"] = [50, 54, 57, 60, 62]
            players.append(player)
            next_id += 1

    for group in (
        [p for p in players if p["pos"] in ("C", "LW", "RW")],
        [p for p in players if p["pos"] == "D"],
        [p for p in players if p["pos"] == "G"],
    ):
        scores = percentile_scores(group, goalie_score if group and group[0]["pos"] == "G" else skater_score)
        for player in group:
            player["score"] = scores[player["id"]]
            player["trajectory"][-1] = player["score"]

    # Goalies normalize within a smaller pool (97) so their 35–100 range sits ~30pts
    # above skaters. Scale them down so an elite starter (~84) ≈ strong top-6 forward.
    for player in players:
        if player["pos"] == "G":
            player["score"] = max(35, round(35 + (player["score"] - 35) * 0.72))
            player["trajectory"][-1] = player["score"]

    # Merge playoff stats after scoring so the score formula stays RS-only
    for player in players:
        po = po_by_id.get(player["id"])
        if not po or po.get("gp", 0) == 0:
            continue
        po_gp = po["gp"]
        player["stats"]["gp_po"] = po_gp
        if player["pos"] == "G":
            rs_gp = player["stats"]["gp"]
            total_gp = rs_gp + po_gp
            player["stats"]["gp"] = total_gp
            player["stats"]["w"]  = player["stats"]["w"] + po.get("w", 0)
            player["stats"]["so"] = player["stats"]["so"] + po.get("so", 0)
            if total_gp > 0:
                player["stats"]["svpct"] = round(
                    (player["stats"]["svpct"] * rs_gp + po.get("svpct", 0) * po_gp) / total_gp, 3
                )
                player["stats"]["gaa"] = round(
                    (player["stats"]["gaa"] * rs_gp + po.get("gaa", 0) * po_gp) / total_gp, 2
                )
        else:
            player["stats"]["gp"] = player["stats"]["gp"] + po_gp
            player["stats"]["g"]  = player["stats"]["g"]  + po.get("g",  0)
            player["stats"]["a"]  = player["stats"]["a"]  + po.get("a",  0)
            player["stats"]["p"]  = player["stats"]["p"]  + po.get("p",  0)
            player["stats"]["pm"] = player["stats"]["pm"] + po.get("pm", 0)

    return sorted(players, key=lambda p: (-p["score"], p["name"]))


def add_roster_strength(teams: list[dict], players: list[dict]) -> None:
    by_team = {team["code"]: [] for team in teams}
    for player in players:
        by_team.setdefault(player["teamCode"], []).append(player)
    for team in teams:
        roster = by_team.get(team["code"], [])
        skaters = sorted((p for p in roster if p["pos"] != "G"), key=lambda p: p["score"], reverse=True)[:18]
        goalies = sorted((p for p in roster if p["pos"] == "G"), key=lambda p: p["score"], reverse=True)[:2]
        roster_score = 0
        if skaters or goalies:
            roster_score = sum(p["score"] for p in skaters + goalies) / max(1, len(skaters) + len(goalies))
        team["score"] = round(team["score"] * 0.58 + roster_score * 0.42)


def series_obj(raw: dict) -> dict:
    hi = raw.get("topSeedTeam") or {}
    lo = raw.get("bottomSeedTeam") or {}
    hi_code = hi.get("abbrev")
    lo_code = lo.get("abbrev")
    winner_id = raw.get("winningTeamId")
    winner = None
    if winner_id and hi.get("id") == winner_id:
        winner = hi_code
    elif winner_id and lo.get("id") == winner_id:
        winner = lo_code
    return {
        "hi": hi_code,
        "lo": lo_code,
        "winner": winner,
        "seriesScore": f"{int(raw.get('topSeedWins') or 0)}-{int(raw.get('bottomSeedWins') or 0)}",
    }


def build_bracket(season_id: int | str) -> dict:
    empty = {"hi": None, "lo": None, "winner": None, "seriesScore": "-"}
    bracket = {
        "east": {"r1": [], "r2": [], "conf": []},
        "west": {"r1": [], "r2": [], "conf": []},
        "final": [empty.copy()],
    }
    try:
        season = str(season_id)
        playoff_year = season[4:] if len(season) >= 8 else season[:4]
        data = fetch_json(f"/playoff-bracket/{playoff_year}")
    except RuntimeError:
        return bracket

    for raw in data.get("series", []):
        letter = raw.get("seriesLetter", "")
        round_no = int(raw.get("playoffRound") or 0)
        item = series_obj(raw)
        if round_no == 1:
            (bracket["east"]["r1"] if letter in "ABCD" else bracket["west"]["r1"]).append(item)
        elif round_no == 2:
            (bracket["east"]["r2"] if letter in "IJ" else bracket["west"]["r2"]).append(item)
        elif round_no == 3:
            side = "east" if raw.get("conferenceAbbrev") == "E" else "west"
            bracket[side]["conf"].append(item)
        elif round_no == 4:
            bracket["final"] = [item]

    for side in ("east", "west"):
        bracket[side]["r1"] = (bracket[side]["r1"] + [empty.copy()] * 4)[:4]
        bracket[side]["r2"] = (bracket[side]["r2"] + [empty.copy()] * 2)[:2]
        bracket[side]["conf"] = (bracket[side]["conf"] + [empty.copy()])[:1]
    return bracket


def build_finals_top(bracket: dict, season_id: int | str, n: int = 5) -> list[dict]:
    """Top-N players ranked by box-score score across the Stanley Cup Final only.

    Aggregates each completed Final game (skaters and goalies separately) and
    scores them with the same per-position formulas used for the season ranking,
    percentiled within the Final field. Degrades gracefully to [] on any failure.
    """
    final = (bracket.get("final") or [{}])[0]
    if not final.get("hi") or not final.get("lo"):
        return []

    season = str(season_id)
    start_year = season[:4] if len(season) >= 4 else season
    winner = final.get("winner")

    skaters: dict[int, dict] = {}
    goalies: dict[int, dict] = {}
    games_seen = 0
    for g in range(1, 8):
        gid = f"{start_year}03041{g}"
        try:
            box = fetch_json(f"/gamecenter/{gid}/boxscore")
        except RuntimeError:
            continue
        if box.get("gameState") not in ("OFF", "FINAL", "OVER"):
            continue
        games_seen += 1
        sides = box.get("playerByGameStats", {})
        team_meta = {
            "homeTeam": (box.get("homeTeam", {}).get("abbrev", ""), box.get("homeTeam", {}).get("score", 0)),
            "awayTeam": (box.get("awayTeam", {}).get("abbrev", ""), box.get("awayTeam", {}).get("score", 0)),
        }
        home_score = team_meta["homeTeam"][1]
        away_score = team_meta["awayTeam"][1]
        for side_key in ("homeTeam", "awayTeam"):
            code, team_score = team_meta[side_key]
            won = team_score > (away_score if side_key == "homeTeam" else home_score)
            side = sides.get(side_key, {})
            for group in ("forwards", "defense"):
                for raw in side.get(group, []):
                    pid = int(raw.get("playerId") or 0)
                    if not pid:
                        continue
                    rec = skaters.setdefault(pid, {
                        "id": pid, "teamCode": code,
                        "name": (raw.get("name") or {}).get("default", ""),
                        "pos": position_code(raw.get("position") or group[:1].upper()),
                        "gp": 0, "g": 0, "a": 0, "p": 0, "pm": 0, "shots": 0, "toi": 0.0,
                    })
                    rec["teamCode"] = code
                    rec["gp"]    += 1
                    rec["g"]     += int(raw.get("goals") or 0)
                    rec["a"]     += int(raw.get("assists") or 0)
                    rec["p"]     += int(raw.get("points") or 0)
                    rec["pm"]    += int(raw.get("plusMinus") or 0)
                    rec["shots"] += int(raw.get("sog") or 0)
                    rec["toi"]   += toi_minutes(raw.get("toi"))
            for raw in side.get("goalies", []):
                pid = int(raw.get("playerId") or 0)
                if not pid:
                    continue
                toi_min = toi_minutes(raw.get("toi"))
                if toi_min <= 0:
                    continue
                rec = goalies.setdefault(pid, {
                    "id": pid, "teamCode": code,
                    "name": (raw.get("name") or {}).get("default", ""),
                    "pos": "G",
                    "gp": 0, "saves": 0, "sa": 0, "ga": 0, "toi": 0.0, "w": 0, "so": 0,
                })
                rec["teamCode"] = code
                ga = int(raw.get("goalsAgainst") or 0)
                rec["gp"]    += 1
                rec["saves"] += int(raw.get("saves") or 0)
                rec["sa"]    += int(raw.get("shotsAgainst") or 0)
                rec["ga"]    += ga
                rec["toi"]   += toi_min
                if won and toi_min >= 30:
                    rec["w"] += 1
                if ga == 0 and toi_min >= 55:
                    rec["so"] += 1

    if games_seen == 0 or (not skaters and not goalies):
        return []

    skater_items = []
    for r in skaters.values():
        gp = max(1, r["gp"])
        stats = {
            "gp": r["gp"], "g": r["g"], "a": r["a"], "p": r["p"],
            "pm": r["pm"], "shots": r["shots"], "toi": round(r["toi"] / gp, 1),
        }
        skater_items.append({**r, "stats": stats})
    goalie_items = []
    for r in goalies.values():
        gp = max(1, r["gp"])
        svpct = round(r["saves"] / r["sa"], 3) if r["sa"] else 0.0
        gaa = round(r["ga"] * 60.0 / r["toi"], 2) if r["toi"] else 0.0
        stats = {"gp": r["gp"], "w": r["w"], "svpct": svpct, "gaa": gaa, "so": r["so"]}
        goalie_items.append({**r, "stats": stats})

    pool = []
    if skater_items:
        sc = percentile_scores(skater_items, skater_score)
        for p in skater_items:
            p["finalsScore"] = sc[p["id"]]
            pool.append(p)
    if goalie_items:
        gc = percentile_scores(goalie_items, goalie_score)
        for p in goalie_items:
            # Match the season ranking: compress goalie pool so an elite starter
            # sits near a strong skater rather than dominating the list.
            p["finalsScore"] = max(35, round(35 + (gc[p["id"]] - 35) * 0.72))
            pool.append(p)

    for p in pool:
        p["colors"] = TEAM_COLORS.get(p["teamCode"], {"primary": "#666666", "secondary": "#d9d9d9"})
        p["headshot"] = f"https://assets.nhle.com/mugs/nhl/{season}/{p['teamCode']}/{p['id']}.png"
        p.pop("toi", None)
        for k in ("g", "a", "p", "pm", "shots", "saves", "sa", "ga", "w", "so"):
            p.pop(k, None)

    pool.sort(key=lambda p: (-p["finalsScore"], -p["stats"].get("p", 0), p["name"]))
    return pool[:n]


def _player_career_score(comparison: dict) -> float:
    seasons = comparison.get("seasons", [])
    if not seasons:
        return 0.0
    scores = sorted([s["score"] for s in seasons], reverse=True)
    n = len(scores)
    top3 = sum(scores[:3]) / min(3, n)
    top8 = sum(scores[:8]) / min(8, n)
    length_bonus = min(1.0, n / 18) * 15.0
    cups_bonus = PLAYER_CUPS.get(comparison["id"], 0) * 4.0
    return round(min(100.0, top3 * 0.55 + top8 * 0.20 + length_bonus + cups_bonus), 1)


def _player_needs_hint(gap: float) -> str:
    if gap <= 6:
        return "One elite Cup run could close the gap"
    if gap <= 13:
        return "1–2 more elite seasons + sustained excellence"
    if gap <= 22:
        return "2–3 peak years + a Cup or two needed"
    return "Multiple elite seasons + several Cups needed"


def _team_needs_hint(gap: float, cups: int) -> str:
    if cups == 0:
        return "Needs at least one Cup + years of dominance"
    if gap > 25:
        return "2–3 more Cups + another dominant era"
    if gap > 14:
        return "1–2 more Cups + sustained regular-season excellence"
    return "One more Cup run could reach the threshold"


# Scaling from current-season percentile score to all-time per-season equivalent.
# Calibrated so McDavid (score≈100) maps to ~72 on the all-time scale.
CURRENT_TO_ALLTIME = 0.72


def _prospect_projected_score(age: int, score: int) -> float:
    est = score * CURRENT_TO_ALLTIME
    # Slight peak boost for very young players who haven't hit their prime
    peak_boost = 1.05 if age <= 21 else 1.02 if age <= 23 else 1.0
    top3 = min(100.0, est * peak_boost)
    top8 = est
    seasons_played = max(1, age - 17)
    seasons_remaining = max(0, 38 - age)
    total_seasons = seasons_played + seasons_remaining
    length_bonus = min(1.0, total_seasons / 18) * 15.0
    # Optimistic cup projection for elite young careers
    cup_proj = 6.0 if age <= 20 else 4.0 if age <= 22 else 2.0
    return round(min(97.0, top3 * 0.55 + top8 * 0.20 + length_bonus + cup_proj), 1)


def _prospect_note(age: int, score: int) -> str:
    if age <= 20 and score >= 85:
        return "Historic rookie pace — all-time tier is possible"
    if age <= 21 and score >= 80:
        return "Elite start to career — ceiling is very high"
    if age <= 23 and score >= 78:
        return "Among the best players of their generation"
    if score >= 80:
        return "Elite current form — needs sustained peak + Cups"
    if score >= 70:
        return "Strong pedigree — leap to elite level needed"
    return "Promising young talent — long road ahead"


def build_young_prospects(players: list[dict]) -> list[dict]:
    p_threshold = float(STATIC_HISTORY_PLAYERS[-1]["score"])
    candidates = []
    for p in players:
        if p["pos"] == "G":
            continue
        age = p.get("age")
        if not age or age > 25:
            continue
        if p["score"] < 50:
            continue
        proj = _prospect_projected_score(age, p["score"])
        gap = round(max(0.0, p_threshold - proj), 1)
        candidates.append({
            "id": p["id"],
            "name": p["name"],
            "pos": p["pos"],
            "teamCode": p["teamCode"],
            "country": p["country"],
            "colors": p["colors"],
            "age": age,
            "currentScore": p["score"],
            "projectedScore": proj,
            "threshold": p_threshold,
            "gap": gap,
            "note": _prospect_note(age, p["score"]),
        })
    candidates.sort(key=lambda x: x["projectedScore"], reverse=True)
    return candidates[:10]


def build_road_to_glory(player_comparisons: list[dict], current_teams: list[dict], players: list[dict]) -> dict:
    p_threshold = float(STATIC_HISTORY_PLAYERS[-1]["score"])  # Hasek 93.1
    t_threshold = float(STATIC_HISTORY_TEAMS[-1]["score"])    # PIT 89.7
    legend_ids = {p["id"] for p in STATIC_HISTORY_PLAYERS}

    candidates_p = []
    for comp in player_comparisons:
        if not comp.get("active") or comp.get("legendScore") is not None:
            continue
        if comp["id"] in legend_ids or not comp.get("seasons"):
            continue
        cs = _player_career_score(comp)
        gap = round(p_threshold - cs, 1)
        candidates_p.append({
            "id": comp["id"],
            "name": comp["name"],
            "pos": comp["pos"],
            "teamCode": comp["teamCode"],
            "country": comp["country"],
            "colors": comp["colors"],
            "age": age_from_birthdate(comp.get("birthDate")),
            "careerScore": cs,
            "threshold": p_threshold,
            "gap": max(0.0, gap),
            "cups": PLAYER_CUPS.get(comp["id"], 0),
            "seasons": len(comp["seasons"]),
            "note": _player_needs_hint(gap),
        })
    candidates_p.sort(key=lambda x: x["careerScore"], reverse=True)

    cups_value = {0: 12, 1: 25, 2: 38, 3: 50, 4: 60}
    candidates_t = []
    for era in ACTIVE_ERA_TEAMS:
        current = next((t for t in current_teams if t["code"] == era["teamCode"]), None)
        current_score = current["score"] if current else 50
        ds = round(min(97.0, cups_value.get(era["cups"], 60) + current_score * 0.55), 1)
        gap = round(t_threshold - ds, 1)
        candidates_t.append({
            "teamCode": era["teamCode"],
            "city": era["city"],
            "era": era["era"],
            "cups": era["cups"],
            "dynastyScore": ds,
            "threshold": t_threshold,
            "gap": max(0.0, gap),
            "note": era["note"],
            "needs": _team_needs_hint(gap, era["cups"]),
            "colors": TEAM_COLORS.get(era["teamCode"], {"primary": "#666666", "secondary": "#d9d9d9"}),
        })
    candidates_t.sort(key=lambda x: x["dynastyScore"], reverse=True)
    young_prospects = build_young_prospects(players)

    return {
        "playerThreshold": p_threshold,
        "teamThreshold": t_threshold,
        "players": candidates_p[:10],
        "teams": candidates_t[:10],
        "youngProspects": young_prospects,
    }


def annotate_player_legend_scores(players: list[dict], player_comparisons: list[dict]) -> None:
    scores: dict[int, float] = {}
    for comp in player_comparisons:
        if comp.get("legendScore") is not None:
            scores[comp["id"]] = float(comp["legendScore"])
        elif comp.get("active") and comp.get("seasons"):
            scores[comp["id"]] = _player_career_score(comp)

    for p in players:
        score = scores.get(p["id"])
        if score is None and p.get("age") and p["age"] <= 25 and p.get("score", 0) >= 50 and p.get("pos") != "G":
            score = _prospect_projected_score(p["age"], p["score"])
        if score is not None:
            p["legendScore"] = round(score, 1)


def _nhl_importance(bracket: dict) -> float:
    final = (bracket.get("final") or [{}])[0]
    if final.get("hi"):
        return 8.0  # Stanley Cup Finals
    for conf in ("east", "west"):
        for rnd in ("r3", "r2", "r1"):
            for s in bracket.get(conf, {}).get(rnd) or []:
                if s.get("hi"):
                    return 6.0  # Playoffs
    month = datetime.now(timezone.utc).month
    return 5.0 if (month >= 10 or month <= 4) else 3.0


def write_data(output: Path) -> None:
    # ── Capturar rankings anteriores ANTES de sobreescribir ──────────────────
    prev_players       = _prev_rank_map(output, "NHL_DATA", "PLAYERS")
    prev_rtg_players   = _prev_rank_map(output, "NHL_DATA", "ROAD_TO_GLORY", "players")
    prev_rtg_young     = _prev_rank_map(output, "NHL_DATA", "ROAD_TO_GLORY", "youngProspects")
    prev_rtg_teams     = _prev_rank_map_teams(output, "NHL_DATA", "ROAD_TO_GLORY", "teams")

    standings_data = fetch_json("/standings/now")
    standings = standings_data.get("standings", [])
    if not standings:
        raise RuntimeError("NHL standings response did not include standings data")

    teams = build_teams(standings)
    for item in STATIC_HISTORY_TEAMS:
        with_colors(item)
    for item in STATIC_HISTORY_PLAYERS:
        with_colors(item)

    season_id = standings[0].get("seasonId") or datetime.now(timezone.utc).year
    players = build_players(teams, season_id)
    add_roster_strength(teams, players)
    bracket = build_bracket(season_id)
    player_comparisons = build_player_comparisons(players, extra_ids=_young_prospect_ids(players))
    annotate_player_legend_scores(players, player_comparisons)
    road_to_glory = build_road_to_glory(player_comparisons, teams, players)

    # ── Asignar prevRank a cada lista ────────────────────────────────────────
    top_players = sorted(players, key=lambda p: p["score"], reverse=True)[:10]
    for i, p in enumerate(top_players):
        p["prevRank"] = prev_players.get(str(p["id"]))

    for i, p in enumerate(road_to_glory.get("players", [])[:10]):
        p["prevRank"] = prev_rtg_players.get(str(p["id"]))

    for i, p in enumerate(road_to_glory.get("youngProspects", [])[:10]):
        p["prevRank"] = prev_rtg_young.get(str(p["id"]))

    for i, t in enumerate(road_to_glory.get("teams", [])[:10]):
        t["prevRank"] = prev_rtg_teams.get(f"{t.get('teamCode','')}-{t.get('era','')}")

    importance = _nhl_importance(bracket)

    print("Computing Stanley Cup Final top performers…")
    finals_top = build_finals_top(bracket, season_id)

    payload = {
        "TEAMS": teams,
        "PLAYERS": players,
        "PLAYER_COMPARISONS": player_comparisons,
        "BRACKET": bracket,
        "FINALS_TOP": finals_top,
        "HISTORY_TEAMS": STATIC_HISTORY_TEAMS,
        "HISTORY_PLAYERS": STATIC_HISTORY_PLAYERS,
        "ROAD_TO_GLORY": road_to_glory,
        "METHODOLOGY": METHODOLOGY,
        "SEASON": season_label(season_id),
        "IMPORTANCE": importance,
        "LAST_UPDATE": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "SOURCE": {
            "name": "NHL API",
            "baseUrl": API,
            "standingsDateTimeUtc": standings_data.get("standingsDateTimeUtc"),
        },
    }
    text_payload = json.dumps(payload, ensure_ascii=False, indent=2)
    output.write_text(
        "// NHL Tracker - generated from public NHL API data.\n"
        "// Run `python3 scripts/update_data.py` to refresh.\n"
        f"window.NHL_DATA = {text_payload};\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate NHL Tracker data.js from real NHL API data.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        write_data(args.output)
    except Exception as exc:
        print(f"update_data.py: {exc}", file=sys.stderr)
        return 1
    print(f"Updated {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
