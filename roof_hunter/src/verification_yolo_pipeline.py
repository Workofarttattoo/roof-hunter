"""
End-to-end verification chip fetch + RoofDeepLens scoring + DB/media updates.
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from lead_verification_media import (
    VERIFICATION_YOLO_ROLE,
    apply_verification_yolo_chip,
    ensure_lead_verification_media_table,
)
from verification_image_sources import (
    append_image_findings_verification,
    append_proof_msg_verification_line,
    fetch_best_verification_image,
)

logger = logging.getLogger(__name__)


def run_contact_verification_pipeline(
    *,
    conn: sqlite3.Connection,
    contact_id: int,
    lat: float,
    lon: float,
    training_dir: Path,
    verification_chips_dir: Path,
    zoom: int = 20,
    size_px: int = 640,
    update_contact_text: bool = True,
) -> dict[str, Any]:
    """
    Fetch multi-source chip, run YOLO/heuristic, prepend media row, append proof markers.
    Copies the saved chip into ``training_dir`` / ``verification_chips`` for ``/images`` static serve.
    """
    ensure_lead_verification_media_table(conn)
    training_dir = Path(training_dir)
    training_sub = training_dir / "verification_chips"
    training_sub.mkdir(parents=True, exist_ok=True)
    verification_chips_dir = Path(verification_chips_dir)
    verification_chips_dir.mkdir(parents=True, exist_ok=True)
    staging = verification_chips_dir / f"vchip_{contact_id}_{lat:.4f}_{lon:.4f}_staging.png"

    result = fetch_best_verification_image(lat, lon, out_path=staging, zoom=zoom, size_px=size_px)
    out: dict[str, Any] = {
        "contact_id": contact_id,
        "lat": lat,
        "lon": lon,
        "imagery": None,
        "yolo": None,
    }
    if not result:
        logger.warning("[info] verification pipeline: no imagery for contact_id=%s", contact_id)
        return out

    suffix = (result.path.suffix or ".png").lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
        suffix = ".png"
    rel_name = f"verification_chips/vchip_{contact_id}_{lat:.4f}_{lon:.4f}{suffix}"
    final_train = training_dir / rel_name
    shutil.copyfile(result.path, final_train)
    out["imagery"] = {
        "source_id": result.source_id,
        "source_url": result.source_url,
        "license_note": result.license_note,
        "path": str(final_train),
        "public_path": f"/images/{rel_name}",
    }

    from yolo_detector import RoofDeepLens  # lazy: ultralytics optional

    yolo = RoofDeepLens().detect_and_quantify(final_train)
    out["yolo"] = yolo

    cur = conn.execute(
        """
        SELECT c.*
        FROM contacts c
        WHERE c.id = ?
        """,
        (contact_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"contact_id {contact_id} not found")
    storm = conn.execute(
        "SELECT magnitude, event_date, state, city, latitude, longitude FROM storms WHERE id = ?",
        (row["event_id"],),
    ).fetchone()
    if storm is None:
        raise ValueError(f"storm missing for contact {contact_id}")

    proof_payload = {
        "source": result.source_id,
        "image_path": out["imagery"]["public_path"],
        "abs_path": str(final_train),
        "yolo_backend": yolo.get("backend"),
        "damage_percent": yolo.get("damage_percent"),
        "confidence_score": yolo.get("confidence_score"),
    }
    chip_item = {
        "image_path": out["imagery"]["public_path"],
        "role": VERIFICATION_YOLO_ROLE,
        "sort_order": 0,
        "rationale": (
            f"Verification chip from {result.source_id} at ({lat:.5f},{lon:.5f}); "
            f"model={yolo.get('backend')} damage≈{yolo.get('damage_percent')}%. {result.license_note}"
        )[:1200],
        "call_hook": (
            f"Mention on-site validation: automated score {yolo.get('damage_percent')}% "
            f"via {yolo.get('backend')} on fresh imagery."
        )[:800],
    }

    apply_verification_yolo_chip(
        conn,
        contact_id=contact_id,
        chip_item=chip_item,
        training_dir=str(training_dir),
        contact_row=row,
        storm_row=storm,
    )

    if update_contact_text:
        new_pm = append_proof_msg_verification_line(
            row["proof_msg"] if "proof_msg" in row.keys() else None,
            proof_payload,
        )
        nar = (
            "VERIFY_YOLO ["
            f"{result.source_id}] {json.dumps({k: proof_payload[k] for k in ('damage_percent', 'confidence_score', 'yolo_backend')})}"
        )
        new_if = append_image_findings_verification(
            row["image_findings"] if "image_findings" in row.keys() else None,
            nar,
        )
        conn.execute(
            "UPDATE contacts SET proof_msg = ?, image_findings = ? WHERE id = ?",
            (new_pm, new_if, contact_id),
        )
        conn.commit()

    try:
        result.path.unlink(missing_ok=True)
    except OSError:
        pass

    return out
