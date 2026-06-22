#!/usr/bin/env python3
"""Build the all-time top-10 seed for athletics from Wikipedia.

One-time / refreshable source for the *historic* all-time lists. The live
generator (update_athletics_data.py) loads these seeds and only splices in new
marks that crack the top 10 during the season, so this scraper does NOT need to
run on every data refresh — it is the durable foundation.

Output: data_sources/athletics_seed/<event_id>.json
  { "event": "100m_m", "label": "100m — H", "unit": "time",
    "marks": [ {rank, mark, athlete, country, year, date, venue}, ... ] }

Wikipedia all-time tables count *performances* (the same athlete can appear
several times), which is exactly "los 10 mejores registros" of each event.
"""
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "data_sources" / "athletics_seed"
CTX = ssl.create_default_context()
UA = {"User-Agent": "HermesBot/1.0 (https://github.com/hermes; sports dashboard seed)"}
TOP_N = 10

# event_id -> (wikipedia page, gender_word, unit)
#   gender_word: which "All-time top N <men|women>" section to read
#   unit: "time" (track) or "dist" (field) — only used downstream for sorting
EVENTS = {
    "100m_m":   ("100 metres", "men", "time"),
    "100m_w":   ("100 metres", "women", "time"),
    "200m_m":   ("200 metres", "men", "time"),
    "200m_w":   ("200 metres", "women", "time"),
    "400m_m":   ("400 metres", "men", "time"),
    "400m_w":   ("400 metres", "women", "time"),
    "110mh_m":  ("110 metres hurdles", "men", "time"),
    "100mh_w":  ("100 metres hurdles", "women", "time"),
    "400mh_m":  ("400 metres hurdles", "men", "time"),
    "400mh_w":  ("400 metres hurdles", "women", "time"),
    "800m_m":   ("800 metres", "men", "time"),
    "800m_w":   ("800 metres", "women", "time"),
    "1500m_m":  ("1500 metres", "men", "time"),
    "1500m_w":  ("1500 metres", "women", "time"),
    "5000m_m":  ("5000 metres", "men", "time"),
    "5000m_w":  ("5000 metres", "women", "time"),
    "3000msc_m": ("3000 metres steeplechase", "men", "time"),
    "3000msc_w": ("3000 metres steeplechase", "women", "time"),
    "hj_m":     ("High jump", "men", "dist"),
    "hj_w":     ("High jump", "women", "dist"),
    "pv_m":     ("Pole vault", "men", "dist"),
    "pv_w":     ("Pole vault", "women", "dist"),
    "lj_m":     ("Long jump", "men", "dist"),
    "lj_w":     ("Long jump", "women", "dist"),
    "tj_m":     ("Triple jump", "men", "dist"),
    "tj_w":     ("Triple jump", "women", "dist"),
    "sp_m":     ("Shot put", "men", "dist"),
    "sp_w":     ("Shot put", "women", "dist"),
    "dt_m":     ("Discus throw", "men", "dist"),
    "dt_w":     ("Discus throw", "women", "dist"),
    "jt_m":     ("Javelin throw", "men", "dist"),
    "jt_w":     ("Javelin throw", "women", "dist"),
}

MONTHS = ("January|February|March|April|May|June|July|August|"
          "September|October|November|December")
MARK_RE = re.compile(r"^(\d+:)?\d{1,3}\.\d{2}(?!\d)")  # 9.58 / 1:40.91 / 74.08
WIND_RE = re.compile(r"^[+\-−±]?\d+\.\d+$")             # wind/reaction columns
TECH_RE = re.compile(r"^(glide|spin|rotational|rotation|o'?brien)$", re.I)  # shot put
CALC_RE = re.compile(r"\{\{\s*(?:T&Fcalc\w*|Time)\s*\|\s*([0-9:.]+)")

# country name -> IOC code (field-event tables use {{flagu|Name}} not {{CODE}})
NAME2IOC = {
    "United States": "USA", "Jamaica": "JAM", "Kenya": "KEN", "Ethiopia": "ETH",
    "Great Britain": "GBR", "Great Britain & N.I.": "GBR",
    "United Kingdom": "GBR", "Canada": "CAN", "Cuba": "CUB", "Brazil": "BRA",
    "Bahamas": "BAH", "Trinidad and Tobago": "TTO", "Nigeria": "NGR",
    "South Africa": "RSA", "France": "FRA", "Germany": "GER",
    "East Germany": "GDR", "West Germany": "FRG", "Soviet Union": "URS",
    "Russia": "RUS", "Italy": "ITA", "Spain": "ESP", "Portugal": "POR",
    "Poland": "POL", "Czech Republic": "CZE", "Czechoslovakia": "TCH",
    "Norway": "NOR", "Sweden": "SWE", "Finland": "FIN", "Greece": "GRE",
    "Ukraine": "UKR", "Belarus": "BLR", "Bulgaria": "BUL", "Romania": "ROU",
    "Hungary": "HUN", "Netherlands": "NED", "Belgium": "BEL",
    "Switzerland": "SUI", "Austria": "AUT", "Morocco": "MAR", "Algeria": "ALG",
    "Tunisia": "TUN", "Qatar": "QAT", "Bahrain": "BRN", "Uganda": "UGA",
    "Botswana": "BOT", "Ivory Coast": "CIV", "Côte d'Ivoire": "CIV",
    "Burundi": "BDI", "Eritrea": "ERI", "Tanzania": "TAN", "China": "CHN",
    "Japan": "JPN", "India": "IND", "Australia": "AUS", "New Zealand": "NZL",
    "Mexico": "MEX", "Colombia": "COL", "Venezuela": "VEN", "Ecuador": "ECU",
    "Dominican Republic": "DOM", "Puerto Rico": "PUR", "Saint Lucia": "LCA",
    "Grenada": "GRN", "Barbados": "BAR", "Turkey": "TUR", "Türkiye": "TUR",
    "Iran": "IRI", "Kazakhstan": "KAZ", "Uzbekistan": "UZB", "Slovenia": "SLO",
    "Croatia": "CRO", "Serbia": "SRB", "Estonia": "EST", "Latvia": "LAT",
    "Lithuania": "LTU", "Iceland": "ISL", "Ireland": "IRL", "Denmark": "DEN",
    "Israel": "ISR", "Egypt": "EGY", "Zambia": "ZAM", "Zimbabwe": "ZIM",
    "Namibia": "NAM", "Mozambique": "MOZ", "Senegal": "SEN", "Ghana": "GHA",
    "Sudan": "SUD", "South Sudan": "SSD", "Slovakia": "SVK", "Moldova": "MDA",
    "North Korea": "PRK", "South Korea": "KOR", "Chinese Taipei": "TPE",
    "Saudi Arabia": "KSA", "Panama": "PAN", "Guyana": "GUY", "Surinam": "SUR",
    "Suriname": "SUR", "Cyprus": "CYP", "Liechtenstein": "LIE",
}


def api(page, **params):
    base = "https://en.wikipedia.org/w/api.php"
    q = {"action": "parse", "page": page, "format": "json", **params}
    url = base + "?" + urllib.parse.urlencode(q)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))
    return None


def find_section(page, gender_word):
    """Return the section index of the 'All-time top N <gender>' table.

    Two article layouts exist:
      A) flat: a section titled e.g. "All-time top 25 men" / "... women".
      B) nested: a parent "All-time top 25" with child "Men"/"Women"
         subsections (track articles use A, field articles use B).
    """
    secs = api(page, prop="sections")["parse"]["sections"]
    # A) gender word present in the all-time heading itself (word-boundary so
    #    "men" does not match inside "women").
    for s in secs:
        line = s["line"].lower()
        if "all" in line and "time" in line and re.search(rf"\b{gender_word}\b", line):
            return s["index"]
    # B) all-time parent -> gendered child subsection by number hierarchy.
    #    Children are titled e.g. "Men" or "Men (outdoor)"/"Men (indoor)";
    #    prefer outdoor (the standard record), never indoor.
    for s in secs:
        line = s["line"].lower()
        if "all" in line and "time" in line:
            parent = s["number"]
            children = [c for c in secs if c["number"].startswith(parent + ".")]
            outdoor = [c for c in children
                       if re.match(rf"{gender_word}\b", c["line"].strip().lower())
                       and "indoor" not in c["line"].lower()]
            if outdoor:
                return outdoor[0]["index"]
            return s["index"]  # single-gender all-time table
    return None


def clean_cell(cell):
    cell = re.sub(r"<ref[^>]*>.*?</ref>", "", cell, flags=re.S)
    cell = re.sub(r"<ref[^>]*/>", "", cell)
    cell = cell.replace("{{0}}", "").replace("&nbsp;", " ")  # alignment padding
    cell = re.sub(r"^\s*(?:rowspan|colspan|align|bgcolor|style|class|width|"
                  r"scope|valign|data-sort-value)\s*=\s*[^|]*\|", "", cell,
                  flags=re.I)
    return cell.strip()


def extract_name(cell, prev):
    """Athlete name from one cell. `prev` is the previous row's full name, used
    to expand repeat-performance rows ('Vetter #2') back to the full name."""
    m = re.search(r"\{\{[Ss]ortname\|([^|}]+)\|([^|}]+)", cell)
    if m:
        name = f"{m.group(1).strip()} {m.group(2).strip()}"
    else:
        m = re.search(r"\{\{[Ss]ort\|([^|}]+)", cell)
        if m:
            key = m.group(1).strip()
            name = (f"{key.split(',', 1)[1].strip()} {key.split(',', 1)[0].strip()}"
                    if "," in key else key)
        else:
            m = re.search(r"\[\[(?:[^\]|]+\|)?([^\]|]+)\]\]", cell)
            if m:
                name = m.group(1).strip()
            else:
                m = re.search(r"'{2,}([^']+?)'{2,}", cell)
                name = (m.group(1) if m
                        else re.sub(r"\{\{[^}]*\}\}|'+", "", cell)).strip()
    name = re.sub(r"#\s*\d+", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    if (prev and name and len(name.split()) == 1
            and prev.split()[-1].lower() == name.lower()):
        return prev
    return name


def parse_country(cell):
    # {{JAM}} / {{GBR2}} / {{ETH|1996}} — template name is the IOC code (+ flag
    # variant digit and/or a historical-flag year param)
    m = re.search(r"\{\{([A-Z]{2,3})\d?(?:\|[^}]*)?\}\}", cell)
    if m:
        return m.group(1)
    # {{flagIOC|JAM}} / {{flagathlete|Name|JAM}} — explicit code
    m = re.search(r"flag(?:IOC|athlete|icon)?\|(?:[^|}]*\|)?([A-Z]{3})\b", cell)
    if m:
        return m.group(1)
    # {{flagu|United States}} / {{flag|Jamaica}} — country name (field articles)
    m = re.search(r"\{\{flag[a-z]*\|([^}|]+)", cell)
    if m:
        return NAME2IOC.get(m.group(1).strip())
    # {{Canada}} / {{Kenya}} — pipeless country-name template (recent edits)
    m = re.search(r"\{\{([A-Z][A-Za-z .'&-]+?)\}\}", cell)
    if m:
        return NAME2IOC.get(m.group(1).strip())
    return None


def parse_date(row):
    m = re.search(rf"(\d{{1,2}})\s+({MONTHS})\s+(\d{{4}})", row)
    if m:
        return m.group(0), int(m.group(3))
    m = re.search(rf"({MONTHS})\s+(\d{{1,2}}),?\s+(\d{{4}})", row)
    if m:
        return m.group(0), int(m.group(3))
    return "", None


def parse_venue(row, after):
    seg = row[after:] if after else row
    for m in re.finditer(r"\[\[(?:[^\]|]+\|)?([^\]|]+)\]\]", seg):
        v = m.group(1).strip()
        if v and not re.match(r"^\d", v):
            return v
    return ""


def parse_table(wikitext):
    """Parse rows positionally: columns are
    rank(s) | Mark | [Wind] | [Reaction] | Athlete | Nation | Date | Place."""
    rows = re.split(r"\n\|-", wikitext)
    out = []
    hints = {}  # surname -> (full name, country) harvested from mark-less rows
    last_country = None
    last_name = None
    for raw in rows:
        if "{{" not in raw and "[[" not in raw:
            continue
        cells = [clean_cell(c) for c in re.split(r"\|\||\n\|", raw)]
        # 1) mark = first cell matching the mark pattern (unwrap {{T&Fcalc…}})
        midx = None
        mark = None
        for i, c in enumerate(cells):
            tm = CALC_RE.search(c)
            cc = tm.group(1) if tm else c
            mm = MARK_RE.match(cc)
            if mm:
                midx, mark = i, mm.group(0)
                break
        if mark is None:
            # Mark-less continuation row (rank/mark rowspanned elsewhere) still
            # carries the athlete's full name + country — harvest it so the
            # mark-bearing sibling (surname-only, blank country) can be filled.
            nm = next((extract_name(c, None) for c in cells
                       if "[[" in c or "{{sort" in c.lower()), None)
            ctry = parse_country(raw)
            if nm and ctry and len(nm.split()) >= 2:
                hints.setdefault(nm.split()[-1].lower(), (nm, ctry))
            continue
        # 2) athlete = first non-empty, non-wind cell after the mark
        j = midx + 1
        while j < len(cells) and (cells[j] == "" or WIND_RE.match(cells[j])
                                  or TECH_RE.match(cells[j])):
            j += 1
        name = extract_name(cells[j], last_name) if j < len(cells) else "?"
        # 3) nation = the cell right after the athlete, else an explicit code
        #    anywhere in the row. Only carry forward across a *true* rowspan
        #    (the row immediately above is the same athlete); otherwise leave it
        #    None and let normalize() fill it by surname.
        country = parse_country(cells[j + 1]) if j + 1 < len(cells) else None
        country = country or parse_country(raw)
        if (not country and last_country and name and last_name
                and name.split()[-1].lower() == last_name.split()[-1].lower()):
            country = last_country  # true rowspan: same athlete as the row above
        # Track the *immediately previous* emitted row only — never let a stale
        # country leak across a different athlete's intervening rows. Unknown
        # countries stay None here and are filled by normalize() by surname.
        last_name, last_country = name, country
        date_str, year = parse_date(raw)
        dpos = raw.find(date_str) if date_str else 0
        venue = parse_venue(raw, dpos)
        out.append({
            "mark": mark, "athlete": name, "country": country,
            "year": year, "date": date_str, "venue": venue,
        })
    return out, hints


def normalize(marks, hints):
    """Expand surname-only repeat rows to full names and fill missing countries
    by surname, using the rows that carry an explicit full name / country plus
    the hints harvested from mark-less continuation rows."""
    full = {s: n for s, (n, c) in hints.items()}
    sur2c = {s: c for s, (n, c) in hints.items()}
    for m in marks:
        parts = m["athlete"].split()
        sur = parts[-1].lower() if parts else ""
        if len(parts) >= 2:
            full.setdefault(sur, m["athlete"])
        if m["country"]:
            sur2c.setdefault(sur, m["country"])
    for m in marks:
        parts = m["athlete"].split()
        sur = parts[-1].lower() if parts else ""
        if len(parts) == 1 and sur in full:
            m["athlete"] = full[sur]
        if not m["country"]:
            m["country"] = sur2c.get(sur)
    return marks


def build_one(event_id):
    page, gender, unit = EVENTS[event_id]
    sect = find_section(page, gender)
    if sect is None:
        return None, f"no all-time section ({gender})"
    j = api(page, section=sect, prop="wikitext")
    wt = j["parse"]["wikitext"]["*"]
    rows, hints = parse_table(wt)
    marks = normalize(rows, hints)[:TOP_N]
    for i, m in enumerate(marks, 1):
        m["rank"] = i
    return marks, f"{len(marks)} marks from '{page}' §{sect}"


def main():
    only = sys.argv[1:] or list(EVENTS)
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    summary = {}
    for ev in only:
        try:
            marks, note = build_one(ev)
        except Exception as e:
            print(f"[{ev:9}] ERROR {e}")
            continue
        if not marks:
            print(f"[{ev:9}] FAIL {note}")
            continue
        page, gender, unit = EVENTS[ev]
        payload = {"event": ev, "page": page, "gender": gender, "unit": unit,
                   "marks": marks}
        (SEED_DIR / f"{ev}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        top = marks[0]
        summary[ev] = (top["mark"], top["athlete"], top["country"])
        print(f"[{ev:9}] {note:32} #1 {top['mark']:>9} {top['athlete']} "
              f"({top['country']})")
        time.sleep(0.6)
    print(f"\nWrote {len(summary)} seeds to {SEED_DIR}")


if __name__ == "__main__":
    main()
