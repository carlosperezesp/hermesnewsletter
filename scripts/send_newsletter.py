#!/usr/bin/env python3
"""
Send the sports newsletter as an HTML email via Gmail SMTP.

Required environment variables:
  GMAIL_USER            – Gmail address used to send (e.g. carlosrealmurcia@gmail.com)
  GMAIL_APP_PASSWORD    – Gmail App Password (not your account password)
  NEWSLETTER_RECIPIENTS – Comma-separated list of recipient emails

If GMAIL_APP_PASSWORD is not set the script exits 0 silently (used in CI
so the workflow step doesn't fail when the secret is absent).
"""

from __future__ import annotations

import json
import os
import re
import smtplib
import sys
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPORTS_DATA_JS = ROOT / "sports-data.js"

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_sports_data() -> dict:
    """Extract the JSON payload from sports-data.js."""
    text = SPORTS_DATA_JS.read_text(encoding="utf-8")
    m = re.search(r"window\.SPORTS_DATA\s*=\s*(\{.*\})\s*;", text, re.DOTALL)
    if not m:
        raise ValueError("Could not find window.SPORTS_DATA in sports-data.js")
    return json.loads(m.group(1))


def score_color(score: float) -> str:
    if score >= 90:
        return "#1a7f37"
    if score >= 70:
        return "#2e7d32"
    if score >= 50:
        return "#6a8f3a"
    return "#c84c29"


def score_bar(score: float) -> str:
    color = score_color(score)
    pct = max(0, min(100, score))
    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px;font-size:.84rem">'
        f'<span style="display:inline-block;width:64px;height:7px;border-radius:999px;'
        f'background:#f1eeea;overflow:hidden;flex-shrink:0">'
        f'<span style="display:block;height:100%;width:{pct}%;background:{color};'
        f'border-radius:999px"></span></span>'
        f'<span style="font-weight:600;min-width:28px;text-align:right">{score}</span>'
        f'</span>'
    )


# ── Section renderers ─────────────────────────────────────────────────────────

def render_standings(league: dict) -> str:
    rows = ""
    for t in league["standings"][:10]:
        dot = (
            f'<span style="display:inline-block;width:11px;height:11px;border-radius:50%;'
            f'background:{t["color"]};margin-right:8px;vertical-align:middle"></span>'
        )
        rows += (
            f'<tr>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #e2dcd4;color:#6a5c4f;'
            f'font-size:.85rem;width:32px">{t["rank"]}</td>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #e2dcd4">'
            f'{dot}{t["team"]}</td>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #e2dcd4;font-size:.9rem">'
            f'{t["record"]}</td>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #e2dcd4;text-align:right;'
            f'font-size:.9rem">{t["points"]}</td>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #e2dcd4">'
            f'{score_bar(t["score"])}</td>'
            f'</tr>'
        )
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border-collapse:collapse;font-family:Inter,system-ui,sans-serif">
      <thead>
        <tr style="background:#f1eeea">
          <th style="padding:8px 12px;text-align:left;font-size:.75rem;letter-spacing:.08em;
                     text-transform:uppercase;color:#6a5c4f;font-weight:600">#</th>
          <th style="padding:8px 12px;text-align:left;font-size:.75rem;letter-spacing:.08em;
                     text-transform:uppercase;color:#6a5c4f;font-weight:600">Equipo</th>
          <th style="padding:8px 12px;text-align:left;font-size:.75rem;letter-spacing:.08em;
                     text-transform:uppercase;color:#6a5c4f;font-weight:600">Récord</th>
          <th style="padding:8px 12px;text-align:right;font-size:.75rem;letter-spacing:.08em;
                     text-transform:uppercase;color:#6a5c4f;font-weight:600">V</th>
          <th style="padding:8px 12px;text-align:left;font-size:.75rem;letter-spacing:.08em;
                     text-transform:uppercase;color:#6a5c4f;font-weight:600">Score</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


def render_top_players(players: list[dict], title: str, note: str = "") -> str:
    rows = ""
    for p in players[:10]:
        rows += (
            f'<tr>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #e2dcd4;color:#6a5c4f;'
            f'font-size:.85rem;width:32px">{p["rank"]}</td>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #e2dcd4">'
            f'<strong style="font-size:.93rem">{p["name"]}</strong>'
            f'<span style="display:block;color:#6a5c4f;font-size:.82rem;margin-top:2px">'
            f'{p["team"]} · {p["pos"]} · {p["age"]} años</span></td>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #e2dcd4">'
            f'{score_bar(p["score"])}</td>'
            f'</tr>'
        )
    note_html = (
        f'<p style="margin:6px 0 0;color:#6a5c4f;font-size:.82rem">{note}</p>'
        if note else ""
    )
    return f"""
    <div style="margin-bottom:4px">
      <strong style="font-size:.95rem">{title}</strong>{note_html}
    </div>
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border-collapse:collapse;font-family:Inter,system-ui,sans-serif">
      <thead>
        <tr style="background:#f1eeea">
          <th style="padding:8px 12px;text-align:left;font-size:.75rem;letter-spacing:.08em;
                     text-transform:uppercase;color:#6a5c4f;font-weight:600">#</th>
          <th style="padding:8px 12px;text-align:left;font-size:.75rem;letter-spacing:.08em;
                     text-transform:uppercase;color:#6a5c4f;font-weight:600">Jugador</th>
          <th style="padding:8px 12px;text-align:left;font-size:.75rem;letter-spacing:.08em;
                     text-transform:uppercase;color:#6a5c4f;font-weight:600">Score</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


def render_bracket_series(s: dict) -> str:
    t1 = s["team1"]
    t2 = s["team2"]
    t1_color = t1.get("color", "#888")
    t2_color = t2.get("color", "#888")
    t1_leads = t1["wins"] > t2["wins"]
    t2_leads = t2["wins"] > t1["wins"]
    summary = s.get("summary", "")

    games_html = ""
    next_found = False
    for g in (s.get("games") or []):
        if g.get("isNecessary") and not g.get("completed"):
            result = "si nec."
            icon = ""
            bg = ""
        elif g.get("completed"):
            result = f'{g.get("awayScore","?")}–{g.get("homeScore","?")}'
            icon = "✓ "
            bg = ""
        else:
            is_next = not next_found
            if is_next:
                next_found = True
                bg = "background:rgba(200,76,41,.04);"
                icon = "▶ "
            else:
                bg = ""
                icon = ""
            result = "—"
        games_html += (
            f'<tr style="{bg}">'
            f'<td style="padding:6px 12px;border-bottom:1px solid #e2dcd4;font-size:.75rem;'
            f'color:#6a5c4f;font-weight:700">G{g.get("num","")}</td>'
            f'<td style="padding:6px 12px;border-bottom:1px solid #e2dcd4;font-size:.78rem;'
            f'color:#6a5c4f;white-space:nowrap">{g.get("date","")}</td>'
            f'<td style="padding:6px 12px;border-bottom:1px solid #e2dcd4;font-size:.84rem;'
            f'font-weight:600">{icon}{g.get("away","")} @ {g.get("home","")}</td>'
            f'<td style="padding:6px 12px;border-bottom:1px solid #e2dcd4;font-size:.82rem;'
            f'color:#6a5c4f;text-align:right;white-space:nowrap">{result}</td>'
            f'</tr>'
        )

    wins1_style = "font-size:1.3rem;font-weight:800;" + ("color:#6a5c4f;" if t2_leads else "")
    wins2_style = "font-size:1.3rem;font-weight:800;" + ("color:#6a5c4f;" if t1_leads else "")

    return f"""
    <div style="border:1px solid #e2dcd4;border-radius:10px;overflow:hidden;
                margin-bottom:14px;font-family:Inter,system-ui,sans-serif">
      <div style="display:flex;align-items:center;justify-content:space-between;
                  padding:10px 14px;background:#f1eeea;border-bottom:1px solid #e2dcd4">
        <div style="display:flex;align-items:center;gap:7px">
          <span style="width:10px;height:10px;border-radius:50%;background:{t1_color};
                       display:inline-block"></span>
          <strong>{t1["abbr"]}</strong>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
          <span style="{wins1_style}">{t1["wins"]}</span>
          <span style="color:#e2dcd4;font-weight:300;font-size:1.1rem">–</span>
          <span style="{wins2_style}">{t2["wins"]}</span>
        </div>
        <div style="display:flex;align-items:center;gap:7px;flex-direction:row-reverse">
          <span style="width:10px;height:10px;border-radius:50%;background:{t2_color};
                       display:inline-block"></span>
          <strong>{t2["abbr"]}</strong>
        </div>
      </div>
      {f'<div style="font-size:.75rem;color:#6a5c4f;padding:5px 14px;background:#f1eeea;border-bottom:1px solid #e2dcd4">{summary}</div>' if summary else ""}
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse">{games_html}</table>
    </div>"""


def render_bracket(league: dict) -> str:
    cr = (league.get("bracket") or {}).get("currentRound")
    if not cr or not cr.get("series"):
        return ""
    east = [s for s in cr["series"] if s.get("conference") == "East"]
    west = [s for s in cr["series"] if s.get("conference") == "West"]
    other = [s for s in cr["series"] if s.get("conference") not in ("East", "West")]

    def conf_block(title: str, series_list: list) -> str:
        cards = "".join(render_bracket_series(s) for s in series_list)
        return f"""
        <td style="width:50%;vertical-align:top;padding:0 10px 0 0">
          <div style="font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;
                      color:#c84c29;font-weight:700;margin-bottom:10px;padding-bottom:7px;
                      border-bottom:2px solid #c84c29">{title}</div>
          {cards}
        </td>"""

    if east or west:
        body = (
            f'<table width="100%" cellpadding="0" cellspacing="0">'
            f'<tr>'
            f'{conf_block("Conferencia Este", east) if east else ""}'
            f'{conf_block("Conferencia Oeste", west) if west else ""}'
            f'</tr></table>'
        )
    else:
        body = "".join(render_bracket_series(s) for s in other)

    return f"""
    <div style="margin-bottom:6px">
      <strong style="font-size:.95rem">{cr["name"]}
        <span style="font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;
                     font-weight:700;background:#fff3cd;color:#856404;border:1px solid #ffc107;
                     padding:2px 8px;border-radius:999px;margin-left:6px">Playoffs</span>
      </strong>
    </div>
    {body}"""


# ── Email assembly ────────────────────────────────────────────────────────────

CARD_STYLE = (
    "background:#ffffff;border:1px solid #e2dcd4;border-radius:14px;"
    "box-shadow:0 4px 16px rgba(47,35,26,.07);overflow:hidden;margin-bottom:20px"
)
HEAD_STYLE = (
    "padding:14px 18px;border-bottom:1px solid #e2dcd4"
)


def card(head_html: str, body_html: str) -> str:
    return (
        f'<div style="{CARD_STYLE}">'
        f'<div style="{HEAD_STYLE}">{head_html}</div>'
        f'<div>{body_html}</div>'
        f'</div>'
    )


def render_league(league: dict) -> str:
    name = league["name"]
    season = league["season"]
    status = league.get("status", "")
    is_playoffs = status and "playoff" in status.lower()

    playoff_badge = (
        '<span style="font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;'
        'font-weight:700;background:#fff3cd;color:#856404;border:1px solid #ffc107;'
        'padding:2px 8px;border-radius:999px;margin-left:8px">Playoffs</span>'
        if is_playoffs else ""
    )

    sections: list[str] = []

    # Standings
    if league.get("standings"):
        sections.append(card(
            f'<strong style="font-size:.95rem">Clasificación{playoff_badge}</strong>'
            f'<p style="margin:5px 0 0;color:#6a5c4f;font-size:.82rem">'
            f'Top 10 equipos · {season}</p>',
            render_standings(league),
        ))

    # Bracket (playoffs only)
    if is_playoffs and league.get("bracket"):
        bracket_html = render_bracket(league)
        if bracket_html:
            sections.append(card(
                f'<strong style="font-size:.95rem">Bracket de playoffs</strong>',
                f'<div style="padding:16px">{bracket_html}</div>',
            ))

    # Top Season
    if league.get("topSeason"):
        sections.append(card(
            f'<strong style="font-size:.95rem">Top 10 Temporada</strong>'
            f'<p style="margin:5px 0 0;color:#6a5c4f;font-size:.82rem">'
            f'Score compuesto ponderado por categorías líderes</p>',
            render_top_players(
                league["topSeason"],
                "",
            ),
        ))

    # Top Career
    if league.get("topCareer"):
        sections.append(card(
            f'<strong style="font-size:.95rem">Top 10 Carrera</strong>'
            f'<p style="margin:5px 0 0;color:#6a5c4f;font-size:.82rem">'
            f'80% temporada + 20% bonus experiencia</p>',
            render_top_players(league["topCareer"], ""),
        ))

    # Road to Glory
    rtg = league.get("roadToGlory") or {}
    normal = rtg.get("normal") or []
    young = rtg.get("young") or []
    if normal or young:
        rtg_body = '<div style="padding:0">'
        if normal:
            rows = render_top_players(normal[:5], "")
            rtg_body += (
                f'<div style="padding:14px 0 6px 18px">'
                f'<span style="font-size:.8rem;font-weight:700;letter-spacing:.06em;'
                f'text-transform:uppercase;color:#6a5c4f">Establecidos (25–30 años)</span>'
                f'</div>{rows}'
            )
        if young:
            rows = render_top_players(young[:5], "")
            rtg_body += (
                f'<div style="padding:14px 0 6px 18px;border-top:1px solid #e2dcd4">'
                f'<span style="font-size:.8rem;font-weight:700;letter-spacing:.06em;'
                f'text-transform:uppercase;color:#6a5c4f">Promesas jóvenes (≤24 años)</span>'
                f'</div>{rows}'
            )
        rtg_body += '</div>'
        sections.append(card(
            '<strong style="font-size:.95rem">Road to Glory</strong>'
            '<p style="margin:5px 0 0;color:#6a5c4f;font-size:.82rem">'
            'Jugadores en ascenso</p>',
            rtg_body,
        ))

    divider = (
        '<hr style="border:none;border-top:2px solid #e2dcd4;margin:32px 0">'
    )
    return (
        f'<div style="margin-bottom:40px">'
        f'<div style="margin-bottom:18px">'
        f'<span style="font-family:monospace;font-size:.75rem;letter-spacing:.14em;'
        f'text-transform:uppercase;color:#c84c29;font-weight:700">{name}</span>'
        f'<h2 style="margin:4px 0 0;font-size:1.6rem;font-weight:700">'
        f'{name} {season}{playoff_badge}</h2>'
        f'<p style="margin:4px 0 0;color:#6a5c4f;font-size:.9rem">{status}</p>'
        f'</div>'
        + "".join(sections)
        + f'</div>{divider}'
    )


def build_email_html(data: dict) -> str:
    today = data.get("lastUpdated", date.today().strftime("%-d %b %Y"))
    leagues_html = "".join(render_league(lg) for lg in data.get("leagues", []))

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Sports Newsletter – {today}</title>
</head>
<body style="margin:0;padding:0;background:#f6f4ef;
             font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,sans-serif;
             color:#1f1a16;line-height:1.5">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f6f4ef">
    <tr><td align="center" style="padding:32px 16px 48px">
      <table width="100%" style="max-width:680px" cellpadding="0" cellspacing="0">

        <!-- Header -->
        <tr><td style="padding-bottom:28px">
          <div style="display:inline-block;padding:6px 12px;border-radius:999px;
                      background:#ffffff;border:1px solid #e2dcd4;font-size:.75rem;
                      letter-spacing:.08em;text-transform:uppercase;color:#6a5c4f;
                      margin-bottom:12px">Sports Newsletter</div>
          <h1 style="margin:0 0 8px;font-size:2rem;font-weight:700;line-height:1.2">
            Resumen estadístico:<br>MLB · NBA · NHL · NFL</h1>
          <p style="margin:0;color:#6a5c4f">
            Clasificaciones, top jugadores y Road to Glory.</p>
          <p style="margin:8px 0 0;font-size:.88rem;color:#6a5c4f">
            Actualizado: <strong style="color:#1f1a16">{today}</strong> ·
            Datos vía ESPN API</p>
        </td></tr>

        <!-- Leagues -->
        <tr><td>
          {leagues_html}
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding-top:8px;font-size:.82rem;color:#6a5c4f;line-height:1.7">
          <p>Los scores son normalizados 0–100. Score carrera = 80% temporada +
          20% bonus experiencia. Score temporada = composite ponderado.</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── Send ──────────────────────────────────────────────────────────────────────

def send(html: str, subject: str, gmail_user: str, app_password: str,
         recipients: list[str]) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_user, app_password)
        smtp.sendmail(gmail_user, recipients, msg.as_string())
    print(f"Newsletter sent to: {', '.join(recipients)}")


def main() -> int:
    gmail_user = os.environ.get("GMAIL_USER", "").strip()
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    recipients_raw = os.environ.get("NEWSLETTER_RECIPIENTS", "").strip()

    if not app_password:
        print("GMAIL_APP_PASSWORD not set — skipping newsletter send.", file=sys.stderr)
        return 0  # silent skip, not an error

    if not gmail_user:
        print("ERROR: GMAIL_USER not set.", file=sys.stderr)
        return 1

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    if not recipients:
        # Default: send to the sender themselves
        recipients = [gmail_user]

    if not SPORTS_DATA_JS.exists():
        print(f"ERROR: {SPORTS_DATA_JS} not found. Run update_sports_data.py first.",
              file=sys.stderr)
        return 1

    data = load_sports_data()
    today = data.get("lastUpdated", date.today().strftime("%-d %b %Y"))
    subject = f"Sports Newsletter – {today}"
    html = build_email_html(data)

    send(html, subject, gmail_user, app_password, recipients)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
