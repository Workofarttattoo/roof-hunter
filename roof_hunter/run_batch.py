import csv
import requests
import json
import time
import os

API_KEY = os.getenv("BLAND_API_KEY", "org_3449d7e4663af15a753720715f8c00813c7690c67cd3cf327c527b05196cec6c8cf70ca1982cd67a0c0c69")
PERSONA_ID = "d0b593d4-75de-45f3-92ab-919bafd0b3d1"
FROM_NUMBER = "+14057252639"
WEBHOOK = "https://script.google.com/macros/s/AKfycbwRj73u0wSyabbFbdVOeEvn5toXP7GI0Y7eeB5xxCDfeNMOnfMGu2zU3XgDZlkTr5aA/exec"
CSV_FILE = "tier1_emergency_80_plus.csv"  # change to your file

def load_csv(path):
    leads = []
    with open(path, "r") as f:
        for row in csv.DictReader(f):
            if row.get("phone_number"):
                leads.append(row)
    return leads

def send_batch(leads):
    call_data = []
    for lead in leads:
        call_data.append({
            "phone_number": lead["phone_number"],
            "from": FROM_NUMBER,
            "persona_id": PERSONA_ID,
            "wait_for_greeting": True,
            "record": True,
            "max_duration": 8,
            "language": "en-US",
            "request_data": {
                "first_name": lead.get("first_name", ""),
                "last_name": lead.get("last_name", ""),
                "property_address": lead.get("property_address", ""),
                "city": lead.get("city", ""),
                "state": lead.get("state", ""),
                "zip_code": lead.get("zip_code", ""),
                "hail_date": lead.get("hail_date", ""),
                "hail_size": lead.get("hail_size", ""),
                "storm_type": lead.get("storm_type", ""),
                "damage_probability": lead.get("damage_probability", ""),
                "structures_hit": lead.get("structures_hit", ""),
                "image_findings": lead.get("image_findings", ""),
                "lead_priority": lead.get("lead_priority", "")
            },
            "webhook": WEBHOOK
        })

    resp = requests.post(
        "https://api.bland.ai/v1/batches",
        headers={"Authorization": API_KEY, "Content-Type": "application/json"},
        json={"call_data": call_data, "label": f"OKC Roofing - {time.strftime('%Y-%m-%d %H:%M')}"}
    )
    return resp.json()

if __name__ == "__main__":
    leads = load_csv(CSV_FILE)
    print(f"Loaded {len(leads)} leads")

    for i in range(0, len(leads), 50):
        batch = leads[i:i+50]
        print(f"Sending batch {i//50+1} ({len(batch)} leads)...")
        result = send_batch(batch)
        print(json.dumps(result, indent=2))
        if i + 50 < len(leads):
            time.sleep(5)

    print("Done.")
Then run:

python run_batch.py
Option B -- Bland dashboard
Go to Send Calls > Batch Calls
Select Sarah - OKC Roofing Pro persona
Upload your CSV
Click Send
Option C -- Single cURL test (verify API key works first)
curl -X POST https://api.bland.ai/v1/calls \
  -H "Authorization: org_3449d7e4663af15a753720715f8c00813c7690c67cd3cf327c527b05196cec6c8cf70ca1982cd67a0c0c69" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "YOUR_TEST_NUMBER",
    "from": "+14057252639",
    "persona_id": "d0b593d4-75de-45f3-92ab-919bafd0b3d1",
    "record": true,
    "max_duration": 8,
    "request_data": {
      "first_name": "Test",
      "property_address": "123 Main St",
      "city": "Wichita Falls",
      "state": "TX",
      "hail_size": "3.0",
      "damage_probability": "82.52",
      "structures_hit": "Primary roof system, soft metals, and ancillary structures",
      "image_findings": "Damage: 82.52%",
      "lead_priority": "PRIORITY_1_EMERGENCY"
    }
  }'
