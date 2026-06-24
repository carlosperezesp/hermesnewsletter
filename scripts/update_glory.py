#!/usr/bin/env python3
"""Genera y PERSISTE el Glory log (glory_data.js) leyendo los *_data.js ya generados.

Es la espina dorsal de Hermes: un registro determinista (sin IA) de hechos de gloria
—victorias, entradas/salidas del top 10— e informes de cierre de competición. Se ejecuta
al final del pipeline (después de actualizar cada deporte) y MEZCLA con el glory_data.js
anterior para que los hechos persistan con su fecha de primera aparición y una ventana de
retención. Así el email/redes podrán consumir el mismo log sin recalcular ni duplicar.

Cada item lleva un `id` estable (no depende del día) para deduplicar entre ejecuciones.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EVENT_RETENTION_DAYS = 14   # cuánto vive un hecho discreto en el feed
REPORT_RETENTION_DAYS = 21  # cuánto vive un informe de cierre
SUMO_REPORT_WINDOW = 16     # un basho cuenta como "recién cerrado" estos días

# id de sección -> (archivo, etiqueta visible). TODOS los deportes: de aquí salen
# tanto los hechos puntuales (victorias) e informes como las tablas vigiladas.
SOURCES = {
    "nhl": ("data.js", "NHL"),
    "nba": ("nba_data.js", "NBA"),
    "mlb": ("mlb_data.js", "MLB"),
    "nfl": ("nfl_data.js", "NFL"),
    "tennis": ("tennis_data.js", "Tenis"),
    "cycling": ("cycling_data.js", "Ciclismo"),
    "sumo": ("sumo_data.js", "Sumo"),
    "nascar": ("nascar_data.js", "NASCAR"),
    "motogp": ("motogp_data.js", "MotoGP"),
    "f1": ("f1_data.js", "F1"),
    "indycar": ("indycar_data.js", "IndyCar"),
    "golf": ("golf_data.js", "Golf"),
    "afl": ("afl_data.js", "AFL"),
    "rugby": ("rugby_data.js", "Rugby"),
    "football": ("football_data.js", "Fútbol"),
    "cricket": ("cricket_data.js", "Cricket"),
    "athletics": ("athletics_data.js", "Atletismo"),
}

# ── Tablas vigiladas: cualquier top-10 que se renderiza en la web ────────────
# Cada tabla -> (ruta dentro del *_data.js, etiqueta de la tabla, clave del nombre,
# modo). modo "full" = avisa de nuevo nº1 + entradas + salidas; "leader" = solo
# del nuevo nº1 (para tablas donde entradas/salidas ya se cubren aparte, p. ej.
# el top-10 ATP/WTA lo lleva ATP_CHANGES). Las rutas con punto bajan a subobjetos.
RANK_TABLES = {
    "nhl": [("ROAD_TO_GLORY.players", "Road to Glory", "name", "full"),
            ("ROAD_TO_GLORY.teams", "dinastías", "city", "full"),
            ("ROAD_TO_GLORY.youngProspects", "jóvenes promesas", "name", "full")],
    "nba": [("ROAD_TO_GLORY.players", "Road to Glory", "name", "full"),
            ("ROAD_TO_GLORY.teams", "dinastías", "city", "full"),
            ("ROAD_TO_GLORY.youngProspects", "jóvenes promesas", "name", "full")],
    "mlb": [("ROAD_TO_GLORY.players", "Road to Glory", "name", "full"),
            ("ROAD_TO_GLORY.teams", "dinastías", "city", "full"),
            ("ROAD_TO_GLORY.youngProspects", "jóvenes promesas", "name", "full")],
    "nfl": [("ROAD_TO_GLORY.players", "Road to Glory", "name", "full"),
            ("ROAD_TO_GLORY.youngProspects", "jóvenes promesas", "name", "full")],
    "cricket": [("ROAD_TO_GLORY.players", "Road to Glory", "name", "full")],
    "rugby": [("ROAD_TO_GLORY.dynasties", "dinastías", "name", "full")],
    "football": [("ROAD_TO_GLORY.dynasties", "dinastías", "name", "full"),
                 ("ROAD_TO_GLORY.currentContenders", "aspirantes", "name", "full")],
    "tennis": [("ATP", "ATP", "name", "leader"),
               ("WTA", "WTA", "name", "leader"),
               ("ATP_LEGENDS", "leyendas ATP", "name", "full"),
               ("WTA_LEGENDS", "leyendas WTA", "name", "full")],
    "cycling": [("LEGENDS", "leyendas", "name", "full"),
                ("CURRENT_RIDERS", "corredores actuales", "name", "full"),
                ("CURRENT_PROSPECTS", "promesas", "name", "full")],
    "golf": [("CURRENT", "Nivel actual", "name", "full"),
             ("LEGENDS", "leyendas", "name", "full")],
    "motogp": [("RIDERS", "Mundial", "name", "full"),
               ("LEGENDS", "leyendas", "name", "full")],
    "f1": [("DRIVERS", "Mundial", "name", "full"),
           ("LEGENDS", "leyendas", "name", "full")],
    "indycar": [("DRIVERS", "campeonato", "name", "full"),
                ("LEGENDS", "leyendas", "name", "full")],
    "nascar": [("DRIVERS", "Cup Series", "name", "full"),
               ("LEGENDS", "leyendas", "name", "full")],
    "sumo": [("BANZUKE", "banzuke", "name", "full")],
    "afl": [("LADDER", "clasificación", "name", "full")],
}

TOP_N = 10  # tamaño del top vigilado en cada tabla


def _load_js(path: Path) -> dict | None:
    """Carga un *_data.js (objeto JS con comentarios y `window.X = {...};`)."""
    try:
        txt = path.read_text(encoding="utf-8")
    except OSError:
        return None
    txt = re.sub(r"^\s*//.*$", "", txt, flags=re.M)
    m = re.search(r"=\s*(\{.*\})\s*;?\s*$", txt, flags=re.S)
    body = m.group(1) if m else txt[txt.find("{"): txt.rfind("}") + 1]
    try:
        return json.loads(body)
    except Exception:
        return None


def _data_fresh(d: dict, days: int = 10) -> bool:
    raw = (d.get("UPDATED") or d.get("LAST_UPDATE") or "")[:10]
    try:
        dd = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return False
    return 0 <= (date.today() - dd).days <= days


def _recently_ended(iso: str, days: int) -> bool:
    try:
        dd = datetime.strptime(str(iso)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False
    return 0 <= (date.today() - dd).days <= days


def _team_name(d: dict, code: str) -> str:
    for t in d.get("TEAMS", []):
        if t.get("code") == code or t.get("teamCode") == code:
            return t.get("commonName") or t.get("shortName") or t.get("city") or t.get("name") or code
    return code


# ── Cambios de clasificación (nuevo nº1 / entra / sale del top-10) ────────────
# Determinista: guardamos la foto del top-10 de cada tabla en glory_data.js y la
# comparamos con la anterior. El cambio aparece solo, sin tocar rosters.

def _dig(d: dict, path: str):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _top_names(arr, name_key: str, top_n: int = TOP_N) -> list[str] | None:
    if not isinstance(arr, list):
        return None
    out = []
    for it in arr[:top_n]:
        if isinstance(it, dict):
            nm = it.get(name_key) or it.get("name") or it.get("city")
            if nm:
                out.append(nm)
    return out


def _rank_events_for(sid: str, label: str, d: dict, prev_snaps: dict, new_snaps: dict) -> list[dict]:
    """Compara cada tabla del deporte con su foto previa y emite los cambios."""
    ev: list[dict] = []
    for path, tlabel, name_key, mode in RANK_TABLES.get(sid, []):
        cur = _top_names(_dig(d, path), name_key)
        if not cur:
            continue
        key = f"{sid}:{path}"
        prev = prev_snaps.get(key)
        new_snaps[key] = cur            # la foto de hoy queda para la próxima vuelta
        if prev is None:
            continue                    # primera vez: solo fijamos la base, sin avisos
        historic = "LEGENDS" in path or "leyenda" in tlabel
        leader_new = cur[0] if cur and prev and cur[0] != prev[0] else None
        if leader_new:
            ev.append({"id": f"rank:{key}:new1:{leader_new}", "sport": sid, "detail": label,
                       "text": f"{leader_new} es nuevo nº1 · {tlabel}", "weight": 96 if historic else 92})
        if mode == "full":
            prev_set, cur_set = set(prev), set(cur)
            for nm in cur:
                if nm not in prev_set and nm != leader_new:
                    ev.append({"id": f"rank:{key}:in:{nm}", "sport": sid, "detail": label,
                               "text": f"{nm} entra en el top-10 · {tlabel}", "weight": 88 if historic else 84})
            for nm in prev:
                if nm not in cur_set:
                    ev.append({"id": f"rank:{key}:out:{nm}", "sport": sid, "detail": label,
                               "text": f"{nm} cae del top-10 · {tlabel}", "weight": 74})
    return ev


def _athletics_rank_events(d: dict, prev_snaps: dict, new_snaps: dict) -> list[dict]:
    """Atletismo: una nueva marca que entra en el top-10 histórico de un evento."""
    ev: list[dict] = []
    for g in d.get("GROUPS", []):
        for e in g.get("events", []):
            eid = e.get("id")
            ath = [r.get("athlete") for r in (e.get("allTime") or [])[:TOP_N] if r.get("athlete")]
            if not eid or not ath:
                continue
            key = f"athletics:allTime:{eid}"
            prev = prev_snaps.get(key)
            new_snaps[key] = ath
            if prev is None:
                continue
            prev_set = set(prev)
            for nm in ath:
                if nm not in prev_set:
                    ev.append({"id": f"rank:{key}:in:{nm}", "sport": "athletics", "detail": "Atletismo",
                               "text": f"{nm} entra en el top-10 histórico · {e.get('name')}", "weight": 90})
    return ev


# ── Hechos discretos (victorias, top 10) ─────────────────────────────────────

def _events_for(sid: str, label: str, d: dict) -> list[dict]:
    ev: list[dict] = []

    def add(eid, text, weight, detail=label):
        ev.append({"id": eid, "sport": sid, "detail": detail, "text": text, "weight": weight})

    if sid == "motogp":
        lr = d.get("LAST_RACE") or {}
        if lr.get("winner"):
            add(f"motogp:win:{lr.get('name')}:{lr['winner']}", f"{lr['winner']} ganó el {lr.get('name', 'último GP')}", 100)
    elif sid == "nascar":
        lr = d.get("LAST_RACE") or {}
        if lr.get("winner"):
            add(f"nascar:win:{lr.get('name')}:{lr['winner']}", f"{lr['winner']} ganó en {lr.get('circuit') or lr.get('name', '')}", 100)
    elif sid == "indycar":
        lr = d.get("LAST_RACE") or {}
        winner = lr.get("winner") or ((lr.get("podium") or [{}])[0].get("name"))
        if winner:
            add(f"indycar:win:{lr.get('name')}:{winner}", f"{winner} ganó en {lr.get('circuit') or lr.get('name', '')}", 100)
    elif sid == "f1":
        lr = d.get("LAST_RACE") or {}
        pod = lr.get("podium") or []
        if pod and pod[0].get("name"):
            add(f"f1:win:{lr.get('name')}:{pod[0]['name']}", f"{pod[0]['name']} ganó el {lr.get('name', 'último GP')}", 100)
    elif sid == "cycling":
        cr = d.get("CURRENT_RACE") or {}
        ls = cr.get("last_stage") or {}
        if ls.get("winner"):
            add(f"cycling:stage:{cr.get('name')}:{ls.get('stage')}:{ls['winner']}",
                f"{ls['winner']} ganó la última etapa del {cr.get('name')}", 88)
    elif sid == "tennis":
        players = (d.get("ATP", []) or []) + (d.get("WTA", []) or [])
        ley = {p.get("name"): p.get("leyendaScore") for p in players}

        def tail(name):
            s = ley.get(name)
            return f" · Leyenda {s:.1f}" if isinstance(s, (int, float)) and s > 0 else ""

        for tour, key in (("ATP", "ATP_CHANGES"), ("WTA", "WTA_CHANGES")):
            ch = d.get(key) or {}
            cd = ch.get("curr_date", "")
            for p in ch.get("entered", []):
                add(f"tennis:in:{tour}:{p['name']}:{cd}", f"{p['name']} entra en el top 10 {tour}{tail(p['name'])}", 90, "Tenis")
            for p in ch.get("exited", []):
                add(f"tennis:out:{tour}:{p['name']}:{cd}", f"{p['name']} sale del top 10 {tour}", 78, "Tenis")
    return ev


# ── Informes de cierre ───────────────────────────────────────────────────────

def _report_for(sid: str, label: str, d: dict) -> dict | None:
    if sid in ("nba", "nhl"):
        fin = (d.get("BRACKET", {}).get("final") or [{}])[0]
        if not fin.get("winner"):
            return None
        champ = _team_name(d, fin["winner"])
        other = _team_name(d, fin["lo"] if fin["winner"] == fin.get("hi") else fin.get("hi"))
        scope = "los playoffs" if d.get("STATS_SCOPE") == "playoffs" else "la temporada"
        top5 = [{"name": p.get("name"), "score": p.get("score")} for p in d.get("PLAYERS", [])[:5]]
        ss = fin.get("seriesScore")
        return {
            "id": f"{sid}:champ:{fin['winner']}:{d.get('SEASON', '')}",
            "sport": sid, "competition": label,
            "champion": f"{champ} se proclama campeón" + (f" ({ss} a {other})" if ss else ""),
            "scopeLabel": f"Top 5 de {scope}", "top5": top5,
        }
    if sid == "mlb":
        ws_raw = d.get("BRACKET", {}).get("ws")
        ws = ws_raw[0] if isinstance(ws_raw, list) and ws_raw else ws_raw
        if not isinstance(ws, dict) or not ws.get("winner"):
            return None
        top5 = [{"name": p.get("name"), "score": p.get("score")} for p in d.get("PLAYERS", [])[:5]]
        return {
            "id": f"mlb:champ:{ws['winner']}:{d.get('SEASON', '')}",
            "sport": "mlb", "competition": label,
            "champion": f"{_team_name(d, ws['winner'])} gana las World Series",
            "scopeLabel": "Top 5 de la temporada", "top5": top5,
        }
    if sid == "cycling":
        cr = d.get("CURRENT_RACE") or {}
        if not cr.get("finished") or not cr.get("gc_winner"):
            return None
        top5 = [{"name": r.get("name"), "sub": r.get("team")} for r in cr.get("gc", [])[:5]]
        return {
            "id": f"cycling:gc:{cr.get('name')}:{cr['gc_winner']}",
            "sport": "cycling", "competition": label,
            "champion": f"{cr['gc_winner']} gana el {cr.get('name')}",
            "scopeLabel": "General final", "top5": top5,
        }
    if sid == "sumo":
        bi = d.get("BASHO_INFO") or {}
        if not bi.get("winner") or not _recently_ended(bi.get("endDate"), SUMO_REPORT_WINDOW):
            return None
        top5 = [{"name": r.get("name"), "sub": r.get("rankLabel")} for r in d.get("BANZUKE", [])[:5]]
        return {
            "id": f"sumo:basho:{bi.get('id')}",
            "sport": "sumo", "competition": label,
            "champion": f"{bi['winner']} conquista el basho",
            "scopeLabel": "Cabeza del banzuke", "top5": top5,
        }
    return None


# ── Merge persistente con el glory_data.js anterior ──────────────────────────

def _merge(current: list[dict], prev: list[dict], retention_days: int) -> list[dict]:
    today = date.today().isoformat()
    prev_by_id = {e.get("id"): e for e in prev if e.get("id")}
    out, seen = [], set()
    for e in current:
        e = dict(e)
        e["firstSeen"] = prev_by_id.get(e["id"], {}).get("firstSeen", today)
        out.append(e)
        seen.add(e["id"])
    # conservar hechos previos aún dentro de la ventana aunque ya no se regeneren
    for e in prev:
        if e.get("id") not in seen:
            out.append(e)
    out = [e for e in out if _within(e.get("firstSeen"), retention_days)]
    return out


def _within(iso: str, days: int) -> bool:
    try:
        dd = datetime.strptime(str(iso)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return True
    return (date.today() - dd).days <= days


def build() -> None:
    prev = _load_js(ROOT / "glory_data.js") or {}
    prev_events = prev.get("EVENTS", []) if isinstance(prev, dict) else []
    prev_reports = prev.get("REPORTS", []) if isinstance(prev, dict) else []
    prev_snaps = prev.get("SNAPSHOTS", {}) if isinstance(prev, dict) else {}

    events: list[dict] = []
    reports: list[dict] = []
    # Las fotos previas de los deportes con datos viejos se conservan tal cual,
    # para no inventar "salidas" cuando un *_data.js no se ha regenerado.
    new_snaps: dict = dict(prev_snaps)
    for sid, (fname, label) in SOURCES.items():
        d = _load_js(ROOT / fname)
        if not d or not _data_fresh(d):
            continue
        events.extend(_events_for(sid, label, d))
        events.extend(_rank_events_for(sid, label, d, prev_snaps, new_snaps))
        if sid == "athletics":
            events.extend(_athletics_rank_events(d, prev_snaps, new_snaps))
        r = _report_for(sid, label, d)
        if r:
            reports.append(r)

    events = _merge(events, prev_events, EVENT_RETENTION_DAYS)
    reports = _merge(reports, prev_reports, REPORT_RETENTION_DAYS)
    events.sort(key=lambda e: (e.get("weight", 0), e.get("firstSeen", "")), reverse=True)
    reports.sort(key=lambda r: r.get("firstSeen", ""), reverse=True)

    payload = {
        "UPDATED": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "EVENTS": events,
        "REPORTS": reports,
        "SNAPSHOTS": new_snaps,
    }
    out_path = ROOT / "glory_data.js"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("// Auto-generated Glory log — hechos de gloria e informes de cierre.\n")
        f.write(f"window.GLORY_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n")
    print(f"Glory log: {len(events)} eventos, {len(reports)} informes -> {out_path}")


if __name__ == "__main__":
    build()
