#!/usr/bin/env python3
"""Bádminton: ranking + leyendas (individual M/F) y último/próximo torneo importante.

Como el resto de deportes sin API fácil (esgrima, golf legends), los datos son un
snapshot CURADO real. Modelado como tenis: por cada modalidad, Top ranking (Nivel)
+ Top leyendas (Leyenda). Y como pediste, además, el ÚLTIMO y el PRÓXIMO torneo
importante (campeones y favoritos), estilo golf.

Score activo (Nivel, 0-100): fuerza actual (semilla curada por ranking BWF).
Score leyenda (0-100): dominancia histórica, no solo los oros — porque en bádminton
hay grandes sin oro (Lee Chong Wei, Tai Tzu-ying). Fórmula:
    oro olímpico ×12 + Mundial ×6 + All England ×3 + semanas nº1 ×0.04,
normalizado a 100 = mejor de la historia de la modalidad.
"""
from __future__ import annotations
import json
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "badminton_data.js"

W_OLY, W_WORLD, W_AE, W_WEEKS = 12.0, 9.0, 3.0, 0.04
AGE_CUTOFF = 23  # cantera: los del top actual con esta edad o menos

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


def flag(cc3): cc2 = CC2.get(cc3, ""); return f"https://flagcdn.com/24x18/{cc2}.png" if cc2 else ""
def _slug(n): import re; return re.sub(r"[^a-z0-9]+", "_", n.lower()).strip("_")
def _base(name, cc3):
    c = COLORS.get(cc3, "#4A4745")
    return {"id": _slug(name), "name": name, "country": cc3, "logo": flag(cc3),
            "colors": {"primary": c, "secondary": "#FFFFFF"}}
def _legend_raw(oly, world, ae, weeks): return oly * W_OLY + world * W_WORLD + ae * W_AE + weeks * W_WEEKS


# ── Datos curados (snapshot real) ────────────────────────────────────────────
# current: (nombre, cc3, edad, nivel_seed, nota)
# legends: (nombre, cc3, era, oros_olímpicos, Mundiales, All_England, semanas_nº1, nota)
DISCIPLINES_RAW = [
    {
        "id": "ms", "label": "Individual Masculino",
        "current": [
            ("Shi Yuqi", "CHN", 30, 100, "Nº1 del mundo"),
            ("Viktor Axelsen", "DEN", 32, 98, "Bicampeón olímpico (2021, 2024)"),
            ("Anders Antonsen", "DEN", 29, 93, "Campeón del mundo 2025"),
            ("Kunlavut Vitidsarn", "THA", 25, 90, "Campeón del mundo 2023, plata olímpica 2024"),
            ("Lee Zii Jia", "MAS", 28, 86, "Bronce olímpico 2024"),
            ("Kodai Naraoka", "JPN", 25, 83, "Subcampeón del mundo 2023"),
            ("Jonatan Christie", "INA", 29, 80, "Campeón de Asia 2024"),
            ("Loh Kean Yew", "SGP", 29, 78, "Campeón del mundo 2021"),
        ],
        "legends": [
            ("Lin Dan", "CHN", "2004-2016", 2, 5, 6, 200, "'Super Dan': el más grande. Dos oros olímpicos, cinco Mundiales."),
            ("Viktor Axelsen", "DEN", "2016-presente", 2, 2, 1, 130, "Dos oros olímpicos y dos Mundiales; la era danesa."),
            ("Lee Chong Wei", "MAS", "2006-2018", 0, 0, 4, 349, "349 semanas nº1: el mejor de la historia sin un gran oro."),
            ("Rudy Hartono", "INA", "1968-1976", 0, 1, 8, 0, "Récord de ocho All England, siete consecutivos."),
            ("Chen Long", "CHN", "2014-2017", 1, 2, 0, 60, "Oro olímpico 2016 y doble campeón del mundo."),
            ("Taufik Hidayat", "INA", "2004-2007", 1, 1, 0, 40, "Oro olímpico 2004 con un revés legendario."),
            ("Kento Momota", "JPN", "2018-2020", 0, 2, 0, 100, "Doble campeón del mundo y récord de victorias en una temporada."),
            ("Morten Frost", "DEN", "1982-1988", 0, 0, 4, 30, "Dominó los 80 con cuatro All England pese a no ganar el Mundial."),
        ],
    },
    {
        "id": "ws", "label": "Individual Femenino",
        "current": [
            ("An Se-young", "KOR", 24, 100, "Campeona olímpica 2024 y nº1"),
            ("Akane Yamaguchi", "JPN", 28, 95, "Doble campeona del mundo"),
            ("Chen Yufei", "CHN", 28, 91, "Campeona olímpica 2021"),
            ("Wang Zhiyi", "CHN", 25, 87, "Campeona de All England"),
            ("He Bingjiao", "CHN", 28, 84, "Medallista olímpica 2024"),
            ("Gregoria Mariska Tunjung", "INA", 26, 81, "Bronce mundial y de Asia"),
            ("Pornpawee Chochuwong", "THA", 27, 78, "Finalista de Grand Prix"),
            ("Ratchanok Intanon", "THA", 31, 76, "Campeona del mundo 2013"),
        ],
        "legends": [
            ("Carolina Marín", "ESP", "2014-2021", 1, 3, 1, 60, "Oro olímpico 2016 y triple campeona del mundo; intensidad única."),
            ("Tai Tzu-ying", "TPE", "2016-2024", 0, 0, 2, 214, "214 semanas nº1: la más dominante sin oro olímpico ni mundial."),
            ("Zhang Ning", "CHN", "2003-2008", 2, 1, 0, 40, "Bicampeona olímpica (2004, 2008)."),
            ("Susi Susanti", "INA", "1989-1997", 1, 1, 4, 50, "Oro olímpico 1992 y cuatro All England; icono indonesio."),
            ("Li Xuerui", "CHN", "2011-2014", 1, 1, 1, 60, "Oro olímpico 2012 y campeona del mundo."),
            ("Wang Yihan", "CHN", "2010-2013", 0, 1, 1, 70, "Nº1 sostenida y campeona del mundo 2011."),
            ("Ratchanok Intanon", "THA", "2013-2016", 0, 1, 0, 30, "Campeona del mundo más joven de la historia (18 años)."),
            ("P. V. Sindhu", "IND", "2016-2019", 0, 1, 0, 10, "Campeona del mundo 2019 y doble medallista olímpica."),
        ],
    },
]

# Palmarés de los ACTIVOS para su score leyenda: (oros, Mundiales, All England, semanas nº1)
CURRENT_TITLES = {
    "Shi Yuqi": (0, 0, 2, 40), "Viktor Axelsen": (2, 2, 1, 130),
    "Anders Antonsen": (0, 1, 1, 20), "Kunlavut Vitidsarn": (0, 1, 0, 10),
    "Lee Zii Jia": (0, 0, 1, 10), "Loh Kean Yew": (0, 1, 0, 5),
    "An Se-young": (1, 1, 1, 100), "Akane Yamaguchi": (0, 2, 0, 80),
    "Chen Yufei": (1, 0, 1, 40), "Ratchanok Intanon": (0, 1, 0, 30),
}

# ── Torneos importantes: último (con campeones) y próximo (con favoritos) ─────
LAST_TOURNAMENT = {
    "name": "Japan Open", "level": "BWF World Tour Super 750", "location": "Tokio",
    "end": "2026-07-20",
    "champions": [
        ("Individual Masculino", "Shi Yuqi", "CHN"),
        ("Individual Femenino", "An Se-young", "KOR"),
    ],
}
NEXT_TOURNAMENT = {
    "name": "Campeonato del Mundo BWF 2026", "level": "Mundial", "location": "París",
    "start": "2026-08-24", "end": "2026-08-30",
    "defending": "Anders Antonsen (M) · An Se-young (F)",
    "favorites": [
        ("Shi Yuqi", "CHN"), ("Viktor Axelsen", "DEN"), ("An Se-young", "KOR"),
        ("Akane Yamaguchi", "JPN"), ("Kunlavut Vitidsarn", "THA"),
    ],
}


def build_discipline(d: dict) -> dict:
    max_raw = max((_legend_raw(o, w, a, k) for *_, o, w, a, k, _ in d["legends"]), default=1.0) or 1.0
    ranking = []
    for i, (name, cc3, age, nivel, note) in enumerate(d["current"]):
        o, w, a, k = CURRENT_TITLES.get(name, (0, 0, 0, 0))
        row = _base(name, cc3)
        row.update({"rank": i + 1, "age": age, "activeScore": nivel,
                    "legendScore": round(_legend_raw(o, w, a, k) / max_raw * 100, 1),
                    "olympicGold": o, "worldGold": w, "allEngland": a, "note": note})
        ranking.append(row)
    # Leyendas = históricos curados + ACTIVOS con palmarés (dedup por nombre), para
    # que un activo con currículum de leyenda aparezca también en las leyendas.
    scored = [(_legend_raw(o, w, a, k), name, cc3, era, o, w, a, k, note)
              for name, cc3, era, o, w, a, k, note in d["legends"]]
    entries = {}
    for raw, name, cc3, era, o, w, a, k, note in sorted(scored, reverse=True):
        row = _base(name, cc3)
        row.update({"era": era, "olympicGold": o, "worldGold": w, "allEngland": a,
                    "weeksNo1": k, "legendScore": round(raw / max_raw * 100, 1),
                    "note": note, "active": False})
        entries[row["id"]] = row
    for name, cc3, age, nivel, note in d["current"]:
        o, w, a, k = CURRENT_TITLES.get(name, (0, 0, 0, 0))
        rid = _slug(name)
        if (o or w or a) and rid not in entries:
            row = _base(name, cc3)
            row.update({"era": "en activo", "olympicGold": o, "worldGold": w, "allEngland": a,
                        "weeksNo1": k, "legendScore": round(_legend_raw(o, w, a, k) / max_raw * 100, 1),
                        "note": note, "active": True})
            entries[rid] = row
    legends = sorted(entries.values(), key=lambda r: -r["legendScore"])
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
    payload = {
        "UPDATED": updated, "SEASON": "BWF World Tour 2026",
        "SOURCE": {"name": "Snapshot curado (rankings BWF + palmarés histórico)",
                   "note": "Datos curados a mano; ampliable a dobles y mixto."},
        "LAST_TOURNAMENT": build_last(today),
        "NEXT_TOURNAMENT": build_next(today),
        "DISCIPLINES": [build_discipline(d) for d in DISCIPLINES_RAW],
        "IMPORTANCE": 8.0,
    }
    payload["PROSPECTS"] = build_prospects(payload["DISCIPLINES"])
    OUT.write_text(f"// Auto-generated {updated}\nwindow.BADMINTON_DATA = "
                   f"{json.dumps(payload, ensure_ascii=False, indent=2)};\n", encoding="utf-8")
    print(f"Wrote {OUT.name} · {len(payload['DISCIPLINES'])} modalidades")
    for d in payload["DISCIPLINES"]:
        print(f"  {d['label']}: nº1 {d['RANKING'][0]['name']} · leyenda {d['LEGENDS'][0]['name']} ({d['LEGENDS'][0]['legendScore']})")
    print(f"  Último: {payload['LAST_TOURNAMENT']['name']} · Próximo: {payload['NEXT_TOURNAMENT']['name']} "
          f"(en {payload['NEXT_TOURNAMENT']['daysToStart']} días)")


if __name__ == "__main__":
    main()
