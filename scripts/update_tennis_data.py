#!/usr/bin/env python3
"""Fetch ATP + WTA singles data from Jeff Sackmann GitHub CSVs and write tennis_data.js."""
from __future__ import annotations
import csv, hashlib, html, json, math, os, re, sys, time, urllib.request
from collections import defaultdict
from datetime import datetime, timezone, date as _date, timedelta
from io import StringIO
from pathlib import Path

ROOT   = Path(__file__).resolve().parent.parent
CACHE  = ROOT / ".tennis_cache"
CACHE.mkdir(exist_ok=True)
STALE_FETCHES: list[tuple[str, float, float]] = []

CURRENT_YEAR  = datetime.now(timezone.utc).year
CAREER_START  = 2010
ACTIVE_YEARS  = [CURRENT_YEAR - 1, CURRENT_YEAR]
TOP_N         = 200  # keep enough depth to show Grand Slam late-round outsiders

BASE = {
    "atp": "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master",
    "wta": "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master",
}

GS_LEVELS    = {"G"}
ELITE_ATP    = {"M", "F"}
ELITE_WTA    = {"P", "PM", "F"}

LEGEND_REF = {
    "atp": {
        "gs": 24, "elite": 40, "titles_500": 28, "gs_consistency": 55,
        "top10_wins": 120, "weeks_no1": 428, "gs_pace_max": 2.5,
    },
    "wta": {
        "gs": 24, "elite": 35, "titles_500": 25, "gs_consistency": 50,
        "top10_wins": 80, "weeks_no1": 377, "gs_pace_max": 2.5,
    },
}

# ── Country data ──────────────────────────────────────────────────────────────

CC3_TO_CC2: dict[str, str] = {
    "ESP": "es", "SRB": "rs", "GER": "de", "RUS": "ru", "NOR": "no",
    "GRE": "gr", "POL": "pl", "ARG": "ar", "USA": "us", "AUS": "au",
    "GBR": "gb", "FRA": "fr", "ITA": "it", "CAN": "ca", "BEL": "be",
    "NED": "nl", "SUI": "ch", "DEN": "dk", "CZE": "cz", "CHI": "cl",
    "BRA": "br", "CRO": "hr", "HUN": "hu", "SVK": "sk", "BUL": "bg",
    "FIN": "fi", "SWE": "se", "AUT": "at", "ROU": "ro", "POR": "pt",
    "KAZ": "kz", "CHN": "cn", "JPN": "jp", "KOR": "kr", "TPE": "tw",
    "THA": "th", "IND": "in", "RSA": "za", "EGY": "eg", "MAR": "ma",
    "TUN": "tn", "COL": "co", "ECU": "ec", "URU": "uy", "PAR": "py",
    "BOL": "bo", "PER": "pe", "MEX": "mx", "BAH": "bs", "HAI": "ht",
    "DOM": "do", "PUR": "pr", "LAT": "lv", "EST": "ee", "LTU": "lt",
    "UKR": "ua", "BLR": "by", "MDA": "md", "AZE": "az", "GEO": "ge",
    "ARM": "am", "UZB": "uz", "ISR": "il", "TUR": "tr", "LUX": "lu",
    "MON": "mc", "SLO": "si", "MKD": "mk", "BIH": "ba", "MNE": "me",
    "CYP": "cy", "NZL": "nz", "ZIM": "zw", "NGR": "ng", "SEN": "sn",
    "CMR": "cm", "GUA": "gt",
}

COUNTRY_COLORS: dict[str, str] = {
    "ESP": "#AA151B", "SRB": "#C6363C", "GER": "#000000", "RUS": "#003DA5",
    "NOR": "#EF2B2D", "GRE": "#0D5EAF", "POL": "#DC143C", "ARG": "#74ACDF",
    "USA": "#B22234", "AUS": "#00008B", "GBR": "#012169", "FRA": "#002395",
    "ITA": "#009246", "CAN": "#FF0000", "BEL": "#000000", "NED": "#AE1C28",
    "SUI": "#FF0000", "DEN": "#C60C30", "CZE": "#D7141A", "CHI": "#D52B1E",
    "BRA": "#009C3B", "CRO": "#FF0000", "HUN": "#477050", "SVK": "#0B4EA2",
    "BUL": "#00966E", "FIN": "#003580", "SWE": "#006AA7", "AUT": "#ED2939",
    "ROU": "#002B7F", "POR": "#006600", "KAZ": "#00AFCA", "CHN": "#DE2910",
    "JPN": "#BC002D", "KOR": "#003478", "TPE": "#FE0000", "THA": "#A51931",
    "IND": "#FF9933", "RSA": "#007749", "EGY": "#CE1126", "MAR": "#C1272D",
    "COL": "#FCD116", "ECU": "#FFD100", "UKR": "#005BBB", "BLR": "#CF101A",
    "ISR": "#0038B8", "TUR": "#E30A17", "UZB": "#1EB53A",
}

def _flag_url(ioc3: str) -> str:
    cc2 = CC3_TO_CC2.get(ioc3, "")
    if not cc2:
        return ""
    return f"https://flagcdn.com/24x18/{cc2}.png"

# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_fetch(url: str, ttl_hours: float = 720.0) -> str:
    key  = hashlib.md5(url.encode()).hexdigest()
    path = CACHE / key
    if path.exists():
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if age_h < ttl_hours:
            return path.read_text(encoding="utf-8")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            text = r.read().decode("utf-8")
        path.write_text(text, encoding="utf-8")
        return text
    except Exception as exc:
        if path.exists():
            age_h = (time.time() - path.stat().st_mtime) / 3600
            if ttl_hours <= 24.0 and age_h >= ttl_hours:
                STALE_FETCHES.append((url, age_h, ttl_hours))
            print(f"[WARN] fetch failed ({exc}), using stale cache: {url}", file=sys.stderr)
            return path.read_text(encoding="utf-8")
        raise

def _csv(url: str, ttl_hours: float = 720.0) -> list[dict]:
    text = _cache_fetch(url, ttl_hours)
    return list(csv.DictReader(StringIO(text)))

def _matches(tour: str, year: int) -> list[dict]:
    prefix = "atp_matches" if tour == "atp" else "wta_matches"
    url    = f"{BASE[tour]}/{prefix}_{year}.csv"
    # current year: corto TTL (2h) para capturas mañana+noche; histórico: 30 días
    ttl    = 2.0 if year == CURRENT_YEAR else 720.0
    try:
        return _csv(url, ttl)
    except Exception:
        return []


# ── Resultados recientes (últimos 14 días) ────────────────────────────────────

_ROUND_ORDER: dict[str, int] = {
    "F": 1, "SF": 2, "QF": 3, "R16": 4, "R32": 5, "R64": 6, "R128": 7,
    "RR": 3, "BR": 4,
}
_ROUND_ES: dict[str, str] = {
    "F":    "Final",
    "SF":   "Semifinal",
    "QF":   "Cuartos",
    "R16":  "Octavos",
    "R32":  "3ª ronda",
    "R64":  "2ª ronda",
    "R128": "1ª ronda",
    "RR":   "Round Robin",
    "BR":   "3er puesto",
}
_LEVEL_ES: dict[str, str] = {
    "G":  "Grand Slam",
    "F":  "Finals",
    "M":  "Masters 1000",
    "A":  "ATP 500",
    "PM": "Premier Mandatory",
    "P":  "Premier 5",
    "D":  "Davis Cup",
    "500": "500",
    "250": "250",
    "C":  "Challenger",
}
_LEVEL_PRIO: dict[str, int] = {"G": 0, "F": 1, "M": 2, "PM": 2, "500": 3, "A": 3, "P": 3, "250": 4}
_IMPORTANT_LEVELS = {"G", "F", "M", "PM", "P", "A", "500"}
_TML_URL = "https://stats.tennismylife.org/"
_TML_SCHEDULE_URL = "https://stats.tennismylife.org/schedule"
_ESPN_ATP_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates={date}&limit=300"
_ESPN_SCOREBOARD_URLS = {
    "atp": _ESPN_ATP_SCOREBOARD_URL,
    "wta": "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard?dates={date}&limit=300",
}
_TML_IMPORTANT_TOURNAMENTS: dict[str, dict[str, str]] = {
    "Roland Garros": {"level": "Grand Slam", "surface": "Clay"},
    "Australian Open": {"level": "Grand Slam", "surface": "Hard"},
    "Wimbledon": {"level": "Grand Slam", "surface": "Grass"},
    "Us Open": {"level": "Grand Slam", "surface": "Hard"},
    "US Open": {"level": "Grand Slam", "surface": "Hard"},
}
_TOUR_SINGLES_GROUP = {
    "atp": "Men's Singles",
    "wta": "Women's Singles",
}
_TOURNAMENT_WITHDRAWALS = {
    "Roland Garros": {
        "atp": {
            "Carlos Alcaraz": "Lesión · no compite en Roland Garros",
        },
        "wta": {},
    },
}


def _tourney_date(value: str) -> _date | None:
    try:
        return _date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except Exception:
        return None


def _tourney_window_days(level: str) -> int:
    if level == "G":
        return 16
    if level in {"F", "M", "PM", "P"}:
        return 12
    return 9


def _match_num(m: dict) -> int:
    try:
        return int(m.get("match_num", "0"))
    except ValueError:
        return 0


def _cell_text(cell_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", cell_html)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _player_cell(cell_html: str) -> str:
    links = re.findall(r'<a[^>]+href="/players/[^"]+"[^>]*>(.*?)</a>', cell_html)
    if links:
        return _cell_text(links[-1])
    return _cell_text(cell_html)


def _name_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _score_lookup(players: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for p in players:
        score = p.get("activeScore")
        if isinstance(score, (int, float)):
            out[_name_key(p.get("name", ""))] = float(score)
    return out


def _player_score(name: str, scores: dict[str, float]) -> float | None:
    return scores.get(_name_key(name))


def _with_match_scores(match: dict, scores: dict[str, float]) -> dict:
    w_score = _player_score(match.get("w", ""), scores)
    l_score = _player_score(match.get("l", ""), scores)
    numeric = [s for s in (w_score, l_score) if isinstance(s, (int, float))]
    return {
        **match,
        "w_score": round(w_score, 1) if isinstance(w_score, (int, float)) else None,
        "l_score": round(l_score, 1) if isinstance(l_score, (int, float)) else None,
        "match_score": round(max(numeric), 1) if numeric else 0.0,
    }


def _rank_recent_tournaments(tournaments: list[dict], scores: dict[str, float], limit: int = 8) -> list[dict]:
    out = []
    for t in tournaments:
        matches = [_with_match_scores(m, scores) for m in t.get("matches", [])]
        matches.sort(key=lambda m: (-m.get("match_score", 0), m.get("round", ""), m.get("w", "")))
        if matches:
            out.append({**t, "matches": matches[:limit]})
    return out


def _tml_recent_results(scores: dict[str, float], target: str = "yesterday") -> list[dict]:
    """Fetch dated latest important ATP results from TennisMyLife."""
    today = _date.today()
    target_date = today.isoformat() if target == "today" else (today - timedelta(days=1)).isoformat()
    req = urllib.request.Request(_TML_URL, headers={"User-Agent": "Mozilla/5.0"})
    try:
        raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    except Exception as exc:
        print(f"[WARN] TennisMyLife latest matches unavailable: {exc}", file=sys.stderr)
        return []

    grouped: dict[str, dict] = {}
    for row_html in re.findall(r'<tr class="hover:bg-gray-800[^"]*">(.*?)</tr>', raw, flags=re.DOTALL):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.DOTALL)
        if len(cells) < 7:
            continue
        match_date = _cell_text(cells[0])
        if match_date != target_date:
            continue
        tournament = _cell_text(cells[1])
        info = _TML_IMPORTANT_TOURNAMENTS.get(tournament)
        if not info:
            continue
        score = _cell_text(cells[6])
        if not score or score == "W/O":
            continue
        group = grouped.setdefault(tournament, {
            "name": tournament,
            "level": info["level"],
            "surface": info["surface"],
            "matches": [],
        })
        group["matches"].append({
            "round": _cell_text(cells[2]),
            "w": _player_cell(cells[4]),
            "w_logo": "",
            "l": _player_cell(cells[5]),
            "l_logo": "",
            "score": score,
            "day": "hoy" if target == "today" else "ayer",
        })

    return _rank_recent_tournaments(list(grouped.values()), scores)


def _title_name(slug: str) -> str:
    particles = {"de", "del", "van", "von", "der", "den", "da", "dos", "du", "agustin"}
    parts = []
    for p in slug.split("-"):
        if p in particles:
            parts.append(p.capitalize() if p == "agustin" else p)
        else:
            parts.append(p.capitalize())
    return " ".join(parts)


def _espn_round_code(label: str) -> str:
    label = (label or "").strip()
    mapping = {
        "Round 1": "R128",
        "Round 2": "R64",
        "Round 3": "R32",
        "Round 4": "R16",
        "Quarterfinals": "QF",
        "Semifinals": "SF",
        "Final": "F",
    }
    return mapping.get(label, label)


def _espn_note_score(note: str) -> str:
    if not note:
        return ""
    # ESPN notes look like: "(3) Novak Djokovic (SER) bt Valentin Royer (FRA) 6-3 ..."
    if " bt " not in note:
        return ""
    right = note.split(" bt ", 1)[1]
    m = re.search(r"\([A-Z]{3}\)\s+(.+)$", right)
    if not m:
        return ""
    return m.group(1).strip()


def _espn_day_matches(scores: dict[str, float], target_date: _date) -> list[dict]:
    """Fetch real ATP singles matches for a date from ESPN's tournament scoreboard."""
    url = _ESPN_ATP_SCOREBOARD_URL.format(date=target_date.strftime("%Y%m%d"))
    try:
        raw = _cache_fetch(url, ttl_hours=0.5)
        data = json.loads(raw)
    except Exception as exc:
        print(f"[WARN] ESPN ATP scoreboard unavailable: {exc}", file=sys.stderr)
        return []

    grouped: dict[str, dict] = {}
    for event in data.get("events", []):
        tournament = event.get("name", "")
        info = _TML_IMPORTANT_TOURNAMENTS.get(tournament)
        if not info:
            continue
        for grouping in event.get("groupings", []):
            if grouping.get("grouping", {}).get("displayName") != "Men's Singles":
                continue
            for comp in grouping.get("competitions", []):
                comp_date = (comp.get("date") or "")[:10]
                if comp_date != target_date.isoformat():
                    continue
                round_label = comp.get("round", {}).get("displayName", "")
                if "Qualifying" in round_label:
                    continue
                competitors = comp.get("competitors", [])
                if len(competitors) != 2:
                    continue
                athletes = [c.get("athlete", {}).get("displayName", "") for c in competitors]
                if not athletes[0] or not athletes[1]:
                    continue
                status_name = comp.get("status", {}).get("type", {}).get("name", "")
                notes = comp.get("notes") or []
                note = notes[0].get("text", "") if notes else ""
                score = _espn_note_score(note)
                scheduled = status_name in {"STATUS_SCHEDULED", "STATUS_PRE"}
                if scheduled:
                    left, right = athletes[0], athletes[1]
                    left_score = _player_score(left, scores) or 0
                    right_score = _player_score(right, scores) or 0
                    if right_score > left_score:
                        left, right = right, left
                    score = "por jugar"
                else:
                    winner = next((c for c in competitors if c.get("winner") is True), None)
                    loser = next((c for c in competitors if c.get("winner") is False), None)
                    if not winner or not loser:
                        left, right = athletes[0], athletes[1]
                    else:
                        left = winner.get("athlete", {}).get("displayName", "")
                        right = loser.get("athlete", {}).get("displayName", "")
                    if not score:
                        score = comp.get("status", {}).get("type", {}).get("description", "")

                group = grouped.setdefault(tournament, {
                    "name": tournament,
                    "level": info["level"],
                    "surface": info["surface"],
                    "matches": [],
                })
                group["matches"].append({
                    "round": _espn_round_code(round_label),
                    "w": left,
                    "w_logo": "",
                    "l": right,
                    "l_logo": "",
                    "score": score,
                    "day": "hoy" if target_date == _date.today() else "ayer",
                    "scheduled": scheduled,
                })

    return _rank_recent_tournaments(list(grouped.values()), scores)


def _espn_current_tournament_status(tour: str, players: list[dict]) -> dict:
    """Return current Grand Slam/Masters singles survival state from ESPN's draw data."""
    url_tmpl = _ESPN_SCOREBOARD_URLS.get(tour, _ESPN_ATP_SCOREBOARD_URL)
    url = url_tmpl.format(date=_date.today().strftime("%Y%m%d"))
    try:
        raw = _cache_fetch(url, ttl_hours=0.5)
        data = json.loads(raw)
    except Exception as exc:
        print(f"[WARN] ESPN {tour.upper()} tournament status unavailable: {exc}", file=sys.stderr)
        return {}

    target_group = _TOUR_SINGLES_GROUP[tour]
    today = _date.today()
    selected: dict | None = None
    selected_info: dict[str, str] = {}
    for event in data.get("events", []):
        name = event.get("name", "")
        info = _TML_IMPORTANT_TOURNAMENTS.get(name)
        if not info:
            continue
        try:
            start = datetime.fromisoformat((event.get("date", "") or "").replace("Z", "+00:00")).date()
            end = datetime.fromisoformat((event.get("endDate", "") or "").replace("Z", "+00:00")).date()
        except Exception:
            start = today - timedelta(days=1)
            end = today + timedelta(days=1)
        if start <= today <= end:
            selected = event
            selected_info = info
            break

    if not selected:
        return {}

    entrants: dict[str, dict] = {}
    matches_seen = 0

    def remember(name: str, state: str, round_label: str = "", reason: str = "") -> None:
        if not name or name == "TBD":
            return
        key = _name_key(name)
        prev = entrants.get(key, {})
        entrants[key] = {
            "name": prev.get("name") or name,
            "state": state,
            "round": round_label or prev.get("round", ""),
            "reason": reason or prev.get("reason", ""),
        }

    competitions: list[dict] = []
    for grouping in selected.get("groupings", []):
        if grouping.get("grouping", {}).get("displayName") != target_group:
            continue
        competitions.extend(grouping.get("competitions", []))

    competitions.sort(key=lambda c: (
        c.get("date", ""),
        _ROUND_ORDER.get(_espn_round_code(c.get("round", {}).get("displayName", "")), 99),
    ))

    for comp in competitions:
        round_label = comp.get("round", {}).get("displayName", "")
        if "Qualifying" in round_label:
            continue
        competitors = comp.get("competitors", [])
        names = [c.get("athlete", {}).get("displayName", "") for c in competitors]
        names = [n for n in names if n and n != "TBD"]
        if len(names) != 2:
            continue
        matches_seen += 1
        short_round = _espn_round_code(round_label)
        completed = comp.get("status", {}).get("type", {}).get("completed") is True
        if completed:
            winner = next((c for c in competitors if c.get("winner") is True), None)
            loser = next((c for c in competitors if c.get("winner") is False), None)
            if winner and loser:
                remember(winner.get("athlete", {}).get("displayName", ""), "alive", short_round)
                remember(loser.get("athlete", {}).get("displayName", ""), "out", short_round, f"Eliminado en {short_round}")
        else:
            for name in names:
                remember(name, "alive", short_round)

    withdrawals = _TOURNAMENT_WITHDRAWALS.get(selected.get("name", ""), {}).get(tour, {})
    for name, reason in withdrawals.items():
        remember(name, "out", "", reason)

    alive_keys = {k for k, v in entrants.items() if v.get("state") == "alive"}
    for player in players:
        key = _name_key(player.get("name", ""))
        status = entrants.get(key)
        if status:
            player["tournamentStatus"] = {
                "tournament": selected.get("name", ""),
                "state": status["state"],
                "round": status.get("round", ""),
                "reason": status.get("reason", ""),
            }
        else:
            player["tournamentStatus"] = {
                "tournament": selected.get("name", ""),
                "state": "out",
                "round": "",
                "reason": f"No compite en {selected.get('name', '')}",
            }

    return {
        "name": selected.get("name", ""),
        "level": selected_info.get("level", ""),
        "surface": selected_info.get("surface", ""),
        "tour": tour.upper(),
        "alive": sorted(v["name"] for v in entrants.values() if v.get("state") == "alive"),
        "out": sorted(v["name"] for v in entrants.values() if v.get("state") == "out"),
        "aliveCount": len(alive_keys),
        "matchesSeen": matches_seen,
    }


def _tml_today_schedule(scores: dict[str, float]) -> list[dict]:
    """Fetch today's ATP schedule from TennisMyLife H2H links."""
    req = urllib.request.Request(_TML_SCHEDULE_URL, headers={"User-Agent": "Mozilla/5.0"})
    try:
        raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    except Exception as exc:
        print(f"[WARN] TennisMyLife schedule unavailable: {exc}", file=sys.stderr)
        return []

    matches = []
    current_round = ""
    for token in re.finditer(r"<h3[^>]*>([^<]+)</h3>|href=\"(?:https://stats\.tennismylife\.org)?/h2h/([^\"]+)\"", raw):
        if token.group(1):
            current_round = _cell_text(token.group(1))
            continue
        slug = token.group(2)
        if not slug or "-vs-" not in slug:
            continue
        p1_slug, p2_slug = slug.split("-vs-", 1)
        matches.append({
            "round": current_round,
            "w": _title_name(p1_slug),
            "w_logo": "",
            "l": _title_name(p2_slug),
            "l_logo": "",
            "score": "por jugar",
            "day": "hoy",
            "scheduled": True,
        })

    if not matches:
        return []

    return _rank_recent_tournaments([{
        "name": "Roland Garros",
        "level": "Grand Slam",
        "surface": "Clay",
        "matches": matches,
    }], scores)


def _recent_results(tour: str, scores: dict[str, float]) -> list[dict]:
    """Return latest results from important tournaments active yesterday/today."""
    today = _date.today()
    yesterday = today - timedelta(days=1)
    important_levels = {"G"} if _tennis_importance() >= 10 else _IMPORTANT_LEVELS
    rows   = _matches(tour, CURRENT_YEAR)
    if not rows:
        return []

    by_tid: dict[str, list[dict]] = defaultdict(list)
    meta:   dict[str, dict] = {}
    for m in rows:
        td  = m.get("tourney_date", "")
        level = m.get("tourney_level", "")
        if level not in important_levels:
            continue
        start = _tourney_date(td)
        if not start:
            continue
        end = start + timedelta(days=_tourney_window_days(level))
        if end < yesterday or start > today:
            continue
        tid = m.get("tourney_id", "")
        if tid not in meta:
            meta[tid] = {
                "name":    m.get("tourney_name", ""),
                "surface": m.get("surface", ""),
                "level":   m.get("tourney_level", ""),
                "date":    td,
            }
        by_tid[tid].append(m)

    if not by_tid:
        return []

    sorted_tids = sorted(
        by_tid,
        key=lambda t: (-int(meta[t]["date"] or "0"), _LEVEL_PRIO.get(meta[t]["level"], 9)),
    )

    result = []
    for tid in sorted_tids[:4]:
        tmeta   = meta[tid]
        matches = sorted(
            by_tid[tid],
            key=lambda m: (_ROUND_ORDER.get(m.get("round", ""), 9), -_match_num(m), m.get("winner_name", "")),
        )
        entries = [
            {
                "round":  _ROUND_ES.get(m.get("round", ""), m.get("round", "")),
                "w":      m.get("winner_name", ""),
                "w_logo": _flag_url(m.get("winner_ioc", "")),
                "l":      m.get("loser_name", ""),
                "l_logo": _flag_url(m.get("loser_ioc", "")),
                "score":  m.get("score", ""),
                "day":    "ayer/hoy",
            }
            for m in matches
            if m.get("winner_name") and m.get("score") and "W/O" not in m.get("score", "")
        ][:12]

        entries = _rank_recent_tournaments([{"matches": entries}], scores)[0]["matches"] if entries else []

        if entries:
            result.append({
                "name":    tmeta["name"],
                "level":   _LEVEL_ES.get(tmeta["level"], tmeta["level"]),
                "surface": tmeta["surface"],
                "matches": entries,
            })

    return result

def _players(tour: str) -> dict[str, dict]:
    prefix = "atp_players" if tour == "atp" else "wta_players"
    rows   = _csv(f"{BASE[tour]}/{prefix}.csv", ttl_hours=168.0)
    out: dict[str, dict] = {}
    for r in rows:
        pid = r.get("player_id", "").strip()
        if pid:
            out[pid] = r
    return out

def _rankings_current(tour: str) -> list[dict]:
    prefix = "atp_rankings" if tour == "atp" else "wta_rankings"
    url    = f"{BASE[tour]}/{prefix}_current.csv"
    rows   = _csv(url, ttl_hours=6.0)
    if not rows:
        return rows
    latest = max(r.get("ranking_date", "") for r in rows)
    return [r for r in rows if r.get("ranking_date") == latest]

def _rankings_two_weeks(tour: str) -> tuple[list[dict], list[dict], str, str]:
    """Return (current, previous) weekly rankings and their dates."""
    prefix = "atp_rankings" if tour == "atp" else "wta_rankings"
    url    = f"{BASE[tour]}/{prefix}_current.csv"
    rows   = _csv(url, ttl_hours=6.0)
    if not rows:
        return [], [], "", ""
    dates = sorted({r.get("ranking_date", "") for r in rows if r.get("ranking_date")})
    curr_date = dates[-1] if dates else ""
    prev_date = dates[-2] if len(dates) > 1 else ""
    curr = [r for r in rows if r.get("ranking_date") == curr_date]
    prev = [r for r in rows if r.get("ranking_date") == prev_date]
    return curr, prev, curr_date, prev_date

def _top10_changes(curr: list[dict], prev: list[dict], player_meta: dict,
                   curr_date: str = "", prev_date: str = "") -> dict:
    """Compute who entered/exited the official top 10 between two ranking weeks."""
    def top10_ids(rows: list[dict]) -> dict[str, int]:
        out = {}
        for r in rows:
            try:
                rk = int(r.get("rank", 9999))
                pid = r.get("player", "").strip()
                if pid and rk <= 10:
                    out[pid] = rk
            except ValueError:
                pass
        return out

    def pid_to_info(pid: str, rank: int) -> dict:
        meta = player_meta.get(pid, {})
        ioc  = meta.get("ioc", "")
        name = f"{meta.get('name_first','')} {meta.get('name_last','')}".strip()
        return {"name": name or pid, "rank": rank, "country": ioc, "logo": _flag_url(ioc)}

    curr_top10 = top10_ids(curr)
    prev_top10 = top10_ids(prev)

    entered = [pid_to_info(pid, curr_top10[pid]) for pid in curr_top10 if pid not in prev_top10]
    exited  = [pid_to_info(pid, prev_top10[pid]) for pid in prev_top10 if pid not in curr_top10]
    entered.sort(key=lambda x: x["rank"])
    exited.sort(key=lambda x: x["rank"])
    return {"entered": entered, "exited": exited, "prev_date": prev_date, "curr_date": curr_date}

def _rankings_year(tour: str, decade: str) -> list[dict]:
    prefix = "atp_rankings" if tour == "atp" else "wta_rankings"
    url    = f"{BASE[tour]}/{prefix}_{decade}s.csv"
    return _csv(url, ttl_hours=720.0)

# ── Singles-only filter ───────────────────────────────────────────────────────

def _singles(rows: list[dict]) -> list[dict]:
    return [r for r in rows
            if r.get("tourney_level", "") not in ("D", "")  # exclude Davis/Fed Cup
            and r.get("score", "").strip() not in ("", "W/O", "walkover", "Walkover")]

# ── Elo ───────────────────────────────────────────────────────────────────────

def _build_elo(all_matches: list[dict]) -> dict[str, float]:
    K     = 32.0
    START = 1500.0
    elo: dict[str, float] = defaultdict(lambda: START)
    for m in all_matches:
        w = m.get("winner_id", "").strip()
        l = m.get("loser_id",  "").strip()
        if not w or not l:
            continue
        ew, el = elo[w], elo[l]
        pw = 1.0 / (1.0 + 10 ** ((el - ew) / 400.0))
        elo[w] = ew + K * (1.0 - pw)
        elo[l] = el + K * (0.0 - (1.0 - pw))
    return dict(elo)

# ── Surface win rates (active years only) ────────────────────────────────────

def _build_surface_rates(active_matches: list[dict]) -> dict[str, dict[str, float]]:
    wins:  dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for m in active_matches:
        surface = m.get("surface", "Unknown") or "Unknown"
        w = m.get("winner_id", "").strip()
        l = m.get("loser_id",  "").strip()
        if w:
            wins[w][surface]  += 1
            total[w][surface] += 1
        if l:
            total[l][surface] += 1
    result: dict[str, dict[str, float]] = {}
    for pid in set(wins) | set(total):
        result[pid] = {}
        for surf in ("Hard", "Clay", "Grass", "Carpet"):
            t = total[pid].get(surf, 0)
            w = wins[pid].get(surf, 0)
            result[pid][surf.lower()] = round(w / t, 3) if t >= 5 else None  # type: ignore[assignment]
    return result

# ── Recent form: last 20 singles matches ─────────────────────────────────────

def _build_form(active_matches: list[dict]) -> dict[str, float]:
    events: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for m in active_matches:
        date = m.get("tourney_date", "00000000")
        w = m.get("winner_id", "").strip()
        l = m.get("loser_id",  "").strip()
        if w:
            events[w].append((date, 1))
        if l:
            events[l].append((date, 0))
    form: dict[str, float] = {}
    for pid, evs in events.items():
        evs.sort(key=lambda x: x[0])
        last20 = evs[-20:]
        form[pid] = sum(r for _, r in last20) / len(last20) if last20 else 0.5
    return form

# ── Opponent quality (avg rank of opponents beaten, lower rank = tougher) ───

def _build_opp_quality(active_matches: list[dict]) -> dict[str, float]:
    beaten_ranks: dict[str, list[int]] = defaultdict(list)
    for m in active_matches:
        w   = m.get("winner_id", "").strip()
        try:
            lr = int(m.get("loser_rank") or 0)
        except ValueError:
            lr = 0
        if w and 1 <= lr <= 500:
            beaten_ranks[w].append(lr)
    quality: dict[str, float] = {}
    for pid, ranks in beaten_ranks.items():
        avg = sum(ranks) / len(ranks)
        # lower avg rank = better opponents; map to 0-1 (rank 1 → 1.0, rank 200 → 0.0)
        quality[pid] = max(0.0, 1.0 - (avg - 1) / 200.0)
    return quality

# ── Career stats ──────────────────────────────────────────────────────────────

def _build_career_stats(
    tour: str,
    all_matches: list[dict],
) -> dict[str, dict]:
    elite_levels = ELITE_ATP if tour == "atp" else ELITE_WTA
    stats: dict[str, dict] = defaultdict(lambda: {
        "gs": 0, "gs_finals": 0, "elite_titles": 0, "titles_500": 0,
        "gs_matches_won": 0, "gs_matches_played": 0,
        "top10_wins": 0, "total_titles": 0,
    })
    # Group by tourney to find winners
    by_tourney: dict[str, list[dict]] = defaultdict(list)
    for m in all_matches:
        key = f"{m.get('tourney_date','')}-{m.get('tourney_id','')}"
        by_tourney[key].append(m)

    for key, matches in by_tourney.items():
        if not matches:
            continue
        level = matches[0].get("tourney_level", "")
        # find the final (highest round)
        final = [m for m in matches if m.get("round") in ("F", "Final")]
        if final:
            winner_id = final[0].get("winner_id", "").strip()
            if winner_id:
                stats[winner_id]["total_titles"] += 1
                if level in GS_LEVELS:
                    stats[winner_id]["gs"] += 1
                if level in elite_levels:
                    stats[winner_id]["elite_titles"] += 1
                if level in ("A", "500", "B", "2") or level in elite_levels:
                    stats[winner_id]["titles_500"] += 1
        # GS consistency: matches won/played in GS
        if level in GS_LEVELS:
            for m in matches:
                w = m.get("winner_id", "").strip()
                l = m.get("loser_id",  "").strip()
                if w:
                    stats[w]["gs_matches_won"]    += 1
                    stats[w]["gs_matches_played"] += 1
                if l:
                    stats[l]["gs_matches_played"] += 1
        # top-10 wins
        for m in matches:
            w = m.get("winner_id", "").strip()
            try:
                lr = int(m.get("loser_rank") or 0)
            except ValueError:
                lr = 0
            if w and 1 <= lr <= 10:
                stats[w]["top10_wins"] += 1

    return {k: dict(v) for k, v in stats.items()}

# ── Weeks at #1 ───────────────────────────────────────────────────────────────

def _build_weeks_no1(tour: str) -> dict[str, int]:
    weeks: dict[str, int] = defaultdict(int)
    for decade in range(2010, CURRENT_YEAR, 10):
        try:
            rows = _rankings_year(tour, str(decade))
        except Exception:
            continue
        # group by date
        by_date: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            by_date[r.get("ranking_date", "")].append(r)
        for date_rows in by_date.values():
            for r in date_rows:
                try:
                    rank = int(r.get("rank", 999))
                except ValueError:
                    continue
                if rank == 1:
                    weeks[r.get("player", "").strip()] += 1
    # current year
    try:
        rows = _rankings_current(tour)
        by_date = defaultdict(list)
        for r in rows:
            by_date[r.get("ranking_date", "")].append(r)
        for date_rows in by_date.values():
            for r in date_rows:
                try:
                    rank = int(r.get("rank", 999))
                except ValueError:
                    continue
                if rank == 1:
                    weeks[r.get("player", "").strip()] += 1
    except Exception:
        pass
    return dict(weeks)

# ── Scoring ───────────────────────────────────────────────────────────────────

def _pct(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))

def _active_score(
    pid: str,
    rank: int,
    elo: dict[str, float],
    all_elos: list[float],
    surface: dict[str, dict[str, float]],
    form: dict[str, float],
    opp_quality: dict[str, float],
) -> float:
    # stat_pct: combined serve-based metric (simplified — we use surface win-rates as proxy)
    surf = surface.get(pid, {})
    non_none = [v for v in surf.values() if v is not None]
    stat_pct = sum(non_none) / len(non_none) if non_none else 0.5

    # rank strength (rank 1 → 1.0, rank 100 → 0.0)
    rank_strength = max(0.0, 1.0 - (rank - 1) / 99.0) if rank <= 100 else 0.0

    # elo percentile
    my_elo   = elo.get(pid, 1500.0)
    elo_pct  = _pct(my_elo, min(all_elos), max(all_elos)) if len(all_elos) > 1 else 0.5

    strength = 0.6 * elo_pct + 0.4 * rank_strength

    f = form.get(pid, 0.5)
    q = opp_quality.get(pid, 0.5)

    raw = 0.40 * stat_pct + 0.35 * strength + 0.15 * f + 0.10 * q
    return round(raw * 100, 1)

def _legend_score(pid: str, tour: str, career: dict, weeks_no1: dict[str, int]) -> float:
    ref  = LEGEND_REF[tour]
    s    = career.get(pid, {})

    gs           = s.get("gs", 0)
    elite_titles = s.get("elite_titles", 0)
    titles_500   = s.get("titles_500", 0)
    gs_w         = s.get("gs_matches_won", 0)
    gs_p         = s.get("gs_matches_played", 0)
    top10_wins   = s.get("top10_wins", 0)
    weeks        = weeks_no1.get(pid, 0)
    total_titles = s.get("total_titles", 0)

    # GS pace: GS per 100 titles (capped at ref max)
    gs_pace = (gs / total_titles * 100) if total_titles > 0 else 0.0

    # GS consistency: GS win rate × 100
    gs_consistency = (gs_w / gs_p * 100) if gs_p > 0 else 0.0

    # surface versatility: placeholder (always neutral 0.5)
    surface_score = 0.5

    components = {
        "gs_pace":        (0.30, _pct(gs_pace,        0, ref["gs_pace_max"] * 100)),
        "ranking":        (0.20, _pct(weeks,           0, ref["weeks_no1"])),
        "elite":          (0.15, _pct(elite_titles,    0, ref["elite"])),
        "titles_500":     (0.10, _pct(titles_500,      0, ref["titles_500"])),
        "gs_consistency": (0.10, _pct(gs_consistency,  0, ref["gs_consistency"])),
        "top10":          (0.075,_pct(top10_wins,      0, ref["top10_wins"])),
        "surface":        (0.05, surface_score),
        "team":           (0.025, 0.50),  # Davis/Fed Cup: neutral
    }
    raw = sum(w * v for _, (w, v) in components.items())
    return round(raw * 100, 1)

# ── All-time legends (hardcoded) ─────────────────────────────────────────────
# name, ioc3, born, gs, year_end_no1, weeks_no1, active, era_start, era_end
# Score: gs×12 + year_end_no1×3 + floor(weeks_no1/10)

LEGENDS_ATP_RAW = [
    ("Novak Djokovic",  "SRB", 1987, 24, 7, 428, True,  2004, None),
    ("Rafael Nadal",    "ESP", 1986, 22, 2, 209, False, 2005, 2024),
    ("Roger Federer",   "SUI", 1981, 20, 5, 310, False, 2003, 2022),
    ("Pete Sampras",    "USA", 1971, 14, 6, 286, False, 1990, 2002),
    ("Björn Borg",      "SWE", 1956, 11, 3, 109, False, 1973, 1983),
    ("Andre Agassi",    "USA", 1970,  8, 1, 101, False, 1986, 2006),
    ("Jimmy Connors",   "USA", 1952,  8, 5, 268, False, 1972, 1996),
    ("Ivan Lendl",      "CZE", 1960,  8, 8, 270, False, 1980, 1994),
    ("John McEnroe",    "USA", 1959,  7, 4, 170, False, 1978, 1992),
    ("Carlos Alcaraz",  "ESP", 2003,  7, 1,  40, True,  2022, None),
    ("Stefan Edberg",   "SWE", 1966,  6, 2,  72, False, 1983, 1996),
    ("Boris Becker",    "GER", 1967,  6, 1,  12, False, 1985, 1999),
    ("Jannik Sinner",   "ITA", 2001,  4, 1,  50, True,  2024, None),
    ("Mats Wilander",   "SWE", 1964,  7, 3,  20, False, 1982, 1991),
]

LEGENDS_WTA_RAW = [
    ("Steffi Graf",          "GER", 1969, 22, 8, 377, False, 1984, 1999),
    ("Serena Williams",      "USA", 1981, 23, 5, 319, False, 1999, 2022),
    ("Martina Navratilova",  "CZE", 1956, 18, 7, 332, False, 1978, 2006),
    ("Chris Evert",          "USA", 1954, 18, 7, 260, False, 1972, 1989),
    ("Monica Seles",         "USA", 1973,  9, 7, 178, False, 1989, 2008),
    ("Iga Swiatek",          "POL", 2001,  6, 5, 125, True,  2020, None),
    ("Martina Hingis",       "SUI", 1980,  5, 4, 209, False, 1994, 2007),
    ("Venus Williams",       "USA", 1980,  7, 3,  11, False, 1997, 2023),
    ("Justine Henin",        "BEL", 1982,  7, 3,  61, False, 2001, 2011),
    ("Aryna Sabalenka",      "BLR", 2004,  5, 2,  60, True,  2021, None),
    ("Maria Sharapova",      "RUS", 1987,  5, 0,  21, False, 2003, 2020),
    ("Lindsay Davenport",    "USA", 1976,  3, 3,  98, False, 1994, 2010),
    ("Kim Clijsters",        "BEL", 1983,  4, 1,   0, False, 1997, 2012),
    ("Billie Jean King",     "USA", 1943, 12, 0,  40, False, 1961, 1983),
]

def _legend_score_tennis(gs: int, year_end_no1: int, weeks_no1: int) -> float:
    return gs * 12 + year_end_no1 * 3 + weeks_no1 // 10

def build_legends_tennis(tour: str) -> list[dict]:
    raw_list = LEGENDS_ATP_RAW if tour == "atp" else LEGENDS_WTA_RAW
    scored   = [(_legend_score_tennis(r[3], r[4], r[5]), r) for r in raw_list]
    max_raw  = max(s for s, _ in scored)
    out = []
    for raw, row in sorted(scored, reverse=True):
        name, ioc3, born, gs, year_end_no1, weeks_no1, active, era_start, era_end = row
        primary = COUNTRY_COLORS.get(ioc3, "#555555")
        out.append({
            "id":          name.lower().replace(" ", "_").replace("ö","o").replace("é","e").replace("ñ","n"),
            "name":        name,
            "country":     ioc3,
            "logo":        _flag_url(ioc3),
            "teamCode":    ioc3,
            "primary":     primary,
            "secondary":   "#FFFFFF",
            "legendScore": round(raw / max_raw * 100, 1),
            "active":      active,
            "stats":       {
                "gs": gs, "year_end_no1": year_end_no1, "weeks_no1": weeks_no1,
                "birth": born, "era_start": era_start, "era_end": era_end,
            },
        })
    return out

# ── Main builder ──────────────────────────────────────────────────────────────

def _prev_rank_map(prev: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in prev:
        try:
            rk  = int(r.get("rank", 9999))
            pid = r.get("player", "").strip()
            if pid and rk <= 500:
                out[pid] = rk
        except ValueError:
            pass
    return out

def build_tour_data(tour: str, prev_ranks: dict[str, int] | None = None) -> list[dict]:
    print(f"[{tour.upper()}] loading player metadata…", file=sys.stderr)
    player_meta = _players(tour)

    print(f"[{tour.upper()}] loading current rankings…", file=sys.stderr)
    current_rankings = _rankings_current(tour)

    # ranked_players: [(rank, pid)]
    ranked: list[tuple[int, str]] = []
    for r in current_rankings:
        try:
            rank = int(r.get("rank", 9999))
            pid  = r.get("player", "").strip()
            if pid and rank <= 200:
                ranked.append((rank, pid))
        except ValueError:
            continue
    ranked.sort()
    top_pids = {pid for _, pid in ranked[:200]}

    print(f"[{tour.upper()}] loading match history {CAREER_START}–{CURRENT_YEAR}…", file=sys.stderr)
    all_matches: list[dict] = []
    for year in range(CAREER_START, CURRENT_YEAR + 1):
        ms = _matches(tour, year)
        all_matches.extend(_singles(ms))

    active_matches: list[dict] = []
    for year in ACTIVE_YEARS:
        ms = _matches(tour, year)
        active_matches.extend(_singles(ms))

    print(f"[{tour.upper()}] computing Elo ({len(all_matches)} matches)…", file=sys.stderr)
    elo = _build_elo(all_matches)

    print(f"[{tour.upper()}] computing surface rates…", file=sys.stderr)
    surface = _build_surface_rates(active_matches)

    print(f"[{tour.upper()}] computing form…", file=sys.stderr)
    form = _build_form(active_matches)

    print(f"[{tour.upper()}] computing opponent quality…", file=sys.stderr)
    opp_quality = _build_opp_quality(active_matches)

    print(f"[{tour.upper()}] computing career stats…", file=sys.stderr)
    career = _build_career_stats(tour, all_matches)

    print(f"[{tour.upper()}] computing weeks at #1…", file=sys.stderr)
    weeks_no1 = _build_weeks_no1(tour)

    # score all top-200 players
    all_elo_vals = [elo.get(pid, 1500.0) for _, pid in ranked[:200]]

    scored: list[dict] = []
    for rank, pid in ranked[:200]:
        meta  = player_meta.get(pid, {})
        fname = meta.get("name_first", "").strip()
        lname = meta.get("name_last",  "").strip()
        name  = f"{fname} {lname}".strip() or pid
        ioc   = meta.get("ioc", "").strip()

        active = _active_score(pid, rank, elo, all_elo_vals, surface, form, opp_quality)
        legend = _legend_score(pid, tour, career, weeks_no1)

        surf = surface.get(pid, {})

        scored.append({
            "id":          pid,
            "name":        name,
            "rank":        rank,
            "prevRank":    prev_ranks.get(pid) if prev_ranks else None,
            "country":     ioc,
            "logo":        _flag_url(ioc),
            "teamCode":    ioc,
            "primary":     COUNTRY_COLORS.get(ioc, "#555555"),
            "secondary":   "#FFFFFF",
            "activeScore": active,
            "legendScore": legend,
            "surface": {
                "hard":   surf.get("hard"),
                "clay":   surf.get("clay"),
                "grass":  surf.get("grass"),
            },
            "stats": {
                "gs":        career.get(pid, {}).get("gs", 0),
                "titles":    career.get(pid, {}).get("total_titles", 0),
                "weeks_no1": weeks_no1.get(pid, 0),
                "top10_wins":career.get(pid, {}).get("top10_wins", 0),
            },
        })

    # normalize active scores to 35-100 range
    active_vals = [p["activeScore"] for p in scored]
    a_min, a_max = min(active_vals), max(active_vals)
    for p in scored:
        if a_max > a_min:
            p["activeScore"] = round(35 + (p["activeScore"] - a_min) / (a_max - a_min) * 65, 1)
        else:
            p["activeScore"] = 70.0

    # normalize legend scores to 0-100 range
    legend_vals = [p["legendScore"] for p in scored]
    l_min, l_max = min(legend_vals), max(legend_vals)
    for p in scored:
        if l_max > l_min:
            p["legendScore"] = round((p["legendScore"] - l_min) / (l_max - l_min) * 100, 1)
        else:
            p["legendScore"] = 50.0

    score_lookup = {p["name"]: p["activeScore"] for p in scored}

    # sort by active score desc, take top N
    scored.sort(key=lambda x: x["activeScore"], reverse=True)
    return scored[:TOP_N], score_lookup


# Tournament windows: (month_start, day_start, month_end, day_end, importance)
# Listed highest-importance first so overlapping windows return the right value.
_TENNIS_CALENDAR = [
    # Grand Slams (10.0)
    (1, 12, 1, 26, 10.0),   # Australian Open
    (5, 25, 6,  8, 10.0),   # Roland Garros
    (6, 30, 7, 13, 10.0),   # Wimbledon
    (8, 25, 9,  7, 10.0),   # US Open
    # Season-ending championships (9.0)
    (10, 20, 11,  5,  9.0), # WTA Finals
    (11,  8, 11, 22,  9.0), # ATP Finals (Nitto)
    # Copa Davis Finals (8.5)
    (11, 14, 11, 26,  8.5), # Davis Cup Finals (Málaga)
    # Masters 1000 / WTA 1000 (8.0)
    (3,  4, 3, 17,  8.0),   # Indian Wells
    (3, 19, 3, 30,  8.0),   # Miami
    (4,  6, 4, 20,  8.0),   # Monte Carlo
    (4, 27, 5, 11,  8.0),   # Madrid
    (5, 12, 5, 25,  8.0),   # Rome
    (8,  5, 8, 24,  8.0),   # Canada + Cincinnati
    (10, 4, 10, 12,  8.0),  # Shanghai
    (10, 26, 11,  8,  8.0), # Paris Bercy
    # Copa Davis Group Stage (7.5)
    (9,  9, 9, 14,  7.5),   # Davis Cup Group Stage
]

def _tennis_importance() -> float:
    today = _date.today()
    year  = today.year
    # Olympics: every 4 years (2024, 2028…), tennis approx. Jul 25 – Aug 10
    if year % 4 == 0 and _date(year, 7, 25) <= today <= _date(year, 8, 10):
        return 9.5
    for m0, d0, m1, d1, score in _TENNIS_CALENDAR:
        start = _date(year, m0, d0)
        end   = _date(year, m1, d1)
        if start <= today <= end:
            return score
    return 7.0  # Ongoing tour, smaller events


def _prev_list_rank_map(tour_key: str) -> "dict[str, int]":
    """Return {player_id: 1-based list rank} from the current tennis_data.js for 'ATP' or 'WTA'."""
    import re as _re, json as _json
    try:
        out_path = ROOT / "tennis_data.js"
        text = out_path.read_text(encoding="utf-8")
        text = _re.sub(r"^\s*//.*\n", "", text)
        text = _re.sub(r"^window\.TENNIS_DATA\s*=\s*", "", text, flags=_re.MULTILINE).rstrip().rstrip(";")
        players = _json.loads(text).get(tour_key, [])
        return {str(p.get("id", "")): i + 1 for i, p in enumerate(players) if p.get("id")}
    except Exception:
        return {}


def write_data() -> None:
    # Capturar posiciones en lista Hermes ANTES de sobreescribir
    prev_atp_list = _prev_list_rank_map("ATP")
    prev_wta_list = _prev_list_rank_map("WTA")

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print("Building ATP data…", file=sys.stderr)
    atp_meta     = _players("atp")
    atp_curr, atp_prev, atp_curr_date, atp_prev_date = _rankings_two_weeks("atp")
    atp, atp_scores = build_tour_data("atp", _prev_rank_map(atp_prev))
    atp_changes  = _top10_changes(atp_curr, atp_prev, atp_meta, atp_curr_date, atp_prev_date)
    atp_legends  = build_legends_tennis("atp")
    # Añadir prevListRank (posición en nuestra lista por activeScore, semana anterior)
    for i, p in enumerate(atp):
        p["prevListRank"] = prev_atp_list.get(str(p.get("id", "")))

    print("Building WTA data…", file=sys.stderr)
    wta_meta     = _players("wta")
    wta_curr, wta_prev, wta_curr_date, wta_prev_date = _rankings_two_weeks("wta")
    wta, wta_scores = build_tour_data("wta", _prev_rank_map(wta_prev))
    wta_changes  = _top10_changes(wta_curr, wta_prev, wta_meta, wta_curr_date, wta_prev_date)
    wta_legends  = build_legends_tennis("wta")
    for i, p in enumerate(wta):
        p["prevListRank"] = prev_wta_list.get(str(p.get("id", "")))

    importance = _tennis_importance()

    print("Building recent match results…", file=sys.stderr)
    atp_score_lookup = {_name_key(name): score for name, score in atp_scores.items()}
    wta_score_lookup = {_name_key(name): score for name, score in wta_scores.items()}
    atp_tournament = _espn_current_tournament_status("atp", atp)
    wta_tournament = _espn_current_tournament_status("wta", wta)
    today = _date.today()
    yesterday = today - timedelta(days=1)
    atp_recent = (
        _espn_day_matches(atp_score_lookup, yesterday)
        or _tml_recent_results(atp_score_lookup, "yesterday")
        or _recent_results("atp", atp_score_lookup)
    )
    atp_today  = (
        _espn_day_matches(atp_score_lookup, today)
        or _tml_today_schedule(atp_score_lookup)
        or _tml_recent_results(atp_score_lookup, "today")
    )
    wta_recent = _recent_results("wta", wta_score_lookup)
    wta_today: list[dict] = []

    payload = {
        "UPDATED":     updated,
        "ATP":         atp,
        "WTA":         wta,
        "ATP_CHANGES": atp_changes,
        "WTA_CHANGES": wta_changes,
        "ATP_LEGENDS": atp_legends,
        "WTA_LEGENDS": wta_legends,
        "ATP_RECENT":  atp_recent,
        "ATP_TODAY":   atp_today,
        "WTA_RECENT":  wta_recent,
        "WTA_TODAY":   wta_today,
        "ATP_TOURNAMENT": atp_tournament,
        "WTA_TOURNAMENT": wta_tournament,
        "IMPORTANCE":  importance,
    }

    if STALE_FETCHES and os.environ.get("HERMES_ALLOW_STALE_TENNIS") != "1":
        details = "; ".join(
            f"{url} stale {age_h:.1f}h > ttl {ttl_h:.1f}h"
            for url, age_h, ttl_h in STALE_FETCHES[:6]
        )
        raise RuntimeError(f"Tennis update used stale critical cache; refusing to overwrite tennis_data.js. {details}")

    out_path = ROOT / "tennis_data.js"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"// Auto-generated {updated}\n")
        f.write(f"window.TENNIS_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n")

    print(f"Written: {out_path}", file=sys.stderr)
    print(f"  ATP top-{len(atp)}: {atp[0]['name']} (active={atp[0]['activeScore']})")
    print(f"  WTA top-{len(wta)}: {wta[0]['name']} (active={wta[0]['activeScore']})")


if __name__ == "__main__":
    write_data()
