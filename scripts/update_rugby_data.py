#!/usr/bin/env python3
"""Build rugby_data.js from a broad men's international rugby results dataset.

Base CSV: data_sources/rugby_mens_data.csv
Coverage: men's international rugby union results from 1871 to 2023, 150+ teams.
Recent extension: ESPN scorepanel results after the base CSV end date.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from urllib.request import Request, urlopen
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_sources" / "rugby_mens_data.csv"
OUT = ROOT / "rugby_data.js"

BASE_ELO = 1500.0
HOME_ADVANTAGE = 60.0
K_NORMAL = 28.0
K_WORLD_CUP = 44.0
ACTIVE_GRACE_DAYS = 548        # ~18 months without penalty
DECAY_HALF_LIFE_DAYS = 365     # after grace, rating edge halves roughly yearly
DYNASTY_MIN_MATCHES = 12
DYNASTY_DENSITY_TARGET = 6.0   # team tests per year for full credit

ESPN_TEAMS = {
    "England": 1,
    "Scotland": 2,
    "Ireland": 3,
    "Wales": 4,
    "South Africa": 5,
    "Australia": 6,
    "New Zealand": 8,
    "France": 9,
    "Argentina": 10,
    "Italy": 20,
}

EXCLUDED_RANKING_TEAMS = {
    "British and Irish Lions",
    "World XV",
    "Barbarians",
}

ESPN_URL = (
    "https://site.web.api.espn.com/apis/site/v2/sports/rugby/scorepanel"
    "?contentorigin=espn&dates={year}&lang=en&limit=200&region=us&team={team_id}&tz=UTC"
)

NAME_ALIASES = {
    "British & Irish Lions": "British and Irish Lions",
    "United States of America": "United States",
    "USA": "United States",
}

TEAM_META = {
    "Argentina": {"code": "ARG", "colors": {"primary": "#75aadb", "secondary": "#f6b40e"}},
    "Australia": {"code": "AUS", "colors": {"primary": "#ffcd00", "secondary": "#00843d"}},
    "England": {"code": "ENG", "colors": {"primary": "#ffffff", "secondary": "#cf142b"}},
    "France": {"code": "FRA", "colors": {"primary": "#1d4f91", "secondary": "#d80f2a"}},
    "Ireland": {"code": "IRE", "colors": {"primary": "#169b62", "secondary": "#ff883e"}},
    "Italy": {"code": "ITA", "colors": {"primary": "#0066b3", "secondary": "#009246"}},
    "Fiji": {"code": "FIJ", "colors": {"primary": "#6ecff6", "secondary": "#111111"}},
    "Georgia": {"code": "GEO", "colors": {"primary": "#b5002d", "secondary": "#ffffff"}},
    "Japan": {"code": "JPN", "colors": {"primary": "#bc002d", "secondary": "#ffffff"}},
    "New Zealand": {"code": "NZL", "colors": {"primary": "#111111", "secondary": "#d8d8d8"}},
    "Samoa": {"code": "SAM", "colors": {"primary": "#0033a0", "secondary": "#ce1126"}},
    "Scotland": {"code": "SCO", "colors": {"primary": "#005eb8", "secondary": "#ffffff"}},
    "South Africa": {"code": "RSA", "colors": {"primary": "#007a4d", "secondary": "#ffb612"}},
    "Tonga": {"code": "TON", "colors": {"primary": "#c8102e", "secondary": "#ffffff"}},
    "United States": {"code": "USA", "colors": {"primary": "#3c3b6e", "secondary": "#b22234"}},
    "Uruguay": {"code": "URU", "colors": {"primary": "#6ec6e8", "secondary": "#ffffff"}},
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
        raw_rows = list(csv.DictReader(f))
    rows = []
    for row in raw_rows:
        match_date = datetime.utcfromtimestamp(int(row["unix_epoc_secs"]) / 1000).date()
        home = normalize_team(row["team_a_name"])
        away = normalize_team(row["team_b_name"])
        location = normalize_team(row.get("location", ""))
        rows.append({
            "date": match_date.isoformat(),
            "home_team": home,
            "away_team": away,
            "home_score": row["team_a_score"],
            "away_score": row["team_b_score"],
            "competition": row.get("competition", ""),
            "stadium": "",
            "city": "",
            "country": location,
            "neutral": str(location not in {home, away}),
            "world_cup": str("World Cup" in row.get("competition", "")),
        })
    rows.sort(key=lambda r: (r["date"], r["home_team"], r["away_team"]))
    return rows


def normalize_team(name: str) -> str:
    return NAME_ALIASES.get(name.strip(), name.strip())


def fetch_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "Hermes Rugby Elo/1.0"})
    with urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_espn_results(start_date: date) -> list[dict]:
    """Fetch finalised ESPN results after the historical CSV end date."""
    current_year = date.today().year
    rows_by_key: dict[tuple, dict] = {}
    fetched_pages = 0
    team_ids: dict[int, str] = {team_id: name for name, team_id in ESPN_TEAMS.items()}

    for year in range(start_date.year, current_year + 1):
        fetched_for_year: set[int] = set()
        pending = list(team_ids)
        while pending:
            team_id = pending.pop(0)
            if team_id in fetched_for_year:
                continue
            fetched_for_year.add(team_id)
            url = ESPN_URL.format(year=year, team_id=team_id)
            try:
                data = fetch_json(url)
            except Exception as exc:
                print(f"[WARN] ESPN rugby fetch failed for {year}/team {team_id}: {exc}", file=sys.stderr)
                continue
            fetched_pages += 1
            for group in data.get("scores", []):
                league_name = ""
                leagues = group.get("leagues") or []
                if leagues:
                    league_name = leagues[0].get("name") or leagues[0].get("abbreviation") or ""
                for event in group.get("events", []):
                    comp = (event.get("competitions") or [{}])[0]
                    status = comp.get("status", {}).get("type", {}).get("name")
                    if status != "STATUS_FINAL":
                        continue
                    competitors = comp.get("competitors") or []
                    if len(competitors) != 2:
                        continue
                    home = next((c for c in competitors if c.get("homeAway") == "home"), None)
                    away = next((c for c in competitors if c.get("homeAway") == "away"), None)
                    if not home or not away:
                        continue
                    try:
                        home_score = int(home.get("score"))
                        away_score = int(away.get("score"))
                    except (TypeError, ValueError):
                        continue
                    match_date = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).date()
                    if match_date <= start_date:
                        continue
                    home_name = normalize_team(home["team"]["displayName"])
                    away_name = normalize_team(away["team"]["displayName"])
                    for competitor in competitors:
                        team = competitor.get("team", {})
                        try:
                            discovered_id = int(team.get("id"))
                        except (TypeError, ValueError):
                            continue
                        discovered_name = normalize_team(team.get("displayName", ""))
                        if discovered_name and discovered_name not in EXCLUDED_RANKING_TEAMS and discovered_id not in team_ids:
                            team_ids[discovered_id] = discovered_name
                            pending.append(discovered_id)
                    key = (match_date.isoformat(), home_name, away_name, home_score, away_score)
                    venue = comp.get("venue", {})
                    address = venue.get("address", {})
                    rows_by_key[key] = {
                        "date": match_date.isoformat(),
                        "home_team": home_name,
                        "away_team": away_name,
                        "home_score": str(home_score),
                        "away_score": str(away_score),
                        "competition": league_name or group.get("season", {}).get("slug", "") or "ESPN Rugby",
                        "stadium": venue.get("fullName", ""),
                        "city": address.get("city", ""),
                        "country": address.get("state", ""),
                        "neutral": str(bool(comp.get("neutralSite", False))),
                        "world_cup": "False",
                    }

    rows = sorted(rows_by_key.values(), key=lambda r: (r["date"], r["home_team"], r["away_team"]))
    print(f"Fetched {len(rows)} incremental ESPN rugby results from {fetched_pages} pages", file=sys.stderr)
    return rows


CALENDAR_PAST_DAYS = 24        # recent results window
CALENDAR_FUTURE_DAYS = 80      # upcoming fixtures window


def fetch_calendar() -> dict:
    """Build a men's international fixtures calendar from ESPN scorepanel.

    Reuses the same per-national-team endpoint the Elo feed uses, but keeps both
    finalised results (recent window) and scheduled/in-progress fixtures
    (upcoming window). Opponents are auto-discovered so a fixture against a team
    outside the seed list still appears once one side is a known nation.
    """
    today = date.today()
    past_cutoff = today - timedelta(days=CALENDAR_PAST_DAYS)
    future_cutoff = today + timedelta(days=CALENDAR_FUTURE_DAYS)
    years = sorted({past_cutoff.year, today.year, future_cutoff.year})

    team_ids: dict[int, str] = {tid: name for name, tid in ESPN_TEAMS.items()}
    by_key: dict[tuple, dict] = {}

    for year in years:
        pending = list(team_ids)
        fetched: set[int] = set()
        while pending:
            team_id = pending.pop(0)
            if team_id in fetched:
                continue
            fetched.add(team_id)
            url = ESPN_URL.format(year=year, team_id=team_id)
            try:
                data = fetch_json(url)
            except Exception as exc:
                print(f"[WARN] ESPN rugby calendar fetch failed for {year}/team {team_id}: {exc}", file=sys.stderr)
                continue
            for group in data.get("scores", []):
                leagues = group.get("leagues") or []
                league_name = ""
                if leagues:
                    league_name = leagues[0].get("name") or leagues[0].get("abbreviation") or ""
                for event in group.get("events", []):
                    comp = (event.get("competitions") or [{}])[0]
                    competitors = comp.get("competitors") or []
                    if len(competitors) != 2:
                        continue
                    # Discover opponents so future rounds pick up their fixtures too.
                    for competitor in competitors:
                        team = competitor.get("team", {})
                        try:
                            discovered_id = int(team.get("id"))
                        except (TypeError, ValueError):
                            continue
                        discovered_name = normalize_team(team.get("displayName", ""))
                        if (discovered_name and discovered_name not in EXCLUDED_RANKING_TEAMS
                                and discovered_id not in team_ids):
                            team_ids[discovered_id] = discovered_name
                            pending.append(discovered_id)

                    try:
                        match_date = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).date()
                    except (KeyError, ValueError):
                        continue
                    if not (past_cutoff <= match_date <= future_cutoff):
                        continue

                    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
                    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
                    home_name = normalize_team(home["team"]["displayName"])
                    away_name = normalize_team(away["team"]["displayName"])
                    if home_name in EXCLUDED_RANKING_TEAMS or away_name in EXCLUDED_RANKING_TEAMS:
                        continue

                    status_name = comp.get("status", {}).get("type", {}).get("name", "")
                    if status_name == "STATUS_FINAL":
                        status = "final"
                    elif status_name in ("STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_END_PERIOD"):
                        status = "live"
                    else:
                        status = "scheduled"

                    def _score(side):
                        try:
                            return int(side.get("score"))
                        except (TypeError, ValueError):
                            return None
                    home_score = _score(home) if status != "scheduled" else None
                    away_score = _score(away) if status != "scheduled" else None

                    venue = comp.get("venue", {})
                    address = venue.get("address", {})
                    city = address.get("city", "")
                    key = (match_date.isoformat(), home_name, away_name)
                    by_key[key] = {
                        "date": match_date.isoformat(),
                        "status": status,
                        "competition": league_name or "Internacional",
                        "home": {"name": home_name, "teamCode": team_code(home_name), "colors": team_colors(home_name)},
                        "away": {"name": away_name, "teamCode": team_code(away_name), "colors": team_colors(away_name)},
                        "homeScore": home_score,
                        "awayScore": away_score,
                        "venue": venue.get("fullName", ""),
                        "city": city,
                    }

    matches = list(by_key.values())
    recent = sorted(
        [m for m in matches if m["status"] == "final"],
        key=lambda m: m["date"], reverse=True,
    )[:12]
    upcoming = sorted(
        [m for m in matches if m["status"] != "final"],
        key=lambda m: m["date"],
    )[:12]
    print(f"Rugby calendar: {len(recent)} recent, {len(upcoming)} upcoming (from {len(matches)} in window)", file=sys.stderr)
    return {"recent": recent, "upcoming": upcoming}


def top_team(ratings: dict[str, float]) -> str | None:
    if not ratings:
        return None
    eligible = [(name, rating) for name, rating in ratings.items() if name not in EXCLUDED_RANKING_TEAMS]
    if not eligible:
        return None
    return max(eligible, key=lambda kv: (kv[1], kv[0]))[0]


def team_code(name: str) -> str:
    meta = TEAM_META.get(name, {})
    if meta.get("code"):
        return meta["code"]
    return "".join(part[0] for part in name.split()[:3]).upper()


def team_colors(name: str) -> dict:
    return TEAM_META.get(name, {}).get("colors", {"primary": "#8a8178", "secondary": "#dedad6"})


def activity_adjusted_elo(raw_elo: float, last_played: date, as_of: date) -> tuple[float, int]:
    inactive_days = max(0, (as_of - last_played).days)
    if inactive_days <= ACTIVE_GRACE_DAYS:
        return raw_elo, inactive_days
    decay_days = inactive_days - ACTIVE_GRACE_DAYS
    retention = 0.5 ** (decay_days / DECAY_HALF_LIFE_DAYS)
    return BASE_ELO + (raw_elo - BASE_ELO) * retention, inactive_days


def build() -> dict:
    matches = read_matches()
    historical_last_date = datetime.strptime(matches[-1]["date"], "%Y-%m-%d").date()
    calendar = fetch_calendar()
    recent_matches = fetch_espn_results(historical_last_date)
    matches.extend(recent_matches)
    matches.sort(key=lambda r: (r["date"], r["home_team"], r["away_team"]))
    ratings: dict[str, float] = {}
    records = defaultdict(lambda: {"w": 0, "l": 0, "d": 0})
    last_match_date: dict[str, date] = {}
    match_dates_by_team: dict[str, list[date]] = defaultdict(list)
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
        match_dates_by_team[home].append(match_date)
        match_dates_by_team[away].append(match_date)
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
    adjusted_ratings = {}
    inactivity_days = {}
    for name, elo in ratings.items():
        if name in EXCLUDED_RANKING_TEAMS or name not in last_match_date:
            continue
        adjusted, inactive_days = activity_adjusted_elo(elo, last_match_date[name], last_date)
        adjusted_ratings[name] = adjusted
        inactivity_days[name] = inactive_days

    for name, elo in sorted(adjusted_ratings.items(), key=lambda kv: -kv[1])[:10]:
        rec = records[name]
        raw_elo = ratings[name]
        peak_date, peak_elo = max(rating_snapshots[name], key=lambda item: item[1])
        teams.append({
            "rank": len(teams) + 1,
            "name": name,
            "teamCode": team_code(name),
            "country": name,
            "elo": round(elo, 1),
            "eloRaw": round(raw_elo, 1),
            "lastMatch": last_match_date[name].isoformat(),
            "inactiveDays": inactivity_days[name],
            "peakElo": round(peak_elo, 1),
            "peakDate": peak_date.isoformat(),
            "worldCups": world_cup_counts[name],
            "record": rec,
            "colors": team_colors(name),
            "note": f"{rec['w']}V-{rec['l']}D-{rec['d']}E · último {last_match_date[name].isoformat()} · raw {raw_elo:.0f}",
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
        period_match_count = sum(1 for d in match_dates_by_team[period["team"]] if start <= d < end)
        if period_match_count < DYNASTY_MIN_MATCHES:
            continue
        matches_per_year = period_match_count / years if years else 0
        density_factor = min(1.0, matches_per_year / DYNASTY_DENSITY_TARGET)
        raw_score = (years * 10.0 * density_factor) + len(wc_years) * 24.0
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
            "matchCount": period_match_count,
            "matchesPerYear": round(matches_per_year, 1),
            "densityFactor": round(density_factor, 2),
            "worldCups": len(wc_years),
            "worldCupYears": ", ".join(str(y) for y in wc_years) if wc_years else "ninguno",
            "rawDynastyScore": raw_score,
            "colors": team_colors(period["team"]),
            "note": f"{years:.1f} años como #1 Hermes Elo · {period_match_count} tests",
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
        # UPDATED = hora de ejecución del pipeline (igual que el resto de deportes),
        # para poder detectar si el updater deja de correr. La fecha del último test
        # va aparte en LAST_MATCH (el rugby de selecciones es esporádico).
        "UPDATED": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "LAST_MATCH": last_date.isoformat(),
        "SOURCE": {
            "name": "Men's international rugby results from 1871-2023 + ESPN rugby results",
            "file": "data_sources/rugby_mens_data.csv",
            "incremental": "ESPN scorepanel by national team/year",
            "historicalThrough": historical_last_date.isoformat(),
            "incrementalMatches": len(recent_matches),
            "teams": len(ratings),
            "matches": len(matches),
            "through": last_date.isoformat(),
        },
        "IMPORTANCE": _rugby_importance(),
        "CALENDAR": calendar,
        "ELO_MODEL": {
            "base": BASE_ELO,
            "homeAdvantage": HOME_ADVANTAGE,
            "kNormal": K_NORMAL,
            "kWorldCup": K_WORLD_CUP,
            "marginCap": 2.35,
            "activityGraceDays": ACTIVE_GRACE_DAYS,
            "decayHalfLifeDays": DECAY_HALF_LIFE_DAYS,
            "dynastyMinMatches": DYNASTY_MIN_MATCHES,
            "dynastyDensityTarget": DYNASTY_DENSITY_TARGET,
        },
        "TEAMS": teams,
        "ROAD_TO_GLORY": {
            "dynastyThreshold": threshold,
            "dynasties": dynasties,
        },
    }


# Tournament windows: (month_start, day_start, month_end, day_end, importance)
_RUGBY_CALENDAR = [
    (2,  1, 3, 22, 7.5),   # Six Nations
    (5, 15, 6, 15, 5.0),   # Spring Tests
    (8,  1, 10, 15, 7.0),  # Rugby Championship + Bledisloe Cup
    (11, 1, 11, 30, 6.5),  # Autumn Internationals
]

def _rugby_importance() -> float:
    today = date.today()
    year  = today.year
    # Rugby World Cup: 2027, 2031… (year % 4 == 3), Sep–Nov
    if year % 4 == 3 and date(year, 9, 5) <= today <= date(year, 11, 10):
        return 9.5
    # British & Irish Lions: 2025, 2029… (year % 4 == 1), Jun–Aug
    if year % 4 == 1 and date(year, 6, 20) <= today <= date(year, 8, 10):
        return 8.5
    for m0, d0, m1, d1, score in _RUGBY_CALENDAR:
        if date(year, m0, d0) <= today <= date(year, m1, d1):
            return score
    return 3.5


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
