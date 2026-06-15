#!/usr/bin/env python3
"""Cycling data: live Grand Tour GC + jerseys via Wikipedia, plus all-time legends."""
from __future__ import annotations
import hashlib, json, re, sys, time, urllib.request, urllib.parse
from html.parser import HTMLParser
from html import unescape
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
        "cf_slug":       "giro-ditalia",
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
        "cf_slug":       "tour-de-france",
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
        "cf_slug":       "vuelta-a-espana",
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


def _fetch_wiki_page(page: str, ttl_hours: float = 2.0) -> str:
    title = urllib.parse.quote(page)
    url   = f"{WIKI_API}?action=parse&page={title}&prop=wikitext&format=json"
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
        print(f"[WARN] Wikipedia page fetch failed ({exc})", file=sys.stderr)
        return path.read_text() if path.exists() else ""


def _fetch_url(url: str, ttl_hours: float = 1.0) -> str:
    key = hashlib.md5(url.encode()).hexdigest()
    path = CACHE / key
    if path.exists():
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if age_h < ttl_hours:
            return path.read_text()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            text = r.read().decode("utf-8", errors="replace")
        path.write_text(text)
        return text
    except Exception as exc:
        print(f"[WARN] Fetch failed ({exc})", file=sys.stderr)
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


def _clean_wiki_name(cell: str) -> str:
    cell = re.sub(r"\{\{[^{}]*\}\}", "", cell)
    links = re.findall(r"\[\[(?:[^\]|]+\|)?([^\]|]+)\]\]", cell)
    name = links[-1] if links else cell
    name = re.sub(r"<[^>]+>", "", name)
    name = re.sub(r"\s*\([^)]*\)", "", name)
    return name.strip()


def _norm_name(name: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return " ".join(sorted(s.split()))


def _display_cf_name(name: str) -> str:
    parts = name.split()
    first_given = next((i for i, p in enumerate(parts) if p != p.upper()), None)
    if first_given is None or first_given == 0:
        return name.title()
    surname = " ".join(parts[:first_given]).title()
    given = " ".join(parts[first_given:])
    return f"{given} {surname}".strip()


def _split_template_args(text: str) -> list[str]:
    args: list[str] = []
    start = 0
    brace_depth = 0
    link_depth = 0
    i = 0
    while i < len(text):
        pair = text[i:i + 2]
        if pair == "{{":
            brace_depth += 1
            i += 2
            continue
        if pair == "}}" and brace_depth:
            brace_depth -= 1
            i += 2
            continue
        if pair == "[[":
            link_depth += 1
            i += 2
            continue
        if pair == "]]" and link_depth:
            link_depth -= 1
            i += 2
            continue
        if text[i] == "|" and brace_depth == 0 and link_depth == 0:
            args.append(text[start:i].strip())
            start = i + 1
        i += 1
    args.append(text[start:].strip())
    return args


def _parse_cyclingresult_rows(wt: str) -> list[dict]:
    rows: list[dict] = []
    for line in wt.splitlines():
        line = line.strip()
        if not line.startswith("{{cyclingresult|") or not line.endswith("}}"):
            continue
        raw = line[len("{{cyclingresult|"):-2]
        parts = _split_template_args(raw)
        if len(parts) < 5:
            continue
        try:
            rank = int(parts[0])
        except ValueError:
            continue
        name = _clean_wiki_name(parts[1])
        country = parts[2].strip().upper()
        team_m = re.search(r"UCI team code\|([^|}]+)", raw)
        rows.append({
            "rank":    rank,
            "name":    name,
            "country": country,
            "logo":    _flag(country) if country else "",
            "team":    team_m.group(1).strip() if team_m else "",
            "time":    parts[4].strip(),
        })
    return rows


def _parse_stage_recap_page(wt: str) -> dict[int, dict]:
    stages: dict[int, dict] = {}
    pieces = re.split(r"\n==\s*Stage\s+(\d+)\s*==", wt)
    for i in range(1, len(pieces), 2):
        stage_num = int(pieces[i])
        block = pieces[i + 1]
        stage_m = re.search(
            r"\{\{cyclingresult start\|title=Stage\s+\d+\s+Result.*?\}\}(.*?)\{\{cyclingresult end\}\}",
            block,
            re.DOTALL | re.IGNORECASE,
        )
        gc_m = re.search(
            r"\{\{cyclingresult start\|title=General classification after Stage\s+\d+.*?\}\}(.*?)\{\{cyclingresult end\}\}",
            block,
            re.DOTALL | re.IGNORECASE,
        )
        stages[stage_num] = {
            "stage_result": _parse_cyclingresult_rows(stage_m.group(1)) if stage_m else [],
            "gc_after":     _parse_cyclingresult_rows(gc_m.group(1))    if gc_m    else [],
        }
    return stages


def _fetch_stage_recaps(page: str, total_stages: int) -> dict[int, dict]:
    # Wikipedia splits Grand Tour recap pages into Stage 1-11 and Stage 12-21.
    midpoint = min(11, total_stages)
    pages = [
        f"{page}, Stage 1 to Stage {midpoint}",
        f"{page}, Stage {midpoint + 1} to Stage {total_stages}",
    ]
    recaps: dict[int, dict] = {}
    for recap_page in pages:
        wt = _fetch_wiki_page(recap_page)
        if wt:
            recaps.update(_parse_stage_recap_page(wt))
    return recaps


class _StageResultHTMLParser(HTMLParser):
    def __init__(self, replacements: dict[str, str]) -> None:
        super().__init__()
        self.replacements = replacements
        self.rows: list[list[str]] = []
        self._in_td = False
        self._row: list[str] = []
        self._cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_d = dict(attrs)
        if tag == "tr":
            self._row = []
        if tag == "td":
            self._in_td = True
            self._cell = []
        if self._in_td and tag == "template":
            template_id = attrs_d.get("id", "")
            if template_id.startswith("P:"):
                self._cell.append(self.replacements.get(template_id[2:], ""))

    def handle_data(self, data: str) -> None:
        if self._in_td:
            self._cell.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag == "td":
            self._in_td = False
            self._row.append(" ".join(x for x in self._cell if x).strip())
        if tag == "tr" and self._row:
            self.rows.append(self._row)


def _parse_cf_stage_results(html: str) -> list[dict]:
    replacements = {
        sid: unescape(re.sub(r"<[^>]+>", "", name))
        for sid, name in re.findall(r'<div hidden id="S:([0-9a-f]+)"><a [^>]+>(.*?)</a></div>', html)
    }
    start = html.find('<div class="tabcontent" id="SC"')
    if start == -1:
        return []
    end = html.find("</tbody></table>", start)
    if end == -1:
        return []
    frag = html[start:end + len("</tbody></table>")]
    parser = _StageResultHTMLParser(replacements)
    parser.feed(frag)
    rows: list[dict] = []
    for row in parser.rows:
        if len(row) < 4:
            continue
        try:
            rank = int(row[0])
        except ValueError:
            continue
        raw_name = row[2].strip()
        if not raw_name:
            continue
        rows.append({
            "rank": rank,
            "name": _display_cf_name(raw_name),
            "country": "",
            "logo": "",
            "team": "",
            "time": row[3].strip(),
        })
    return rows


def _fetch_cf_stage_results(race: dict, stage_num: int) -> list[dict]:
    slug = race.get("cf_slug")
    if not slug:
        return []
    url = f"https://cyclingfantasy.cc/en/race/{slug}/2026/results/stage/{stage_num}"
    return _parse_cf_stage_results(_fetch_url(url))


def _last_stage_result(race: dict, last_stage: dict | None, recaps: dict[int, dict], gc: list[dict]) -> list[dict]:
    if not last_stage:
        return []
    stage_num = int(last_stage.get("stage", 0) or 0)
    wiki_rows = (recaps.get(stage_num, {}) or {}).get("stage_result", [])
    full_rows = _fetch_cf_stage_results(race, stage_num)
    lookup_rows = full_rows or wiki_rows
    full_by_name = {_norm_name(r["name"]): r for r in lookup_rows}

    result: list[dict] = []
    top_rows = (wiki_rows or full_rows)[:5]
    gc_by_name = {_norm_name(r["name"]): r for r in gc[:3]}
    for row in top_rows:
        item = dict(row)
        gc_row = gc_by_name.get(_norm_name(item["name"]))
        if gc_row:
            item["gc_rank"] = gc_row.get("rank")
        result.append(item)

    seen = {_norm_name(r["name"]) for r in result}
    for gc_row in gc[:3]:
        key = _norm_name(gc_row["name"])
        if key in seen:
            continue
        stage_row = full_by_name.get(key)
        item = dict(stage_row) if stage_row else {
            "rank": None,
            "name": gc_row["name"],
            "country": gc_row.get("country", ""),
            "logo": gc_row.get("logo", ""),
            "team": gc_row.get("team", ""),
            "time": "",
        }
        item.update({
            "name":    gc_row["name"],
            "country": gc_row.get("country", item.get("country", "")),
            "logo":    gc_row.get("logo", item.get("logo", "")),
            "team":    gc_row.get("team", item.get("team", "")),
            "gc_rank": gc_row.get("rank"),
        })
        result.append(item)
    return result

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
            if entry["to"] == winner:
                entry["to"] = entry["from"]
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
    ("Jonas Vingegaard",      "DEN", 1996,   2,   1,   0,      0,       0),
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

CURRENT_RIDERS_RAW = [
    # name,                         cc3,   birth, tour,giro,vuelta,monuments,worlds
    ("Tadej Pogacar",              "SLO", 2000,   3,   1,   0,      6,       1),
    ("Primoz Roglic",              "SLO", 1989,   0,   1,   4,      1,       0),
    ("Mathieu van der Poel",       "NED", 1995,   0,   0,   0,      8,       1),
    ("Remco Evenepoel",            "BEL", 2000,   0,   0,   1,      3,       2),
    ("Jonas Vingegaard",           "DEN", 1996,   2,   1,   0,      0,       0),
    ("Egan Bernal",                "COL", 1997,   1,   1,   0,      0,       0),
    ("Richard Carapaz",            "ECU", 1993,   0,   1,   0,      0,       0),
    ("Jai Hindley",                "AUS", 1996,   0,   1,   0,      0,       0),
    ("Wout van Aert",              "BEL", 1994,   0,   0,   0,      1,       0),
    ("Mads Pedersen",              "DEN", 1995,   0,   0,   0,      0,       1),
    ("João Almeida",               "POR", 1998,   0,   0,   0,      0,       0),
    ("Sepp Kuss",                  "USA", 1994,   0,   0,   1,      0,       0),
    ("Tom Pidcock",                "GBR", 1999,   0,   0,   0,      1,       0),
    ("Filippo Ganna",              "ITA", 1996,   0,   0,   0,      0,       2),
    ("Julian Alaphilippe",         "FRA", 1992,   0,   0,   0,      1,       2),
]


def _cycling_raw_score(row: tuple) -> int:
    return (
        row[3] * W["tour"] + row[4] * W["giro"] + row[5] * W["vuelta"]
        + row[6] * W["monument"] + row[7] * W["worlds"]
    )


def _cycling_player(row: tuple, max_raw: int, prev_rank: int | None = None) -> dict:
    name, cc3, birth, tour, giro, vuelta, monuments, worlds = row[:8]
    out = {
        "id":          name.lower().replace(" ", "_"),
        "name":        name,
        "country":     cc3,
        "logo":        _flag(cc3),
        "teamCode":    cc3,
        "primary":     _color(cc3),
        "secondary":   "#FFFFFF",
        "legendScore": round(_cycling_raw_score(row) / max_raw * 100, 1),
        "active":      birth >= 1985,
        "age":         (datetime.now(timezone.utc).year - birth) if birth else None,
        "stats":       {"tour": tour, "giro": giro, "vuelta": vuelta,
                        "monuments": monuments, "worlds": worlds, "birth": birth},
    }
    if prev_rank is not None:
        out["prevRank"] = prev_rank
    return out


def _auto_current_insight(player: dict, threshold: float) -> str:
    s = player.get("stats", {})
    score = float(player.get("legendScore", 0))
    gap = max(0.0, threshold - score)
    grand_tours = int(s.get("tour", 0)) + int(s.get("giro", 0)) + int(s.get("vuelta", 0))
    monuments = int(s.get("monuments", 0))
    worlds = int(s.get("worlds", 0))

    if gap <= 5:
        return "A una gran victoria de entrar en zona top 10"
    if grand_tours >= 4:
        return "Palmarés de Grand Tour ya muy serio"
    if monuments >= 5 and worlds:
        return "Legado de clásicas y Mundial sostienen su score"
    if monuments >= 3:
        return "El camino al top histórico pasa por seguir sumando monumentos"
    if worlds >= 2:
        return "Doble arcoíris: le falta más volumen de grandes victorias"
    if grand_tours >= 2:
        return "Base de grandes vueltas; el siguiente salto pesa mucho"
    if grand_tours == 1:
        return "Una grande ya cuenta; necesita repetir para escalar"
    if worlds == 1:
        return "Un Mundial abre la puerta, falta palmarés acumulado"
    return "Necesita una victoria mayor para activar el salto histórico"


def build_legends() -> list[dict]:
    raw_scores = [
        (_cycling_raw_score(row), row)
        for row in LEGENDS_RAW
    ]
    max_raw = max(s for s, _ in raw_scores)
    out = []
    for raw, row in sorted(raw_scores, reverse=True):
        out.append(_cycling_player(row, max_raw))
    return out


def build_prospects(max_age: int = 28, top_n: int = 8) -> list[dict]:
    """Jóvenes promesa del ciclismo: sub-29 con mejor palmarés ya acumulado —
    los que han empezado fuerte camino del panteón."""
    max_raw = max(_cycling_raw_score(row) for row in LEGENDS_RAW)
    year = datetime.now(timezone.utc).year
    out = []
    for row in CURRENT_RIDERS_RAW:
        birth = row[2]
        age = year - birth if birth else None
        if not age or age > max_age:
            continue
        p = _cycling_player(row, max_raw)
        s = p["stats"]
        gt = s["tour"] + s["giro"] + s["vuelta"]
        if gt >= 2:
            note = f"Ya con {gt} grandes vueltas a los {age}"
        elif gt == 1:
            note = f"Una gran vuelta a los {age}"
        elif s["monuments"] >= 1:
            note = f"{s['monuments']} monumento{'s' if s['monuments'] > 1 else ''} a los {age}"
        elif s["worlds"] >= 1:
            note = f"Arcoíris a los {age}"
        else:
            note = f"Emerge a los {age}"
        p["note"] = note
        out.append(p)
    out.sort(key=lambda r: r["legendScore"], reverse=True)
    return out[:top_n]


def build_current_riders(prev_rank: dict[str, int]) -> list[dict]:
    max_raw = max(_cycling_raw_score(row) for row in LEGENDS_RAW)
    legend_scores = sorted((_cycling_player(row, max_raw)["legendScore"] for row in LEGENDS_RAW), reverse=True)
    threshold = legend_scores[9] if len(legend_scores) >= 10 else 0.0
    riders = [_cycling_player(row, max_raw, prev_rank.get(row[0].lower().replace(" ", "_"))) for row in CURRENT_RIDERS_RAW]
    for rider in riders:
        rider["insight"] = _auto_current_insight(rider, threshold)
    return sorted(riders, key=lambda r: r["legendScore"], reverse=True)[:10]

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

    last_stage    = next((s for s in reversed(stages) if s["completed"]), None)
    next_stage    = next((s for s in stages if not s["completed"]), None)
    caption_stage = _current_stage_from_caption(wt_gc)
    completed_stage = last_stage.get("stage", 0) if last_stage else 0
    current_stage = max(caption_stage, completed_stage, sum(1 for s in stages if s["completed"]))
    stage_recaps  = _fetch_stage_recaps(page, race["total_stages"])
    last_stage_result = _last_stage_result(race, last_stage, stage_recaps, gc)

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

    # Ganador de la general: solo cuando la carrera ha terminado (todas las etapas).
    finished = current_stage >= race["total_stages"] and next_stage is None
    gc_winner = gc[0]["name"] if (finished and gc) else None

    return {
        "name":           race["name"],
        "stage":          current_stage,
        "total_stages":   race["total_stages"],
        "jersey_primary": race["jersey_primary"],
        "jersey_name":    race["jersey_name"],
        "last_stage":     last_stage,
        "next_stage":     next_stage,
        "last_stage_result": last_stage_result,
        "finished":       finished,
        "gc_winner":      gc_winner,
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
    prev_current = _prev_rank_map(out_path, "CYCLING_DATA", "CURRENT_RIDERS")

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    legends = build_legends()
    for lg in legends:
        lg["prevRank"] = prev_legends.get(str(lg.get("id") or lg.get("name", "")))
    current_riders = build_current_riders(prev_current)

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
        "CURRENT_RIDERS": current_riders,
        "CURRENT_PROSPECTS": build_prospects(),
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
