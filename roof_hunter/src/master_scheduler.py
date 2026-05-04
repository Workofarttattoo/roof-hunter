import os
import time
import requests
import csv
import schedule
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_BASE = "http://localhost:8000/elevenlabs/dispatch-batch"
MANIFEST_DIR = "leads_manifests"

def run_scheduled_dispatch():
    """Triggers the prioritized OK and TX batches at the scheduled time."""
    print(f"[{datetime.now()}] 🚀 7:00 AM START: Executing Scheduled Forensic Outreach...")
    
    # 1. OKLAHOMA RICH BATCH (Edmond/Nichols Hills)
    ok_manifest = sorted([f for f in os.listdir(MANIFEST_DIR) if "OKLAHOMA_CATASTROPHIC_RICH_BATCH" in f])[-1]
    ok_path = os.path.join(MANIFEST_DIR, ok_manifest)
    
    print(f"Triggering OK Rich Batch: {ok_manifest}")
    requests.post(API_BASE, json={"csv_path": ok_path})
    
    # Wait for OK to clear (approx 1 hour for 1k leads at 1s throttle)
    time.sleep(3600)
    
    # 2. TEXAS TARGET BATCH (Fort Worth/Paris)
    tx_manifest = sorted([f for f in os.listdir(MANIFEST_DIR) if "FORT_WORTH_TARGET_BATCH" in f])[-1]
    tx_path = os.path.join(MANIFEST_DIR, tx_manifest)
    
    print(f"Triggering TX Batch: {tx_manifest}")
    requests.post(API_BASE, json={"csv_path": tx_path})

# Schedule for 7:00 AM Central Time (assuming server is on Central or adjust accordingly)
# If server is UTC, adjust the time. 7 AM CST = 12 PM UTC.
schedule.every().day.at("07:00").do(run_scheduled_dispatch)

if __name__ == "__main__":
    print("🕰️ Roof Hunter Scheduler Active. Waiting for 7:00 AM to launch forensic dispatches...")
    while True:
        schedule.run_pending()
        time.sleep(60)
