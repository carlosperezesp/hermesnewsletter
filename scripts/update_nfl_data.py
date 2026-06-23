#!/usr/bin/env python3
"""Fetch NFL data from ESPN public API and regenerate nfl_data.js."""

from __future__ import annotations

import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "nfl_data.js"


# ── Prev-rank helper ─────────────────────────────────────────────────────────

def _prev_rank_map(filepath: Path, js_var: str, *path: str) -> "dict[str, int]":
    import re as _re, json as _json
    try:
        text = filepath.read_text(encoding="utf-8")
        text = _re.sub(
            r"^window\." + _re.escape(js_var) + r"\s*=\s*", "", text, flags=_re.MULTILINE
        ).rstrip().rstrip(";")
        obj = _json.loads(text[text.find("{"):text.rfind("}") + 1])
        for key in path:
            obj = obj.get(key) if isinstance(obj, dict) else None
            if obj is None:
                return {}
        if not isinstance(obj, list):
            return {}
        result: dict[str, int] = {}
        for i, item in enumerate(obj[:60]):
            k = str(item.get("id") or item.get("name", ""))
            if k:
                result[k] = i + 1
        return result
    except Exception:
        return {}

API_STANDINGS  = "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"
API_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
API_PLAYERS    = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/statistics/byathlete"

NFL_DIVISIONS: dict[str, list[str]] = {
    "AFC East":  ["NE",  "BUF", "NYJ", "MIA"],
    "AFC North": ["BAL", "CIN", "CLE", "PIT"],
    "AFC South": ["HOU", "IND", "JAX", "TEN"],
    "AFC West":  ["KC",  "LAC", "LV",  "DEN"],
    "NFC East":  ["DAL", "PHI", "NYG", "WSH"],
    "NFC North": ["CHI", "MIN", "GB",  "DET"],
    "NFC South": ["NO",  "CAR", "TB",  "ATL"],
    "NFC West":  ["LAR", "ARI", "SEA", "SF"],
}
_CODE_TO_DIV = {code: div for div, codes in NFL_DIVISIONS.items() for code in codes}

NFL_TEAM_COLORS: dict[str, dict] = {
    "NE":  {"primary": "#002244", "secondary": "#c60c30"},
    "BUF": {"primary": "#00338d", "secondary": "#c60c30"},
    "NYJ": {"primary": "#125740", "secondary": "#000000"},
    "MIA": {"primary": "#008e97", "secondary": "#fc4c02"},
    "BAL": {"primary": "#241773", "secondary": "#9e7c0c"},
    "CIN": {"primary": "#fb4f14", "secondary": "#000000"},
    "CLE": {"primary": "#311d00", "secondary": "#ff3c00"},
    "PIT": {"primary": "#101820", "secondary": "#ffb612"},
    "HOU": {"primary": "#03202f", "secondary": "#a71930"},
    "IND": {"primary": "#002c5f", "secondary": "#a2aaad"},
    "JAX": {"primary": "#006778", "secondary": "#9f792c"},
    "TEN": {"primary": "#0c2340", "secondary": "#4b92db"},
    "KC":  {"primary": "#e31837", "secondary": "#ffb612"},
    "LAC": {"primary": "#0080c6", "secondary": "#ffb612"},
    "LV":  {"primary": "#000000", "secondary": "#a5acaf"},
    "DEN": {"primary": "#fb4f14", "secondary": "#002244"},
    "DAL": {"primary": "#003594", "secondary": "#869397"},
    "PHI": {"primary": "#004c54", "secondary": "#a5acaf"},
    "NYG": {"primary": "#0b2265", "secondary": "#a71930"},
    "WSH": {"primary": "#5a1414", "secondary": "#ffb612"},
    "CHI": {"primary": "#0b162a", "secondary": "#c83803"},
    "MIN": {"primary": "#4f2683", "secondary": "#ffc62f"},
    "GB":  {"primary": "#203731", "secondary": "#ffb612"},
    "DET": {"primary": "#0076b6", "secondary": "#b0b7bc"},
    "NO":  {"primary": "#d3bc8d", "secondary": "#101820"},
    "CAR": {"primary": "#0085ca", "secondary": "#101820"},
    "TB":  {"primary": "#d50a0a", "secondary": "#ff7900"},
    "ATL": {"primary": "#a71930", "secondary": "#000000"},
    "LAR": {"primary": "#003594", "secondary": "#ffd100"},
    "ARI": {"primary": "#97233f", "secondary": "#ffb612"},
    "SEA": {"primary": "#002244", "secondary": "#69be28"},
    "SF":  {"primary": "#aa0000", "secondary": "#b3995d"},
}

# ESPN byathlete passing stat indices (confirmed from 2025 season data)
# [cmp, att, pct, yds, ypa, ypg, long, td, int, sacks, sackyds, qbr, rating, ...]
PI_CMP  = 0; PI_ATT = 1; PI_PCT = 2; PI_YDS = 3
PI_YPA  = 4; PI_YPG = 5; PI_TD  = 7; PI_INT = 8; PI_SACK = 9


def fetch_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "NFL Tracker local updater"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except HTTPError as exc:
        raise RuntimeError(f"{url} → HTTP {exc.code}") from exc
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


def _season_and_status() -> tuple[int, str]:
    """Return (season_year, status) where status is 'regular' | 'postseason' | 'offseason'."""
    try:
        data = fetch_json(f"{API_SCOREBOARD}")
        s = data.get("season", {})
        year  = s.get("year", date.today().year)
        stype = s.get("type", 4)
        if stype == 2:
            return year, "regular"
        if stype == 3:
            return year, "postseason"
    except RuntimeError:
        pass
    # Off-season: use the most recently completed season
    today = date.today()
    # NFL season year = year the season started (Sep). Super Bowl in Feb of year+1.
    if today.month >= 9:
        return today.year, "offseason"
    return today.year - 1, "offseason"


def build_teams(season_year: int) -> tuple[list[dict], dict[str, dict]]:
    data = fetch_json(f"{API_STANDINGS}?season={season_year}")
    teams: list[dict] = []
    team_by_code: dict[str, dict] = {}
    for conf_data in data.get("children", []):
        conf_name = conf_data.get("name", "")
        conf = "AFC" if "American" in conf_name else "NFC"
        for entry in conf_data.get("standings", {}).get("entries", []):
            t = entry["team"]
            stats = {s["name"]: s.get("value") for s in entry.get("stats", [])}
            code = t.get("abbreviation", "")
            wins   = int(stats.get("wins",   0) or 0)
            losses = int(stats.get("losses", 0) or 0)
            ties   = int(stats.get("ties",   0) or 0)
            pf     = int(stats.get("pointsFor",     stats.get("pointDifferential", 0) or 0))
            pa     = int(stats.get("pointsAgainst", 0) or 0)
            win_pct = float(stats.get("winPercent",  0) or 0)
            pd     = pf - pa
            gp     = wins + losses + ties
            seed   = int(stats.get("playoffSeed", 0) or 0)
            # Score: win% weighted 80% + points differential per game 20%
            pdpg   = pd / max(1, gp)
            score  = round(max(0, min(100, win_pct * 80 + pdpg * 0.8)))
            logos  = t.get("logos", [])
            logo   = logos[0].get("href", "") if logos else f"https://a.espncdn.com/i/teamlogos/nfl/500/{code.lower()}.png"
            team = {
                "code":       code,
                "city":       t.get("displayName", ""),
                "shortName":  t.get("location", ""),
                "commonName": t.get("name", ""),
                "conf":       conf,
                "div":        _CODE_TO_DIV.get(code, conf),
                "gp":         gp,
                "w":          wins,
                "l":          losses,
                "t":          ties,
                "winPct":     round(win_pct, 3),
                "pf":         pf,
                "pa":         pa,
                "pd":         pd,
                "seed":       seed,
                "score":      score,
                "logo":       logo,
                "colors":     NFL_TEAM_COLORS.get(code, {"primary": "#666", "secondary": "#ccc"}),
            }
            teams.append(team)
            team_by_code[code] = team
    return sorted(teams, key=lambda t: (-t["w"], -t["pd"])), team_by_code


def build_players(season_year: int) -> list[dict]:
    try:
        data = fetch_json(
            f"{API_PLAYERS}?season={season_year}&seasontype=2&limit=100"
        )
    except RuntimeError:
        return []

    qbs: list[dict] = []

    def _v(arr: list, i: int, default: float = 0.0) -> float:
        return float(arr[i]) if len(arr) > i and arr[i] is not None else default

    for entry in data.get("athletes", []):
        ath   = entry.get("athlete", {})
        pos   = ath.get("position", {}).get("abbreviation", "?")
        if pos != "QB":
            continue
        cats  = {c["name"]: c.get("values", []) for c in entry.get("categories", [])}
        pit   = cats.get("passing", [])
        rush  = cats.get("rushing", [])

        cmp  = _v(pit, PI_CMP)
        att  = _v(pit, PI_ATT)
        if att < 50:
            continue
        yds  = _v(pit, PI_YDS)
        pct  = _v(pit, PI_PCT)
        ypa  = _v(pit, PI_YPA)
        td   = _v(pit, PI_TD)
        ints = _v(pit, PI_INT)

        rush_yds = _v(rush, 1)
        rush_td  = _v(rush, 4)

        raw = yds * 0.04 + td * 5 - ints * 4 + pct * 0.3

        teams_arr = ath.get("teams", [])
        team_code = teams_arr[0].get("abbreviation", "") if teams_arr else ath.get("teamId", "")
        hs = ath.get("headshot", {})
        headshot = hs.get("href", "") if isinstance(hs, dict) else str(hs or "")

        qbs.append({
            "id":       int(ath.get("id", 0)),
            "name":     ath.get("displayName", ""),
            "pos":      pos,
            "teamCode": team_code,
            "age":      ath.get("age"),
            "headshot": headshot,
            "colors":   NFL_TEAM_COLORS.get(team_code, {"primary": "#666", "secondary": "#ccc"}),
            "score":    50,
            "raw":      raw,
            "stats": {
                "type":     "passing",
                "cmp":      int(cmp),
                "att":      int(att),
                "pct":      round(pct, 1),
                "yds":      int(yds),
                "ypa":      round(ypa, 1),
                "td":       int(td),
                "int":      int(ints),
                "rushYds":  int(rush_yds),
                "rushTd":   int(rush_td),
            },
        })

    scores = percentile_scores(qbs, lambda p: p["raw"])
    for p in qbs:
        p["score"] = scores.get(p["id"], 50)
        del p["raw"]

    return sorted(qbs, key=lambda p: (-p["score"], p["name"]))


def _parse_round_nfl(headline: str) -> tuple[str | None, str | None]:
    h = headline.lower()
    if "super bowl" in h:
        return "sb", "sb"
    if "afc" in h or "american football" in h:
        conf = "afc"
    elif "nfc" in h or "national football" in h:
        conf = "nfc"
    else:
        return None, None
    if "wild card" in h:
        return "wc", conf
    if "divisional" in h:
        return "div", conf
    if "championship" in h:
        return "conf", conf
    return None, None


def build_bracket(season_year: int) -> dict:
    empty = {"hi": None, "lo": None, "winner": None, "seriesScore": "-"}
    bracket = {
        "afc": {"wc": [], "div": [], "conf": []},
        "nfc": {"wc": [], "div": [], "conf": []},
        "sb":  [empty.copy()],
    }
    try:
        start = f"{season_year}0101"
        end   = f"{season_year + 1}0228"
        today = date.today().strftime("%Y%m%d")
        if today < f"{season_year}0101":
            return bracket
        data = fetch_json(
            f"{API_SCOREBOARD}?seasontype=3&season={season_year}&dates={start}-{today}&limit=100"
        )
    except RuntimeError:
        return bracket

    seen: dict[frozenset, dict] = {}
    for event in data.get("events", []):
        comp = event.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
        teams = [c.get("team", {}).get("abbreviation", "") for c in competitors]
        if len(teams) != 2 or not all(teams):
            continue
        key = frozenset(teams)
        e_date = event.get("date", "")
        notes = comp.get("notes", [])
        headline = notes[0].get("headline", "") if notes else ""
        # For NFL, each playoff game is one game (not a series)
        t0, t1 = teams
        competitors_map = {c.get("team", {}).get("abbreviation", ""): c for c in competitors}
        c0 = competitors_map.get(t0, {})
        c1 = competitors_map.get(t1, {})
        s0 = int(c0.get("score", 0) or 0)
        s1 = int(c1.get("score", 0) or 0)
        status = comp.get("status", {}).get("type", {}).get("completed", False)
        if key not in seen or e_date > seen[key]["date"]:
            seen[key] = {
                "date": e_date, "headline": headline,
                "teams": [t0, t1], "scores": [s0, s1],
                "completed": status,
            }

    for s in seen.values():
        round_key, conf = _parse_round_nfl(s["headline"])
        if round_key is None:
            continue
        t0, t1 = s["teams"]
        s0, s1 = s["scores"]
        hi, lo, hi_s, lo_s = (t0, t1, s0, s1) if s0 >= s1 else (t1, t0, s1, s0)
        winner = hi if (s["completed"] and hi_s > lo_s) else None
        match_obj = {"hi": hi, "lo": lo, "winner": winner, "seriesScore": f"{hi_s}-{lo_s}"}
        if round_key == "sb":
            bracket["sb"] = [match_obj]
        elif conf in ("afc", "nfc"):
            bracket[conf][round_key].append(match_obj)

    for side in ("afc", "nfc"):
        bracket[side]["wc"]   = (bracket[side]["wc"]   + [empty.copy()] * 3)[:3]
        bracket[side]["div"]  = (bracket[side]["div"]  + [empty.copy()] * 2)[:2]
        bracket[side]["conf"] = (bracket[side]["conf"] + [empty.copy()])[:1]
    return bracket


def _nfl_importance(status: str, bracket: dict) -> float:
    if status == "offseason":
        return 3.0
    sb = (bracket.get("sb") or [{}])[0]
    if sb.get("hi"):
        return 10.0  # Super Bowl
    for conf in ("afc", "nfc"):
        for rnd in ("conf", "div", "wc"):
            for s in bracket.get(conf, {}).get(rnd) or []:
                if s.get("hi"):
                    return 9.0  # Playoffs
    return 8.0  # Regular season


# ── Panteón QB all-time (es leyenda) ─────────────────────────────────────────
# La NFL en Hermes es una liga de QBs: el top histórico son mariscales de campo.
STATIC_HISTORY_PLAYERS = [
    {"rank": 1,  "name": "Tom Brady",       "pos": "QB", "teamCode": "NE",  "era": "2000-22",      "score": 100.0, "note": "7 Super Bowls · 5 SB MVP · GOAT indiscutible"},
    {"rank": 2,  "name": "Peyton Manning",  "pos": "QB", "teamCode": "IND", "era": "1998-15",      "score": 96.0,  "note": "5 MVP · 2 Super Bowls · cerebro ofensivo"},
    {"rank": 3,  "name": "Joe Montana",     "pos": "QB", "teamCode": "SF",  "era": "1979-94",      "score": 94.0,  "note": "4 Super Bowls · 3 SB MVP · 'Joe Cool'"},
    {"rank": 4,  "name": "Patrick Mahomes", "pos": "QB", "teamCode": "KC",  "era": "2017-present", "score": 93.0,  "note": "3 Super Bowls · 2 MVP · leyenda en construcción"},
    {"rank": 5,  "name": "Johnny Unitas",   "pos": "QB", "teamCode": "BAL", "era": "1956-73",      "score": 92.5,  "note": "3 títulos · pionero del juego aéreo moderno"},
    {"rank": 6,  "name": "Brett Favre",     "pos": "QB", "teamCode": "GB",  "era": "1991-10",      "score": 92.0,  "note": "3 MVP · Super Bowl XXXI · récord de durabilidad"},
    {"rank": 7,  "name": "Aaron Rodgers",   "pos": "QB", "teamCode": "GB",  "era": "2005-present", "score": 91.5,  "note": "4 MVP · Super Bowl XLV · precisión histórica"},
    {"rank": 8,  "name": "Drew Brees",      "pos": "QB", "teamCode": "NO",  "era": "2001-20",      "score": 91.0,  "note": "Super Bowl XLIV · récords de yardas y completados"},
    {"rank": 9,  "name": "John Elway",      "pos": "QB", "teamCode": "DEN", "era": "1983-98",      "score": 90.5,  "note": "2 Super Bowls · 'The Drive' · brazo legendario"},
    {"rank": 10, "name": "Dan Marino",      "pos": "QB", "teamCode": "MIA", "era": "1983-99",      "score": 90.0,  "note": "MVP · récords de pase de su era (sin anillo)"},
]

# Anillos de Super Bowl de QBs en activo — bonus para el Camino a la Gloria.
PLAYER_RINGS = {
    "Patrick Mahomes": 3, "Matthew Stafford": 1, "Jalen Hurts": 1, "Aaron Rodgers": 1,
}

# QBs en activo que siempre se siguen en el Camino a la Gloria.
ROAD_TO_GLORY_STARS = {
    "Patrick Mahomes", "Josh Allen", "Joe Burrow", "Justin Herbert", "Lamar Jackson",
    "Jalen Hurts", "Jayden Daniels", "C.J. Stroud", "Brock Purdy", "Caleb Williams",
}

NFL_CURRENT_TO_ALLTIME = 0.86


def _nfl_career_score(name: str, current_score: int, age: "int | None") -> float:
    seasons = max(1, (age or 27) - 21)
    rings = PLAYER_RINGS.get(name, 0)
    est = current_score * NFL_CURRENT_TO_ALLTIME
    top3 = min(100.0, est * 1.06)
    length_bonus = min(1.0, seasons / 13) * 16.0
    rings_bonus = rings * 4.5
    return round(min(100.0, top3 * 0.55 + est * 0.20 + length_bonus + rings_bonus), 1)


def _nfl_prospect_score(current_score: int, age: int) -> float:
    est = current_score * NFL_CURRENT_TO_ALLTIME
    peak = 1.08 if age <= 23 else 1.04 if age <= 25 else 1.0
    top3 = min(100.0, est * peak)
    seasons_total = max(1, (age - 21) + max(0, 38 - age))
    length_bonus = min(1.0, seasons_total / 13) * 16.0
    ring_proj = 7.0 if age <= 24 else 4.0
    return round(min(97.0, top3 * 0.55 + est * 0.20 + length_bonus + ring_proj), 1)


def _nfl_player_note(gap: float) -> str:
    if gap <= 6:
        return "Un anillo + temporada elite y entra al panteón"
    if gap <= 13:
        return "1–2 temporadas elite + un Super Bowl"
    if gap <= 22:
        return "2–3 años de pico + varios anillos"
    return "Largo camino: años elite y títulos por delante"


def _nfl_prospect_note(age: int, score: int) -> str:
    if age <= 23 and score >= 85:
        return "Arranque histórico — techo de leyenda"
    if age <= 24 and score >= 80:
        return "Inicio elite — techo altísimo"
    if age <= 26 and score >= 78:
        return "De los mejores de su generación"
    if score >= 78:
        return "Forma elite — falta sostener pico y anillos"
    return "Joven con pedigrí — salto a elite pendiente"


def build_road_to_glory_nfl(players: list[dict]) -> dict:
    threshold = float(STATIC_HISTORY_PLAYERS[-1]["score"])  # Marino 90.0
    legend_names = {p["name"] for p in STATIC_HISTORY_PLAYERS}
    top_ids = {p["id"] for p in sorted(players, key=lambda p: -p["score"])[:24]}
    star_names = {p["name"] for p in players if p["name"] in ROAD_TO_GLORY_STARS}

    chase = []
    for p in players:
        if p["id"] not in top_ids and p["name"] not in star_names:
            continue
        if p["name"] in legend_names:
            continue
        cs = _nfl_career_score(p["name"], p["score"], p.get("age"))
        gap = round(max(0.0, threshold - cs), 1)
        chase.append({
            "id": p["id"], "name": p["name"], "pos": p["pos"], "teamCode": p["teamCode"],
            "colors": p["colors"], "age": p.get("age"), "careerScore": cs,
            "threshold": threshold, "gap": gap, "rings": PLAYER_RINGS.get(p["name"], 0),
            "note": _nfl_player_note(gap), "prevRank": None,
        })
    chase.sort(key=lambda x: x["careerScore"], reverse=True)

    young = []
    for p in players:
        age = p.get("age")
        if not age or age > 25 or p["score"] < 50 or p["name"] in legend_names:
            continue
        proj = _nfl_prospect_score(p["score"], age)
        young.append({
            "id": p["id"], "name": p["name"], "pos": p["pos"], "teamCode": p["teamCode"],
            "colors": p["colors"], "age": age, "currentScore": p["score"],
            "projectedScore": proj, "threshold": threshold,
            "gap": round(max(0.0, threshold - proj), 1),
            "note": _nfl_prospect_note(age, p["score"]), "prevRank": None,
        })
    young.sort(key=lambda x: x["projectedScore"], reverse=True)

    return {"playerThreshold": threshold, "players": chase[:10], "youngProspects": young[:10]}


def write_data(output: Path) -> None:
    prev_players = _prev_rank_map(output, "NFL_DATA", "PLAYERS")

    season_year, status = _season_and_status()

    print(f"Season {season_year} ({status}). Fetching NFL standings…")
    teams, team_by_code = build_teams(season_year)

    # If standings are empty the season hasn't started yet — fall back to last season
    if not teams:
        season_year -= 1
        status = "offseason"
        print(f"No teams found, falling back to season {season_year}…")
        teams, team_by_code = build_teams(season_year)

    standings_year = season_year
    print("Fetching NFL player stats (QBs)…")
    players = build_players(standings_year)

    print("Fetching NFL bracket…")
    bracket = build_bracket(season_year)

    importance = _nfl_importance(status, bracket)

    # ── Asignar prevRank ──────────────────────────────────────────────────────
    for p in sorted(players, key=lambda x: x["score"], reverse=True)[:10]:
        p["prevRank"] = prev_players.get(str(p.get("id") or p.get("name", "")))

    road_to_glory = build_road_to_glory_nfl(players)
    # Road-to-Glory lists also need week-over-week ranks (else they show NEW
    # forever, like the main player list did before).
    prev_rtg_players = _prev_rank_map(output, "NFL_DATA", "ROAD_TO_GLORY", "players")
    prev_rtg_young = _prev_rank_map(output, "NFL_DATA", "ROAD_TO_GLORY", "youngProspects")
    for p in road_to_glory.get("players", []):
        p["prevRank"] = prev_rtg_players.get(str(p.get("id") or p.get("name", "")))
    for p in road_to_glory.get("youngProspects", []):
        p["prevRank"] = prev_rtg_young.get(str(p.get("id") or p.get("name", "")))

    payload = {
        "TEAMS":         teams,
        "PLAYERS":       players,
        "BRACKET":       bracket,
        "HISTORY_PLAYERS": STATIC_HISTORY_PLAYERS,
        "ROAD_TO_GLORY": road_to_glory,
        "DIVISIONS":     list(NFL_DIVISIONS.keys()),
        "SEASON":        str(season_year),
        "SEASON_STATUS": status,
        "IMPORTANCE":    importance,
        "LAST_UPDATE":   datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "SOURCE":        {"name": "ESPN API", "baseUrl": "site.api.espn.com"},
    }

    output.write_text(
        "// NFL Tracker - generated from ESPN public API data.\n"
        "// Run `python3 scripts/update_nfl_data.py` to refresh.\n"
        f"window.NFL_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        write_data(args.output)
    except Exception as exc:
        print(f"update_nfl_data.py: {exc}", file=sys.stderr)
        return 1
    print(f"Updated {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
