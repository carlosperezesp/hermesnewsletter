#!/usr/bin/env python3
"""Snooker: ranking + leyendas y último/próximo torneo importante (schema común
de deportes individuales). Datos curados. Elo real (SnookerPredict, etc.) queda
como proyecto aparte.

Leyenda (0-100): Triple Corona pesa lo máximo — Mundial ×10 + UK ×4 + Masters ×4
+ otros títulos de ranking ×0.5, normalizado a 100 = el más grande (O'Sullivan).
"""
from __future__ import annotations
import json, re
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "snooker_data.js"
W_WORLD, W_UK, W_MASTERS, W_RANK = 10.0, 4.0, 4.0, 0.5

CC2 = {"ENG": "gb-eng", "SCO": "gb-sct", "WAL": "gb-wls", "NIR": "gb-nir",
       "CHN": "cn", "AUS": "au", "BEL": "be", "HKG": "hk", "GER": "de", "IRL": "ie"}
COLORS = {"ENG": "#CE1124", "SCO": "#005EB8", "WAL": "#C8102E", "NIR": "#009A44",
          "CHN": "#DE2910", "AUS": "#00008B", "BEL": "#000000", "GER": "#000000", "IRL": "#169B62"}


def flag(c): x = CC2.get(c, ""); return f"https://flagcdn.com/24x18/{x}.png" if x else ""
def _slug(n): return re.sub(r"[^a-z0-9]+", "_", n.lower()).strip("_")
def _base(name, c):
    col = COLORS.get(c, "#4A4745")
    return {"id": _slug(name), "name": name, "country": c, "logo": flag(c),
            "colors": {"primary": col, "secondary": "#FFFFFF"}}
def _raw(w, u, m, r): return w * W_WORLD + u * W_UK + m * W_MASTERS + r * W_RANK


# current: (nombre, cc3, nivel, nota)
CURRENT = [
    ("Judd Trump", "ENG", 100, "Nº1 del ranking mundial"),
    ("Kyren Wilson", "ENG", 94, "Campeón del mundo 2024"),
    ("Ronnie O'Sullivan", "ENG", 92, "El más grande de todos los tiempos"),
    ("Zhao Xintong", "CHN", 90, "Campeón del mundo 2025"),
    ("Mark Williams", "WAL", 87, "Tricampeón del mundo, aún en la élite"),
    ("John Higgins", "SCO", 84, "Cuádruple campeón del mundo"),
    ("Neil Robertson", "AUS", 82, "Campeón del mundo 2010"),
    ("Mark Selby", "ENG", 80, "Cuádruple campeón del mundo"),
]
# legends: (nombre, cc3, era, Mundiales, UK, Masters, ranking_titles, nota)
LEGENDS = [
    ("Ronnie O'Sullivan", "ENG", "1993-presente", 7, 8, 8, 41, "Récord de 41 títulos de ranking y de Triple Coronas; genio irrepetible."),
    ("Stephen Hendry", "SCO", "1990-1999", 7, 5, 6, 36, "Dominó los 90 con siete Mundiales; el más precoz."),
    ("Steve Davis", "ENG", "1981-1989", 6, 6, 3, 28, "El icono de los 80 que llevó el snooker a la tele."),
    ("John Higgins", "SCO", "1998-2011", 4, 3, 2, 32, "'El Mago': uno de los constructores de tacadas más brillantes."),
    ("Mark Selby", "ENG", "2014-2021", 4, 2, 3, 20, "'El Torturador': cuatro Mundiales a base de táctica."),
    ("Mark Williams", "WAL", "2000-2018", 3, 3, 2, 26, "Zurdo letal con dos décadas en la cima."),
    ("Ray Reardon", "WAL", "1970-1978", 6, 0, 1, 0, "'Drácula': seis Mundiales en la era pre-Crucible moderna."),
    ("Judd Trump", "ENG", "2019-presente", 1, 3, 2, 28, "El más completo de su generación; ataque total."),
]
# palmarés de los activos para su score leyenda: (Mundiales, UK, Masters, ranking)
CURRENT_TITLES = {
    "Judd Trump": (1, 3, 2, 28), "Ronnie O'Sullivan": (7, 8, 8, 41),
    "Mark Williams": (3, 3, 2, 26), "John Higgins": (4, 3, 2, 32),
    "Mark Selby": (4, 2, 3, 20), "Kyren Wilson": (1, 0, 1, 4),
    "Zhao Xintong": (1, 1, 0, 3), "Neil Robertson": (1, 1, 1, 24),
}

LAST_TOURNAMENT = {"name": "Campeonato del Mundo", "level": "Triple Corona", "location": "Crucible, Sheffield",
                   "end": "2026-05-04", "champions": [("Zhao Xintong", "CHN", "Individual")]}
NEXT_TOURNAMENT = {"name": "UK Championship", "level": "Triple Corona", "location": "York",
                   "start": "2026-11-28", "end": "2026-12-06", "defending": "Judd Trump",
                   "favorites": [("Judd Trump", "ENG"), ("Ronnie O'Sullivan", "ENG"),
                                 ("Zhao Xintong", "CHN"), ("Kyren Wilson", "ENG"), ("Mark Selby", "ENG")]}


def build():
    max_raw = max(_raw(w, u, m, r) for *_, w, u, m, r, _ in LEGENDS) or 1.0
    ranking = []
    for i, (name, c, nivel, note) in enumerate(CURRENT):
        w, u, m, r = CURRENT_TITLES.get(name, (0, 0, 0, 0))
        row = _base(name, c)
        row.update({"rank": i + 1, "activeScore": nivel,
                    "legendScore": round(_raw(w, u, m, r) / max_raw * 100, 1), "note": note})
        ranking.append(row)
    entries = {}
    for name, c, era, w, u, m, r, note in LEGENDS:
        row = _base(name, c)
        row.update({"era": era, "legendScore": round(_raw(w, u, m, r) / max_raw * 100, 1),
                    "note": f"{w} Mundial{'es' if w != 1 else ''} · {u} UK · {m} Masters. {note}", "active": False})
        entries[row["id"]] = row
    for name, c, nivel, note in CURRENT:
        rid = _slug(name)
        if rid in entries:
            continue
        w, u, m, r = CURRENT_TITLES.get(name, (0, 0, 0, 0))
        if not (w or u or m):
            continue
        row = _base(name, c)
        row.update({"era": "en activo", "legendScore": round(_raw(w, u, m, r) / max_raw * 100, 1),
                    "note": f"{w} Mundial{'es' if w != 1 else ''} · {u} UK · {m} Masters. {note}", "active": True})
        entries[rid] = row
    legends = sorted(entries.values(), key=lambda x: -x["legendScore"])
    for i, row in enumerate(legends):
        row["rank"] = i + 1
    return [{"id": "main", "label": "Individual", "RANKING": ranking, "LEGENDS": legends}]


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
    payload = {"UPDATED": updated, "SEASON": "Temporada 2025/26",
               "LAST_TOURNAMENT": _tour(LAST_TOURNAMENT, today, "last"),
               "NEXT_TOURNAMENT": _tour(NEXT_TOURNAMENT, today, "next"),
               "DISCIPLINES": build(), "IMPORTANCE": 7.0}
    OUT.write_text(f"// Auto-generated {updated}\nwindow.SNOOKER_DATA = "
                   f"{json.dumps(payload, ensure_ascii=False, indent=2)};\n", encoding="utf-8")
    L = payload["DISCIPLINES"][0]
    print(f"Wrote {OUT.name} · nº1 {L['RANKING'][0]['name']} · leyenda {L['LEGENDS'][0]['name']} ({L['LEGENDS'][0]['legendScore']})")


if __name__ == "__main__":
    main()
