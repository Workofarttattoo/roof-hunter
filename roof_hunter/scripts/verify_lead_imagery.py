#!/usr/bin/env python3
"""Fetch verification imagery (multi-provider) and run RoofDeepLens; optional DB update."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from verification_image_sources import fetch_best_verification_image  # noqa: E402
from verification_yolo_pipeline import run_contact_verification_pipeline  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_DB = _REPO / "leads_manifests" / "authoritative_storms.db"
TRAINING = _REPO / "training_data"
VER_CHIPS = _REPO / "verification_chips"


def _preview_lat_lon(
    lat: float,
    lon: float,
    out_dir: Path,
    *,
    zoom: int,
    size_px: int,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"vchip_preview_{lat:.4f}_{lon:.4f}.png"
    res = fetch_best_verification_image(lat, lon, out_path=dest, zoom=zoom, size_px=size_px)
    if not res:
        logger.error("[info] verification: no imagery for preview (%s, %s)", lat, lon)
        return 2
    from yolo_detector import RoofDeepLens  # noqa: WPS433

    yolo = RoofDeepLens().detect_and_quantify(res.path)
    summary = {"imagery_source": res.source_id, "image_path": str(res.path), "yolo": yolo}
    print(json.dumps(summary, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Multi-source verification chip + RoofDeepLens")
    p.add_argument("--contact-id", type=int, default=None, help="Contact row id (updates DB + media)")
    p.add_argument("--lat", type=float, default=None, help="Latitude (requires --lon; preview-only)")
    p.add_argument("--lon", type=float, help="Longitude (required with --lat)")
    p.add_argument("--db", default=os.getenv("ROOF_HUNTER_DB_PATH", str(DEFAULT_DB)))
    p.add_argument(
        "--training-dir",
        default=os.getenv("ROOF_HUNTER_TRAINING_DIR", str(TRAINING)),
        help="Static /images root (dashboard mount)",
    )
    p.add_argument(
        "--verification-chips-dir",
        default=os.getenv("ROOF_HUNTER_VERIFICATION_CHIPS", str(VER_CHIPS)),
        help="Staging directory before copy into training_dir",
    )
    p.add_argument("--zoom", type=int, default=20)
    p.add_argument("--size", type=int, default=640, dest="size_px")
    p.add_argument(
        "--preview-out-dir",
        default=str(VER_CHIPS),
        help="When using --lat/--lon without contact, write chip here",
    )
    p.add_argument("--no-update-contact-text", action="store_true", help="Skip proof_msg / image_findings")

    args = p.parse_args()

    if args.contact_id is None and args.lat is None:
        p.error("Provide --contact-id or both --lat and --lon")

    if args.lat is not None and args.lon is None:
        p.error("--lon is required with --lat")

    if args.contact_id is not None and args.lat is not None:
        p.error("Choose either --contact-id or --lat/--lon, not both")

    if args.lat is not None:
        assert args.lon is not None
        return _preview_lat_lon(
            args.lat,
            args.lon,
            Path(args.preview_out_dir),
            zoom=args.zoom,
            size_px=args.size_px,
        )

    if args.contact_id is not None:
        conn = sqlite3.connect(args.db, timeout=120)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT c.id, s.latitude, s.longitude FROM contacts c "
            "JOIN storms s ON c.event_id = s.id WHERE c.id = ?",
            (args.contact_id,),
        ).fetchone()
        if row is None:
            logger.error("contact_id %s not found or missing storm join", args.contact_id)
            return 1
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        out = run_contact_verification_pipeline(
            conn=conn,
            contact_id=args.contact_id,
            lat=lat,
            lon=lon,
            training_dir=Path(args.training_dir),
            verification_chips_dir=Path(args.verification_chips_dir),
            zoom=args.zoom,
            size_px=args.size_px,
            update_contact_text=not args.no_update_contact_text,
        )
        conn.close()
        print(json.dumps(out, indent=2, default=str))
        if not out.get("imagery"):
            return 3
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
