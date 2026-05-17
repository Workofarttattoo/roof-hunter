#!/usr/bin/env python3
"""
Smoke: multi-source verification chip + RoofDeepLens over a fixed OAM-heavy bbox.

Uses Kathmandu sample tile (public OAM UAV thumbnail) so the run succeeds without Google keys.

Expected (success):
  exit 0
  log line contains: [info] verification imagery: winning_source=oam_
  JSON printed with yolo.backend heuristic or yolo

If ultralytics missing, yolo.backend is still ``heuristic`` (opencv path in yolo_detector).

Run from repo root::

  python scripts/smoke_verification_imagery.py
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, default=27.6902, help="Default: OAM Dallu sample")
    p.add_argument("--lon", type=float, default=85.3352, help="Default: OAM Dallu sample")
    args = p.parse_args()

    script = _REPO / "scripts" / "verify_lead_imagery.py"
    cmd = [
        sys.executable,
        str(script),
        "--lat",
        str(args.lat),
        "--lon",
        str(args.lon),
        "--preview-out-dir",
        str(_REPO / "verification_chips" / "smoke"),
    ]
    print("[info] running:", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(_REPO))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
