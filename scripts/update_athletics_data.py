#!/usr/bin/env python3
"""Athletics data generator — all-time + current-season top-10 per event.

Model (hybrid, per the product decision):
  * ALL-TIME top 10  — durable, committed Wikipedia seed in
    data_sources/athletics_seed/<event>.json (built by _build_athletics_seed.py).
    Each run merges in any current-season mark good enough to crack the top 10
    (e.g. a new world record at a major meet) and persists the updated seed, so
    the historic list maintains itself when records fall.
  * SEASON top 10    — the current-year World Athletics toplist for each event
    (the canonical season source), fetched fresh every run.

Triggered by the same 6×/day pipeline; World Athletics reflects big-meet marks
(Diamond League, World Champs, Olympics, continentals) within hours.

Writes athletics_data.js only on success; a broad World Athletics outage aborts
without writing so the previous data is kept (CI is continue-on-error).
"""
from __future__ import annotations

import json
import re
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "data_sources" / "athletics_seed"
OUT = ROOT / "athletics_data.js"
CTX = ssl.create_default_context()
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) HermesBot/1.0"}
YEAR = datetime.now(timezone.utc).year
TOP_N = 10

MARK_RE = re.compile(r"^(\d+:)?\d{1,3}\.\d{2}$")
DATE_RE = re.compile(r"^\d{1,2} [A-Z]{3} \d{4}$")
FIELD = {"hj", "pv", "lj", "tj", "sp", "dt", "jt"}  # higher mark is better

# ── group layout + per-event display names / World Athletics path ─────────────
GROUPS = [
    ("velocidad", "Velocidad", "100m · 200m · 400m",
     ["100m_m", "100m_w", "200m_m", "200m_w", "400m_m", "400m_w"]),
    ("vallas", "Vallas", "110m/100m vallas · 400m vallas",
     ["110mh_m", "100mh_w", "400mh_m", "400mh_w"]),
    ("fondo", "Medio Fondo · Fondo · Obstáculos", "800m → 5000m · 3000m obst.",
     ["800m_m", "800m_w", "1500m_m", "1500m_w", "5000m_m", "5000m_w",
      "3000msc_m", "3000msc_w"]),
    ("saltos", "Saltos", "Altura · Pértiga · Longitud · Triple",
     ["hj_m", "hj_w", "pv_m", "pv_w", "lj_m", "lj_w", "tj_m", "tj_w"]),
    ("lanzamientos", "Lanzamientos", "Peso · Disco · Jabalina",
     ["sp_m", "sp_w", "dt_m", "dt_w", "jt_m", "jt_w"]),
]
NAMES = {
    "100m": "100m", "200m": "200m", "400m": "400m",
    "110mh": "110m vallas", "100mh": "100m vallas", "400mh": "400m vallas",
    "800m": "800m", "1500m": "1500m", "5000m": "5000m",
    "3000msc": "3000m obstáculos",
    "hj": "Salto de altura", "pv": "Salto con pértiga", "lj": "Salto de longitud",
    "tj": "Triple salto", "sp": "Lanzamiento de peso", "dt": "Lanzamiento de disco",
    "jt": "Lanzamiento de jabalina",
}
WA_PATH = {
    "100m": "sprints/100-metres", "200m": "sprints/200-metres",
    "400m": "sprints/400-metres",
    "110mh": "hurdles/110-metres-hurdles", "100mh": "hurdles/100-metres-hurdles",
    "400mh": "hurdles/400-metres-hurdles",
    "800m": "middlelong/800-metres", "1500m": "middlelong/1500-metres",
    "5000m": "middlelong/5000-metres",
    "3000msc": "middlelong/3000-metres-steeplechase",
    "hj": "jumps/high-jump", "pv": "jumps/pole-vault", "lj": "jumps/long-jump",
    "tj": "jumps/triple-jump",
    "sp": "throws/shot-put", "dt": "throws/discus-throw", "jt": "throws/javelin-throw",
}

# ── country → flag / colour ───────────────────────────────────────────────────
IOC2ISO = {
    "USA": "us", "JAM": "jm", "KEN": "ke", "ETH": "et", "GBR": "gb", "CAN": "ca",
    "CUB": "cu", "BRA": "br", "BAH": "bs", "TTO": "tt", "NGR": "ng", "NGA": "ng",
    "RSA": "za", "FRA": "fr", "GER": "de", "ITA": "it", "ESP": "es", "POR": "pt",
    "POL": "pl", "CZE": "cz", "NOR": "no", "SWE": "se", "FIN": "fi", "GRE": "gr",
    "UKR": "ua", "BLR": "by", "BUL": "bg", "ROU": "ro", "HUN": "hu", "NED": "nl",
    "BEL": "be", "SUI": "ch", "CHE": "ch", "AUT": "at", "MAR": "ma", "ALG": "dz",
    "TUN": "tn", "QAT": "qa", "BRN": "bh", "BHR": "bh", "UGA": "ug", "BOT": "bw",
    "CIV": "ci", "BDI": "bi", "ERI": "er", "TAN": "tz", "CHN": "cn", "JPN": "jp",
    "IND": "in", "AUS": "au", "NZL": "nz", "MEX": "mx", "COL": "co", "VEN": "ve",
    "ECU": "ec", "DOM": "do", "PUR": "pr", "LCA": "lc", "GRN": "gd", "BAR": "bb",
    "TUR": "tr", "KAZ": "kz", "UZB": "uz", "SLO": "si", "CRO": "hr", "SRB": "rs",
    "EST": "ee", "LAT": "lv", "LTU": "lt", "IRL": "ie", "DEN": "dk", "ISR": "il",
    "EGY": "eg", "ZAM": "zm", "NAM": "na", "GHA": "gh", "KSA": "sa", "CMR": "cm",
    "IVB": "vg", "RUS": "ru", "PAN": "pa", "JOR": "jo",
    # defunct — successor flag, the IOC label still shows so the era is clear
    "URS": "ru", "GDR": "de", "FRG": "de", "TCH": "cz", "ANA": "",
}
COLORS = {
    "USA": "#B22234", "JAM": "#000000", "KEN": "#006600", "ETH": "#078930",
    "GBR": "#012169", "CAN": "#FF0000", "CUB": "#002A8F", "BRA": "#009C3B",
    "NGR": "#008751", "NGA": "#008751", "RSA": "#007749", "FRA": "#002395",
    "GER": "#000000", "GDR": "#000000", "ITA": "#009246", "ESP": "#AA151B",
    "POR": "#006600", "POL": "#DC143C", "CZE": "#11457E", "TCH": "#11457E",
    "NOR": "#EF2B2D", "SWE": "#006AA7", "UKR": "#005BBB", "BUL": "#00966E",
    "ROU": "#002B7F", "NED": "#AE1C28", "SUI": "#D52B1E", "CHE": "#D52B1E",
    "MAR": "#C1272D", "ALG": "#006233", "QAT": "#8A1538", "BRN": "#CE1126",
    "BHR": "#CE1126", "UGA": "#FCDC04", "BOT": "#75AADB", "CHN": "#DE2910",
    "JPN": "#BC002D", "AUS": "#00008B", "VEN": "#CF142B", "DOM": "#002D62",
    "RUS": "#0039A6", "URS": "#CD0000", "CRO": "#FF0000", "LTU": "#FDB913",
    "CMR": "#007A5E", "IVB": "#012169", "ANA": "#888888",
}


def flag(cc):
    iso = IOC2ISO.get((cc or "").upper())
    return f"https://flagcdn.com/24x18/{iso}.png" if iso else ""


def color(cc):
    return COLORS.get((cc or "").upper(), "#4A4745")


def mark_value(mark):
    mark = mark.strip()
    if ":" in mark:
        mm, ss = mark.split(":")
        return int(mm) * 60 + float(ss)
    return float(mark)


def title_name(s):
    parts = []
    for w in s.split():
        if w.isupper() or (w.replace("-", "").replace("'", "").isupper()):
            parts.append("-".join(p.capitalize() for p in w.split("-")))
        else:
            parts.append(w)
    return " ".join(parts)


# ── World Athletics season toplist ────────────────────────────────────────────
def fetch_wa_season(path, gender):
    url = (f"https://worldathletics.org/records/toplists/{path}/outdoor/"
           f"{gender}/senior/{YEAR}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        html = r.read().decode("utf-8", "replace")
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        cells = [c for c in cells if c]
        if not cells:
            continue
        # locate mark, athlete, country, date, venue by content (the wind column
        # is present only on sprints/jumps, so parse positionally by pattern)
        mark = next((c for c in cells if MARK_RE.match(c)), None)
        if not mark:
            continue
        country = next((c for c in cells if re.fullmatch(r"[A-Z]{3}", c)), None)
        dates = [c for c in cells if DATE_RE.match(c)]
        comp_date = dates[-1] if dates else ""          # last date = competition
        venue = next((c for c in cells if "(" in c and any(ch.isalpha()
                      for ch in c)), "")
        # athlete = a name cell (has a space, letters, not venue/date/country)
        athlete = next((c for c in cells if " " in c and re.search(r"[A-Za-z]", c)
                        and "(" not in c and not DATE_RE.match(c)
                        and not MARK_RE.match(c)), "")
        if not athlete or not country:
            continue
        venue = re.sub(r"&#?\w+;", "", venue).strip()
        rows.append({
            "mark": mark,
            "athlete": title_name(athlete),
            "country": country,
            "date": comp_date,
            "year": int(comp_date.split()[-1]) if comp_date else YEAR,
            "venue": venue.split(",")[0].strip() or venue,
        })
        if len(rows) >= TOP_N:
            break
    return rows


# ── merge season marks into the all-time list (and persist the seed) ──────────
def merge_alltime(seed_marks, season_rows, unit):
    combined = [dict(m) for m in seed_marks]
    seen = {(m["athlete"].lower(), m["mark"]) for m in combined}
    for r in season_rows:
        key = (r["athlete"].lower(), r["mark"])
        if key not in seen:
            combined.append({"mark": r["mark"], "athlete": r["athlete"],
                             "country": r["country"], "year": r["year"],
                             "venue": r["venue"]})
            seen.add(key)
    combined.sort(key=lambda m: mark_value(m["mark"]), reverse=(unit == "dist"))
    top = combined[:TOP_N]
    for i, m in enumerate(top, 1):
        m["rank"] = i
    return top


def decorate(rows, date_key):
    out = []
    for m in rows:
        row = {
            "rank": m["rank"], "mark": m["mark"], "athlete": m["athlete"],
            "country": m["country"], "flag": flag(m["country"]),
            "primary": color(m["country"]), "venue": m.get("venue", ""),
        }
        row[date_key] = m.get("year") if date_key == "year" else m.get("date", "")
        out.append(row)
    return out


# ── Leyendas del atletismo (curado, determinista) ────────────────────────────
# El "pilar Leyenda" de la sección: las grandes figuras de la historia del
# atletismo, abarcando disciplinas (velocidad, fondo, maratón, saltos, pértiga,
# multipruebas) y ambos sexos. legendScore es una valoración curada anclada en
# Bolt = 100. El frontend muestra la sección "Leyendas del atletismo" en cuanto
# este array no está vacío.
_ATH_RED = "#C0392B"


def _legend(slug, name, events, cc3, iso2, score, note, active=False):
    return {
        "id": slug, "name": name, "events": events, "country": cc3,
        "logo": f"https://flagcdn.com/24x18/{iso2}.png", "primary": _ATH_RED,
        "legendScore": float(score), "active": active, "note": note,
    }


ATHLETICS_LEGENDS = [
    _legend("usain_bolt", "Usain Bolt", "100 m · 200 m", "JAM", "jm", 100,
            "8 oros olímpicos · récords mundiales de 100 m y 200 m"),
    _legend("eliud_kipchoge", "Eliud Kipchoge", "Maratón", "KEN", "ke", 96,
            "Récord mundial de maratón y primer sub-2 horas; doble oro olímpico"),
    _legend("carl_lewis", "Carl Lewis", "100 m · Salto de longitud", "USA", "us", 96,
            "9 oros olímpicos en cuatro Juegos"),
    _legend("kenenisa_bekele", "Kenenisa Bekele", "5000 m · 10 000 m", "ETH", "et", 95,
            "Récords mundiales de 5000 y 10 000 m"),
    _legend("allyson_felix", "Allyson Felix", "200 m · 400 m", "USA", "us", 94,
            "La atleta con más medallas olímpicas de la historia (11)"),
    _legend("michael_johnson", "Michael Johnson", "200 m · 400 m", "USA", "us", 93,
            "Dobletes 200/400 y récords mundiales legendarios"),
    _legend("haile_gebrselassie", "Haile Gebrselassie", "10 000 m · Maratón", "ETH", "et", 93,
            "27 récords mundiales en pruebas de fondo"),
    _legend("hicham_el_guerrouj", "Hicham El Guerrouj", "1500 m · Milla", "MAR", "ma", 92,
            "Récords de 1500 m y milla aún vigentes"),
    _legend("sergey_bubka", "Sergey Bubka", "Pértiga", "UKR", "ua", 92,
            "35 récords mundiales de salto con pértiga"),
    _legend("jackie_joyner_kersee", "Jackie Joyner-Kersee", "Heptatlón · Longitud", "USA", "us", 92,
            "Récord mundial de heptatlón aún vigente"),
    _legend("florence_griffith_joyner", "Florence Griffith-Joyner", "100 m · 200 m", "USA", "us", 91,
            "Récords mundiales de 100 y 200 m intactos desde 1988"),
    _legend("mondo_duplantis", "Mondo Duplantis", "Pértiga", "SWE", "se", 90,
            "Plusmarquista mundial en activo y oro olímpico", active=True),
]


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    groups_out = []
    new_records = []
    wa_fail = 0
    wa_total = 0

    for gid, label, sub, ev_ids in GROUPS:
        events = []
        for ev in ev_ids:
            base, gender_sfx = ev.rsplit("_", 1)
            gender = "men" if gender_sfx == "m" else "women"
            unit = "dist" if base in FIELD else "time"
            seed_path = SEED_DIR / f"{ev}.json"
            if not seed_path.exists():
                print(f"[WARN] missing seed {ev}")
                continue
            seed = json.loads(seed_path.read_text(encoding="utf-8"))
            seed_marks = seed["marks"]

            wa_total += 1
            try:
                season_rows = fetch_wa_season(WA_PATH[base], gender)
            except Exception as e:
                wa_fail += 1
                season_rows = []
                print(f"[WARN] WA {ev}: {str(e)[:80]}")

            merged = merge_alltime(seed_marks, season_rows, unit)
            # persist seed if the historic top 10 changed (a record fell)
            old_sig = [(m["mark"], m["athlete"]) for m in seed_marks]
            new_sig = [(m["mark"], m["athlete"]) for m in merged]
            if new_sig != old_sig:
                seed["marks"] = [{k: m[k] for k in
                                  ("rank", "mark", "athlete", "country", "year",
                                   "date", "venue") if k in m} for m in merged]
                seed_path.write_text(json.dumps(seed, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
                if new_sig[0] != old_sig[0]:
                    new_records.append(f"{NAMES[base]} {gender_sfx.upper()}: "
                                       f"{merged[0]['mark']} {merged[0]['athlete']}")
                print(f"  [seed↑] {ev}: #1 {merged[0]['mark']} {merged[0]['athlete']}")

            wr = merged[0]
            events.append({
                "id": ev,
                "name": f"{NAMES[base]} — {'H' if gender == 'men' else 'M'}",
                "gender": "M" if gender == "men" else "W",
                "unit": unit,
                "wr": {"mark": wr["mark"], "athlete": wr["athlete"],
                       "country": wr["country"], "year": wr.get("year"),
                       "flag": flag(wr["country"])},
                "allTime": decorate(merged, "year"),
                "season": decorate([dict(r, rank=i + 1)
                                    for i, r in enumerate(season_rows)], "date"),
            })
        groups_out.append({"id": gid, "label": label, "sub": sub, "events": events})

    if wa_total and wa_fail > wa_total // 3:
        sys.exit(f"World Athletics broadly unavailable ({wa_fail}/{wa_total} "
                 f"failed) — keeping previous athletics data.")

    data = {
        "UPDATED": stamp,
        "SEASON": YEAR,
        "IMPORTANCE": 7,
        "GROUPS": groups_out,
        "NEW_RECORDS": new_records,
        "LEGENDS": ATHLETICS_LEGENDS,
    }
    OUT.write_text("// Auto-generated " + stamp + "\nwindow.ATHLETICS_DATA = "
                   + json.dumps(data, ensure_ascii=False, indent=2) + ";\n",
                   encoding="utf-8")
    ev_count = sum(len(g["events"]) for g in groups_out)
    print(f"\nWritten: {OUT}")
    print(f"  {ev_count} events · {len(new_records)} new records · "
          f"WA failures {wa_fail}/{wa_total}")
    for nr in new_records:
        print(f"  ★ {nr}")


if __name__ == "__main__":
    main()
