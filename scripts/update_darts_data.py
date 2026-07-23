#!/usr/bin/env python3
"""Dardos (PDC): leyendas por palmarés REAL descargado (no a mano) + ranking de forma.

El score leyenda sale del recuento AUTOMÁTICO de títulos mundiales (PDC + BDO)
leído de Wikipedia — todos los que califican, con sus títulos reales, recalculado
en cada ejecución. Los metadatos descriptivos (país, era, frase) son estables y
curados; lo que decide el ranking (los títulos) es fehaciente y automático.

El ranking de forma actual (Nivel) sigue curado: no hay feed abierto del Order of
Merit; se actualiza aparte.
"""
from __future__ import annotations
import json, re, html, time, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "darts_data.js"
CACHE = ROOT / ".sports_cache"; CACHE.mkdir(exist_ok=True)

CC2 = {"ENG": "gb-eng", "SCO": "gb-sct", "WAL": "gb-wls", "NIR": "gb-nir",
       "NED": "nl", "AUS": "au", "BEL": "be", "GER": "de", "AUT": "at", "CAN": "ca", "USA": "us"}
COLORS = {"ENG": "#CE1124", "SCO": "#005EB8", "WAL": "#C8102E", "NIR": "#009A44",
          "NED": "#AE1C28", "AUS": "#00008B", "BEL": "#000000", "GER": "#000000",
          "AUT": "#ED2939", "CAN": "#FF0000", "USA": "#B22234"}
_COUNTRIES = {"England", "Scotland", "Wales", "Northern Ireland", "Republic of Ireland",
              "Australia", "Canada", "United States", "Belgium", "Germany", "Austria",
              "Finland", "Sweden", "Poland", "Latvia", "Gibraltar", "Netherlands"}

WORLD_SOURCES = ["https://en.wikipedia.org/wiki/PDC_World_Darts_Championship",
                 "https://en.wikipedia.org/wiki/BDO_World_Darts_Championship"]


def flag(c): x = CC2.get(c, ""); return f"https://flagcdn.com/24x18/{x}.png" if x else ""
def _slug(n): return re.sub(r"[^a-z0-9]+", "_", n.lower()).strip("_")
def _base(name, c):
    col = COLORS.get(c, "#4A4745")
    return {"id": _slug(name), "name": name, "country": c, "logo": flag(c),
            "colors": {"primary": col, "secondary": "#FFFFFF"}}


def _parse_champions(page_html: str) -> dict:
    """Cuenta ganadores de la tabla de finales (la que tiene columna 'Runner-up')."""
    from collections import Counter
    counts = Counter()
    for t in re.findall(r"<table[^>]*wikitable[^>]*>.*?</table>", page_html, re.S):
        if "unner" not in t:
            continue
        for row in re.findall(r"<tr[^>]*>.*?</tr>", t, re.S):
            if not re.search(r">\s*(19|20)\d{2}\b", row):
                continue
            names = [html.unescape(m).split(" (")[0].strip() for m in re.findall(r'title="([^"]+)"', row)]
            win = [n for n in names if n and not n[0].isdigit() and n not in _COUNTRIES and len(n) > 3]
            if win:
                counts[win[0]] += 1
        break
    return dict(counts)


def fetch_world_titles(ttl_h: float = 24.0) -> dict:
    """{jugador: títulos mundiales totales}. Cachea; si el fetch falla, usa caché."""
    cache = CACHE / "darts_world_titles.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime) / 3600 < ttl_h:
        return json.loads(cache.read_text())
    from collections import Counter
    total = Counter()
    ok = False
    for url in WORLD_SOURCES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0 (data pipeline)"})
            h = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
            total.update(_parse_champions(h)); ok = True
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] darts fetch {url}: {e}")
    if ok:
        cache.write_text(json.dumps(dict(total), ensure_ascii=False))
        return dict(total)
    if cache.exists():
        return json.loads(cache.read_text())
    return {}


# Metadatos estables (país, era, frase) de los grandes; los TÍTULOS vienen del fetch.
LEGEND_META = {
    "Phil Taylor": ("ENG", "1990-2018", "'The Power': un dominio que jamás se repetirá."),
    "Raymond van Barneveld": ("NED", "1998-2019", "Cinco Mundiales entre BDO y PDC; ídolo de masas."),
    "Eric Bristow": ("ENG", "1980-1986", "'Crafty Cockney': la primera superestrella del dardo."),
    "John Lowe": ("ENG", "1979-1993", "Tres Mundiales en tres décadas distintas."),
    "Michael van Gerwen": ("NED", "2013-presente", "'Mighty Mike': la máquina más consistente de la era moderna."),
    "John Part": ("CAN", "1994-2008", "Primer campeón mundial no británico."),
    "Martin Adams": ("ENG", "2007-2011", "'Wolfie': el gran referente del BDO."),
    "Glen Durrant": ("ENG", "2017-2019", "Triple campeón BDO consecutivo."),
    "Dennis Priestley": ("ENG", "1991-1997", "El primer campeón de la era PDC."),
    "Adrian Lewis": ("ENG", "2011-2012", "'Jackpot': bicampeón mundial consecutivo."),
    "Gary Anderson": ("SCO", "2015-2016", "'The Flying Scotsman': dos Mundiales seguidos."),
    "Peter Wright": ("SCO", "2020-2022", "'Snakebite': colorido y letal en su mejor momento."),
    "Luke Humphries": ("ENG", "2024-presente", "'Cool Hand Luke': la nueva referencia del circuito."),
    "Luke Littler": ("ENG", "2025-presente", "Fenómeno adolescente que revolucionó el deporte."),
    "Bob Anderson": ("ENG", "1988", "Campeón del mundo BDO en su mejor año."),
    "Ted Hankey": ("ENG", "2000-2009", "'The Count': dos coronas del BDO."),
    "Scott Waddell": ("ENG", "2007", "Campeón del BDO."),
}

# Ranking de forma actual (curado; sin feed abierto del Order of Merit).
# (nombre, cc3, edad, nivel, nota) — la edad es un dato factual, alimenta la cantera.
CURRENT = [
    ("Luke Humphries", "ENG", 31, 100, "Nº1 del Order of Merit"),
    ("Luke Littler", "ENG", 19, 99, "Bicampeón del mundo siendo adolescente"),
    ("Michael van Gerwen", "NED", 37, 92, "Tricampeón del mundo, aún en la élite"),
    ("Michael Smith", "ENG", 36, 86, "Campeón del mundo 2023"),
    ("Gerwyn Price", "WAL", 41, 84, "Campeón del mundo 2021"),
    ("Nathan Aspinall", "ENG", 35, 80, "Ganador de World Matchplay"),
    ("Rob Cross", "ENG", 36, 79, "Campeón del mundo 2018"),
    ("Stephen Bunting", "ENG", 41, 77, "Top del Order of Merit"),
]
CURRENT_CC = {name: cc for name, cc, *_ in CURRENT}
AGE_CUTOFF = 23  # cantera: los del top actual con esta edad o menos

LAST_TOURNAMENT = {"name": "World Matchplay", "level": "Major televisado", "location": "Blackpool",
                   "end": "2026-07-19", "champions": [("Luke Humphries", "ENG", "Individual")]}
NEXT_TOURNAMENT = {"name": "Campeonato del Mundo PDC", "level": "Mundial", "location": "Alexandra Palace, Londres",
                   "start": "2026-12-17", "end": "2027-01-03", "defending": "Luke Littler",
                   "favorites": [("Luke Humphries", "ENG"), ("Luke Littler", "ENG"),
                                 ("Michael van Gerwen", "NED"), ("Gerwyn Price", "WAL"), ("Michael Smith", "ENG")]}


def build(titles: dict):
    max_t = max(titles.values()) if titles else 1
    active_names = {n for n, *_ in CURRENT}

    ranking = []
    for i, (name, cc, age, nivel, note) in enumerate(CURRENT):
        t = titles.get(name, 0)
        row = _base(name, cc)
        row.update({"rank": i + 1, "age": age, "activeScore": nivel,
                    "legendScore": round(t / max_t * 100, 1), "note": note})
        ranking.append(row)

    legends = []
    for name, t in sorted(titles.items(), key=lambda kv: -kv[1]):
        cc, era, note = LEGEND_META.get(name, (CURRENT_CC.get(name, ""), "—", "Campeón del mundo."))
        row = _base(name, cc)
        active = name in active_names
        row.update({"era": ("en activo" if active and cc == CURRENT_CC.get(name) else era),
                    "worldTitles": t, "legendScore": round(t / max_t * 100, 1),
                    "note": f"{t} Mundial{'es' if t != 1 else ''}. {note}", "active": active})
        legends.append(row)
    legends = legends[:14]
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
    titles = fetch_world_titles()
    disciplines = build(titles)
    payload = {"UPDATED": updated, "SEASON": "PDC 2026",
               "SOURCE": {"name": "Palmarés real (Wikipedia: campeones PDC + BDO)",
                          "note": "Títulos descargados y contados automáticamente; ranking de forma curado."},
               "LAST_TOURNAMENT": _tour(LAST_TOURNAMENT, today, "last"),
               "NEXT_TOURNAMENT": _tour(NEXT_TOURNAMENT, today, "next"),
               "DISCIPLINES": disciplines, "PROSPECTS": build_prospects(disciplines),
               "IMPORTANCE": 7.0}
    OUT.write_text(f"// Auto-generated {updated}\nwindow.DARTS_DATA = "
                   f"{json.dumps(payload, ensure_ascii=False, indent=2)};\n", encoding="utf-8")
    L = payload["DISCIPLINES"][0]
    print(f"Wrote {OUT.name} · {len(titles)} campeones · leyenda nº1 {L['LEGENDS'][0]['name']} ({L['LEGENDS'][0]['worldTitles']} Mundiales)")


if __name__ == "__main__":
    main()
