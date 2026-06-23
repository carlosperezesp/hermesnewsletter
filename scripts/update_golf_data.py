#!/usr/bin/env python3
"""Golf data: current major window, current stars, legends, and road-to-glory."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".golf_cache"
CACHE.mkdir(exist_ok=True)

CURRENT_YEAR = datetime.now(timezone.utc).year


CC3_TO_CC2 = {
    "USA": "us", "NIR": "gb-nir", "ENG": "gb-eng", "SCO": "gb-sct", "WAL": "gb-wls",
    "ESP": "es", "JPN": "jp", "KOR": "kr", "SWE": "se", "NOR": "no", "AUS": "au",
    "NZL": "nz", "CAN": "ca", "FRA": "fr", "GER": "de", "RSA": "za", "THA": "th",
    "CHN": "cn", "IRL": "ie", "MEX": "mx", "ITA": "it", "DEN": "dk", "BEL": "be",
}

COUNTRY_COLORS = {
    "USA": "#B22234", "NIR": "#012169", "ENG": "#CE1124", "SCO": "#005EB8",
    "ESP": "#AA151B", "JPN": "#BC002D", "KOR": "#003478", "SWE": "#006AA7",
    "NOR": "#EF2B2D", "AUS": "#00008B", "NZL": "#00247D", "CAN": "#FF0000",
    "FRA": "#002395", "GER": "#000000", "RSA": "#007749", "THA": "#A51931",
    "CHN": "#DE2910", "IRL": "#169B62", "MEX": "#006341", "ITA": "#009246",
    "DEN": "#C60C30", "BEL": "#000000",
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _flag(cc3: str) -> str:
    cc2 = CC3_TO_CC2.get(cc3.upper())
    return f"https://flagcdn.com/24x18/{cc2}.png" if cc2 else ""


def _color(cc3: str) -> str:
    return COUNTRY_COLORS.get(cc3.upper(), "#4A4745")


def _prev_rank_map(filepath: Path, js_var: str, key: str) -> dict[str, int]:
    try:
        text = filepath.read_text(encoding="utf-8")
        text = re.sub(r"^window\." + re.escape(js_var) + r"\s*=\s*", "", text, flags=re.MULTILINE).rstrip().rstrip(";")
        obj = json.loads(text[text.find("{"):text.rfind("}") + 1])
        rows = obj.get(key) or []
        return {str(item.get("id") or item.get("name")): i + 1 for i, item in enumerate(rows[:60])}
    except Exception:
        return {}


MAJORS = [
    {"name": "The Masters", "tour": "Men", "start": "2026-04-09", "end": "2026-04-12", "venue": "Augusta National Golf Club", "location": "Augusta, Georgia", "surface": "Augusta", "defending": "Rory McIlroy"},
    {"name": "PGA Championship", "tour": "Men", "start": "2026-05-14", "end": "2026-05-17", "venue": "Aronimink Golf Club", "location": "Newtown Square, Pennsylvania", "surface": "Parkland", "defending": "Scottie Scheffler"},
    {"name": "U.S. Open", "tour": "Men", "start": "2026-06-18", "end": "2026-06-21", "venue": "Shinnecock Hills Golf Club", "location": "Southampton, New York", "surface": "U.S. Open setup", "defending": "J.J. Spaun"},
    {"name": "The Open Championship", "tour": "Men", "start": "2026-07-16", "end": "2026-07-19", "venue": "Royal Birkdale Golf Club", "location": "Southport, England", "surface": "Links", "defending": "Scottie Scheffler"},
]


# ── Elevated tier (golf's "Masters 1000") ───────────────────────────────────
# The closest analogue to ATP Masters 1000: the PGA Tour Signature Events
# (limited fields, elevated purses) plus THE PLAYERS, the Tour's flagship. We
# don't hard-code their dates — they're read live from ESPN's season calendar,
# so the tracker follows whichever one is current with no yearly maintenance.
PGA_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"

SIGNATURE_KEYS = (
    "sentry", "pebble beach", "genesis invitational", "arnold palmer", "bay hill",
    "players championship", "rbc heritage", "cadillac championship",
    "truist championship", "wells fargo", "memorial tournament", "travelers",
)


def _is_signature(name: str) -> bool:
    n = (name or "").lower()
    return any(k in n for k in SIGNATURE_KEYS)


# name, cc3, tour, rank points, majors, elite wins, recent major top10, active score seed
CURRENT_RAW = [
    ("Scottie Scheffler", "USA", "PGA", 100, 4, 12, 15, 100),
    ("Rory McIlroy", "NIR", "PGA", 94, 6, 18, 18, 96),
    ("Xander Schauffele", "USA", "PGA", 88, 2, 10, 14, 91),
    ("Ludvig Aberg", "SWE", "PGA", 84, 0, 3, 5, 87),
    ("Jon Rahm", "ESP", "PGA", 82, 2, 9, 10, 86),
    ("Collin Morikawa", "USA", "PGA", 80, 2, 7, 11, 84),
    ("Hideki Matsuyama", "JPN", "PGA", 78, 1, 9, 9, 82),
    ("Bryson DeChambeau", "USA", "PGA", 76, 2, 6, 8, 81),
    ("Viktor Hovland", "NOR", "PGA", 74, 0, 6, 6, 79),
    ("Tommy Fleetwood", "ENG", "PGA", 72, 0, 4, 9, 77),
    ("Patrick Cantlay", "USA", "PGA", 70, 0, 8, 8, 75),
]


# name, cc3, tour/era, majors, tour wins, weeks/no1 or dominance proxy, active
LEGENDS_RAW = [
    ("Jack Nicklaus", "USA", "PGA", 18, 73, 160, False),
    ("Tiger Woods", "USA", "PGA", 15, 82, 683, False),
    ("Walter Hagen", "USA", "PGA", 11, 45, 120, False),
    ("Ben Hogan", "USA", "PGA", 9, 64, 95, False),
    ("Gary Player", "RSA", "PGA", 9, 24, 80, False),
    ("Tom Watson", "USA", "PGA", 8, 39, 75, False),
    ("Bobby Jones", "USA", "Amateur", 7, 13, 100, False),
    ("Arnold Palmer", "USA", "PGA", 7, 62, 70, False),
    ("Sam Snead", "USA", "PGA", 7, 82, 65, False),
    ("Gene Sarazen", "USA", "PGA", 7, 39, 55, False),
    ("Harry Vardon", "ENG", "PGA", 7, 49, 70, False),
    ("Seve Ballesteros", "ESP", "PGA", 5, 50, 60, False),
    ("Phil Mickelson", "USA", "PGA", 6, 45, 65, False),
    ("Lee Trevino", "USA", "PGA", 6, 29, 55, False),
    ("Rory McIlroy", "NIR", "PGA", 6, 29, 122, True),
    ("Scottie Scheffler", "USA", "PGA", 4, 18, 115, True),
]

W_LEGEND = {"major": 12.0, "win": 0.45, "dominance": 0.10}


def _legend_raw(majors: int, wins: int, dominance: int) -> float:
    return majors * W_LEGEND["major"] + wins * W_LEGEND["win"] + dominance * W_LEGEND["dominance"]


# ── Podium enrichment: Nivel (current form) + Leyenda (legacy) for ANY golfer ──
# Career majors for likely podium names that aren't in the curated CURRENT/LEGEND
# pools. Kept small and to well-known champions; everyone else defaults to 0.
CAREER_MAJORS = {
    "Wyndham Clark": 2, "Brooks Koepka": 5, "Jordan Spieth": 3,
    "Justin Thomas": 2, "Shane Lowry": 1, "Matt Fitzpatrick": 1,
    "Cameron Smith": 1, "Brian Harman": 1, "J.J. Spaun": 1,
    "Keegan Bradley": 1, "Adam Scott": 1, "Sergio Garcia": 1,
    "Jason Day": 1, "Gary Woodland": 1, "Phil Mickelson": 6,
}
_RAW_MAJORS = {r[0]: r[4] for r in CURRENT_RAW}          # name -> career majors
_RAW_MAJORS.update({r[0]: r[3] for r in LEGENDS_RAW})


def _career_majors(name: str) -> int:
    if name in _RAW_MAJORS:
        return _RAW_MAJORS[name]
    return CAREER_MAJORS.get(name, 0)


def _leyenda(majors: int) -> float:
    # Same scale as the curated legendScore (majors are the dominant term);
    # other terms unknown for arbitrary players, so this is a majors-floor.
    return round(min(72.0, _legend_raw(majors, 0, 0) / 210 * 100), 1)


def _nivel_from_rank(rank: int | None) -> int | None:
    # Season scoring-average rank → 0-100 "current level". Rank 1 ≈ 100.
    if not rank:
        return None
    return round(max(45, 100 - (rank - 1) * 0.55))


def _athlete_scoring_rank(athlete_id) -> int | None:
    """Player's season scoring-average rank from ESPN (proxy for current form)."""
    if not athlete_id:
        return None
    url = (f"https://site.web.api.espn.com/apis/common/v3/sports/golf/pga/"
           f"athletes/{athlete_id}")
    text = _fetch_url(url, ttl_hours=24.0)
    if not text or not text.lstrip().startswith("{"):
        return None
    try:
        stats = json.loads(text)["athlete"]["statsSummary"]["statistics"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    sa = next((s for s in stats if s.get("name") == "scoringAverage"), None)
    return sa.get("rank") if sa else None


def _player_base(name: str, cc3: str, tour: str, primary: str | None = None) -> dict:
    return {
        "id": _slug(name),
        "name": name,
        "country": cc3,
        "logo": _flag(cc3),
        "teamCode": tour,
        "primary": primary or _color(cc3),
        "secondary": "#FFFFFF",
        "colors": {"primary": primary or _color(cc3), "secondary": "#FFFFFF"},
    }


def build_legends(prev: dict[str, int]) -> list[dict]:
    scored = [(_legend_raw(r[3], r[4], r[5]), r) for r in LEGENDS_RAW]
    max_raw = max(raw for raw, _ in scored)
    out = []
    for raw, row in sorted(scored, reverse=True):
        name, cc3, tour, majors, wins, dominance, active = row
        p = _player_base(name, cc3, tour)
        p.update({
            "legendScore": round(raw / max_raw * 100, 1),
            "active": active,
            "stats": {"majors": majors, "wins": wins, "dominance": dominance, "tour": tour},
            "prevRank": prev.get(_slug(name)),
        })
        out.append(p)
    return out


def build_current(prev: dict[str, int], legends: list[dict]) -> list[dict]:
    legend_by_name = {p["name"]: p["legendScore"] for p in legends}
    out = []
    for name, cc3, tour, rank_pts, majors, elite_wins, major_top10, active_seed in CURRENT_RAW:
        p = _player_base(name, cc3, tour)
        raw_legend = _legend_raw(majors, elite_wins, major_top10 * 4)
        p.update({
            "activeScore": round(active_seed, 1),
            "legendScore": round(legend_by_name.get(name, min(72.0, raw_legend / 210 * 100)), 1),
            "stats": {"majors": majors, "eliteWins": elite_wins, "majorTop10": major_top10, "rankPoints": rank_pts, "tour": tour},
            "prevRank": prev.get(_slug(name)),
        })
        out.append(p)
    return sorted(out, key=lambda p: p["activeScore"], reverse=True)


# Jóvenes promesa: lista curada (como el resto del roster de golf, que es manual).
# Año de nacimiento = dato público estable; nivel = seed de fuerza en el ranking mundial.
GOLF_PROSPECTS_RAW = [
    # name, cc3, dob (YYYY-MM-DD, dato público estable), nivel_seed
    ("Ludvig Aberg", "SWE", "1999-11-16", 87),
    ("Tom Kim", "KOR", "2002-06-21", 72),
    ("Akshay Bhatia", "USA", "2002-01-31", 64),
    ("Nicolai Hojgaard", "DEN", "2001-03-16", 57),
    ("Nick Dunlap", "USA", "2003-12-18", 56),
    ("Rasmus Hojgaard", "DEN", "2001-03-16", 54),
    ("Aldrich Potgieter", "RSA", "2004-07-01", 52),
]


def build_golf_prospects(max_age: int = 26, top_n: int = 8) -> list[dict]:
    today = date.today()
    out = []
    for name, cc3, dob, seed in GOLF_PROSPECTS_RAW:
        d = date.fromisoformat(dob)
        age = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
        if age > max_age:
            continue
        p = _player_base(name, cc3, "PGA")
        if age <= 21:
            note = f"Talento generacional a los {age}"
        elif seed >= 80:
            note = f"Ya entre la élite a los {age}"
        elif seed >= 62:
            note = f"Top del circuito a los {age}"
        else:
            note = f"Promesa emergente a los {age}"
        p.update({"activeScore": float(seed), "age": age, "note": note})
        out.append(p)
    out.sort(key=lambda p: p["activeScore"], reverse=True)
    return out[:top_n]


def build_road_to_glory(prev: dict[str, int], current: list[dict], legends: list[dict]) -> list[dict]:
    threshold = sorted((p["legendScore"] for p in legends), reverse=True)[9]
    rows = []
    for p in current:
        gap = max(0.0, threshold - p["legendScore"])
        rows.append({
            **p,
            "gapToTop10": round(gap, 1),
            "note": "Ya está en zona top 10 histórico" if gap <= 0 else f"A {gap:.1f} del top 10 histórico",
            "prevRank": prev.get(p["id"]),
        })
    return sorted(rows, key=lambda p: (p["gapToTop10"], -p["activeScore"]))[:10]


def _major_state(major: dict, today: date) -> str:
    start = date.fromisoformat(major["start"])
    end = date.fromisoformat(major["end"])
    if start <= today <= end:
        return "live"
    if today < start:
        return "upcoming"
    return "completed"


def select_major(today: date) -> dict:
    enriched = [{**m, "state": _major_state(m, today)} for m in MAJORS]
    live = [m for m in enriched if m["state"] == "live"]
    if live:
        return sorted(live, key=lambda m: m["start"])[0]
    upcoming = [m for m in enriched if m["state"] == "upcoming"]
    if upcoming:
        return sorted(upcoming, key=lambda m: m["start"])[0]
    return sorted(enriched, key=lambda m: m["end"])[-1]


def _fetch_url(url: str, ttl_hours: float = 6.0) -> str:
    key = hashlib.md5(url.encode()).hexdigest()
    path = CACHE / key
    if path.exists() and (time.time() - path.stat().st_mtime) / 3600 < ttl_hours:
        return path.read_text(encoding="utf-8")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            text = r.read().decode("utf-8", errors="replace")
        path.write_text(text, encoding="utf-8")
        return text
    except Exception as exc:
        print(f"[WARN] Golf live fetch failed ({exc})", file=sys.stderr)
        return path.read_text(encoding="utf-8") if path.exists() else ""


def _fetch_pga_scoreboard(ttl_hours: float = 2.0) -> dict:
    text = _fetch_url(PGA_SCOREBOARD_URL, ttl_hours=ttl_hours)
    if not text or not text.lstrip().startswith("{"):
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _fetch_scoreboard_window(start: str, end: str, ttl_hours: float = 24.0) -> dict:
    """ESPN scoreboard for a specific date window (e.g. a finished major's
    week), so we can read its final leaderboard once ESPN moves on."""
    url = f"{PGA_SCOREBOARD_URL}?dates={start.replace('-', '')}-{end.replace('-', '')}"
    text = _fetch_url(url, ttl_hours=ttl_hours)
    if not text or not text.lstrip().startswith("{"):
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


# Distinctive words that confirm two event names refer to the same tournament,
# so "U.S. Open" never cross-matches "The Open" on the shared word "open".
_STRONG_TOKENS = {
    "masters", "pga", "sentry", "genesis", "arnold", "palmer", "players",
    "heritage", "cadillac", "truist", "memorial", "travelers", "pebble", "sawgrass",
}


def _same_event(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    shared = set(na.split()) & set(nb.split())
    return bool(shared & _STRONG_TOKENS) or len(shared) >= 2


def _clean_event_name(name: str) -> str:
    # Drop the sponsor tail ESPN appends, e.g. "the Memorial Tournament pres. by Workday".
    return re.split(r"\s+pres(?:ented)?\.?\s+by\s+", name, flags=re.IGNORECASE)[0].strip()


def _parse_leaderboard(competitors: list, limit: int = 10) -> list[dict]:
    rows = []
    for i, c in enumerate(competitors):
        ath = c.get("athlete") or {}
        name = ath.get("displayName") or ath.get("fullName")
        if not name:
            continue
        score = c.get("score")
        if isinstance(score, dict):
            score = score.get("displayValue")
        rounds = c.get("linescores") or []
        today = rounds[-1].get("displayValue", "") if rounds else ""
        if today in ("-", "--"):  # hasn't teed off in the current round yet
            today = ""
        rows.append({
            "rank": c.get("order") or i + 1,
            "name": name,
            "id": c.get("id"),  # ESPN athlete id — used to fetch season form
            "country": (ath.get("flag") or {}).get("alt", ""),
            "score": score or "",
            "today": today,
        })
        if len(rows) >= limit:
            break
    return rows


def _scoreboard_current(data: dict) -> dict:
    """The PGA event being played this week, plus its parsed leaderboard."""
    events = data.get("events") or []
    if not events:
        return {}
    ev = events[0]
    comp = (ev.get("competitions") or [{}])[0]
    state = (comp.get("status") or {}).get("type", {}).get("state", "")
    return {
        "name": ev.get("name") or ev.get("shortName") or "",
        "state": state,  # "pre" | "in" | "post"
        "leaderboard": _parse_leaderboard(comp.get("competitors") or []),
    }


def _calendar_events(data: dict) -> list[dict]:
    lg = (data.get("leagues") or [{}])[0]
    out = []
    for c in lg.get("calendar") or []:
        if not isinstance(c, dict):
            continue
        label = c.get("label") or c.get("value") or ""
        sd = (c.get("startDate") or "")[:10]
        ed = (c.get("endDate") or "")[:10]
        if label and sd and ed:
            out.append({"name": label, "start": sd, "end": ed})
    return out


def _window_state(start: str, end: str, today: date) -> str:
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    if s <= today <= e:
        return "live"
    return "upcoming" if today < s else "completed"


def select_signature(calendar: list[dict], today: date) -> dict:
    elevated = [
        {**e, "state": _window_state(e["start"], e["end"], today)}
        for e in calendar if _is_signature(e["name"])
    ]
    if not elevated:
        return {}
    live = [e for e in elevated if e["state"] == "live"]
    if live:
        return sorted(live, key=lambda e: e["start"])[0]
    upcoming = [e for e in elevated if e["state"] == "upcoming"]
    if upcoming:
        return sorted(upcoming, key=lambda e: e["start"])[0]
    completed = [e for e in elevated if e["state"] == "completed"]
    return sorted(completed, key=lambda e: e["end"])[-1] if completed else {}


def _event_payload(event: dict, today: date, current: list[dict],
                   current_event: dict, tier: str) -> dict:
    start = date.fromisoformat(event["start"])
    end = date.fromisoformat(event["end"])
    live = event.get("state") == "live"
    leaderboard = (
        current_event.get("leaderboard", [])
        if live and current_event and _same_event(event["name"], current_event.get("name", ""))
        else []
    )
    favorites = [p["name"] for p in current if p["teamCode"] == "PGA"][:5]
    return {
        **event,
        "name": _clean_event_name(event["name"]),
        "tier": tier,
        "startLabel": start.strftime("%d %b"),
        "endLabel": end.strftime("%d %b"),
        "round": min(4, max(0, (today - start).days + 1)) if live else 0,
        "daysToStart": max(0, (start - today).days),
        "leaderboard": leaderboard,
        "favorites": favorites,
    }


def major_payload(today: date, current: list[dict], current_event: dict) -> dict:
    return _event_payload(select_major(today), today, current, current_event, "Major")


def select_last_major(today: date) -> dict:
    """The most recently finished major (so its champion is never dropped when
    CURRENT_MAJOR rolls forward to the next, far-off one)."""
    done = [{**m, "state": _major_state(m, today)} for m in MAJORS]
    done = [m for m in done if m["state"] == "completed"]
    return sorted(done, key=lambda m: m["end"])[-1] if done else {}


def last_major_payload(today: date, current_event: dict) -> dict:
    m = select_last_major(today)
    if not m:
        return {}
    # Final leaderboard: prefer the live scoreboard if it still sits on this
    # event in "post" state; otherwise pull the major's own date window.
    lb = []
    if (current_event and current_event.get("state") == "post"
            and _same_event(m["name"], current_event.get("name", ""))):
        lb = current_event.get("leaderboard", [])
    if not lb:
        cur = _scoreboard_current(_fetch_scoreboard_window(m["start"], m["end"]))
        if cur.get("state") == "post" and _same_event(m["name"], cur.get("name", "")):
            lb = cur.get("leaderboard", [])
    end = date.fromisoformat(m["end"])
    podium = lb[:5]
    # Nivel (current form from ESPN season stats) + Leyenda (career majors) for
    # every podium player, so over/under-performance is visible at a glance.
    for row in podium:
        row["nivel"] = _nivel_from_rank(_athlete_scoring_rank(row.get("id")))
        row["legend"] = _leyenda(_career_majors(row["name"]))
    return {
        "name": _clean_event_name(m["name"]),
        "venue": m["venue"], "location": m["location"], "surface": m["surface"],
        "tour": m["tour"], "end": m["end"], "endLabel": end.strftime("%d %b %Y"),
        "champion": podium[0] if podium else None,
        "podium": podium,
    }


def signature_payload(today: date, calendar: list[dict], current: list[dict],
                      current_event: dict) -> dict:
    sig = select_signature(calendar, today)
    return _event_payload(sig, today, current, current_event, "Signature Event") if sig else {}


def _importance(major: dict, signature: dict) -> float:
    if major.get("state") == "live" or signature.get("state") == "live":
        return 10.0
    soon = (major.get("state") == "upcoming" and major.get("daysToStart", 99) <= 7) or \
           (signature.get("state") == "upcoming" and signature.get("daysToStart", 99) <= 7)
    if soon:
        return 8.5
    if major.get("state") == "completed":
        return 6.5
    return 5.0


def write_data() -> None:
    out_path = ROOT / "golf_data.js"
    prev_current = _prev_rank_map(out_path, "GOLF_DATA", "CURRENT")
    prev_legends = _prev_rank_map(out_path, "GOLF_DATA", "LEGENDS")
    prev_road = _prev_rank_map(out_path, "GOLF_DATA", "ROAD_TO_GLORY")
    legends = build_legends(prev_legends)
    current = build_current(prev_current, legends)
    road = build_road_to_glory(prev_road, current, legends)
    today = date.today()
    scoreboard = _fetch_pga_scoreboard()
    current_event = _scoreboard_current(scoreboard)
    calendar = _calendar_events(scoreboard)
    major = major_payload(today, current, current_event)
    last_major = last_major_payload(today, current_event)
    signature = signature_payload(today, calendar, current, current_event)
    legend_threshold = sorted((p["legendScore"] for p in legends), reverse=True)[9]
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "UPDATED": updated,
        "SEASON": CURRENT_YEAR,
        "CURRENT_MAJOR": major,
        "LAST_MAJOR": last_major,
        "CURRENT_SIGNATURE": signature,
        "CURRENT": current,
        "PROSPECTS": build_golf_prospects(),
        "LEGENDS": legends,
        "ROAD_TO_GLORY": road,
        "LEGEND_THRESHOLD": round(legend_threshold, 1),
        "IMPORTANCE": _importance(major, signature),
    }
    out_path.write_text(
        f"// Auto-generated {updated}\nwindow.GOLF_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )
    print(f"Written: {out_path}", file=sys.stderr)
    print(f"  Major: {major['name']} ({major['state']}) — {major.get('venue', '')}", file=sys.stderr)
    if last_major:
        champ = (last_major.get("champion") or {}).get("name", "—")
        print(f"  Last major: {last_major['name']} → {champ} ({last_major.get('champion', {}).get('score', '')})", file=sys.stderr)
    if signature:
        print(f"  Signature: {signature['name']} ({signature['state']}) — {len(signature['leaderboard'])} lb rows", file=sys.stderr)
    print(f"  Current #1: {current[0]['name']} ({current[0]['activeScore']})", file=sys.stderr)


if __name__ == "__main__":
    write_data()
