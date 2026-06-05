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
        obj = json.loads(text)
        rows = obj.get(key) or []
        return {str(item.get("id") or item.get("name")): i + 1 for i, item in enumerate(rows[:20])}
    except Exception:
        return {}


MAJORS = [
    {"name": "The Masters", "tour": "Men", "start": "2026-04-09", "end": "2026-04-12", "venue": "Augusta National Golf Club", "location": "Augusta, Georgia", "surface": "Augusta", "defending": "Rory McIlroy"},
    {"name": "PGA Championship", "tour": "Men", "start": "2026-05-14", "end": "2026-05-17", "venue": "Aronimink Golf Club", "location": "Newtown Square, Pennsylvania", "surface": "Parkland", "defending": "Scottie Scheffler"},
    {"name": "U.S. Open", "tour": "Men", "start": "2026-06-18", "end": "2026-06-21", "venue": "Shinnecock Hills Golf Club", "location": "Southampton, New York", "surface": "U.S. Open setup", "defending": "J.J. Spaun"},
    {"name": "The Open Championship", "tour": "Men", "start": "2026-07-16", "end": "2026-07-19", "venue": "Royal Birkdale Golf Club", "location": "Southport, England", "surface": "Links", "defending": "Scottie Scheffler"},
]


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


def fetch_leaderboard(major: dict) -> list[dict]:
    # ESPN's public golf APIs vary by event; keep this best-effort and harmless.
    candidates = [
        "https://site.web.api.espn.com/apis/v2/sports/golf/leaderboard",
        "https://site.api.espn.com/apis/site/v2/sports/golf/scoreboard",
    ]
    for url in candidates:
        text = _fetch_url(url, ttl_hours=2.0)
        if not text or not text.lstrip().startswith("{"):
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        rows = []
        for comp in data.get("competitions", []) + data.get("events", []):
            name = json.dumps(comp).lower()
            if major["name"].split()[0].lower().replace(".", "") not in name:
                continue
            competitors = comp.get("competitors") or comp.get("leaderboard") or []
            for i, c in enumerate(competitors[:10]):
                athlete = c.get("athlete") or c.get("competitor") or c
                pname = athlete.get("displayName") or athlete.get("name")
                if not pname:
                    continue
                rows.append({
                    "rank": c.get("rank") or c.get("position") or i + 1,
                    "name": pname,
                    "score": c.get("score") or c.get("total") or c.get("displayScore") or "",
                    "today": c.get("today") or c.get("roundScore") or "",
                })
            if rows:
                return rows
    return []


def major_payload(today: date, current: list[dict]) -> dict:
    major = select_major(today)
    start = date.fromisoformat(major["start"])
    end = date.fromisoformat(major["end"])
    leaderboard = fetch_leaderboard(major) if major["state"] == "live" else []
    favorites = [p["name"] for p in current if p["teamCode"] == "PGA"][:5]
    days_to_start = (start - today).days
    return {
        **major,
        "startLabel": start.strftime("%d %b"),
        "endLabel": end.strftime("%d %b"),
        "round": min(4, max(0, (today - start).days + 1)) if major["state"] == "live" else 0,
        "daysToStart": max(0, days_to_start),
        "leaderboard": leaderboard,
        "favorites": favorites,
    }


def _importance(major: dict) -> float:
    if major["state"] == "live":
        return 10.0
    if major["state"] == "upcoming" and major.get("daysToStart", 99) <= 7:
        return 8.5
    if major["state"] == "completed":
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
    major = major_payload(date.today(), current)
    legend_threshold = sorted((p["legendScore"] for p in legends), reverse=True)[9]
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "UPDATED": updated,
        "SEASON": CURRENT_YEAR,
        "CURRENT_MAJOR": major,
        "CURRENT": current,
        "LEGENDS": legends,
        "ROAD_TO_GLORY": road,
        "LEGEND_THRESHOLD": round(legend_threshold, 1),
        "IMPORTANCE": _importance(major),
    }
    out_path.write_text(
        f"// Auto-generated {updated}\nwindow.GOLF_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )
    print(f"Written: {out_path}", file=sys.stderr)
    print(f"  Major: {major['name']} ({major['state']}) — {major['venue']}", file=sys.stderr)
    print(f"  Current #1: {current[0]['name']} ({current[0]['activeScore']})", file=sys.stderr)


if __name__ == "__main__":
    write_data()
