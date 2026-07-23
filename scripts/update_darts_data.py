#!/usr/bin/env python3
"""Dardos (PDC): ranking + leyendas y último/próximo torneo importante.
Datos curados. El oficial es dinero (Order of Merit); el Elo es un proyecto aparte.

Leyenda (0-100): títulos mundiales ×10 + otros majors televisados ×0.5,
normalizado a 100 = el más grande (Phil Taylor).
"""
from __future__ import annotations
import json, re
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "darts_data.js"
W_WORLD, W_MAJOR = 10.0, 0.5

CC2 = {"ENG": "gb-eng", "SCO": "gb-sct", "WAL": "gb-wls", "NIR": "gb-nir",
       "NED": "nl", "AUS": "au", "BEL": "be", "GER": "de", "AUT": "at"}
COLORS = {"ENG": "#CE1124", "SCO": "#005EB8", "WAL": "#C8102E", "NIR": "#009A44",
          "NED": "#AE1C28", "AUS": "#00008B", "BEL": "#000000", "GER": "#000000", "AUT": "#ED2939"}


def flag(c): x = CC2.get(c, ""); return f"https://flagcdn.com/24x18/{x}.png" if x else ""
def _slug(n): return re.sub(r"[^a-z0-9]+", "_", n.lower()).strip("_")
def _base(name, c):
    col = COLORS.get(c, "#4A4745")
    return {"id": _slug(name), "name": name, "country": c, "logo": flag(c),
            "colors": {"primary": col, "secondary": "#FFFFFF"}}
def _raw(w, mj): return w * W_WORLD + mj * W_MAJOR


CURRENT = [
    ("Luke Humphries", "ENG", 100, "Nº1 y campeón del mundo 2024"),
    ("Luke Littler", "ENG", 99, "Campeón del mundo 2025 con 17 años"),
    ("Michael van Gerwen", "NED", 92, "Tricampeón del mundo"),
    ("Michael Smith", "ENG", 86, "Campeón del mundo 2023"),
    ("Gerwyn Price", "WAL", 84, "Campeón del mundo 2021"),
    ("Nathan Aspinall", "ENG", 80, "Ganador de World Matchplay"),
    ("Rob Cross", "ENG", 79, "Campeón del mundo 2018"),
    ("Stephen Bunting", "ENG", 77, "Top del Order of Merit"),
]
# legends: (nombre, cc3, era, Mundiales, otros_majors, nota)
LEGENDS = [
    ("Phil Taylor", "ENG", "1990-2018", 16, 69, "'The Power': 16 títulos mundiales, un dominio que jamás se repetirá."),
    ("Michael van Gerwen", "NED", "2013-presente", 3, 40, "'Mighty Mike': la máquina más consistente de la era moderna."),
    ("Raymond van Barneveld", "NED", "1998-2007", 5, 12, "Cinco Mundiales entre BDO y PDC; ídolo de masas."),
    ("Eric Bristow", "ENG", "1980-1986", 5, 10, "'Crafty Cockney': la primera superestrella del dardo."),
    ("Gary Anderson", "SCO", "2015-2016", 2, 15, "'The Flying Scotsman': dos Mundiales consecutivos."),
    ("John Lowe", "ENG", "1979-1993", 3, 8, "Tres Mundiales en tres décadas distintas."),
    ("Luke Humphries", "ENG", "2023-presente", 1, 8, "'Cool Hand Luke': la nueva referencia del circuito."),
    ("Luke Littler", "ENG", "2025-presente", 1, 6, "Fenómeno adolescente que revolucionó el deporte."),
]
CURRENT_TITLES = {  # (Mundiales, otros majors)
    "Luke Humphries": (1, 8), "Luke Littler": (1, 6), "Michael van Gerwen": (3, 40),
    "Michael Smith": (1, 3), "Gerwyn Price": (1, 4), "Rob Cross": (1, 2),
}

LAST_TOURNAMENT = {"name": "World Matchplay", "level": "Major televisado", "location": "Blackpool",
                   "end": "2026-07-19", "champions": [("Luke Humphries", "ENG", "Individual")]}
NEXT_TOURNAMENT = {"name": "Campeonato del Mundo PDC", "level": "Mundial", "location": "Alexandra Palace, Londres",
                   "start": "2026-12-17", "end": "2027-01-03", "defending": "Luke Littler",
                   "favorites": [("Luke Humphries", "ENG"), ("Luke Littler", "ENG"),
                                 ("Michael van Gerwen", "NED"), ("Gerwyn Price", "WAL"), ("Michael Smith", "ENG")]}


def build():
    max_raw = max(_raw(w, mj) for *_, w, mj, _ in LEGENDS) or 1.0
    ranking = []
    for i, (name, c, nivel, note) in enumerate(CURRENT):
        w, mj = CURRENT_TITLES.get(name, (0, 0))
        row = _base(name, c)
        row.update({"rank": i + 1, "activeScore": nivel,
                    "legendScore": round(_raw(w, mj) / max_raw * 100, 1), "note": note})
        ranking.append(row)
    entries = {}
    for name, c, era, w, mj, note in LEGENDS:
        row = _base(name, c)
        row.update({"era": era, "legendScore": round(_raw(w, mj) / max_raw * 100, 1),
                    "note": f"{w} Mundial{'es' if w != 1 else ''} · {mj} majors. {note}", "active": False})
        entries[row["id"]] = row
    for name, c, nivel, note in CURRENT:
        rid = _slug(name)
        if rid in entries:
            continue
        w, mj = CURRENT_TITLES.get(name, (0, 0))
        if not w:
            continue
        row = _base(name, c)
        row.update({"era": "en activo", "legendScore": round(_raw(w, mj) / max_raw * 100, 1),
                    "note": f"{w} Mundial{'es' if w != 1 else ''} · {mj} majors. {note}", "active": True})
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
    payload = {"UPDATED": updated, "SEASON": "PDC 2026",
               "LAST_TOURNAMENT": _tour(LAST_TOURNAMENT, today, "last"),
               "NEXT_TOURNAMENT": _tour(NEXT_TOURNAMENT, today, "next"),
               "DISCIPLINES": build(), "IMPORTANCE": 7.0}
    OUT.write_text(f"// Auto-generated {updated}\nwindow.DARTS_DATA = "
                   f"{json.dumps(payload, ensure_ascii=False, indent=2)};\n", encoding="utf-8")
    L = payload["DISCIPLINES"][0]
    print(f"Wrote {OUT.name} · nº1 {L['RANKING'][0]['name']} · leyenda {L['LEGENDS'][0]['name']} ({L['LEGENDS'][0]['legendScore']})")


if __name__ == "__main__":
    main()
