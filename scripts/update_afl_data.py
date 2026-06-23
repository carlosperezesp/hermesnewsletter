#!/usr/bin/env python3
"""AFL data: ladder, last round results, VFL/AFL legends. Uses Squiggle API."""
from __future__ import annotations
import hashlib, html, json, re, sys, time, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT  = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".afl_cache"
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
SQUIGGLE     = "https://api.squiggle.com.au"
AFL_REGULAR_ROUNDS = 23  # rounds before finals
AFL_TABLES_STATS = f"https://afltables.com/afl/stats/{CURRENT_YEAR}a.html"

# ── Team colors ───────────────────────────────────────────────────────────────
TEAM_COLORS: dict[str, dict] = {
    "Adelaide":               {"primary": "#002B5C", "secondary": "#CC2031"},
    "Brisbane Lions":         {"primary": "#7B1A4B", "secondary": "#F6AE00"},
    "Carlton":                {"primary": "#0E1E2D", "secondary": "#FFFFFF"},
    "Collingwood":            {"primary": "#000000", "secondary": "#FFFFFF"},
    "Essendon":               {"primary": "#CC2031", "secondary": "#000000"},
    "Fremantle":              {"primary": "#2A0D54", "secondary": "#FFFFFF"},
    "Geelong":                {"primary": "#002A54", "secondary": "#FFFFFF"},
    "Gold Coast":             {"primary": "#C5002F", "secondary": "#F1B500"},
    "Greater Western Sydney": {"primary": "#F57F00", "secondary": "#002040"},
    "GWS Giants":             {"primary": "#F57F00", "secondary": "#002040"},
    "Hawthorn":               {"primary": "#4D2004", "secondary": "#FFD200"},
    "Melbourne":              {"primary": "#CC2031", "secondary": "#013B9F"},
    "North Melbourne":        {"primary": "#003087", "secondary": "#FFFFFF"},
    "Port Adelaide":          {"primary": "#008AAB", "secondary": "#000000"},
    "Richmond":               {"primary": "#FFD200", "secondary": "#000000"},
    "St Kilda":               {"primary": "#ED1C2E", "secondary": "#000000"},
    "Sydney":                 {"primary": "#CC2031", "secondary": "#FFFFFF"},
    "West Coast":             {"primary": "#002B5C", "secondary": "#F5C209"},
    "Western Bulldogs":       {"primary": "#0039A6", "secondary": "#CC2031"},
}

TEAM_CODE_TO_NAME = {
    "AD": "Adelaide",
    "BL": "Brisbane Lions",
    "CA": "Carlton",
    "CW": "Collingwood",
    "ES": "Essendon",
    "FR": "Fremantle",
    "GE": "Geelong",
    "GC": "Gold Coast",
    "GW": "Greater Western Sydney",
    "HW": "Hawthorn",
    "ME": "Melbourne",
    "NM": "North Melbourne",
    "PA": "Port Adelaide",
    "RI": "Richmond",
    "SK": "St Kilda",
    "SY": "Sydney",
    "WC": "West Coast",
    "WB": "Western Bulldogs",
}

def _team_colors(name: str) -> dict:
    for key, val in TEAM_COLORS.items():
        if key.lower() in name.lower() or name.lower() in key.lower():
            return val
    return {"primary": "#555555", "secondary": "#FFFFFF"}

# ── VFL/AFL Legends ───────────────────────────────────────────────────────────
# name, team, born, flags(as player), brownlow, all_aus, active
AFL_LEGENDS_RAW = [
    ("Kevin Bartlett",      "Richmond",           1947, 5, 0, 5, False),
    ("Dick Reynolds",       "Essendon",           1915, 4, 3, 0, False),
    ("Ron Barassi",         "Melbourne/Carlton",  1936, 5, 0, 0, False),
    ("Sam Mitchell",        "Hawthorn",           1983, 4, 1, 3, False),
    ("Leigh Matthews",      "Hawthorn",           1952, 4, 0, 4, False),
    ("Jason Dunstall",      "Hawthorn",           1965, 4, 0, 3, False),
    ("Cyril Rioli",         "Hawthorn",           1990, 4, 0, 2, False),
    ("Dustin Martin",       "Richmond",           1991, 3, 1, 5, True),
    ("Gary Ablett Jr.",     "Geelong/GCS",        1984, 2, 2, 6, False),
    ("Adam Goodes",         "Sydney",             1980, 2, 2, 5, False),
    ("Wayne Carey",         "North Melbourne",    1971, 2, 0, 8, False),
    ("Nathan Buckley",      "Collingwood",        1972, 1, 1, 8, False),
    ("Patrick Dangerfield", "Geelong",            1990, 1, 1, 8, True),
    ("Bob Skilton",         "South Melbourne",    1938, 0, 3, 0, False),
    ("Gary Ablett Sr.",     "Geelong",            1961, 0, 1, 5, False),
]

AFL_CURRENT_RAW = [
    ("Dustin Martin",       "Richmond",          1991, 3, 1, 5, True),
    ("Patrick Dangerfield", "Geelong",           1990, 1, 1, 8, True),
    ("Marcus Bontempelli",  "Western Bulldogs",  1995, 0, 1, 6, True),
    ("Lachie Neale",        "Brisbane Lions",    1993, 0, 2, 3, True),
    ("Patrick Cripps",      "Carlton",           1995, 0, 2, 4, True),
    ("Nat Fyfe",            "Fremantle",         1991, 0, 2, 3, True),
    ("Jeremy Cameron",      "Geelong",           1993, 1, 0, 4, True),
    ("Nick Daicos",         "Collingwood",       2003, 1, 0, 2, True),
    ("Christian Petracca",  "Melbourne",         1996, 1, 0, 4, True),
    ("Clayton Oliver",      "Greater Western Sydney", 1997, 0, 0, 3, True),
    ("Bailey Smith",        "Geelong",           2000, 0, 0, 0, True),
    ("Zak Butters",         "Port Adelaide",     2000, 0, 0, 2, True),
    ("Harry Sheezel",       "North Melbourne",   2004, 0, 0, 1, True),
]

W_LEGEND = {"flags": 8.0, "brownlow": 5.0, "all_aus": 1.5}

def _raw_score(row: tuple) -> float:
    *_, flags, brownlow, all_aus, _active = row
    return flags * W_LEGEND["flags"] + brownlow * W_LEGEND["brownlow"] + all_aus * W_LEGEND["all_aus"]

def _person_id(name: str) -> str:
    return name.lower().replace(" ", "_").replace(".","")

def build_legends() -> list[dict]:
    scored  = [(_raw_score(r), r) for r in AFL_LEGENDS_RAW]
    max_raw = max(s for s, _ in scored)
    out = []
    for raw, row in sorted(scored, reverse=True):
        name, team, born, flags, brownlow, all_aus, active = row
        colors = _team_colors(team.split("/")[0])
        out.append({
            "id":          _person_id(name),
            "name":        name,
            "country":     "AUS",
            "logo":        "https://flagcdn.com/24x18/au.png",
            "teamCode":    team.split("/")[0],
            "primary":     colors["primary"],
            "secondary":   colors["secondary"],
            "legendScore": round(raw / max_raw * 100, 1),
            "active":      active,
            "stats":       {"flags": flags, "brownlow": brownlow, "all_aus": all_aus, "birth": born},
        })
    return out

def build_current_contenders(legend_threshold: float) -> list[dict]:
    max_raw = max(_raw_score(row) for row in AFL_LEGENDS_RAW)
    prev = _prev_rank_map(ROOT / "afl_data.js", "AFL_DATA", "CURRENT_CONTENDERS")
    rows = []
    for row in AFL_CURRENT_RAW:
        name, team, born, flags, brownlow, all_aus, active = row
        colors = _team_colors(team.split("/")[0])
        score = round(_raw_score(row) / max_raw * 100, 1)
        rows.append({
            "id": _person_id(name),
            "name": name,
            "country": "AUS",
            "logo": "https://flagcdn.com/24x18/au.png",
            "team": team,
            "teamCode": team.split("/")[0],
            "primary": colors["primary"],
            "secondary": colors["secondary"],
            "colors": colors,
            "legendScore": score,
            "gapToTop10": round(max(0, legend_threshold - score), 1),
            "active": active,
            "prevRank": prev.get(_person_id(name), prev.get(name)),
            "stats": {"flags": flags, "brownlow": brownlow, "all_aus": all_aus, "birth": born},
        })
    return sorted(rows, key=lambda x: x["legendScore"], reverse=True)[:10]

# ── API helpers ───────────────────────────────────────────────────────────────

def _fetch(url: str, ttl_hours: float = 1.0) -> dict | None:
    key  = hashlib.md5(url.encode()).hexdigest()
    path = CACHE / key
    if path.exists():
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if age_h < ttl_hours:
            return json.loads(path.read_text())
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        path.write_text(json.dumps(data))
        return data
    except Exception as exc:
        print(f"[WARN] Squiggle fetch failed ({exc}): {url}", file=sys.stderr)
        if path.exists():
            return json.loads(path.read_text())
        return None

def _fetch_text(url: str, ttl_hours: float = 6.0) -> str:
    key = hashlib.md5(url.encode()).hexdigest()
    path = CACHE / f"{key}.html"
    if path.exists():
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if age_h < ttl_hours:
            return path.read_text(encoding="utf-8", errors="ignore")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            text = r.read().decode("utf-8", errors="ignore")
        path.write_text(text, encoding="utf-8")
        return text
    except Exception as exc:
        print(f"[WARN] AFL Tables fetch failed ({exc}): {url}", file=sys.stderr)
        return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""

class _StatsTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.headers: list[str] = []
        self.rows: list[list[str]] = []
        self._in_first_table = False
        self._table_depth = 0
        self._in_tr = False
        self._in_cell = False
        self._cell: list[str] = []
        self._row: list[str] = []
        self._is_header_row = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "table" and not self._in_first_table and "sortable" in (attrs_dict.get("class") or ""):
            self._in_first_table = True
            self._table_depth = 1
        elif tag == "table" and self._in_first_table:
            self._table_depth += 1
        if not self._in_first_table:
            return
        if tag == "tr":
            self._in_tr = True
            self._row = []
            self._is_header_row = False
        elif self._in_tr and tag in {"td", "th"}:
            self._in_cell = True
            self._cell = []
            if tag == "th":
                self._is_header_row = True

    def handle_endtag(self, tag: str) -> None:
        if not self._in_first_table:
            return
        if tag in {"td", "th"} and self._in_cell:
            value = html.unescape(" ".join("".join(self._cell).split())).replace("\xa0", " ").strip()
            self._row.append(value)
            self._in_cell = False
        elif tag == "tr" and self._in_tr:
            if self._row:
                if self._is_header_row and not self.headers:
                    self.headers = self._row
                elif not self._is_header_row:
                    self.rows.append(self._row)
            self._in_tr = False
        elif tag == "table":
            self._table_depth -= 1
            if self._table_depth <= 0:
                self._in_first_table = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell.append(data)

def _name_from_afl_tables(value: str) -> str:
    if "," not in value:
        return value.strip()
    last, first = [part.strip() for part in value.split(",", 1)]
    return f"{first} {last}".strip()

def _num(value: str) -> float:
    value = value.strip()
    if not value or value == "&nbsp;":
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0

# ── Data builders ─────────────────────────────────────────────────────────────

def _ladder(year: int) -> list[dict]:
    data = _fetch(f"{SQUIGGLE}/?q=standings;year={year}", ttl_hours=1.0)
    if not data:
        return []
    out = []
    for s in data.get("standings", []):
        name   = s.get("name", "")
        colors = _team_colors(name)
        pct    = float(s.get("percentage", 0))
        out.append({
            "rank":       int(s.get("rank", 0)),
            "name":       name,
            "wins":       int(s.get("wins", 0)),
            "losses":     int(s.get("losses", 0)),
            "draws":      int(s.get("draws", 0)),
            "pts":        int(s.get("pts", 0)),
            "percentage": round(pct, 1),
            "primary":    colors["primary"],
            "secondary":  colors["secondary"],
        })
    out.sort(key=lambda x: x["rank"])
    return out[:18]

def _last_round(year: int) -> tuple[int, list[dict]]:
    data = _fetch(f"{SQUIGGLE}/?q=games;complete=100;year={year}", ttl_hours=1.0)
    if not data:
        return 0, []
    games = data.get("games", [])
    if not games:
        return 0, []
    last_round = max(g.get("round", 0) for g in games)
    round_games = [g for g in games if g.get("round") == last_round]
    out = []
    for g in sorted(round_games, key=lambda x: x.get("unixtime", 0)):
        hname  = g.get("hteam", "")
        aname  = g.get("ateam", "")
        winner = g.get("winner", "")
        out.append({
            "hteam":    hname,
            "hscore":   int(g.get("hscore", 0)),
            "ateam":    aname,
            "ascore":   int(g.get("ascore", 0)),
            "winner":   winner,
            "date":     g.get("date", "")[:10],
            "hprimary": _team_colors(hname)["primary"],
            "aprimary": _team_colors(aname)["primary"],
        })
    return last_round, out

def _player_performers(prev: dict[str, int]) -> list[dict]:
    text = _fetch_text(AFL_TABLES_STATS, ttl_hours=6.0)
    if not text:
        return []
    parser = _StatsTableParser()
    parser.feed(text)
    headers = parser.headers
    if not headers:
        return []
    idx = {name: i for i, name in enumerate(headers)}
    required = {"Player", "TM", "GM", "DI", "GL", "TK", "CL", "CP", "MK"}
    if not required.issubset(idx):
        return []

    rows: list[dict] = []
    raw_scores: list[float] = []
    max_legend_raw = max(_raw_score(row) for row in AFL_LEGENDS_RAW)
    legend_by_name = {row[0]: round(_raw_score(row) / max_legend_raw * 100, 1) for row in AFL_CURRENT_RAW}
    for row in parser.rows:
        if len(row) < len(headers):
            continue
        name = _name_from_afl_tables(row[idx["Player"]])
        team_code = row[idx["TM"]]
        team = TEAM_CODE_TO_NAME.get(team_code, team_code)
        colors = _team_colors(team)
        gm = int(_num(row[idx["GM"]]))
        if gm <= 0:
            continue
        stats = {key: _num(row[idx[key]]) for key in headers if key in idx and idx[key] < len(row)}
        raw = (
            stats.get("DI", 0) * 0.18
            + stats.get("GL", 0) * 3.8
            + stats.get("TK", 0) * 1.25
            + stats.get("CL", 0) * 1.45
            + stats.get("CP", 0) * 0.85
            + stats.get("MK", 0) * 0.55
            + stats.get("HO", 0) * 0.12
            + stats.get("GA", 0) * 2.2
            + stats.get("MI", 0) * 1.1
            + stats.get("IF", 0) * 0.5
            - stats.get("CG", 0) * 0.35
        )
        if gm < 4:
            raw *= 0.72
        row_id = name.lower().replace(" ", "_").replace(".", "")
        rows.append({
            "id": row_id,
            "name": name,
            "country": "AUS",
            "logo": "https://flagcdn.com/24x18/au.png",
            "team": team,
            "teamCode": team_code,
            "primary": colors["primary"],
            "secondary": colors["secondary"],
            "colors": colors,
            "rawScore": raw,
            "prevRank": prev.get(row_id, prev.get(name)),
            "stats": {
                "games": gm,
                "disposals": int(stats.get("DI", 0)),
                "goals": int(stats.get("GL", 0)),
                "tackles": int(stats.get("TK", 0)),
                "clearances": int(stats.get("CL", 0)),
                "contested": int(stats.get("CP", 0)),
                "marks": int(stats.get("MK", 0)),
                "hitouts": int(stats.get("HO", 0)),
            },
        })
        raw_scores.append(raw)

    if not rows:
        return []
    max_raw = max(raw_scores) or 1.0
    rows.sort(key=lambda x: x["rawScore"], reverse=True)
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
        row["score"] = round(row["rawScore"] / max_raw * 100, 1)
        row["legendScore"] = legend_by_name.get(row["name"], 0.0)
        row.pop("rawScore", None)
    return rows[:30]

def _importance(round_num: int) -> float:
    if round_num >= AFL_REGULAR_ROUNDS + 3:
        return 10.0  # Grand Final week
    if round_num >= AFL_REGULAR_ROUNDS + 1:
        return 9.5   # Finals
    if round_num >= AFL_REGULAR_ROUNDS:
        return 9.0   # Last home-and-away round
    progress = round_num / AFL_REGULAR_ROUNDS
    return round(7.0 + progress * 1.5, 1)

# ── Main ──────────────────────────────────────────────────────────────────────

def write_data() -> None:
    out_path = ROOT / "afl_data.js"
    prev_ladder  = _prev_rank_map(out_path, "AFL_DATA", "LADDER")
    prev_players = _prev_rank_map(out_path, "AFL_DATA", "PERFORMERS")
    prev_legends = _prev_rank_map(out_path, "AFL_DATA", "LEGENDS")

    updated  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    year     = CURRENT_YEAR
    print(f"[AFL] Fetching {year} season data…", file=sys.stderr)

    legends              = build_legends()
    legend_threshold     = legends[9]["legendScore"] if len(legends) >= 10 else 0
    ladder               = _ladder(year)
    last_round, results  = _last_round(year)
    performers           = _player_performers(prev_players)
    current_contenders   = build_current_contenders(legend_threshold)
    importance           = _importance(last_round)

    # ── Asignar prevRank ──────────────────────────────────────────────────────
    for t in ladder[:8]:
        t["prevRank"] = prev_ladder.get(str(t.get("name", "")))
    for lg in legends:
        lg["prevRank"] = prev_legends.get(str(lg.get("id") or lg.get("name", "")))

    payload = {
        "UPDATED":    updated,
        "SEASON":     str(year),
        "ROUND":      last_round,
        "IMPORTANCE": importance,
        "LEGEND_THRESHOLD": legend_threshold,
        "LADDER":     ladder,
        "PERFORMERS": performers,
        "LAST_ROUND": results,
        "CURRENT_CONTENDERS": current_contenders,
        "LEGENDS":    legends,
    }

    out = ROOT / "afl_data.js"
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"// Auto-generated {updated}\n")
        f.write(f"window.AFL_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n")

    print(f"Written: {out}", file=sys.stderr)
    print(f"  Round {last_round} · importance={importance}")
    if ladder:
        print(f"  Leader: {ladder[0]['name']} (W{ladder[0]['wins']} L{ladder[0]['losses']})")
    if legends:
        print(f"  Top legend: {legends[0]['name']} ({legends[0]['legendScore']})")
    if performers:
        print(f"  Top performer: {performers[0]['name']} ({performers[0]['score']})")


if __name__ == "__main__":
    write_data()
