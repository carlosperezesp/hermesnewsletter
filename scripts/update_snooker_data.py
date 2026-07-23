#!/usr/bin/env python3
"""Snooker: leyendas por palmarés REAL descargado (Triple Corona) + ranking de forma.

Las leyendas y su score salen del recuento AUTOMÁTICO de títulos de Triple Corona
(Mundial + UK + Masters) leído de Wikipedia (artículo 'Triple Crown (snooker)',
parrilla temporada×evento) — todos los que califican, con sus títulos reales,
recalculado en cada ejecución. Es la medida estándar de grandeza en snooker.

Nota de alcance: la Triple Corona es un concepto de la era moderna (Masters desde
1975, UK desde 1977), así que grandes anteriores (Joe/Fred Davis, y los Mundiales
de Reardon previos a 1977) quedan fuera por definición.

El ranking de forma actual (Nivel) sigue curado: no hay feed abierto del ranking
mundial. Los metadatos descriptivos (país, era, frase) son estables; lo que decide
el ranking de leyendas (los títulos) es fehaciente y automático.
"""
from __future__ import annotations
import json, re, html, time, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "snooker_data.js"
CACHE = ROOT / ".sports_cache"; CACHE.mkdir(exist_ok=True)
W_WORLD, W_UK, W_MASTERS = 10.0, 4.0, 4.0
AGE_CUTOFF = 23  # cantera: los del top actual con esta edad o menos

TC_SOURCE = "https://en.wikipedia.org/wiki/Triple_Crown_(snooker)"

CC2 = {"ENG": "gb-eng", "SCO": "gb-sct", "WAL": "gb-wls", "NIR": "gb-nir",
       "IRL": "ie", "CHN": "cn", "AUS": "au", "BEL": "be", "HKG": "hk", "GER": "de", "THA": "th"}
COLORS = {"ENG": "#CE1124", "SCO": "#005EB8", "WAL": "#C8102E", "NIR": "#009A44",
          "IRL": "#169B62", "CHN": "#DE2910", "AUS": "#00008B", "BEL": "#000000",
          "HKG": "#DE2910", "GER": "#000000", "THA": "#A51931"}

# País por jugador (dato estable). Para quien falte, sin bandera.
COUNTRY = {
    "Ronnie O'Sullivan": "ENG", "Stephen Hendry": "SCO", "Steve Davis": "ENG",
    "Mark Selby": "ENG", "John Higgins": "SCO", "Mark Williams": "WAL",
    "Neil Robertson": "AUS", "Judd Trump": "ENG", "Alex Higgins": "NIR",
    "Ray Reardon": "WAL", "Cliff Thorburn": "CAN", "Shaun Murphy": "ENG",
    "Terry Griffiths": "WAL", "John Spencer": "ENG", "Ding Junhui": "CHN",
    "Stuart Bingham": "ENG", "John Parrott": "ENG", "Zhao Xintong": "CHN",
    "Dennis Taylor": "NIR", "Kyren Wilson": "ENG", "Peter Ebdon": "ENG",
    "Doug Mountjoy": "WAL", "Wu Yize": "CHN", "Luca Brecel": "BEL",
    "Mark Allen": "NIR", "Ken Doherty": "IRL", "Yan Bingtao": "CHN",
    "Graeme Dott": "SCO", "Joe Johnson": "ENG", "Jimmy White": "ENG",
    "Matthew Stevens": "WAL", "Stephen Maguire": "SCO", "Paul Hunter": "ENG",
    "Alan McManus": "SCO", "Perrie Mans": "ZAF", "John Virgo": "ENG",
    "Patsy Fagan": "IRL",
}
# Frases curadas para los grandes (estable). Para el resto se genera con los conteos.
NOTE = {
    "Ronnie O'Sullivan": "'The Rocket': récord absoluto de Triple Coronas; genio irrepetible.",
    "Stephen Hendry": "Dominó los 90 con siete Mundiales; el más precoz.",
    "Steve Davis": "El icono de los 80 que llevó el snooker a la tele.",
    "Mark Selby": "'El Torturador': cuatro Mundiales a base de táctica.",
    "John Higgins": "'El Mago': uno de los constructores de tacadas más brillantes.",
    "Mark Williams": "Zurdo letal con dos décadas en la cima.",
    "Neil Robertson": "El mejor jugador no británico de la historia.",
    "Judd Trump": "El más completo de su generación; ataque total.",
    "Alex Higgins": "'Huracán': el carisma que popularizó el snooker.",
    "Ray Reardon": "'Drácula': dominador de los 70 (seis Mundiales, dos previos a la Triple Corona).",
    "Cliff Thorburn": "'El Nugget': primer campeón del mundo de fuera de las islas.",
    "Shaun Murphy": "Campeón del mundo 2005 saliendo de la fase previa.",
    "Ding Junhui": "El pionero chino que abrió el snooker a un continente.",
    "Zhao Xintong": "La nueva ola china; campeón del mundo 2025.",
    "Kyren Wilson": "'El Guerrero': campeón del mundo 2024.",
}

# Ranking de forma actual (curado; sin feed abierto del ranking mundial).
# (nombre, cc3, edad, nivel, nota) — la edad alimenta la cantera automática.
CURRENT = [
    ("Judd Trump", "ENG", 37, 100, "Nº1 del ranking mundial"),
    ("Kyren Wilson", "ENG", 35, 94, "Campeón del mundo 2024"),
    ("Ronnie O'Sullivan", "ENG", 51, 92, "El más grande de todos los tiempos"),
    ("Zhao Xintong", "CHN", 29, 90, "Campeón del mundo 2025"),
    ("Mark Williams", "WAL", 51, 87, "Tricampeón del mundo, aún en la élite"),
    ("John Higgins", "SCO", 51, 84, "Cuádruple campeón del mundo"),
    ("Neil Robertson", "AUS", 44, 82, "Campeón del mundo 2010"),
    ("Mark Selby", "ENG", 43, 80, "Cuádruple campeón del mundo"),
]
CURRENT_NAMES = {name for name, *_ in CURRENT}


def flag(c): x = CC2.get(c, ""); return f"https://flagcdn.com/24x18/{x}.png" if x else ""
def _slug(n): return re.sub(r"[^a-z0-9]+", "_", n.lower()).strip("_")
def _base(name, c):
    col = COLORS.get(c, "#4A4745")
    return {"id": _slug(name), "name": name, "country": c, "logo": flag(c),
            "colors": {"primary": col, "secondary": "#FFFFFF"}}
def _raw(w, u, m): return w * W_WORLD + u * W_UK + m * W_MASTERS


_NON_PLAYER = {"snooker", "championship", "masters", "crown"}
_COUNTRY_WORDS = {"England", "Scotland", "Wales", "Northern Ireland", "Republic of Ireland",
                  "China", "Australia", "Belgium", "Hong Kong", "Thailand", "Canada",
                  "Malta", "Germany", "Norway", "South Africa", "Ireland"}


def _winner(cell: str):
    """Primer enlace de jugador en la celda (el campeón va primero)."""
    for m in re.findall(r'title="([^"]+)"', cell):
        n = html.unescape(m).split(" (")[0].strip()
        if (n and not n[0].isdigit() and n not in _COUNTRY_WORDS and len(n) > 3
                and not any(w in n.lower() for w in _NON_PLAYER)):
            return n
    return None


def _parse_grid(page_html: str) -> dict:
    """{jugador: {'W','UK','M'}} desde la parrilla temporada×evento (Season|UK|Masters|World)."""
    tabs = re.findall(r"<table[^>]*wikitable[^>]*>.*?</table>", page_html, re.S)
    grid = None
    for t in tabs:
        heads = " ".join(re.sub(r"<[^>]+>", "", h) for h in re.findall(r"<th[^>]*>(.*?)</th>", t, re.S)[:6])
        if "Season" in heads and "Masters" in heads and "World" in heads and "UK" in heads:
            grid = t; break
    if grid is None:
        return {}
    counts: dict[str, dict] = {}
    def bump(name, key):
        if name:
            counts.setdefault(name, {"W": 0, "UK": 0, "M": 0})[key] += 1
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", grid, re.S):
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)
        if len(cells) < 4:
            continue
        season = re.sub(r"<[^>]+>", "", cells[0]).strip()
        if not re.search(r"\d{4}", season):
            continue
        bump(_winner(cells[1]), "UK")
        bump(_winner(cells[2]), "M")
        bump(_winner(cells[3]), "W")
    return counts


def fetch_triple_crown(ttl_h: float = 24.0) -> dict:
    """{jugador: {'W','UK','M'}} de Triple Corona. Cachea; si el fetch falla, usa caché."""
    cache = CACHE / "snooker_triple_crown.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime) / 3600 < ttl_h:
        return json.loads(cache.read_text())
    try:
        req = urllib.request.Request(TC_SOURCE, headers={"User-Agent": "Hermes/1.0 (data pipeline)"})
        h = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
        counts = _parse_grid(h)
        if counts:
            cache.write_text(json.dumps(counts, ensure_ascii=False))
            return counts
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] snooker fetch {TC_SOURCE}: {e}")
    if cache.exists():
        return json.loads(cache.read_text())
    return {}


def _note_for(name, w, u, m):
    if name in NOTE:
        return NOTE[name]
    parts = []
    if w: parts.append(f"{w} Mundial{'es' if w != 1 else ''}")
    if u: parts.append(f"{u} UK")
    if m: parts.append(f"{m} Masters")
    return "Triple Corona: " + " · ".join(parts) + "." if parts else "Campeón de Triple Corona."


def build(tc: dict, limit: int = 14):
    max_raw = max((_raw(v["W"], v["UK"], v["M"]) for v in tc.values()), default=1.0) or 1.0

    def legend_score(name):
        v = tc.get(name)
        return round(_raw(v["W"], v["UK"], v["M"]) / max_raw * 100, 1) if v else 0.0

    # Ranking de forma (curado); legendScore de cada uno desde el palmarés real.
    ranking = []
    for i, (name, c, age, nivel, note) in enumerate(CURRENT):
        row = _base(name, c)
        row.update({"rank": i + 1, "age": age, "activeScore": nivel,
                    "legendScore": legend_score(name), "note": note})
        ranking.append(row)

    # Leyendas = TODOS los ganadores de Triple Corona, ordenados por score.
    legends = []
    for name, v in tc.items():
        w, u, m = v["W"], v["UK"], v["M"]
        c = COUNTRY.get(name, "")
        active = name in CURRENT_NAMES
        row = _base(name, c)
        row.update({"era": "en activo" if active else "—",
                    "worldTitles": w, "ukTitles": u, "mastersTitles": m,
                    "legendScore": round(_raw(w, u, m) / max_raw * 100, 1),
                    "note": f"{w} Mundial{'es' if w != 1 else ''} · {u} UK · {m} Masters. {_note_for(name, w, u, m)}",
                    "active": active})
        legends.append(row)
    legends.sort(key=lambda r: (-r["legendScore"], r["name"]))
    legends = legends[:limit]
    for i, row in enumerate(legends):
        row["rank"] = i + 1
    return [{"id": "main", "label": "Individual", "RANKING": ranking, "LEGENDS": legends}]


def build_prospects(disciplines, cutoff=AGE_CUTOFF, limit=6):
    """Cantera automática: los más jóvenes del ranking (≤cutoff), sin curar."""
    multi = len(disciplines) > 1
    pool = []
    for d in disciplines:
        for p in d.get("RANKING", []):
            if p.get("age") and p["age"] <= cutoff:
                q = dict(p)
                if multi:
                    q["discipline"] = d["label"]
                pool.append(q)
    pool.sort(key=lambda x: (x["age"], -x.get("activeScore", 0)))
    out = pool[:limit]
    for i, p in enumerate(out):
        p["rank"] = i + 1
    return out


LAST_TOURNAMENT = {"name": "Campeonato del Mundo", "level": "Triple Corona", "location": "Crucible, Sheffield",
                   "end": "2026-05-04", "champions": [("Zhao Xintong", "CHN", "Individual")]}
NEXT_TOURNAMENT = {"name": "UK Championship", "level": "Triple Corona", "location": "York",
                   "start": "2026-11-28", "end": "2026-12-06", "defending": "Judd Trump",
                   "favorites": [("Judd Trump", "ENG"), ("Ronnie O'Sullivan", "ENG"),
                                 ("Zhao Xintong", "CHN"), ("Kyren Wilson", "ENG"), ("Mark Selby", "ENG")]}


def _tour(t, today, kind):
    out = {"name": t["name"], "level": t["level"], "location": t["location"]}
    if kind == "last":
        out["endLabel"] = date.fromisoformat(t["end"]).strftime("%d %b %Y")
        out["champions"] = [{**_base(n, c), "discipline": disc} for n, c, disc in t["champions"]]
    else:
        s, e = date.fromisoformat(t["start"]), date.fromisoformat(t["end"])
        out.update({"startLabel": s.strftime("%d %b"), "endLabel": e.strftime("%d %b"),
                    "daysToStart": max(0, (s - today).days), "defending": t["defending"],
                    "favorites": [_base(n, c) for n, c in t["favorites"]]})
    return out


def main():
    today = date.today()
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    tc = fetch_triple_crown()
    disciplines = build(tc)
    payload = {"UPDATED": updated, "SEASON": "Temporada 2025/26",
               "SOURCE": {"name": "Palmarés real (Wikipedia: Triple Corona snooker)",
                          "note": "Títulos de Mundial + UK + Masters descargados y contados automáticamente; ranking de forma curado."},
               "LAST_TOURNAMENT": _tour(LAST_TOURNAMENT, today, "last"),
               "NEXT_TOURNAMENT": _tour(NEXT_TOURNAMENT, today, "next"),
               "DISCIPLINES": disciplines, "PROSPECTS": build_prospects(disciplines),
               "IMPORTANCE": 7.0}
    OUT.write_text(f"// Auto-generated {updated}\nwindow.SNOOKER_DATA = "
                   f"{json.dumps(payload, ensure_ascii=False, indent=2)};\n", encoding="utf-8")
    L = payload["DISCIPLINES"][0]
    print(f"Wrote {OUT.name} · {len(tc)} campeones Triple Corona · "
          f"leyenda nº1 {L['LEGENDS'][0]['name']} ({L['LEGENDS'][0]['legendScore']})")


if __name__ == "__main__":
    main()
