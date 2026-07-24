#!/usr/bin/env python3
"""Tenis de mesa: leyendas por palmarés REAL descargado + ranking de forma.

Las leyendas y su score salen del recuento AUTOMÁTICO de títulos de individual
(oro olímpico + Mundial + Copa del Mundo) leídos de Wikipedia — todos los que
califican, con sus títulos reales, recalculado en cada ejecución. La columna
"Gold" se localiza por su cabecera (las tablas tienen distinto nº de columnas) y
se filtran los enlaces de país para quedarnos con el jugador.

El ranking de forma actual (Nivel) sigue curado: no hay feed abierto del ranking
WTT. Metadatos descriptivos (país, era, frase) estables; los títulos, fehacientes.

Leyenda (0-100): oro olímpico ×12 + Mundial ×7 + Copa del Mundo ×3 (individual),
normalizado a 100 = mejor de la modalidad.
"""
from __future__ import annotations
import json, re, html, time, urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tabletennis_data.js"
CACHE = ROOT / ".sports_cache"; CACHE.mkdir(exist_ok=True)
W_OLY, W_WORLD, W_WC = 12.0, 7.0, 3.0
AGE_CUTOFF = 23  # cantera: los del top actual con esta edad o menos

SOURCES = {
    "world": "https://en.wikipedia.org/wiki/List_of_World_Table_Tennis_Championships_medalists",
    "oly": "https://en.wikipedia.org/wiki/List_of_Olympic_medalists_in_table_tennis",
    "wc": "https://en.wikipedia.org/wiki/Table_Tennis_World_Cup",
}

CC2 = {"CHN": "cn", "SWE": "se", "JPN": "jp", "KOR": "kr", "GER": "de", "FRA": "fr",
       "BRA": "br", "TPE": "tw", "HKG": "hk", "SGP": "sg", "HUN": "hu", "ROU": "ro",
       "AUT": "at", "CZE": "cz", "ENG": "gb-eng"}
COLORS = {"CHN": "#DE2910", "SWE": "#006AA7", "JPN": "#BC002D", "KOR": "#003478",
          "GER": "#000000", "FRA": "#002395", "BRA": "#009C3B", "TPE": "#000095",
          "HKG": "#DE2910", "SGP": "#EF3340", "HUN": "#436F4D", "ROU": "#002B7F",
          "AUT": "#ED2939", "CZE": "#11457E", "ENG": "#CE1124"}

# País por jugador (dato estable). Para quien falte, sin bandera.
COUNTRY = {
    "Ma Long": "CHN", "Fan Zhendong": "CHN", "Zhang Jike": "CHN", "Ma Lin": "CHN",
    "Liu Guoliang": "CHN", "Kong Linghui": "CHN", "Wang Liqin": "CHN", "Wang Hao": "CHN",
    "Zhuang Zedong": "CHN", "Xu Xin": "CHN", "Lin Shidong": "CHN", "Wang Chuqin": "CHN",
    "Jan-Ove Waldner": "SWE", "Truls Möregårdh": "SWE", "Jörgen Persson": "SWE",
    "Stellan Bengtsson": "SWE", "Viktor Barna": "HUN", "Miklós Szabados": "HUN",
    "Ferenc Sidó": "HUN", "Richard Bergmann": "AUT", "Bohumil Váňa": "CZE",
    "Ichiro Ogimura": "JPN", "Tomokazu Harimoto": "JPN", "Hugo Calderano": "BRA",
    "Felix Lebrun": "FRA", "Jean-Philippe Gatien": "FRA", "Ryu Seung-min": "KOR",
    "Yoo Nam-kyu": "KOR", "Johnny Leach": "ENG", "Hiroji Satoh": "JPN",
    "Zhang Yining": "CHN", "Deng Yaping": "CHN", "Wang Nan": "CHN", "Ding Ning": "CHN",
    "Chen Meng": "CHN", "Sun Yingsha": "CHN", "Liu Shiwen": "CHN", "Li Xiaoxia": "CHN",
    "Guo Yue": "CHN", "Wang Manyu": "CHN", "Wang Yidi": "CHN", "Chen Xingtong": "CHN",
    "Cao Yanhua": "CHN", "Qiao Hong": "CHN", "Angelica Rozeanu": "ROU",
    "Mária Mednyánszky": "HUN", "Anna Sipos": "HUN", "Gizella Farkas": "HUN",
    "Marie Kettnerová": "CZE", "Hina Hayata": "JPN", "Mima Ito": "JPN",
    "Kimiyo Matsuzaki": "JPN", "Shin Yubin": "KOR", "Hyun Jung-hwa": "KOR",
    "Lin Huiqing": "CHN",
}
# Frases curadas para los grandes (estable). Para el resto, se genera con los conteos.
NOTE = {
    "Ma Long": "El GOAT: doble oro olímpico y Grand Slam completo.",
    "Fan Zhendong": "Oro olímpico 2024 y dominador de la Copa del Mundo.",
    "Jan-Ove Waldner": "'El Mozart': el europeo que dominó a China.",
    "Zhang Jike": "Grand Slam en tiempo récord (445 días).",
    "Wang Liqin": "Triple campeón del mundo individual.",
    "Viktor Barna": "Cinco Mundiales en los años 30; leyenda fundacional.",
    "Zhang Yining": "Doble oro olímpico y récord de Copas del Mundo.",
    "Deng Yaping": "La reina: doble oro olímpico y dominio absoluto.",
    "Wang Nan": "Grand Slam y triple campeona del mundo.",
    "Ding Ning": "Grand Slam y triple campeona del mundo.",
    "Angelica Rozeanu": "Seis Mundiales seguidos (1950-1955): dominio histórico.",
    "Chen Meng": "Bicampeona olímpica individual consecutiva (2020, 2024).",
    "Li Xiaoxia": "Oro olímpico 2012 y Grand Slam.",
    "Liu Shiwen": "'La reina de la Copa del Mundo': cinco títulos.",
}


def flag(c): x = CC2.get(c, ""); return f"https://flagcdn.com/24x18/{x}.png" if x else ""
def _slug(n): return re.sub(r"[^a-z0-9]+", "_", n.lower()).strip("_")
def _base(name, c):
    col = COLORS.get(c, "#4A4745")
    return {"id": _slug(name), "name": name, "country": c, "logo": flag(c),
            "colors": {"primary": col, "secondary": "#FFFFFF"}}
def _raw(o, w, wc): return o * W_OLY + w * W_WORLD + wc * W_WC


_NATION = re.compile(
    r'\b(China|Japan|Hungary|England|Sweden|Czechoslovakia|Romania|Germany|Austria|'
    r'France|Korea|Yugoslavia|United States|Poland|India|Chinese Taipei|Hong Kong|'
    r'Croatia|Belgium|North Korea|South Korea|Wales|Scotland|Nigeria|Egypt|Denmark|'
    r'Netherlands|Russia|Soviet|Chinese|Kingdom of|Republic of|West Germany|Czech)')


def _player(cell: str):
    """Primer enlace que no es país (el jugador va tras la bandera del país)."""
    for m in re.findall(r'title="([^"]+)"', cell):
        n = html.unescape(m).split(" (")[0].strip()
        if n and not _NATION.search(n) and not n[0].isdigit() and len(n) > 3:
            return n
    return None


def _gold_idx(table: str):
    hrow = re.search(r"<tr[^>]*>(.*?)</tr>", table, re.S).group(1)
    heads = [re.sub(r"<[^>]+>", "", html.unescape(x)).strip().lower()
             for x in re.findall(r"<th[^>]*>(.*?)</th>", hrow, re.S)]
    return heads.index("gold") if "gold" in heads else None


def _count(page_html: str):
    """{'m': {player: golds}, 'w': {player: golds}} de las secciones '* singles'."""
    res = {"m": defaultdict(int), "w": defaultdict(int)}
    sec = ""
    for chunk in re.split(r'(<h[234][^>]*>.*?</h[234]>)', page_html, flags=re.S):
        hm = re.match(r'<h[234][^>]*>(.*?)</h[234]>', chunk, re.S)
        if hm:
            sec = re.sub(r"<[^>]+>", "", html.unescape(hm.group(1))).replace("[edit]", "").strip().lower()
            continue
        tab = re.search(r"<table[^>]*wikitable[^>]*>.*?</table>", chunk, re.S)
        if not tab or "singles" not in sec:
            continue
        g = "w" if "women" in sec else ("m" if "men" in sec else None)
        if not g:
            continue
        t = tab.group(0)
        gi = _gold_idx(t)
        if gi is None:
            continue
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
            cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)
            if len(cells) <= gi or not re.search(r"\b(19|20)\d{2}\b", re.sub(r"<[^>]+>", "", cells[0])):
                continue
            p = _player(cells[gi])
            if p:
                res[g][p] += 1
    return res


def fetch_titles(ttl_h: float = 24.0):
    """{'m'/'w': {player: {'o','w','wc'}}}. Cachea; si el fetch falla, usa caché."""
    cache = CACHE / "tabletennis_titles.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime) / 3600 < ttl_h:
        return json.loads(cache.read_text())
    got = {}
    ok = True
    for key, url in SOURCES.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0 (data pipeline)"})
            h = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
            got[key] = _count(h)
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] tabletennis fetch {url}: {e}"); ok = False
    if ok:
        out = {"m": {}, "w": {}}
        for g in ("m", "w"):
            names = set()
            for key in SOURCES:
                names |= set(got[key][g])
            for n in names:
                out[g][n] = {"o": got["oly"][g].get(n, 0), "w": got["world"][g].get(n, 0),
                             "wc": got["wc"][g].get(n, 0)}
        cache.write_text(json.dumps(out, ensure_ascii=False))
        return out
    if cache.exists():
        return json.loads(cache.read_text())
    return {"m": {}, "w": {}}


# ── Ranking de forma actual (curado; sin feed abierto del ranking WTT) ────────
# (nombre, cc3, edad, nivel, nota) — la edad alimenta la cantera automática.
DISCIPLINES_META = [
    {"id": "ms", "label": "Individual Masculino", "gender": "m", "current": [
        ("Lin Shidong", "CHN", 20, 100, "Nº1 del ranking mundial"),
        ("Wang Chuqin", "CHN", 25, 97, "Campeón olímpico de dobles mixtos 2024"),
        ("Fan Zhendong", "CHN", 28, 95, "Campeón olímpico individual 2024"),
        ("Ma Long", "CHN", 37, 90, "El más grande de todos los tiempos"),
        ("Truls Möregårdh", "SWE", 23, 87, "Plata olímpica individual 2024"),
        ("Tomokazu Harimoto", "JPN", 22, 85, "Referente japonés"),
        ("Hugo Calderano", "BRA", 29, 83, "El mejor de la historia fuera de Asia/Europa"),
        ("Felix Lebrun", "FRA", 19, 81, "Fenómeno francés adolescente"),
    ]},
    {"id": "ws", "label": "Individual Femenino", "gender": "w", "current": [
        ("Sun Yingsha", "CHN", 25, 100, "Nº1 del mundo"),
        ("Wang Manyu", "CHN", 26, 96, "Múltiple campeona por equipos"),
        ("Chen Meng", "CHN", 31, 93, "Bicampeona olímpica individual (2020, 2024)"),
        ("Hina Hayata", "JPN", 25, 88, "Medallista olímpica"),
        ("Wang Yidi", "CHN", 28, 85, "Top del ranking mundial"),
        ("Mima Ito", "JPN", 25, 83, "Prodigio japonés"),
        ("Shin Yubin", "KOR", 21, 81, "Estrella coreana emergente"),
        ("Chen Xingtong", "CHN", 28, 79, "Podio mundial constante"),
    ]},
]

LAST_TOURNAMENT = {"name": "WTT US Smash", "level": "Grand Smash", "location": "Las Vegas",
                   "end": "2026-07-12", "champions": [("Lin Shidong", "CHN", "Individual Masculino"),
                                                       ("Sun Yingsha", "CHN", "Individual Femenino")]}
NEXT_TOURNAMENT = {"name": "WTT China Smash", "level": "Grand Smash", "location": "Pekín",
                   "start": "2026-09-25", "end": "2026-10-04", "defending": "Wang Chuqin (M) · Sun Yingsha (F)",
                   "favorites": [("Lin Shidong", "CHN"), ("Wang Chuqin", "CHN"), ("Sun Yingsha", "CHN"),
                                 ("Fan Zhendong", "CHN"), ("Hina Hayata", "JPN")]}


def _note_for(name, o, w, wc):
    base = (f"{o} oro{'s' if o != 1 else ''} olímpico{'s' if o != 1 else ''} · "
            f"{w} Mundial{'es' if w != 1 else ''} · {wc} Copa del Mundo.")
    return f"{base} {NOTE[name]}" if name in NOTE else base


def build_discipline(meta, titles, limit=10):
    T = titles.get(meta["gender"], {})
    max_raw = max((_raw(v["o"], v["w"], v["wc"]) for v in T.values()), default=1.0) or 1.0
    current_names = {n for n, *_ in meta["current"]}

    def legend_score(name):
        v = T.get(name)
        return round(_raw(v["o"], v["w"], v["wc"]) / max_raw * 100, 1) if v else 0.0

    ranking = []
    for i, (name, c, age, nivel, note) in enumerate(meta["current"]):
        row = _base(name, c)
        row.update({"rank": i + 1, "age": age, "activeScore": nivel,
                    "legendScore": legend_score(name), "note": note})
        ranking.append(row)

    legends = []
    for name, v in T.items():
        o, w, wc = v["o"], v["w"], v["wc"]
        c = COUNTRY.get(name, "")
        active = name in current_names
        row = _base(name, c)
        row.update({"era": "en activo" if active else "—",
                    "olympicGold": o, "worldTitles": w, "worldCups": wc,
                    "legendScore": round(_raw(o, w, wc) / max_raw * 100, 1),
                    "note": _note_for(name, o, w, wc), "active": active})
        legends.append(row)
    legends.sort(key=lambda r: (-r["legendScore"], r["name"]))
    legends = legends[:limit]
    for i, row in enumerate(legends):
        row["rank"] = i + 1
    return {"id": meta["id"], "label": meta["label"], "RANKING": ranking, "LEGENDS": legends}


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
    titles = fetch_titles()
    disciplines = [build_discipline(m, titles) for m in DISCIPLINES_META]
    payload = {"UPDATED": updated, "SEASON": "WTT 2026",
               "SOURCE": {"name": "Palmarés real (Wikipedia: oro olímpico + Mundial + Copa del Mundo, individual)",
                          "note": "Títulos descargados y contados automáticamente; ranking de forma curado."},
               "LAST_TOURNAMENT": _tour(LAST_TOURNAMENT, today, "last"),
               "NEXT_TOURNAMENT": _tour(NEXT_TOURNAMENT, today, "next"),
               "DISCIPLINES": disciplines, "PROSPECTS": build_prospects(disciplines),
               "IMPORTANCE": 7.5}
    OUT.write_text(f"// Auto-generated {updated}\nwindow.TABLETENNIS_DATA = "
                   f"{json.dumps(payload, ensure_ascii=False, indent=2)};\n", encoding="utf-8")
    for d in payload["DISCIPLINES"]:
        print(f"  {d['label']}: nº1 {d['RANKING'][0]['name']} · "
              f"leyenda {d['LEGENDS'][0]['name']} ({d['LEGENDS'][0]['legendScore']})")


if __name__ == "__main__":
    main()
