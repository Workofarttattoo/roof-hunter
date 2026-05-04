import sys
import csv
import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

BLAND_API_KEY = os.getenv("BLAND_AI_API_KEY")
import glob

def get_latest_enriched_leads():
    search_pattern = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'leads_manifests', 'TOP_200_ENRICHED_LEADS_*.csv'))
    files = glob.glob(search_pattern)
    if not files:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'leads_manifests', 'okc_edmond_bland_batch.csv')) # fallback
    return max(files, key=os.path.getmtime)

DEFAULT_CSV = get_latest_enriched_leads()
CSV_FILE = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
CSV_FILE = os.path.abspath(CSV_FILE)
PERSONA_ID = os.getenv("BLAND_AGENT_ID")
WEBHOOK_URL = os.getenv("GOOGLE_SHEETS_WEBHOOK", "https://script.google.com/macros/s/AKfycbwcEyyU9EnjCFEQor34tfz5nYe76q3qc2ZMjUuijIqMuCsjAz-OmcFaRkaONp3JYbcI/exec")
PROMPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sarah_master_prompt_lite.md'))

def get_prompt():
    if os.path.exists(PROMPT_PATH):
        with open(PROMPT_PATH, 'r') as f:
            return f.read()
    return ""

def send_batch(leads):
    """Send a batch of leads to Bland AI."""
    if not BLAND_API_KEY:
        print("❌ ERROR: BLAND_AI_API_KEY not found in .env")
        return

    prompt_content = get_prompt()
    call_data = []
    for lead in leads:
        call_data.append({
            "phone_number": lead["phone_number"],
            "request_data": {
                "first_name": lead.get("first_name", "Homeowner"),
                "property_address": lead.get("property_address", ""),
                "city": lead.get("city", ""),
                "state": lead.get("state", ""),
                "hail_date": lead.get("hail_date", ""),
                "hail_size": lead.get("hail_size", ""),
                "storm_type": lead.get("storm_type", "hail"),
                "damage_probability": lead.get("damage_probability", ""),
                "structures_hit": lead.get("structures_hit", ""),
                "image_findings": lead.get("image_findings", ""),
                "lead_priority": lead.get("lead_priority", "UNKNOWN")
            }
        })
    
    payload = {
        "call_objects": call_data,
        "global": {
            "pathway_id": "626c6769-ec22-4722-a91e-c5c12dfd4b6d",
            "voice": "45bfac80-786f-409e-acd0-6c424603a12e",
            "wait_for_greeting": false,
            "record": true,
            "answered_by_enabled": true,
            "noise_cancellation": false,
            "interruption_threshold": 450,
            "block_interruptions": false,
            "max_duration": 12,
            "model": "base",
            "memory_id": "20eeb38c-c1b0-47e5-a708-ebd230ae6b4e",
            "language": "babel-en",
            "background_track": "office",
            "voicemail_action": "leave_message",
            "voicemail_message": "OKC Roofing Pros here, we spotted damages to your roof from our satelite images taken after the last hail strike. We can fix it in one day...want a free estimate?",
            "summary_prompt": "summarize call and upload all lead info to google sheets",
            "temperature": 0.7,
            "from": "+14057252639",
            "sensitive_voicemail_detection": true,
            "webhook": WEBHOOK_URL,
            "json_mode_enabled": true,
            "analysis_schema": {
                "lead_priority": "string",
                "homeowner_name": "string",
                "property_address": "string",
                "inspection_booked": "boolean",
                "call_outcome": "string",
                "notes": "string"
            }
        },
        "description": f"Batch: {os.path.basename(CSV_FILE)[:30]} {time.strftime('%H:%M')}"
    }

    response = requests.post(
        "https://api.bland.ai/v2/batches/create",
        headers={
            "Authorization": BLAND_API_KEY,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        json=payload
    )
    
    if response.status_code != 200:
        print(f"❌ API Error {response.status_code}: {response.text}")
        return {"status": "error", "message": response.text}

    return response.json()

def load_csv(filepath):
    """Load leads from CSV file."""
    leads = []
    if not os.path.exists(filepath):
        print(f"❌ ERROR: CSV file not found at {filepath}")
        return []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("phone_number"):
                leads.append(row)
    return leads

if __name__ == "__main__":
    leads = load_csv(CSV_FILE)
    if not leads:
        print("No leads to process.")
        exit()

    print(f"Loaded {len(leads)} leads from {CSV_FILE}")
    
    # Send in batches of 50
    BATCH_SIZE = 50
    for i in range(0, len(leads), BATCH_SIZE):
        batch = leads[i:i + BATCH_SIZE]
        print(f"\nSending batch {i // BATCH_SIZE + 1} ({len(batch)} leads)...")
        result = send_batch(batch)
        print(f"Response: {json.dumps(result, indent=2)}")
        if i + BATCH_SIZE < len(leads):
            time.sleep(2)
