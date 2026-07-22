#!/usr/bin/env python3
"""Men's national football data: Elo snapshot and historical dynasties."""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
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


# ─────────────────────────────────────────────────────────────────────────────
# Resultados reales + variación Elo
# ─────────────────────────────────────────────────────────────────────────────
# El snapshot curado (CURRENT_RAW / OPPONENT_ELOS) es el rating de partida; a
# partir de él reproducimos los partidos de selecciones publicados por ESPN y
# aplicamos la fórmula de World Football Elo para mostrar cuánto Elo gana o
# pierde cada equipo tras cada partido (chips verdes/rojos en la web).

# Punto de partida del replay. Reproducimos desde el arranque del Mundial 2026
# para que las variaciones acumuladas del torneo se reflejen en el Elo actual.
REPLAY_START = date(2026, 6, 11)
REPLAY_MAX_DAYS = 60  # red de seguridad: nunca reproducir más de N días hacia atrás

# Ligas de selecciones que consultamos en el scoreboard de ESPN (slug -> etiqueta ES).
ESPN_NATIONAL_LEAGUES: dict[str, str] = {
    "fifa.world": "Mundial 2026",
    "fifa.friendly": "Amistoso",
    "uefa.nations": "UEFA Nations League",
    "uefa.euroq": "Clasificación Euro",
    "concacaf.nations.league": "CONCACAF Nations League",
}

# K-factor (peso del partido) por liga; fórmula eloratings.net.
K_BY_LEAGUE: dict[str, int] = {
    "fifa.world": 60,
    "uefa.euroq": 40,
    "uefa.nations": 40,
    "concacaf.nations.league": 35,
    "fifa.friendly": 20,
}
DEFAULT_K = 30
# Ventaja de campo: 0 en torneos a sede neutral (Mundial), ~60 en el resto.
HOME_ADV_BY_LEAGUE: dict[str, int] = {"fifa.world": 0}
DEFAULT_HOME_ADV = 60

# Elo de partida por selección (abreviatura ESPN). Top 10 = CURRENT_RAW; el resto
# son estimaciones curadas tipo World Football Elo para tener un universo cerrado.
ELO_SEED: dict[str, int] = {
    "ARG": 2133, "ESP": 2109, "FRA": 2029, "ENG": 2017, "POR": 1997,
    "BRA": 1985, "NED": 1976, "GER": 1958, "ITA": 1945, "URU": 1934,
    "COL": 1960, "BEL": 1925, "MAR": 1875, "AUT": 1840, "CRO": 1835,
    "CIV": 1820, "SUI": 1820, "NOR": 1815, "USA": 1800, "ALG": 1800,
    "SEN": 1795, "SWE": 1790, "MEX": 1790, "SCO": 1790, "JPN": 1785,
    "TUR": 1780, "KOR": 1770, "IRN": 1760, "CZE": 1760, "CAN": 1760,
    "ECU": 1750, "EGY": 1740, "AUS": 1730, "PAR": 1730, "GHA": 1720,
    "TUN": 1700, "BIH": 1700, "QAT": 1690, "RSA": 1670, "COD": 1665,
    "IRQ": 1660, "PAN": 1655, "UZB": 1625, "CPV": 1615, "KSA": 1605,
    "CUW": 1560, "NZL": 1560, "JOR": 1545, "HAI": 1545,
}
DEFAULT_SEED_ELO = 1600

# Nombre en español por abreviatura (para la UI). Fallback: displayName de ESPN.
NAME_ES: dict[str, str] = {
    "ARG": "Argentina", "ESP": "España", "FRA": "Francia", "ENG": "Inglaterra",
    "POR": "Portugal", "BRA": "Brasil", "NED": "Países Bajos", "GER": "Alemania",
    "ITA": "Italia", "URU": "Uruguay", "COL": "Colombia", "BEL": "Bélgica",
    "MAR": "Marruecos", "AUT": "Austria", "CRO": "Croacia", "CIV": "Costa de Marfil",
    "SUI": "Suiza", "NOR": "Noruega", "USA": "Estados Unidos", "ALG": "Argelia",
    "SEN": "Senegal", "SWE": "Suecia", "MEX": "México", "SCO": "Escocia",
    "JPN": "Japón", "TUR": "Türkiye", "KOR": "Corea del Sur", "IRN": "Irán",
    "CZE": "Chequia", "CAN": "Canadá", "ECU": "Ecuador", "EGY": "Egipto",
    "AUS": "Australia", "PAR": "Paraguay", "GHA": "Ghana", "TUN": "Túnez",
    "BIH": "Bosnia", "QAT": "Catar", "RSA": "Sudáfrica", "COD": "RD Congo",
    "IRQ": "Irak", "PAN": "Panamá", "UZB": "Uzbekistán", "CPV": "Cabo Verde",
    "KSA": "Arabia Saudí", "CUW": "Curazao", "NZL": "Nueva Zelanda",
    "JOR": "Jordania", "HAI": "Haití",
}

# Selecciones destacadas: las del top 10 curado. Solo mostramos en el feed de
# resultados los partidos que involucran a alguna de ellas.
FEATURED_CODES = {COUNTRIES[name]["code"] for name, *_ in CURRENT_RAW}


def _expected_score(elo_a: float, elo_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400.0))


def _goal_index(goal_diff: int) -> float:
    gd = abs(goal_diff)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11 + gd) / 8.0


def _fetch_espn_events(slug: str, start: date, end: date) -> list[dict]:
    url = (
        f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard"
        f"?dates={start:%Y%m%d}-{end:%Y%m%d}&limit=300"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except Exception as exc:  # noqa: BLE001 - never break the build on a feed hiccup
        print(f"[WARN] ESPN soccer {slug} unavailable: {exc}", file=sys.stderr)
        return []
    return data.get("events", [])


def _parse_match(event: dict, slug: str) -> dict | None:
    """Convierte un evento ESPN finalizado en un dict de partido normalizado."""
    status = event.get("status", {}).get("type", {})
    if not status.get("completed"):
        return None
    comps = event.get("competitions", [{}])[0].get("competitors", [])
    if len(comps) != 2:
        return None
    sides = {}
    for c in comps:
        team = c.get("team", {})
        code = (team.get("abbreviation") or "").upper()
        try:
            score = int(c.get("score"))
        except (TypeError, ValueError):
            return None
        sides[c.get("homeAway", "home")] = {
            "code": code,
            "espnName": team.get("displayName") or code,
            "name": NAME_ES.get(code, team.get("displayName") or code),
            "logo": team.get("logo") or team.get("flag"),
            "score": score,
        }
    if "home" not in sides or "away" not in sides:
        return None
    return {
        "id": event.get("id"),
        "date": (event.get("date") or "")[:10],
        "slug": slug,
        "league": ESPN_NATIONAL_LEAGUES.get(slug, slug),
        "home": sides["home"],
        "away": sides["away"],
    }


def _collect_matches(start: date, end: date) -> list[dict]:
    seen: set[str] = set()
    matches: list[dict] = []
    for slug in ESPN_NATIONAL_LEAGUES:
        for event in _fetch_espn_events(slug, start, end):
            match = _parse_match(event, slug)
            if not match:
                continue
            key = match["id"] or f"{match['date']}-{match['home']['code']}-{match['away']['code']}"
            if key in seen:
                continue
            seen.add(key)
            matches.append(match)
    matches.sort(key=lambda m: (m["date"], m["id"] or ""))
    return matches


def replay_elo(seed_elos: dict[str, int]) -> tuple[list[dict], dict[str, float], dict[str, float], dict[str, int]]:
    """Reproduce los partidos del periodo y devuelve (feed, elos_finales, deltas_netos, partidos)."""
    today = date.today()
    start = max(REPLAY_START, today - timedelta(days=REPLAY_MAX_DAYS))
    matches = _collect_matches(start, today)
    elos: dict[str, float] = {}

    def elo_of(code: str) -> float:
        if code not in elos:
            elos[code] = float(seed_elos.get(code, DEFAULT_SEED_ELO))
        return elos[code]

    net_delta: dict[str, float] = {}
    played: dict[str, int] = {}
    feed: list[dict] = []
    for m in matches:
        hc, ac = m["home"]["code"], m["away"]["code"]
        hs, as_ = m["home"]["score"], m["away"]["score"]
        eh, ea = elo_of(hc), elo_of(ac)
        k = K_BY_LEAGUE.get(m["slug"], DEFAULT_K)
        home_adv = HOME_ADV_BY_LEAGUE.get(m["slug"], DEFAULT_HOME_ADV)
        exp_home = _expected_score(eh + home_adv, ea)
        result_home = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
        delta_home = k * _goal_index(hs - as_) * (result_home - exp_home)
        elos[hc] = eh + delta_home
        elos[ac] = ea - delta_home
        for code, d in ((hc, delta_home), (ac, -delta_home)):
            net_delta[code] = net_delta.get(code, 0.0) + d
            played[code] = played.get(code, 0) + 1

        def side(code, before, delta, score, opp_score, meta):
            return {
                "code": code,
                "name": meta["name"],
                "logo": meta["logo"],
                "score": score,
                "eloBefore": round(before),
                "eloAfter": round(before + delta),
                "delta": round(delta, 1),
                "result": "W" if score > opp_score else ("D" if score == opp_score else "L"),
            }

        featured = [c for c in (hc, ac) if c in FEATURED_CODES]
        if featured:
            feed.append({
                "id": m["id"],
                "date": m["date"],
                "league": m["league"],
                "slug": m["slug"],
                "featured": featured,
                "home": side(hc, eh, delta_home, hs, as_, m["home"]),
                "away": side(ac, ea, -delta_home, as_, hs, m["away"]),
            })

    feed.sort(key=lambda f: (f["date"], f["id"] or ""), reverse=True)
    return feed, dict(elos), net_delta, played


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


def _load_prev() -> dict:
    """Lee el football_data.js anterior para conservar estado que no se puede
    derivar de una sola foto: el récord Elo histórico (marca de agua) y desde
    cuándo la selección líder es nº1 (para medir su racha)."""
    try:
        txt = OUT.read_text(encoding="utf-8")
        i = txt.find("=")
        return json.loads(txt[i + 1:].strip().rstrip(";"))
    except (FileNotFoundError, ValueError):
        return {}


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


def build_elo_record(teams: list[dict], dynasties: list[dict], prev: dict) -> dict:
    """Máximo Elo jamás alcanzado (marca de agua monotónica).

    Candidatos: el pico histórico de las dinastías, el Elo actual más alto y el
    récord ya almacenado (para que nunca baje). Si el nº1 vivo supera el récord
    histórico, se guarda el anterior en prevRecord para poder decir 'nuevo máximo'."""
    hist = max(dynasties, key=lambda d: d["peakElo"]) if dynasties else None
    cur_top = max(teams, key=lambda t: t["elo"]) if teams else None
    candidates: list[dict] = []
    if hist:
        candidates.append({"elo": hist["peakElo"], "name": hist["name"], "teamCode": hist["teamCode"],
                           "logo": hist["logo"], "when": hist["era"], "current": False})
    if cur_top:
        candidates.append({"elo": cur_top["elo"], "name": cur_top["name"], "teamCode": cur_top["teamCode"],
                           "logo": cur_top["logo"], "when": str(date.today().year), "current": True})
    prev_rec = prev.get("ELO_RECORD") or {}
    if prev_rec.get("elo"):
        candidates.append({k: prev_rec.get(k) for k in ("elo", "name", "teamCode", "logo", "when", "current")})
    record = dict(max(candidates, key=lambda c: c["elo"]))
    if hist and record["elo"] > hist["peakElo"]:
        record["prevRecord"] = {"elo": hist["peakElo"], "name": hist["name"], "when": hist["era"]}
    record["heldByCurrentNo1"] = bool(cur_top and cur_top["elo"] >= record["elo"])
    return record


def build_dynasty_chase(teams: list[dict], dynasties: list[dict], max_raw: float,
                        threshold: float, prev: dict) -> dict | None:
    """La selección nº1 actual medida en la MISMA escala que las dinastías
    históricas, para ver cuánto le falta para entrar en el top 10 (o si ya entra).
    Reemplaza a la antigua tabla de 'potencial dinástico'."""
    if not teams:
        return None
    leader = teams[0]
    seed = CURRENT_DYNASTY_SEEDS.get(leader["name"], {})
    cycle_years = float(seed.get("cycleYears", 1.0))
    cur_wc = int(seed.get("currentWorldCups", 0))
    cur_cont = int(seed.get("currentContinental", 0))
    # Racha como nº1: se conserva mientras no cambie el líder; si cambia, reinicia.
    today = date.today()
    prev_chase = (prev.get("ROAD_TO_GLORY") or {}).get("dynastyChase") or {}
    no1_since = prev_chase.get("no1Since")
    if prev_chase.get("teamCode") != leader["teamCode"] or not no1_since:
        no1_since = today.isoformat()
    try:
        streak_years = round((today - date.fromisoformat(no1_since)).days / 365.25, 1)
    except ValueError:
        streak_years = 0.0
    # yearsNo1 del ciclo vivo: el mayor entre la estimación curada y la racha real.
    years_no1 = max(cycle_years, streak_years)
    peak_elo = leader["elo"]                      # pico del ciclo actual = Elo vivo
    raw = dynasty_raw({"yearsNo1": years_no1, "worldCups": cur_wc,
                       "continentalTitles": cur_cont, "peakElo": peak_elo})
    score = round(raw / max(max_raw, 1.0) * 100.0, 1)
    gap = round(max(0.0, threshold - score), 1)
    row = team_meta(leader["name"])
    row.update({
        "rank": leader.get("rank", 1),
        "elo": leader["elo"],
        "no1Since": no1_since,
        "streakYears": streak_years,
        "cycleYears": cycle_years,
        "yearsNo1": years_no1,
        "currentWorldCups": cur_wc,
        "currentContinentalTitles": cur_cont,
        "peakElo": peak_elo,
        "dynastyScore": score,
        "gapToTop10": gap,
        "qualifies": gap <= 0,
    })
    return row


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


def apply_recent_results(teams: list[dict]) -> list[dict]:
    """Reproduce resultados reales sobre el Elo semilla y actualiza el top 10.

    Devuelve el feed de partidos recientes (con variación Elo por equipo).
    """
    seed = dict(ELO_SEED)
    for team in teams:  # el snapshot curado manda sobre la estimación
        seed[team["teamCode"]] = team["elo"]
    feed, final_elos, net_delta, played = replay_elo(seed)
    for team in teams:
        code = team["teamCode"]
        if code in final_elos:
            team["eloPrev"] = team["elo"]
            team["elo"] = round(final_elos[code])
            team["recentDelta"] = round(net_delta.get(code, 0.0), 1)
            team["recentMatches"] = played.get(code, 0)
        else:
            team["recentDelta"] = 0.0
            team["recentMatches"] = 0
    # Re-ranking y re-escalado del eloScore tras incorporar resultados.
    teams.sort(key=lambda t: t["elo"], reverse=True)
    max_elo = max(t["elo"] for t in teams)
    min_elo = min(t["elo"] for t in teams)
    span = (max_elo - min_elo) or 1
    for i, team in enumerate(teams):
        team["rank"] = i + 1
        team["eloScore"] = round(70 + (team["elo"] - min_elo) / span * 30, 1)
    return feed


def write_data() -> None:
    prev = _load_prev()
    teams = build_teams()
    recent_matches = apply_recent_results(teams)
    world_cup = build_world_cup(teams)
    attach_next_matches(teams, world_cup)
    dynasties = build_dynasties()
    threshold = dynasties[9]["dynastyScore"] if len(dynasties) >= 10 else 70.0
    raw_threshold = min(dynasty_raw(row) for row in DYNASTIES_RAW)
    max_raw = max(dynasty_raw(row) for row in dynasties)
    elo_record = build_elo_record(teams, dynasties, prev)
    dynasty_chase = build_dynasty_chase(teams, dynasties, max_raw, threshold, prev)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "UPDATED": updated,
        "SEASON": "Men's national teams",
        "SOURCE": {
            "name": "Elo Hermes (World Football Elo) + resultados en vivo de ESPN",
            "notes": "Rating de partida curado; tras cada partido se aplica la fórmula World Football Elo sobre los resultados reales del scoreboard de ESPN.",
            "through": updated,
        },
        "IMPORTANCE": importance(),
        "TEAMS": teams,
        "ELO_RECORD": elo_record,
        "RECENT_MATCHES": recent_matches,
        "WORLD_CUP_2026": world_cup,
        "ROAD_TO_GLORY": {
            "dynastyThreshold": threshold,
            "rawDynastyThreshold": round(raw_threshold, 1),
            "dynasties": dynasties,
            "dynastyChase": dynasty_chase,
        },
    }
    OUT.write_text(
        f"// Auto-generated {updated}\nwindow.FOOTBALL_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT.relative_to(ROOT)} · {len(teams)} teams · {len(dynasties)} dynasties · {len(recent_matches)} recent matches")


if __name__ == "__main__":
    write_data()
