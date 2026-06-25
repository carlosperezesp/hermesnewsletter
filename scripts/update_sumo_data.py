#!/usr/bin/env python3
"""Sumo data: Yokozuna legends (hardcoded) + live banzuke from sumo-api.com."""
from __future__ import annotations
import hashlib, json, sys, time, urllib.request
from datetime import datetime, timezone, date as _date
from pathlib import Path

ROOT  = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".sumo_cache"
CACHE.mkdir(exist_ok=True)

SUMO_API = "https://sumo-api.com/api"


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

# Country code mapping (JSA codes → ISO 2-letter for flags)
JSA_TO_CC2: dict[str, str] = {
    "JPN": "jp", "MGL": "mn", "MON": "mn",
    "BUL": "bg", "EST": "ee", "KAZ": "kz", "RUS": "ru", "BRA": "br",
    "USA": "us", "GEO": "ge", "TGA": "to", "CHN": "cn", "KOR": "kr",
    "IND": "in", "AUS": "au", "NZL": "nz", "UKR": "ua", "ARM": "am",
    "CZE": "cz",
}
COUNTRY_COLORS: dict[str, str] = {
    "JPN": "#BC002D", "MGL": "#C4272F", "MON": "#C4272F",
    "USA": "#B22234", "BUL": "#00966E", "EST": "#0072CE",
    "KAZ": "#00AFCA", "RUS": "#003DA5", "GEO": "#DA291C",
}

def _flag(cc3: str) -> str:
    cc2 = JSA_TO_CC2.get(cc3, "")
    return f"https://flagcdn.com/24x18/{cc2}.png" if cc2 else ""

# shusshin (origen del rikishi) -> código JSA. Los japoneses traen una prefectura
# (Tokyo, Hokkaido…), así que cualquier origen no reconocido como país extranjero
# se asume Japón.
_FOREIGN_SHUSSHIN: dict[str, str] = {
    "Mongolia": "MGL", "Georgia": "GEO", "Russia": "RUS", "Brazil": "BRA",
    "Bulgaria": "BUL", "Kazakhstan": "KAZ", "China": "CHN", "Ukraine": "UKR",
    "Estonia": "EST", "Tonga": "TGA", "Korea": "KOR", "Czech": "CZE",
    "Australia": "AUS", "Hawaii": "USA", "United States": "USA",
}

def _rikishi_country(shusshin: str) -> str:
    s = shusshin or ""
    for key, cc in _FOREIGN_SHUSSHIN.items():
        if key in s:
            return cc
    return "JPN"

# ── Yokozuna legends (hardcoded — authoritative source: JSA official records) ─
# yusho = Emperor's Cup wins; yokozuna_basho = basho competed at Yokozuna rank
YOKOZUNA_LEGENDS = [
    {"name": "Hakuho",      "country": "MGL", "birth": 1985, "yusho": 45, "yokozuna_basho": 84, "yok_start": 2007, "yok_end": 2021},
    {"name": "Taiho",       "country": "JPN", "birth": 1940, "yusho": 32, "yokozuna_basho": 58, "yok_start": 1961, "yok_end": 1971},
    {"name": "Chiyonofuji", "country": "JPN", "birth": 1955, "yusho": 31, "yokozuna_basho": 58, "yok_start": 1981, "yok_end": 1991},
    {"name": "Asashoryu",   "country": "MGL", "birth": 1980, "yusho": 25, "yokozuna_basho": 60, "yok_start": 2003, "yok_end": 2010},
    {"name": "Kitanoumi",   "country": "JPN", "birth": 1953, "yusho": 24, "yokozuna_basho": 63, "yok_start": 1974, "yok_end": 1985},
    {"name": "Musashimaru", "country": "USA", "birth": 1971, "yusho": 12, "yokozuna_basho": 38, "yok_start": 1999, "yok_end": 2003},
    {"name": "Futabayama",  "country": "JPN", "birth": 1912, "yusho": 12, "yokozuna_basho": 35, "yok_start": 1936, "yok_end": 1943},
    {"name": "Terunofuji",  "country": "MGL", "birth": 1991, "yusho": 10, "yokozuna_basho": 18, "yok_start": 2021, "yok_end": 2024},
    {"name": "Akebono",     "country": "USA", "birth": 1969, "yusho": 11, "yokozuna_basho": 36, "yok_start": 1993, "yok_end": 2001},
    {"name": "Harumafuji",  "country": "MGL", "birth": 1984, "yusho":  9, "yokozuna_basho": 30, "yok_start": 2012, "yok_end": 2017},
    {"name": "Kakuryu",     "country": "MGL", "birth": 1985, "yusho":  6, "yokozuna_basho": 42, "yok_start": 2014, "yok_end": 2021},
    {"name": "Hoshoryu",    "country": "MGL", "birth": 1999, "yusho":  3, "yokozuna_basho":  8, "yok_start": 2024, "yok_end": None},
    {"name": "Onosato",     "country": "JPN", "birth": 2000, "yusho":  5, "yokozuna_basho":  6, "yok_start": 2025, "yok_end": None},
]

# ── Cache helpers ─────────────────────────────────────────────────────────────

def _fetch_json(url: str, ttl_hours: float = 6.0) -> dict | list | None:
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
        print(f"[WARN] sumo-api fetch failed: {exc}", file=sys.stderr)
        if path.exists():
            return json.loads(path.read_text())
        return None

# ── Basho ID helpers ──────────────────────────────────────────────────────────

def _current_basho_id() -> str:
    now = datetime.now(timezone.utc)
    basho_months = [1, 3, 5, 7, 9, 11]
    year, month = now.year, now.month
    for m in sorted(basho_months, reverse=True):
        if m <= month:
            return f"{year}{m:02d}"
    return f"{year - 1}11"

def _prev_basho_id(basho_id: str) -> str:
    year, month = int(basho_id[:4]), int(basho_id[4:])
    basho_months = [1, 3, 5, 7, 9, 11]
    idx = basho_months.index(month)
    if idx > 0:
        return f"{year}{basho_months[idx-1]:02d}"
    return f"{year-1}11"

def _all_basho_ids(years_back: int = 5) -> list[str]:
    """All basho IDs from (current_year - years_back) up to current basho."""
    from datetime import date
    current = _current_basho_id()
    months  = [1, 3, 5, 7, 9, 11]
    result  = []
    for y in range(date.today().year - years_back, date.today().year + 1):
        for m in months:
            bid = f"{y}{m:02d}"
            if bid <= current:
                result.append(bid)
    return result

# ── Banzuke fetch ─────────────────────────────────────────────────────────────

def _fetch_banzuke(basho_id: str) -> list[dict]:
    url  = f"{SUMO_API}/basho/{basho_id}/banzuke/Makuuchi"
    data = _fetch_json(url)
    if not isinstance(data, dict):
        return []
    rows = []
    for side in ("east", "west"):
        for w in data.get(side, []):
            record = w.get("record", [])
            wins     = w.get("wins")   or sum(1 for b in record if b.get("result") == "win")
            losses   = w.get("losses") or sum(1 for b in record if b.get("result") == "loss")
            absences = w.get("absences") or sum(1 for b in record if b.get("result") == "absent")
            rows.append({
                "side":       side.capitalize(),
                "rankValue":  w.get("rankValue", 999),
                "rankLabel":  w.get("rank", ""),
                "name":       w.get("shikonaEn") or w.get("shikona", ""),
                "rikishiID":  w.get("rikishiID"),
                "wins":       wins,
                "losses":     losses,
                "absences":   absences,
            })
    rows.sort(key=lambda x: x["rankValue"])
    return rows[:20]

def _fetch_rikishi_info(rikishi_id: int) -> dict:
    """Perfil del luchador: edad (de birthDate) y país (de shusshin). Cacheado 30
    días — ni el nacimiento ni el origen cambian."""
    if not rikishi_id:
        return {}
    data = _fetch_json(f"{SUMO_API}/rikishi/{rikishi_id}", ttl_hours=720.0)
    if not isinstance(data, dict):
        return {}
    out: dict = {"country": _rikishi_country(data.get("shusshin", ""))}
    bd = data.get("birthDate", "")
    if bd:
        try:
            born = datetime.fromisoformat(bd.replace("Z", "+00:00")).date()
            today = _date.today()
            out["age"] = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        except Exception:
            pass
    return out

def _fetch_basho_info(basho_id: str, ttl_hours: float = 6.0) -> dict | None:
    url  = f"{SUMO_API}/basho/{basho_id}"
    data = _fetch_json(url, ttl_hours=ttl_hours)
    if not isinstance(data, dict):
        return None
    yusho_list = data.get("yusho", [])
    if not isinstance(yusho_list, list):
        yusho_list = [yusho_list] if yusho_list else []
    makuuchi = next((y for y in yusho_list if y.get("type") == "Makuuchi"), None)
    return {
        "id":        basho_id,
        "startDate": data.get("startDate", ""),
        "endDate":   data.get("endDate", ""),
        "winner":    makuuchi.get("shikonaEn") if makuuchi else None,
    }

def _fetch_career_yusho(current_basho_id: str) -> dict[str, int]:
    """Count Makuuchi tournament wins per wrestler across the last 5 years."""
    counts: dict[str, int] = {}
    for bid in _all_basho_ids(years_back=5):
        ttl = 2.0 if bid == current_basho_id else 168.0  # past basho never change
        info = _fetch_basho_info(bid, ttl_hours=ttl)
        if info and info.get("winner"):
            # Normalize to first word (stable shikona root) so "Kirishima Tetsuo" → "Kirishima"
            w = info["winner"].split()[0]
            counts[w] = counts.get(w, 0) + 1
    return counts

def _short_rank(label: str) -> str:
    """Strip East/West positioning — meaningless to non-sumo readers."""
    label = label.replace(" East", "").replace(" West", "").strip()
    # For sanyaku, drop the number (only one Yokozuna spot, etc.)
    for top in ("Yokozuna", "Ozeki", "Sekiwake", "Komusubi"):
        if label.startswith(top):
            return top
    # Maegashira: keep the number (1 = near top, 5 = further down)
    return label

# ── Scoring ───────────────────────────────────────────────────────────────────

def _legend_score(y: int, yb: int, max_raw: float) -> float:
    raw = y * 5.0 + yb * 0.5
    return round(raw / max_raw * 100, 1)

# ── Jóvenes promesa (pilar 5) ─────────────────────────────────────────────────
# Sumo no trae un score de "devenir" como el resto, pero el banzuke ya da edad,
# rango y resultados. La promesa = haber llegado MUY alto siendo MUY joven, así
# que proyectamos con una base por tier de rango + un bonus de juventud. Es
# determinista y explicable (sin IA).
PROSPECT_MAX_AGE = 25
_TIER_SCORE = {"Yokozuna": 100.0, "Ozeki": 88.0, "Sekiwake": 76.0, "Komusubi": 68.0}

def _prospect_score(rank_short: str, age: "int | None") -> float:
    base = _TIER_SCORE.get(rank_short)
    if base is None:  # Maegashira N: 1 cerca de la cúspide, baja con N
        try:
            n = int(rank_short.split()[-1])
        except (ValueError, IndexError):
            n = 10
        base = max(30.0, 60.0 - (n - 1) * 3.0)
    youth = max(0, PROSPECT_MAX_AGE - age) * 1.5 if age else 0.0
    return round(min(100.0, base + youth), 1)

def build_young_prospects(banzuke: list[dict]) -> list[dict]:
    out = [{
        "id":             w["name"].lower().replace(" ", "_"),
        "name":           w["name"],
        "rankShort":      w.get("rankShort", ""),
        "age":            w.get("age"),
        "wins":           w.get("wins", 0),
        "losses":         w.get("losses", 0),
        "absences":       w.get("absences", 0),
        "yusho":          w.get("yusho", 0),
        "country":        w.get("country"),
        "logo":           w.get("logo"),
        "primary":        w.get("primary", "#4a4745"),
        "projectedScore": _prospect_score(w.get("rankShort", ""), w.get("age")),
    } for w in banzuke if w.get("age") and w["age"] <= PROSPECT_MAX_AGE]
    out.sort(key=lambda p: -p["projectedScore"])
    return out[:6]

def _sumo_importance(banzuke: list) -> float:
    active = [w for w in banzuke if w.get("wins", 0) or w.get("losses", 0) or w.get("absences", 0)]
    if not active:
        return 8.0  # Between basho or no data
    max_bouts = max(w.get("wins", 0) + w.get("losses", 0) + w.get("absences", 0) for w in active)
    remaining = max(0, 15 - max_bouts)
    sorted_w = sorted(active, key=lambda w: -w.get("wins", 0))
    lead = sorted_w[0].get("wins", 0) - (sorted_w[1].get("wins", 0) if len(sorted_w) >= 2 else 0)
    # Champion already decided: gently above base
    if remaining == 0 or lead > remaining:
        return round(8.0 + 0.5 * (max_bouts / 15), 1)
    # Race alive: scale 8→10 as basho completes, with tension bonus for tight lead
    completion = max_bouts / 15
    tension = max(0.0, 1.0 - lead / max(1, remaining))  # 1 = very tight
    return round(8.0 + 2.0 * completion * (0.5 + 0.5 * tension), 1)

# ── Main ──────────────────────────────────────────────────────────────────────

def build_legends() -> list[dict]:
    max_raw = max(y["yusho"] * 5 + y["yokozuna_basho"] * 0.5 for y in YOKOZUNA_LEGENDS)
    out = []
    for y in sorted(YOKOZUNA_LEGENDS, key=lambda x: x["yusho"] * 5 + x["yokozuna_basho"] * 0.5, reverse=True):
        out.append({
            "id":          y["name"].lower().replace(" ", "_"),
            "name":        y["name"],
            "country":     y["country"],
            "logo":        _flag(y["country"]),
            "teamCode":    y["country"],
            "primary":     COUNTRY_COLORS.get(y["country"], "#555"),
            "secondary":   "#FFFFFF",
            "legendScore": _legend_score(y["yusho"], y["yokozuna_basho"], max_raw),
            "stats": {
                "yusho":          y["yusho"],
                "yokozuna_basho": y["yokozuna_basho"],
                "birth":          y["birth"],
                "yok_start":      y.get("yok_start"),
                "yok_end":        y.get("yok_end"),
            },
        })
    return out

def write_data() -> None:
    out_path = ROOT / "sumo_data.js"
    prev_legends = _prev_rank_map(out_path, "SUMO_DATA", "LEGENDS")

    updated    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    legends    = build_legends()
    for lg in legends:
        lg["prevRank"] = prev_legends.get(str(lg.get("id") or lg.get("name", "")))
    basho_id   = _current_basho_id()
    basho_info = _fetch_basho_info(basho_id)
    banzuke    = _fetch_banzuke(basho_id)

    # If current basho has no data yet, try previous
    if not banzuke:
        prev_id    = _prev_basho_id(basho_id)
        basho_info = _fetch_basho_info(prev_id) or basho_info
        banzuke    = _fetch_banzuke(prev_id)
        if banzuke:
            basho_id = prev_id

    # Enrich banzuke with career yusho counts and legend scores
    max_raw         = max(y["yusho"] * 5 + y["yokozuna_basho"] * 0.5 for y in YOKOZUNA_LEGENDS)
    full_legend_map = {lg["name"]: lg for lg in legends}
    career_yusho    = _fetch_career_yusho(basho_id)
    print(f"  Career yusho data: {dict(sorted(career_yusho.items(), key=lambda x: -x[1])[:8])}", file=sys.stderr)

    for w in banzuke:
        name = w["name"]
        w["rankShort"] = _short_rank(w.get("rankLabel", ""))
        if name in full_legend_map:
            lg = full_legend_map[name]
            w["yusho"]       = lg["stats"]["yusho"]
            w["legendScore"] = lg["legendScore"]
        else:
            yusho = career_yusho.get(name, 0)
            w["yusho"]       = yusho
            w["legendScore"] = round(yusho * 5 / max_raw * 100, 1) if yusho else 0.0
        # Edad y país desde el perfil del rikishi (cacheado 30 días)
        info = _fetch_rikishi_info(w.get("rikishiID"))
        if info.get("age") is not None:
            w["age"] = info["age"]
        cc = info.get("country", "JPN")
        w["country"] = cc
        w["logo"]    = _flag(cc)
        w["primary"] = COUNTRY_COLORS.get(cc, "#4a4745")

    importance = _sumo_importance(banzuke)
    young_prospects = build_young_prospects(banzuke)

    payload = {
        "UPDATED":        updated,
        "LEGENDS":        legends,
        "BASHO_ID":       basho_id,
        "BASHO_INFO":     basho_info,
        "BANZUKE":        banzuke,
        "YOUNG_PROSPECTS": young_prospects,
        "IMPORTANCE":     importance,
    }

    out = ROOT / "sumo_data.js"
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"// Auto-generated {updated}\n")
        f.write(f"window.SUMO_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n")

    print(f"Written: {out}", file=sys.stderr)
    print(f"  Top Yokozuna: {legends[0]['name']} ({legends[0]['stats']['yusho']} yusho)")
    print(f"  Basho: {basho_id} · banzuke rows: {len(banzuke)}")


if __name__ == "__main__":
    write_data()
