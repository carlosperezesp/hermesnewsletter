#!/usr/bin/env python3
"""Esgrima: ranking actual + leyendas por prueba individual (florete/espada/sable × M/F).

Score de leyenda = oro olímpico individual (×10) + Mundial individual (×3.5).
  - Mundiales: DESCARGADOS y contados automáticamente de Wikipedia
    (World Fencing Championships), por arma y género, con un parser que respeta
    los rowspan de las rachas. La lista de leyendas se completa sola con todos los
    campeones del mundo; los títulos se recalculan en cada ejecución.
  - Oros olímpicos: dato histórico ESTABLE (curado). No hay una tabla limpia por
    atleta (las páginas por prueba redirigen/404), y cambian una vez cada 4 años.
    Sostienen a los grandes que brillaron sobre todo en los Juegos (Nadi, Fonst).

El ranking de forma (Nivel) sigue curado (la FIE no expone un feed estable).
"""
from __future__ import annotations
import json, re, html, time, unicodedata, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fencing_data.js"
CACHE = ROOT / ".sports_cache"; CACHE.mkdir(exist_ok=True)

W_OLYMPIC = 10.0   # oro olímpico individual
W_WORLD = 3.5      # oro mundial individual

WORLD_SOURCE = "https://en.wikipedia.org/wiki/World_Fencing_Championships"

CC2 = {
    "HKG": "hk", "ITA": "it", "FRA": "fr", "USA": "us", "HUN": "hu", "EST": "ee",
    "KOR": "kr", "TUN": "tn", "EGY": "eg", "GEO": "ge", "POL": "pl", "GER": "de",
    "UKR": "ua", "RUS": "ru", "JPN": "jp", "CHN": "cn", "AZE": "az", "ROU": "ro",
    "CAN": "ca", "GBR": "gb", "SWE": "se", "CUB": "cu", "VEN": "ve", "SUI": "ch",
    "BEL": "be", "AUT": "at", "NED": "nl", "ESP": "es", "MDA": "md", "GRE": "gr",
    "CZE": "cz",
}
COLORS = {
    "HKG": "#DE2910", "ITA": "#009246", "FRA": "#002395", "USA": "#B22234",
    "HUN": "#436F4D", "EST": "#0072CE", "KOR": "#003478", "TUN": "#E70013",
    "EGY": "#CE1126", "GEO": "#FF0000", "POL": "#DC143C", "GER": "#000000",
    "UKR": "#0057B7", "RUS": "#0039A6", "JPN": "#BC002D", "ROU": "#002B7F",
    "SWE": "#006AA7", "CUB": "#002A8F", "VEN": "#CF142B", "SUI": "#D52B1E",
    "BEL": "#000000", "AUT": "#ED2939", "NED": "#AE1C28", "ESP": "#AA151B",
    "CHN": "#DE2910", "GBR": "#012169", "CAN": "#FF0000",
}
# Nombre de país (Wikipedia) → cc3, para dar bandera a los campeones descargados.
NATION_CC = {
    "Italy": "ITA", "France": "FRA", "Hungary": "HUN", "Soviet Union": "RUS",
    "Russia": "RUS", "Unified Team": "RUS", "Ukraine": "UKR", "Poland": "POL",
    "Germany": "GER", "West Germany": "GER", "East Germany": "GER", "China": "CHN",
    "South Korea": "KOR", "Korea": "KOR", "Romania": "ROU", "United States": "USA",
    "Estonia": "EST", "Egypt": "EGY", "Tunisia": "TUN", "Georgia": "GEO",
    "Azerbaijan": "AZE", "Cuba": "CUB", "Sweden": "SWE", "Japan": "JPN",
    "Great Britain": "GBR", "Switzerland": "SUI", "Belgium": "BEL", "Austria": "AUT",
    "Netherlands": "NED", "Spain": "ESP", "Canada": "CAN", "Hong Kong": "HKG",
    "Moldova": "MDA", "Greece": "GRE", "Czech Republic": "CZE", "Czechia": "CZE",
}


def flag(cc3: str) -> str:
    cc2 = CC2.get(cc3, "")
    return f"https://flagcdn.com/24x18/{cc2}.png" if cc2 else ""


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _base(name: str, cc3: str) -> dict:
    c = COLORS.get(cc3, "#4A4745")
    return {"id": _slug(name), "name": name, "country": cc3, "logo": flag(cc3),
            "colors": {"primary": c, "secondary": "#FFFFFF"}}


def _norm(s: str) -> str:
    """Clave de emparejamiento: sin acentos, minúsculas, solo alfanumérico."""
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


# Alias nombre curado → nombre en Wikipedia (transliteraciones / apellidos añadidos)
# que el emparejamiento por acentos no resuelve solo.
ALIAS = {
    "Aleksandr Romankov": "Alexandr Romankov",
    "Stanislav Pozdniakov": "Stanislav Pozdnyakov",
    "Laura Flessel": "Laura Flessel-Colovic",
}


# ── Descarga de Mundiales individuales (fehaciente) ──────────────────────────
_NATION_RE = re.compile("|".join(re.escape(n) for n in sorted(NATION_CC, key=len, reverse=True)))
_JUNK = re.compile(r"World War|Not held|not held|Cancelled|No competition|Olympic Games", re.I)


def _winner_cc(cell: str):
    """(jugador, cc3) de la celda: primer enlace que no es país + país de la bandera."""
    player = None
    cc = ""
    for m in re.findall(r'title="([^"]+)"', cell):
        title = html.unescape(m).strip()
        name = title.split(" (")[0].strip()
        nat = _NATION_RE.match(title)
        if nat and not cc:
            cc = NATION_CC.get(nat.group(0), "")
        elif player is None and name and not name[0].isdigit() and len(name) > 3 \
                and not _NATION_RE.match(name) and not _JUNK.search(name):
            player = name
    return player, cc


def _grid(table: str):
    """Reconstruye la tabla en rejilla respetando rowspan/colspan."""
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)
    out = []
    carry: dict = {}  # col -> (html, filas restantes)
    for r in rows:
        cells = re.findall(r"(<t[hd][^>]*>.*?</t[hd]>)", r, re.S)
        rowout = []
        col = 0
        def place_carries():
            nonlocal col
            while col in carry:
                chtml, rem = carry[col]
                rowout.append(chtml)
                if rem - 1 > 0:
                    carry[col] = (chtml, rem - 1)
                else:
                    del carry[col]
                col += 1
        for c in cells:
            place_carries()
            cs = int(re.search(r'colspan="?(\d+)', c).group(1)) if re.search(r'colspan', c) else 1
            rs = int(re.search(r'rowspan="?(\d+)', c).group(1)) if re.search(r'rowspan', c) else 1
            for _ in range(cs):
                rowout.append(c)
                if rs > 1:
                    carry[col] = (c, rs - 1)
                col += 1
        place_carries()
        out.append(rowout)
    return out


_WEAPON_KEY = {"foil": "foil", "épée": "epee", "epée": "epee", "epee": "epee", "sabre": "sabre"}


def _parse_world(page_html: str):
    """{weapon: {'m'/'w': {jugador: títulos}}} y {jugador: cc3}."""
    counts = {"foil": {"m": defaultdict(int), "w": defaultdict(int)},
              "epee": {"m": defaultdict(int), "w": defaultdict(int)},
              "sabre": {"m": defaultdict(int), "w": defaultdict(int)}}
    reign = {w: {"m": None, "w": None} for w in counts}  # (año, nombre, cc) del más reciente
    cc_map = {}
    sec = ""
    for chunk in re.split(r'(<h[234][^>]*>.*?</h[234]>)', page_html, flags=re.S):
        hm = re.match(r'<h[234][^>]*>(.*?)</h[234]>', chunk, re.S)
        if hm:
            sec = re.sub(r"<[^>]+>", "", html.unescape(hm.group(1))).replace("[edit]", "").strip().lower()
            continue
        wk = _WEAPON_KEY.get(sec)
        if not wk:
            continue
        tab = re.search(r"<table[^>]*wikitable[^>]*>.*?</table>", chunk, re.S)
        if not tab:
            continue
        g = _grid(tab.group(0))
        head = [re.sub(r"<[^>]+>", "", html.unescape(x)).strip().lower() for x in g[0]]
        try:
            mi = head.index("men's individual"); wi = head.index("women's individual")
        except ValueError:
            continue
        for row in g[1:]:
            if len(row) <= max(mi, wi):
                continue
            ym = re.search(r"\b(19|20)\d{2}\b", re.sub(r"<[^>]+>", "", row[0]))
            if not ym:
                continue
            year = int(ym.group(0))
            for idx, gen in ((mi, "m"), (wi, "w")):
                p, cc = _winner_cc(row[idx])
                if p:
                    counts[wk][gen][p] += 1
                    if cc and p not in cc_map:
                        cc_map[p] = cc
                    if reign[wk][gen] is None or year > reign[wk][gen][0]:
                        reign[wk][gen] = [year, p, cc]
    return ({w: {g: dict(counts[w][g]) for g in ("m", "w")} for w in counts}, cc_map,
            {w: {g: reign[w][g] for g in ("m", "w")} for w in reign})


_EMPTY_REIGN = {"foil": {"m": None, "w": None}, "epee": {"m": None, "w": None}, "sabre": {"m": None, "w": None}}


def fetch_world(ttl_h: float = 24.0):
    """(counts, cc_map, reign). Cachea; si el fetch falla, usa caché."""
    cache = CACHE / "fencing_world.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime) / 3600 < ttl_h:
        d = json.loads(cache.read_text())
        if "reign" in d:  # caché con el esquema nuevo
            return d["counts"], d["cc"], d["reign"]
    try:
        req = urllib.request.Request(WORLD_SOURCE, headers={"User-Agent": "Hermes/1.0 (data pipeline)"})
        h = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
        counts, cc, reign = _parse_world(h)
        if any(counts[w][g] for w in counts for g in ("m", "w")):
            cache.write_text(json.dumps({"counts": counts, "cc": cc, "reign": reign}, ensure_ascii=False))
            return counts, cc, reign
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] fencing fetch {WORLD_SOURCE}: {e}")
    if cache.exists():
        d = json.loads(cache.read_text())
        return d["counts"], d["cc"], d.get("reign", _EMPTY_REIGN)
    return ({"foil": {"m": {}, "w": {}}, "epee": {"m": {}, "w": {}}, "sabre": {"m": {}, "w": {}}},
            {}, _EMPTY_REIGN)


# ── Datos curados: ranking de forma + fichas de leyendas (oro olímpico + bio) ──
# current: (nombre, cc3, edad, nivel, nota)
# legends: (nombre, cc3, era, oros_olímpicos_ind, nota) — el Mundial viene del fetch.
EVENTS_RAW = [
    {"id": "foil-m", "weapon": "Florete", "gender": "M", "label": "Florete Masculino", "wk": "foil", "g": "m",
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
         ("Christian d'Oriola", "FRA", "1947-1958", 2, "El 'Mozart del florete': dos oros olímpicos."),
         ("Aleksandr Romankov", "RUS", "1974-1988", 0, "Dominio soviético del florete."),
         ("Giulio Gaudini", "ITA", "1928-1936", 1, "Oro olímpico 1936."),
         ("Stefano Cerioni", "ITA", "1984-1990", 1, "Oro olímpico 1984."),
         ("Nedo Nadi", "ITA", "1912-1920", 2, "Cinco oros en 1920; el más versátil de la historia."),
         ("Sergei Golubitsky", "UKR", "1996-1999", 0, "Tricampeón mundial consecutivo (1997-99)."),
         ("Ilgar Mammadov", "AZE", "1988-1996", 1, "Oro olímpico 1992 con el Equipo Unificado."),
         ("Andrea Cassarà", "ITA", "2003-2016", 0, "Del bloque italiano dominante."),
     ]},
    {"id": "epee-w", "weapon": "Espada", "gender": "F", "label": "Espada Femenina", "wk": "epee", "g": "w",
     "current": [
         ("Katrina Lehis", "EST", 31, 100, "Nº1 del ranking FIE"),
         ("Vivian Kong Man Wai", "HKG", 31, 96, "Campeona olímpica 2024"),
         ("Alberta Santuccio", "ITA", 30, 92, "Nº2 mundial, oro por equipos 2024"),
         ("Eszter Muhári", "HUN", 27, 89, "Podio mundial constante"),
         ("Auriane Mallo-Breton", "FRA", 32, 86, "Plata olímpica 2024"),
         ("Song Se-ra", "KOR", 25, 83, "Potencia coreana emergente"),
         ("Rossella Fiamingo", "ITA", 34, 80, "Doble campeona del mundo"),
         ("Giulia Rizzi", "ITA", 35, 77, "Oro olímpico por equipos 2024"),
     ],
     "legends": [
         ("Timea Nagy", "HUN", "2000-2004", 2, "Bicampeona olímpica individual."),
         ("Laura Flessel", "FRA", "1996-2004", 2, "'La Guêpe': dos oros olímpicos."),
         ("Britta Heidemann", "GER", "2007-2012", 1, "Oro olímpico 2008."),
         ("Emese Szász", "HUN", "2015-2016", 1, "Oro olímpico 2016."),
         ("Rossella Fiamingo", "ITA", "2014-2015", 0, "Bicampeona mundial consecutiva."),
         ("Yana Shemyakina", "UKR", "2012-2013", 1, "Oro olímpico 2012."),
         ("Nathalie Moellhausen", "ITA", "2019", 0, "Campeona del mundo 2019 (por Brasil)."),
     ]},
    {"id": "sabre-m", "weapon": "Sable", "gender": "M", "label": "Sable Masculino", "wk": "sabre", "g": "m",
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
         ("Aladár Gerevich", "HUN", "1932-1960", 2, "Siete oros olímpicos en seis Juegos; el GOAT del sable."),
         ("Viktor Krovopuskov", "RUS", "1976-1980", 2, "Doble oro olímpico individual soviético."),
         ("Jerzy Pawłowski", "POL", "1957-1968", 1, "Oro olímpico y triple campeón del mundo."),
         ("Áron Szilágyi", "HUN", "2012-2020", 3, "Tricampeón olímpico individual consecutivo."),
         ("Jean-François Lamour", "FRA", "1984-1988", 2, "Bicampeón olímpico individual."),
         ("Stanislav Pozdniakov", "RUS", "1996-2002", 1, "Oro olímpico y múltiple campeón del mundo."),
         ("Rudolf Kárpáti", "HUN", "1956-1960", 2, "Doble oro olímpico de la dinastía húngara."),
     ]},
    {"id": "epee-m", "weapon": "Espada", "gender": "M", "label": "Espada Masculina", "wk": "epee", "g": "m",
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
         ("Edoardo Mangiarotti", "ITA", "1936-1960", 1, "El mayor espadista: 13 medallas olímpicas en cinco Juegos."),
         ("Pavel Kolobkov", "RUS", "1996-2005", 1, "Oro olímpico 2000."),
         ("Ramón Fonst", "CUB", "1900-1904", 2, "Pionero: dos oros olímpicos a comienzos del siglo XX."),
         ("Éric Srecki", "FRA", "1988-1996", 1, "Oro olímpico 1992."),
         ("Arnd Schmitt", "GER", "1988-1992", 1, "Oro olímpico individual 1988."),
         ("Grigory Kriss", "UKR", "1964-1968", 1, "Oro olímpico 1964 de la escuela soviética."),
         ("Johan Harmenberg", "SWE", "1980", 1, "Oro olímpico 1980 con una táctica revolucionaria."),
         ("Géza Imre", "HUN", "2015-2016", 0, "Campeón del mundo 2015 y plata olímpica."),
     ]},
    {"id": "foil-w", "weapon": "Florete", "gender": "F", "label": "Florete Femenino", "wk": "foil", "g": "w",
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
         ("Valentina Vezzali", "ITA", "2000-2012", 3, "La reina del florete: tres oros olímpicos individuales seguidos."),
         ("Ilona Elek", "HUN", "1936-1948", 2, "Dos oros olímpicos con doce años de diferencia."),
         ("Giovanna Trillini", "ITA", "1992-2000", 1, "Oro olímpico 1992."),
         ("Cornelia Hanisch", "GER", "1979-1985", 1, "Oro olímpico 1984."),
         ("Elisa Di Francisca", "ITA", "2012", 1, "Oro olímpico 2012."),
         ("Yelena Novikova-Belova", "UKR", "1968-1976", 1, "Oro olímpico 1968, escuela soviética."),
         ("Laura Badea", "ROU", "1996", 1, "Oro olímpico 1996."),
         ("Antonella Ragno-Lonzi", "ITA", "1972", 1, "Oro olímpico 1972."),
     ]},
    {"id": "sabre-w", "weapon": "Sable", "gender": "F", "label": "Sable Femenino", "wk": "sabre", "g": "w",
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
         ("Mariel Zagunis", "USA", "2004-2012", 2, "Bicampeona olímpica; la mejor sablista de la historia."),
         ("Olga Kharlan", "UKR", "2013-2019", 0, "Icono del sable, múltiple campeona del mundo."),
         ("Yana Egorian", "RUS", "2016", 1, "Oro olímpico individual 2016."),
         ("Sofya Velikaya", "RUS", "2011-2015", 0, "Doble plata olímpica y campeona del mundo."),
         ("Tan Xue", "CHN", "2002-2008", 0, "Plata olímpica 2008."),
     ]},
]

# Oros olímpicos individuales de los ACTIVOS (estable, para su score de leyenda).
CURRENT_OLY = {
    "Ka Long Cheung": 2, "Koki Kano": 1, "Romain Cannone": 1, "Ruben Limardo": 1,
    "Vivian Kong Man Wai": 1, "Lee Kiefer": 2, "Sanguk Oh": 1, "Áron Szilágyi": 3,
    "Manon Apithy-Brunet": 1,
}


def _note(name, oly, wc, bio):
    return (f"{oly} oro{'s' if oly != 1 else ''} olímpico{'s' if oly != 1 else ''} · "
            f"{wc} Mundial{'es' if wc != 1 else ''}. {bio}").strip()


def build_event(ev: dict, world, cc_map, reign=None, limit: int = 9) -> dict:
    wc_counts = world.get(ev["wk"], {}).get(ev["g"], {})
    # Índice normalizado para emparejar nombres curados con los de Wikipedia.
    norm_index = {}
    for k in wc_counts:
        norm_index.setdefault(_norm(k), k)
    claimed = set()

    def wc_of(name):
        """Mundiales de 'name' resolviendo alias/acentos; marca la clave como usada."""
        key = ALIAS.get(name, name)
        if key not in wc_counts:
            key = norm_index.get(_norm(key))
        if key is None:
            return 0
        claimed.add(key)
        return wc_counts[key]

    # Fichas de leyenda: curadas (oro olímpico + bio) con Mundial DESCARGADO.
    info = {}  # slug -> dict
    for name, cc3, era, oly, bio in ev["legends"]:
        info[_slug(name)] = {"name": name, "cc": cc3, "era": era, "oly": oly,
                             "wc": wc_of(name), "bio": bio, "active": False}
    # Mundiales de los activos (reclaman su clave antes del auto-añadido → sin duplicar).
    cur_wc = {name: wc_of(name) for name, *_ in ev["current"]}
    # Auto-añade campeones del mundo descargados que no estén ya (lista completa).
    for name, cnt in wc_counts.items():
        if name in claimed:
            continue
        rid = _slug(name)
        if rid in info:
            continue
        info[rid] = {"name": name, "cc": cc_map.get(name, ""), "era": "—",
                     "oly": 0, "wc": cnt, "bio": "Campeón del mundo.", "active": False}
    # Activos con palmarés → también en leyendas, marcados en activo.
    for name, cc3, age, nivel, note in ev["current"]:
        oly = CURRENT_OLY.get(name, 0)
        wc = cur_wc[name]
        if oly or wc:
            info[_slug(name)] = {"name": name, "cc": cc3, "era": "en activo", "oly": oly,
                                 "wc": wc, "bio": note, "active": True}

    raws = {rid: v["oly"] * W_OLYMPIC + v["wc"] * W_WORLD for rid, v in info.items()}
    max_raw = max(raws.values(), default=1.0) or 1.0

    legends = []
    for rid, v in info.items():
        row = _base(v["name"], v["cc"])
        row.update({"era": v["era"], "olympicGold": v["oly"], "worldGold": v["wc"],
                    "legendScore": round(raws[rid] / max_raw * 100, 1),
                    "note": _note(v["name"], v["oly"], v["wc"], v["bio"]), "active": v["active"]})
        legends.append(row)
    legends.sort(key=lambda r: (-r["legendScore"], r["name"]))
    legends = legends[:limit]
    for i, row in enumerate(legends):
        row["rank"] = i + 1

    # Campeón del mundo VIGENTE (del fetch): se usa para anotar/inyectar en el ranking.
    rw = (reign or {}).get(ev["wk"], {}).get(ev["g"]) if reign else None
    reign_world = None
    if rw:
        y, nm, cc = rw
        reign_world = {"year": y, "name": nm, "country": cc, "logo": flag(cc)}
    champ_key = _norm(reign_world["name"]) if reign_world else None
    champ_word = "Campeona" if ev["gender"] == "F" else "Campeón"

    ranking = []
    for i, (name, cc3, age, nivel, note) in enumerate(ev["current"]):
        oly = CURRENT_OLY.get(name, 0)
        wc = cur_wc[name]
        n = f"{champ_word} del mundo {reign_world['year']}. {note}" if (champ_key and _norm(name) == champ_key) else note
        row = _base(name, cc3)
        row.update({"rank": i + 1, "age": age, "activeScore": nivel,
                    "legendScore": round((oly * W_OLYMPIC + wc * W_WORLD) / max_raw * 100, 1),
                    "olympicGold": oly, "worldGold": wc, "note": n})
        ranking.append(row)

    # Si el campeón vigente NO está en el ranking curado (que va a mano y no siempre
    # está al día), se inyecta arriba con su palmarés real descargado.
    if champ_key and not any(_norm(r["name"]) == champ_key for r in ranking):
        cw = wc_of(reign_world["name"])
        oly = CURRENT_OLY.get(reign_world["name"], 0)
        champ = _base(reign_world["name"], reign_world["country"])
        champ.update({"age": None, "activeScore": 96,
                      "legendScore": round((oly * W_OLYMPIC + cw * W_WORLD) / max_raw * 100, 1),
                      "olympicGold": oly, "worldGold": cw,
                      "note": f"{champ_word} del mundo {reign_world['year']}"})
        ranking.append(champ)
    ranking.sort(key=lambda r: -r["activeScore"])
    for i, r in enumerate(ranking):
        r["rank"] = i + 1

    return {"id": ev["id"], "weapon": ev["weapon"], "gender": ev["gender"],
            "label": ev["label"], "RANKING": ranking, "LEGENDS": legends,
            "reignWorld": reign_world, "_maxRaw": max_raw}


def build_road_to_glory(events: list) -> list:
    """Activos ordenados por cercanía a las leyendas de SU arma (legendScore→gap)."""
    rows = []
    for ev in events:
        for r in ev["RANKING"]:
            oly, wc = r["olympicGold"], r["worldGold"]
            legend = r["legendScore"]
            gap = round(max(0.0, 100.0 - legend), 1)
            row = _base(r["name"], r["country"])
            row.update({
                "weapon": ev["weapon"], "label": ev["label"], "age": r.get("age"),
                "activeScore": r["activeScore"], "legendScore": legend,
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


def build_prospects(max_age: int = 25, top_n: int = 8) -> list:
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
    world, cc_map, reign = fetch_world()
    events = [build_event(ev, world, cc_map, reign) for ev in EVENTS_RAW]
    # Orden de visualización: masculino (espada, florete, sable) y luego femenino.
    _order = ["epee-m", "foil-m", "sabre-m", "epee-w", "foil-w", "sabre-w"]
    events.sort(key=lambda e: _order.index(e["id"]) if e["id"] in _order else 99)
    road = build_road_to_glory(events)
    for ev in events:
        ev.pop("_maxRaw", None)
    payload = {
        "UPDATED": updated,
        "SEASON": "Temporada 2025/26",
        "WORLDS": {
            "name": "Campeonato del Mundo de Esgrima 2026",
            "note": "Mundiales en curso: el mejor momento para medir quién es leyenda y quién aspira a serlo.",
        },
        "SOURCE": {"name": "Mundiales descargados (Wikipedia: World Fencing Championships); oros olímpicos estables",
                   "note": "Los Mundiales individuales se cuentan automáticamente; los oros olímpicos son datos históricos curados."},
        "EVENTS": events,
        "ROAD_TO_GLORY": road,
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
