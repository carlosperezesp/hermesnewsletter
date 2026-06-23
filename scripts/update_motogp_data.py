#!/usr/bin/env python3
"""MotoGP data: rider standings, last GP, legends. Uses Wikipedia API for live data."""
from __future__ import annotations
import hashlib, json, re, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT  = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".motogp_cache"
CACHE.mkdir(exist_ok=True)

CURRENT_YEAR = datetime.now(timezone.utc).year


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

WIKI_API = "https://en.wikipedia.org/w/api.php"

# ── Bike / manufacturer colors ────────────────────────────────────────────────
BIKE_COLORS: dict[str, dict] = {
    "Aprilia": {"primary": "#003366", "secondary": "#E8002D"},
    "Ducati":  {"primary": "#CC0000", "secondary": "#FFD200"},
    "KTM":     {"primary": "#E86825", "secondary": "#000000"},
    "Yamaha":  {"primary": "#003399", "secondary": "#FFFFFF"},
    "Honda":   {"primary": "#CC0000", "secondary": "#FFFFFF"},
}

def _bike_colors(bike: str) -> dict:
    for key, val in BIKE_COLORS.items():
        if key.lower() in bike.lower():
            return val
    return {"primary": "#555555", "secondary": "#FFFFFF"}

# ── Country mapping ───────────────────────────────────────────────────────────
WIKI_CC_TO_CC2: dict[str, str] = {
    "ITA": "it", "ESP": "es", "SPA": "es", "JPN": "jp", "JAP": "jp",
    "AUS": "au", "FRA": "fr", "GER": "de", "BRA": "br", "ZAF": "za",
    "RSA": "za", "TUR": "tr", "GBR": "gb", "CHN": "cn", "FIN": "fi",
    "NED": "nl", "ARG": "ar", "POR": "pt", "USA": "us", "MAL": "my",
    "INA": "id", "THA": "th", "QAT": "qa",
}

def _flag(cc: str) -> str:
    cc2 = WIKI_CC_TO_CC2.get(cc.upper(), cc.lower()[:2])
    return f"https://flagcdn.com/24x18/{cc2}.png"

# ── MotoGP/500cc all-time legends ─────────────────────────────────────────────
# name, cc3, born, premier-class titles, premier-class wins, premier-class poles, active
MOTOGP_LEGENDS_RAW = [
    ("Giacomo Agostini",  "ITA", 1942, 8,  68, 54, False),  # 8 × 500cc
    ("Valentino Rossi",   "ITA", 1979, 7,  89, 65, False),  # 7 × MotoGP/500cc
    ("Marc Márquez",      "ESP", 1993, 6,  65, 63, True),   # through 2024
    ("Mick Doohan",       "AUS", 1965, 5,  54, 58, False),
    ("Eddie Lawson",      "USA", 1958, 4,  31, 18, False),
    ("Kenny Roberts",     "USA", 1951, 3,  24, 22, False),
    ("Wayne Rainey",      "USA", 1960, 3,  24, 19, False),
    ("Jorge Lorenzo",     "ESP", 1987, 3,  47, 65, False),
    ("Casey Stoner",      "AUS", 1985, 2,  45, 56, False),
    ("Francesco Bagnaia", "ITA", 1997, 2,  31, 26, True),   # through 2024
    ("Kevin Schwantz",    "USA", 1964, 1,  25, 25, False),
    ("Jorge Martín",      "ESP", 1988, 1,  14, 20, True),   # 2024 champion
]

W_LEGEND = {"titles": 10.0, "wins": 0.20, "poles": 0.10}

def _raw_score(row: tuple) -> float:
    *_, titles, wins, poles, _active = row
    return titles * W_LEGEND["titles"] + wins * W_LEGEND["wins"] + poles * W_LEGEND["poles"]

def build_legends() -> list[dict]:
    scored  = [(_raw_score(r), r) for r in MOTOGP_LEGENDS_RAW]
    max_raw = max(s for s, _ in scored)
    out = []
    for raw, row in sorted(scored, reverse=True):
        name, cc3, born, titles, wins, poles, active = row
        colors = _bike_colors("")   # country-neutral; use fallback
        cc3_upper = cc3.upper()
        out.append({
            "id":          name.lower().replace(" ", "_").replace("á","a").replace("é","e").replace("ó","o").replace("ú","u"),
            "name":        name,
            "country":     cc3_upper,
            "logo":        _flag(cc3_upper),
            "teamCode":    cc3_upper,
            "primary":     "#C80000",
            "secondary":   "#FFFFFF",
            "legendScore": round(raw / max_raw * 100, 1),
            "active":      active,
            "stats":       {"titles": titles, "wins": wins, "poles": poles, "birth": born},
        })
    return out

# ── Wikipedia helpers ─────────────────────────────────────────────────────────

def _fetch_wiki_section(year: int, section: int, ttl_hours: float = 4.0) -> str:
    title = urllib.parse.quote(f"{year} MotoGP World Championship")
    url   = f"{WIKI_API}?action=parse&page={title}&prop=wikitext&section={section}&format=json"
    key   = hashlib.md5(url.encode()).hexdigest()
    path  = CACHE / key
    if path.exists():
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if age_h < ttl_hours:
            return path.read_text()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
        wt = d.get("parse", {}).get("wikitext", {}).get("*", "")
        path.write_text(wt)
        return wt
    except Exception as exc:
        print(f"[WARN] Wikipedia fetch failed ({exc})", file=sys.stderr)
        return path.read_text() if path.exists() else ""

def _wiki_sections(year: int) -> dict[str, int]:
    title = urllib.parse.quote(f"{year} MotoGP World Championship")
    url   = f"{WIKI_API}?action=parse&page={title}&prop=sections&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
        return {s["line"]: int(s["index"]) for s in d.get("parse", {}).get("sections", [])}
    except Exception:
        return {}

# ── Standings parser ──────────────────────────────────────────────────────────

def _parse_rider_standings(wt: str) -> tuple[list[dict], int, int]:
    """Returns (riders, completed_rounds, total_rounds)."""
    tables = wt.split("{|")
    rider_table = next(
        (t for t in tables if "Pos." in t and "Rider" in t and "Bike" in t), ""
    )
    if not rider_table:
        return [], 0, 0

    # Count total race columns: headers are [[2026 <name>|ABB]] links
    header = rider_table.split("|-")[0] if "|-" in rider_table else ""
    gp_cols = re.findall(r"\[\[2\d{3}[^\]|]+\|([A-Z]{2,4})\]\]", header)
    total_rounds = len(gp_cols)

    rows = rider_table.split("|-")
    riders: list[dict] = []
    for row in rows:
        pos_m = re.search(r"^\s*!\s*(\d+)\s*$", row, re.MULTILINE)
        if not pos_m:
            continue
        pos = int(pos_m.group(1))

        rider_m = re.search(r"\{\{flagicon\|([^}]+)\}\}\s*\[\[([^\]|]+)", row)
        if not rider_m:
            continue
        cc   = rider_m.group(1).strip()
        name = re.sub(r"\s*\([^)]*\)", "", rider_m.group(2)).strip()

        bike_m = re.search(r"\|\s*\[\[([^\]|]+)", row.split("\n", 3)[-1] if "\n" in row else "")
        bike   = ""
        for bm in re.finditer(r"\| \[\[([^\]|]+)[\]|]", row):
            candidate = bm.group(1).strip()
            if candidate in BIKE_COLORS:
                bike = candidate
                break

        pts_all = re.findall(r"^\s*!\s*(\d+)\s*$", row, re.MULTILINE)
        pts     = int(pts_all[-1]) if pts_all else 0

        colors = _bike_colors(bike)
        riders.append({
            "position": pos,
            "name":     name,
            "country":  cc.upper(),
            "bike":     bike,
            "logo":     _flag(cc),
            "primary":  colors["primary"],
            "secondary":colors["secondary"],
            "points":   float(pts),
            "score":    0.0,
        })

    # Determine completed rounds from top rider's result cells
    completed = 0
    if rows and total_rounds > 0:
        top_row = next((r for r in rows if re.search(r"^\s*!\s*1\s*$", r, re.MULTILINE)), "")
        if top_row:
            cells = re.findall(r"bgcolor=[\"#][^|]*\|\s*[^\n|]+", top_row)
            completed = len(cells)

    riders = [r for r in riders if r["position"] >= 1]
    riders.sort(key=lambda x: x["position"])
    max_season_pts = total_rounds * 25
    for r in riders:
        r["score"]    = round(r["points"] / max(max_season_pts, 1) * 100, 1)
        r["stats"]    = {"pts": r["points"]}
        r["seasonPct"] = r["score"]

    return riders, completed, total_rounds, max_season_pts

# ── Last race parser ──────────────────────────────────────────────────────────

def _fetch_race_podium(gp_name: str, year: int) -> list[dict]:
    """Fetch P1–P3 from the individual Wikipedia race article (cached 24h)."""
    slug  = f"{year} {gp_name}"
    title = urllib.parse.quote(slug)
    url   = f"{WIKI_API}?action=parse&page={title}&prop=wikitext&format=json"
    key   = hashlib.md5(url.encode()).hexdigest()
    path  = CACHE / key
    if path.exists():
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if age_h < 24.0:
            wt = path.read_text()
        else:
            wt = ""
    else:
        wt = ""
    if not wt:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.loads(r.read())
            wt = d.get("parse", {}).get("wikitext", {}).get("*", "")
            path.write_text(wt)
        except Exception as exc:
            print(f"[WARN] race article fetch failed ({exc})", file=sys.stderr)
            return []
    # Wikipedia race classification rows look like: "! 1\n| ... {{flagicon|SPA}} '''[[Rider]]'''\n..."
    podium: list[dict] = []
    seen_pos: set[int] = set()
    for row in re.split(r"\n\s*\|-", wt):
        pos_m = re.search(r"^\s*!\s*([123])\s*$", row, re.MULTILINE)
        if not pos_m:
            continue
        pos = int(pos_m.group(1))
        if pos in seen_pos:
            continue
        icons = re.findall(r"\{\{flagicon\|([^}]+)\}\}[^[]*\[\[([^\]|]+)", row)
        if not icons:
            continue
        cc   = icons[0][0].strip().upper()
        name = re.sub(r"\s*\([^)]*\)", "", icons[0][1]).strip()
        if not name or "Grand Prix" in name or "Racing" in name:
            continue
        bike = ""
        for bm in re.finditer(r"\[\[([^\]|]+)[\]|]", row):
            if bm.group(1).strip() in BIKE_COLORS:
                bike = bm.group(1).strip()
                break
        colors = _bike_colors(bike)
        podium.append({
            "pos":     pos,
            "name":    name,
            "country": cc,
            "logo":    _flag(cc),
            "bike":    bike,
            "primary": colors["primary"],
        })
        seen_pos.add(pos)
        if len(seen_pos) == 3:
            break
    podium.sort(key=lambda x: x["pos"])
    return podium

def _parse_last_race(wt: str) -> dict | None:
    rows = wt.split("|-")
    races: list[dict] = []
    for row in rows:
        rnd_m = re.search(r"^\s*!\s*(\d+)\s*$", row, re.MULTILINE)
        if not rnd_m:
            continue
        rnd = int(rnd_m.group(1))
        # GP name — first [[...Grand Prix...]] link text
        gp_m = re.search(r"\{\{flagicon\|[^}]+\}\}\s*\[\[([^\]|]+Grand Prix[^\]|]*)", row)
        if not gp_m:
            continue
        gp_name = gp_m.group(1).strip()
        # Winning rider (3rd flagicon occurrence = winning rider column)
        flagicons = re.findall(r"\{\{flagicon\|([^}]+)\}\}\s*\[\[([^\]|]+)\]\]", row)
        if len(flagicons) < 3:
            continue
        winner_cc   = flagicons[2][0].strip()
        winner_name = re.sub(r"\s*\([^)]*\)", "", flagicons[2][1]).strip()
        # Constructor (last [[Aprilia/Ducati/KTM/...]] link)
        ctor_m = re.findall(r"\[\[(" + "|".join(BIKE_COLORS.keys()) + r")\]\]", row)
        bike   = ctor_m[0] if ctor_m else ""
        colors = _bike_colors(bike)
        races.append({
            "round":   rnd,
            "name":    gp_name,
            "winner":  winner_name,
            "country": winner_cc.upper(),
            "bike":    bike,
            "primary": colors["primary"],
        })
    if not races:
        return None
    last = races[-1]
    # Attempt to enrich with full podium from individual race article
    podium = _fetch_race_podium(last["name"], CURRENT_YEAR)
    if podium:
        last["podium"] = podium
    else:
        last["podium"] = [{
            "pos": 1, "name": last["winner"], "country": last["country"],
            "logo": _flag(last["country"]), "bike": last["bike"], "primary": last["primary"],
        }]
    return last

# ── Importance ────────────────────────────────────────────────────────────────

def _importance(riders: list[dict], completed: int, total: int) -> float:
    if total == 0:
        return 7.0
    progress = completed / total
    base     = 7.0 + progress * 2.0
    if len(riders) >= 2:
        leader    = riders[0]["points"]
        remaining = (total - completed) * 25
        gap       = leader - riders[1]["points"]
        if gap > remaining:
            return 7.0
        contenders = sum(1 for r in riders if leader - r["points"] <= remaining)
        if completed >= total - 1 and contenders >= 2:
            return 10.0
        if contenders >= 2:
            base = min(10.0, base + contenders * 0.2)
    return round(min(10.0, base), 1)

# ── Main ──────────────────────────────────────────────────────────────────────

MOTOGP_RIDER_BIRTH = {
    "Marc Márquez": 1993, "Álex Márquez": 1996, "Francesco Bagnaia": 1997,
    "Jorge Martín": 1998, "Marco Bezzecchi": 1998, "Fabio Di Giannantonio": 1998,
    "Pedro Acosta": 2004, "Fermín Aldeguer": 2005, "Ai Ogura": 2001,
    "Raúl Fernández": 2000, "Fabio Quartararo": 1999, "Brad Binder": 1995,
    "Maverick Viñales": 1995, "Enea Bastianini": 1997, "Franco Morbidelli": 1994,
    "Joan Mir": 1997, "Johann Zarco": 1990, "Alex Rins": 1995, "Jack Miller": 1995,
}


def _motogp_prospects(riders: list[dict], max_age: int = 25, top_n: int = 6) -> list[dict]:
    """Jóvenes promesa MotoGP: pilotos sub-26 con mejor marcha en el campeonato."""
    out = []
    for r in riders:
        age = r.get("age")
        if not age or age > max_age:
            continue
        pos = r.get("position", 99)
        note = (f"Líder del Mundial a los {age}" if pos == 1
                else f"Top {pos} a los {age}" if pos <= 5
                else f"Irrumpe a los {age} (P{pos})")
        out.append({
            "name": r["name"], "country": r.get("country"), "logo": r.get("logo"),
            "primary": r.get("primary"), "secondary": r.get("secondary"),
            "bike": r.get("bike"), "score": r.get("score"), "position": pos, "age": age, "note": note,
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:top_n]


def build_legend_chase(legends: list[dict], top_n: int = 8) -> list[dict]:
    """Candidato a leyenda: pilotos en activo por trayectoria histórica y distancia al top-10."""
    ranked = sorted(legends, key=lambda x: x["legendScore"], reverse=True)
    threshold = ranked[9]["legendScore"] if len(ranked) >= 10 else 0.0
    chase = []
    for p in ranked:
        if not p.get("active"):
            continue
        s = p.get("stats", {})
        gap = round(max(0.0, threshold - p["legendScore"]), 1)
        tt, ww = s.get('titles', 0), s.get('wins', 0)
        palmares = f"{tt} título{'' if tt == 1 else 's'} · {ww} victoria{'' if ww == 1 else 's'}"
        note = (f"Ya en zona top 10 histórico · {palmares}" if p["legendScore"] >= threshold
                else f"A {gap} del top 10 histórico · {palmares}")
        chase.append({**p, "gap": gap, "threshold": round(threshold, 1), "note": note})
    return chase[:top_n]


def write_data() -> None:
    out_path = ROOT / "motogp_data.js"
    prev_riders  = _prev_rank_map(out_path, "MOTOGP_DATA", "RIDERS")
    prev_legends = _prev_rank_map(out_path, "MOTOGP_DATA", "LEGENDS")

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    year    = CURRENT_YEAR
    print(f"[MotoGP] Fetching {year} season data…", file=sys.stderr)

    sections = _wiki_sections(year)
    riders_sec   = sections.get("Riders' standings",   sections.get("Riders' standings",   11))
    gp_sec       = sections.get("Grands Prix",         10)

    wt_riders = _fetch_wiki_section(year, riders_sec)
    wt_gp     = _fetch_wiki_section(year, gp_sec)

    legends              = build_legends()
    riders, completed, total, max_season_pts = _parse_rider_standings(wt_riders)
    last_race  = _parse_last_race(wt_gp)
    importance = _importance(riders, completed, total)

    # ── Asignar prevRank ──────────────────────────────────────────────────────
    for r in riders[:10]:
        r["prevRank"] = prev_riders.get(str(r.get("name", "")))
    for lg in legends:
        lg["prevRank"] = prev_legends.get(str(lg.get("id") or lg.get("name", "")))

    for r in riders:
        b = MOTOGP_RIDER_BIRTH.get(r["name"])
        r["age"] = (CURRENT_YEAR - b) if b else None
    prospects = _motogp_prospects(riders)

    payload = {
        "UPDATED":        updated,
        "SEASON":         str(year),
        "ROUND":          completed,
        "TOTAL_ROUNDS":   total,
        "MAX_SEASON_PTS": max_season_pts,
        "IMPORTANCE":     importance,
        "RIDERS":         riders[:10],
        "PROSPECTS":      prospects,
        "LEGEND_CHASE":   build_legend_chase(legends),
        "LAST_RACE":      last_race,
        "LEGENDS":        legends,
    }

    out = ROOT / "motogp_data.js"
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"// Auto-generated {updated}\n")
        f.write(f"window.MOTOGP_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n")

    print(f"Written: {out}", file=sys.stderr)
    print(f"  Round {completed}/{total} · importance={importance}")
    if riders:
        print(f"  Leader: {riders[0]['name']} ({riders[0]['points']} pts)")
    if last_race:
        print(f"  Last race: {last_race['name']} → {last_race['winner']}")


if __name__ == "__main__":
    write_data()
