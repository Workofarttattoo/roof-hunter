"""
aws_discovery_worker.py
-----------------------
AWS-Optimized Lead Discovery Worker.
Functions:
  1. Identifies targets from Authoritative DB (Hail >= 1.5\", last 30 days).
  2. Harvests sub-meter resolution satellite imagery via Google Maps Static API.
  3. Runs YOLOv8 Deep-Inspection for spectral damage markers.
  4. Updates Lead Manifest with 'Forensic Damage Score'.

Deployment: Designed for EC2 us-east-2.
"""

import os
import sqlite3
import requests
import logging
from dotenv import load_dotenv, dotenv_values
from cloud_notifier import send_lead_dispatch
from insurance_enricher import enrich_leads_with_insurance

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Dynamic Path Resolution
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DOTENV_PATH = os.path.join(BASE_DIR, '.env')
config = dotenv_values(DOTENV_PATH)
DB_PATH = os.path.join(BASE_DIR, 'leads_manifests', 'authoritative_storms.db')
IMAGE_DIR = os.path.join(BASE_DIR, 'training_data')

# Ensure image directory exists
os.makedirs(IMAGE_DIR, exist_ok=True)

class AWSDiscoveryWorker:
    def __init__(self):
        pass
        
    def get_discovery_targets(self, min_hail=1.5, days=30):
        """Query DB for leads hit by significant hail recently."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # PRIORITY: Oklahoma catastrophic wind swath (Vance AFB area)
        # Sort by Magnitude DESC and prioritize Oklahoma states
        query = """
        SELECT DISTINCT c.street_address, s.id, s.latitude, s.longitude, s.city, s.state, s.magnitude
        FROM storms s
        JOIN contacts c ON s.id = c.event_id
        WHERE s.magnitude >= ? 
        AND s.event_date >= date('now', ?)
        ORDER BY (CASE WHEN s.state = 'OKLAHOMA' THEN 0 ELSE 1 END), s.magnitude DESC
        """
        params = (min_hail, f'-{days} days')
        c.execute(query, params)
        targets = c.fetchall()
        conn.close()
        return targets

    def harvest_imagery(self, lat, lon, target_id):
        """Fetch 640x640 Satellite view via ArcGIS Tile API and stitch tiles (Open Data)."""
        import math
        from PIL import Image
        from io import BytesIO
        
        filename = f"hail_target_{target_id}.png"
        save_path = os.path.join(IMAGE_DIR, filename)
        zoom = 20
        
        # Lat/Lon to Tile Coordinates (Slippy Map Tiles)
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        xtile_f = (lon + 180.0) / 360.0 * n
        ytile_f = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
        
        xtile = int(xtile_f)
        ytile = int(ytile_f)
        
        # Pixels within the center tile
        x_offset = int((xtile_f - xtile) * 256)
        y_offset = int((ytile_f - ytile) * 256)
        
        # Stitch a 3x3 grid (768x768 pixels) to allow cropping a 640x640 centered image
        combined_image = Image.new('RGB', (768, 768))
        
        try:
            logger.info(f"  [ARCGIS] Stitching 3x3 tile grid for {lat}, {lon}")
            for i in range(-1, 2):
                for j in range(-1, 2):
                    cur_x = xtile + i
                    cur_y = ytile + j
                    # ArcGIS REST Tile URL
                    url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{cur_y}/{cur_x}"
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        tile_img = Image.open(BytesIO(r.content))
                        combined_image.paste(tile_img, ((i + 1) * 256, (j + 1) * 256))
                    else:
                        logger.warning(f"    [!] Tile {cur_x}/{cur_y} missing (Status {r.status_code})")
            
            # Crop 640x640 centered on the exact coordinates
            # Center of the 3x3 grid is at index (1,1), which starts at pixel (256, 256)
            center_x = 256 + x_offset
            center_y = 256 + y_offset
            
            left = center_x - 320
            top = center_y - 320
            right = left + 640
            bottom = top + 640
            
            final_image = combined_image.crop((left, top, right, bottom))
            final_image.save(save_path)
            return save_path
            
        except Exception as e:
            logger.error(f"ArcGIS Stitching failed for {target_id}: {e}")
        return None

    def process_pipeline(self):
        """Main loop: Discovery -> Harvest -> Assessment."""
        targets = self.get_discovery_targets()
        logger.info(f"Targeting {len(targets)} leads for forensic discovery.")
        
        try:
            from yolo_detector import RoofDeepLens
            brain = RoofDeepLens()
        except ImportError:
            logger.error("RoofDeepLens (yolo_detector.py) not found in src/")
            return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        results_found = 0
        for t in targets:
            logger.info(f"Scanning target #{t['id']} | {t['city']}, {t['state']} ({t['magnitude']}\")")
            
            # 1. Harvest Imagery
            image_path = self.harvest_imagery(t['latitude'], t['longitude'], t['id'])
            
            if image_path:
                # 2. Run AI Inference
                analysis = brain.detect_and_quantify(image_path)
                damage_score = analysis.get('damage_percent', 0)
                
                # 3. Update DB with Damage Metrics
                c.execute('''
                    UPDATE contacts 
                    SET status = ?, 
                        proof_msg = ?,
                        damage_score = ?
                    WHERE event_id = ?
                ''', (
                    f"AI_SCANNED_{damage_score}%", 
                    f"Damage: {damage_score}% | Hail: {t['magnitude']}\"",
                    damage_score,
                    t['id']
                ))
                results_found += 1
                logger.info(f"  --> Result: {damage_score}% Damage Detected. DB Updated.")

        conn.commit()
        conn.close()
        logger.info(f"AWS Discovery Pipeline Complete. Processed {results_found} properties.")
        
        # Trigger Insurance Enrichment
        logger.info("Enriching leads with Insurance Carrier data...")
        enrich_leads_with_insurance()

        # Trigger Auto-Dispatch to Inventor
        logger.info("Triggering Lead Dispatch to inventor@aios.is...")
        send_lead_dispatch()

if __name__ == "__main__":
    worker = AWSDiscoveryWorker()
    worker.process_pipeline()
