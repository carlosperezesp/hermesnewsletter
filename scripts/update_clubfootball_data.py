#!/usr/bin/env python3
"""Fútbol de clubes: power ranking Elo de la Champions League (equipos y jugadores).

Todo fehaciente y automático:
  - SEMILLA: Elo de clubelo.com (ranking parseado una vez y congelado como punto
    de partida de la temporada; se cachea sin caducidad).
  - PARTIDOS/CLASIFICACIÓN/ALINEACIONES: API pública de ESPN (uefa.champions).
  - ELO PROPIO por partido: ΔElo = K × G × (resultado − esperado), con esperado
    según diferencia de Elo + 65 pts de ventaja de campo; K=25 (Champions);
    G = ×1 (ganar por 1), ×1,5 (por 2), ×1,75+(N−3)/8 (por 3+). Suma cero.
  - JUGADORES: el ΔElo del equipo en cada partido se reparte a sus jugadores en
    proporción a los minutos (Δ × min/90), simétrico (también en derrotas).
    Minutos derivados de titularidades y sustituciones con minuto (ESPN).

Solo cuentan partidos entre los 36 de la fase liga (y luego eliminatorias).
"""
from __future__ import annotations
import json, re, sys, time, unicodedata, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "clubfootball_data.js"
CACHE = ROOT / ".sports_cache"; CACHE.mkdir(exist_ok=True)

K_FACTOR = 25.0
HOME_ADV = 65.0
SEASON_START = "20260901"   # fase liga 2026-27
SEASON_END = "20270601"
SEED_URLS = ["https://clubelo.com/2026-08-31/Ranking", "https://clubelo.com/Ranking"]
SEED_CACHE = CACHE / "clubelo_seed_202627.json"   # permanente: la semilla no se re-lee
ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions"
ESPN_STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer/uefa.champions/standings?season=2026"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Hermes/1.0"}


def _get(url: str, ttl_h: float, permanent: bool = False) -> str:
    """GET vía curl (el WAF de ESPN rechaza el fingerprint TLS de urllib)."""
    import hashlib, subprocess
    key = CACHE / ("cf_" + hashlib.md5(url.encode()).hexdigest())
    if key.exists():
        age_h = (time.time() - key.stat().st_mtime) / 3600
        if permanent or age_h < ttl_h:
            return key.read_text()
    try:
        # UA por defecto de curl: el WAF de ESPN rechaza UAs custom y a urllib.
        r = subprocess.run(["curl", "-s", "--max-time", "25", url],
                           capture_output=True, text=True, timeout=30)
        text = r.stdout
        if r.returncode == 0 and text.lstrip()[:1] in ("{", "["):
            key.write_text(text)
            return text
        raise RuntimeError(f"curl rc={r.returncode}, {len(text)}B, no-JSON")
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] fetch {url}: {exc}", file=sys.stderr)
        return key.read_text() if key.exists() else ""


def _norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    drop = {"fc", "cf", "afc", "ac", "as", "sl", "sk", "vfb", "rc", "cp", "bsc", "tsg", "rb", "club", "de", "the"}
    toks = [t for t in s.split() if t and t not in drop]
    return " ".join(toks)


# ESPN → ClubElo (para los que el normalizado no resuelve solo)
ALIAS = {
    "internazionale": "inter",
    "inter milan": "inter",
    "atletico madrid": "atletico",
    "bayern munich": "bayern munchen",
    "sporting": "sporting lisbon",
    "psv eindhoven": "psv",
    "bodo glimt": "bodoe glimt",
    "crvena zvezda": "red star belgrade",
    "estrella roja": "red star belgrade",
    "union saint gilloise": "union sg",
    "royale union saint gilloise": "union sg",
    "bodo glimt": "bod glimt",          # la ø de ClubElo no descompone a 'o'
    "slavia prague": "slavia praha",
}
# Fuera del ranking visible de ClubElo (nivel bajo): semilla neutral documentada.
SEED_DEFAULT_NOTE = "semilla 1500 por defecto (fuera del ranking visible de ClubElo)"


def fetch_seed() -> dict:
    """{norm_nombre: elo} de ClubElo, congelado como semilla de la temporada."""
    if SEED_CACHE.exists():
        return json.loads(SEED_CACHE.read_text())
    table = {}
    for url in SEED_URLS:
        try:
            html = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                                          timeout=25).read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] seed {url}: {exc}", file=sys.stderr)
            continue
        rows = re.findall(
            r'<a href="/([A-Za-z0-9]+)"><span class="NonAst">[^<]*</span>'
            r'<span class="Ast">([^<]+)</span></a></td><td class="r">(\d+)</td>', html)
        for slug, name, elo in rows:
            table[_norm(name)] = int(elo)
            table.setdefault(_norm(slug), int(elo))
        if table:
            print(f"[seed] {len(rows)} clubes desde {url}", file=sys.stderr)
            break
    if table:
        SEED_CACHE.write_text(json.dumps(table, ensure_ascii=False))
    return table


def seed_for(team_name: str, seed: dict):
    n = _norm(team_name)
    for cand in (n, ALIAS.get(n, ""), n.replace(" ", "")):
        if cand and cand in seed:
            return seed[cand]
    # último intento: contención de tokens (nombre ESPN dentro de nombre ClubElo o viceversa)
    ntoks = set(n.split())
    for k, v in seed.items():
        kt = set(k.split())
        if ntoks and (ntoks <= kt or kt <= ntoks):
            return v
    return None


# ── ESPN: clasificación, partidos, alineaciones ──────────────────────────────

def fetch_standings():
    d = json.loads(_get(ESPN_STANDINGS, ttl_h=6) or "{}")

    def find_entries(o):
        if isinstance(o, dict):
            if isinstance(o.get("entries"), list):
                return o["entries"]
            for v in o.values():
                r = find_entries(v)
                if r:
                    return r
        if isinstance(o, list):
            for v in o:
                r = find_entries(v)
                if r:
                    return r
        return None

    rows = []
    for e in find_entries(d) or []:
        t = e.get("team", {})
        st = {s.get("name"): s for s in e.get("stats", [])}
        def val(k): return int(st.get(k, {}).get("value", 0))
        logos = t.get("logos", [])
        rows.append({
            "id": t.get("id"), "name": t.get("displayName", ""),
            "shortName": t.get("shortDisplayName", t.get("displayName", "")),
            "logo": logos[0]["href"] if logos else "",
            "played": val("gamesPlayed"), "won": val("wins"), "drawn": val("ties"),
            "lost": val("losses"), "gf": val("pointsFor"), "ga": val("pointsAgainst"),
            "gd": val("pointDifferential"), "points": val("points"),
            "rank": int(st.get("rank", {}).get("value", 0)) or None,
        })
    rows.sort(key=lambda r: (-(r["points"]), -(r["gd"]), -(r["gf"])))
    for i, r in enumerate(rows):
        r["pos"] = i + 1
    return rows


def _month_ranges():
    """Rangos mensuales entre SEASON_START y hoy+90d (partidos jugados y próximos)."""
    from datetime import timedelta
    start = datetime.strptime(SEASON_START, "%Y%m%d").date()
    end = min(datetime.strptime(SEASON_END, "%Y%m%d").date(), date.today() + timedelta(days=90))
    cur = start
    while cur <= end:
        nxt = (cur.replace(day=1) + timedelta(days=32)).replace(day=1)
        yield cur.strftime("%Y%m%d"), min(nxt - timedelta(days=1), end).strftime("%Y%m%d")
        cur = nxt


def fetch_events():
    events = {}
    for a, b in _month_ranges():
        d = json.loads(_get(f"{ESPN}/scoreboard?dates={a}-{b}&limit=100", ttl_h=6) or "{}")
        for ev in d.get("events", []):
            events[ev["id"]] = ev
    return list(events.values())


def _parse_minute(txt: str):
    m = re.match(r"(\d+)", str(txt or ""))
    return int(m.group(1)) if m else None


def fetch_match_players(event_id: str):
    """[(athlete_id, nombre, team_id, minutos)] de un partido acabado (cache permanente)."""
    d = json.loads(_get(f"{ESPN}/summary?event={event_id}", ttl_h=6, permanent=True) or "{}")
    out = []
    for side in d.get("rosters", []):
        team_id = str(side.get("team", {}).get("id", ""))
        for p in side.get("roster", []):
            a = p.get("athlete", {})
            starter = bool(p.get("starter"))
            sub_in = sub_out = None
            for play in p.get("plays", []) or []:
                clock = _parse_minute((play.get("clock") or {}).get("displayValue"))
                txt = (play.get("type", {}) or {}).get("text", "") + " " + str(play.get("text", ""))
                if "ubstitut" not in txt and "sub" not in txt.lower():
                    continue
                if clock is None:
                    continue
                if p.get("subbedIn") and sub_in is None:
                    sub_in = clock
                elif p.get("subbedOut") and sub_out is None:
                    sub_out = clock
            if starter:
                minutes = (sub_out if p.get("subbedOut") and sub_out else 90)
            elif p.get("subbedIn"):
                start_min = sub_in if sub_in is not None else 70   # fallback conservador
                end_min = sub_out if (p.get("subbedOut") and sub_out) else 90
                minutes = max(0, end_min - start_min)
            else:
                minutes = 0
            if minutes > 0:
                out.append((str(a.get("id", "")), a.get("displayName", "?"), team_id, min(minutes, 90)))
    return out


# ── Elo propio ───────────────────────────────────────────────────────────────

def g_mult(diff: int) -> float:
    if diff <= 1:
        return 1.0
    if diff == 2:
        return 1.5
    return 1.75 + (diff - 3) / 8.0


def process(events, teams_by_id, seed):
    """Aplica el Elo partido a partido. Muta teams_by_id; devuelve (jugados, próximos, jugador_acum)."""
    played, upcoming = [], []
    players = {}   # (athlete_id, team_id) -> {name, teamId, delta, minutes, matches}
    finished = []
    for ev in events:
        comp = (ev.get("competitions") or [{}])[0]
        cs = comp.get("competitors", [])
        if len(cs) != 2:
            continue
        home = next((c for c in cs if c.get("homeAway") == "home"), cs[0])
        away = next((c for c in cs if c.get("homeAway") == "away"), cs[1])
        hid, aid = str(home["team"]["id"]), str(away["team"]["id"])
        if hid not in teams_by_id or aid not in teams_by_id:
            continue   # fuera de los 36 (previas, etc.)
        row = {"id": ev["id"], "date": ev.get("date", ""),
               "home": teams_by_id[hid]["shortName"], "away": teams_by_id[aid]["shortName"],
               "homeLogo": teams_by_id[hid]["logo"], "awayLogo": teams_by_id[aid]["logo"]}
        if (ev.get("status", {}).get("type", {}) or {}).get("completed"):
            finished.append((ev, row, hid, aid, home, away))
        else:
            upcoming.append((ev, row, hid, aid))

    finished.sort(key=lambda x: x[0].get("date", ""))
    for ev, row, hid, aid, home, away in finished:
        th, ta = teams_by_id[hid], teams_by_id[aid]
        gh, ga = int(home.get("score", 0)), int(away.get("score", 0))
        eh, ea = th["elo"], ta["elo"]
        exp_h = 1 / (1 + 10 ** (-((eh + HOME_ADV) - ea) / 400))
        res_h = 1.0 if gh > ga else (0.5 if gh == ga else 0.0)
        delta = K_FACTOR * g_mult(abs(gh - ga)) * (res_h - exp_h)
        th["elo"] += delta; ta["elo"] -= delta
        th["played"] += 1; ta["played"] += 1
        th["lastDelta"] = round(delta, 1); ta["lastDelta"] = round(-delta, 1)
        row.update({"score": f"{gh}-{ga}", "deltaHome": round(delta, 1),
                    "deltaAway": round(-delta, 1), "expHome": round(exp_h * 100)})
        played.append(row)
        # atribución a jugadores por minutos
        for pid, name, team_id, minutes in fetch_match_players(ev["id"]):
            if team_id not in (hid, aid):
                continue
            d = (delta if team_id == hid else -delta) * minutes / 90.0
            key = (pid, team_id)
            entry = players.setdefault(key, {"name": name, "teamId": team_id,
                                             "delta": 0.0, "minutes": 0, "matches": 0})
            entry["delta"] += d; entry["minutes"] += minutes; entry["matches"] += 1
        time.sleep(0.2)

    ups = []
    for ev, row, hid, aid in sorted(upcoming, key=lambda x: x[0].get("date", ""))[:18]:
        eh, ea = teams_by_id[hid]["elo"], teams_by_id[aid]["elo"]
        exp_h = 1 / (1 + 10 ** (-((eh + HOME_ADV) - ea) / 400))
        row["expHome"] = round(exp_h * 100)
        ups.append(row)
    return played, ups, players


def main():
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    seed = fetch_seed()
    standings = fetch_standings()
    if not standings:
        print("[ERROR] sin clasificación ESPN"); sys.exit(1)

    teams_by_id = {}
    missing = []
    for s in standings:
        elo0 = seed_for(s["name"], seed) or seed_for(s["shortName"], seed)
        if elo0 is None:
            missing.append(s["name"]); elo0 = 1500
        teams_by_id[str(s["id"])] = {**s, "seed": elo0, "elo": float(elo0),
                                     "played": 0, "lastDelta": None}
    if missing:
        print(f"[WARN] sin semilla ClubElo (usan 1500): {missing}", file=sys.stderr)

    events = fetch_events()
    played, upcoming, players_acc = process(events, teams_by_id, seed)

    ranking = sorted(teams_by_id.values(), key=lambda t: -t["elo"])
    ELO_RANKING = [{
        "rank": i + 1, "name": t["shortName"], "fullName": t["name"], "logo": t["logo"],
        "elo": round(t["elo"]), "seed": t["seed"], "delta": round(t["elo"] - t["seed"], 1),
        "lastDelta": t["lastDelta"], "played": t["played"],
    } for i, t in enumerate(ranking)]

    tname = {str(t["id"]): t["shortName"] for t in standings}
    tlogo = {str(t["id"]): t["logo"] for t in standings}
    PLAYERS = sorted(players_acc.values(), key=lambda p: -p["delta"])
    PLAYER_RANKING = [{
        "rank": i + 1, "name": p["name"], "team": tname.get(p["teamId"], "?"),
        "teamLogo": tlogo.get(p["teamId"], ""), "delta": round(p["delta"], 1),
        "minutes": p["minutes"], "matches": p["matches"],
    } for i, p in enumerate(PLAYERS[:30])]
    PLAYER_BOTTOM = [{
        "name": p["name"], "team": tname.get(p["teamId"], "?"), "delta": round(p["delta"], 1),
        "minutes": p["minutes"],
    } for p in PLAYERS[-5:]][::-1] if PLAYERS else []

    payload = {
        "UPDATED": updated, "SEASON": "UEFA Champions League 2026-27 · Fase liga",
        "FORMULA": "ΔElo = 25 × G × (resultado − esperado) · +65 en casa · G: ×1 / ×1,5 / ×1,75+ por margen",
        "SOURCE": {"name": "Elo propio (semilla ClubElo congelada a inicio de temporada) + resultados y alineaciones de ESPN",
                   "note": "Solo mueven el Elo los partidos de Champions entre los 36. Jugadores: ΔElo del equipo × minutos/90, simétrico."},
        "ELO_RANKING": ELO_RANKING,
        "STANDINGS": standings,
        "MATCHES_RECENT": played[-18:][::-1],
        "MATCHES_UPCOMING": upcoming,
        "PLAYER_RANKING": PLAYER_RANKING,
        "PLAYER_BOTTOM": PLAYER_BOTTOM,
        "IMPORTANCE": 8.6,
    }
    OUT.write_text(f"// Auto-generated {updated}\nwindow.CLUBFOOTBALL_DATA = "
                   f"{json.dumps(payload, ensure_ascii=False, indent=2)};\n", encoding="utf-8")
    print(f"Wrote {OUT.name} · {len(ELO_RANKING)} equipos · {len(played)} jugados · "
          f"{len(upcoming)} próximos · {len(PLAYER_RANKING)} jugadores rankeados")
    for t in ELO_RANKING[:5]:
        print(f"   {t['rank']}. {t['name']:22s} {t['elo']} (semilla {t['seed']}, Δ {t['delta']:+})")


if __name__ == "__main__":
    main()
