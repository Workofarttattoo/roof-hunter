#!/usr/bin/env python3
"""Backfill lead_verification_media for all contacts (batch). Safe to re-run."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))

from lead_verification_media import (  # noqa: E402
    build_media_items_for_lead,
    ensure_lead_verification_media_table,
    replace_media_for_contact,
)
from verification_yolo_pipeline import run_contact_verification_pipeline  # noqa: E402

DEFAULT_DB = _REPO / "leads_manifests" / "authoritative_storms.db"
TRAINING = _REPO / "training_data"
VER_CHIPS = _REPO / "verification_chips"


def main() -> None:
    ap = argparse.ArgumentParser(description="Populate lead_verification_media rows")
    ap.add_argument("--db", default=os.getenv("ROOF_HUNTER_DB_PATH", str(DEFAULT_DB)))
    ap.add_argument("--training-dir", default=os.getenv("ROOF_HUNTER_TRAINING_DIR", str(TRAINING)))
    ap.add_argument(
        "--verification-chips-dir",
        default=os.getenv("ROOF_HUNTER_VERIFICATION_CHIPS", str(VER_CHIPS)),
    )
    ap.add_argument(
        "--multi-source-verify",
        action="store_true",
        help="Fetch multi-source chip + YOLO for a single contact (requires --contact-id)",
    )
    ap.add_argument("--contact-id", type=int, default=None, help="With --multi-source-verify only")
    args = ap.parse_args()

    if args.multi_source_verify:
        if args.contact_id is None:
            ap.error("--multi-source-verify requires --contact-id")
        conn = sqlite3.connect(args.db, timeout=120)
        conn.row_factory = sqlite3.Row
        ensure_lead_verification_media_table(conn)
        row = conn.execute(
            "SELECT c.id, s.latitude, s.longitude FROM contacts c "
            "JOIN storms s ON c.event_id = s.id WHERE c.id = ?",
            (args.contact_id,),
        ).fetchone()
        if row is None:
            raise SystemExit(f"contact_id {args.contact_id} not found or missing storm coordinates")
        out = run_contact_verification_pipeline(
            conn=conn,
            contact_id=args.contact_id,
            lat=float(row["latitude"]),
            lon=float(row["longitude"]),
            training_dir=Path(args.training_dir),
            verification_chips_dir=Path(args.verification_chips_dir),
        )
        conn.close()
        print(json.dumps(out, indent=2, default=str))
        if not out.get("imagery"):
            raise SystemExit(3)
        return

    conn = sqlite3.connect(args.db, timeout=120)
    conn.row_factory = sqlite3.Row
    ensure_lead_verification_media_table(conn)
    cur = conn.execute(
        """
        SELECT c.id AS cid, c.damage_score, c.proof_msg, c.image_findings, c.zip_code,
               s.magnitude, s.event_date, s.state, s.city, s.latitude, s.longitude
        FROM contacts c
        JOIN storms s ON c.event_id = s.id
        """
    )
    n = 0
    while True:
        chunk = cur.fetchmany(2000)
        if not chunk:
            break
        for row in chunk:
            cid = row["cid"]
            built = build_media_items_for_lead(
                contact_id=cid,
                damage_score=float(row["damage_score"] or 0),
                magnitude=float(row["magnitude"] or 0),
                event_date=row["event_date"],
                state=row["state"],
                city=row["city"],
                zip_code=row["zip_code"],
                latitude=float(row["latitude"]) if row["latitude"] is not None else None,
                longitude=float(row["longitude"]) if row["longitude"] is not None else None,
                proof_msg=row["proof_msg"],
                image_findings=row["image_findings"],
                training_dir=str(args.training_dir),
            )
            replace_media_for_contact(conn, cid, built)
            n += 1
            if n % 5000 == 0:
                print(f"Processed {n} contacts...", flush=True)
    conn.close()
    print(f"Done. Updated verification media for {n} contacts.")


if __name__ == "__main__":
    main()
