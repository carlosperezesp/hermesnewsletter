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
    return (svpct - 0.86) * 900 - gaa * 7 + stats.get("w", 0) * 1.8 + stats.get("so", 0) * 3 + gp * 0.45


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


def build_player_comparisons(players: list[dict]) -> list[dict]:
    current_ids = [p["id"] for p in sorted((p for p in players if p["pos"] != "G"), key=lambda p: p["score"], reverse=True)[:36]]
    wanted_ids = list(dict.fromkeys(current_ids + list(LEGEND_IDS.keys())))
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
        team_code = landing.get("currentTeamAbbrev") or LEGEND_IDS.get(player_id)
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


def build_players(teams: list[dict]) -> list[dict]:
    players = []
    next_id = 1
    for team in teams:
        roster_meta = {}
        try:
            roster = fetch_json(f"/roster/{team['code']}/current")
            for group in ("forwards", "defensemen", "goalies"):
                for person in roster.get(group, []):
                    roster_meta[int(person.get("id"))] = person
        except RuntimeError:
            roster_meta = {}

        club = fetch_json(f"/club-stats/{team['code']}/now")
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


def write_data(output: Path) -> None:
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
    players = build_players(teams)
    add_roster_strength(teams, players)
    bracket = build_bracket(season_id)
    player_comparisons = build_player_comparisons(players)

    payload = {
        "TEAMS": teams,
        "PLAYERS": players,
        "PLAYER_COMPARISONS": player_comparisons,
        "BRACKET": bracket,
        "HISTORY_TEAMS": STATIC_HISTORY_TEAMS,
        "HISTORY_PLAYERS": STATIC_HISTORY_PLAYERS,
        "METHODOLOGY": METHODOLOGY,
        "SEASON": season_label(season_id),
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
