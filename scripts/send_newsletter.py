#!/usr/bin/env python3
"""Update NHL + NBA data and send the daily newsletter email via Gmail SMTP."""

from __future__ import annotations

import json
import os
import re
import smtplib
import subprocess
import sys
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

ROOT      = Path(__file__).resolve().parents[1]
SENDER    = "carlosrealmurcia@gmail.com"
RECIPIENT = "carlosrealmurcia@gmail.com"

# ── Palette ──────────────────────────────────────────────────────
BG       = "#f5f3f0"
PAPER    = "#fafaf8"
INK      = "#1a1714"
INK2     = "#3d3a37"
MUTED    = "#888880"
RULE     = "#e8e5e1"
ACCENT   = "#b84832"
GOOD     = "#2d7a3a"
BAR_FILL = "#4a4745"
BAR_BG   = "#dedad6"
WARN     = "#a86513"
BAD      = "#c92d2d"
SERIF    = "Newsreader, Georgia, serif"
SANS     = "'IBM Plex Sans', Arial, Helvetica, sans-serif"
MONO     = "'IBM Plex Mono', ui-monospace, monospace"


# ── Config ───────────────────────────────────────────────────────

def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_js_data(js_file: Path) -> dict:
    text = js_file.read_text(encoding="utf-8")
    m = re.search(r"window\.\w+\s*=\s*(\{.*\})\s*;", text, re.DOTALL)
    return json.loads(m.group(1)) if m else {}


# ── HTML primitives ───────────────────────────────────────────────

def swatch(color: str, size: int = 10) -> str:
    return (f'<span style="display:inline-block;width:{size}px;height:{size}px;'
            f'border-radius:2px;background:{color};vertical-align:middle;'
            f'margin-right:5px;flex-shrink:0"></span>')


def score_bar(value: float, threshold: float, width: int = 130) -> str:
    """Horizontal progress bar with threshold marker — table-based, email-safe."""
    if not threshold:
        return ""
    pct   = min(100.0, max(0.0, value / threshold * 100))
    t_pct = 100.0  # threshold line is always at the right edge
    fill_px = round(width * pct / 100)
    rest_px = width - fill_px
    # Threshold marker: a 2px dark line positioned at threshold (= right edge)
    bar = (
        f'<table cellpadding="0" cellspacing="0" border="0" '
        f'style="display:inline-table;width:{width}px;height:7px;'
        f'background:{BAR_BG};border-spacing:0;vertical-align:middle">'
        f'<tr>'
        f'<td style="width:{fill_px}px;background:{BAR_FILL};height:7px;padding:0"></td>'
        f'<td style="background:{BAR_BG};height:7px;padding:0"></td>'
        f'<td style="width:2px;background:{ACCENT};height:7px;padding:0"></td>'
        f'</tr>'
        f'</table>'
    )
    return bar


def score_chip(value) -> str:
    if value is None:
        return ""
    try:
        score = float(value)
    except (TypeError, ValueError):
        return ""
    if score >= 85:
        bg, fg = "#dcefe2", "#1f7a3d"
    elif score >= 70:
        bg, fg = "#e8efdc", "#5f7d1e"
    elif score >= 55:
        bg, fg = "#f5ead4", WARN
    else:
        bg, fg = "#f8ded9", BAD
    return (f'<span style="display:inline-block;min-width:34px;margin-left:5px;'
            f'padding:1px 5px;border-radius:3px;background:{bg};color:{fg};'
            f'font-family:{MONO};font-size:11px;font-weight:700;text-align:center">'
            f'{score:.1f}</span>')


# ── Bracket ───────────────────────────────────────────────────────

def _series_row(s: dict, round_label: str, team_colors: dict[str, str]) -> str:
    hi, lo = s.get("hi"), s.get("lo")
    if not hi and not lo:
        return ""
    score   = s.get("seriesScore", "-")
    winner  = s.get("winner")
    hi_col  = team_colors.get(hi, MUTED)
    lo_col  = team_colors.get(lo, MUTED)

    if winner:
        loser  = lo if winner == hi else hi
        l_col  = team_colors.get(loser, MUTED)
        w_col  = team_colors.get(winner, MUTED)
        result = (
            f'{swatch(w_col)}<b style="color:{INK}">{winner}</b> '
            f'<span style="color:{MUTED}">vs</span> '
            f'<span style="color:{MUTED};text-decoration:line-through">{loser}</span> '
            f'<span style="color:{GOOD};font-weight:700;margin-left:4px">{score}</span>'
        )
    elif hi and lo:
        result = (
            f'{swatch(hi_col)}<b style="color:{INK}">{hi}</b> '
            f'<span style="color:{MUTED}">vs</span> '
            f'{swatch(lo_col)}<b style="color:{INK}">{lo}</b> '
            f'<span style="color:{ACCENT};font-weight:700;margin-left:4px">{score} live</span>'
        )
    else:
        result = f'<span style="color:{MUTED}">TBD</span>'

    label_style = (f'font-size:9px;letter-spacing:.1em;text-transform:uppercase;'
                   f'color:{MUTED};font-family:monospace;white-space:nowrap')
    return (
        f'<tr>'
        f'<td style="padding:5px 10px 5px 0;{label_style};vertical-align:top">{round_label}</td>'
        f'<td style="padding:5px 0;font-size:13px;vertical-align:top">{result}</td>'
        f'</tr>'
    )


def bracket_html(bracket: dict, sport: str, team_colors: dict[str, str]) -> str:
    round_labels = {"r1": "Round 1", "r2": "Semis", "conf": "Conf. Final"}
    finals_label = "Stanley Cup Final" if sport == "NHL" else "NBA Finals"

    def conf_col(conf: str) -> str:
        rows = ""
        for rnd, label in round_labels.items():
            for s in bracket.get(conf, {}).get(rnd, []):
                rows += _series_row(s, label, team_colors)
        # Finals (shared, only show in east col)
        if conf == "east":
            for s in bracket.get("final", []):
                rows += _series_row(s, finals_label, team_colors)
        return (
            f'<table cellpadding="0" cellspacing="0" border="0" style="width:100%;border-spacing:0">'
            f'{rows}</table>'
        )

    conf_head = (f'font-size:10px;letter-spacing:.1em;text-transform:uppercase;'
                 f'color:{MUTED};font-family:monospace;padding-bottom:8px;display:block')

    return (
        f'<table cellpadding="0" cellspacing="0" border="0" style="width:100%;border-spacing:0">'
        f'<tr>'
        f'<td style="width:48%;vertical-align:top;padding:0 16px 0 0;'
        f'border-right:1px solid {RULE}">'
        f'<span style="{conf_head}">Conferencia Este</span>'
        f'{conf_col("east")}</td>'
        f'<td style="width:4%"></td>'
        f'<td style="width:48%;vertical-align:top;padding:0 0 0 16px">'
        f'<span style="{conf_head}">Conferencia Oeste</span>'
        f'{conf_col("west")}</td>'
        f'</tr>'
        f'</table>'
    )


# ── Player rows ───────────────────────────────────────────────────

def player_list_html(players: list[dict],
                     score_key: str,
                     score_label: str,
                     meta_fn,
                     note_fn,
                     threshold: float | None = None,
                     score_b_key: str | None = None,
                     score_b_label: str = "") -> str:
    rows = ""
    for i, p in enumerate(players, 1):
        primary = p.get("colors", {}).get("primary") or p.get("primary", "#666")
        score_val = p.get(score_key, 0)
        tourney_state = (p.get("tournamentStatus") or {}).get("state")
        is_out = tourney_state == "out"
        row_bg = (
            f'background:repeating-linear-gradient(135deg, rgba(0,0,0,0.025) 0 6px, '
            f'rgba(0,0,0,0.045) 6px 7px),{BG};'
        ) if is_out else ""
        name_color = MUTED if is_out else INK
        score_b_val = p.get(score_b_key, "") if score_b_key else ""
        score_b_html = ""
        if score_b_key:
            score_b_html = (
                f'<td style="padding:12px 12px 12px 8px;text-align:right;vertical-align:top;white-space:nowrap">'
                f'<div style="font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:{MUTED};'
                f'font-family:{MONO}">{score_b_label}</div>'
                f'<div style="font-size:24px;font-weight:500;color:{INK};font-family:{SERIF};'
                f'font-variant-numeric:tabular-nums">{score_b_val}</div>'
                f'</td>'
            )
        gap_txt = ""
        bar_html = ""
        if threshold:
            gap = round(threshold - score_val, 1)
            gap_txt = f' <span style="color:{MUTED};font-size:11px">/ {threshold} (−{gap})</span>' if gap > 0 else ""
            bar_html = f'<div style="margin-top:4px">{score_bar(score_val, threshold)}</div>'

        rows += (
            f'<tr style="border-bottom:1px solid {RULE};{row_bg}">'
            f'<td style="padding:12px 14px 12px 0;font-size:26px;color:{MUTED};'
            f'font-family:{SERIF};font-variant-numeric:tabular-nums;width:42px;'
            f'vertical-align:top;text-align:right">{i:02d}</td>'
            f'<td style="padding:12px 16px 12px 0;vertical-align:top">'
            f'<div style="font-size:19px;line-height:1.15;font-family:{SERIF};'
            f'font-weight:500;color:{name_color}">'
            f'{swatch(primary)}{p.get("name","")}</div>'
            f'<div style="font-size:10.5px;color:{MUTED};font-family:{MONO};margin-top:4px">'
            f'{meta_fn(p)}</div>'
            f'<div style="font-size:10.5px;color:{INK2};font-family:{MONO};margin-top:2px">'
            f'{note_fn(p)}</div>'
            f'</td>'
            f'{score_b_html}'
            f'<td style="padding:12px 0 12px 8px;text-align:right;vertical-align:top;white-space:nowrap">'
            f'<div style="font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:{MUTED};'
            f'font-family:{MONO}">{score_label}</div>'
            f'<div style="font-size:28px;font-weight:500;color:{ACCENT};font-family:{SERIF};'
            f'font-variant-numeric:tabular-nums">{score_val}{gap_txt}</div>'
            f'{bar_html}'
            f'</td>'
            f'</tr>'
        )
    return (
        f'<table cellpadding="0" cellspacing="0" border="0" '
        f'style="width:100%;border-collapse:collapse;background:{PAPER}">'
        f'{rows}</table>'
    )


def team_list_html(teams: list[dict],
                   score_key: str,
                   score_label: str,
                   meta_fn,
                   note_fn,
                   threshold: float | None = None) -> str:
    rows = ""
    for i, t in enumerate(teams[:10], 1):
        primary = t.get("colors", {}).get("primary") or t.get("primary", "#666")
        score_val = t.get(score_key, 0)
        gap_txt = ""
        bar_html = ""
        if threshold:
            gap = round(threshold - score_val, 1)
            gap_txt = f' <span style="color:{MUTED};font-size:11px">/ {threshold} (−{gap})</span>' if gap > 0 else ""
            bar_html = f'<div style="margin-top:4px">{score_bar(score_val, threshold)}</div>'

        name = t.get("city") or t.get("name", "")
        rows += (
            f'<tr style="border-bottom:1px solid {RULE}">'
            f'<td style="padding:12px 14px 12px 0;font-size:26px;color:{MUTED};'
            f'font-family:{SERIF};font-variant-numeric:tabular-nums;width:42px;'
            f'vertical-align:top;text-align:right">{i:02d}</td>'
            f'<td style="padding:12px 16px 12px 0;vertical-align:top">'
            f'<div style="font-size:19px;line-height:1.15;font-family:{SERIF};'
            f'font-weight:500;color:{INK}">'
            f'{swatch(primary)}{name}</div>'
            f'<div style="font-size:10.5px;color:{MUTED};font-family:{MONO};margin-top:4px">'
            f'{meta_fn(t)}</div>'
            f'<div style="font-size:10.5px;color:{INK2};font-family:{MONO};margin-top:2px">'
            f'{note_fn(t)}</div>'
            f'</td>'
            f'<td style="padding:12px 0 12px 8px;text-align:right;vertical-align:top;white-space:nowrap">'
            f'<div style="font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:{MUTED};'
            f'font-family:{MONO}">{score_label}</div>'
            f'<div style="font-size:28px;font-weight:500;color:{ACCENT};font-family:{SERIF};'
            f'font-variant-numeric:tabular-nums">{score_val}{gap_txt}</div>'
            f'{bar_html}'
            f'</td>'
            f'</tr>'
        )
    return (
        f'<table cellpadding="0" cellspacing="0" border="0" '
        f'style="width:100%;border-collapse:collapse;background:{PAPER}">'
        f'{rows}</table>'
    )


# ── Section wrapper ───────────────────────────────────────────────

def section(kicker: str, title: str, sub: str, body: str) -> str:
    return (
        f'<div style="border-top:1px solid {INK};padding:18px 28px 0">'
        f'<table cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse;margin-bottom:16px">'
        f'<tr>'
        f'<td style="width:18%;vertical-align:top;padding:0 16px 0 0;'
        f'font-size:11px;letter-spacing:.12em;text-transform:uppercase;'
        f'color:{MUTED};font-family:{MONO};line-height:1.45">[ {kicker} ]</td>'
        f'<td style="width:44%;vertical-align:top;padding:0 18px 0 0;'
        f'font-size:34px;font-weight:500;color:{INK};font-family:{SERIF};'
        f'letter-spacing:-.01em;line-height:1.02">{title}</td>'
        f'<td style="width:38%;vertical-align:top;padding:4px 0 0 0;'
        f'font-size:12px;color:{MUTED};font-family:{MONO};line-height:1.55">{sub}</td>'
        f'</tr></table>'
        f'{body}'
        f'</div>'
    )


def sport_header(sport: str, season: str, last_update: str, title: str = "") -> str:
    display = title or f"{sport} Playoffs"
    return (
        f'<div style="background:{PAPER};border-top:2px solid {INK};'
        f'border-bottom:1px solid {RULE};padding:18px 28px 28px">'
        f'<table cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse;margin-bottom:22px">'
        f'<tr>'
        f'<td style="font-size:10px;letter-spacing:.12em;text-transform:uppercase;'
        f'color:{MUTED};font-family:{MONO};text-align:left">{sport} Tracker</td>'
        f'<td style="font-size:10px;letter-spacing:.12em;text-transform:uppercase;'
        f'color:{MUTED};font-family:{MONO};text-align:center">{season}</td>'
        f'<td style="font-size:10px;color:{MUTED};font-family:{MONO};text-align:right">'
        f'Actualizado {last_update}</td>'
        f'</tr></table>'
        f'<div style="font-size:56px;font-weight:500;color:{INK};font-family:{SERIF};'
        f'letter-spacing:-.01em;line-height:1;text-align:left">{display}</div>'
        f'</div>'
    )


# ── NHL ───────────────────────────────────────────────────────────

def nhl_html(d: dict) -> str:
    team_map   = {t["code"]: t for t in d.get("TEAMS", [])}
    players    = d.get("PLAYERS", [])
    bracket    = d.get("BRACKET", {})
    rtg        = d.get("ROAD_TO_GLORY", {})
    team_colors = {code: t["colors"]["primary"] for code, t in team_map.items()}

    top        = sorted(players, key=lambda p: -p["score"])[:10]
    p_thresh   = rtg.get("playerThreshold")
    t_thresh   = rtg.get("teamThreshold")

    def p_meta(p):
        tn  = team_map.get(p["teamCode"], {}).get("commonName", p["teamCode"])
        age = f" · {p['age']} años" if p.get("age") else ""
        return f"{p.get('country','NHL')} · {p.get('pos','')} · {tn}{age}"

    def p_note(p):
        if p.get("pos") == "G":
            return f"{p.get('stats',{}).get('svpct',0):.3f} SV%"
        st = p.get("stats", {})
        return f"{st.get('p',0)} P · {st.get('g',0)} G · {st.get('a',0)} A"

    def rtg_p_meta(p):
        tn  = team_map.get(p["teamCode"], {}).get("commonName", p["teamCode"])
        cups = p.get("cups", 0)
        seas = p.get("seasons", "?")
        return f"{p.get('country','NHL')} · {p.get('pos','')} · {tn} · {seas} temp · {cups} Cups"

    def rtg_y_meta(p):
        tn = team_map.get(p["teamCode"], {}).get("commonName", p["teamCode"])
        return f"{p.get('country','NHL')} · {p.get('pos','')} · {tn} · score actual {p.get('currentScore','?')}"

    def rtg_t_meta(t):
        cups = t.get("cups", 0)
        return f"{t.get('era','')} · {cups} Cup{'s' if cups != 1 else ''} · {t.get('note','')}"

    return (
        sport_header("NHL", d.get("SEASON",""), d.get("LAST_UPDATE",""))
        + section("Playoff bracket", "Camino a la Stanley Cup",
                  "Series al mejor de siete.",
                  bracket_html(bracket, "NHL", team_colors))
        + section("Top performers", "Top 10 de la temporada",
                  "Score percentil por posición — skaters y porteros.",
                  player_list_html(top, "score", "Score", p_note, p_meta))
        + section("Road to Glory · Jugadores",
                  f"Top 10 Road to Glory",
                  f"Umbral histórico top 10: {p_thresh}.",
                  player_list_html(rtg.get("players",[])[:10], "careerScore", "Career",
                                   lambda p: p.get("note",""), rtg_p_meta, p_thresh))
        + section("Road to Glory · Jóvenes (≤25)",
                  "Top 10 Jóvenes",
                  "Proyección de carrera para menores de 25.",
                  player_list_html(rtg.get("youngProspects",[])[:10], "projectedScore", "Proj.",
                                   lambda p: p.get("note",""), rtg_y_meta, p_thresh))
        + section("Road to Glory · Franquicias",
                  "Top 10 Franquicias",
                  f"Umbral histórico top 10: {t_thresh}.",
                  team_list_html(rtg.get("teams",[])[:10], "dynastyScore", "Dynasty",
                                 rtg_t_meta, lambda t: t.get("needs",""), t_thresh))
    )


# ── NBA ───────────────────────────────────────────────────────────

def nba_html(d: dict) -> str:
    team_map    = {t["code"]: t for t in d.get("TEAMS", [])}
    players     = d.get("PLAYERS", [])
    bracket     = d.get("BRACKET", {})
    rtg         = d.get("ROAD_TO_GLORY", {})
    team_colors = {code: t["colors"]["primary"] for code, t in team_map.items()}
    stats_scope = d.get("STATS_SCOPE") or "temporada"
    stats_label = "playoffs" if stats_scope == "playoffs" else "temporada"

    top       = sorted(players, key=lambda p: -p["score"])[:10]
    p_thresh  = rtg.get("playerThreshold")
    t_thresh  = rtg.get("teamThreshold")

    def p_meta(p):
        tn  = team_map.get(p["teamCode"], {}).get("commonName", p["teamCode"])
        age = f" · {p['age']} años" if p.get("age") else ""
        return f"NBA · {p.get('pos','')} · {tn}{age}"

    def p_note(p):
        st = p.get("stats", {})
        return f"{st.get('pts',0)} PPG · {st.get('reb',0)} REB · {st.get('ast',0)} AST"

    def rtg_p_meta(p):
        tn    = team_map.get(p["teamCode"], {}).get("commonName", p["teamCode"])
        rings = p.get("rings", 0)
        return f"NBA · {p.get('pos','')} · {tn} · {rings} ring{'s' if rings != 1 else ''}"

    def rtg_y_meta(p):
        tn = team_map.get(p["teamCode"], {}).get("commonName", p["teamCode"])
        return f"NBA · {p.get('pos','')} · {tn} · score actual {p.get('currentScore','?')}"

    def rtg_t_meta(t):
        rings = t.get("rings", 0)
        return f"{t.get('era','')} · {rings} ring{'s' if rings != 1 else ''} · {t.get('note','')}"

    return (
        f'<div style="margin-top:32px"></div>'
        + sport_header("NBA", d.get("SEASON",""), d.get("LAST_UPDATE",""))
        + section("Playoff bracket", "Camino a las NBA Finals",
                  "Series al mejor de siete.",
                  bracket_html(bracket, "NBA", team_colors))
        + section("Top performers", f"Top 10 de {stats_label}",
                  f"Score percentil de {stats_label} — pts, reb, ast, stl, blk ponderados.",
                  player_list_html(top, "score", "Score", p_note, p_meta))
        + section("Road to Glory · Jugadores",
                  "Top 10 Road to Glory",
                  f"Umbral histórico top 10: {p_thresh} (Tim Duncan).",
                  player_list_html(rtg.get("players",[])[:10], "careerScore", "Career",
                                   lambda p: p.get("note",""), rtg_p_meta, p_thresh))
        + section("Road to Glory · Jóvenes (≤25)",
                  "Top 10 Jóvenes",
                  "Proyección de carrera para menores de 25.",
                  player_list_html(rtg.get("youngProspects",[])[:10], "projectedScore", "Proj.",
                                   lambda p: p.get("note",""), rtg_y_meta, p_thresh))
        + section("Road to Glory · Franquicias",
                  "Top 10 Franquicias",
                  f"Umbral histórico top 10: {t_thresh} (Celtics 07-08).",
                  team_list_html(rtg.get("teams",[])[:10], "dynastyScore", "Dynasty",
                                 rtg_t_meta, lambda t: t.get("needs",""), t_thresh))
    )


MLB_DIV_ORDER = ["AL East", "AL Central", "AL West", "NL East", "NL Central", "NL West"]
MLB_TEAM_DIV = {
    "NYY":"AL East", "BOS":"AL East", "TOR":"AL East", "TB":"AL East",  "BAL":"AL East",
    "CWS":"AL Central","CLE":"AL Central","DET":"AL Central","KC":"AL Central","MIN":"AL Central",
    "HOU":"AL West",  "LAA":"AL West",  "ATH":"AL West",  "SEA":"AL West",  "TEX":"AL West",
    "ATL":"NL East",  "MIA":"NL East",  "NYM":"NL East",  "PHI":"NL East",  "WSH":"NL East",
    "CHC":"NL Central","CIN":"NL Central","MIL":"NL Central","PIT":"NL Central","STL":"NL Central",
    "LAD":"NL West",  "ARI":"NL West",  "COL":"NL West",  "SF":"NL West",   "SD":"NL West",
}


def mlb_html(d: dict) -> str:
    team_map    = {t["code"]: t for t in d.get("TEAMS", [])}
    players     = d.get("PLAYERS", [])
    bracket     = d.get("BRACKET", {})
    rtg         = d.get("ROAD_TO_GLORY", {})
    team_colors = {code: t["colors"]["primary"] for code, t in team_map.items()}

    pitchers = sorted([p for p in players if p.get("stats", {}).get("type") == "pitching"], key=lambda p: -p["score"])[:10]
    batters  = sorted([p for p in players if p.get("stats", {}).get("type") == "batting"],  key=lambda p: -p["score"])[:10]
    p_thresh = rtg.get("playerThreshold")
    t_thresh = rtg.get("teamThreshold")

    def p_meta(p):
        tn  = team_map.get(p["teamCode"], {}).get("commonName", p["teamCode"])
        age = f" · {p['age']} años" if p.get("age") else ""
        return f"MLB · {p.get('pos','')} · {tn}{age}"

    def p_note(p):
        st = p.get("stats", {})
        if st.get("type") == "pitching":
            return f"{st.get('era','-')} ERA · {st.get('so',0)} K · {st.get('w',0)} W"
        avg = st.get("avg", 0)
        avg_str = f".{str(int(round(avg * 1000))).zfill(3)}" if avg else ".000"
        return f"{avg_str} AVG · {st.get('hr',0)} HR · {st.get('rbi',0)} RBI"

    def rtg_p_meta(p):
        tn    = team_map.get(p["teamCode"], {}).get("commonName", p["teamCode"])
        rings = p.get("rings", 0)
        return f"MLB · {p.get('pos','')} · {tn} · {rings} ring{'s' if rings != 1 else ''}"

    def rtg_y_meta(p):
        tn = team_map.get(p["teamCode"], {}).get("commonName", p["teamCode"])
        return f"MLB · {p.get('pos','')} · {tn} · score actual {p.get('currentScore','?')}"

    def rtg_t_meta(t):
        rings = t.get("rings", 0)
        return f"{t.get('era','')} · {rings} ring{'s' if rings != 1 else ''} · {t.get('note','')}"

    # Standings by division (regular season) or bracket (postseason)
    ws_list = bracket.get("ws", [{}])
    al_lcs  = bracket.get("al", {}).get("lcs", [{}])
    nl_lcs  = bracket.get("nl", {}).get("lcs", [{}])
    has_playoffs = ((ws_list or [{}])[0].get("hi") or
                    (al_lcs or [{}])[0].get("hi") or
                    (nl_lcs or [{}])[0].get("hi"))

    def mlb_standings_html() -> str:
        # Group teams by division
        div_map: dict[str, list] = {div: [] for div in MLB_DIV_ORDER}
        for t in d.get("TEAMS", []):
            div = MLB_TEAM_DIV.get(t["code"], t.get("div", "Other"))
            if div in div_map:
                div_map[div].append(t)
        for div in div_map:
            div_map[div].sort(key=lambda t: (-t["w"], t["l"]))

        div_head = (f'font-size:10px;letter-spacing:.1em;text-transform:uppercase;'
                    f'color:{MUTED};font-family:monospace;padding:8px 0 4px;'
                    f'border-bottom:1px solid {RULE};display:block;margin-bottom:2px')
        cell_style = f'vertical-align:top;width:48%;padding-bottom:16px'

        def div_col(divs: list[str]) -> str:
            out = ""
            for div in divs:
                out += f'<span style="{div_head}">{div}</span>'
                for i, t in enumerate(div_map.get(div, []), 1):
                    pct = f".{str(int(round(t['winPct']*1000))).zfill(3)}"
                    rd_str = f"+{t['rd']}" if t["rd"] > 0 else str(t["rd"])
                    out += (
                        f'<table cellpadding="0" cellspacing="0" border="0" '
                        f'style="width:100%;border-spacing:0;padding:4px 0">'
                        f'<tr>'
                        f'<td style="width:20px;color:{MUTED};font-size:11px;font-family:monospace">{i}</td>'
                        f'<td style="padding:0 4px">{swatch(t["colors"]["primary"], 8)}'
                        f'<span style="font-size:13px;font-weight:600;color:{INK}">{t["shortName"]}</span></td>'
                        f'<td style="text-align:right;font-size:12px;font-family:monospace;color:{INK2};white-space:nowrap">'
                        f'{t["w"]}–{t["l"]} <span style="color:{MUTED}">{pct}</span></td>'
                        f'</tr></table>'
                    )
            return out

        al_divs = [d for d in MLB_DIV_ORDER if d.startswith("AL")]
        nl_divs = [d for d in MLB_DIV_ORDER if d.startswith("NL")]
        return (
            f'<table cellpadding="0" cellspacing="0" border="0" style="width:100%;border-spacing:0">'
            f'<tr>'
            f'<td style="{cell_style};padding-right:16px;border-right:1px solid {RULE}">'
            f'{div_col(al_divs)}</td>'
            f'<td style="width:4%"></td>'
            f'<td style="{cell_style};padding-left:16px">{div_col(nl_divs)}</td>'
            f'</tr></table>'
        )

    def mlb_bracket_html() -> str:
        round_labels = {"wc": "Wild Card", "ds": "Div. Series", "lcs": "LCS"}
        def conf_col(conf: str) -> str:
            rows = ""
            for rnd, label in round_labels.items():
                for s in bracket.get(conf, {}).get(rnd, []):
                    rows += _series_row(s, label, team_colors)
            if conf == "al":
                for s in bracket.get("ws", []):
                    rows += _series_row(s, "World Series", team_colors)
            return (f'<table cellpadding="0" cellspacing="0" border="0" '
                    f'style="width:100%;border-spacing:0">{rows}</table>')
        conf_head = (f'font-size:10px;letter-spacing:.1em;text-transform:uppercase;'
                     f'color:{MUTED};font-family:monospace;padding-bottom:8px;display:block')
        return (
            f'<table cellpadding="0" cellspacing="0" border="0" style="width:100%;border-spacing:0">'
            f'<tr>'
            f'<td style="width:48%;vertical-align:top;padding:0 16px 0 0;border-right:1px solid {RULE}">'
            f'<span style="{conf_head}">American League</span>{conf_col("al")}</td>'
            f'<td style="width:4%"></td>'
            f'<td style="width:48%;vertical-align:top;padding:0 0 0 16px">'
            f'<span style="{conf_head}">National League</span>{conf_col("nl")}</td>'
            f'</tr></table>'
        )

    standings_or_bracket = (
        section("Playoff bracket", "Camino a las World Series",
                "Wild Card (3) → Div. Series (5) → LCS (7) → World Series (7).",
                mlb_bracket_html())
        if has_playoffs else
        section("Clasificación", f"MLB {d.get('SEASON','')} · Standings por división",
                "Temporada regular — ordenados por W dentro de cada división.",
                mlb_standings_html())
    )

    return (
        f'<div style="margin-top:32px"></div>'
        + sport_header("MLB", d.get("SEASON",""), d.get("LAST_UPDATE",""))
        + standings_or_bracket
        + section("Top pitchers", "Top 10 pitchers de la temporada",
                  "Score percentil — ERA, K, W, WHIP ponderados.",
                  player_list_html(pitchers, "score", "Score", p_note, p_meta))
        + section("Top batters", "Top 10 batters de la temporada",
                  "Score percentil — HR, RBI, AVG, SB, OPS ponderados.",
                  player_list_html(batters, "score", "Score", p_note, p_meta))
        + section("Road to Glory · Jugadores",
                  "Top 10 Road to Glory",
                  f"Umbral histórico top 10: {p_thresh} (Rogers Hornsby).",
                  player_list_html(rtg.get("players",[])[:10], "careerScore", "Career",
                                   lambda p: p.get("note",""), rtg_p_meta, p_thresh))
        + section("Road to Glory · Jóvenes (≤25)",
                  "Top 10 Jóvenes",
                  "Proyección de carrera para menores de 25.",
                  player_list_html(rtg.get("youngProspects",[])[:10], "projectedScore", "Proj.",
                                   lambda p: p.get("note",""), rtg_y_meta, p_thresh))
        + section("Road to Glory · Franquicias",
                  "Top 10 Franquicias",
                  f"Umbral histórico top 10: {t_thresh} (Astros 2017).",
                  team_list_html(rtg.get("teams",[])[:10], "dynastyScore", "Dynasty",
                                 rtg_t_meta, lambda t: t.get("needs",""), t_thresh))
    )


# ── NFL ───────────────────────────────────────────────────────────

NFL_DIV_ORDER = ["AFC East", "AFC North", "AFC South", "AFC West",
                 "NFC East", "NFC North", "NFC South", "NFC West"]


def nfl_html(d: dict) -> str:
    team_map = {t["code"]: t for t in d.get("TEAMS", [])}
    players  = d.get("PLAYERS", [])
    status   = d.get("SEASON_STATUS", "")
    bracket  = d.get("BRACKET", {})

    qbs = sorted([p for p in players if p.get("stats", {}).get("type") == "passing"],
                 key=lambda p: -p["score"])[:10]

    def p_meta(p):
        tn  = team_map.get(p["teamCode"], {}).get("commonName", p["teamCode"])
        age = f" · {p['age']} años" if p.get("age") else ""
        return f"NFL · {p.get('pos','')} · {tn}{age}"

    def p_note(p):
        st = p.get("stats", {})
        t  = st.get("type", "")
        if t == "passing":
            return f"{st.get('yds',0)} yds · {st.get('td',0)} TD · {st.get('int',0)} INT"
        if t == "rushing":
            return f"{st.get('yds',0)} yds · {st.get('td',0)} TD"
        if t == "receiving":
            return f"{st.get('yds',0)} yds · {st.get('td',0)} TD · {st.get('rec',0)} rec"
        return ""

    def nfl_standings_html() -> str:
        div_map = {div: [] for div in NFL_DIV_ORDER}
        for t in d.get("TEAMS", []):
            div = t.get("div", "")
            if div in div_map:
                div_map[div].append(t)
        for div in div_map:
            div_map[div].sort(key=lambda t: (-t["w"], t["l"]))

        div_head = (f'font-size:10px;letter-spacing:.1em;text-transform:uppercase;'
                    f'color:{MUTED};font-family:monospace;padding:8px 0 4px;'
                    f'border-bottom:1px solid {RULE};display:block;margin-bottom:2px')

        def div_col(divs: list[str]) -> str:
            out = ""
            for div in divs:
                out += f'<span style="{div_head}">{div}</span>'
                for i, t in enumerate(div_map.get(div, []), 1):
                    out += (
                        f'<table cellpadding="0" cellspacing="0" border="0" '
                        f'style="width:100%;border-spacing:0;padding:4px 0"><tr>'
                        f'<td style="width:20px;color:{MUTED};font-size:11px;font-family:monospace">{i}</td>'
                        f'<td style="padding:0 4px">{swatch(t["colors"]["primary"], 8)}'
                        f'<span style="font-size:13px;font-weight:600;color:{INK}">{t["shortName"]}</span></td>'
                        f'<td style="text-align:right;font-size:12px;font-family:monospace;color:{INK2};white-space:nowrap">'
                        f'{t["w"]}–{t["l"]}</td>'
                        f'</tr></table>'
                    )
            return out

        afc_divs = [d for d in NFL_DIV_ORDER if d.startswith("AFC")]
        nfc_divs = [d for d in NFL_DIV_ORDER if d.startswith("NFC")]
        return (
            f'<table cellpadding="0" cellspacing="0" border="0" style="width:100%;border-spacing:0"><tr>'
            f'<td style="vertical-align:top;width:48%;padding-right:16px;border-right:1px solid {RULE}">'
            f'{div_col(afc_divs)}</td>'
            f'<td style="width:4%"></td>'
            f'<td style="vertical-align:top;width:48%;padding-left:16px">{div_col(nfc_divs)}</td>'
            f'</tr></table>'
        )

    has_playoffs = bool(
        (bracket.get("afc", {}).get("wc") or [{}])[0].get("hi") or
        (bracket.get("nfc", {}).get("wc") or [{}])[0].get("hi")
    )
    team_colors = {code: t["colors"]["primary"] for code, t in team_map.items()}

    def nfl_bracket_html() -> str:
        round_labels = {"wc": "Wild Card", "div": "Divisional", "conf": "Conf. Champ."}
        def conf_col(conf: str) -> str:
            rows = ""
            for rnd, label in round_labels.items():
                for s in bracket.get(conf, {}).get(rnd, []):
                    rows += _series_row(s, label, team_colors)
            if conf == "afc":
                for s in bracket.get("sb", []):
                    rows += _series_row(s, "Super Bowl", team_colors)
            return (f'<table cellpadding="0" cellspacing="0" border="0" '
                    f'style="width:100%;border-spacing:0">{rows}</table>')
        conf_head = (f'font-size:10px;letter-spacing:.1em;text-transform:uppercase;'
                     f'color:{MUTED};font-family:monospace;padding-bottom:8px;display:block')
        return (
            f'<table cellpadding="0" cellspacing="0" border="0" style="width:100%;border-spacing:0"><tr>'
            f'<td style="width:48%;vertical-align:top;padding:0 16px 0 0;border-right:1px solid {RULE}">'
            f'<span style="{conf_head}">AFC</span>{conf_col("afc")}</td>'
            f'<td style="width:4%"></td>'
            f'<td style="width:48%;vertical-align:top;padding:0 0 0 16px">'
            f'<span style="{conf_head}">NFC</span>{conf_col("nfc")}</td>'
            f'</tr></table>'
        )

    standings_or_bracket = (
        section("Playoff bracket", "Camino al Super Bowl",
                "Wild Card → Divisional → Conf. Champ. → Super Bowl.",
                nfl_bracket_html())
        if has_playoffs else
        section("Clasificación final", f"NFL {d.get('SEASON','')} · Standings por división",
                "Temporada regular finalizada — ordenados por victorias.",
                nfl_standings_html())
    )

    return (
        f'<div style="margin-top:32px"></div>'
        + sport_header("NFL", d.get("SEASON",""), d.get("LAST_UPDATE",""),
                       title="NFL Season")
        + standings_or_bracket
        + section("Top quarterbacks", "Top 10 QBs de la temporada",
                  "Score percentil — yds, TD, INT, completion% ponderados.",
                  player_list_html(qbs, "score", "Score", p_note, p_meta))
    )


# ── F1 ────────────────────────────────────────────────────────────

def f1_html(d: dict) -> str:
    drivers      = d.get("DRIVERS", [])
    constructors = d.get("CONSTRUCTORS", [])
    last_race    = d.get("LAST_RACE") or {}
    legends      = d.get("LEGENDS", [])
    round_num    = d.get("ROUND", 0)
    total        = d.get("TOTAL_ROUNDS", 0)
    max_pts      = d.get("MAX_SEASON_PTS", 1)
    remaining    = max(0, total - round_num)
    second_pts   = drivers[1]["points"] if len(drivers) > 1 else 0
    threshold    = min(second_pts + remaining * 25 + 1, max_pts) if remaining > 0 else None

    def d_meta(p):
        return f"F1 · {p.get('country','')} · {p.get('teamCode','')}"

    def d_note(p):
        wins = p.get("wins", 0)
        return f"{wins} victoira{'s' if wins != 1 else ''} · {remaining} carreras restantes"

    def podium_html() -> str:
        if not last_race:
            return '<p style="color:{MUTED};font-size:13px">Sin datos de carrera.</p>'
        podium = last_race.get("podium", [])
        rows = ""
        medals = ["🥇", "🥈", "🥉"]
        for pos in podium[:3]:
            color   = pos.get("primary", MUTED)
            medal   = medals[pos["position"] - 1] if pos["position"] <= 3 else str(pos["position"])
            rows += (
                f'<tr style="border-bottom:1px solid {RULE}">'
                f'<td style="padding:9px 8px;font-size:16px;width:28px">{medal}</td>'
                f'<td style="padding:9px 8px 9px 0;font-size:13px;font-weight:600;color:{INK}">'
                f'{swatch(color)}{pos.get("name","")}</td>'
                f'<td style="padding:9px 0;font-size:11px;color:{MUTED};font-family:monospace;'
                f'text-align:right">{pos.get("team","")}</td>'
                f'</tr>'
            )
        name    = last_race.get("name","")
        circuit = last_race.get("circuit","")
        date    = last_race.get("date","")
        return (
            f'<div style="font-size:11px;color:{MUTED};font-family:monospace;margin-bottom:8px">'
            f'{circuit} · {date}</div>'
            f'<table cellpadding="0" cellspacing="0" border="0" '
            f'style="width:100%;border-collapse:collapse">{rows}</table>'
        )

    def lg_meta(p):
        st = p.get("stats", {})
        return (f"{p.get('country','')} · {st.get('titles',0)} títulos · "
                f"{st.get('wins',0)} victorias · {st.get('poles',0)} poles")

    return (
        f'<div style="margin-top:32px"></div>'
        + sport_header("F1", d.get("SEASON",""), d.get("UPDATED",""),
                       title="F1 World Championship")
        + section("Última carrera", last_race.get("name","Última carrera"),
                  f"Ronda {round_num}/{total}",
                  podium_html())
        + section("Campeonato de Pilotos",
                  f"Top 10 — Temporada {d.get('SEASON','')}",
                  f"Puntos máximos de temporada: {max_pts}. Umbral para ser campeón: {threshold} pts.",
                  player_list_html(drivers[:10], "points", "Puntos", d_note, d_meta, threshold))
        + section("Campeonato de Constructores",
                  "Top Constructores",
                  "Clasificación acumulada por escudería.",
                  player_list_html(constructors[:10], "points", "Puntos",
                                   lambda c: c.get("id",""),
                                   lambda c: ""))
        + section("Road to Glory · Leyendas F1",
                  "Los mejores de la historia",
                  "Score: títulos × 10 + victorias × 0.2 + poles × 0.1",
                  player_list_html(legends[:10], "legendScore", "Legend",
                                   lambda p: "", lg_meta))
    )


# ── MotoGP ────────────────────────────────────────────────────────

def motogp_html(d: dict) -> str:
    riders    = d.get("RIDERS", [])
    last_race = d.get("LAST_RACE") or {}
    legends   = d.get("LEGENDS", [])
    round_num = d.get("ROUND", 0)
    total     = d.get("TOTAL_ROUNDS", 0)
    max_pts   = d.get("MAX_SEASON_PTS", 1)
    remaining = max(0, total - round_num)
    second_pts = riders[1]["points"] if len(riders) > 1 else 0
    threshold  = min(second_pts + remaining * 25 + 1, max_pts) if remaining > 0 else None

    def r_meta(p):
        return f"MotoGP · {p.get('country','')} · {p.get('bike','')}"

    def r_note(p):
        return f"{remaining} carreras restantes en la temporada"

    def lg_meta(p):
        st = p.get("stats", {})
        return (f"{p.get('country','')} · {st.get('titles',0)} títulos · "
                f"{st.get('wins',0)} victorias · {st.get('poles',0)} poles")

    last_winner_html = ""
    if last_race:
        color = last_race.get("primary", MUTED)
        last_winner_html = (
            f'<div style="font-size:13px;color:{INK};padding:10px 0">'
            f'{swatch(color)}<b>{last_race.get("winner","")}</b>'
            f' <span style="color:{MUTED}">({last_race.get("bike","")})</span> — '
            f'Ronda {last_race.get("round","")} · {last_race.get("name","")}</div>'
        )

    return (
        f'<div style="margin-top:32px"></div>'
        + sport_header("MotoGP", d.get("SEASON",""), d.get("UPDATED",""),
                       title="MotoGP World Championship")
        + section("Última carrera", last_race.get("name","Última carrera"),
                  f"Ronda {round_num}/{total}",
                  last_winner_html)
        + section("Campeonato de Pilotos",
                  f"Top 10 — Temporada {d.get('SEASON','')}",
                  f"Puntos máximos: {max_pts}. Umbral para ser campeón: {threshold} pts.",
                  player_list_html(riders[:10], "points", "Puntos", r_note, r_meta, threshold))
        + section("Road to Glory · Leyendas MotoGP",
                  "Los mejores de la historia",
                  "Score: títulos × 10 + victorias × 0.2 + poles × 0.1",
                  player_list_html(legends[:10], "legendScore", "Legend",
                                   lambda p: "", lg_meta))
    )


# ── AFL ───────────────────────────────────────────────────────────

def afl_html(d: dict) -> str:
    ladder     = d.get("LADDER", [])
    last_round = d.get("LAST_ROUND", [])
    legends    = d.get("LEGENDS", [])
    round_num  = d.get("ROUND", 0)

    def ladder_html() -> str:
        rows = ""
        for i, t in enumerate(ladder[:18], 1):
            color = t.get("primary", MUTED)
            pct   = f"{t.get('percentage', 0):.1f}%"
            marker = ""
            if i == 8:
                marker = (f'<tr><td colspan="4" style="padding:2px 0;font-size:9px;'
                          f'letter-spacing:.08em;text-transform:uppercase;color:{MUTED};'
                          f'font-family:monospace;border-bottom:2px solid {ACCENT}">Línea playoff</td></tr>')
            rows += (
                marker +
                f'<tr style="border-bottom:1px solid {RULE}">'
                f'<td style="padding:7px 8px;font-size:14px;color:{MUTED};width:28px;'
                f'font-family:monospace">{i}</td>'
                f'<td style="padding:7px 4px;font-size:13px;font-weight:600;color:{INK}">'
                f'{swatch(color, 8)}{t.get("name","")}</td>'
                f'<td style="padding:7px 8px;font-size:12px;font-family:monospace;color:{INK2};'
                f'text-align:right;white-space:nowrap">{t.get("wins",0)}–{t.get("losses",0)}</td>'
                f'<td style="padding:7px 0 7px 8px;font-size:11px;color:{MUTED};'
                f'font-family:monospace;text-align:right">{pct}</td>'
                f'</tr>'
            )
        return (f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="width:100%;border-collapse:collapse">{rows}</table>')

    def results_html() -> str:
        rows = ""
        for g in last_round:
            hw = g.get("winner") == g.get("hteam")
            aw = g.get("winner") == g.get("ateam")
            h_style = f'font-weight:{"700" if hw else "400"};color:{INK if hw else MUTED}'
            a_style = f'font-weight:{"700" if aw else "400"};color:{INK if aw else MUTED}'
            rows += (
                f'<tr style="border-bottom:1px solid {RULE}">'
                f'<td style="padding:7px 8px 7px 0;font-size:12px;{h_style}">'
                f'{swatch(g.get("hprimary", MUTED), 8)}{g.get("hteam","")}</td>'
                f'<td style="padding:7px 4px;font-size:12px;font-family:monospace;'
                f'color:{INK};text-align:center;white-space:nowrap">'
                f'{g.get("hscore","")} – {g.get("ascore","")}</td>'
                f'<td style="padding:7px 0 7px 8px;font-size:12px;{a_style};text-align:right">'
                f'{g.get("ateam","")}{swatch(g.get("aprimary", MUTED), 8)}</td>'
                f'</tr>'
            )
        return (f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="width:100%;border-collapse:collapse">{rows}</table>')

    def lg_meta(p):
        st = p.get("stats", {})
        return (f"{p.get('teamCode','')} · {st.get('flags',0)} flags VFL/AFL · "
                f"{st.get('brownlow',0)} Brownlow · {st.get('all_aus',0)} All-Australian")

    return (
        f'<div style="margin-top:32px"></div>'
        + sport_header("AFL", d.get("SEASON",""), d.get("UPDATED",""),
                       title="AFL Season")
        + section("Clasificación", f"AFL {d.get('SEASON','')} — Jornada {round_num}",
                  "Ordenado por puntos de competición. Los 8 primeros clasifican a playoffs.",
                  ladder_html())
        + section("Última jornada", f"Resultados — Ronda {round_num}",
                  "Resultados de la última ronda completada.",
                  results_html())
        + section("Road to Glory · Leyendas VFL/AFL",
                  "Los mejores de la historia",
                  "Score: flags × 8 + Brownlow × 5 + All-Australian × 1.5",
                  player_list_html(legends[:10], "legendScore", "Legend",
                                   lambda p: "", lg_meta))
    )


# ── Tennis ────────────────────────────────────────────────────────

def tennis_html(d: dict) -> str:
    atp       = d.get("ATP", [])
    wta       = d.get("WTA", [])
    atp_ch    = d.get("ATP_CHANGES", {})
    wta_ch    = d.get("WTA_CHANGES", {})
    atp_lg    = d.get("ATP_LEGENDS", [])
    wta_lg    = d.get("WTA_LEGENDS", [])
    atp_yday  = d.get("ATP_RECENT", [])
    atp_today = d.get("ATP_TODAY", [])
    wta_yday  = d.get("WTA_RECENT", [])
    wta_today = d.get("WTA_TODAY", [])
    atp_tourn = d.get("ATP_TOURNAMENT", {})
    wta_tourn = d.get("WTA_TOURNAMENT", {})

    def p_meta(p):
        sf  = p.get("surface") or {}
        h   = int((sf.get("hard")  or 0) * 100)
        cl  = int((sf.get("clay")  or 0) * 100)
        gr  = int((sf.get("grass") or 0) * 100)
        return f"{p.get('country','')} · Dura {h}% · Tierra {cl}% · Hierba {gr}%"

    def p_note(p):
        st = p.get("stats", {})
        tourney = p.get("tournamentStatus") or {}
        tournament_note = ""
        if tourney.get("tournament"):
            if tourney.get("state") == "alive":
                tournament_note = f'{tourney.get("tournament")}: vivo'
            else:
                tournament_note = tourney.get("reason") or f'{tourney.get("tournament")}: eliminado/no compite'
        base = f"{st.get('gs',0)} GS · {st.get('titles',0)} títulos · #{p.get('rank','')}"
        return f"{tournament_note} · {base}" if tournament_note else base

    def active_ids(players: list[dict]) -> set[str]:
        return {str(p.get("id")) for p in players if (p.get("tournamentStatus") or {}).get("state") == "alive"}

    def tournament_display(players: list[dict], tournament: dict) -> list[dict]:
        base = list(players[:10])
        alive = active_ids(players)
        if not alive:
            return base
        include_all = 0 < int(tournament.get("aliveCount") or 0) <= 8
        min_alive = 2
        seen = {str(p.get("id")) for p in base}
        def alive_count() -> int:
            return sum(1 for p in base if str(p.get("id")) in alive)
        for p in players:
            if not include_all and alive_count() >= min_alive:
                break
            pid = str(p.get("id"))
            if pid not in seen and pid in alive:
                base.append(p)
                seen.add(pid)
        return base

    def lg_meta(p):
        st = p.get("stats", {})
        return (f"{p.get('country','')} · {st.get('gs',0)} Grand Slams · "
                f"{st.get('year_end_no1',0)} cierres #1 · {st.get('weeks_no1',0)} semanas #1")

    def changes_html(ch: dict) -> str:
        entered = ch.get("entered", [])
        exited  = ch.get("exited", [])
        prev    = ch.get("prev_date", "")
        curr    = ch.get("curr_date", "")
        if not entered and not exited:
            return (f'<div style="padding:10px 0;font-size:13px;color:{MUTED};'
                    f'font-family:monospace">Sin cambios vs {prev}</div>')
        rows = ""
        for p in entered:
            color = p.get("primary", GOOD)
            rows += (
                f'<tr style="border-bottom:1px solid {RULE}">'
                f'<td style="padding:7px 0;font-size:20px;color:{GOOD};width:24px">↑</td>'
                f'<td style="padding:7px 8px;font-size:13px;font-weight:600;color:{INK}">'
                f'{swatch(color)}{p.get("name","")}</td>'
                f'<td style="padding:7px 0;font-size:12px;font-family:monospace;'
                f'color:{GOOD};text-align:right">#{p.get("rank","")}</td>'
                f'</tr>'
            )
        for p in exited:
            color = p.get("primary", ACCENT)
            rows += (
                f'<tr style="border-bottom:1px solid {RULE}">'
                f'<td style="padding:7px 0;font-size:20px;color:{ACCENT};width:24px">↓</td>'
                f'<td style="padding:7px 8px;font-size:13px;font-weight:600;color:{MUTED}">'
                f'{swatch(color)}{p.get("name","")}</td>'
                f'<td style="padding:7px 0;font-size:12px;font-family:monospace;'
                f'color:{MUTED};text-align:right">salió</td>'
                f'</tr>'
            )
        return (
            f'<div style="font-size:11px;color:{MUTED};font-family:monospace;margin-bottom:6px">'
            f'{prev} → {curr}</div>'
            f'<table cellpadding="0" cellspacing="0" border="0" '
            f'style="width:100%;border-collapse:collapse">{rows}</table>'
        )

    def matches_html(tournaments: list[dict], scheduled: bool = False) -> str:
        rows = ""
        for t in tournaments:
            rows += (
                f'<tr><td colspan="3" style="padding:10px 0 6px;border-bottom:2px solid {INK};">'
                f'{swatch("#c47a4b", 9)}'
                f'<b style="font-size:15px;color:{INK}">{t.get("name","")}</b>'
                f'<span style="font-size:11px;color:{MUTED};font-family:monospace;'
                f'text-transform:uppercase;margin-left:8px">{t.get("level","")} · {t.get("surface","")}</span>'
                f'</td></tr>'
            )
            for m in t.get("matches", [])[:8]:
                left_weight = "400" if scheduled or m.get("scheduled") else "700"
                sep = "vs" if scheduled or m.get("scheduled") else "def."
                rows += (
                    f'<tr style="border-bottom:1px solid {RULE}">'
                    f'<td style="padding:8px 10px 8px 0;width:82px;vertical-align:top;'
                    f'font-family:monospace;font-size:11px;color:{MUTED};text-transform:uppercase">'
                    f'{m.get("day","")} · {m.get("round","")}</td>'
                    f'<td style="padding:8px 0;vertical-align:top;font-size:13px;color:{INK2}">'
                    f'<span style="font-weight:{left_weight};color:{INK}">{m.get("w","")}</span>'
                    f'{score_chip(m.get("w_score"))}'
                    f'<span style="color:{MUTED};margin:0 6px">{sep}</span>'
                    f'<span>{m.get("l","")}</span>'
                    f'{score_chip(m.get("l_score"))}'
                    f'</td>'
                    f'<td style="padding:8px 0 8px 8px;text-align:right;vertical-align:top;'
                    f'font-family:monospace;font-size:12px;color:{MUTED};white-space:nowrap">'
                    f'{m.get("score","por jugar")}</td>'
                    f'</tr>'
                )
        if not rows:
            return (f'<div style="padding:10px 0;font-size:13px;color:{MUTED};'
                    f'font-family:monospace">Sin partidos importantes disponibles.</div>')
        return (f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="width:100%;border-collapse:collapse;background:{PAPER}">{rows}</table>')

    updated = d.get("UPDATED", "")
    return (
        f'<div style="margin-top:32px"></div>'
        + sport_header("Tennis", "2026", updated, title="ATP · WTA Rankings")
        + section("ATP · Partidos importantes", "ATP — Ayer",
                  "Top resultados de ayer por mejor score individual del duelo.",
                  matches_html(atp_yday, scheduled=False))
        + section("ATP · Partidos importantes", "ATP — Hoy",
                  "Top partidos programados hoy por mejor score individual del duelo.",
                  matches_html(atp_today, scheduled=True))
        + (section("WTA · Partidos importantes", "WTA — Ayer",
                   "Top resultados de ayer por mejor score individual del duelo.",
                   matches_html(wta_yday, scheduled=False)) if wta_yday else "")
        + (section("WTA · Partidos importantes", "WTA — Hoy",
                   "Top partidos programados hoy por mejor score individual del duelo.",
                   matches_html(wta_today, scheduled=True)) if wta_today else "")
        + section("ATP Top 10", "Top 10 ATP Singles — Score activo",
                  f'{atp_tourn.get("name","Torneo actual")}: vivos en claro; eliminados/no inscritos sombreados.',
                  player_list_html(tournament_display(atp, atp_tourn), "activeScore", "Score", p_note, p_meta))
        + section("Cambios ATP Top 10", "Quién entra y sale del top 10",
                  "Comparado con el ranking de la semana pasada.",
                  changes_html(atp_ch))
        + section("WTA Top 10", "Top 10 WTA Singles — Score activo",
                  f'{wta_tourn.get("name","Torneo actual")}: vivas en claro; eliminadas/no inscritas sombreadas.',
                  player_list_html(tournament_display(wta, wta_tourn), "activeScore", "Score", p_note, p_meta))
        + section("Cambios WTA Top 10", "Quién entra y sale del top 10",
                  "Comparado con el ranking de la semana pasada.",
                  changes_html(wta_ch))
        + section("Road to Glory · Leyendas ATP",
                  "Top 10 leyendas ATP",
                  "Score: GS × 12 + cierres #1 × 3 + semanas #1 ÷ 10",
                  player_list_html(atp_lg[:10], "legendScore", "Legend",
                                   lambda p: "", lg_meta))
        + section("Road to Glory · Leyendas WTA",
                  "Top 10 leyendas WTA",
                  "Score: GS × 12 + cierres #1 × 3 + semanas #1 ÷ 10",
                  player_list_html(wta_lg[:10], "legendScore", "Legend",
                                   lambda p: "", lg_meta))
    )


# ── Cycling ───────────────────────────────────────────────────────

def cycling_html(d: dict) -> str:
    legends      = d.get("LEGENDS", [])
    cr           = d.get("CURRENT_RACE") or {}

    def lg_meta(p):
        st = p.get("stats", {})
        return (f"{p.get('country','')} · Tour {st.get('tour',0)} · Giro {st.get('giro',0)} · "
                f"Vuelta {st.get('vuelta',0)} · Monumentos {st.get('monuments',0)}")

    def gc_table_html(gc: list) -> str:
        return player_list_html(
            gc[:10],
            "legendScore",
            "Leyenda",
            lambda r: "Ya suma palmarés histórico" if r.get("legendScore", 0) > 0 else "Sin grandes títulos todavía",
            lambda r: f'{r.get("team","")} · {r.get("country","")}',
            threshold=100,
            score_b_key="time",
            score_b_label="Tiempo" if (gc and gc[0].get("rank") == 1) else "GC",
        )

    def jersey_leaders_html() -> str:
        pl = cr.get("points_leader") or {}
        kl = cr.get("kom_leader") or {}
        yl = cr.get("young_leader") or {}
        def row(emoji, label, leader):
            if not leader:
                return ""
            color    = leader.get("primary", MUTED)
            val      = leader.get("points") or leader.get("time") or ""
            lg_score = leader.get("legendScore", 0.0)
            lg_pct   = min(100.0, lg_score)
            fill_px  = round(50 * lg_pct / 100)
            lg_bar   = (
                f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="display:inline-table;width:50px;height:4px;background:{BAR_BG};'
                f'border-spacing:0;vertical-align:middle;margin-left:4px">'
                f'<tr><td style="width:{fill_px}px;background:{BAR_FILL};height:4px;padding:0"></td>'
                f'<td style="background:{BAR_BG};height:4px;padding:0"></td></tr></table>'
                f'<span style="font-size:9px;color:{MUTED};font-family:monospace;margin-left:3px">'
                f'{lg_score:.0f}/100</span>'
            )
            return (
                f'<tr style="border-bottom:1px solid {RULE}">'
                f'<td style="padding:9px 8px;font-size:18px;width:28px">{emoji}</td>'
                f'<td style="padding:9px 6px 9px 0;vertical-align:top">'
                f'<div style="font-size:9px;letter-spacing:.08em;text-transform:uppercase;'
                f'color:{MUTED};font-family:monospace">{label}</div>'
                f'<div style="font-size:13px;font-weight:600;color:{INK}">'
                f'{swatch(color)}{leader.get("name","")}</div>'
                f'<div style="font-size:11px;color:{MUTED};font-family:monospace;'
                f'margin-top:2px">{leader.get("country","")} · {leader.get("team","")}</div>'
                f'<div style="margin-top:4px;display:inline-flex;align-items:center">'
                f'{lg_bar}</div>'
                f'</td>'
                f'<td style="padding:9px 0;font-size:16px;font-weight:700;color:{ACCENT};'
                f'text-align:right;white-space:nowrap;vertical-align:top">{val}</td>'
                f'</tr>'
            )
        rows = row("🟣", "Puntos (Maglia Ciclamino)", pl)
        rows += row("🔵", "Montaña (Maglia Azzurra)", kl)
        rows += row("⬜", "Joven (Maglia Bianca)", yl)
        return (f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="width:100%;border-collapse:collapse">{rows}</table>')

    def last_stage_html() -> str:
        ls = cr.get("last_stage") or {}
        if not ls:
            return f'<div style="color:{MUTED};font-family:monospace;padding:8px 0">Sin datos de etapa.</div>'
        color    = ls.get("winner_primary", MUTED)
        route    = f'{ls.get("from","")} → {ls.get("to","")}'.strip(" →")
        type_map = {
            "Flat stage": "Etapa llana",
            "Mountain stage": "Etapa de montaña",
            "Hilly stage": "Etapa con colinas",
            "Individual time trial": "Contrarreloj individual",
            "Team time trial": "Contrarreloj por equipos",
        }
        type_es = type_map.get(ls.get("type",""), ls.get("type",""))
        return (
            f'<div style="font-size:11px;color:{MUTED};font-family:monospace;margin-bottom:6px">'
            f'{ls.get("date","")} · {type_es} · {route}</div>'
            f'<div style="font-size:16px;font-weight:600;color:{INK};padding:6px 0">'
            f'{swatch(color, 12)}{ls.get("winner","")}'
            f' <span style="font-size:12px;color:{MUTED};font-weight:400">'
            f'({ls.get("winner_cc","")})</span></div>'
        )

    def next_stage_html() -> str:
        ns = cr.get("next_stage") or {}
        if not ns:
            return f'<div style="color:{MUTED};font-family:monospace;padding:8px 0">Carrera finalizada.</div>'
        type_map = {
            "Flat stage": "Etapa llana",
            "Mountain stage": "Etapa de montaña ⛰️",
            "Hilly stage": "Etapa con colinas",
            "Individual time trial": "Contrarreloj individual ⏱️",
            "Team time trial": "Contrarreloj por equipos ⏱️",
        }
        type_es = type_map.get(ns.get("type",""), ns.get("type",""))
        dist    = f' · {ns["dist_km"]} km' if ns.get("dist_km") else ""
        route   = f'{ns.get("from","")} → {ns.get("to","")}'.strip(" →")
        return (
            f'<div style="font-size:14px;font-weight:600;color:{INK};padding:10px 0 4px">'
            f'{ns.get("date","")} · {type_es}{dist}</div>'
            f'<div style="font-size:12px;color:{INK2};font-family:monospace">{route}</div>'
        )

    if cr:
        race_name  = cr.get("name","Gran Vuelta")
        stage_num  = cr.get("stage", 0)
        total_st   = cr.get("total_stages", 21)
        gc         = cr.get("gc", [])
        gc_leader  = gc[0]["name"] if gc else ""
        jersey_nm  = cr.get("jersey_name","")
        ns         = cr.get("next_stage") or {}
        race_finished = bool(stage_num >= total_st and not ns)
        leader_label = "Campeón" if race_finished else "Líder"
        gc_title = "GC final" if race_finished else "GC"
        stage_sub = f"{race_name} 2026 · finalizado" if race_finished else f"{race_name} 2026 · en directo"
        next_sub = "No quedan etapas pendientes." if race_finished else f"{race_name} continúa mañana."
        jersey_section = "Maillots finales" if race_finished else "Líderes de maillot"
        jersey_sub = "Clasificaciones secundarias finales." if race_finished else "Barra = score histórico de leyendas (Merckx=100)."
        ns_label   = f'Etapa {ns["stage"]}' if ns else "Sin etapas pendientes"
        sections_html = (
            section("Última etapa", f"Etapa {stage_num} de {total_st}",
                    stage_sub,
                    last_stage_html())
            + section("Próxima etapa", ns_label,
                      next_sub,
                      next_stage_html())
            + section("Clasificación General", f"{gc_title} — Etapa {stage_num}/{total_st}",
                      f"{leader_label}: {gc_leader} · {jersey_nm}. Score leyenda: Tour×12, Giro×9, Vuelta×8, Monumentos×4, Mundiales×4; Merckx=100.",
                      gc_table_html(gc))
            + section(jersey_section,
                      "Puntos · Montaña · Mejor joven",
                      jersey_sub,
                      jersey_leaders_html())
        )
    else:
        sections_html = section(
            "En curso", "Gran vuelta activa",
            "No hay gran vuelta en curso actualmente.",
            f'<div style="padding:10px 0;font-size:13px;color:{MUTED};font-family:monospace">'
            f'Próxima carrera: Tour de France (4 jul).</div>'
        )

    return (
        f'<div style="margin-top:32px"></div>'
        + sport_header("Cycling", "2026", d.get("UPDATED",""),
                       title=cr.get("name","UCI Road Cycling") + " 2026" if cr else "UCI Road Cycling")
        + sections_html
        + section("Road to Glory · Leyendas del Ciclismo",
                  "Los mejores de la historia",
                  "Tour × 12 · Giro × 9 · Vuelta × 8 · Monumentos × 4 · Mundiales × 4",
                  player_list_html(legends[:10], "legendScore", "Legend",
                                   lambda p: "", lg_meta))
    )


# ── Sumo ──────────────────────────────────────────────────────────

def sumo_html(d: dict) -> str:
    banzuke   = d.get("BANZUKE", [])
    basho     = d.get("BASHO_INFO") or {}
    legends   = d.get("LEGENDS", [])

    def record_str(w: dict) -> str:
        if w.get("wins", 0) == 0 and w.get("losses", 0) == 0:
            return f'Kyujo ({w.get("absences",0)}A)'
        r = f'{w.get("wins",0)}W–{w.get("losses",0)}L'
        if w.get("absences", 0) > 0:
            r += f'–{w["absences"]}A'
        return r

    def standings_html() -> str:
        winner = basho.get("winner", "")
        # Top 5 by wins, excluding pure-absence entries
        active  = [w for w in banzuke if w.get("wins", 0) > 0 or w.get("losses", 0) > 0]
        top5    = sorted(active, key=lambda w: -w.get("wins", 0))[:5]
        top5_names = {w["name"] for w in top5}
        yokozunas  = [w for w in banzuke if w.get("rankShort", "") == "Yokozuna" and w["name"] not in top5_names]

        def wrestler_row(w: dict, label: str = "") -> str:
            short_rank = w.get("rankShort", w.get("rankLabel", ""))
            lg_score   = w.get("legendScore", 0.0)
            fill_px    = round(60 * min(100.0, lg_score) / 100)
            is_winner  = w["name"] == winner
            age        = w.get("age")
            age_html   = (f' <span style="font-size:10px;color:{MUTED};font-weight:400">{age} años</span>'
                          if age else "")
            name_html  = f'<b>{w["name"]}</b>{age_html}'
            if is_winner:
                name_html += f' <span style="background:{ACCENT};color:#fff;font-size:9px;border-radius:3px;padding:1px 5px;vertical-align:middle">🏆 Campeón</span>'
            lg_bar = (
                f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="display:inline-table;width:60px;height:4px;background:{BAR_BG};'
                f'border-spacing:0;vertical-align:middle">'
                f'<tr><td style="width:{fill_px}px;background:{BAR_FILL};height:4px;padding:0"></td>'
                f'<td style="background:{BAR_BG};height:4px;padding:0"></td></tr></table>'
                f' <span style="font-size:9px;color:{MUTED};font-family:monospace">'
                f'{lg_score:.0f}/100</span>'
            )
            return (
                f'<tr style="border-bottom:1px solid {RULE}">'
                f'<td style="padding:8px 6px 8px 0;font-size:13px;color:{INK};vertical-align:top">'
                f'{name_html}'
                f'<div style="font-size:10px;color:{MUTED};font-family:monospace;margin-top:2px">{short_rank}</div>'
                f'<div style="margin-top:4px">{lg_bar}</div>'
                f'</td>'
                f'<td style="padding:8px 0;font-size:12px;font-family:monospace;font-weight:600;'
                f'color:{INK2};text-align:right;vertical-align:top;white-space:nowrap">'
                f'{record_str(w)}</td>'
                f'</tr>'
            )

        sep_style = (f'font-size:9px;letter-spacing:.1em;text-transform:uppercase;'
                     f'color:{MUTED};font-family:monospace;padding:6px 0 4px;'
                     f'border-bottom:2px solid {INK};display:block;margin-bottom:2px')
        rows = f'<tr><td colspan="2"><span style="{sep_style}">Top por victorias</span></td></tr>'
        for w in top5:
            rows += wrestler_row(w)
        if yokozunas:
            rows += f'<tr><td colspan="2"><span style="{sep_style}">Yokozunas</span></td></tr>'
            for w in yokozunas:
                rows += wrestler_row(w)
        return (f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="width:100%;border-collapse:collapse">{rows}</table>')

    def lg_meta(p):
        st = p.get("stats", {})
        era = ""
        if st.get("yok_start"):
            era = f' · Yokozuna {st["yok_start"]}–{st["yok_end"] or "hoy"}'
        return f"{p.get('country','')}{era}"

    winner      = basho.get("winner","")
    basho_id    = basho.get("id","")
    start       = basho.get("startDate","")[:10]
    end         = basho.get("endDate","")[:10]
    basho_note  = f"Basho {basho_id} · {start} – {end}" if basho_id else "Sin basho activo"
    winner_html = (
        f'<div style="font-size:13px;color:{INK};padding:10px 0">'
        f'{swatch(ACCENT)}<b>Campeón: {winner}</b>'
        f' <span style="color:{MUTED}">({basho_note})</span></div>'
        if winner else
        f'<div style="padding:10px 0;font-size:13px;color:{MUTED};font-family:monospace">'
        f'{basho_note}</div>'
    )

    return (
        f'<div style="margin-top:32px"></div>'
        + sport_header("Sumo", "2026", d.get("UPDATED",""), title="Sumo — Banzuke")
        + section("Último basho", "Campeón del torneo", basho_note, winner_html)
        + section(f"Clasificación — {basho_id}",
                  "Top 5 + Yokozunas",
                  "Ordenado por victorias · Score de leyendas (Hakuho=100) junto a cada luchador.",
                  standings_html())
        + section("Road to Glory · Leyendas del Sumo",
                  "Los mejores de la historia",
                  "Score: yusho × 10 + basho como Yokozuna × 0.5",
                  player_list_html(legends[:10], "legendScore", "Legend",
                                   lambda p: "", lg_meta))
    )


# ── Rugby ─────────────────────────────────────────────────────────

def golf_html(d: dict) -> str:
    major  = d.get("CURRENT_MAJOR") or {}
    current = d.get("CURRENT", [])
    legends = d.get("LEGENDS", [])
    road = d.get("ROAD_TO_GLORY", [])
    threshold = d.get("LEGEND_THRESHOLD") or (legends[9].get("legendScore") if len(legends) >= 10 else 0)

    def p_meta(p):
        st = p.get("stats", {})
        return f'{st.get("tour", p.get("teamCode",""))} · {p.get("country","")}'

    def current_note(p):
        st = p.get("stats", {})
        return (f'{st.get("majors",0)} majors · {st.get("eliteWins",0)} victorias élite · '
                f'{st.get("majorTop10",0)} top-10 major')

    def legend_note(p):
        st = p.get("stats", {})
        return f'{st.get("majors",0)} majors · {st.get("wins",0)} victorias · dominio {st.get("dominance",0)}'

    def road_note(p):
        return p.get("note") or (f'A {p.get("gapToTop10",0)} del top 10 histórico' if p.get("gapToTop10", 0) > 0 else "Ya está en zona top 10 histórico")

    state = major.get("state", "")
    if state == "live":
        state_txt = f'Ronda {major.get("round",1)} en juego'
    elif state == "upcoming":
        days = int(major.get("daysToStart") or 0)
        state_txt = f'Empieza en {days} día{"s" if days != 1 else ""}'
    else:
        state_txt = "Último major completado"
    tour = "Men's Major"

    def major_rows() -> str:
        leaderboard = major.get("leaderboard") or []
        if leaderboard:
            rows = ""
            for r in leaderboard[:10]:
                rows += (
                    f'<tr style="border-bottom:1px solid {RULE}">'
                    f'<td style="padding:8px 10px 8px 0;color:{MUTED};font-family:{SERIF};font-size:20px;width:38px;text-align:right">{r.get("rank","")}</td>'
                    f'<td style="padding:8px 0;font-weight:600;color:{INK}">{swatch("#2f6b3f")}{r.get("name","")}</td>'
                    f'<td style="padding:8px 0;text-align:right;font-family:{MONO};color:{ACCENT};font-weight:700">{r.get("score","-")}</td>'
                    f'</tr>'
                )
            return f'<table cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse">{rows}</table>'
        favs = major.get("favorites") or []
        if not favs:
            return f'<div style="padding:10px 0;color:{MUTED};font-family:{MONO};font-size:13px">Sin favoritos disponibles.</div>'
        rows = "".join(
            f'<tr style="border-bottom:1px solid {RULE}"><td style="padding:8px 0;color:{MUTED};font-family:{SERIF};font-size:20px;width:38px;text-align:right">{i:02d}</td>'
            f'<td style="padding:8px 0 8px 10px;font-weight:600;color:{INK}">{swatch("#2f6b3f")}{name}</td>'
            f'<td style="padding:8px 0;text-align:right;font-family:{MONO};font-size:11px;color:{MUTED}">Favorito Hermes</td></tr>'
            for i, name in enumerate(favs, 1)
        )
        return f'<table cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse">{rows}</table>'

    return (
        f'<div style="margin-top:32px"></div>'
        + sport_header("Golf", str(d.get("SEASON","")), d.get("UPDATED",""), title="Golf Majors")
        + section(f"{tour} · {state}",
                  major.get("name", "Major Championship"),
                  f'{state_txt}. {major.get("startLabel","")}–{major.get("endLabel","")} · {major.get("venue","")} · {major.get("location","")}. Defiende: {major.get("defending","N/A")}.',
                  major_rows())
        + section("Golf · Actuales",
                  "Top 10 golfistas actuales",
                  "Score activo PGA: ranking, forma de majors, victorias élite y consistencia reciente.",
                  player_list_html(current[:10], "activeScore", "Nivel", p_meta, current_note,
                                   score_b_key="legendScore", score_b_label="Leyenda"))
        + section("Road to Glory",
                  "Top 10 golfistas Road to Glory",
                  f"Umbral top 10 histórico: {threshold}. Ordenado por cercanía al territorio de leyenda.",
                  player_list_html(road[:10], "legendScore", "Leyenda", p_meta, road_note, threshold))
        + section("Golf Legends",
                  "Top 10 golfistas leyendas",
                  "Score histórico: majors × 12 + victorias × 0.45 + dominio/#1 × 0.10.",
                  player_list_html(legends[:10], "legendScore", "Legend", p_meta, legend_note, threshold))
    )


def rugby_html(d: dict) -> str:
    teams = sorted(d.get("TEAMS", []), key=lambda t: -t.get("elo", 0))[:10]
    dynasties = d.get("ROAD_TO_GLORY", {}).get("dynasties", [])[:10]
    threshold = d.get("ROAD_TO_GLORY", {}).get("dynastyThreshold", 73)

    def wc_label(count: int) -> str:
        return f"{count} Mundial{'es' if count != 1 else ''}"

    def rugby_rows(items: list[dict]) -> str:
        rows = ""
        for i, t in enumerate(items, 1):
            color = t.get("colors", {}).get("primary", ACCENT)
            rows += (
                f'<tr style="border-bottom:1px solid {RULE}">'
                f'<td style="padding:12px 14px 12px 0;font-size:26px;color:{MUTED};'
                f'font-family:{SERIF};font-variant-numeric:tabular-nums;width:42px;'
                f'vertical-align:top;text-align:right">{i:02d}</td>'
                f'<td style="padding:12px 16px 12px 0;vertical-align:top">'
                f'<div style="font-size:19px;line-height:1.15;font-family:{SERIF};'
                f'font-weight:500;color:{INK}">{swatch(color)}{t.get("name","")}</div>'
                f'<div style="font-size:10.5px;color:{MUTED};font-family:{MONO};margin-top:4px">'
                f'Rugby Union · {t.get("country","")}</div>'
                f'<div style="font-size:10.5px;color:{INK2};font-family:{MONO};margin-top:2px">'
                f'{t.get("note","")}</div>'
                f'</td>'
                f'<td style="padding:12px 12px 12px 8px;text-align:right;vertical-align:top;white-space:nowrap">'
                f'<div style="font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:{MUTED};'
                f'font-family:{MONO}">Elo</div>'
                f'<div style="font-size:28px;font-weight:500;color:{ACCENT};font-family:{SERIF};'
                f'font-variant-numeric:tabular-nums">{t.get("elo",0):.2f}</div>'
                f'</td>'
                f'<td style="padding:12px 0 12px 8px;text-align:right;vertical-align:top;white-space:nowrap">'
                f'<div style="font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:{MUTED};'
                f'font-family:{MONO}">Mundiales</div>'
                f'<div style="font-size:28px;font-weight:500;color:{INK};font-family:{SERIF};'
                f'font-variant-numeric:tabular-nums">{t.get("worldCups",0)}</div>'
                f'</td>'
                f'</tr>'
            )
        return (f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="width:100%;border-collapse:collapse">{rows}</table>')

    def dynasty_meta(t):
        return f'{t.get("era","")} · {t.get("weeksNo1",0)} semanas #1/Elo · {t.get("matchCount",0)} tests'

    def dynasty_note(t):
        return (f'{wc_label(t.get("worldCups",0))} en la época: '
                f'{t.get("worldCupYears","ninguno")}. {t.get("note","")}')

    return (
        f'<div style="margin-top:32px"></div>'
        + sport_header("Rugby", d.get("SEASON",""), d.get("UPDATED",""), title="Rugby Union · Hermes Elo")
        + section("Rugby Elo",
                  "Top 10 selecciones — Elo actual",
                  f"Modelo propio desde 1871: {d.get('SOURCE',{}).get('matches',0)} partidos y {d.get('SOURCE',{}).get('teams',0)} selecciones hasta {d.get('SOURCE',{}).get('through', d.get('UPDATED',''))}. El ranking actual aplica decay por inactividad; dinastías usan Elo histórico raw.",
                  rugby_rows(teams))
        + section("Road to Glory",
                  "Dinastías de Elo",
                  f"Umbral top 10: {threshold}. Score: años como #1 ajustados por densidad de tests + Mundiales ganados en la época.",
                  team_list_html(dynasties, "dynastyScore", "Dynasty",
                                 dynasty_meta, dynasty_note, threshold))
    )


def football_html(d: dict) -> str:
    teams = sorted(d.get("TEAMS", []), key=lambda t: -t.get("elo", 0))[:10]
    rtg = d.get("ROAD_TO_GLORY") or {}
    contenders = rtg.get("currentContenders", [])[:10]
    dynasties = rtg.get("dynasties", [])[:10]
    threshold = rtg.get("dynastyThreshold", 70)
    raw_threshold = rtg.get("rawDynastyThreshold", 0)

    def trophy_label(wc: int, continental: int) -> str:
        parts = []
        if wc:
            parts.append(f'{wc} Mundial{"es" if wc != 1 else ""}')
        if continental:
            parts.append(f'{continental} continental{"es" if continental != 1 else ""}')
        return " · ".join(parts) if parts else "Sin grandes títulos en la era"

    def elo_rows(rows: list[dict]) -> str:
        return player_list_html(
            rows,
            "eloScore",
            "Elo",
            lambda t: f'Selecciones · {t.get("country","")}',
            lambda t: f'{trophy_label(t.get("worldCups",0), t.get("continentalTitles",0))}. {t.get("note","")}',
            score_b_key="elo",
            score_b_label="Rating",
        )

    def dynasty_meta(t):
        return f'{t.get("era","")} · {t.get("weeksNo1",0)} semanas #1/Elo · pico {t.get("peakElo",0)}'

    def dynasty_note(t):
        return f'{trophy_label(t.get("worldCups",0), t.get("continentalTitles",0))}. {t.get("note","")}'

    def contender_meta(t):
        return f'Ciclo {t.get("cycleYears",0)} años · {t.get("country","")}'

    def contender_note(t):
        return (f'{trophy_label(t.get("currentWorldCups",0), t.get("currentContinentalTitles",0))} · '
                f'{t.get("recentFinals",0)} finales recientes. {t.get("note","")}')

    return (
        f'<div style="margin-top:32px"></div>'
        + sport_header("Fútbol", "Selecciones", d.get("UPDATED",""), title="Fútbol de Selecciones")
        + section("Football Elo",
                  "Top 10 selecciones — Ranking Elo",
                  f'Snapshot Hermes basado en ratings tipo World Football Elo / MoreElo. Fuente: {d.get("SOURCE",{}).get("name","Elo snapshot")}.',
                  elo_rows(teams))
        + section("Road to Glory · Actual",
                  "Top 10 selecciones con potencial dinástico",
                  f"Quién puede meterse en el top 10 de dinastías. Umbral bruto estimado: {raw_threshold}. Score: Elo actual + años de ciclo + títulos recientes + finales + curva generacional.",
                  player_list_html(contenders, "dynastyPotential", "Potencial",
                                   contender_meta, contender_note, 100,
                                   score_b_key="elo", score_b_label="Elo"))
        + section("Road to Glory",
                  "Top 10 dinastías de selecciones",
                  f"Umbral top 10: {threshold}. Score: años #1/Elo + Mundiales + títulos continentales + pico Elo.",
                  team_list_html(dynasties, "dynastyScore", "Dynasty",
                                 dynasty_meta, dynasty_note, threshold))
    )


# ── Assemble ──────────────────────────────────────────────────────

def build_email(nhl: dict, nba: dict, mlb: dict,
                nfl: dict | None = None, f1: dict | None = None,
                motogp: dict | None = None, afl: dict | None = None,
                tennis: dict | None = None, cycling: dict | None = None,
                sumo: dict | None = None, rugby: dict | None = None,
                golf: dict | None = None, football: dict | None = None) -> str:
    today = date.today().strftime("%-d de %B de %Y")
    body  = (
        nhl_html(nhl)
        + (nba_html(nba)       if nba     else "")
        + (mlb_html(mlb)       if mlb     else "")
        + (nfl_html(nfl)       if nfl     else "")
        + (f1_html(f1)         if f1      else "")
        + (motogp_html(motogp) if motogp  else "")
        + (afl_html(afl)       if afl     else "")
        + (tennis_html(tennis) if tennis  else "")
        + (cycling_html(cycling) if cycling else "")
        + (sumo_html(sumo)     if sumo    else "")
        + (golf_html(golf)      if golf    else "")
        + (rugby_html(rugby)    if rugby   else "")
        + (football_html(football) if football else "")
    )
    footer = (
        f'<div style="background:{PAPER};border-top:1px solid {RULE};padding:18px 28px;'
        f'font-size:10px;color:{MUTED};font-family:{MONO};letter-spacing:.04em">'
        f'Hermes Newsletter &nbsp;·&nbsp; {today} &nbsp;·&nbsp; '
        f'NHL · NBA · MLB · NFL · F1 · MotoGP · AFL · Tennis · Cycling · Sumo · Golf · Rugby · Fútbol'
        f'</div>'
    )
    return (
        f'<!doctype html><html lang="es"><head>'
        f'<meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600;6..72,700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">'
        f'<title>Hermes Newsletter</title>'
        f'</head>'
        f'<body style="margin:0;padding:0;background:{BG};'
        f'font-family:{SANS};font-size:14px;color:{INK};line-height:1.45">'
        f'<div style="max-width:1040px;margin:0 auto;background:{PAPER}">'
        f'{body}{footer}'
        f'</div>'
        f'</body></html>'
    )


# ── Main ──────────────────────────────────────────────────────────

ALL_UPDATES = [
    ("NHL",     "update_data.py"),
    ("NBA",     "update_nba_data.py"),
    ("MLB",     "update_mlb_data.py"),
    ("NFL",     "update_nfl_data.py"),
    ("Tennis",  "update_tennis_data.py"),
    ("Cycling", "update_cycling_data.py"),
    ("Sumo",    "update_sumo_data.py"),
    ("F1",      "update_f1_data.py"),
    ("AFL",     "update_afl_data.py"),
    ("Golf",    "update_golf_data.py"),
    ("MotoGP",  "update_motogp_data.py"),
    ("Rugby",   "update_rugby_data.py"),
    ("Football", "update_football_data.py"),
]


def main() -> int:
    load_env()

    skip_updates = os.environ.get("HERMES_SKIP_UPDATES", "").strip().lower()
    if skip_updates in {"1", "true", "yes"}:
        print("HERMES_SKIP_UPDATES=1: usando los datos ya generados.")
    else:
        for sport, script in ALL_UPDATES:
            path = ROOT / "scripts" / script
            if path.exists():
                print(f"Actualizando {sport}…")
                try:
                    subprocess.run([sys.executable, str(path)], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"[WARN] {sport} update failed: {e}", file=sys.stderr)
            else:
                print(f"[SKIP] {script} not found", file=sys.stderr)

    password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if not password:
        print(
            "Datos actualizados. GMAIL_APP_PASSWORD no configurado — newsletter no enviada.\n"
            "  Añade esta línea a .env:\n"
            "  GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxxxxxx",
            file=sys.stderr,
        )
        return 0

    nhl     = load_js_data(ROOT / "data.js")
    nba     = load_js_data(ROOT / "nba_data.js")
    mlb     = load_js_data(ROOT / "mlb_data.js")
    nfl     = load_js_data(ROOT / "nfl_data.js")
    f1      = load_js_data(ROOT / "f1_data.js")
    motogp  = load_js_data(ROOT / "motogp_data.js")
    afl     = load_js_data(ROOT / "afl_data.js")
    tennis  = load_js_data(ROOT / "tennis_data.js")
    cycling = load_js_data(ROOT / "cycling_data.js")
    sumo    = load_js_data(ROOT / "sumo_data.js")
    golf    = load_js_data(ROOT / "golf_data.js")
    rugby   = load_js_data(ROOT / "rugby_data.js")
    football = load_js_data(ROOT / "football_data.js")

    if not nhl:
        print("Error: data.js vacío.", file=sys.stderr)
        return 1

    html    = build_email(nhl, nba, mlb, nfl, f1, motogp, afl, tennis, cycling, sumo, rugby, golf, football)
    today   = date.today().strftime("%d %b %Y")
    subject = f"Hermes Newsletter · {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html, "html", "utf-8"))

    print(f"Enviando a {RECIPIENT}…")
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(SENDER, password)
        smtp.sendmail(SENDER, RECIPIENT, msg.as_string())

    print(f"Newsletter enviada · {subject}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
