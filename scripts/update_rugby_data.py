#!/usr/bin/env python3
"""Build rugby_data.js from historical international rugby results.

Source CSV: data_sources/rugby_results.csv
Coverage: men's international rugby union tests from 1871 to 2024.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_sources" / "rugby_results.csv"
OUT = ROOT / "rugby_data.js"

BASE_ELO = 1500.0
HOME_ADVANTAGE = 60.0
K_NORMAL = 28.0
K_WORLD_CUP = 44.0

TEAM_META = {
    "Argentina": {"code": "ARG", "colors": {"primary": "#75aadb", "secondary": "#f6b40e"}},
    "Australia": {"code": "AUS", "colors": {"primary": "#ffcd00", "secondary": "#00843d"}},
    "England": {"code": "ENG", "colors": {"primary": "#ffffff", "secondary": "#cf142b"}},
    "France": {"code": "FRA", "colors": {"primary": "#1d4f91", "secondary": "#d80f2a"}},
    "Ireland": {"code": "IRE", "colors": {"primary": "#169b62", "secondary": "#ff883e"}},
    "Italy": {"code": "ITA", "colors": {"primary": "#0066b3", "secondary": "#009246"}},
    "New Zealand": {"code": "NZL", "colors": {"primary": "#111111", "secondary": "#d8d8d8"}},
    "Scotland": {"code": "SCO", "colors": {"primary": "#005eb8", "secondary": "#ffffff"}},
    "South Africa": {"code": "RSA", "colors": {"primary": "#007a4d", "secondary": "#ffb612"}},
    "Wales": {"code": "WAL", "colors": {"primary": "#c8102e", "secondary": "#ffffff"}},
}

WORLD_CUP_WINNERS = {
    1987: "New Zealand",
    1991: "Australia",
    1995: "South Africa",
    1999: "Australia",
    2003: "England",
    2007: "South Africa",
    2011: "New Zealand",
    2015: "New Zealand",
    2019: "South Africa",
    2023: "South Africa",
}


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def result_score(points_for: int, points_against: int) -> float:
    if points_for > points_against:
        return 1.0
    if points_for < points_against:
        return 0.0
    return 0.5


def margin_multiplier(diff: int, elo_diff: float) -> float:
    if diff <= 0:
        return 1.0
    mult = math.log(diff + 1.0) * 2.2 / ((abs(elo_diff) * 0.001) + 2.2)
    return min(2.35, max(1.0, mult))


def read_matches() -> list[dict]:
    with SOURCE.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: (r["date"], r["home_team"], r["away_team"]))
    return rows


def top_team(ratings: dict[str, float]) -> str | None:
    if not ratings:
        return None
    return max(ratings.items(), key=lambda kv: (kv[1], kv[0]))[0]


def team_code(name: str) -> str:
    meta = TEAM_META.get(name, {})
    if meta.get("code"):
        return meta["code"]
    return "".join(part[0] for part in name.split()[:3]).upper()


def team_colors(name: str) -> dict:
    return TEAM_META.get(name, {}).get("colors", {"primary": "#8a8178", "secondary": "#dedad6"})


def build() -> dict:
    matches = read_matches()
    ratings: dict[str, float] = {}
    records = defaultdict(lambda: {"w": 0, "l": 0, "d": 0})
    last_match_date: dict[str, date] = {}
    leader_periods: list[dict] = []

    first_date = datetime.strptime(matches[0]["date"], "%Y-%m-%d").date()
    current_leader: str | None = None
    current_start = first_date
    rating_snapshots: dict[str, list[tuple[date, float]]] = defaultdict(list)

    for row in matches:
        match_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
        home = row["home_team"]
        away = row["away_team"]
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])
        neutral = parse_bool(row["neutral"])
        world_cup = parse_bool(row["world_cup"])

        ratings.setdefault(home, BASE_ELO)
        ratings.setdefault(away, BASE_ELO)

        home_rating = ratings[home]
        away_rating = ratings[away]
        adjusted_home = home_rating + (0 if neutral else HOME_ADVANTAGE)
        expected_home = expected_score(adjusted_home, away_rating)
        actual_home = result_score(home_score, away_score)
        diff = abs(home_score - away_score)
        mult = margin_multiplier(diff, home_rating - away_rating)
        k = K_WORLD_CUP if world_cup else K_NORMAL
        delta = k * mult * (actual_home - expected_home)

        ratings[home] = home_rating + delta
        ratings[away] = away_rating - delta

        if actual_home == 1.0:
            records[home]["w"] += 1
            records[away]["l"] += 1
        elif actual_home == 0.0:
            records[home]["l"] += 1
            records[away]["w"] += 1
        else:
            records[home]["d"] += 1
            records[away]["d"] += 1

        last_match_date[home] = match_date
        last_match_date[away] = match_date
        rating_snapshots[home].append((match_date, ratings[home]))
        rating_snapshots[away].append((match_date, ratings[away]))

        leader = top_team(ratings)
        if current_leader is None:
            current_leader = leader
            current_start = match_date
        elif leader != current_leader:
            leader_periods.append({
                "team": current_leader,
                "start": current_start,
                "end": match_date,
            })
            current_leader = leader
            current_start = match_date

    last_date = datetime.strptime(matches[-1]["date"], "%Y-%m-%d").date()
    if current_leader:
        leader_periods.append({"team": current_leader, "start": current_start, "end": last_date})

    world_cup_counts = defaultdict(int)
    for winner in WORLD_CUP_WINNERS.values():
        world_cup_counts[winner] += 1

    teams = []
    for name, elo in sorted(ratings.items(), key=lambda kv: -kv[1])[:10]:
        rec = records[name]
        peak_date, peak_elo = max(rating_snapshots[name], key=lambda item: item[1])
        teams.append({
            "rank": len(teams) + 1,
            "name": name,
            "teamCode": team_code(name),
            "country": name,
            "elo": round(elo, 1),
            "peakElo": round(peak_elo, 1),
            "peakDate": peak_date.isoformat(),
            "worldCups": world_cup_counts[name],
            "record": rec,
            "colors": team_colors(name),
            "note": f"{rec['w']}V-{rec['l']}D-{rec['d']}E desde 1871 · pico {peak_elo:.0f}",
        })

    dynasty_candidates = []
    for period in leader_periods:
        start = period["start"]
        end = period["end"]
        days = (end - start).days
        if days < 365:
            continue
        wc_years = [
            year for year, winner in WORLD_CUP_WINNERS.items()
            if winner == period["team"] and start.year <= year <= end.year
        ]
        years = days / 365.25
        raw_score = years * 10.0 + len(wc_years) * 24.0
        dynasty_candidates.append({
            "name": period["team"],
            "teamCode": team_code(period["team"]),
            "country": period["team"],
            "era": f"{start.year}-{end.year if end < last_date else 'present'}",
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "daysNo1": days,
            "yearsNo1": round(years, 1),
            "weeksNo1": round(days / 7),
            "worldCups": len(wc_years),
            "worldCupYears": ", ".join(str(y) for y in wc_years) if wc_years else "ninguno",
            "rawDynastyScore": raw_score,
            "colors": team_colors(period["team"]),
            "note": f"{years:.1f} años como #1 Hermes Elo",
        })

    dynasty_candidates.sort(key=lambda d: (d["rawDynastyScore"], d["daysNo1"]), reverse=True)
    max_raw = dynasty_candidates[0]["rawDynastyScore"] if dynasty_candidates else 1.0
    dynasties = []
    for i, item in enumerate(dynasty_candidates[:10], 1):
        item = dict(item)
        item["rank"] = i
        item["dynastyScore"] = round(item.pop("rawDynastyScore") / max_raw * 100.0, 1)
        dynasties.append(item)

    threshold = dynasties[9]["dynastyScore"] if len(dynasties) >= 10 else 70.0

    return {
        "SEASON": "1871-present",
        "UPDATED": last_date.isoformat(),
        "SOURCE": {
            "name": "International Rugby Union results from 1871-2024",
            "file": "data_sources/rugby_results.csv",
            "matches": len(matches),
            "through": last_date.isoformat(),
        },
        "IMPORTANCE": 3.7,
        "ELO_MODEL": {
            "base": BASE_ELO,
            "homeAdvantage": HOME_ADVANTAGE,
            "kNormal": K_NORMAL,
            "kWorldCup": K_WORLD_CUP,
            "marginCap": 2.35,
        },
        "TEAMS": teams,
        "ROAD_TO_GLORY": {
            "dynastyThreshold": threshold,
            "dynasties": dynasties,
        },
    }


def main() -> int:
    data = build()
    OUT.write_text(
        "window.RUGBY_DATA = "
        + json.dumps(data, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT.relative_to(ROOT)} · {len(data['TEAMS'])} teams · "
          f"{len(data['ROAD_TO_GLORY']['dynasties'])} dynasties")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
