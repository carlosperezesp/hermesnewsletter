#!/usr/bin/env python3
"""IndyCar data: standings, last race, legends. Uses ESPN API."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".indycar_cache"
CACHE.mkdir(exist_ok=True)

CURRENT_YEAR = datetime.now(timezone.utc).year

ESPN_STANDINGS = "https://site.api.espn.com/apis/v2/sports/racing/irl/standings"
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/racing/irl/scoreboard"

CC2_TO_CC3 = {
    "aus": "AUS", "bra": "BRA", "can": "CAN", "cay": "CAY", "den": "DEN",
    "eng": "GBR", "esp": "ESP", "fra": "FRA", "ger": "GER", "mex": "MEX",
    "ned": "NED", "nzl": "NZL", "nor": "NOR", "swe": "SWE", "usa": "USA",
}

COUNTRY_COLORS = {
    "USA": "#B22234", "ESP": "#AA151B", "NZL": "#00247D", "MEX": "#006847",
    "SWE": "#006AA7", "DEN": "#C60C30", "AUS": "#00008B", "BRA": "#009C3B",
    "FRA": "#002395", "GBR": "#012169", "NED": "#AE1C28", "CAN": "#D52B1E",
    "GER": "#000000", "NOR": "#BA0C2F",
}

TEAM_BY_DRIVER = {
    "Álex Palou": "Chip Ganassi Racing",
    "Alex Palou": "Chip Ganassi Racing",
    "Scott Dixon": "Chip Ganassi Racing",
    "Kyffin Simpson": "Chip Ganassi Racing",
    "Josef Newgarden": "Team Penske",
    "Scott McLaughlin": "Team Penske",
    "Will Power": "Team Penske",
    "Pato O'Ward": "Arrow McLaren",
    "Christian Lundgaard": "Arrow McLaren",
    "Nolan Siegel": "Arrow McLaren",
    "Kyle Kirkwood": "Andretti Global",
    "Marcus Ericsson": "Andretti Global",
    "Colton Herta": "Andretti Global",
    "Felix Rosenqvist": "Meyer Shank Racing",
    "David Malukas": "A. J. Foyt Racing",
    "Santino Ferrucci": "A. J. Foyt Racing",
    "Rinus VeeKay": "Dale Coyne Racing",
    "Louis Foster": "Rahal Letterman Lanigan",
    "Graham Rahal": "Rahal Letterman Lanigan",
    "Devlin DeFrancesco": "Rahal Letterman Lanigan",
    "Sting Ray Robb": "Juncos Hollinger Racing",
    "Conor Daly": "Juncos Hollinger Racing",
    "Alexander Rossi": "Ed Carpenter Racing",
    "Christian Rasmussen": "Ed Carpenter Racing",
    "Romain Grosjean": "Prema Racing",
    "Mick Schumacher": "Prema Racing",
    "Robert Shwartzman": "Prema Racing",
    "Marcus Armstrong": "Meyer Shank Racing",
}

TEAM_COLORS = {
    "Chip Ganassi Racing": {"primary": "#D71920", "secondary": "#FFFFFF"},
    "Team Penske": {"primary": "#E31837", "secondary": "#002D72"},
    "Arrow McLaren": {"primary": "#FF8700", "secondary": "#111111"},
    "Andretti Global": {"primary": "#003DA5", "secondary": "#FFFFFF"},
    "Meyer Shank Racing": {"primary": "#EE2737", "secondary": "#111111"},
    "A. J. Foyt Racing": {"primary": "#C8102E", "secondary": "#FFFFFF"},
    "Dale Coyne Racing": {"primary": "#111111", "secondary": "#D71920"},
    "Rahal Letterman Lanigan": {"primary": "#005BBB", "secondary": "#FFFFFF"},
    "Juncos Hollinger Racing": {"primary": "#1C8B43", "secondary": "#111111"},
    "Ed Carpenter Racing": {"primary": "#005EB8", "secondary": "#F2A900"},
    "Prema Racing": {"primary": "#C8002F", "secondary": "#FFFFFF"},
}

INDYCAR_LEGENDS_RAW = [
    ("A. J. Foyt", "USA", 1935, 7, 67, 53, False),
    ("Scott Dixon", "NZL", 1980, 6, 58, 34, True),
    ("Mario Andretti", "USA", 1940, 4, 52, 67, False),
    ("Dario Franchitti", "GBR", 1973, 4, 31, 33, False),
    ("Al Unser", "USA", 1939, 3, 39, 28, False),
    ("Bobby Unser", "USA", 1934, 2, 35, 49, False),
    ("Josef Newgarden", "USA", 1990, 2, 31, 18, True),
    ("Will Power", "AUS", 1981, 2, 43, 70, True),
    ("Alex Palou", "ESP", 1997, 4, 17, 7, True),
    ("Juan Pablo Montoya", "COL", 1975, 1, 15, 14, False),
    ("Helio Castroneves", "BRA", 1975, 0, 31, 50, False),
]

INDYCAR_CURRENT_RAW = [
    ("Scott Dixon", "NZL", 1980, 6, 58, 34, True),
    ("Alex Palou", "ESP", 1997, 4, 17, 7, True),
    ("Josef Newgarden", "USA", 1990, 2, 31, 18, True),
    ("Will Power", "AUS", 1981, 2, 43, 70, True),
    ("Scott McLaughlin", "NZL", 1993, 0, 8, 8, True),
    ("Pato O'Ward", "MEX", 1999, 0, 7, 6, True),
    ("Colton Herta", "USA", 2000, 0, 9, 14, True),
    ("Marcus Ericsson", "SWE", 1990, 0, 4, 0, True),
    ("Kyle Kirkwood", "USA", 1998, 0, 3, 3, True),
    ("Felix Rosenqvist", "SWE", 1991, 0, 1, 6, True),
    ("Rinus VeeKay", "NED", 2000, 0, 1, 2, True),
    ("David Malukas", "USA", 2001, 0, 0, 1, True),
]

W_LEGEND = {"titles": 12.0, "wins": 0.45, "poles": 0.20}


def _driver_id(name: str) -> str:
    return name.lower().replace(" ", "_").replace(".", "").replace("'", "").replace("á", "a")


def _legend_raw(row: tuple) -> float:
    *_head, titles, wins, poles, _active = row
    return titles * W_LEGEND["titles"] + wins * W_LEGEND["wins"] + poles * W_LEGEND["poles"]


def _fetch(url: str, ttl_hours: float = 1.0) -> dict | None:
    key = hashlib.md5(url.encode()).hexdigest()
    path = CACHE / key
    if path.exists() and (time.time() - path.stat().st_mtime) / 3600 < ttl_hours:
        return json.loads(path.read_text())
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
        with urllib.request.urlopen(req, timeout=20) as res:
            data = json.loads(res.read().decode("utf-8"))
        path.write_text(json.dumps(data), encoding="utf-8")
        return data
    except Exception as exc:
        print(f"[WARN] IndyCar fetch failed ({exc}): {url}", file=sys.stderr)
        return json.loads(path.read_text()) if path.exists() else None


def _prev_rank_map(filepath: Path, js_var: str, path_key: str) -> dict[str, int]:
    try:
        text = filepath.read_text(encoding="utf-8")
        text = re.sub(r"^window\." + re.escape(js_var) + r"\s*=\s*", "", text).rstrip().rstrip(";")
        obj = json.loads(text)
        rows = obj.get(path_key) or []
        return {str(row.get("id") or row.get("name")): i + 1 for i, row in enumerate(rows[:40])}
    except Exception:
        return {}


def _cc3_from_flag(flag_url: str) -> str:
    if not flag_url:
        return "USA"
    stem = flag_url.rstrip("/").split("/")[-1].replace(".png", "").lower()
    return CC2_TO_CC3.get(stem, stem.upper())


def _flag(cc3: str) -> str:
    cc2 = {
        "AUS": "au", "BRA": "br", "CAN": "ca", "CAY": "ky", "COL": "co",
        "DEN": "dk", "ESP": "es", "FRA": "fr", "GBR": "gb", "GER": "de",
        "MEX": "mx", "NED": "nl", "NOR": "no", "NZL": "nz", "SWE": "se",
        "USA": "us",
    }.get(cc3, cc3.lower()[:2])
    return f"https://flagcdn.com/24x18/{cc2}.png"


def _stat(entry: dict, name: str, default: float = 0.0) -> float:
    for stat in entry.get("stats", []):
        if stat.get("name") == name:
            return float(stat.get("value") or stat.get("displayValue") or default)
    return default


def _race_stats(entries: list[dict]) -> tuple[int, int, list[str]]:
    race_names: list[str] = []
    played = 0
    for stat in (entries[0].get("stats", []) if entries else []):
        if not stat.get("id") or not stat.get("displayName"):
            continue
        race_names.append(stat["displayName"])
        if stat.get("played"):
            played += 1
    return played, len(race_names), race_names


def build_standings() -> tuple[list[dict], int, int]:
    data = _fetch(ESPN_STANDINGS)
    entries = (((data or {}).get("children") or [{}])[0].get("standings") or {}).get("entries") or []
    completed, total, _race_names = _race_stats(entries)
    max_pts = max(total * 54, 1)
    prev = _prev_rank_map(ROOT / "indycar_data.js", "INDYCAR_DATA", "DRIVERS")
    max_legend_raw = max(_legend_raw(row) for row in INDYCAR_LEGENDS_RAW)
    legend_by_name = {
        row[0].lower().replace("á", "a"): round(_legend_raw(row) / max_legend_raw * 100, 1)
        for row in INDYCAR_CURRENT_RAW
    }
    rows: list[dict] = []
    for entry in entries:
        athlete = entry.get("athlete") or {}
        name = athlete.get("displayName") or athlete.get("name") or ""
        if not name:
            continue
        points = _stat(entry, "championshipPts")
        rank = int(_stat(entry, "rank", len(rows) + 1))
        cc3 = _cc3_from_flag((athlete.get("flag") or {}).get("href", ""))
        team = TEAM_BY_DRIVER.get(name) or TEAM_BY_DRIVER.get(name.replace("Á", "A")) or "IndyCar"
        colors = TEAM_COLORS.get(team) or {"primary": COUNTRY_COLORS.get(cc3, "#555555"), "secondary": "#FFFFFF"}
        row_id = str(athlete.get("id") or name)
        rows.append({
            "id": row_id,
            "position": rank,
            "name": name,
            "country": cc3,
            "team": team,
            "teamCode": team.split()[0].upper(),
            "logo": _flag(cc3),
            "primary": colors["primary"],
            "secondary": colors["secondary"],
            "colors": colors,
            "points": points,
            "score": round(points / max_pts * 100, 1),
            "legendScore": legend_by_name.get(name.lower().replace("á", "a"), 0.0),
            "prevRank": prev.get(row_id, prev.get(name)),
            "stats": {"pts": points},
        })
    rows.sort(key=lambda r: r["position"])
    return rows, completed, total


def build_last_race(drivers_by_name: dict[str, dict]) -> dict | None:
    data = _fetch(ESPN_SCOREBOARD, ttl_hours=0.5)
    events = (data or {}).get("events") or []
    completed = [event for event in events if ((event.get("status") or {}).get("type") or {}).get("completed")]
    if not completed:
        return None
    event = completed[-1]
    comp = ((event.get("competitions") or [{}])[0])
    podium = []
    for comp_entry in (comp.get("competitors") or [])[:5]:
        athlete = comp_entry.get("athlete") or {}
        name = athlete.get("displayName") or athlete.get("fullName") or ""
        info = drivers_by_name.get(name) or {}
        cc3 = _cc3_from_flag((athlete.get("flag") or {}).get("href", ""))
        podium.append({
            "position": int(comp_entry.get("order") or len(podium) + 1),
            "name": name,
            "country": info.get("country") or cc3,
            "team": info.get("team") or "IndyCar",
            "logo": info.get("logo") or _flag(cc3),
            "primary": info.get("primary") or COUNTRY_COLORS.get(cc3, "#555555"),
        })
    return {
        "round": None,
        "name": event.get("name") or event.get("shortName"),
        "circuit": event.get("shortName") or "",
        "date": (event.get("date") or "")[:10],
        "winner": podium[0]["name"] if podium else "",
        "podium": podium,
    }


def build_legends() -> list[dict]:
    max_raw = max(_legend_raw(row) for row in INDYCAR_LEGENDS_RAW)
    out = []
    for row in sorted(INDYCAR_LEGENDS_RAW, key=_legend_raw, reverse=True):
        name, cc3, born, titles, wins, poles, active = row
        primary = COUNTRY_COLORS.get(cc3, "#555555")
        out.append({
            "id": name.lower().replace(" ", "_").replace(".", ""),
            "name": name,
            "country": cc3,
            "logo": _flag(cc3),
            "teamCode": cc3,
            "primary": primary,
            "secondary": "#FFFFFF",
            "colors": {"primary": primary, "secondary": "#FFFFFF"},
            "legendScore": round(_legend_raw(row) / max_raw * 100, 1),
            "active": active,
            "stats": {"titles": titles, "wins": wins, "poles": poles, "birth": born},
        })
    return out


def build_current_contenders(legend_threshold: float) -> list[dict]:
    max_raw = max(_legend_raw(row) for row in INDYCAR_LEGENDS_RAW)
    prev = _prev_rank_map(ROOT / "indycar_data.js", "INDYCAR_DATA", "CURRENT_CONTENDERS")
    rows = []
    for row in INDYCAR_CURRENT_RAW:
        name, cc3, born, titles, wins, poles, active = row
        team = TEAM_BY_DRIVER.get(name) or TEAM_BY_DRIVER.get(name.replace("Alex", "Álex")) or cc3
        colors = TEAM_COLORS.get(team) or {"primary": COUNTRY_COLORS.get(cc3, "#555555"), "secondary": "#FFFFFF"}
        score = round(_legend_raw(row) / max_raw * 100, 1)
        rows.append({
            "id": _driver_id(name),
            "name": name,
            "country": cc3,
            "logo": _flag(cc3),
            "team": team,
            "teamCode": cc3,
            "primary": colors["primary"],
            "secondary": colors["secondary"],
            "colors": colors,
            "legendScore": score,
            "gapToTop10": round(max(0, legend_threshold - score), 1),
            "active": active,
            "prevRank": prev.get(_driver_id(name), prev.get(name)),
            "stats": {"titles": titles, "wins": wins, "poles": poles, "birth": born},
        })
    return sorted(rows, key=lambda x: x["legendScore"], reverse=True)[:10]


def _importance(drivers: list[dict], completed: int, total: int) -> float:
    if not total:
        return 6.5
    base = 6.5 + min(completed / total, 1) * 2.0
    if len(drivers) >= 2:
        gap = drivers[0]["points"] - drivers[1]["points"]
        remaining = (total - completed) * 54
        if gap <= remaining:
            base += 0.6
    return round(min(9.5, base), 1)


def main() -> int:
    drivers, completed, total = build_standings()
    if not drivers:
        print("No IndyCar standings found", file=sys.stderr)
        return 1
    by_name = {driver["name"]: driver for driver in drivers}
    legends = build_legends()
    legend_threshold = legends[9]["legendScore"] if len(legends) >= 10 else 0
    payload = {
        "UPDATED": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "SEASON": CURRENT_YEAR,
        "ROUND": completed,
        "TOTAL_ROUNDS": total,
        "MAX_SEASON_PTS": total * 54,
        "IMPORTANCE": _importance(drivers, completed, total),
        "LEGEND_THRESHOLD": legend_threshold,
        "DRIVERS": drivers,
        "LAST_RACE": build_last_race(by_name),
        "CURRENT_CONTENDERS": build_current_contenders(legend_threshold),
        "LEGENDS": legends,
    }
    (ROOT / "indycar_data.js").write_text(
        "window.INDYCAR_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"IndyCar data updated: {len(drivers)} drivers, round {completed}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
