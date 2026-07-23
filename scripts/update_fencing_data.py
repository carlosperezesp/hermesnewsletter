#!/usr/bin/env python3
"""Esgrima: ranking actual + leyendas por prueba individual.

Como no hay una API pública fácil (la FIE no expone JSON estable), los datos son
un snapshot CURADO real (top actuales y leyendas por prueba), igual que el roster
de golf. Modelado como el tenis pero SIN partidos: por cada prueba, un Top ranking
(score activo) y un Top leyendas (score histórico). v1 con 3 pruebas para validar
el formato; ampliable a las 6.

Score activo (0-100): fuerza actual (semilla curada por posición de ranking).
Score leyenda (0-100): palmarés = oros olímpicos individuales + Mundiales
individuales, normalizado a 100 = mejor de esa arma.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fencing_data.js"

W_OLYMPIC = 10.0   # oro olímpico individual
W_WORLD = 3.5      # oro mundial individual

CC2 = {
    "HKG": "hk", "ITA": "it", "FRA": "fr", "USA": "us", "HUN": "hu", "EST": "ee",
    "KOR": "kr", "TUN": "tn", "EGY": "eg", "GEO": "ge", "POL": "pl", "GER": "de",
    "UKR": "ua", "RUS": "ru", "JPN": "jp", "CHN": "cn", "AZE": "az", "ROU": "ro",
    "CAN": "ca", "GBR": "gb", "SWE": "se", "CUB": "cu", "VEN": "ve",
}
COLORS = {
    "HKG": "#DE2910", "ITA": "#009246", "FRA": "#002395", "USA": "#B22234",
    "HUN": "#436F4D", "EST": "#0072CE", "KOR": "#003478", "TUN": "#E70013",
    "EGY": "#CE1126", "GEO": "#FF0000", "POL": "#DC143C", "GER": "#000000",
    "UKR": "#0057B7", "RUS": "#0039A6", "JPN": "#BC002D", "ROU": "#002B7F",
    "SWE": "#006AA7", "CUB": "#002A8F", "VEN": "#CF142B",
}


def flag(cc3: str) -> str:
    cc2 = CC2.get(cc3, "")
    return f"https://flagcdn.com/24x18/{cc2}.png" if cc2 else ""


def _slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _base(name: str, cc3: str) -> dict:
    c = COLORS.get(cc3, "#4A4745")
    return {"id": _slug(name), "name": name, "country": cc3, "logo": flag(cc3),
            "colors": {"primary": c, "secondary": "#FFFFFF"}}


# ── Datos curados (snapshot real) ────────────────────────────────────────────
# current: (nombre, cc3, edad, nivel_seed 0-100, nota)
# legends: (nombre, cc3, era, oros_olímpicos_ind, oros_mundiales_ind, nota)
EVENTS_RAW = [
    {
        "id": "foil-m", "weapon": "Florete", "gender": "M", "label": "Florete Masculino",
        "current": [
            ("Ka Long Cheung", "HKG", 28, 100, "Bicampeón olímpico (2021, 2024)"),
            ("Tommaso Marini", "ITA", 25, 96, "Campeón del mundo 2023"),
            ("Filippo Macchi", "ITA", 24, 92, "Plata olímpica 2024"),
            ("Guillaume Bianchi", "ITA", 29, 88, "Bloque italiano dominante"),
            ("Alexander Massialas", "USA", 31, 84, "Plata olímpica 2016"),
            ("Nick Itkin", "USA", 26, 82, "Bronce olímpico 2024"),
            ("Enzo Lefort", "FRA", 34, 79, "Campeón del mundo 2019"),
            ("Kirill Borodachev", "RUS", 26, 77, "Plata olímpica 2020"),
        ],
        "legends": [
            ("Christian d'Oriola", "FRA", "1947-1958", 2, 4, "El 'Mozart del florete': 2 oros olímpicos y 4 mundiales."),
            ("Aleksandr Romankov", "RUS", "1974-1988", 0, 5, "Cinco veces campeón del mundo, dominio soviético."),
            ("Giulio Gaudini", "ITA", "1928-1936", 1, 3, "Oro olímpico 1936 y triple campeón mundial."),
            ("Stefano Cerioni", "ITA", "1984-1990", 1, 2, "Oro olímpico 1984 y dos mundiales."),
            ("Nedo Nadi", "ITA", "1912-1920", 2, 0, "Cinco oros en 1920; el más versátil de la historia."),
            ("Sergei Golubitsky", "UKR", "1996-1999", 0, 3, "Tricampeón mundial consecutivo (1997-99)."),
            ("Ilgar Mammadov", "AZE", "1988-1996", 1, 0, "Oro olímpico 1992 con el Equipo Unificado."),
            ("Andrea Cassarà", "ITA", "2003-2016", 0, 2, "Doble campeón del mundo del bloque italiano."),
        ],
    },
    {
        "id": "epee-w", "weapon": "Espada", "gender": "F", "label": "Espada Femenina",
        "current": [
            ("Katrina Lehis", "EST", 31, 100, "Nº1 del ranking FIE"),
            ("Vivian Kong Man Wai", "HKG", 31, 96, "Campeona olímpica 2024"),
            ("Alberta Santuccio", "ITA", 30, 92, "Nº2 mundial, oro por equipos 2024"),
            ("Eszter Muhári", "HUN", 27, 89, "Podio mundial constante"),
            ("Auriane Mallo-Breton", "FRA", 32, 86, "Plata olímpica 2024"),
            ("Sera Song", "KOR", 25, 83, "Potencia coreana emergente"),
            ("Rossella Fiamingo", "ITA", 34, 80, "Doble campeona del mundo"),
            ("Giulia Rizzi", "ITA", 35, 77, "Oro olímpico por equipos 2024"),
        ],
        "legends": [
            ("Timea Nagy", "HUN", "2000-2004", 2, 2, "Bicampeona olímpica individual y doble mundial."),
            ("Laura Flessel", "FRA", "1996-2004", 2, 2, "'La Guêpe': dos oros olímpicos y dos mundiales."),
            ("Britta Heidemann", "GER", "2007-2012", 1, 1, "Oro olímpico 2008 y campeona del mundo."),
            ("Emese Szász", "HUN", "2015-2016", 1, 1, "Oro olímpico 2016 y título mundial."),
            ("Rossella Fiamingo", "ITA", "2014-2015", 0, 2, "Bicampeona mundial consecutiva."),
            ("Yana Shemyakina", "UKR", "2012-2013", 1, 1, "Oro olímpico 2012 y mundial."),
            ("Tímea Nagy", "HUN", "1998-1999", 0, 2, "Base de la escuela húngara de espada."),
            ("Nathalie Moellhausen", "ITA", "2019", 0, 1, "Campeona del mundo 2019 (por Brasil)."),
        ],
    },
    {
        "id": "sabre-m", "weapon": "Sable", "gender": "M", "label": "Sable Masculino",
        "current": [
            ("Sébastien Patrice", "FRA", 27, 100, "Nº1 del ranking FIE"),
            ("Sanguk Oh", "KOR", 26, 96, "Campeón olímpico 2024"),
            ("Áron Szilágyi", "HUN", 35, 93, "Tricampeón olímpico (2012-2020)"),
            ("Fares Ferjani", "TUN", 26, 89, "Plata olímpica 2024"),
            ("Sandro Bazadze", "GEO", 32, 86, "Campeón del mundo 2022"),
            ("Luigi Samele", "ITA", 38, 82, "Plata olímpica 2020"),
            ("Ziad Elsissy", "EGY", 30, 80, "Referente africano del sable"),
            ("Colin Heathcock", "USA", 21, 78, "Joven campeón del mundo júnior"),
        ],
        "legends": [
            ("Aladár Gerevich", "HUN", "1932-1960", 2, 3, "Siete oros olímpicos en seis Juegos; el GOAT del sable."),
            ("Viktor Krovopuskov", "RUS", "1976-1980", 2, 2, "Doble oro olímpico individual soviético."),
            ("Jerzy Pawłowski", "POL", "1957-1968", 1, 3, "Oro olímpico y triple campeón del mundo."),
            ("Áron Szilágyi", "HUN", "2012-2020", 3, 1, "Tricampeón olímpico individual consecutivo."),
            ("Jean-François Lamour", "FRA", "1984-1988", 2, 1, "Bicampeón olímpico individual."),
            ("Stanislav Pozdniakov", "RUS", "1996-2002", 1, 4, "Oro olímpico y cuádruple campeón mundial."),
            ("Rudolf Kárpáti", "HUN", "1956-1960", 2, 2, "Doble oro olímpico de la dinastía húngara."),
            ("Sergey Sharikov", "RUS", "1996-2000", 1, 2, "Oro olímpico y doble título mundial."),
        ],
    },
    {
        "id": "epee-m", "weapon": "Espada", "gender": "M", "label": "Espada Masculina",
        "current": [
            ("Koki Kano", "JPN", 27, 100, "Campeón olímpico 2024 y del mundo"),
            ("Yannick Borel", "FRA", 37, 95, "Campeón del mundo y oro por equipos"),
            ("Gergely Siklósi", "HUN", 28, 91, "Plata olímpica 2020"),
            ("Romain Cannone", "FRA", 28, 88, "Campeón olímpico 2021"),
            ("Máté Tamás Koch", "HUN", 32, 84, "Podio mundial constante"),
            ("Andrea Santarelli", "ITA", 32, 81, "Referente de la espada italiana"),
            ("Kazuyasu Minobe", "JPN", 39, 79, "Oro olímpico por equipos 2020"),
            ("Ruben Limardo", "VEN", 40, 77, "Campeón olímpico 2012"),
        ],
        "legends": [
            ("Edoardo Mangiarotti", "ITA", "1936-1960", 1, 5, "El mayor espadista: 13 medallas olímpicas en cinco Juegos."),
            ("Pavel Kolobkov", "RUS", "1996-2005", 1, 4, "Oro olímpico 2000 y cuádruple campeón del mundo."),
            ("Ramón Fonst", "CUB", "1900-1904", 2, 0, "Pionero: dos oros olímpicos a comienzos del siglo XX."),
            ("Éric Srecki", "FRA", "1988-1996", 1, 2, "Oro olímpico 1992 y doble campeón del mundo."),
            ("Arnd Schmitt", "GER", "1988-1992", 1, 1, "Oro olímpico individual 1988."),
            ("Grigory Kriss", "UKR", "1964-1968", 1, 1, "Oro olímpico 1964 de la escuela soviética."),
            ("Johan Harmenberg", "SWE", "1980", 1, 1, "Oro olímpico 1980 con una táctica revolucionaria."),
            ("Géza Imre", "HUN", "2015-2016", 0, 1, "Campeón del mundo 2015 y plata olímpica."),
        ],
    },
    {
        "id": "foil-w", "weapon": "Florete", "gender": "F", "label": "Florete Femenino",
        "current": [
            ("Lee Kiefer", "USA", 32, 100, "Bicampeona olímpica (2021, 2024)"),
            ("Alice Volpi", "ITA", 33, 95, "Campeona del mundo"),
            ("Arianna Errigo", "ITA", 38, 92, "Múltiple campeona del mundo"),
            ("Martina Favaretto", "ITA", 24, 89, "Nº1 del ranking FIE"),
            ("Lauren Scruggs", "USA", 22, 85, "Plata olímpica 2024"),
            ("Eleanor Harvey", "CAN", 30, 82, "Medallista mundial"),
            ("Yuka Ueno", "JPN", 27, 79, "Podio de Copa del Mundo"),
            ("Pauline Ranvier", "FRA", 31, 77, "Bloque francés en ascenso"),
        ],
        "legends": [
            ("Valentina Vezzali", "ITA", "2000-2012", 3, 6, "La reina del florete: tres oros olímpicos individuales seguidos."),
            ("Ilona Elek", "HUN", "1936-1948", 2, 2, "Dos oros olímpicos con doce años de diferencia."),
            ("Giovanna Trillini", "ITA", "1992-2000", 1, 4, "Oro olímpico 1992 y cuádruple campeona del mundo."),
            ("Cornelia Hanisch", "GER", "1979-1985", 1, 3, "Oro olímpico 1984 y triple campeona del mundo."),
            ("Elisa Di Francisca", "ITA", "2012", 1, 2, "Oro olímpico 2012 y doble campeona del mundo."),
            ("Yelena Novikova-Belova", "UKR", "1968-1976", 1, 2, "Oro olímpico 1968, escuela soviética."),
            ("Laura Badea", "ROU", "1996", 1, 1, "Oro olímpico 1996 y campeona del mundo."),
            ("Antonella Ragno-Lonzi", "ITA", "1972", 1, 1, "Oro olímpico 1972, pionera del florete italiano."),
        ],
    },
    {
        "id": "sabre-w", "weapon": "Sable", "gender": "F", "label": "Sable Femenino",
        "current": [
            ("Manon Apithy-Brunet", "FRA", 30, 100, "Campeona olímpica 2024"),
            ("Sara Balzer", "FRA", 31, 96, "Plata olímpica 2024 y campeona del mundo"),
            ("Misaki Emura", "JPN", 30, 92, "Campeona del mundo"),
            ("Martina Criscio", "ITA", 32, 85, "Oro mundial por equipos"),
            ("Anna Márton", "HUN", 34, 82, "Podio europeo y mundial"),
            ("Sebin Choi", "KOR", 25, 80, "Potencia coreana emergente"),
            ("Nozomi Sato", "JPN", 27, 78, "Bloque japonés al alza"),
            ("Elizabeth Tartakovsky", "USA", 24, 76, "Joven referente estadounidense"),
        ],
        "legends": [
            ("Mariel Zagunis", "USA", "2004-2012", 2, 2, "Bicampeona olímpica; la mejor sablista de la historia."),
            ("Olga Kharlan", "UKR", "2013-2019", 0, 4, "Cuádruple campeona del mundo, icono del sable."),
            ("Yana Egorian", "RUS", "2016", 1, 1, "Oro olímpico individual 2016."),
            ("Sofya Velikaya", "RUS", "2011-2015", 0, 2, "Doble campeona del mundo y doble plata olímpica."),
            ("Tan Xue", "CHN", "2002-2008", 0, 2, "Doble campeona del mundo y plata olímpica 2008."),
            ("Ekaterina Dyachenko", "RUS", "2015", 0, 1, "Campeona del mundo y oro olímpico por equipos."),
        ],
    },
]


def build_event(ev: dict) -> dict:
    # Normalización de leyenda del arma (100 = mejor de la historia), para dar a
    # cada ACTIVO también su score leyenda por lo que ya ha ganado (como en tenis).
    scored = [(oly * W_OLYMPIC + wc * W_WORLD, name, cc3, era, oly, wc, note)
              for name, cc3, era, oly, wc, note in ev["legends"]]
    max_raw = max((r[0] for r in scored), default=1.0) or 1.0

    ranking = []
    for i, (name, cc3, age, nivel, note) in enumerate(ev["current"]):
        oly, wc = CURRENT_TITLES.get(name, (0, 0))
        legend = round((oly * W_OLYMPIC + wc * W_WORLD) / max_raw * 100, 1)
        row = _base(name, cc3)
        row.update({"rank": i + 1, "age": age, "activeScore": nivel,
                    "legendScore": legend, "olympicGold": oly, "worldGold": wc, "note": note})
        ranking.append(row)
    legends = []
    for raw, name, cc3, era, oly, wc, note in sorted(scored, reverse=True):
        row = _base(name, cc3)
        row.update({
            "era": era, "olympicGold": oly, "worldGold": wc,
            "legendScore": round(raw / max_raw * 100, 1), "note": note,
        })
        legends.append(row)
    for i, row in enumerate(legends):
        row["rank"] = i + 1

    return {"id": ev["id"], "weapon": ev["weapon"], "gender": ev["gender"],
            "label": ev["label"], "RANKING": ranking, "LEGENDS": legends}


# Títulos individuales (oros olímpicos, oros mundiales) de los ACTIVOS, para medir
# su cercanía a la leyenda en el Road to Glory. Solo los que ya tienen palmarés.
CURRENT_TITLES = {
    "Ka Long Cheung": (2, 0), "Tommaso Marini": (0, 1), "Enzo Lefort": (0, 1),
    "Koki Kano": (1, 1), "Yannick Borel": (0, 1), "Romain Cannone": (1, 1),
    "Gergely Siklósi": (0, 1), "Ruben Limardo": (1, 0), "Rossella Fiamingo": (0, 2),
    "Vivian Kong Man Wai": (1, 0), "Lee Kiefer": (2, 0), "Alice Volpi": (0, 2),
    "Arianna Errigo": (0, 2), "Sanguk Oh": (1, 0), "Áron Szilágyi": (3, 1),
    "Sandro Bazadze": (0, 1), "Manon Apithy-Brunet": (1, 0), "Sara Balzer": (0, 1),
    "Misaki Emura": (0, 1),
}


def build_road_to_glory(events: list[dict]) -> list[dict]:
    """Activos ordenados por cercanía a las leyendas de SU arma. legendScore =
    palmarés individual (oros olímpicos ×10 + mundiales ×3.5) normalizado a 100 =
    mejor de la historia de esa arma; gap = distancia a ese 100."""
    rows = []
    for ev_raw, ev in zip(EVENTS_RAW, events):
        max_raw = max((o * W_OLYMPIC + w * W_WORLD for *_, o, w, _ in ev_raw["legends"]),
                      default=1.0) or 1.0
        for name, cc3, age, nivel, note in ev_raw["current"]:
            oly, wc = CURRENT_TITLES.get(name, (0, 0))
            legend = round((oly * W_OLYMPIC + wc * W_WORLD) / max_raw * 100, 1)
            gap = round(max(0.0, 100.0 - legend), 1)
            row = _base(name, cc3)
            row.update({
                "weapon": ev["weapon"], "label": ev["label"], "age": age,
                "activeScore": nivel, "legendScore": legend,
                "olympicGold": oly, "worldGold": wc, "gapToLegend": gap,
                "note": f"{oly} oro{'s' if oly != 1 else ''} olímpico{'s' if oly != 1 else ''} · "
                        f"{wc} Mundial{'es' if wc != 1 else ''} · "
                        + ("ya en el olimpo del arma" if gap <= 8 else f"a {gap:.0f} del mejor de la historia"),
            })
            rows.append(row)
    rows.sort(key=lambda r: (-r["legendScore"], -r["activeScore"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows[:12]


def build_prospects(max_age: int = 25, top_n: int = 8) -> list[dict]:
    """Cantera: los más jóvenes que ya asoman en el top de cada prueba."""
    out = []
    for ev in EVENTS_RAW:
        for name, cc3, age, nivel, note in ev["current"]:
            if age <= max_age:
                row = _base(name, cc3)
                row.update({"weapon": ev["weapon"], "age": age, "activeScore": nivel,
                            "note": f"{note} · promesa a los {age}"})
                out.append(row)
    out.sort(key=lambda p: p["activeScore"], reverse=True)
    out = out[:top_n]
    for i, p in enumerate(out):
        p["rank"] = i + 1
    return out


def main() -> None:
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    events = [build_event(ev) for ev in EVENTS_RAW]
    payload = {
        "UPDATED": updated,
        "SEASON": "Temporada 2025/26",
        "WORLDS": {
            "name": "Campeonato del Mundo de Esgrima 2026",
            "note": "Mundiales en curso: el mejor momento para medir quién es leyenda y quién aspira a serlo.",
        },
        "SOURCE": {"name": "Snapshot curado (rankings FIE + palmarés histórico)",
                   "note": "Datos curados a mano; ampliable a las 6 pruebas."},
        "EVENTS": events,
        "ROAD_TO_GLORY": build_road_to_glory(events),
        "PROSPECTS": build_prospects(),
        "IMPORTANCE": 8.5,
    }
    OUT.write_text(
        f"// Auto-generated {updated}\nwindow.FENCING_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT.name} · {len(payload['EVENTS'])} pruebas")
    for ev in payload["EVENTS"]:
        top = ev["RANKING"][0]["name"]; leg = ev["LEGENDS"][0]["name"]
        print(f"  {ev['label']}: nº1 {top} · leyenda {leg} ({ev['LEGENDS'][0]['legendScore']})")


if __name__ == "__main__":
    main()
