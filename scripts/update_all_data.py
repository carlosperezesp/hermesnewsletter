#!/usr/bin/env python3
"""Update all sport data files (NHL, NBA, MLB, NFL). No email dependency."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

UPDATES = [
    ("NHL",    SCRIPTS / "update_data.py"),
    ("NBA",    SCRIPTS / "update_nba_data.py"),
    ("MLB",    SCRIPTS / "update_mlb_data.py"),
    ("NFL",    SCRIPTS / "update_nfl_data.py"),
    ("Tennis",  SCRIPTS / "update_tennis_data.py"),
    ("Cycling", SCRIPTS / "update_cycling_data.py"),
    ("Sumo",    SCRIPTS / "update_sumo_data.py"),
    ("F1",      SCRIPTS / "update_f1_data.py"),
    ("AFL",     SCRIPTS / "update_afl_data.py"),
    ("MotoGP",  SCRIPTS / "update_motogp_data.py"),
    ("Rugby",   SCRIPTS / "update_rugby_data.py"),
]


def main() -> int:
    errors = []
    for sport, script in UPDATES:
        print(f"Actualizando {sport}…")
        try:
            subprocess.run([sys.executable, str(script)], check=True)
        except subprocess.CalledProcessError as exc:
            print(f"  ✗ {sport} falló (código {exc.returncode})", file=sys.stderr)
            errors.append(sport)
    if errors:
        print(f"Errores en: {', '.join(errors)}", file=sys.stderr)
        return 1
    print("Todos los datos actualizados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
