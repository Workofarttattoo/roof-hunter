import os
import sqlite3
import logging
import shutil
from datetime import datetime, timezone
from dotenv import load_dotenv
from aws_discovery_worker import AWSDiscoveryWorker
from webhook_sync import send_lead_to_sheets

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, 'leads_manifests', 'authoritative_storms.db')
TRAINING_DIR = os.path.join(BASE_DIR, "training_data")
THREED_DIR = os.path.join(TRAINING_DIR, "models_3d")
ENABLE_HF_3D = os.getenv("ENABLE_HF_3D", "0").strip().lower() in {"1", "true", "yes", "on"}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _maybe_snapshot_previous_image(event_id: int) -> str | None:
    latest_path = os.path.join(TRAINING_DIR, f"hail_target_{event_id}.png")
    if not os.path.exists(latest_path):
        return None
    pre_dir = os.path.join(TRAINING_DIR, "pre_event_snapshots")
    os.makedirs(pre_dir, exist_ok=True)
    snap_path = os.path.join(pre_dir, f"hail_target_{event_id}_{_ts()}_before.png")
    shutil.copy2(latest_path, snap_path)
    return snap_path


def _run_advanced_forensics(
    *,
    event_id: int,
    post_image_path: str,
    pre_image_path: str | None,
) -> dict:
    out = {
        "height_drop_points": 0,
        "max_drop_meters": 0.0,
        "topology_probability": 0.0,
        "topology_status": "SKIPPED",
        "three_d_model_path": None,
    }

    # Optional 2D -> 3D stage using Hugging Face inference.
    if ENABLE_HF_3D and os.getenv("HF_TOKEN"):
        try:
            from weather_twin.integrations.hf_3d_visualizer import generate_3d_from_2d

            os.makedirs(THREED_DIR, exist_ok=True)
            model_path = os.path.join(THREED_DIR, f"hail_target_{event_id}_{_ts()}.glb")
            if generate_3d_from_2d(post_image_path, model_path):
                out["three_d_model_path"] = model_path
        except Exception as e:
            logger.warning("HF 3D stage failed for event %s: %s", event_id, e)

    # Structural delta stage (pre/post comparison) when we have both images.
    if pre_image_path and os.path.exists(pre_image_path):
        try:
            from topological_forensics import TopologicalForensics

            topo = TopologicalForensics()
            topo_res = topo.compare_images_for_structural_delta(pre_image_path, post_image_path)
            out["height_drop_points"] = int(topo_res.get("height_drop_points", 0))
            out["max_drop_meters"] = float(topo_res.get("max_drop_meters", 0.0))
            out["topology_probability"] = float(topo_res.get("probability_score", 0.0))
            out["topology_status"] = str(topo_res.get("status", "SCANNED"))
        except Exception as e:
            logger.warning("Topological stage failed for event %s: %s", event_id, e)
            out["topology_status"] = "FAILED"

    return out

def regional_deep_scan(limit=20000):
    """
    Targets unscanned or estimated OK/TX leads, prioritizing high-magnitude events.
    """
    logger.info(f"--- Starting Regional Deep-Scan for OK/TX (Limit: {limit}) ---")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Query for unscanned Oklahoma leads, sorted by magnitude DESC
    query = """
    SELECT c.rowid as contact_id, c.street_address, c.phone_number, s.id as event_id, 
           s.latitude, s.longitude, s.city, s.state, s.magnitude, s.event_date
    FROM contacts c
    JOIN storms s ON c.event_id = s.id
    WHERE (c.damage_score IS NULL OR c.damage_score = 0 OR c.proof_msg LIKE '%PROB_ESTIMATE%')
    AND (s.state IN ('OKLAHOMA', 'OK', 'TEXAS', 'TX'))
    AND s.latitude IS NOT NULL AND s.longitude IS NOT NULL
    ORDER BY s.magnitude DESC
    LIMIT ?
    """
    
    c.execute(query, (limit,))
    targets = c.fetchall()
    conn.close()
    
    if not targets:
        logger.info("No unscanned Oklahoma leads found.")
        return

    logger.info(f"Processing {len(targets)} high-priority targets in OK/TX...")
    
    worker = AWSDiscoveryWorker()
    
    try:
        from yolo_detector import RoofDeepLens
        brain = RoofDeepLens()
    except ImportError:
        logger.error("RoofDeepLens not found. Scan aborted.")
        return

    results_found = 0
    catastrophic_found = 0
    
    # We open a new connection for updates
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for t in targets:
        logger.info(f"Scanning: {t['street_address']}, {t['city']} ({t['magnitude']}\")")

        pre_image_path = _maybe_snapshot_previous_image(int(t["event_id"]))

        # 1. Harvest Imagery
        image_path = worker.harvest_imagery(t['latitude'], t['longitude'], t['event_id'])

        advanced = None
        if image_path:
            # 2a. Run AI Inference
            analysis = brain.detect_and_quantify(image_path)
            base_damage_score = float(analysis.get('damage_percent', 0))
            advanced = _run_advanced_forensics(
                event_id=int(t["event_id"]),
                post_image_path=image_path,
                pre_image_path=pre_image_path,
            )
            topo_bonus = min(25.0, float(advanced.get("max_drop_meters", 0.0)) * 15.0)
            damage_score = round(min(99.0, base_damage_score + topo_bonus), 2)
            status_prefix = "AI_SCANNED_3D_TOPO"
        else:
            # 2b. Probabilistic Fallback (If imagery fails)
            # Calibration: 2.0" = ~35% Damage, 3.0" = ~60% Damage, 4.0"+ = ~90% Damage
            damage_score = round(min(99.0, (t['magnitude'] / 4.0) * 100.0), 2)
            status_prefix = "PROB_ESTIMATE"
            logger.warning(f"  [!] Imagery failed. Using Probabilistic Estimate: {damage_score}% based on {t['magnitude']}\" hail.")
            
        # 3. Update DB
        cur.execute('''
            UPDATE contacts 
            SET status = ?, 
                proof_msg = ?,
                damage_score = ?,
                qualification_status = ?
            WHERE rowid = ?
        ''', (
            f"{status_prefix}_{damage_score}%", 
            (
                f"Damage: {damage_score}% | Hail: {t['magnitude']}\" | Method: {status_prefix}"
                + (
                    f" | Topo: {advanced.get('topology_status')} drops={advanced.get('height_drop_points')} "
                    f"max_drop={advanced.get('max_drop_meters')}m"
                    if advanced
                    else ""
                )
                + (
                    f" | 3D: {advanced.get('three_d_model_path')}"
                    if advanced and advanced.get("three_d_model_path")
                    else ""
                )
            ),
            damage_score,
            'QUALIFIED' if damage_score >= 40.0 else 'UNVERIFIED',
            t['contact_id']
        ))
        conn.commit()
        results_found += 1
        
        # 4. If Catastrophic, Sync to Webhook immediately
        if damage_score >= 40.0:
            catastrophic_found += 1
            logger.info(f"  [!!!] CATASTROPHIC DAMAGE DETECTED: {damage_score}%")
            
            lead_data = {
                "first_name": "Homeowner",
                "last_name": "",
                "phone_number": t['phone_number'] or "", 
                "property_address": t['street_address'],
                "city": t['city'],
                "state": t['state'],
                "hail_date": t['event_date'],
                "hail_size": t['magnitude'],
                "damage_probability": damage_score,
                "lead_priority": "PRIORITY_1_EMERGENCY",
                "image_findings": (
                    f"Forensic scan identified {damage_score}% roof degradation (Method: {status_prefix})."
                    + (
                        f" Structural delta={advanced.get('max_drop_meters')}m "
                        f"({advanced.get('height_drop_points')} critical points)."
                        if advanced
                        else ""
                    )
                ),
            }
            send_lead_to_sheets(lead_data)
            import time
            time.sleep(0.5) # Prevent webhook throttling

    conn.close()
    logger.info(f"Deep-Scan Complete. Processed {results_found} properties. Found {catastrophic_found} new catastrophic leads.")

if __name__ == "__main__":
    # Increasing batch size to cover the entire OK/TX list (~20k)
    regional_deep_scan(limit=25000) 
