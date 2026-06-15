#!/usr/bin/env python3
"""Build cricket_data.js from completed Cricsheet scorecards.

This is deliberately not live. It downloads Cricsheet ZIP archives, parses
completed scorecards, and recalculates Hermes cricket rankings from matches
that have already happened.
"""

from __future__ import annotations

import io
import json
import math
import sys
import time
import urllib.request
import zipfile
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cricket_data.js"
CACHE = ROOT / ".cricket_cache"
CACHE.mkdir(exist_ok=True)

CRICSHEET = "https://cricsheet.org/downloads/{name}_json.zip"
ARCHIVES = {
    "test": {"name": "tests", "format": "test", "weight": 1.0, "days": 730, "label": "Tests"},
    "odi": {"name": "odis", "format": "odi", "weight": 1.0, "days": 548, "label": "ODIs"},
    "t20i": {"name": "t20s", "format": "t20", "weight": 0.86, "days": 548, "label": "T20Is"},
    "ipl": {"name": "ipl", "format": "franchise", "weight": 1.0, "days": 730, "label": "IPL"},
    "bbl": {"name": "bbl", "format": "franchise", "weight": 0.72, "days": 730, "label": "BBL"},
    "psl": {"name": "psl", "format": "franchise", "weight": 0.72, "days": 730, "label": "PSL"},
    "sa20": {"name": "sa20", "format": "franchise", "weight": 0.68, "days": 730, "label": "SA20"},
    "cpl": {"name": "cpl", "format": "franchise", "weight": 0.62, "days": 730, "label": "CPL"},
    "mlc": {"name": "mlc", "format": "franchise", "weight": 0.58, "days": 730, "label": "MLC"},
}

COUNTRIES = {
    "Australia": {"code": "AUS", "primary": "#ffcd00", "secondary": "#006341", "flag": "au"},
    "England": {"code": "ENG", "primary": "#c8102e", "secondary": "#ffffff", "flag": "gb-eng"},
    "India": {"code": "IND", "primary": "#1c4fa1", "secondary": "#ff9933", "flag": "in"},
    "New Zealand": {"code": "NZ", "primary": "#111111", "secondary": "#d8d8d8", "flag": "nz"},
    "Pakistan": {"code": "PAK", "primary": "#115740", "secondary": "#ffffff", "flag": "pk"},
    "South Africa": {"code": "SA", "primary": "#007a4d", "secondary": "#ffb81c", "flag": "za"},
    "Sri Lanka": {"code": "SL", "primary": "#0033a0", "secondary": "#ffb612", "flag": "lk"},
    "Afghanistan": {"code": "AFG", "primary": "#d32011", "secondary": "#007a36", "flag": "af"},
    "West Indies": {"code": "WI", "primary": "#7a263a", "secondary": "#f6c344", "flag": ""},
    "Bangladesh": {"code": "BAN", "primary": "#006a4e", "secondary": "#f42a41", "flag": "bd"},
    "Zimbabwe": {"code": "ZIM", "primary": "#009739", "secondary": "#ffd100", "flag": "zw"},
    "Ireland": {"code": "IRE", "primary": "#169b62", "secondary": "#ff883e", "flag": "ie"},
    "Netherlands": {"code": "NED", "primary": "#ff7f00", "secondary": "#21468b", "flag": "nl"},
}

TEAM_ALIASES = {
    "United Arab Emirates": ("UAE", "#00732f", "#ffffff", "ae"),
    "Scotland": ("SCO", "#005eb8", "#ffffff", "gb-sct"),
    "Nepal": ("NEP", "#dc143c", "#003893", "np"),
    "Oman": ("OMA", "#db161b", "#ffffff", "om"),
    "Namibia": ("NAM", "#003580", "#ffce00", "na"),
    "United States of America": ("USA", "#3c3b6e", "#b22234", "us"),
}

PLAYER_COUNTRY_OVERRIDES = {
    "Virat Kohli": "India",
    "Jasprit Bumrah": "India",
    "Rohit Sharma": "India",
    "Joe Root": "England",
    "Harry Brook": "England",
    "Ben Stokes": "England",
    "Steven Smith": "Australia",
    "Pat Cummins": "Australia",
    "Travis Head": "Australia",
    "Kane Williamson": "New Zealand",
    "Babar Azam": "Pakistan",
    "Shaheen Shah Afridi": "Pakistan",
    "Rashid Khan": "Afghanistan",
    "Kagiso Rabada": "South Africa",
}

LEGACY_SEEDS = {
    "Virat Kohli": 88.0,
    "Joe Root": 78.0,
    "Steven Smith": 76.0,
    "Kane Williamson": 73.0,
    "Pat Cummins": 63.0,
    "Jasprit Bumrah": 58.0,
    "Rashid Khan": 52.0,
    "Babar Azam": 49.0,
    "Kagiso Rabada": 48.0,
    "Travis Head": 44.0,
    "Harry Brook": 27.0,
}

TROPHIES = [
    {"code": "AUS", "name": "Australia", "odi_wc": 6, "t20_wc": 1, "ct": 2, "wtc": 1, "note": "Gold standard ICC cabinet"},
    {"code": "IND", "name": "India", "odi_wc": 2, "t20_wc": 2, "ct": 2, "wtc": 0, "note": "Modern depth monster; WTC still the missing line"},
    {"code": "WI", "name": "West Indies", "odi_wc": 2, "t20_wc": 2, "ct": 1, "wtc": 0, "note": "White-ball legacy still enormous"},
    {"code": "ENG", "name": "England", "odi_wc": 1, "t20_wc": 2, "ct": 0, "wtc": 0, "note": "White-ball reinvention changed the sport"},
    {"code": "PAK", "name": "Pakistan", "odi_wc": 1, "t20_wc": 1, "ct": 1, "wtc": 0, "note": "Tournament volatility as identity"},
    {"code": "SL", "name": "Sri Lanka", "odi_wc": 1, "t20_wc": 1, "ct": 1, "wtc": 0, "note": "Underrated cross-format era peak"},
    {"code": "NZ", "name": "New Zealand", "odi_wc": 0, "t20_wc": 0, "ct": 1, "wtc": 1, "note": "WTC crown anchors the legacy"},
    {"code": "SA", "name": "South Africa", "odi_wc": 0, "t20_wc": 0, "ct": 1, "wtc": 0, "note": "Talent says more than the trophy shelf"},
]

HISTORIC_TOP_10_THRESHOLD = 79.0

WTC_TEAMS = {"Australia", "Bangladesh", "England", "India", "New Zealand", "Pakistan", "South Africa", "Sri Lanka", "West Indies"}

WTC_STANDINGS = [
    {"rank": 1, "name": "Australia", "played": 8, "won": 7, "lost": 1, "drawn": 0, "points": 84, "pct": 87.50, "note": "7 victorias en 8 Tests; ritmo claro de final."},
    {"rank": 2, "name": "South Africa", "played": 4, "won": 3, "lost": 1, "drawn": 0, "points": 36, "pct": 75.00, "note": "Actual campeona WTC, todavía en plaza de final."},
    {"rank": 3, "name": "Sri Lanka", "played": 2, "won": 1, "lost": 0, "drawn": 1, "points": 16, "pct": 66.67, "note": "Pocos partidos, PCT alto y margen estrecho."},
    {"rank": 4, "name": "New Zealand", "played": 4, "won": 2, "lost": 1, "drawn": 1, "points": 28, "pct": 58.33, "note": "Cayó al cuarto puesto tras perder en Lord's."},
    {"rank": 5, "name": "Bangladesh", "played": 4, "won": 2, "lost": 1, "drawn": 1, "points": 28, "pct": 58.33, "note": "Empatada con NZ en PCT tras barrer a Pakistán."},
    {"rank": 6, "name": "India", "played": 9, "won": 4, "lost": 4, "drawn": 1, "points": 52, "pct": 48.15, "note": "Mucho volumen jugado; necesita una racha fuerte."},
    {"rank": 7, "name": "England", "played": 11, "won": 4, "lost": 6, "drawn": 1, "points": 50, "pct": 37.88, "note": "La victoria ante NZ ayuda, pero sigue lejos del corte."},
    {"rank": 8, "name": "Pakistan", "played": 4, "won": 1, "lost": 3, "drawn": 0, "points": 4, "pct": 8.33, "note": "Penalizada con -8 puntos por over-rate."},
    {"rank": 9, "name": "West Indies", "played": 8, "won": 0, "lost": 7, "drawn": 1, "points": 4, "pct": 4.17, "note": "Sin victoria en el ciclo; necesita giro drástico."},
]

WTC_RECENT_MATCHES = [
    {"date": "2026-06-07", "series": "England v New Zealand", "match": "1st Test", "home": "England", "away": "New Zealand", "venue": "Lord's, London", "result": "England ganó por 115 runs", "winner": "ENG"},
    {"date": "2026-05-20", "series": "Bangladesh v Pakistan", "match": "2nd Test", "home": "Bangladesh", "away": "Pakistan", "venue": "Sylhet", "result": "Bangladesh ganó por 78 runs", "winner": "BAN"},
    {"date": "2026-05-12", "series": "Bangladesh v Pakistan", "match": "1st Test", "home": "Bangladesh", "away": "Pakistan", "venue": "Mirpur, Dhaka", "result": "Bangladesh ganó por 104 runs", "winner": "BAN"},
    {"date": "2025-12-22", "series": "New Zealand v West Indies", "match": "3rd Test", "home": "New Zealand", "away": "West Indies", "venue": "Bay Oval, Mount Maunganui", "result": "New Zealand selló la serie 2-0", "winner": "NZ"},
    {"date": "2025-12-12", "series": "New Zealand v West Indies", "match": "2nd Test", "home": "New Zealand", "away": "West Indies", "venue": "Basin Reserve, Wellington", "result": "New Zealand ganó por 9 wickets", "winner": "NZ"},
]

WTC_UPCOMING_MATCHES = [
    {"date": "2026-06-17", "series": "England v New Zealand", "match": "2nd Test", "home": "England", "away": "New Zealand", "venue": "The Oval, London"},
    {"date": "2026-06-25", "series": "England v New Zealand", "match": "3rd Test", "home": "England", "away": "New Zealand", "venue": "Trent Bridge, Nottingham"},
    {"date": "2026-06-25", "series": "West Indies v Sri Lanka", "match": "1st Test", "home": "West Indies", "away": "Sri Lanka", "venue": "Sir Vivian Richards Stadium, North Sound"},
    {"date": "2026-07-03", "series": "West Indies v Sri Lanka", "match": "2nd Test", "home": "West Indies", "away": "Sri Lanka", "venue": "Sir Vivian Richards Stadium, North Sound"},
    {"date": "2026-07-25", "series": "West Indies v Pakistan", "match": "1st Test", "home": "West Indies", "away": "Pakistan", "venue": "Caribbean venue TBC"},
]

WTC_PLAYER_SEEDS = [
    {"name": "Shubman Gill", "country": "India", "role": "Batter", "level": 100.0, "runs": 950, "wickets": 0, "note": "950 runs, cinco cientos y 269 como pico del ciclo."},
    {"name": "Joe Root", "country": "England", "role": "Batter", "level": 97.8, "runs": 937, "wickets": 0, "note": "937 runs; sigue sosteniendo el techo técnico de Inglaterra."},
    {"name": "Travis Head", "country": "Australia", "role": "Batter", "level": 92.4, "runs": 853, "wickets": 0, "note": "Impacto enorme en el dominio australiano."},
    {"name": "Harry Brook", "country": "England", "role": "Batter", "level": 90.7, "runs": 839, "wickets": 0, "note": "Volumen, velocidad y cuatro fifties en el ciclo."},
    {"name": "Mitchell Starc", "country": "Australia", "role": "Bowler", "level": 89.8, "runs": 120, "wickets": 34, "note": "Picos de 7/58 y 6/9; wicket-taking de élite."},
    {"name": "KL Rahul", "country": "India", "role": "Batter", "level": 86.3, "runs": 796, "wickets": 0, "note": "Promedio cerca de 50 y tres cientos."},
    {"name": "Jacob Duffy", "country": "New Zealand", "role": "Bowler", "level": 84.1, "runs": 70, "wickets": 23, "note": "Jugador de la serie ante West Indies; NZ revive con su pelota."},
    {"name": "Keshav Maharaj", "country": "South Africa", "role": "Bowler", "level": 82.9, "runs": 155, "wickets": 18, "note": "7/102 en Rawalpindi y control largo de innings."},
    {"name": "Aiden Markram", "country": "South Africa", "role": "Batter", "level": 81.6, "runs": 510, "wickets": 1, "note": "Runs importantes y campo de élite para la campeona."},
    {"name": "Nahid Rana", "country": "Bangladesh", "role": "Bowler", "level": 80.2, "runs": 35, "wickets": 15, "note": "Spell decisivo en la victoria histórica ante Pakistán."},
]


def fetch_archive(name: str, max_age_hours: float = 18.0) -> bytes | None:
    path = CACHE / f"{name}_json.zip"
    if path.exists() and (time.time() - path.stat().st_mtime) / 3600 < max_age_hours:
        return path.read_bytes()
    url = CRICSHEET.format(name=name)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
        with urllib.request.urlopen(req, timeout=35) as response:
            data = response.read()
        path.write_bytes(data)
        return data
    except Exception as exc:
        print(f"[WARN] Cricsheet download failed for {name}: {exc}", file=sys.stderr)
        return path.read_bytes() if path.exists() else None


def parse_match_date(info: dict) -> date | None:
    dates = info.get("dates") or []
    if not dates:
        return None
    try:
        return date.fromisoformat(str(dates[-1]))
    except ValueError:
        return None


def wicket_credit(wicket: dict, bowler: str) -> bool:
    if wicket.get("kind") in {"run out", "retired hurt", "retired out", "obstructing the field"}:
        return False
    return bool(bowler)


def empty_player() -> dict:
    return {
        "runs": 0,
        "balls": 0,
        "outs": 0,
        "wickets": 0,
        "bowl_balls": 0,
        "bowl_runs": 0,
        "matches": 0,
        "teams": defaultdict(int),
        "formats": defaultdict(float),
        "bat_formats": defaultdict(float),
        "bowl_formats": defaultdict(float),
    }


def add_match(stats: dict, match: dict, archive: dict, today: date) -> bool:
    info = match.get("info", {})
    if info.get("gender") != "male":
        return False
    match_date = parse_match_date(info)
    if not match_date or match_date > today:
        return False
    if (today - match_date).days > archive["days"]:
        return False

    fmt = archive["format"]
    weight = archive["weight"]
    players_by_team = info.get("players") or {}
    for team, names in players_by_team.items():
        for name in names:
            stats[name]["matches"] += 1
            stats[name]["teams"][team] += 1

    for innings in match.get("innings", []):
        for over in innings.get("overs", []):
            for delivery in over.get("deliveries", []):
                batter = delivery.get("batter")
                bowler = delivery.get("bowler")
                runs = delivery.get("runs") or {}
                extras = delivery.get("extras") or {}

                if batter:
                    stats[batter]["runs"] += int(runs.get("batter") or 0)
                    if "wides" not in extras:
                        stats[batter]["balls"] += 1
                if bowler:
                    stats[bowler]["bowl_balls"] += 0 if "wides" in extras else 1
                    bowler_runs = int(runs.get("total") or 0)
                    bowler_runs -= int(extras.get("byes") or 0)
                    bowler_runs -= int(extras.get("legbyes") or 0)
                    bowler_runs -= int(extras.get("penalty") or 0)
                    stats[bowler]["bowl_runs"] += max(0, bowler_runs)

                for wicket in delivery.get("wickets") or []:
                    out = wicket.get("player_out")
                    if out:
                        stats[out]["outs"] += 1
                    if bowler and wicket_credit(wicket, bowler):
                        stats[bowler]["wickets"] += 1

    for name, row in stats.items():
        # Cheap but robust: if a player appeared in the scorecard, translate their
        # current aggregate into a format-specific raw score after this match.
        if row["matches"]:
            batting, bowling, involvement = raw_components(row, fmt)
            row["formats"][fmt] = max(0.0, batting + bowling + involvement) * weight
            # Las listas de bateo/bowling llevan un poco de "involvement" para amortiguar
            # muestras pequeñas, pero sin contaminar (un bowler puro no sube en bateo).
            row["bat_formats"][fmt] = (batting + involvement * 0.3) * weight
            row["bowl_formats"][fmt] = (bowling + involvement * 0.3) * weight
    return True


def raw_components(row: dict, fmt: str) -> tuple[float, float, float]:
    """Devuelve (batting, bowling, involvement) por separado — como en béisbol
    bateadores y lanzadores son disciplinas distintas."""
    runs = row["runs"]
    balls = max(1, row["balls"])
    outs = max(1, row["outs"])
    wickets = row["wickets"]
    bowl_balls = max(1, row["bowl_balls"])
    bowl_runs = row["bowl_runs"]
    matches = max(1, row["matches"])

    avg = runs / outs
    sr = runs / balls * 100
    runs_per_match = runs / matches
    batting = runs_per_match * 1.5 + avg * 0.9 + sr * (0.14 if fmt in {"t20", "franchise"} else 0.07)

    wkts_per_match = wickets / matches
    economy = bowl_runs / bowl_balls * 6
    bowling = wickets * 4.5 + wkts_per_match * 34 - economy * (2.2 if fmt in {"t20", "franchise"} else 1.2)

    involvement = min(14.0, math.log1p(matches) * 4.0)
    return max(0.0, batting), max(0.0, bowling), involvement


def raw_score(row: dict, fmt: str) -> float:
    batting, bowling, involvement = raw_components(row, fmt)
    return max(0.0, batting + bowling + involvement)


def normalise(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values.items(), key=lambda x: x[1], reverse=True)
    top = ordered[0][1] or 1.0
    return {name: round(min(100.0, score / top * 100), 1) for name, score in ordered}


def team_meta(team_name: str) -> dict:
    if team_name in COUNTRIES:
        c = COUNTRIES[team_name]
        flag = f"https://flagcdn.com/24x18/{c['flag']}.png" if c["flag"] else ""
        return {
            "country": team_name,
            "teamCode": c["code"],
            "colors": {"primary": c["primary"], "secondary": c["secondary"]},
            "logo": flag,
        }
    if team_name in TEAM_ALIASES:
        code, primary, secondary, flag = TEAM_ALIASES[team_name]
        return {
            "country": team_name,
            "teamCode": code,
            "colors": {"primary": primary, "secondary": secondary},
            "logo": f"https://flagcdn.com/24x18/{flag}.png" if flag else "",
        }
    return {
        "country": team_name,
        "teamCode": team_name[:3].upper(),
        "colors": {"primary": "#555555", "secondary": "#dddddd"},
        "logo": "",
    }


def infer_country(name: str, row: dict) -> str:
    if name in PLAYER_COUNTRY_OVERRIDES:
        return PLAYER_COUNTRY_OVERRIDES[name]
    for team, _ in sorted(row["teams"].items(), key=lambda x: x[1], reverse=True):
        if team in COUNTRIES or team in TEAM_ALIASES:
            return team
    return next(iter(row["teams"]), "World")


def role_for(row: dict) -> str:
    bat = row["runs"] / max(1, row["matches"])
    bowl = row["wickets"] / max(1, row["matches"])
    if bat >= 24 and bowl >= 0.8:
        return "All-rounder"
    if bowl >= 1.1:
        return "Bowler"
    if bat >= 20:
        return "Batter"
    return "Cricketer"


def player_rows(stats: dict) -> tuple[list[dict], dict[str, dict]]:
    fmts = ("test", "odi", "t20", "franchise")
    format_values = {fmt: normalise({n: r["formats"].get(fmt, 0.0) for n, r in stats.items() if r["formats"].get(fmt, 0.0) > 0}) for fmt in fmts}
    bat_values = {fmt: normalise({n: r["bat_formats"].get(fmt, 0.0) for n, r in stats.items() if r["bat_formats"].get(fmt, 0.0) > 0}) for fmt in fmts}
    bowl_values = {fmt: normalise({n: r["bowl_formats"].get(fmt, 0.0) for n, r in stats.items() if r["bowl_formats"].get(fmt, 0.0) > 0}) for fmt in fmts}

    rows = []
    for name, row in stats.items():
        overall = {fmt: format_values[fmt].get(name, 0.0) for fmt in fmts}
        if max(overall.values()) < 18:
            continue
        score = round(overall["test"] * 0.34 + overall["odi"] * 0.24 + overall["t20"] * 0.18 + overall["franchise"] * 0.14 + max(overall.values()) * 0.10, 1)
        country = infer_country(name, row)
        meta = team_meta(country)
        legend = max(LEGACY_SEEDS.get(name, 0.0), min(96.0, score * 0.55 + math.log1p(row["matches"]) * 5.0))
        format_scores = {fmt: {"overall": overall[fmt], "batting": bat_values[fmt].get(name, 0.0), "bowling": bowl_values[fmt].get(name, 0.0)} for fmt in fmts}
        rows.append({
            "id": name.lower().replace(" ", "-").replace(".", ""),
            "name": name,
            "role": role_for(row),
            "score": score,
            "legendScore": round(legend, 1),
            "stats": {**overall, "runs": row["runs"], "wickets": row["wickets"], "matches": row["matches"]},
            "formatScores": format_scores,
            **meta,
        })
    rows.sort(key=lambda x: x["score"], reverse=True)

    # Por formato, tres rankings: overall, batting (bateadores) y bowling — como en
    # béisbol bateadores y lanzadores van por separado.
    def entry(r: dict, fmt: str, disc: str) -> dict:
        fs = r["formatScores"][fmt]
        return {k: r[k] for k in ("id", "name", "role", "country", "teamCode", "colors", "logo")} | {
            "score": fs[disc], "batting": fs["batting"], "bowling": fs["bowling"], "overall": fs["overall"],
            "runs": r["stats"]["runs"], "wickets": r["stats"]["wickets"],
        }
    groups = {}
    for fmt in fmts:
        elig = [r for r in rows if r["formatScores"][fmt]["overall"] > 0]
        groups[fmt] = {
            "overall": sorted((entry(r, fmt, "overall") for r in elig), key=lambda x: x["score"], reverse=True)[:10],
            "batting": sorted((entry(r, fmt, "batting") for r in elig if r["formatScores"][fmt]["batting"] > 0), key=lambda x: x["score"], reverse=True)[:10],
            "bowling": sorted((entry(r, fmt, "bowling") for r in elig if r["formatScores"][fmt]["bowling"] > 0), key=lambda x: x["score"], reverse=True)[:10],
        }
    return rows[:10], groups


def trophy_score(t: dict) -> float:
    return round(t["odi_wc"] * 14 + t["t20_wc"] * 9 + t["ct"] * 6 + t["wtc"] * 10, 1)


def trophy_rows() -> list[dict]:
    rows = []
    for t in TROPHIES:
        rows.append({
            **team_meta(t["name"]),
            "name": t["name"],
            "score": trophy_score(t),
            "stats": {k: t[k] for k in ("odi_wc", "t20_wc", "ct", "wtc")},
            "note": t["note"],
        })
    return sorted(rows, key=lambda x: x["score"], reverse=True)


def wtc_rows(groups: dict[str, list[dict]]) -> list[dict]:
    rows = []
    for seed in WTC_STANDINGS:
        meta = team_meta(seed["name"])
        rows.append({
            **meta,
            "name": seed["name"],
            "rank": seed["rank"],
            "score": seed["pct"],
            "pct": seed["pct"],
            "played": seed["played"],
            "won": seed["won"],
            "lost": seed["lost"],
            "drawn": seed["drawn"],
            "points": seed["points"],
            "note": seed["note"],
        })
    return rows


def wtc_player_rows() -> list[dict]:
    rows = []
    for seed in WTC_PLAYER_SEEDS:
        meta = team_meta(seed["country"])
        legend = max(
            LEGACY_SEEDS.get(seed["name"], 0.0),
            min(96.0, seed["level"] * 0.48 + math.log1p(seed["runs"] + seed["wickets"] * 35) * 5.4),
        )
        rows.append({
            **meta,
            "id": seed["name"].lower().replace(" ", "-").replace(".", ""),
            "name": seed["name"],
            "role": seed["role"],
            "score": seed["level"],
            "level": seed["level"],
            "legendScore": round(legend, 1),
            "stats": {"runs": seed["runs"], "wickets": seed["wickets"]},
            "note": seed["note"],
        })
    return sorted(rows, key=lambda x: x["level"], reverse=True)[:10]


def main() -> int:
    today = datetime.now(timezone.utc).date()
    stats = defaultdict(empty_player)
    source = {"archives": [], "matches": 0}

    for archive in ARCHIVES.values():
        data = fetch_archive(archive["name"])
        if not data:
            continue
        used = 0
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            print(f"[WARN] Cricsheet archive for {archive['name']} was not a valid ZIP", file=sys.stderr)
            continue
        with zf:
            for name in zf.namelist():
                if not name.endswith(".json"):
                    continue
                try:
                    match = json.loads(zf.read(name))
                except Exception:
                    continue
                if add_match(stats, match, archive, today):
                    used += 1
        source["archives"].append({"name": archive["label"], "matches": used})
        source["matches"] += used

    if source["matches"] == 0:
        raise RuntimeError("No Cricsheet matches available; keeping existing cricket_data.js unchanged.")

    players, groups = player_rows(stats)
    road = sorted(players, key=lambda x: x["legendScore"], reverse=True)[:10]

    payload = {
        "UPDATED": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "IMPORTANCE": 5.8,
        "SOURCE": {
            "mode": "Cricsheet completed scorecards + Hermes scoring",
            "matches": source["matches"],
            "archives": source["archives"],
            "note": "Daily-after-results model: no live scores, recalculates from completed Cricsheet scorecards.",
        },
        "PLAYERS": players,
        "FORMAT_KINGS": {
            "test": groups.get("test", []),
            "odi": groups.get("odi", []),
            "t20": groups.get("t20", []),
            "franchise": groups.get("franchise", []),
        },
        "WTC": {
            "cycle": "2025-27",
            "mode": "ICC table snapshot + Hermes WTC player index",
            "sourceNote": "Standings snapshot through England v New Zealand, 1st Test, 8 Jun 2026.",
            "standings": wtc_rows(groups),
            "recentMatches": WTC_RECENT_MATCHES,
            "upcomingMatches": WTC_UPCOMING_MATCHES,
            "players": wtc_player_rows(),
        },
        "TROPHIES": trophy_rows(),
        "ROAD_TO_GLORY": {"playerThreshold": HISTORIC_TOP_10_THRESHOLD, "players": road},
    }
    OUT.write_text(
        "// Cricket Tracker - generated from Cricsheet completed scorecards + Hermes scoring.\n"
        "// Run `python3 scripts/update_cricket_data.py` to refresh.\n"
        f"window.CRICKET_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )
    print(f"Updated {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
