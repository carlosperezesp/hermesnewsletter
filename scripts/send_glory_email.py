#!/usr/bin/env python3
"""Envía un email de Gloria cuando hay novedades en el Glory log.

Lee glory_data.js (generado por update_glory.py) y manda un digest conciso
—informes de cierre y hechos de gloria— SOLO con lo que aún no se ha enviado.
Deduplica con un estado local (scripts/.glory_sent.json) usando los `id` estables
del log, así cada hecho se envía una sola vez. Sin IA: todo son plantillas.

Uso:
  python3 scripts/send_glory_email.py            # envía si hay novedades y hay password
  python3 scripts/send_glory_email.py --dry-run  # imprime el HTML, no envía ni marca
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
SENDER = "carlosrealmurcia@gmail.com"
RECIPIENT = "carlosrealmurcia@gmail.com"
SENT_STATE = ROOT / "scripts" / ".glory_sent.json"


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_glory() -> dict:
    f = ROOT / "glory_data.js"
    if not f.exists():
        return {}
    text = f.read_text(encoding="utf-8")
    m = re.search(r"window\.\w+\s*=\s*(\{.*\})\s*;", text, re.DOTALL)
    return json.loads(m.group(1)) if m else {}


def load_sent() -> set[str]:
    try:
        return set(json.loads(SENT_STATE.read_text(encoding="utf-8")))
    except Exception:
        return set()


def save_sent(ids: set[str]) -> None:
    SENT_STATE.write_text(json.dumps(sorted(ids), ensure_ascii=False, indent=0), encoding="utf-8")


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_html(reports: list[dict], events: list[dict]) -> str:
    today = date.today().strftime("%d %b %Y")
    parts = [
        '<div style="max-width:560px;margin:0 auto;font-family:Georgia,serif;color:#1a1714;">',
        f'<div style="font:11px monospace;letter-spacing:.18em;text-transform:uppercase;color:#888;">Hermes · {today}</div>',
        '<h1 style="font-size:30px;margin:6px 0 18px;">Gloria · lo último</h1>',
    ]
    for r in reports:
        rows = "".join(
            f'<tr><td style="color:#999;font:12px monospace;padding:2px 8px 2px 0;">{i+1}</td>'
            f'<td style="padding:2px 0;">{esc(p.get("name"))}</td>'
            f'<td style="text-align:right;font:12px monospace;color:#555;">{esc(p.get("sub") if p.get("sub") is not None else (p.get("score") if p.get("score") is not None else ""))}</td></tr>'
            for i, p in enumerate(r.get("top5", []))
        )
        parts.append(
            f'<div style="border:1px solid #1a1714;border-top:4px solid #1a1714;padding:14px 16px;margin:0 0 16px;">'
            f'<div style="font:10px monospace;letter-spacing:.16em;text-transform:uppercase;color:#888;">Informe de cierre · {esc(r.get("competition"))}</div>'
            f'<div style="font-size:18px;font-weight:bold;margin:6px 0 10px;">{esc(r.get("champion"))}</div>'
            f'<div style="font:10px monospace;letter-spacing:.1em;text-transform:uppercase;color:#999;margin-bottom:4px;">{esc(r.get("scopeLabel"))}</div>'
            f'<table style="width:100%;border-collapse:collapse;font-size:13px;">{rows}</table>'
            f'</div>'
        )
    if events:
        parts.append('<div style="font:10px monospace;letter-spacing:.16em;text-transform:uppercase;color:#888;margin:4px 0 8px;">Movimientos</div>')
        for e in events:
            parts.append(
                f'<div style="padding:6px 0;border-bottom:1px solid #eee;font-size:14px;">'
                f'<span style="font:10px monospace;text-transform:uppercase;color:#999;margin-right:8px;">{esc(e.get("detail"))}</span>'
                f'{esc(e.get("text"))}</div>'
            )
    parts.append('<div style="margin-top:20px;font:11px monospace;color:#aaa;">hermesnewsletter.vercel.app · automático, sin IA</div>')
    parts.append('</div>')
    return "".join(parts)


def build_text(reports: list[dict], events: list[dict]) -> str:
    lines = ["GLORIA · lo último", ""]
    for r in reports:
        lines.append(f"[{r.get('competition')}] {r.get('champion')}")
        for i, p in enumerate(r.get("top5", [])):
            extra = p.get("sub") if p.get("sub") is not None else p.get("score", "")
            lines.append(f"  {i+1}. {p.get('name')}  {extra}")
        lines.append("")
    if events:
        lines.append("Movimientos:")
        for e in events:
            lines.append(f"  · [{e.get('detail')}] {e.get('text')}")
    return "\n".join(lines)


def main() -> int:
    load_env()
    dry = "--dry-run" in sys.argv

    glory = load_glory()
    all_reports = glory.get("REPORTS", []) or []
    all_events = glory.get("EVENTS", []) or []

    sent = load_sent()
    new_reports = [r for r in all_reports if r.get("id") and r["id"] not in sent]
    new_events = [e for e in all_events if e.get("id") and e["id"] not in sent]

    if not new_reports and not new_events:
        print("Gloria: sin novedades, no se envía email.")
        return 0

    html = build_html(new_reports, new_events)
    text = build_text(new_reports, new_events)

    lead = new_reports[0]["champion"] if new_reports else new_events[0]["text"]
    extra = len(new_reports) + len(new_events) - 1
    subject = f"Hermes · Gloria: {lead}" + (f" (+{extra} más)" if extra > 0 else "")

    if dry:
        print(f"SUBJECT: {subject}\n")
        print(text)
        print(f"\n[dry-run] {len(new_reports)} informes + {len(new_events)} hechos nuevos. No enviado.")
        return 0

    password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if not password:
        print("GMAIL_APP_PASSWORD no configurado — email de Gloria no enviado.", file=sys.stderr)
        return 0

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER
    msg["To"] = RECIPIENT
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    print(f"Enviando Gloria a {RECIPIENT}…")
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(SENDER, password)
        smtp.sendmail(SENDER, RECIPIENT, msg.as_string())

    # Marcar como enviados; podar a los ids aún presentes en el log para acotar el estado.
    present = {x.get("id") for x in all_reports + all_events if x.get("id")}
    save_sent((sent | present))
    print(f"Gloria enviada · {subject}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
