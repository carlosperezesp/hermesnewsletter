#!/usr/bin/env python3
"""F1 championship data: standings, last race, legends. Uses ESPN API."""
from __future__ import annotations
import hashlib, json, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT  = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".f1_cache"
CACHE.mkdir(exist_ok=True)

CURRENT_YEAR = datetime.now(timezone.utc).year


# ── Prev-rank helper ─────────────────────────────────────────────────────────

def _prev_rank_map(filepath: Path, js_var: str, *path: str) -> "dict[str, int]":
    import re as _re, json as _json
    try:
        text = filepath.read_text(encoding="utf-8")
        text = _re.sub(r"^\s*//[^\n]*\n?", "", text, flags=_re.MULTILINE)
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

ESPN_STANDINGS   = "https://site.api.espn.com/apis/v2/sports/racing/f1/standings"
ESPN_SCOREBOARD  = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard"
ESPN_SCHEDULE    = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/schedule"

# ── 2026 driver → constructor mapping ────────────────────────────────────────
# Updated each season; constructor IDs match ESPN team names (lowercased)
DRIVER_TEAM: dict[str, str] = {
    "Kimi Antonelli":    "mercedes",
    "George Russell":    "mercedes",
    "Charles Leclerc":   "ferrari",
    "Lewis Hamilton":    "ferrari",
    "Lando Norris":      "mclaren",
    "Oscar Piastri":     "mclaren",
    "Max Verstappen":    "red_bull",
    "Yuki Tsunoda":      "red_bull",
    "Pierre Gasly":      "alpine",
    "Jack Doohan":       "alpine",
    "Franco Colapinto":  "alpine",
    "Fernando Alonso":   "aston_martin",
    "Lance Stroll":      "aston_martin",
    "Alexander Albon":   "williams",
    "Carlos Sainz":      "williams",
    "Nico Hulkenberg":   "sauber",
    "Nico Hülkenberg":   "sauber",
    "Gabriel Bortoleto": "sauber",
    "Isack Hadjar":      "rb",
    "Liam Lawson":       "rb",
    "Esteban Ocon":      "haas",
    "Oliver Bearman":    "haas",
}

# Fallback constructor colors (used when ESPN color unavailable)
CONSTRUCTOR_COLORS: dict[str, dict] = {
    "mercedes":     {"primary": "#00D2BE", "secondary": "#000000"},
    "ferrari":      {"primary": "#E8002D", "secondary": "#FFFFFF"},
    "mclaren":      {"primary": "#FF8000", "secondary": "#000000"},
    "red_bull":     {"primary": "#3671C6", "secondary": "#CC1E4A"},
    "alpine":       {"primary": "#0090FF", "secondary": "#FF0000"},
    "aston_martin": {"primary": "#358C75", "secondary": "#FFFFFF"},
    "williams":     {"primary": "#64C4FF", "secondary": "#000000"},
    "haas":         {"primary": "#B6BABD", "secondary": "#E8002D"},
    "rb":           {"primary": "#6692FF", "secondary": "#1E41FF"},
    "sauber":       {"primary": "#C92D4B", "secondary": "#000000"},
}

def _ctor_colors(team_key: str, espn_color: str = "") -> dict:
    primary = f"#{espn_color}" if espn_color else CONSTRUCTOR_COLORS.get(team_key, {}).get("primary", "#555555")
    secondary = CONSTRUCTOR_COLORS.get(team_key, {}).get("secondary", "#FFFFFF")
    return {"primary": primary, "secondary": secondary}

def _driver_ctor_colors(driver_name: str, ctor_color_map: dict[str, dict]) -> dict:
    for key, val in DRIVER_TEAM.items():
        if key.lower() == driver_name.lower() or driver_name.lower() in key.lower():
            return ctor_color_map.get(val, {"primary": "#555555", "secondary": "#FFFFFF"})
    return {"primary": "#555555", "secondary": "#FFFFFF"}

# ── All-time F1 legends (through 2024 season) ─────────────────────────────────
# name, cc3, birth, titles, wins, poles, podiums, active
F1_LEGENDS_RAW = [
    ("Lewis Hamilton",     "GBR", 1985, 7, 103, 104, 197, True),
    ("Michael Schumacher", "GER", 1969, 7,  91,  68, 155, False),
    ("Max Verstappen",     "NED", 1997, 4,  63,  40, 113, True),
    ("Juan Manuel Fangio", "ARG", 1911, 5,  24,  29,  35, False),
    ("Alain Prost",        "FRA", 1955, 4,  51,  33, 106, False),
    ("Sebastian Vettel",   "GER", 1987, 4,  53,  57, 122, False),
    ("Ayrton Senna",       "BRA", 1960, 3,  41,  65,  80, False),
    ("Niki Lauda",         "AUT", 1949, 3,  25,  24,  54, False),
    ("Nelson Piquet",      "BRA", 1952, 3,  23,  24,  60, False),
    ("Jackie Stewart",     "GBR", 1939, 3,  27,  17,  43, False),
    ("Fernando Alonso",    "ESP", 1981, 2,  32,  22, 106, True),
    ("Mika Häkkinen",      "FIN", 1968, 2,  20,  26,  51, False),
    ("Jim Clark",          "GBR", 1936, 2,  25,  33,  32, False),
    ("Nigel Mansell",      "GBR", 1953, 1,  31,  32,  59, False),
    ("Charles Leclerc",    "MON", 1997, 0,   8,  26,  40, True),
    ("Lando Norris",       "GBR", 2000, 0,   5,   8,  33, True),
]

COUNTRY_COLORS: dict[str, str] = {
    "GBR": "#012169", "NED": "#AE1C28", "GER": "#000000", "ESP": "#AA151B",
    "FIN": "#003580", "FRA": "#002395", "ITA": "#009246", "BRA": "#009C3B",
    "AUS": "#00008B", "CAN": "#FF0000", "JPN": "#BC002D", "AUT": "#ED2939",
    "SUI": "#FF0000", "BEL": "#000000", "USA": "#B22234", "MEX": "#006847",
    "DEN": "#C60C30", "MON": "#CE1126", "ARG": "#74ACDF",
}

W_LEGEND = {"titles": 15, "wins": 0.5, "poles": 0.3, "podiums": 0.15}

NATIONALITY_TO_CC3: dict[str, str] = {
    "British": "GBR", "Dutch": "NED", "German": "GER", "Spanish": "ESP",
    "Finnish": "FIN", "French": "FRA", "Italian": "ITA", "Brazilian": "BRA",
    "Australian": "AUS", "Canadian": "CAN", "Japanese": "JPN",
    "Austrian": "AUT", "Swiss": "SUI", "Belgian": "BEL", "American": "USA",
    "Mexican": "MEX", "Danish": "DEN", "Chinese": "CHN",
    "Monegasque": "MON", "Thai": "THA", "Argentine": "ARG",
    "South African": "RSA", "New Zealander": "NZL",
}

# ESPN flag URL → cc3 (based on URL pattern .../ita.png → ITA)
ESPN_CC2_TO_CC3: dict[str, str] = {
    "gbr": "GBR", "ned": "NED", "ger": "GER", "esp": "ESP", "fin": "FIN",
    "fra": "FRA", "ita": "ITA", "bra": "BRA", "aus": "AUS", "can": "CAN",
    "jpn": "JPN", "aut": "AUT", "sui": "SUI", "bel": "BEL", "usa": "USA",
    "mex": "MEX", "dnk": "DEN", "mco": "MON", "arg": "ARG", "tha": "THA",
    "nzl": "NZL", "chn": "CHN",
}

def _cc3_from_flag(flag_url: str) -> str:
    if not flag_url:
        return ""
    stem = flag_url.rstrip("/").split("/")[-1].replace(".png", "").lower()
    return ESPN_CC2_TO_CC3.get(stem, stem.upper())

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
        print(f"[WARN] F1 fetch failed ({exc}): {url}", file=sys.stderr)
        if path.exists():
            return json.loads(path.read_text())
        return None

# ── Championship importance (7–10, dynamic) ───────────────────────────────────

def _importance(standings: list[dict], round_num: int, total_races: int) -> float:
    if total_races == 0:
        return 7.0
    progress = round_num / total_races
    base     = 7.0 + progress * 2.0      # 7 → 9 as season progresses
    if len(standings) < 2:
        return round(min(9.0, base), 1)
    leader    = standings[0]["points"]
    remaining = (total_races - round_num) * 25
    gap       = leader - standings[1]["points"]
    if gap > remaining:
        return 7.0  # title mathematically decided
    contenders = sum(1 for s in standings if leader - s["points"] <= remaining)
    if round_num >= total_races and contenders >= 2:
        return 10.0
    if round_num >= total_races - 1 and contenders >= 2:
        return 10.0
    if contenders >= 2:
        base = min(10.0, base + contenders * 0.3)
    return round(min(10.0, base), 1)

# ── Data builders ─────────────────────────────────────────────────────────────

def _standings() -> tuple[list[dict], list[dict], int, int]:
    data = _fetch(ESPN_STANDINGS, ttl_hours=1.0)
    if not data:
        return [], [], 0, 0

    children = data.get("children", [])
    driver_child      = next((c for c in children if c.get("name","").lower() == "driver championship"), None)
    ctor_child        = next((c for c in children if c.get("name","").lower() == "constructor championship"), None)
    if not driver_child:
        driver_child = children[0] if children else {}
    if not ctor_child:
        ctor_child   = children[1] if len(children) > 1 else {}

    # Build constructor color map from ESPN colors
    ctor_color_map: dict[str, dict] = {}
    ctor_list: list[dict] = []
    for e in ctor_child.get("standings", {}).get("entries", []):
        t    = e.get("team", {})
        name = t.get("displayName", "")
        key  = name.lower().replace(" ", "_")
        espn_color = t.get("color", "")
        colors = _ctor_colors(key, espn_color)
        ctor_color_map[key] = colors
        pts = next((float(s["displayValue"]) for s in e.get("stats", []) if s["name"] == "points" and s["displayValue"].strip()), 0.0)
        rnk = int(next((s["value"] for s in e.get("stats", []) if s["name"] == "rank"), 0))
        ctor_list.append({
            "position": rnk,
            "name":     name,
            "id":       key,
            "primary":  colors["primary"],
            "secondary":colors["secondary"],
            "points":   pts,
        })

    # Driver standings
    driver_list: list[dict] = []
    race_stat_names: list[str] = []
    for e in driver_child.get("standings", {}).get("entries", []):
        a    = e.get("athlete", {})
        name = a.get("displayName", "")
        flag = a.get("flag", {}).get("href", "")
        cc3  = _cc3_from_flag(flag)
        pts  = next((float(s["displayValue"]) for s in e.get("stats", []) if s["name"] == "championshipPts" and s["displayValue"].strip()), 0.0)
        rnk  = int(next((s["value"] for s in e.get("stats", []) if s["name"] == "rank"), 0))
        if not race_stat_names:
            race_stat_names = [s["name"] for s in e.get("stats", [])
                               if s["name"] not in ("rank", "championshipPts", "overall")]
        colors = _driver_ctor_colors(name, ctor_color_map)
        driver_list.append({
            "position":  rnk,
            "name":      name,
            "nationality": "",
            "country":   cc3,
            "teamCode":  DRIVER_TEAM.get(name, ""),
            "logo":      flag,
            "primary":   colors["primary"],
            "secondary": colors["secondary"],
            "colors":    colors,
            "team":      "",
            "points":    pts,
            "wins":      0,
        })

    # round_num = races with non-blank results (check top driver)
    round_num   = 0
    total_races = len(race_stat_names)
    if driver_child.get("standings", {}).get("entries"):
        top_stats = driver_child["standings"]["entries"][0].get("stats", [])
        round_num = sum(
            1 for s in top_stats
            if s["name"] in race_stat_names and s.get("displayValue", "").strip() not in ("", "-")
        )

    driver_list.sort(key=lambda x: x["position"])
    ctor_list.sort(key=lambda x: x["position"])
    return driver_list, ctor_list, round_num, total_races


def _parse_event(ev: dict) -> dict | None:
    """Extract podium + metadata from an ESPN F1 event dict."""
    comps = ev.get("competitions", [{}])[0].get("competitors", [])
    comps_sorted = sorted(comps, key=lambda c: c.get("order", 999))
    podium = []
    for c in comps_sorted[:3]:
        a    = c.get("athlete", {})
        name = a.get("displayName", "")
        podium.append({
            "position": c.get("order", ""),
            "name":     name,
            "team":     DRIVER_TEAM.get(name, ""),
            "time":     "",
            "primary":  "#555555",
        })
    if not podium:
        return None
    circuit = ev.get("circuit", {})
    return {
        "name":    ev.get("name", ""),
        "date":    ev.get("date", "")[:10],
        "circuit": circuit.get("fullName") or circuit.get("shortName", ""),
        "round":   0,
        "podium":  podium,
    }

def _last_race() -> dict | None:
    data = _fetch(ESPN_SCOREBOARD, ttl_hours=1.0)
    if not data:
        return None
    events = data.get("events", [])
    # Find most recent completed non-sprint grand prix
    for ev in events:
        if "sprint" in ev.get("name", "").lower():
            continue
        result = _parse_event(ev)
        if result and result["podium"]:
            return result
    # Fallback: any completed event
    return _parse_event(events[0]) if events else None

def _last_sprint() -> dict | None:
    """Return the most recent sprint race result, or None if no sprint this season."""
    data = _fetch(ESPN_SCOREBOARD, ttl_hours=1.0)
    if not data:
        return None
    for ev in data.get("events", []):
        if "sprint" in ev.get("name", "").lower():
            result = _parse_event(ev)
            if result and result["podium"]:
                return result
    return None

# ── Legends ───────────────────────────────────────────────────────────────────

def build_legends() -> list[dict]:
    scored = [
        (r[3]*W_LEGEND["titles"] + r[4]*W_LEGEND["wins"] + r[5]*W_LEGEND["poles"] + r[6]*W_LEGEND["podiums"], r)
        for r in F1_LEGENDS_RAW
    ]
    max_raw = max(s for s, _ in scored)
    out = []
    for raw, row in sorted(scored, reverse=True):
        name, cc3, birth, titles, wins, poles, podiums, active = row
        out.append({
            "id":          name.lower().replace(" ", "_").replace("ä","a"),
            "name":        name,
            "country":     cc3,
            "logo":        f"https://a.espncdn.com/i/teamlogos/countries/500/{cc3.lower()}.png",
            "teamCode":    cc3,
            "primary":     COUNTRY_COLORS.get(cc3, "#555"),
            "secondary":   "#FFFFFF",
            "legendScore": round(raw / max_raw * 100, 1),
            "active":      active,
            "stats":       {"titles": titles, "wins": wins, "poles": poles, "podiums": podiums, "birth": birth},
        })
    return out

# ── Main ──────────────────────────────────────────────────────────────────────

def write_data() -> None:
    out_path = ROOT / "f1_data.js"
    prev_drivers = _prev_rank_map(out_path, "F1_DATA", "DRIVERS")
    prev_legends = _prev_rank_map(out_path, "F1_DATA", "LEGENDS")

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[F1] Fetching {CURRENT_YEAR} season data…", file=sys.stderr)

    legends                              = build_legends()
    drivers, constructors, round_num, total_races = _standings()
    last_race                            = _last_race()
    last_sprint                          = _last_sprint()
    importance = _importance(drivers, round_num, total_races)

    # Enrich last race podium with team colors
    if last_race:
        ctor_colors_quick = {k: v["primary"] for k, v in CONSTRUCTOR_COLORS.items()}
        for p in last_race["podium"]:
            team_key = p["team"]
            # find matching constructor
            for k in ctor_colors_quick:
                if k in team_key.lower():
                    p["primary"] = ctor_colors_quick[k]
                    break
            if p["primary"] == "#555555":
                # try drivers list
                drv = next((d for d in drivers if d["name"] == p["name"]), None)
                if drv:
                    p["primary"] = drv["primary"]

    # score = progress toward theoretical season max (total_races × 25 pts)
    max_season_pts = total_races * 25
    for i, d in enumerate(drivers[:10]):
        d["score"] = round(d["points"] / max(max_season_pts, 1) * 100, 1)
        d["stats"] = {"pts": d["points"], "wins": d["wins"]}
        d["prevRank"] = prev_drivers.get(str(d.get("name", "")))
    for d in drivers[10:]:
        d["score"] = round(d["points"] / max(max_season_pts, 1) * 100, 1)
        d["stats"] = {"pts": d["points"], "wins": d["wins"]}
    for lg in legends:
        lg["prevRank"] = prev_legends.get(str(lg.get("id") or lg.get("name", "")))

    payload = {
        "UPDATED":        updated,
        "SEASON":         str(CURRENT_YEAR),
        "ROUND":          round_num,
        "TOTAL_ROUNDS":   total_races,
        "MAX_SEASON_PTS": max_season_pts,
        "IMPORTANCE":   importance,
        "DRIVERS":      drivers[:10],
        "CONSTRUCTORS": constructors[:5],
        "LAST_RACE":    last_race,
        "LAST_SPRINT":  last_sprint,
        "LEGENDS":      legends,
    }

    out = ROOT / "f1_data.js"
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"// Auto-generated {updated}\n")
        f.write(f"window.F1_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n")

    print(f"Written: {out}", file=sys.stderr)
    print(f"  Round {round_num}/{total_races} · importance={importance}")
    if drivers:
        print(f"  Leader: {drivers[0]['name']} ({drivers[0]['points']} pts)")
    if last_race:
        print(f"  Last race: {last_race['name']} → {last_race['podium'][0]['name'] if last_race['podium'] else '?'}")


if __name__ == "__main__":
    write_data()
