#!/usr/bin/env python3
"""Bádminton: leyendas por palmarés (parte fehaciente + parte estable) + ranking.

Componentes del score de leyenda:
  - Oro olímpico (×12) y Mundial (×9): DESCARGADOS y contados automáticamente de
    Wikipedia (medallistas olímpicos + Mundiales BWF), individual M/F. La columna
    Gold se localiza por cabecera y se filtran los enlaces de país.
  - All England (×3) y semanas nº1 (×0.04): datos históricos ESTABLES (curados).
    No hay tabla limpia: All England usa rowspans en rachas y las semanas nº1 no
    están tabuladas. Cambian como mucho una vez al año.

La LISTA de leyendas se completa sola con todos los campeones olímpicos/mundiales
descargados; a los grandes se les añade su All England y semanas nº1 estables, y a
quienes brillaron sin oro (Lee Chong Wei, Tai Tzu-ying, Rudy Hartono) los sostiene
esa parte. El ranking de forma (Nivel) sigue curado.

Leyenda (0-100): oro olímpico ×12 + Mundial ×9 + All England ×3 + semanas nº1 ×0.04,
normalizado a 100 = mejor de la modalidad.
"""
from __future__ import annotations
import json, re, html, time, urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "badminton_data.js"
CACHE = ROOT / ".sports_cache"; CACHE.mkdir(exist_ok=True)
W_OLY, W_WORLD, W_AE, W_WEEKS = 12.0, 9.0, 3.0, 0.04
AGE_CUTOFF = 23  # cantera: los del top actual con esta edad o menos

SOURCES = {
    "oly": "https://en.wikipedia.org/wiki/List_of_Olympic_medalists_in_badminton",
    "world": "https://en.wikipedia.org/wiki/List_of_BWF_World_Championships_medalists",
}

CC2 = {
    "CHN": "cn", "DEN": "dk", "JPN": "jp", "KOR": "kr", "THA": "th", "INA": "id",
    "MAS": "my", "TPE": "tw", "ESP": "es", "IND": "in", "SGP": "sg", "ENG": "gb-eng",
    "GBR": "gb", "HKG": "hk", "FRA": "fr", "GER": "de", "VIE": "vn",
}
COLORS = {
    "CHN": "#DE2910", "DEN": "#C60C30", "JPN": "#BC002D", "KOR": "#003478",
    "THA": "#A51931", "INA": "#CE1126", "MAS": "#CC0001", "TPE": "#000095",
    "ESP": "#AA151B", "IND": "#FF9933", "SGP": "#EF3340", "ENG": "#CE1124",
    "HKG": "#DE2910", "FRA": "#002395", "GER": "#000000", "VIE": "#DA251D",
}

# País por jugador (estable). Para campeones descargados sin ficha, sin bandera.
COUNTRY = {
    "Lin Dan": "CHN", "Viktor Axelsen": "DEN", "Lee Chong Wei": "MAS", "Rudy Hartono": "INA",
    "Chen Long": "CHN", "Taufik Hidayat": "INA", "Kento Momota": "JPN", "Morten Frost": "DEN",
    "Yang Yang": "CHN", "Ji Xinpeng": "CHN", "Alan Budikusuma": "INA", "Poul-Erik Høyer Larsen": "DEN",
    "Sun Jun": "CHN", "Zhao Jianhua": "CHN", "Han Jian": "CHN", "Flemming Delfs": "DEN",
    "Prakash Padukone": "IND", "Erland Kops": "DEN", "Loh Kean Yew": "SGP", "Kunlavut Vitidsarn": "THA",
    "Anders Antonsen": "DEN", "Shi Yuqi": "CHN", "Hans-Kristian Solberg Vittinghus": "DEN",
    "Carolina Marín": "ESP", "Tai Tzu-ying": "TPE", "Zhang Ning": "CHN", "Susi Susanti": "INA",
    "Li Xuerui": "CHN", "Wang Yihan": "CHN", "Ratchanok Intanon": "THA", "P. V. Sindhu": "IND",
    "Akane Yamaguchi": "JPN", "An Se-young": "KOR", "Ye Zhaoying": "CHN", "Xie Xingfang": "CHN",
    "Han Aiping": "CHN", "Li Lingwei": "CHN", "Gong Zhichao": "CHN", "Bang Soo-hyun": "KOR",
    "Chen Yufei": "CHN", "Gong Ruina": "CHN", "Zhou Mi": "CHN", "Camilla Martin": "DEN",
    "Nozomi Okuhara": "JPN", "Pusarla Venkata Sindhu": "IND",
}

# Fichas estables de los grandes: (género, era, All England, semanas nº1, frase).
# Oro olímpico y Mundial NO van aquí: se descargan. Para quien no esté, ae=0,weeks=0.
LEGEND_INFO = {
    "Lin Dan": ("m", "2004-2016", 6, 200, "'Super Dan': el más grande de la historia."),
    "Viktor Axelsen": ("m", "2016-presente", 1, 130, "La era danesa; dominador actual."),
    "Lee Chong Wei": ("m", "2006-2018", 4, 349, "349 semanas nº1: el mejor sin un gran oro."),
    "Rudy Hartono": ("m", "1968-1976", 8, 0, "Récord de ocho All England, siete consecutivos."),
    "Chen Long": ("m", "2014-2017", 0, 60, "Oro olímpico 2016 y doble campeón del mundo."),
    "Taufik Hidayat": ("m", "2004-2007", 0, 40, "Oro olímpico 2004 con un revés legendario."),
    "Kento Momota": ("m", "2018-2020", 0, 100, "Doble campeón del mundo y récord de victorias."),
    "Morten Frost": ("m", "1982-1988", 4, 30, "Dominó los 80 con cuatro All England pese a no ganar el Mundial."),
    "Prakash Padukone": ("m", "1980-1981", 1, 0, "El pionero indio; All England 1980."),
    "Carolina Marín": ("w", "2014-2021", 1, 60, "Oro olímpico 2016 y triple campeona del mundo; intensidad única."),
    "Tai Tzu-ying": ("w", "2016-2024", 2, 214, "214 semanas nº1: la más dominante sin oro olímpico ni mundial."),
    "Zhang Ning": ("w", "2003-2008", 0, 40, "Bicampeona olímpica (2004, 2008)."),
    "Susi Susanti": ("w", "1989-1997", 4, 50, "Oro olímpico 1992 y cuatro All England; icono indonesio."),
    "Li Xuerui": ("w", "2011-2014", 1, 60, "Oro olímpico 2012 y campeona del mundo."),
    "Wang Yihan": ("w", "2010-2013", 1, 70, "Nº1 sostenida y campeona del mundo 2011."),
    "Ratchanok Intanon": ("w", "2013-2016", 0, 30, "Campeona del mundo más joven de la historia (18 años)."),
    "P. V. Sindhu": ("w", "2016-2019", 0, 10, "Campeona del mundo 2019 y doble medallista olímpica."),
    "An Se-young": ("w", "2023-presente", 1, 100, "Campeona olímpica 2024 y nº1 dominante."),
    "Akane Yamaguchi": ("w", "2021-2023", 0, 80, "Múltiple campeona del mundo; motor incansable."),
}

# Ranking de forma actual (curado). (nombre, cc3, edad, nivel, nota)
DISCIPLINES_META = [
    {"id": "ms", "label": "Individual Masculino", "gender": "m", "current": [
        ("Shi Yuqi", "CHN", 30, 100, "Nº1 del mundo"),
        ("Viktor Axelsen", "DEN", 32, 98, "Bicampeón olímpico (2021, 2024)"),
        ("Anders Antonsen", "DEN", 29, 93, "Campeón del mundo 2025"),
        ("Kunlavut Vitidsarn", "THA", 25, 90, "Campeón del mundo 2023, plata olímpica 2024"),
        ("Lee Zii Jia", "MAS", 28, 86, "Bronce olímpico 2024"),
        ("Kodai Naraoka", "JPN", 25, 83, "Subcampeón del mundo 2023"),
        ("Jonatan Christie", "INA", 29, 80, "Campeón de Asia 2024"),
        ("Loh Kean Yew", "SGP", 29, 78, "Campeón del mundo 2021"),
    ]},
    {"id": "ws", "label": "Individual Femenino", "gender": "w", "current": [
        ("An Se-young", "KOR", 24, 100, "Campeona olímpica 2024 y nº1"),
        ("Akane Yamaguchi", "JPN", 28, 95, "Múltiple campeona del mundo"),
        ("Chen Yufei", "CHN", 28, 91, "Campeona olímpica 2021"),
        ("Wang Zhiyi", "CHN", 25, 87, "Campeona de All England"),
        ("He Bingjiao", "CHN", 28, 84, "Medallista olímpica 2024"),
        ("Gregoria Mariska Tunjung", "INA", 26, 81, "Bronce mundial y de Asia"),
        ("Pornpawee Chochuwong", "THA", 27, 78, "Finalista de Grand Prix"),
        ("Ratchanok Intanon", "THA", 31, 76, "Campeona del mundo 2013"),
    ]},
]
# All England + semanas nº1 estables de los ACTIVOS del ranking (para su score leyenda).
CURRENT_EXTRA = {  # name: (allEngland, weeks)
    "Shi Yuqi": (2, 40), "Viktor Axelsen": (1, 130), "Anders Antonsen": (1, 20),
    "Kunlavut Vitidsarn": (0, 10), "Lee Zii Jia": (1, 10), "Loh Kean Yew": (0, 5),
    "An Se-young": (1, 100), "Akane Yamaguchi": (0, 80), "Chen Yufei": (1, 40),
    "Ratchanok Intanon": (0, 30), "Wang Zhiyi": (1, 10),
}

LAST_TOURNAMENT = {
    "name": "Japan Open", "level": "BWF World Tour Super 750", "location": "Tokio",
    "end": "2026-07-20",
    "champions": [("Individual Masculino", "Shi Yuqi", "CHN"), ("Individual Femenino", "An Se-young", "KOR")],
}
NEXT_TOURNAMENT = {
    "name": "Campeonato del Mundo BWF 2026", "level": "Mundial", "location": "París",
    "start": "2026-08-24", "end": "2026-08-30", "defending": "Anders Antonsen (M) · An Se-young (F)",
    "favorites": [("Shi Yuqi", "CHN"), ("Viktor Axelsen", "DEN"), ("An Se-young", "KOR"),
                  ("Akane Yamaguchi", "JPN"), ("Kunlavut Vitidsarn", "THA")],
}

_NATION = re.compile(
    r'\b(China|Indonesia|Malaysia|Denmark|Japan|Korea|South Korea|India|Thailand|'
    r'Chinese Taipei|Taiwan|England|Spain|Hong Kong|Germany|Netherlands|Sweden|Vietnam|'
    r'Singapore|United States|Chinese|Republic of|Ireland|France|Scotland|Wales|Canada|People)')


def flag(cc3): cc2 = CC2.get(cc3, ""); return f"https://flagcdn.com/24x18/{cc2}.png" if cc2 else ""
def _slug(n): return re.sub(r"[^a-z0-9]+", "_", n.lower()).strip("_")
def _base(name, cc3):
    c = COLORS.get(cc3, "#4A4745")
    return {"id": _slug(name), "name": name, "country": cc3, "logo": flag(cc3),
            "colors": {"primary": c, "secondary": "#FFFFFF"}}
def _raw(o, w, ae, weeks): return o * W_OLY + w * W_WORLD + ae * W_AE + weeks * W_WEEKS


def _player(cell: str):
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
    """{'m'/'w': {player: {'o','w'}}} de oro olímpico y Mundial. Cachea + fallback."""
    cache = CACHE / "badminton_titles.json"
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
            print(f"[WARN] badminton fetch {url}: {e}"); ok = False
    if ok:
        out = {"m": {}, "w": {}}
        for g in ("m", "w"):
            for n in set(got["oly"][g]) | set(got["world"][g]):
                out[g][n] = {"o": got["oly"][g].get(n, 0), "w": got["world"][g].get(n, 0)}
        cache.write_text(json.dumps(out, ensure_ascii=False))
        return out
    if cache.exists():
        return json.loads(cache.read_text())
    return {"m": {}, "w": {}}


def _note_for(name, o, w, ae):
    base = (f"{o} oro{'s' if o != 1 else ''} olímpico{'s' if o != 1 else ''} · "
            f"{w} Mundial{'es' if w != 1 else ''} · {ae} All England.")
    info = LEGEND_INFO.get(name)
    return f"{base} {info[4]}" if info else base


def build_discipline(meta, titles, limit=9):
    g = meta["gender"]
    T = titles.get(g, {})
    current_names = {n for n, *_ in meta["current"]}

    # Reúne a todos los que puntúan: campeones descargados (oly/world) + fichas
    # curadas de ese género (para los grandes sin oro y sus All England/semanas).
    names = set(T) | {n for n, info in LEGEND_INFO.items() if info[0] == g}

    def stats(name):
        o = T.get(name, {}).get("o", 0)
        w = T.get(name, {}).get("w", 0)
        info = LEGEND_INFO.get(name)
        ae, weeks = (info[2], info[3]) if info else (0, 0)
        return o, w, ae, weeks

    max_raw = max((_raw(*stats(n)) for n in names), default=1.0) or 1.0

    legends = []
    for name in names:
        o, w, ae, weeks = stats(name)
        info = LEGEND_INFO.get(name)
        cc = COUNTRY.get(name, "")
        active = name in current_names
        row = _base(name, cc)
        row.update({"era": "en activo" if active else (info[1] if info else "—"),
                    "olympicGold": o, "worldGold": w, "allEngland": ae, "weeksNo1": weeks,
                    "legendScore": round(_raw(o, w, ae, weeks) / max_raw * 100, 1),
                    "note": _note_for(name, o, w, ae), "active": active})
        legends.append(row)
    legends.sort(key=lambda r: (-r["legendScore"], r["name"]))
    legends = legends[:limit]
    for i, row in enumerate(legends):
        row["rank"] = i + 1

    # Ranking de forma (curado); legendScore desde fetched (o,w) + estable (ae,weeks).
    ranking = []
    for i, (name, cc3, age, nivel, note) in enumerate(meta["current"]):
        o = T.get(name, {}).get("o", 0)
        w = T.get(name, {}).get("w", 0)
        ae, weeks = CURRENT_EXTRA.get(name, (0, 0))
        row = _base(name, cc3)
        row.update({"rank": i + 1, "age": age, "activeScore": nivel,
                    "legendScore": round(_raw(o, w, ae, weeks) / max_raw * 100, 1),
                    "olympicGold": o, "worldGold": w, "allEngland": ae, "note": note})
        ranking.append(row)

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


def _champ_row(name, cc3, discipline):
    row = _base(name, cc3); row["discipline"] = discipline; return row


def build_last(today: date) -> dict:
    t = LAST_TOURNAMENT
    end = date.fromisoformat(t["end"])
    return {"name": t["name"], "level": t["level"], "location": t["location"],
            "endLabel": end.strftime("%d %b %Y"),
            "champions": [_champ_row(n, c, disc) for disc, n, c in t["champions"]]}


def build_next(today: date) -> dict:
    t = NEXT_TOURNAMENT
    start = date.fromisoformat(t["start"]); end = date.fromisoformat(t["end"])
    return {"name": t["name"], "level": t["level"], "location": t["location"],
            "startLabel": start.strftime("%d %b"), "endLabel": end.strftime("%d %b"),
            "daysToStart": max(0, (start - today).days), "defending": t["defending"],
            "favorites": [_champ_row(n, c, "") for n, c in t["favorites"]]}


def main() -> None:
    today = date.today()
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    titles = fetch_titles()
    disciplines = [build_discipline(m, titles) for m in DISCIPLINES_META]
    payload = {
        "UPDATED": updated, "SEASON": "BWF World Tour 2026",
        "SOURCE": {"name": "Oro olímpico + Mundial descargados (Wikipedia); All England y semanas nº1 estables",
                   "note": "Los títulos mayores se cuentan automáticamente; All England y semanas nº1 son datos históricos curados."},
        "LAST_TOURNAMENT": build_last(today),
        "NEXT_TOURNAMENT": build_next(today),
        "DISCIPLINES": disciplines, "PROSPECTS": build_prospects(disciplines),
        "IMPORTANCE": 8.0,
    }
    OUT.write_text(f"// Auto-generated {updated}\nwindow.BADMINTON_DATA = "
                   f"{json.dumps(payload, ensure_ascii=False, indent=2)};\n", encoding="utf-8")
    print(f"Wrote {OUT.name} · {len(payload['DISCIPLINES'])} modalidades")
    for d in payload["DISCIPLINES"]:
        print(f"  {d['label']}: nº1 {d['RANKING'][0]['name']} · leyenda {d['LEGENDS'][0]['name']} ({d['LEGENDS'][0]['legendScore']})")


if __name__ == "__main__":
    main()
