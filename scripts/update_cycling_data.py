#!/usr/bin/env python3
"""Cycling data: live Grand Tour GC + jerseys via Wikipedia, plus all-time legends."""
from __future__ import annotations
import hashlib, json, re, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone, date
from pathlib import Path

ROOT  = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cycling_cache"
CACHE.mkdir(exist_ok=True)

WIKI_API = "https://en.wikipedia.org/w/api.php"


# ── Prev-rank helper ─────────────────────────────────────────────────────────

def _prev_rank_map(filepath: Path, js_var: str, *path: str) -> "dict[str, int]":
    import re as _re, json as _json
    try:
        text = filepath.read_text(encoding="utf-8")
        text = _re.sub(
            r"^window\." + _re.escape(js_var) + r"\s*=\s*", "", text, flags=_re.MULTILINE
        ).rstrip().rstrip(";")
        obj = _json.loads(text)
        for key in path:
            obj = obj.get(key) if isinstance(obj, dict) else None
            if obj is None:
                return {}
        if not isinstance(obj, list):
            return {}
        result: dict[str, int] = {}
        for i, item in enumerate(obj[:20]):
            k = str(item.get("id") or item.get("name", ""))
            if k:
                result[k] = i + 1
        return result
    except Exception:
        return {}

# ── Country helpers ───────────────────────────────────────────────────────────
CC3_TO_CC2: dict[str, str] = {
    "BEL": "be", "FRA": "fr", "ITA": "it", "ESP": "es", "GBR": "gb",
    "USA": "us", "NED": "nl", "SUI": "ch", "DEN": "dk", "SLO": "si",
    "COL": "co", "AUS": "au", "IRL": "ie", "SVK": "sk", "GER": "de",
    "LUX": "lu", "POR": "pt", "NOR": "no", "POL": "pl", "AUT": "at",
    "ECU": "ec", "URU": "uy", "CAN": "ca", "RUS": "ru", "KAZ": "kz",
    "LAT": "lv", "EST": "ee", "LTU": "lt", "CZE": "cz", "CRO": "hr",
    "RSA": "za", "NZL": "nz", "ARG": "ar", "BRA": "br", "UKR": "ua",
    "BLR": "by", "SVN": "si",
}
COUNTRY_COLORS: dict[str, str] = {
    "BEL": "#000000", "FRA": "#002395", "ITA": "#009246", "ESP": "#AA151B",
    "GBR": "#012169", "USA": "#B22234", "NED": "#AE1C28", "SUI": "#FF0000",
    "DEN": "#C60C30", "SLO": "#003DA5", "COL": "#FCD116", "AUS": "#00008B",
    "IRL": "#169B62", "SVK": "#0B4EA2", "GER": "#000000", "LUX": "#EF3340",
    "POR": "#006600", "NOR": "#EF2B2D", "POL": "#DC143C", "AUT": "#ED2939",
    "ECU": "#FFD100", "URU": "#75AADB", "CAN": "#FF0000",
}

def _flag(cc3: str) -> str:
    cc2 = CC3_TO_CC2.get(cc3.upper(), cc3.lower()[:2])
    return f"https://flagcdn.com/24x18/{cc2}.png"

def _color(cc3: str) -> str:
    return COUNTRY_COLORS.get(cc3.upper(), "#555555")

# ── Grand Tours calendar ──────────────────────────────────────────────────────
GRAND_TOURS: list[dict] = [
    {
        "name":          "Giro d'Italia",
        "wiki_page":     "2026 Giro d'Italia",
        "start":         "2026-05-08",
        "end":           "2026-06-01",
        "total_stages":  21,
        "jersey_primary": "#E8006D",
        "jersey_name":   "Maglia Rosa",
        "sections": {
            "stages": 2,
            "gc":     5,
            "points": 6,
            "mountains": 7,
            "young":  8,
        },
    },
    {
        "name":          "Tour de France",
        "wiki_page":     "2026 Tour de France",
        "start":         "2026-07-04",
        "end":           "2026-07-27",
        "total_stages":  21,
        "jersey_primary": "#FFD700",
        "jersey_name":   "Maillot Jaune",
        "sections": {
            "stages": 2,
            "gc":     5,
            "points": 6,
            "mountains": 7,
            "young":  8,
        },
    },
    {
        "name":          "Vuelta a España",
        "wiki_page":     "2026 Vuelta a España",
        "start":         "2026-08-15",
        "end":           "2026-09-06",
        "total_stages":  21,
        "jersey_primary": "#E8002D",
        "jersey_name":   "Maillot Rojo",
        "sections": {
            "stages": 2,
            "gc":     5,
            "points": 6,
            "mountains": 7,
            "young":  8,
        },
    },
]

def _active_race() -> dict | None:
    today = date.today().isoformat()
    for race in GRAND_TOURS:
        if race["start"] <= today <= race["end"]:
            return race
    # If none active, show the most recently completed one
    past = [r for r in GRAND_TOURS if r["end"] < today]
    return max(past, key=lambda r: r["end"]) if past else None

# ── Wikipedia helpers ─────────────────────────────────────────────────────────

def _fetch_wiki_section(page: str, section: int, ttl_hours: float = 2.0) -> str:
    title = urllib.parse.quote(page)
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

# ── Wikitext parsers ──────────────────────────────────────────────────────────

def _parse_flagathlete(block: str) -> tuple[str, str] | None:
    """Extract (display_name, cc3) from a {{Flagathlete|[[...]]|CC3}} template."""
    m = re.search(
        r'\{\{Flagathlete\|\[\[(?:[^\]|]+\|)?([^\]|]+)\]\]\|([A-Z]{2,4})\}\}',
        block,
    )
    if not m:
        return None
    name = re.sub(r'\s*\([^)]*\)', '', m.group(1)).strip()
    cc3  = m.group(2).strip()
    return name, cc3

def _current_stage_from_caption(wt: str) -> int:
    """Parse 'after stage 15' from table caption."""
    m = re.search(r'after stage\s+(\d+)', wt, re.IGNORECASE)
    return int(m.group(1)) if m else 0

def _parse_gc(wt: str) -> list[dict]:
    """Parse GC table → top 10 rider dicts with rank, name, country, team, time."""
    riders: list[dict] = []
    for block in wt.split("|-"):
        rank_m = re.search(r'!\s*scope="row"\s*\|\s*(\d+)', block)
        if not rank_m:
            continue
        fa = _parse_flagathlete(block)
        if not fa:
            continue
        name, cc3 = fa
        team_m = re.search(r'\{\{UCI team code\|([^|]+)\|', block)
        team   = team_m.group(1).strip() if team_m else ""
        # Time is the last style="text-align:right" cell
        time_m = re.search(r'style="text-align:right;?"\s*\|\s*([^\n|]+)', block)
        gap    = time_m.group(1).strip() if time_m else ""
        riders.append({
            "rank":    int(rank_m.group(1)),
            "name":    name,
            "country": cc3,
            "logo":    _flag(cc3),
            "team":    team,
            "primary": _color(cc3),
            "time":    gap,
        })
    return sorted(riders, key=lambda r: r["rank"])[:10]

def _parse_jersey_class(wt: str, score_type: str = "points") -> list[dict]:
    """Parse Points / Mountains / Young rider classification tables."""
    riders: list[dict] = []
    for block in wt.split("|-"):
        rank_m = re.search(r'!\s*scope="row"\s*\|\s*(\d+)', block)
        if not rank_m:
            continue
        fa = _parse_flagathlete(block)
        if not fa:
            continue
        name, cc3 = fa
        team_m = re.search(r'\{\{UCI team code\|([^|]+)\|', block)
        team   = team_m.group(1).strip() if team_m else ""
        val_m  = re.search(r'style="text-align:right;?"\s*\|\s*([^\n|]+)', block)
        val    = val_m.group(1).strip() if val_m else ""
        entry: dict = {
            "rank":    int(rank_m.group(1)),
            "name":    name,
            "country": cc3,
            "logo":    _flag(cc3),
            "team":    team,
            "primary": _color(cc3),
        }
        if score_type == "points":
            try:
                entry["points"] = int(val)
            except ValueError:
                entry["points"] = 0
        else:
            entry["time"] = val
        riders.append(entry)
    return sorted(riders, key=lambda r: r["rank"])[:10]

def _parse_stages(wt: str) -> list[dict]:
    """Parse stage table → all stages; completed ones have winner set."""
    stages: list[dict] = []
    for block in wt.split("|-"):
        stage_m = re.search(r'!\s*scope="row"\s*\|\s*\[\[[^\]]+?#Stage (\d+)\|\d+\]\]', block)
        if not stage_m:
            continue
        stage_num = int(stage_m.group(1))
        # Date
        date_m = re.search(r'style="text-align:right"\s*\|\s*(\d+\s+\w+)', block)
        stage_date = date_m.group(1).strip() if date_m else ""
        # Stage type
        type_m = re.search(
            r'(Flat stage|Mountain stage|Hilly stage|Individual time trial|Team time trial)',
            block,
        )
        stage_type = type_m.group(1) if type_m else "Stage"
        # Distance
        dist_m = re.search(r'\{\{convert\|(\d+)\|km\|', block)
        dist_km = int(dist_m.group(1)) if dist_m else None
        # Route: first two [[...]] links that aren't files or year pages
        links = re.findall(r'\[\[(?:([^\]|]+)\|)?([^\]|]+)\]\]', block)
        locs  = [
            (disp or page).strip()
            for page, disp in links
            if not page.startswith("File:") and not re.match(r'^\d{4}', page)
        ]
        from_loc = locs[0] if locs else ""
        to_loc   = locs[1] if len(locs) > 1 else ""
        # Winner (None for future stages)
        fa = _parse_flagathlete(block)
        entry: dict = {
            "stage":     stage_num,
            "date":      stage_date,
            "type":      stage_type,
            "dist_km":   dist_km,
            "from":      from_loc,
            "to":        to_loc,
            "completed": fa is not None,
        }
        if fa:
            winner, cc3 = fa
            entry.update({
                "winner":         winner,
                "winner_cc":      cc3,
                "winner_primary": _color(cc3),
                "winner_logo":    _flag(cc3),
            })
        stages.append(entry)
    return stages

# ── Legends ───────────────────────────────────────────────────────────────────
LEGENDS_RAW = [
    # name,                    cc3,   birth, tour,giro,vuelta,monuments,worlds
    ("Eddy Merckx",           "BEL", 1945,   5,   5,   1,     19,       3),
    ("Bernard Hinault",       "FRA", 1954,   5,   3,   2,      6,       2),
    ("Jacques Anquetil",      "FRA", 1934,   5,   2,   1,      2,       0),
    ("Miguel Indurain",       "ESP", 1964,   5,   2,   0,      1,       0),
    ("Fausto Coppi",          "ITA", 1919,   2,   5,   0,      7,       2),
    ("Chris Froome",          "GBR", 1985,   4,   1,   2,      0,       0),
    ("Alberto Contador",      "ESP", 1982,   2,   2,   3,      0,       0),
    ("Tadej Pogacar",         "SLO", 2000,   3,   1,   0,      6,       1),
    ("Jonas Vingegaard",      "DEN", 1996,   2,   0,   0,      0,       0),
    ("Primoz Roglic",         "SLO", 1989,   0,   1,   4,      1,       0),
    ("Greg LeMond",           "USA", 1961,   3,   0,   0,      1,       2),
    ("Laurent Fignon",        "FRA", 1960,   2,   2,   0,      3,       1),
    ("Vincenzo Nibali",       "ITA", 1984,   1,   2,   1,      3,       0),
    ("Felice Gimondi",        "ITA", 1942,   1,   3,   1,      4,       1),
    ("Fabian Cancellara",     "SUI", 1981,   0,   0,   0,     11,       2),
    ("Peter Sagan",           "SVK", 1990,   0,   0,   0,      7,       3),
    ("Sean Kelly",            "IRL", 1956,   0,   0,   1,      5,       0),
    ("Roger De Vlaeminck",    "BEL", 1947,   0,   0,   0,      8,       0),
    ("Remco Evenepoel",       "BEL", 2000,   0,   0,   1,      3,       2),
    ("Egan Bernal",           "COL", 1997,   1,   1,   0,      0,       0),
]

W = {"tour": 12, "giro": 9, "vuelta": 8, "monument": 4, "worlds": 4}

def build_legends() -> list[dict]:
    raw_scores = [
        (row[3]*W["tour"] + row[4]*W["giro"] + row[5]*W["vuelta"]
         + row[6]*W["monument"] + row[7]*W["worlds"], row)
        for row in LEGENDS_RAW
    ]
    max_raw = max(s for s, _ in raw_scores)
    out = []
    for raw, row in sorted(raw_scores, reverse=True):
        name, cc3, birth, tour, giro, vuelta, monuments, worlds = row
        out.append({
            "id":          name.lower().replace(" ", "_"),
            "name":        name,
            "country":     cc3,
            "logo":        _flag(cc3),
            "teamCode":    cc3,
            "primary":     _color(cc3),
            "secondary":   "#FFFFFF",
            "legendScore": round(raw / max_raw * 100, 1),
            "active":      birth >= 1985,
            "stats":       {"tour": tour, "giro": giro, "vuelta": vuelta,
                            "monuments": monuments, "worlds": worlds, "birth": birth},
        })
    return out

# ── Main ──────────────────────────────────────────────────────────────────────

def fetch_race_data(race: dict, legends: list[dict]) -> dict:
    page  = race["wiki_page"]
    secs  = race["sections"]
    print(f"[Cycling] Fetching {page}…", file=sys.stderr)

    wt_stages = _fetch_wiki_section(page, secs["stages"])
    wt_gc     = _fetch_wiki_section(page, secs["gc"])
    wt_pts    = _fetch_wiki_section(page, secs["points"])
    wt_kom    = _fetch_wiki_section(page, secs["mountains"])
    wt_young  = _fetch_wiki_section(page, secs["young"])

    stages       = _parse_stages(wt_stages)
    gc           = _parse_gc(wt_gc)
    points_class = _parse_jersey_class(wt_pts,   "points")
    kom_class    = _parse_jersey_class(wt_kom,   "points")
    young_class  = _parse_jersey_class(wt_young, "time")

    current_stage = _current_stage_from_caption(wt_gc) or sum(1 for s in stages if s["completed"])
    last_stage    = next((s for s in reversed(stages) if s["completed"]), None)
    next_stage    = next((s for s in stages if not s["completed"]), None)

    # Legend score lookup by normalised name
    legend_map = {lg["name"].lower(): lg["legendScore"] for lg in legends}
    def _legend_score(name: str) -> float:
        return legend_map.get(name.lower(), 0.0)

    for r in gc:
        r["legendScore"] = _legend_score(r["name"])
    for r in points_class:
        r["legendScore"] = _legend_score(r["name"])
    for r in kom_class:
        r["legendScore"] = _legend_score(r["name"])
    for r in young_class:
        r["legendScore"] = _legend_score(r["name"])

    return {
        "name":           race["name"],
        "stage":          current_stage,
        "total_stages":   race["total_stages"],
        "jersey_primary": race["jersey_primary"],
        "jersey_name":    race["jersey_name"],
        "last_stage":     last_stage,
        "next_stage":     next_stage,
        "gc":             gc,
        "points_leader":  points_class[0] if points_class else None,
        "kom_leader":     kom_class[0]    if kom_class    else None,
        "young_leader":   young_class[0]  if young_class  else None,
    }


def _cycling_importance(current_race: dict | None) -> float:
    if not current_race:
        return 4.0
    name = current_race.get("name", "")
    if "Tour de France" in name:
        return 10.0
    if "Giro" in name or "Vuelta" in name:
        return 9.0
    return 7.0  # Monuments, Worlds, other stage races


def write_data() -> None:
    out_path = ROOT / "cycling_data.js"
    prev_legends = _prev_rank_map(out_path, "CYCLING_DATA", "LEGENDS")

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    legends = build_legends()
    for lg in legends:
        lg["prevRank"] = prev_legends.get(str(lg.get("id") or lg.get("name", "")))

    race_meta   = _active_race()
    current_race = None
    if race_meta:
        try:
            current_race = fetch_race_data(race_meta, legends)
        except Exception as exc:
            print(f"[WARN] Race data fetch failed: {exc}", file=sys.stderr)

    importance = _cycling_importance(current_race)

    payload = {
        "UPDATED":      updated,
        "LEGENDS":      legends,
        "CURRENT_RACE": current_race,
        "IMPORTANCE":   importance,
    }

    out = ROOT / "cycling_data.js"
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"// Auto-generated {updated}\n")
        f.write(f"window.CYCLING_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n")

    print(f"Written: {out}", file=sys.stderr)
    if current_race:
        gc = current_race.get("gc", [])
        ls = current_race.get("last_stage") or {}
        print(f"  {current_race['name']} — Stage {current_race['stage']}/{current_race['total_stages']}")
        if ls:
            print(f"  Last stage: {ls.get('type','')} — winner: {ls.get('winner','')}")
        if gc:
            print(f"  GC leader: {gc[0]['name']} ({gc[0]['time']})")
    else:
        print("  No active race.")


if __name__ == "__main__":
    write_data()
