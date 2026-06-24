#!/usr/bin/env python3
"""Cycling data: live Grand Tour GC + jerseys via Wikipedia, plus all-time legends."""
from __future__ import annotations
import hashlib, json, re, sys, time, urllib.request, urllib.parse, urllib.error
from html.parser import HTMLParser
from html import unescape
from datetime import datetime, timezone, date
from pathlib import Path

ROOT  = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cycling_cache"
CACHE.mkdir(exist_ok=True)

WIKI_API = "https://en.wikipedia.org/w/api.php"

# Wikipedia's API policy requires a descriptive User-Agent with contact info;
# a generic one ("Hermes/1.0") gets throttled with 429s in bursts.
USER_AGENT = "Hermes/1.0 (https://github.com/carlosrealmurcia-wq; carlosrealmurcia@gmail.com)"


def _urlopen_retry(url: str, timeout: int = 15, tries: int = 4):
    """GET with exponential backoff on 429/503 (Wikipedia throttling)."""
    last_exc: Exception | None = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            return urllib.request.urlopen(req, timeout=timeout).read()
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in (429, 503) and attempt < tries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
                continue
            raise
    if last_exc:
        raise last_exc


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

# ── Country helpers ───────────────────────────────────────────────────────────
CC3_TO_CC2: dict[str, str] = {
    "BEL": "be", "FRA": "fr", "ITA": "it", "ESP": "es", "GBR": "gb",
    "USA": "us", "NED": "nl", "SUI": "ch", "DEN": "dk", "SLO": "si",
    "COL": "co", "AUS": "au", "IRL": "ie", "SVK": "sk", "GER": "de",
    "LUX": "lu", "POR": "pt", "NOR": "no", "POL": "pl", "AUT": "at",
    "ECU": "ec", "URU": "uy", "CAN": "ca", "RUS": "ru", "KAZ": "kz",
    "LAT": "lv", "EST": "ee", "LTU": "lt", "CZE": "cz", "CRO": "hr",
    "RSA": "za", "NZL": "nz", "ARG": "ar", "BRA": "br", "UKR": "ua",
    "BLR": "by", "SVN": "si", "MEX": "mx", "ERI": "er", "JPN": "jp",
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


# ── Calendario por categorías (tiers, estilo Masters del tenis) ────────────────
# Curated 2026 calendar of the major one-day and stage races, grouped by tier.
# The winner of each is auto-extracted from the race's Wikipedia infobox (|first=),
# so finished races fill in by themselves day to day; upcoming ones stay pending.
# tier · name (ES) · exact Wikipedia title · start · end (one-day: start==end)
MAJOR_RACES: list[dict] = [
    # Grandes Vueltas (la cúspide, ya con seguimiento live aparte)
    ("Gran Vuelta", "Giro d'Italia",        "2026 Giro d'Italia",        "2026-05-08", "2026-06-01"),
    ("Gran Vuelta", "Tour de Francia",       "2026 Tour de France",       "2026-07-04", "2026-07-27"),
    ("Gran Vuelta", "Vuelta a España",       "2026 Vuelta a España",      "2026-08-15", "2026-09-06"),
    # Monumentos (los 5 clásicos de un día de máximo prestigio)
    ("Monumento", "Milán-San Remo",          "2026 Milan–San Remo",                 "2026-03-21", "2026-03-21"),
    ("Monumento", "Tour de Flandes",         "2026 Tour of Flanders (men's race)",  "2026-04-05", "2026-04-05"),
    ("Monumento", "París-Roubaix",           "2026 Paris–Roubaix",                  "2026-04-12", "2026-04-12"),
    ("Monumento", "Lieja-Bastoña-Lieja",     "2026 Liège–Bastogne–Liège",           "2026-04-26", "2026-04-26"),
    ("Monumento", "Il Lombardia",            "2026 Il Lombardia",                   "2026-10-10", "2026-10-10"),
    # Mundial (pináculo de un día, anual)
    ("Mundial", "Mundial en ruta",  "2026 UCI Road World Championships – Men's road race", "2026-09-27", "2026-09-27"),
    # Vueltas de una semana (WorldTour por etapas)
    ("Vuelta de una semana", "Paris-Niza",        "2026 Paris–Nice",             "2026-03-08", "2026-03-15"),
    ("Vuelta de una semana", "Tirreno-Adriático", "2026 Tirreno–Adriatico",      "2026-03-09", "2026-03-15"),
    ("Vuelta de una semana", "Itzulia País Vasco","2026 Tour of the Basque Country", "2026-04-06", "2026-04-11"),
    # El Dauphiné pasó a llamarse Tour Auvergne-Rhône-Alpes en 2026.
    ("Vuelta de una semana", "Tour Auvergne-Rhône-Alpes","2026 Tour Auvergne-Rhône-Alpes","2026-06-07", "2026-06-14"),
    ("Vuelta de una semana", "Tour de Suisse",    "2026 Tour de Suisse",         "2026-06-14", "2026-06-21"),
    # Clásicas grandes (un día, fuera de Monumentos)
    ("Clásica", "Strade Bianche",   "2026 Strade Bianche",          "2026-03-07", "2026-03-07"),
    ("Clásica", "Amstel Gold Race", "2026 Amstel Gold Race",        "2026-04-19", "2026-04-19"),
    ("Clásica", "Flecha Valona",    "2026 La Flèche Wallonne",      "2026-04-22", "2026-04-22"),
    ("Clásica", "San Sebastián",    "2026 Clásica de San Sebastián","2026-08-01", "2026-08-01"),
]

TIER_ORDER = ["Gran Vuelta", "Monumento", "Mundial", "JJOO", "Vuelta de una semana", "Clásica"]

# JJOO: cada 4 años (no hay en 2026). Mostramos al campeón olímpico vigente.
OLYMPIC_ROAD = {
    "name": "Remco Evenepoel", "cc3": "BEL",
    "edition": "París 2024", "next": "Los Ángeles 2028",
}

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
        d = json.loads(_urlopen_retry(url))
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
        d = json.loads(_urlopen_retry(url))
        wt = d.get("parse", {}).get("wikitext", {}).get("*", "")
        if wt:  # no cacheamos vacíos (página inexistente o 429) para poder reintentar
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
        text = _urlopen_retry(url).decode("utf-8", errors="replace")
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
        "active":      bool(birth) and birth >= 1985,
        "age":         (datetime.now(timezone.utc).year - birth) if birth else None,
        "stats":       {"tour": tour, "giro": giro, "vuelta": vuelta,
                        "monuments": monuments, "worlds": worlds, "birth": birth},
    }
    if prev_rank is not None:
        out["prevRank"] = prev_rank
    return out


# ── Palmarés auto-incremental ──────────────────────────────────────────────────
# Las tablas LEGENDS_RAW / CURRENT_RIDERS_RAW reflejan el palmarés HASTA 2025.
# Las victorias de 2026 que ya detectamos del calendario de Wikipedia (grandes
# vueltas, monumentos y mundial) se suman encima, de modo que los top-10 se
# actualizan solos sin tocar las tablas a mano. (Las vueltas de una semana y las
# clásicas no entran en el score, así que no se contabilizan.)
_GT_FIELD = {
    "Giro d'Italia":   "giro",
    "Tour de Francia": "tour",
    "Vuelta a España": "vuelta",
}


def _majors_2026_by_rider(race_calendar: list[dict]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for row in race_calendar:
        if row.get("status") != "finished" or not row.get("winner"):
            continue
        tier = row.get("tier")
        if tier == "Gran Vuelta":
            field = _GT_FIELD.get(row.get("name"))
        elif tier == "Monumento":
            field = "monuments"
        elif tier == "Mundial":
            field = "worlds"
        else:
            continue  # vueltas de una semana / clásicas no puntúan
        if not field:
            continue
        bucket = out.setdefault(
            _norm_name(row["winner"]["name"]),
            {"tour": 0, "giro": 0, "vuelta": 0, "monuments": 0, "worlds": 0},
        )
        bucket[field] += 1
    return out


def _apply_majors(row: tuple, majors: dict[str, dict[str, int]]) -> tuple:
    add = majors.get(_norm_name(row[0]))
    if not add:
        return row
    name, cc3, birth, tour, giro, vuelta, monuments, worlds = row[:8]
    return (
        name, cc3, birth,
        tour + add["tour"], giro + add["giro"], vuelta + add["vuelta"],
        monuments + add["monuments"], worlds + add["worlds"],
    )


def _season_wins_2026_by_rider(race_calendar: list[dict]) -> dict[str, list[dict]]:
    """Todas las victorias de 2026 ya disputadas, por corredor (cualquier
    categoría). Sirve para descubrir corredores y para medir la forma del año
    en las Promesas — incluso las que no puntúan para el panteón."""
    out: dict[str, list[dict]] = {}
    for row in race_calendar:
        if row.get("status") != "finished" or not row.get("winner"):
            continue
        out.setdefault(_norm_name(row["winner"]["name"]), []).append(
            {"tier": row["tier"], "name": row["name"]}
        )
    return out


def _fetch_rider_birth(name: str) -> int | None:
    """Año de nacimiento desde el infobox del corredor en Wikipedia."""
    wt = _fetch_wiki_page(name, ttl_hours=72.0)
    if not wt:
        return None
    m = re.search(r"[Bb]irth date(?:\s+and\s+age)?\s*\|\s*(?:df=\w+\s*\|\s*)?(\d{4})", wt)
    return int(m.group(1)) if m else None


def _discover_new_riders(
    race_calendar: list[dict],
    majors: dict[str, dict[str, int]],
    known_norm: set[str],
) -> list[tuple]:
    """Cualquier ganador de 2026 que no esté ya en el roster se incorpora solo:
    nombre y país salen del calendario, el año de nacimiento de su página de
    Wikipedia. Base de palmarés 0 (hasta 2025) + sus victorias panteón de 2026,
    para que emerja en Promesas sin tocar tablas a mano."""
    new_rows: list[tuple] = []
    seen = set(known_norm)
    for row in race_calendar:
        if row.get("status") != "finished" or not row.get("winner"):
            continue
        w = row["winner"]
        key = _norm_name(w["name"])
        if key in seen:
            continue
        seen.add(key)
        birth = _fetch_rider_birth(w["name"])
        time.sleep(0.3)  # cortesía con la API de Wikipedia
        add = majors.get(key, {"tour": 0, "giro": 0, "vuelta": 0, "monuments": 0, "worlds": 0})
        new_rows.append((
            w["name"], (w.get("cc3") or ""), birth,
            add["tour"], add["giro"], add["vuelta"], add["monuments"], add["worlds"],
        ))
    return new_rows


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


def build_legends(legends_rows: list[tuple], max_raw: int) -> list[dict]:
    raw_scores = [
        (_cycling_raw_score(row), row)
        for row in legends_rows
    ]
    out = []
    for raw, row in sorted(raw_scores, reverse=True):
        out.append(_cycling_player(row, max_raw))
    return out


def build_prospects(current_rows: list[tuple], max_raw: int,
                    season_wins: dict[str, list[dict]] | None = None,
                    max_age: int = 28, top_n: int = 8) -> list[dict]:
    """Jóvenes promesa del ciclismo: sub-29 que ya están dejando huella —
    palmarés acumulado camino del panteón y/o victorias en la temporada actual.
    El desempate por forma 2026 hace emerger a los recién llegados."""
    season_wins = season_wins or {}
    year = datetime.now(timezone.utc).year
    out = []
    for row in current_rows:
        birth = row[2]
        age = year - birth if birth else None
        if not age or age > max_age:
            continue
        p = _cycling_player(row, max_raw)
        s = p["stats"]
        wins2026 = season_wins.get(_norm_name(row[0]), [])
        gt = s["tour"] + s["giro"] + s["vuelta"]
        if gt >= 2:
            note = f"Ya con {gt} grandes vueltas a los {age}"
        elif gt == 1:
            note = f"Una gran vuelta a los {age}"
        elif s["monuments"] >= 1:
            note = f"{s['monuments']} monumento{'s' if s['monuments'] > 1 else ''} a los {age}"
        elif s["worlds"] >= 1:
            note = f"Arcoíris a los {age}"
        elif wins2026:
            n = len(wins2026)
            note = f"{n} victoria{'s' if n > 1 else ''} de relieve en 2026 a los {age}"
        else:
            note = f"Emerge a los {age}"
        p["note"] = note
        p["_season"] = len(wins2026)
        out.append(p)
    # Orden: palmarés panteón primero; a igualdad, la forma de 2026 desempata
    # (así un recién llegado que está ganando sube por delante de uno parado).
    out.sort(key=lambda r: (r["legendScore"], r.pop("_season")), reverse=True)
    return out[:top_n]


def build_current_riders(current_rows: list[tuple], legends_rows: list[tuple], max_raw: int, prev_rank: dict[str, int]) -> list[dict]:
    legend_scores = sorted((_cycling_player(row, max_raw)["legendScore"] for row in legends_rows), reverse=True)
    threshold = legend_scores[9] if len(legend_scores) >= 10 else 0.0
    riders = [_cycling_player(row, max_raw, prev_rank.get(row[0].lower().replace(" ", "_"))) for row in current_rows]
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
        "start":          race.get("start"),
        "end":            race.get("end"),
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


def _fetch_race_winner(wiki_title: str) -> dict | None:
    """Ganador de una carrera desde el infobox de Wikipedia (|first= / |first_nat=).
    Funciona para carreras de un día y vueltas por etapas (general). None si la
    página no existe o aún no tiene ganador (carrera futura o en curso)."""
    wt = _fetch_wiki_page(wiki_title, ttl_hours=6.0)
    if not wt:
        return None
    m = re.search(r"\|\s*first\s*=\s*\[\[(?:[^\]|]+\|)?([^\]|\n]+)\]\]", wt)
    if not m:
        return None
    name = m.group(1).strip()
    nat = re.search(r"\|\s*first_nat\s*=\s*([A-Za-z]{2,4})", wt)
    cc3 = nat.group(1).strip().upper() if nat else None
    return {"name": name, "cc3": cc3}


def _race_date_label(start: date, end: date) -> str:
    months = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
    if start == end:
        return f"{start.day} {months[start.month - 1]}"
    if start.month == end.month:
        return f"{start.day}–{end.day} {months[start.month - 1]}"
    return f"{start.day} {months[start.month - 1]}–{end.day} {months[end.month - 1]}"


def build_race_calendar() -> list[dict]:
    """Calendario por categorías con ganador auto-extraído de Wikipedia."""
    today = date.today()
    rows = []
    for tier, name, wiki, start_s, end_s in MAJOR_RACES:
        start = date.fromisoformat(start_s)
        end = date.fromisoformat(end_s)
        # Carreras futuras: no hay página/ganador todavía, evitamos el fetch.
        if today < start:
            winner = None
        else:
            winner = _fetch_race_winner(wiki)
            time.sleep(0.4)  # cortesía con la API de Wikipedia (evita 429 en ráfaga)
        if winner:
            status = "finished"
            cc3 = winner.get("cc3") or ""
            winner = {
                "name": winner["name"],
                "cc3": cc3,
                "logo": _flag(cc3) if cc3 else None,
                "color": _color(cc3) if cc3 else "#555",
            }
        elif today < start:
            status = "upcoming"
        elif today > end:
            status = "pending"  # ya disputada pero sin página/ganador todavía
        else:
            status = "ongoing"
        rows.append({
            "tier": tier, "name": name, "dateLabel": _race_date_label(start, end),
            "start": start_s, "end": end_s, "status": status, "winner": winner,
        })
    rows.sort(key=lambda r: (TIER_ORDER.index(r["tier"]), r["start"]))
    return rows


def build_olympic_road() -> dict:
    cc3 = OLYMPIC_ROAD["cc3"]
    return {
        "tier": "JJOO", "name": "Juegos Olímpicos · ruta",
        "status": "reigning",
        "winner": {"name": OLYMPIC_ROAD["name"], "cc3": cc3, "logo": _flag(cc3), "color": _color(cc3)},
        "edition": OLYMPIC_ROAD["edition"], "next": OLYMPIC_ROAD["next"],
    }


def write_data() -> None:
    out_path = ROOT / "cycling_data.js"
    prev_legends = _prev_rank_map(out_path, "CYCLING_DATA", "LEGENDS")
    prev_current = _prev_rank_map(out_path, "CYCLING_DATA", "CURRENT_RIDERS")

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # El calendario (con ganadores de 2026 de Wikipedia) se construye primero:
    # de él derivamos las victorias que se suman al palmarés base de las tablas.
    race_calendar = build_race_calendar()
    majors = _majors_2026_by_rider(race_calendar)
    season_wins = _season_wins_2026_by_rider(race_calendar)
    legends_rows = [_apply_majors(r, majors) for r in LEGENDS_RAW]
    current_rows = [_apply_majors(r, majors) for r in CURRENT_RIDERS_RAW]

    # Auto-descubrimiento: cualquier ganador de 2026 que no esté ya en el roster
    # se incorpora solo (nacimiento/país desde Wikipedia), así emerge sin editar
    # las tablas a mano.
    known = {_norm_name(r[0]) for r in legends_rows} | {_norm_name(r[0]) for r in current_rows}
    current_rows += _discover_new_riders(race_calendar, majors, known)

    max_raw = max(_cycling_raw_score(r) for r in legends_rows)

    legends = build_legends(legends_rows, max_raw)
    for lg in legends:
        lg["prevRank"] = prev_legends.get(str(lg.get("id") or lg.get("name", "")))
    current_riders = build_current_riders(current_rows, legends_rows, max_raw, prev_current)

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
        "CURRENT_PROSPECTS": build_prospects(current_rows, max_raw, season_wins),
        "CURRENT_RACE": current_race,
        "RACE_CALENDAR": race_calendar,
        "OLYMPIC_ROAD": build_olympic_road(),
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
