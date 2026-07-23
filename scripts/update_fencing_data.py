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
    "CAN": "ca", "GBR": "gb",
}
COLORS = {
    "HKG": "#DE2910", "ITA": "#009246", "FRA": "#002395", "USA": "#B22234",
    "HUN": "#436F4D", "EST": "#0072CE", "KOR": "#003478", "TUN": "#E70013",
    "EGY": "#CE1126", "GEO": "#FF0000", "POL": "#DC143C", "GER": "#000000",
    "UKR": "#0057B7", "RUS": "#0039A6", "JPN": "#BC002D", "ROU": "#002B7F",
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
]


def build_event(ev: dict) -> dict:
    ranking = []
    for i, (name, cc3, age, nivel, note) in enumerate(ev["current"]):
        row = _base(name, cc3)
        row.update({"rank": i + 1, "age": age, "activeScore": nivel, "note": note})
        ranking.append(row)

    scored = []
    for name, cc3, era, oly, wc, note in ev["legends"]:
        raw = oly * W_OLYMPIC + wc * W_WORLD
        scored.append((raw, name, cc3, era, oly, wc, note))
    max_raw = max(r[0] for r in scored) or 1.0
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


def main() -> None:
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "UPDATED": updated,
        "SEASON": "Temporada 2025/26",
        "WORLDS": {
            "name": "Campeonato del Mundo de Esgrima 2026",
            "note": "Mundiales en curso: el mejor momento para medir quién es leyenda y quién aspira a serlo.",
        },
        "SOURCE": {"name": "Snapshot curado (rankings FIE + palmarés histórico)",
                   "note": "Datos curados a mano; ampliable a las 6 pruebas."},
        "EVENTS": [build_event(ev) for ev in EVENTS_RAW],
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
