#!/usr/bin/env python3
"""Men's national football data: Elo snapshot and historical dynasties."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "football_data.js"


COUNTRIES = {
    "Argentina": {"code": "ARG", "cc2": "ar", "colors": {"primary": "#75AADB", "secondary": "#FFFFFF"}},
    "Spain": {"code": "ESP", "cc2": "es", "colors": {"primary": "#AA151B", "secondary": "#F1BF00"}},
    "France": {"code": "FRA", "cc2": "fr", "colors": {"primary": "#002395", "secondary": "#ED2939"}},
    "England": {"code": "ENG", "cc2": "gb-eng", "colors": {"primary": "#FFFFFF", "secondary": "#CE1124"}},
    "Portugal": {"code": "POR", "cc2": "pt", "colors": {"primary": "#006600", "secondary": "#FF0000"}},
    "Brazil": {"code": "BRA", "cc2": "br", "colors": {"primary": "#009C3B", "secondary": "#FFDF00"}},
    "Netherlands": {"code": "NED", "cc2": "nl", "colors": {"primary": "#FF4F00", "secondary": "#21468B"}},
    "Germany": {"code": "GER", "cc2": "de", "colors": {"primary": "#000000", "secondary": "#DD0000"}},
    "Italy": {"code": "ITA", "cc2": "it", "colors": {"primary": "#0066B3", "secondary": "#009246"}},
    "Uruguay": {"code": "URU", "cc2": "uy", "colors": {"primary": "#75AADB", "secondary": "#FFFFFF"}},
    "Belgium": {"code": "BEL", "cc2": "be", "colors": {"primary": "#000000", "secondary": "#EF3340"}},
    "Croatia": {"code": "CRO", "cc2": "hr", "colors": {"primary": "#FF0000", "secondary": "#171796"}},
}


# Current men's national-team Elo-style snapshot.
# Ratings are kept as a curated Hermes snapshot so the UI can update daily without
# depending on a brittle scraper. Refresh these seeds when the source snapshot changes.
CURRENT_RAW = [
    ("Argentina", 2133, 1, "Campeón mundial y Copa América; ciclo Scaloni sostiene el pico Elo."),
    ("Spain", 2109, 2, "Euro vigente y bloque joven de altísimo rendimiento."),
    ("France", 2029, 3, "Finalista mundial reciente; profundidad ofensiva y defensiva."),
    ("England", 2017, 4, "Finalista de Euro; rating alto por consistencia ante élite UEFA."),
    ("Portugal", 1997, 5, "Plantilla top y fase clasificatoria fuerte."),
    ("Brazil", 1985, 6, "Histórico gigante todavía en zona top 10 pese a ciclo irregular."),
    ("Netherlands", 1976, 7, "Bloque estable con muy buen diferencial ante rivales fuertes."),
    ("Germany", 1958, 8, "Rebote competitivo tras la Euro como anfitrión."),
    ("Italy", 1945, 9, "Euro 2020 todavía pesa; ciclo actual busca volver a pico mundial."),
    ("Uruguay", 1934, 10, "Ciclo Bielsa y resultados CONMEBOL elevan el rating."),
]


CURRENT_DYNASTY_SEEDS = {
    "Argentina": {"cycleYears": 3.2, "currentWorldCups": 1, "currentContinental": 2, "recentFinals": 3, "ageCurve": 0.78},
    "Spain": {"cycleYears": 1.6, "currentWorldCups": 0, "currentContinental": 1, "recentFinals": 1, "ageCurve": 0.96},
    "France": {"cycleYears": 2.8, "currentWorldCups": 1, "currentContinental": 0, "recentFinals": 2, "ageCurve": 0.90},
    "England": {"cycleYears": 2.4, "currentWorldCups": 0, "currentContinental": 0, "recentFinals": 2, "ageCurve": 0.88},
    "Portugal": {"cycleYears": 1.8, "currentWorldCups": 0, "currentContinental": 0, "recentFinals": 0, "ageCurve": 0.86},
    "Brazil": {"cycleYears": 1.2, "currentWorldCups": 0, "currentContinental": 0, "recentFinals": 1, "ageCurve": 0.84},
    "Netherlands": {"cycleYears": 1.4, "currentWorldCups": 0, "currentContinental": 0, "recentFinals": 0, "ageCurve": 0.85},
    "Germany": {"cycleYears": 1.0, "currentWorldCups": 0, "currentContinental": 0, "recentFinals": 0, "ageCurve": 0.82},
    "Italy": {"cycleYears": 0.9, "currentWorldCups": 0, "currentContinental": 0, "recentFinals": 0, "ageCurve": 0.78},
    "Uruguay": {"cycleYears": 1.3, "currentWorldCups": 0, "currentContinental": 0, "recentFinals": 0, "ageCurve": 0.83},
}


# Grupos del Mundial 2026 para el top 10.
WC2026_GROUPS: dict[str, dict] = {
    "ARG": {"group": "J", "groupTeams": ["Argentina", "Argelia", "Austria", "Jordania"]},
    "ESP": {"group": "H", "groupTeams": ["España", "Cabo Verde", "Arabia Saudí", "Uruguay"]},
    "FRA": {"group": "I", "groupTeams": ["Francia", "Senegal", "Irak", "Noruega"]},
    "ENG": {"group": "L", "groupTeams": ["Inglaterra", "Croacia", "Ghana", "Panamá"]},
    "POR": {"group": "K", "groupTeams": ["Portugal", "RD Congo", "Uzbekistán", "Colombia"]},
    "BRA": {"group": "C", "groupTeams": ["Brasil", "Marruecos", "Haití", "Escocia"]},
    "NED": {"group": "F", "groupTeams": ["Países Bajos", "Japón", "Suecia", "Túnez"]},
    "GER": {"group": "E", "groupTeams": ["Alemania", "Curazao", "Costa de Marfil", "Ecuador"]},
    "URU": {"group": "H", "groupTeams": ["España", "Cabo Verde", "Arabia Saudí", "Uruguay"]},
}

# Partidos del Mundial 2026 — jornadas 1 y 2, solo top 10 Elo.
# Horarios marcados TBD hasta cargar kickoffs oficiales en el snapshot.
WC2026_MATCHES: list[dict] = [
    # Jornada 1
    {"round": 1, "date": "2026-06-13", "timeET": "TBD", "home": "BRA", "homeName": "Brasil",         "away": "MAR", "awayName": "Marruecos",       "group": "C", "venue": "MetLife Stadium",         "city": "East Rutherford"},
    {"round": 1, "date": "2026-06-14", "timeET": "TBD", "home": "GER", "homeName": "Alemania",       "away": "CUW", "awayName": "Curazao",         "group": "E", "venue": "NRG Stadium",             "city": "Houston"},
    {"round": 1, "date": "2026-06-14", "timeET": "TBD", "home": "NED", "homeName": "Países Bajos",   "away": "JPN", "awayName": "Japón",           "group": "F", "venue": "AT&T Stadium",            "city": "Dallas"},
    {"round": 1, "date": "2026-06-15", "timeET": "TBD", "home": "KSA", "homeName": "Arabia Saudí",   "away": "URU", "awayName": "Uruguay",         "group": "H", "venue": "Hard Rock Stadium",       "city": "Miami"},
    {"round": 1, "date": "2026-06-15", "timeET": "TBD", "home": "ESP", "homeName": "España",         "away": "CPV", "awayName": "Cabo Verde",      "group": "H", "venue": "Mercedes-Benz Stadium",   "city": "Atlanta"},
    {"round": 1, "date": "2026-06-16", "timeET": "TBD", "home": "FRA", "homeName": "Francia",        "away": "SEN", "awayName": "Senegal",         "group": "I", "venue": "MetLife Stadium",         "city": "East Rutherford"},
    {"round": 1, "date": "2026-06-16", "timeET": "TBD", "home": "ARG", "homeName": "Argentina",      "away": "ALG", "awayName": "Argelia",         "group": "J", "venue": "Arrowhead Stadium",       "city": "Kansas City"},
    {"round": 1, "date": "2026-06-17", "timeET": "TBD", "home": "ENG", "homeName": "Inglaterra",     "away": "CRO", "awayName": "Croacia",         "group": "L", "venue": "AT&T Stadium",            "city": "Dallas"},
    {"round": 1, "date": "2026-06-17", "timeET": "TBD", "home": "POR", "homeName": "Portugal",       "away": "COD", "awayName": "RD Congo",        "group": "K", "venue": "NRG Stadium",             "city": "Houston"},
    # Jornada 2
    {"round": 2, "date": "2026-06-19", "timeET": "TBD", "home": "BRA", "homeName": "Brasil",         "away": "HAI", "awayName": "Haití",           "group": "C", "venue": "Lincoln Financial Field", "city": "Filadelfia"},
    {"round": 2, "date": "2026-06-20", "timeET": "TBD", "home": "GER", "homeName": "Alemania",       "away": "CIV", "awayName": "Costa de Marfil", "group": "E", "venue": "BMO Field",                "city": "Toronto"},
    {"round": 2, "date": "2026-06-20", "timeET": "TBD", "home": "NED", "homeName": "Países Bajos",   "away": "SWE", "awayName": "Suecia",          "group": "F", "venue": "NRG Stadium",             "city": "Houston"},
    {"round": 2, "date": "2026-06-21", "timeET": "TBD", "home": "URU", "homeName": "Uruguay",        "away": "CPV", "awayName": "Cabo Verde",      "group": "H", "venue": "Hard Rock Stadium",       "city": "Miami"},
    {"round": 2, "date": "2026-06-21", "timeET": "TBD", "home": "ESP", "homeName": "España",         "away": "KSA", "awayName": "Arabia Saudí",    "group": "H", "venue": "Mercedes-Benz Stadium",   "city": "Atlanta"},
    {"round": 2, "date": "2026-06-22", "timeET": "TBD", "home": "FRA", "homeName": "Francia",        "away": "IRQ", "awayName": "Irak",            "group": "I", "venue": "Lincoln Financial Field", "city": "Filadelfia"},
    {"round": 2, "date": "2026-06-22", "timeET": "TBD", "home": "ARG", "homeName": "Argentina",      "away": "AUT", "awayName": "Austria",         "group": "J", "venue": "AT&T Stadium",            "city": "Dallas"},
    {"round": 2, "date": "2026-06-23", "timeET": "TBD", "home": "ENG", "homeName": "Inglaterra",     "away": "GHA", "awayName": "Ghana",           "group": "L", "venue": "Gillette Stadium",        "city": "Boston"},
    {"round": 2, "date": "2026-06-23", "timeET": "TBD", "home": "POR", "homeName": "Portugal",       "away": "UZB", "awayName": "Uzbekistán",      "group": "K", "venue": "NRG Stadium",             "city": "Houston"},
]

# Elos estimados para selecciones que no están en el top 10 CURRENT_RAW.
OPPONENT_ELOS: dict[str, int] = {
    "ALG": 1800, "AUT": 1840, "COD": 1665, "CPV": 1615, "CRO": 1835, "CUW": 1560,
    "CIV": 1820, "ECU": 1750, "GHA": 1720, "HAI": 1545, "IRQ": 1660,
    "JPN": 1785, "KSA": 1605, "MAR": 1875, "SEN": 1795, "SWE": 1790,
    "UZB": 1625,
}


DYNASTIES_RAW = [
    {
        "name": "Brazil",
        "era": "1958-1970",
        "yearsNo1": 9.2,
        "weeksNo1": 480,
        "worldCups": 3,
        "continentalTitles": 0,
        "matchCount": 118,
        "peakElo": 2160,
        "note": "Pelé, Garrincha, Jairzinho y tres Mundiales en cuatro torneos.",
    },
    {
        "name": "Spain",
        "era": "2008-2012",
        "yearsNo1": 4.1,
        "weeksNo1": 214,
        "worldCups": 1,
        "continentalTitles": 2,
        "matchCount": 72,
        "peakElo": 2164,
        "note": "Euro-Mundial-Euro: la dinastía de posesión más limpia de la era moderna.",
    },
    {
        "name": "Argentina",
        "era": "2021-present",
        "yearsNo1": 3.2,
        "weeksNo1": 166,
        "worldCups": 1,
        "continentalTitles": 2,
        "matchCount": 58,
        "peakElo": 2133,
        "note": "Copa América, Mundial y nueva Copa América en una racha larguísima sin derrota.",
    },
    {
        "name": "France",
        "era": "1998-2001",
        "yearsNo1": 3.0,
        "weeksNo1": 156,
        "worldCups": 1,
        "continentalTitles": 1,
        "matchCount": 55,
        "peakElo": 2118,
        "note": "Zidane, Desailly, Thuram, Henry: Mundial y Euro consecutivos.",
    },
    {
        "name": "Germany",
        "era": "1972-1976",
        "yearsNo1": 3.7,
        "weeksNo1": 193,
        "worldCups": 1,
        "continentalTitles": 1,
        "matchCount": 61,
        "peakElo": 2105,
        "note": "Beckenbauer y Müller sostienen Euro 72, Mundial 74 y final Euro 76.",
    },
    {
        "name": "Italy",
        "era": "1934-1938",
        "yearsNo1": 3.5,
        "weeksNo1": 182,
        "worldCups": 2,
        "continentalTitles": 0,
        "matchCount": 46,
        "peakElo": 2070,
        "note": "Primer bicampeón mundial; dominio de los años treinta.",
    },
    {
        "name": "Brazil",
        "era": "1994-2002",
        "yearsNo1": 5.6,
        "weeksNo1": 292,
        "worldCups": 2,
        "continentalTitles": 2,
        "matchCount": 124,
        "peakElo": 2120,
        "note": "Romário, Ronaldo, Rivaldo y Ronaldinho: dos Mundiales y una final más.",
    },
    {
        "name": "France",
        "era": "2018-2022",
        "yearsNo1": 2.8,
        "weeksNo1": 146,
        "worldCups": 1,
        "continentalTitles": 0,
        "matchCount": 67,
        "peakElo": 2096,
        "note": "Mundial 2018, Nations League y final de Qatar 2022.",
    },
    {
        "name": "Netherlands",
        "era": "1974-1978",
        "yearsNo1": 2.9,
        "weeksNo1": 151,
        "worldCups": 0,
        "continentalTitles": 0,
        "matchCount": 48,
        "peakElo": 2088,
        "note": "Fútbol total: dos finales mundialistas y enorme pico Elo sin título.",
    },
    {
        "name": "Germany",
        "era": "2014-2017",
        "yearsNo1": 2.5,
        "weeksNo1": 130,
        "worldCups": 1,
        "continentalTitles": 0,
        "matchCount": 63,
        "peakElo": 2075,
        "note": "Mundial 2014 y Confederaciones 2017 con profundidad de plantilla.",
    },
    # --- Eras históricas incorporadas ---
    {
        "name": "Argentina",
        "era": "1978-1986",
        "yearsNo1": 3.5,
        "weeksNo1": 182,
        "worldCups": 2,
        "continentalTitles": 1,
        "matchCount": 88,
        "peakElo": 2095,
        "note": "Kempes 78 y Maradona 86: dos Mundiales con estilos y leyendas opuestos.",
    },
    {
        "name": "Uruguay",
        "era": "1928-1950",
        "yearsNo1": 4.5,
        "weeksNo1": 234,
        "worldCups": 2,
        "continentalTitles": 2,
        "matchCount": 65,
        "peakElo": 2065,
        "note": "Fundadores del fútbol moderno: primer Mundial, Copa Am 35/42 y el Maracanazo.",
    },
    {
        "name": "Germany",
        "era": "1980-1990",
        "yearsNo1": 4.0,
        "weeksNo1": 208,
        "worldCups": 1,
        "continentalTitles": 1,
        "matchCount": 112,
        "peakElo": 2095,
        "note": "Euro 80, tres finales mundialistas en ocho años y campeones en Italia 90.",
    },
    {
        "name": "Italy",
        "era": "2000-2006",
        "yearsNo1": 2.0,
        "weeksNo1": 104,
        "worldCups": 1,
        "continentalTitles": 0,
        "matchCount": 68,
        "peakElo": 2078,
        "note": "Final Euro 2000 y campeones del mundo en Alemania 2006 con Cannavaro.",
    },
    {
        "name": "Italy",
        "era": "1982-1984",
        "yearsNo1": 1.5,
        "weeksNo1": 78,
        "worldCups": 1,
        "continentalTitles": 0,
        "matchCount": 38,
        "peakElo": 2062,
        "note": "Paolo Rossi y el tercer Mundial italiano; pico breve pero irrepetible.",
    },
    {
        "name": "Germany",
        "era": "1954-1956",
        "yearsNo1": 1.5,
        "weeksNo1": 78,
        "worldCups": 1,
        "continentalTitles": 0,
        "matchCount": 32,
        "peakElo": 2042,
        "note": "Milagro de Berna: Alemania Occidental derrota a la invicta Hungría en la final.",
    },
]


def _id(name: str, suffix: str = "") -> str:
    base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return f"{base}_{suffix}" if suffix else base


def team_meta(name: str) -> dict:
    meta = COUNTRIES[name]
    return {
        "id": _id(name),
        "name": name,
        "teamCode": meta["code"],
        "country": name,
        "logo": f"https://flagcdn.com/24x18/{meta['cc2']}.png",
        "colors": meta["colors"],
    }


def build_teams() -> list[dict]:
    rows = []
    max_elo = max(r[1] for r in CURRENT_RAW)
    min_elo = min(r[1] for r in CURRENT_RAW)
    span = max_elo - min_elo or 1
    for name, elo, source_rank, note in CURRENT_RAW:
        score = 70 + (elo - min_elo) / span * 30
        row = team_meta(name)
        row.update({
            "rank": len(rows) + 1,
            "elo": elo,
            "eloScore": round(score, 1),
            "sourceRank": source_rank,
            "worldCups": 0,
            "continentalTitles": 0,
            "note": note,
        })
        rows.append(row)
    trophy_map = {
        "Argentina": (3, 16), "Spain": (1, 4), "France": (2, 2), "England": (1, 0),
        "Portugal": (0, 1), "Brazil": (5, 9), "Netherlands": (0, 1), "Germany": (4, 3),
        "Italy": (4, 2), "Uruguay": (2, 15),
    }
    for row in rows:
        wc, cont = trophy_map.get(row["name"], (0, 0))
        row["worldCups"] = wc
        row["continentalTitles"] = cont
    return rows


def dynasty_raw(row: dict) -> float:
    return (
        row["yearsNo1"] * 10.0
        + row["worldCups"] * 28.0
        + row["continentalTitles"] * 10.0
        + max(0, row["peakElo"] - 1900) / 18.0
    )


def _enrich_dynasties(rows: list[dict]) -> list[dict]:
    """Auto-compute yearsNo1 for active ('present') dynasties from era start year."""
    today = date.today()
    enriched = []
    for row in rows:
        if row["era"].endswith("present"):
            start_year = int(row["era"].split("-")[0])
            elapsed = (today - date(start_year, 1, 1)).days / 365.25
            row = dict(row)
            row["yearsNo1"] = round(elapsed, 1)
        enriched.append(row)
    return enriched


def build_dynasties() -> list[dict]:
    scored = [(dynasty_raw(r), r) for r in _enrich_dynasties(DYNASTIES_RAW)]
    max_raw = max(raw for raw, _ in scored)
    out = []
    for raw, item in sorted(scored, reverse=True):
        row = team_meta(item["name"])
        era_slug = item["era"].replace("-", "_").replace("present", "now")
        row["id"] = _id(item["name"], era_slug)
        row.update({
            "rank": len(out) + 1,
            "era": item["era"],
            "yearsNo1": item["yearsNo1"],
            "weeksNo1": item["weeksNo1"],
            "matchCount": item["matchCount"],
            "worldCups": item["worldCups"],
            "continentalTitles": item["continentalTitles"],
            "peakElo": item["peakElo"],
            "dynastyScore": round(raw / max_raw * 100, 1),
            "note": item["note"],
        })
        out.append(row)
    return out[:10]


def build_contenders(teams: list[dict], threshold: float) -> list[dict]:
    rows = []
    for team in teams:
        seed = CURRENT_DYNASTY_SEEDS.get(team["name"], {})
        cycle_years = float(seed.get("cycleYears", 1.0))
        current_world_cups = int(seed.get("currentWorldCups", 0))
        current_continental = int(seed.get("currentContinental", 0))
        recent_finals = int(seed.get("recentFinals", 0))
        age_curve = float(seed.get("ageCurve", 0.8))
        elo_component = max(0.0, team["elo"] - 1900) / 18.0
        raw = (
            cycle_years * 10.0
            + current_world_cups * 28.0
            + current_continental * 10.0
            + recent_finals * 6.0
            + elo_component
            + age_curve * 14.0
        )
        potential = min(100.0, round(raw / max(threshold, 1.0) * 100.0, 1))
        gap = max(0.0, round(threshold - raw, 1))
        row = dict(team)
        row.update({
            "dynastyPotential": potential,
            "rawDynastyPotential": round(raw, 1),
            "gapToDynastyTop10": gap,
            "cycleYears": cycle_years,
            "currentWorldCups": current_world_cups,
            "currentContinentalTitles": current_continental,
            "recentFinals": recent_finals,
            "ageCurve": age_curve,
            "note": (
                "Ya está proyectada en zona top 10 si sostiene el ciclo"
                if gap <= 0 else
                f"A {gap:.1f} puntos brutos del umbral dinástico"
            ),
        })
        rows.append(row)
    return sorted(rows, key=lambda r: (r["dynastyPotential"], r["elo"]), reverse=True)[:10]


def build_world_cup(teams: list[dict]) -> dict:
    today = date.today()
    start = date(2026, 6, 11)
    end = date(2026, 7, 19)
    if today < start:
        phase = "pre_tournament"
    elif today <= end:
        phase = "group_stage"
    else:
        phase = "finished"
    elo_map = {t["teamCode"]: t["elo"] for t in teams}
    elo_map.update(OPPONENT_ELOS)
    upcoming = []
    for m in WC2026_MATCHES:
        if date.fromisoformat(m["date"]) >= today:
            upcoming.append({**m, "homeElo": elo_map.get(m["home"]), "awayElo": elo_map.get(m["away"])})
    return {
        "edition": "26ª edición",
        "hosts": "Estados Unidos · México · Canadá",
        "startDate": "2026-06-11",
        "finalDate": "2026-07-19",
        "teams": 48,
        "phase": phase,
        "groups": WC2026_GROUPS,
        "upcomingMatches": upcoming,
    }


def attach_next_matches(teams: list[dict], world_cup: dict) -> None:
    by_code = {team["teamCode"]: team for team in teams}
    for match in world_cup.get("upcomingMatches", []):
        for side, other in (("home", "away"), ("away", "home")):
            code = match.get(side)
            team = by_code.get(code)
            if not team or team.get("nextMatch"):
                continue
            team["nextMatch"] = {
                "date": match["date"],
                "round": match["round"],
                "opponent": match[f"{other}Name"],
                "opponentCode": match[other],
                "venue": match["venue"],
                "city": match["city"],
                "group": match["group"],
                "type": "Mundial 2026",
            }


def importance() -> float:
    today = date.today()
    year = today.year
    if year == 2026 and date(2026, 6, 11) <= today <= date(2026, 7, 19):
        return 10.0
    if year in {2028, 2032} and date(year, 6, 1) <= today <= date(year, 7, 20):
        return 8.5
    if year in {2026, 2030, 2034} and date(year, 5, 20) <= today <= date(year, 8, 1):
        return 9.0
    return 6.0


def write_data() -> None:
    teams = build_teams()
    world_cup = build_world_cup(teams)
    attach_next_matches(teams, world_cup)
    dynasties = build_dynasties()
    threshold = dynasties[9]["dynastyScore"] if len(dynasties) >= 10 else 70.0
    raw_threshold = min(dynasty_raw(row) for row in DYNASTIES_RAW)
    contenders = build_contenders(teams, raw_threshold)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "UPDATED": updated,
        "SEASON": "Men's national teams",
        "SOURCE": {
            "name": "Hermes curated snapshot using World Football Elo / MoreElo-style ratings",
            "notes": "Daily-generated static snapshot; update CURRENT_RAW seeds when source rankings move.",
            "through": updated,
        },
        "IMPORTANCE": importance(),
        "TEAMS": teams,
        "WORLD_CUP_2026": world_cup,
        "ROAD_TO_GLORY": {
            "dynastyThreshold": threshold,
            "rawDynastyThreshold": round(raw_threshold, 1),
            "dynasties": dynasties,
            "currentContenders": contenders,
        },
    }
    OUT.write_text(
        f"// Auto-generated {updated}\nwindow.FOOTBALL_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT.relative_to(ROOT)} · {len(teams)} teams · {len(dynasties)} dynasties")


if __name__ == "__main__":
    write_data()
