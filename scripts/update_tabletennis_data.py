#!/usr/bin/env python3
"""Tenis de mesa: ranking + leyendas (individual M/F) y último/próximo torneo.
Schema común (IndividualSport). Datos curados.

Leyenda (0-100): oro olímpico individual ×12 + Mundial individual ×7 +
Copa del Mundo individual ×3, normalizado a 100 = mejor de la modalidad.
"""
from __future__ import annotations
import json, re
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tabletennis_data.js"
W_OLY, W_WORLD, W_WC = 12.0, 7.0, 3.0
AGE_CUTOFF = 23  # cantera: los del top actual con esta edad o menos

CC2 = {"CHN": "cn", "SWE": "se", "JPN": "jp", "KOR": "kr", "GER": "de", "FRA": "fr",
       "BRA": "br", "TPE": "tw", "HKG": "hk", "SGP": "sg"}
COLORS = {"CHN": "#DE2910", "SWE": "#006AA7", "JPN": "#BC002D", "KOR": "#003478",
          "GER": "#000000", "FRA": "#002395", "BRA": "#009C3B", "TPE": "#000095",
          "HKG": "#DE2910", "SGP": "#EF3340"}


def flag(c): x = CC2.get(c, ""); return f"https://flagcdn.com/24x18/{x}.png" if x else ""
def _slug(n): return re.sub(r"[^a-z0-9]+", "_", n.lower()).strip("_")
def _base(name, c):
    col = COLORS.get(c, "#4A4745")
    return {"id": _slug(name), "name": name, "country": c, "logo": flag(c),
            "colors": {"primary": col, "secondary": "#FFFFFF"}}
def _raw(o, w, wc): return o * W_OLY + w * W_WORLD + wc * W_WC


DISCIPLINES_RAW = [
    {"id": "ms", "label": "Individual Masculino",
     "current": [
         ("Lin Shidong", "CHN", 20, 100, "Nº1 del ranking mundial"),
         ("Wang Chuqin", "CHN", 25, 97, "Campeón olímpico de dobles mixtos 2024"),
         ("Fan Zhendong", "CHN", 28, 95, "Campeón olímpico individual 2024"),
         ("Ma Long", "CHN", 37, 90, "El más grande de todos los tiempos"),
         ("Truls Möregårdh", "SWE", 23, 87, "Plata olímpica individual 2024"),
         ("Tomokazu Harimoto", "JPN", 22, 85, "Referente japonés"),
         ("Hugo Calderano", "BRA", 29, 83, "El mejor de la historia fuera de Asia/Europa"),
         ("Felix Lebrun", "FRA", 19, 81, "Fenómeno francés adolescente"),
     ],
     "legends": [
         ("Ma Long", "CHN", "2011-2021", 2, 3, 2, "El GOAT: doble oro olímpico individual y Grand Slam completo."),
         ("Jan-Ove Waldner", "SWE", "1989-2000", 1, 2, 1, "'El Mozart': el europeo que dominó a China."),
         ("Zhang Jike", "CHN", "2011-2014", 1, 2, 1, "Grand Slam en tiempo récord (445 días)."),
         ("Wang Liqin", "CHN", "2001-2007", 0, 3, 1, "Triple campeón del mundo individual."),
         ("Kong Linghui", "CHN", "1995-2000", 1, 1, 1, "Uno de los primeros Grand Slam de la historia."),
         ("Liu Guoliang", "CHN", "1996-1999", 1, 1, 1, "Grand Slam y después seleccionador legendario."),
         ("Timo Boll", "GER", "2002-2018", 0, 0, 2, "El mejor europeo de su era; nº1 sin oro olímpico ni mundial."),
     ]},
    {"id": "ws", "label": "Individual Femenino",
     "current": [
         ("Sun Yingsha", "CHN", 25, 100, "Nº1 del mundo"),
         ("Wang Manyu", "CHN", 26, 96, "Múltiple campeona por equipos"),
         ("Chen Meng", "CHN", 31, 93, "Bicampeona olímpica individual (2020, 2024)"),
         ("Hina Hayata", "JPN", 25, 88, "Medallista olímpica"),
         ("Wang Yidi", "CHN", 28, 85, "Top del ranking mundial"),
         ("Mima Ito", "JPN", 25, 83, "Prodigio japonés"),
         ("Shin Yubin", "KOR", 21, 81, "Estrella coreana emergente"),
         ("Chen Xingtong", "CHN", 28, 79, "Podio mundial constante"),
     ],
     "legends": [
         ("Deng Yaping", "CHN", "1991-1997", 2, 3, 2, "La reina: doble oro olímpico individual y dominio absoluto."),
         ("Zhang Yining", "CHN", "2004-2008", 2, 2, 4, "Doble oro olímpico y récord de Copas del Mundo."),
         ("Wang Nan", "CHN", "1999-2005", 1, 3, 4, "Triple campeona del mundo y Grand Slam."),
         ("Ding Ning", "CHN", "2011-2016", 1, 3, 1, "Grand Slam y triple campeona del mundo."),
         ("Chen Meng", "CHN", "2020-2024", 2, 0, 0, "Bicampeona olímpica individual consecutiva."),
         ("Li Xiaoxia", "CHN", "2008-2013", 1, 1, 1, "Oro olímpico 2012 y Grand Slam."),
         ("Liu Shiwen", "CHN", "2009-2019", 0, 1, 5, "'La reina de la Copa del Mundo': cinco títulos."),
     ]},
]
CURRENT_TITLES = {  # (oro olímpico, Mundial, Copa del Mundo) — individual
    "Fan Zhendong": (1, 1, 3), "Ma Long": (2, 3, 2), "Wang Chuqin": (0, 1, 1),
    "Chen Meng": (2, 0, 0), "Sun Yingsha": (0, 1, 1), "Wang Manyu": (0, 0, 1),
}

LAST_TOURNAMENT = {"name": "WTT US Smash", "level": "Grand Smash", "location": "Las Vegas",
                   "end": "2026-07-12", "champions": [("Lin Shidong", "CHN", "Individual Masculino"),
                                                       ("Sun Yingsha", "CHN", "Individual Femenino")]}
NEXT_TOURNAMENT = {"name": "WTT China Smash", "level": "Grand Smash", "location": "Pekín",
                   "start": "2026-09-25", "end": "2026-10-04", "defending": "Wang Chuqin (M) · Sun Yingsha (F)",
                   "favorites": [("Lin Shidong", "CHN"), ("Wang Chuqin", "CHN"), ("Sun Yingsha", "CHN"),
                                 ("Fan Zhendong", "CHN"), ("Hina Hayata", "JPN")]}


def build_discipline(d):
    max_raw = max((_raw(o, w, wc) for *_, o, w, wc, _ in d["legends"]), default=1.0) or 1.0
    ranking = []
    for i, (name, c, age, nivel, note) in enumerate(d["current"]):
        o, w, wc = CURRENT_TITLES.get(name, (0, 0, 0))
        row = _base(name, c)
        row.update({"rank": i + 1, "age": age, "activeScore": nivel,
                    "legendScore": round(_raw(o, w, wc) / max_raw * 100, 1), "note": note})
        ranking.append(row)
    entries = {}
    for name, c, era, o, w, wc, note in d["legends"]:
        row = _base(name, c)
        row.update({"era": era, "legendScore": round(_raw(o, w, wc) / max_raw * 100, 1),
                    "note": f"{o} oro{'s' if o != 1 else ''} olímpico{'s' if o != 1 else ''} · {w} Mundial{'es' if w != 1 else ''} · {wc} Copa del Mundo. {note}", "active": False})
        entries[row["id"]] = row
    for name, c, age, nivel, note in d["current"]:
        rid = _slug(name)
        if rid in entries:
            continue
        o, w, wc = CURRENT_TITLES.get(name, (0, 0, 0))
        if not (o or w or wc):
            continue
        row = _base(name, c)
        row.update({"era": "en activo", "legendScore": round(_raw(o, w, wc) / max_raw * 100, 1),
                    "note": f"{o} oro{'s' if o != 1 else ''} olímpico{'s' if o != 1 else ''} · {w} Mundial{'es' if w != 1 else ''} · {wc} Copa del Mundo. {note}", "active": True})
        entries[rid] = row
    legends = sorted(entries.values(), key=lambda x: -x["legendScore"])
    for i, row in enumerate(legends):
        row["rank"] = i + 1
    return {"id": d["id"], "label": d["label"], "RANKING": ranking, "LEGENDS": legends}


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
    payload = {"UPDATED": updated, "SEASON": "WTT 2026",
               "LAST_TOURNAMENT": _tour(LAST_TOURNAMENT, today, "last"),
               "NEXT_TOURNAMENT": _tour(NEXT_TOURNAMENT, today, "next"),
               "DISCIPLINES": [build_discipline(d) for d in DISCIPLINES_RAW], "IMPORTANCE": 7.5}
    payload["PROSPECTS"] = build_prospects(payload["DISCIPLINES"])
    OUT.write_text(f"// Auto-generated {updated}\nwindow.TABLETENNIS_DATA = "
                   f"{json.dumps(payload, ensure_ascii=False, indent=2)};\n", encoding="utf-8")
    for d in payload["DISCIPLINES"]:
        print(f"  {d['label']}: nº1 {d['RANKING'][0]['name']} · leyenda {d['LEGENDS'][0]['name']} ({d['LEGENDS'][0]['legendScore']})")


if __name__ == "__main__":
    main()
