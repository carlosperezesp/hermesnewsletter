#!/usr/bin/env python3
"""NASCAR Cup data: ESPN standings/results, playoff picture, legends."""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".nascar_cache"
CACHE.mkdir(exist_ok=True)

CURRENT_YEAR = datetime.now(timezone.utc).year

ESPN_STANDINGS = "https://www.espn.com/racing/standings"
ESPN_RESULTS = "https://www.espn.com/racing/results"

MANUFACTURER_COLORS = {
    "Chevrolet": {"primary": "#F7C600", "secondary": "#111111"},
    "Ford": {"primary": "#003478", "secondary": "#FFFFFF"},
    "Toyota": {"primary": "#EB0A1E", "secondary": "#FFFFFF"},
    "NASCAR": {"primary": "#E4002B", "secondary": "#FFD200"},
}

MANUFACTURER_BY_DRIVER = {
    "Tyler Reddick": "Toyota", "Denny Hamlin": "Toyota", "Ty Gibbs": "Toyota",
    "Christopher Bell": "Toyota", "Bubba Wallace": "Toyota", "Chase Briscoe": "Toyota",
    "Ryan Blaney": "Ford", "Joey Logano": "Ford", "Chris Buescher": "Ford",
    "Brad Keselowski": "Ford", "Ryan Preece": "Ford", "Austin Cindric": "Ford",
    "Josh Berry": "Ford", "Noah Gragson": "Ford",
    "Chase Elliott": "Chevrolet", "Kyle Larson": "Chevrolet", "William Byron": "Chevrolet",
    "Alex Bowman": "Chevrolet", "Daniel Suarez": "Chevrolet", "Ross Chastain": "Chevrolet",
    "Carson Hocevar": "Chevrolet", "Kyle Busch": "Chevrolet", "Austin Dillon": "Chevrolet",
    "Shane van Gisbergen": "Chevrolet", "Ricky Stenhouse Jr.": "Chevrolet",
}

TEAM_BY_DRIVER = {
    "Tyler Reddick": "23XI Racing", "Denny Hamlin": "Joe Gibbs Racing",
    "Ty Gibbs": "Joe Gibbs Racing", "Christopher Bell": "Joe Gibbs Racing",
    "Ryan Blaney": "Team Penske", "Joey Logano": "Team Penske",
    "Austin Cindric": "Team Penske", "Chase Elliott": "Hendrick Motorsports",
    "Kyle Larson": "Hendrick Motorsports", "William Byron": "Hendrick Motorsports",
    "Alex Bowman": "Hendrick Motorsports", "Chris Buescher": "RFK Racing",
    "Brad Keselowski": "RFK Racing", "Daniel Suarez": "Trackhouse Racing",
    "Ross Chastain": "Trackhouse Racing", "Shane van Gisbergen": "Trackhouse Racing",
    "Carson Hocevar": "Spire Motorsports", "Kyle Busch": "Richard Childress Racing",
    "Austin Dillon": "Richard Childress Racing", "Bubba Wallace": "23XI Racing",
    "Chase Briscoe": "Joe Gibbs Racing", "Ryan Preece": "RFK Racing",
}

NASCAR_LEGENDS_RAW = [
    ("Richard Petty", "USA", 1937, 7, 200, 123, False),
    ("Dale Earnhardt", "USA", 1951, 7, 76, 22, False),
    ("Jimmie Johnson", "USA", 1975, 7, 83, 36, False),
    ("Jeff Gordon", "USA", 1971, 4, 93, 81, False),
    ("David Pearson", "USA", 1934, 3, 105, 113, False),
    ("Darrell Waltrip", "USA", 1947, 3, 84, 59, False),
    ("Cale Yarborough", "USA", 1939, 3, 83, 69, False),
    ("Kyle Busch", "USA", 1985, 2, 63, 33, True),
    ("Joey Logano", "USA", 1990, 3, 36, 32, True),
    ("Kyle Larson", "USA", 1992, 1, 29, 21, True),
    ("Denny Hamlin", "USA", 1980, 0, 55, 41, True),
]

NASCAR_CURRENT_RAW = [
    ("Kyle Busch", "USA", 1985, 2, 63, 33, True),
    ("Joey Logano", "USA", 1990, 3, 36, 32, True),
    ("Denny Hamlin", "USA", 1980, 0, 55, 41, True),
    ("Kyle Larson", "USA", 1992, 1, 29, 21, True),
    ("Brad Keselowski", "USA", 1984, 1, 36, 18, True),
    ("Chase Elliott", "USA", 1995, 1, 19, 13, True),
    ("Ryan Blaney", "USA", 1993, 1, 13, 11, True),
    ("William Byron", "USA", 1997, 0, 13, 16, True),
    ("Christopher Bell", "USA", 1994, 0, 9, 13, True),
    ("Tyler Reddick", "USA", 1996, 0, 8, 8, True),
    ("Chase Briscoe", "USA", 1994, 0, 2, 4, True),
    ("Ty Gibbs", "USA", 2002, 0, 1, 1, True),
]

W_LEGEND = {"titles": 13.0, "wins": 0.35, "poles": 0.15}


def _driver_id(name: str) -> str:
    return name.lower().replace(" ", "_").replace(".", "")


def _legend_raw(row: tuple) -> float:
    *_head, titles, wins, poles, _active = row
    return titles * W_LEGEND["titles"] + wins * W_LEGEND["wins"] + poles * W_LEGEND["poles"]


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.links: list[list[str]] = []
        self._in_td = False
        self._in_tr = False
        self._cell: list[str] = []
        self._row: list[str] = []
        self._row_links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "tr" and ("oddrow" in (attrs_dict.get("class") or "") or "evenrow" in (attrs_dict.get("class") or "")):
            self._in_tr = True
            self._row = []
            self._row_links = []
        elif self._in_tr and tag == "td":
            self._in_td = True
            self._cell = []
        elif self._in_td and tag == "br":
            self._cell.append(" | ")
        elif self._in_tr and tag == "a":
            href = attrs_dict.get("href") or ""
            if href:
                self._row_links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._in_td:
            value = " ".join("".join(self._cell).split())
            self._row.append(html.unescape(value))
            self._in_td = False
        elif tag == "tr" and self._in_tr:
            if self._row:
                self.rows.append(self._row)
                self.links.append(self._row_links)
            self._in_tr = False

    def handle_data(self, data: str) -> None:
        if self._in_td:
            self._cell.append(data)


def _fetch_text(url: str, ttl_hours: float = 1.0) -> str:
    key = re.sub(r"[^a-zA-Z0-9]+", "_", url).strip("_")[:180]
    path = CACHE / f"{key}.html"
    if path.exists() and (time.time() - path.stat().st_mtime) / 3600 < ttl_hours:
        return path.read_text(encoding="utf-8", errors="ignore")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
        with urllib.request.urlopen(req, timeout=20) as res:
            text = res.read().decode("utf-8", errors="ignore")
        path.write_text(text, encoding="utf-8")
        return text
    except Exception as exc:
        print(f"[WARN] NASCAR fetch failed ({exc}): {url}", file=sys.stderr)
        return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def _prev_rank_map(path_key: str = "DRIVERS") -> dict[str, int]:
    try:
        text = (ROOT / "nascar_data.js").read_text(encoding="utf-8")
        text = re.sub(r"^window\.NASCAR_DATA\s*=\s*", "", text).rstrip().rstrip(";")
        obj = json.loads(text)
        return {str(row.get("id") or row.get("name")): i + 1 for i, row in enumerate(obj.get(path_key) or [])}
    except Exception:
        return {}


def _flag() -> str:
    return "https://flagcdn.com/24x18/us.png"


def _colors(manufacturer: str) -> dict:
    return MANUFACTURER_COLORS.get(manufacturer) or MANUFACTURER_COLORS["NASCAR"]


def parse_standings() -> list[dict]:
    parser = TableParser()
    parser.feed(_fetch_text(ESPN_STANDINGS))
    prev = _prev_rank_map()
    max_legend_raw = max(_legend_raw(row) for row in NASCAR_LEGENDS_RAW)
    legend_by_name = {row[0]: round(_legend_raw(row) / max_legend_raw * 100, 1) for row in NASCAR_CURRENT_RAW}
    rows: list[dict] = []
    for row in parser.rows:
        if len(row) < 7 or not row[0].isdigit():
            continue
        name = row[1]
        points = int(row[2]) if row[2].isdigit() else 0
        wins = int(row[3]) if row[3].isdigit() else 0
        poles = int(row[4]) if row[4].isdigit() else 0
        top5 = int(row[5]) if row[5].isdigit() else 0
        top10 = int(row[6]) if row[6].isdigit() else 0
        manufacturer = MANUFACTURER_BY_DRIVER.get(name, "NASCAR")
        colors = _colors(manufacturer)
        row_id = name.lower().replace(" ", "_").replace(".", "")
        rows.append({
            "id": row_id,
            "position": int(row[0]),
            "name": name,
            "country": "USA",
            "team": TEAM_BY_DRIVER.get(name, "NASCAR Cup"),
            "manufacturer": manufacturer,
            "teamCode": manufacturer[:3].upper(),
            "logo": _flag(),
            "primary": colors["primary"],
            "secondary": colors["secondary"],
            "colors": colors,
            "points": points,
            "wins": wins,
            "poles": poles,
            "top5": top5,
            "top10": top10,
            "stats": {"pts": points, "wins": wins, "poles": poles, "top5": top5, "top10": top10},
            "prevRank": prev.get(row_id, prev.get(name)),
        })

    playoff_sorted = sorted(rows, key=lambda r: (-r["wins"], -r["points"], r["position"]))
    for i, row in enumerate(playoff_sorted, start=1):
        row["playoffRank"] = i
        row["locked"] = row["wins"] > 0
        row["playoffPoints"] = row["wins"] * 5
        row["playoffScore"] = round(max(0, (17 - min(i, 17))) / 16 * 100, 1)
        row["score"] = round(row["points"] / max(rows[0]["points"] if rows else 1, 1) * 100, 1)
        row["legendScore"] = legend_by_name.get(row["name"], 0.0)
    return sorted(rows, key=lambda r: r["playoffRank"])


def parse_results(drivers_by_name: dict[str, dict]) -> tuple[dict | None, int]:
    parser = TableParser()
    parser.feed(_fetch_text(ESPN_RESULTS))
    races = []
    for row, links in zip(parser.rows, parser.links):
        if len(row) < 4 or not row[0]:
            continue
        race_bits = [part.strip() for part in row[1].split("|") if part.strip()]
        race_name = race_bits[0] if race_bits else row[1].strip()
        track = race_bits[1] if len(race_bits) > 1 else ""
        winner_bits = [part.strip() for part in row[2].split("|") if part.strip()]
        winner = winner_bits[0] if winner_bits else row[2].strip()
        manufacturer = next((m for m in MANUFACTURER_COLORS if m in row[2]), MANUFACTURER_BY_DRIVER.get(winner, "NASCAR"))
        race_url = next((href for href in links if "raceresults" in href), "")
        if winner and "TBD" not in winner:
            races.append({
                "date": row[0],
                "name": race_name,
                "circuit": track,
                "winner": winner,
                "manufacturer": manufacturer,
                "url": race_url if race_url.startswith("http") else f"https://www.espn.com{race_url}",
            })
    if not races:
        return None, 0
    last = races[-1]
    podium = parse_race_top5(last["url"], drivers_by_name) if last.get("url") else []
    if not podium:
        info = drivers_by_name.get(last["winner"]) or {}
        colors = _colors(last["manufacturer"])
        podium = [{
            "position": 1,
            "name": last["winner"],
            "team": info.get("team") or "NASCAR Cup",
            "manufacturer": last["manufacturer"],
            "logo": _flag(),
            "primary": colors["primary"],
        }]
    last["podium"] = podium
    return last, len(races)


def parse_race_top5(url: str, drivers_by_name: dict[str, dict]) -> list[dict]:
    if not url or "raceresults" not in url:
        return []
    parser = TableParser()
    parser.feed(_fetch_text(url, ttl_hours=24.0))
    podium = []
    for row in parser.rows:
        if len(row) < 3 or not row[0].isdigit():
            continue
        pos = int(row[0])
        if pos > 5:
            continue
        name = row[1]
        info = drivers_by_name.get(name) or {}
        manufacturer = info.get("manufacturer") or MANUFACTURER_BY_DRIVER.get(name, "NASCAR")
        colors = _colors(manufacturer)
        podium.append({
            "position": pos,
            "name": name,
            "team": info.get("team") or "NASCAR Cup",
            "manufacturer": manufacturer,
            "logo": _flag(),
            "primary": colors["primary"],
        })
    return podium


def build_legends() -> list[dict]:
    max_raw = max(_legend_raw(row) for row in NASCAR_LEGENDS_RAW)
    colors = MANUFACTURER_COLORS["NASCAR"]
    out = []
    for row in sorted(NASCAR_LEGENDS_RAW, key=_legend_raw, reverse=True):
        name, cc3, born, titles, wins, poles, active = row
        out.append({
            "id": name.lower().replace(" ", "_").replace(".", ""),
            "name": name,
            "country": cc3,
            "logo": _flag(),
            "teamCode": "USA",
            "primary": colors["primary"],
            "secondary": colors["secondary"],
            "colors": colors,
            "legendScore": round(_legend_raw(row) / max_raw * 100, 1),
            "active": active,
            "stats": {"titles": titles, "wins": wins, "poles": poles, "birth": born},
        })
    return out


def build_current_contenders(legend_threshold: float) -> list[dict]:
    max_raw = max(_legend_raw(row) for row in NASCAR_LEGENDS_RAW)
    prev = _prev_rank_map("CURRENT_CONTENDERS")
    rows = []
    for row in NASCAR_CURRENT_RAW:
        name, cc3, born, titles, wins, poles, active = row
        manufacturer = MANUFACTURER_BY_DRIVER.get(name, "NASCAR")
        colors = _colors(manufacturer)
        score = round(_legend_raw(row) / max_raw * 100, 1)
        rows.append({
            "id": _driver_id(name),
            "name": name,
            "country": cc3,
            "logo": _flag(),
            "team": TEAM_BY_DRIVER.get(name, "NASCAR Cup"),
            "manufacturer": manufacturer,
            "teamCode": manufacturer[:3].upper(),
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


def _importance(completed: int) -> float:
    if completed >= 26:
        return 9.0
    return round(min(8.8, 6.6 + completed / 26 * 2.0), 1)


def main() -> int:
    drivers = parse_standings()
    if not drivers:
        print("No NASCAR standings found", file=sys.stderr)
        return 1
    by_name = {driver["name"]: driver for driver in drivers}
    last_race, completed = parse_results(by_name)
    cutoff = next((d for d in drivers if d["playoffRank"] == 16), drivers[min(len(drivers), 16) - 1])
    legends = build_legends()
    legend_threshold = legends[9]["legendScore"] if len(legends) >= 10 else 0
    payload = {
        "UPDATED": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "SEASON": CURRENT_YEAR,
        "ROUND": completed,
        "TOTAL_ROUNDS": 36,
        "REGULAR_SEASON_ROUNDS": 26,
        "PLAYOFF_FIELD_SIZE": 16,
        "IMPORTANCE": _importance(completed),
        "LEGEND_THRESHOLD": legend_threshold,
        "PLAYOFF_CUTOFF": {"rank": 16, "driver": cutoff["name"], "points": cutoff["points"], "wins": cutoff["wins"]},
        "DRIVERS": drivers,
        "LAST_RACE": last_race,
        "CURRENT_CONTENDERS": build_current_contenders(legend_threshold),
        "LEGENDS": legends,
    }
    (ROOT / "nascar_data.js").write_text(
        "window.NASCAR_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"NASCAR data updated: {len(drivers)} drivers, playoff cutoff {cutoff['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
