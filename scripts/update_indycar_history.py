#!/usr/bin/env python3
"""IndyCar · Road to Glory histórico: puntos ABSOLUTOS y acumulativos (nadie baja).

A diferencia del score de leyenda normalizado (líder = 100, que baja cuando alguien
te supera), aquí los puntos solo suben o se quedan planos. Baremo:
    Campeonato ×30 · Indy 500 ×18 (además de contar como victoria) ·
    Victoria ×3 · Pole ×1 · Salida ×0,1

Datos históricos (campeones y ganadores de Indy 500, 1909-2026) contrastados con
el Historical Record Book de IndyCar + Wikipedia. Todos los organismos de la máxima
categoría cuentan (AAA/USAC/CART/Champ Car/IRL/IndyCar). Estático: se actualiza una
vez por temporada.
"""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "indycar_history_data.js"

BAREMO = {"title": 30.0, "indy500": 18.0, "win": 3.0, "pole": 1.0, "start": 0.1}

# ── Campeón nacional por año (nombre, organismo). Era escindida 1996-2007: dos. ──
# Organismos: AAA, USAC, CART, CC (Champ Car), IRL, IC (IndyCar unificado).
CHAMPIONS = {
    1909: [("George Robertson", "AAA")], 1910: [("Ray Harroun", "AAA")],
    1911: [("Ralph Mulford", "AAA")], 1912: [("Ralph DePalma", "AAA")],
    1913: [("Earl Cooper", "AAA")], 1914: [("Ralph DePalma", "AAA")],
    1915: [("Earl Cooper", "AAA")], 1916: [("Dario Resta", "AAA")],
    1917: [("Earl Cooper", "AAA")], 1918: [("Ralph Mulford", "AAA")],
    1919: [("Howard Wilcox", "AAA")], 1920: [("Gaston Chevrolet", "AAA")],
    1921: [("Tommy Milton", "AAA")], 1922: [("Jimmy Murphy", "AAA")],
    1923: [("Eddie Hearne", "AAA")], 1924: [("Jimmy Murphy", "AAA")],
    1925: [("Peter DePaolo", "AAA")], 1926: [("Harry Hartz", "AAA")],
    1927: [("Peter DePaolo", "AAA")], 1928: [("Louis Meyer", "AAA")],
    1929: [("Louis Meyer", "AAA")], 1930: [("Billy Arnold", "AAA")],
    1931: [("Louis Schneider", "AAA")], 1932: [("Bob Carey", "AAA")],
    1933: [("Louis Meyer", "AAA")], 1934: [("Bill Cummings", "AAA")],
    1935: [("Kelly Petillo", "AAA")], 1936: [("Mauri Rose", "AAA")],
    1937: [("Wilbur Shaw", "AAA")], 1938: [("Floyd Roberts", "AAA")],
    1939: [("Wilbur Shaw", "AAA")], 1940: [("Rex Mays", "AAA")],
    1941: [("Rex Mays", "AAA")],
    1946: [("Ted Horn", "AAA")], 1947: [("Ted Horn", "AAA")],
    1948: [("Ted Horn", "AAA")], 1949: [("Johnnie Parsons", "AAA")],
    1950: [("Henry Banks", "AAA")], 1951: [("Tony Bettenhausen", "AAA")],
    1952: [("Chuck Stevenson", "AAA")], 1953: [("Sam Hanks", "AAA")],
    1954: [("Jimmy Bryan", "AAA")], 1955: [("Bob Sweikert", "AAA")],
    1956: [("Jimmy Bryan", "USAC")], 1957: [("Jimmy Bryan", "USAC")],
    1958: [("Tony Bettenhausen", "USAC")], 1959: [("Rodger Ward", "USAC")],
    1960: [("A. J. Foyt", "USAC")], 1961: [("A. J. Foyt", "USAC")],
    1962: [("Rodger Ward", "USAC")], 1963: [("A. J. Foyt", "USAC")],
    1964: [("A. J. Foyt", "USAC")], 1965: [("Mario Andretti", "USAC")],
    1966: [("Mario Andretti", "USAC")], 1967: [("A. J. Foyt", "USAC")],
    1968: [("Bobby Unser", "USAC")], 1969: [("Mario Andretti", "USAC")],
    1970: [("Al Unser", "USAC")], 1971: [("Joe Leonard", "USAC")],
    1972: [("Joe Leonard", "USAC")], 1973: [("Roger McCluskey", "USAC")],
    1974: [("Bobby Unser", "USAC")], 1975: [("A. J. Foyt", "USAC")],
    1976: [("Gordon Johncock", "USAC")], 1977: [("Tom Sneva", "USAC")],
    1978: [("Tom Sneva", "USAC")],
    1979: [("Rick Mears", "CART"), ("A. J. Foyt", "USAC")],
    1980: [("Johnny Rutherford", "CART")],
    1981: [("Rick Mears", "CART")], 1982: [("Rick Mears", "CART")],
    1983: [("Al Unser", "CART")], 1984: [("Mario Andretti", "CART")],
    1985: [("Al Unser", "CART")], 1986: [("Bobby Rahal", "CART")],
    1987: [("Bobby Rahal", "CART")], 1988: [("Danny Sullivan", "CART")],
    1989: [("Emerson Fittipaldi", "CART")], 1990: [("Al Unser Jr.", "CART")],
    1991: [("Michael Andretti", "CART")], 1992: [("Bobby Rahal", "CART")],
    1993: [("Nigel Mansell", "CART")], 1994: [("Al Unser Jr.", "CART")],
    1995: [("Jacques Villeneuve", "CART")],
    1996: [("Jimmy Vasser", "CART"), ("Scott Sharp", "IRL")],
    1997: [("Alex Zanardi", "CART"), ("Tony Stewart", "IRL")],
    1998: [("Alex Zanardi", "CART"), ("Kenny Bräck", "IRL")],
    1999: [("Juan Pablo Montoya", "CART"), ("Greg Ray", "IRL")],
    2000: [("Gil de Ferran", "CART"), ("Buddy Lazier", "IRL")],
    2001: [("Gil de Ferran", "CART"), ("Sam Hornish Jr.", "IRL")],
    2002: [("Cristiano da Matta", "CART"), ("Sam Hornish Jr.", "IRL")],
    2003: [("Paul Tracy", "CART"), ("Scott Dixon", "IRL")],
    2004: [("Sébastien Bourdais", "CC"), ("Tony Kanaan", "IRL")],
    2005: [("Sébastien Bourdais", "CC"), ("Dan Wheldon", "IRL")],
    2006: [("Sébastien Bourdais", "CC"), ("Sam Hornish Jr.", "IRL")],
    2007: [("Sébastien Bourdais", "CC"), ("Dario Franchitti", "IRL")],
    2008: [("Scott Dixon", "IRL")], 2009: [("Dario Franchitti", "IRL")],
    2010: [("Dario Franchitti", "IRL")], 2011: [("Dario Franchitti", "IC")],
    2012: [("Ryan Hunter-Reay", "IC")], 2013: [("Scott Dixon", "IC")],
    2014: [("Will Power", "IC")], 2015: [("Scott Dixon", "IC")],
    2016: [("Simon Pagenaud", "IC")], 2017: [("Josef Newgarden", "IC")],
    2018: [("Scott Dixon", "IC")], 2019: [("Josef Newgarden", "IC")],
    2020: [("Scott Dixon", "IC")], 2021: [("Álex Palou", "IC")],
    2022: [("Will Power", "IC")], 2023: [("Álex Palou", "IC")],
    2024: [("Álex Palou", "IC")], 2025: [("Álex Palou", "IC")],
    2026: [("Álex Palou", "IC")],
}

# ── Ganador de Indy 500 por año (no disputada 1917-18, 1942-45). ──
INDY500 = {
    1911: "Ray Harroun", 1912: "Joe Dawson", 1913: "Jules Goux", 1914: "René Thomas",
    1915: "Ralph DePalma", 1916: "Dario Resta", 1919: "Howdy Wilcox",
    1920: "Gaston Chevrolet", 1921: "Tommy Milton", 1922: "Jimmy Murphy",
    1923: "Tommy Milton", 1924: "L. L. Corum / Joe Boyer", 1925: "Pete DePaolo",
    1926: "Frank Lockhart", 1927: "George Souders", 1928: "Louis Meyer",
    1929: "Ray Keech", 1930: "Billy Arnold", 1931: "Louis Schneider",
    1932: "Fred Frame", 1933: "Louis Meyer", 1934: "Bill Cummings",
    1935: "Kelly Petillo", 1936: "Louis Meyer", 1937: "Wilbur Shaw",
    1938: "Floyd Roberts", 1939: "Wilbur Shaw", 1940: "Wilbur Shaw",
    1941: "Mauri Rose", 1946: "George Robson", 1947: "Mauri Rose",
    1948: "Mauri Rose", 1949: "Bill Holland", 1950: "Johnnie Parsons",
    1951: "Lee Wallard", 1952: "Troy Ruttman", 1953: "Bill Vukovich",
    1954: "Bill Vukovich", 1955: "Bob Sweikert", 1956: "Pat Flaherty",
    1957: "Sam Hanks", 1958: "Jimmy Bryan", 1959: "Rodger Ward",
    1960: "Jim Rathmann", 1961: "A. J. Foyt", 1962: "Rodger Ward",
    1963: "Parnelli Jones", 1964: "A. J. Foyt", 1965: "Jim Clark",
    1966: "Graham Hill", 1967: "A. J. Foyt", 1968: "Bobby Unser",
    1969: "Mario Andretti", 1970: "Al Unser", 1971: "Al Unser",
    1972: "Mark Donohue", 1973: "Gordon Johncock", 1974: "Johnny Rutherford",
    1975: "Bobby Unser", 1976: "Johnny Rutherford", 1977: "A. J. Foyt",
    1978: "Al Unser", 1979: "Rick Mears", 1980: "Johnny Rutherford",
    1981: "Bobby Unser", 1982: "Gordon Johncock", 1983: "Tom Sneva",
    1984: "Rick Mears", 1985: "Danny Sullivan", 1986: "Bobby Rahal",
    1987: "Al Unser", 1988: "Rick Mears", 1989: "Emerson Fittipaldi",
    1990: "Arie Luyendyk", 1991: "Rick Mears", 1992: "Al Unser Jr.",
    1993: "Emerson Fittipaldi", 1994: "Al Unser Jr.", 1995: "Jacques Villeneuve",
    1996: "Buddy Lazier", 1997: "Arie Luyendyk", 1998: "Eddie Cheever",
    1999: "Kenny Bräck", 2000: "Juan Pablo Montoya", 2001: "Hélio Castroneves",
    2002: "Hélio Castroneves", 2003: "Gil de Ferran", 2004: "Buddy Rice",
    2005: "Dan Wheldon", 2006: "Sam Hornish Jr.", 2007: "Dario Franchitti",
    2008: "Scott Dixon", 2009: "Hélio Castroneves", 2010: "Dario Franchitti",
    2011: "Dan Wheldon", 2012: "Dario Franchitti", 2013: "Tony Kanaan",
    2014: "Ryan Hunter-Reay", 2015: "Juan Pablo Montoya", 2016: "Alexander Rossi",
    2017: "Takuma Sato", 2018: "Will Power", 2019: "Simon Pagenaud",
    2020: "Takuma Sato", 2021: "Hélio Castroneves", 2022: "Marcus Ericsson",
    2023: "Josef Newgarden", 2024: "Josef Newgarden", 2025: "Álex Palou",
    2026: "Felix Rosenqvist",
}

# ── Totales de carrera de las leyendas (todos los organismos combinados) ──
# (nombre, cc3, año_nac, títulos, indy500s, victorias, poles, salidas, activo)
LEGENDS_RAW = [
    ("A. J. Foyt",         "USA", 1935, 7, 4, 67, 53, 369, False),
    ("Scott Dixon",        "NZL", 1980, 6, 1, 59, 32, 430, True),
    ("Mario Andretti",     "USA", 1940, 4, 1, 52, 65, 407, False),
    ("Al Unser",           "USA", 1939, 3, 4, 39, 28, 321, False),
    ("Dario Franchitti",   "GBR", 1973, 4, 3, 31, 34, 265, False),
    ("Rick Mears",         "USA", 1951, 3, 4, 29, 40, 203, False),
    ("Will Power",         "AUS", 1981, 2, 1, 45, 71, 304, True),
    ("Bobby Unser",        "USA", 1934, 2, 3, 35, 52, 258, False),
    ("Sébastien Bourdais", "FRA", 1979, 4, 0, 37, 34, 224, False),
    ("Álex Palou",         "ESP", 1997, 5, 1, 25, 20, 115, True),
    ("Hélio Castroneves",  "BRA", 1975, 0, 4, 31, 55, 395, True),
    ("Josef Newgarden",    "USA", 1990, 2, 2, 35, 19, 244, True),
    ("Al Unser Jr.",       "USA", 1962, 2, 2, 34, 7, 329, False),
    ("Bobby Rahal",        "USA", 1953, 3, 1, 24, 18, 264, False),
    ("Johnny Rutherford",  "USA", 1938, 1, 3, 27, 23, 314, False),
    ("Michael Andretti",   "USA", 1962, 1, 0, 42, 32, 309, False),
    ("Sam Hornish Jr.",    "USA", 1979, 3, 1, 19, 12, 116, False),
    ("Jimmy Bryan",        "USA", 1926, 3, 1, 23, 3, 72, False),
    ("Gordon Johncock",    "USA", 1936, 1, 2, 25, 20, 262, False),
    ("Paul Tracy",         "CAN", 1968, 1, 0, 31, 25, 294, False),
    ("Ralph DePalma",      "USA", 1882, 2, 1, 25, 9, 100, False),
    ("Louis Meyer",        "USA", 1904, 3, 3, 8, 0, 33, False),
    ("Emerson Fittipaldi", "BRA", 1946, 1, 2, 22, 17, 195, False),
    ("Earl Cooper",        "USA", 1886, 3, 0, 21, 3, 89, False),
    ("Ted Horn",           "USA", 1910, 3, 0, 24, 7, 72, False),
    ("Tony Kanaan",        "BRA", 1974, 1, 1, 17, 15, 389, False),
    ("Tom Sneva",          "USA", 1948, 2, 1, 13, 14, 205, False),
    ("Tony Bettenhausen",  "USA", 1916, 2, 0, 22, 13, 118, False),
    ("Gil de Ferran",      "BRA", 1967, 2, 1, 10, 21, 160, False),
    ("Juan Pablo Montoya", "COL", 1975, 1, 2, 15, 17, 97, False),
    ("Jimmy Murphy",       "USA", 1894, 2, 1, 17, 7, 52, False),
    ("Tommy Milton",       "USA", 1893, 1, 2, 20, 5, 102, False),
    ("Wilbur Shaw",        "USA", 1902, 2, 3, 6, 1, 38, False),
    ("Danny Sullivan",     "USA", 1950, 1, 1, 17, 19, 171, False),
    ("Ralph Mulford",      "USA", 1885, 2, 0, 19, 0, 87, False),
    ("Ryan Hunter-Reay",   "USA", 1980, 1, 1, 16, 6, 252, False),
    ("Simon Pagenaud",     "FRA", 1984, 1, 1, 15, 13, 207, False),
    ("Alex Zanardi",       "ITA", 1966, 2, 0, 15, 10, 66, False),
    ("Rex Mays",           "USA", 1913, 2, 0, 8, 19, 57, False),
    ("Jimmy Vasser",       "USA", 1965, 1, 0, 10, 8, 233, False),
    ("Johnnie Parsons",    "USA", 1918, 1, 1, 11, 1, 61, False),
    ("Nigel Mansell",      "GBR", 1953, 1, 0, 5, 9, 31, False),
    ("Bill Vukovich",      "USA", 1918, 0, 2, 4, 3, 22, False),
    ("Dan Wheldon",        "GBR", 1978, 1, 2, 16, 5, 128, False),
    ("Peter DePaolo",      "USA", 1898, 2, 1, 10, 5, 55, False),
    ("Arie Luyendyk",      "NED", 1953, 0, 2, 7, 8, 169, False),
    ("Jacques Villeneuve", "CAN", 1971, 1, 1, 5, 6, 33, False),
]


CC2 = {"USA": "us", "NZL": "nz", "GBR": "gb", "BRA": "br", "ESP": "es", "COL": "co",
       "FRA": "fr", "CAN": "ca", "ITA": "it", "SWE": "se", "JPN": "jp", "AUS": "au", "NED": "nl"}
COLORS = {"USA": "#B22234", "NZL": "#00247D", "GBR": "#012169", "BRA": "#009C3B",
          "ESP": "#AA151B", "COL": "#FCD116", "FRA": "#002395", "CAN": "#FF0000",
          "ITA": "#009246", "SWE": "#006AA7", "JPN": "#BC002D", "AUS": "#00008B", "NED": "#AE1C28"}


def flag(cc3): c = CC2.get(cc3, ""); return f"https://flagcdn.com/24x18/{c}.png" if c else ""
def _slug(n): return re.sub(r"[^a-z0-9]+", "_", n.lower()).strip("_")
def abs_score(titles, indy500s, wins, poles, starts):
    return round(titles * BAREMO["title"] + indy500s * BAREMO["indy500"]
                 + wins * BAREMO["win"] + poles * BAREMO["pole"] + starts * BAREMO["start"], 1)


def build_legends():
    rows = []
    for name, cc3, born, titles, indy500s, wins, poles, starts, active in LEGENDS_RAW:
        rows.append({
            "id": _slug(name), "name": name, "country": cc3, "logo": flag(cc3),
            "primary": COLORS.get(cc3, "#555"), "active": active,
            "score": abs_score(titles, indy500s, wins, poles, starts),
            "stats": {"titles": titles, "indy500s": indy500s, "wins": wins,
                      "poles": poles, "starts": starts, "birth": born},
        })
    rows.sort(key=lambda r: -r["score"])
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows


def build_years():
    out = []
    for y in sorted(CHAMPIONS):
        champs = [{"name": n, "body": b} for n, b in CHAMPIONS[y]]
        out.append({"year": y, "champions": champs, "indy500": INDY500.get(y)})
    return out


def main():
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "UPDATED": updated,
        "BAREMO": BAREMO,
        "BAREMO_LABEL": "Campeonato ×30 · Indy 500 ×18 · Victoria ×3 · Pole ×1 · Salida ×0,1",
        "LEGENDS": build_legends(),
        "YEARS": build_years(),
    }
    OUT.write_text(f"// Auto-generated {updated}\nwindow.INDYCAR_HISTORY = "
                   f"{json.dumps(payload, ensure_ascii=False, indent=2)};\n", encoding="utf-8")
    print(f"Wrote {OUT.name} · {len(payload['YEARS'])} años · {len(payload['LEGENDS'])} leyendas")


if __name__ == "__main__":
    main()
