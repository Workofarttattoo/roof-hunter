import csv
import requests
import random
import json
import time
import os
from flask import Flask, request as flask_request

# ============================================================
# CONFIG
# ============================================================

API_KEY = os.getenv("BLAND_API_KEY", "org_3449d7e4663af15a753720715f8c00813c7690c67cd3cf327c527b05196cec6c8cf70ca1982cd67a0c0c69")
PERSONA_ID = os.getenv("BBB_PERSONA_ID", "d0b593d4-75de-45f3-92ab-919bafd0b3d1")
FROM_NUMBER = os.getenv("BLAND_FROM_NUMBER", "+14057252639")
WEBHOOK_URL = os.getenv("BLAND_WEBHOOK_URL", "https://script.google.com/macros/s/AKfycbwRj73u0wSyabbFbdVOeEvn5toXP7GI0Y7eeB5xxCDfeNMOnfMGu2zU3XgDZlkTr5aA/exec")
CSV_FILE = os.getenv("CSV_FILE", "leads.csv")
BATCH_SIZE = int(os.getenv("BLAND_BATCH_SIZE", "50"))

# ============================================================
# A/B TEST STATE
# ============================================================

variant_weights = {"A": 0.5, "B": 0.5}
campaign_results = []

# ============================================================
# GENDER INFERENCE
# ============================================================

MALE_NAMES = {
    "james","john","robert","michael","david","william","richard","joseph",
    "thomas","charles","christopher","daniel","matthew","anthony","mark",
    "donald","steven","paul","andrew","joshua","kenneth","kevin","brian",
    "george","timothy","ronald","edward","jason","jeffrey","ryan","jacob",
    "gary","nicholas","eric","jonathan","stephen","larry","justin","scott",
    "brandon","benjamin","samuel","raymond","gregory","frank","alexander",
    "patrick","jack","dennis","jerry","tyler","aaron","jose","adam","nathan",
    "henry","douglas","peter","zachary","kyle","noah","ethan","jeremy",
    "walter","christian","keith","roger","terry","austin","sean","gerald",
    "carl","harold","dylan","arthur","lawrence","jordan","jesse","bryan",
    "billy","bruce","gabriel","joe","logan","albert","willie","alan","eugene",
    "vincent","russell","bobby","johnny","phillip","troy","randy","harry",
    "howard","carlos","hector","leon","mario","craig","todd","allen","jeff",
    "chad","lance","darrell","darren","derrick","joel","ricardo","juan",
    "pedro","jorge","caleb","evan","chase","levi","duane","edward"
}

FEMALE_NAMES = {
    "mary","patricia","jennifer","linda","barbara","elizabeth","susan",
    "jessica","sarah","karen","lisa","nancy","betty","margaret","sandra",
    "ashley","dorothy","kimberly","emily","donna","michelle","carol",
    "amanda","melissa","deborah","stephanie","rebecca","sharon","laura",
    "cynthia","kathleen","amy","angela","shirley","anna","brenda","pamela",
    "emma","nicole","helen","samantha","katherine","christine","debra",
    "rachel","carolyn","janet","catherine","maria","heather","diane",
    "ruth","julie","olivia","joyce","virginia","victoria","kelly","lauren",
    "christina","joan","evelyn","judith","megan","andrea","cheryl","hannah",
    "jacqueline","martha","gloria","teresa","ann","sara","madison","frances",
    "kathryn","janice","jean","abigail","alice","judy","sophia","grace",
    "denise","amber","doris","marilyn","danielle","beverly","isabella",
    "theresa","diana","natalie","brittany","charlotte","marie","kayla",
    "alexis","lori","crystal","tiffany","tammy","tracy","holly","leslie",
    "courtney","briana","tanya","gail","mallory","melinda","miranda",
    "rhonda","sierra","tabitha","valerie","erin","allison","jasmine",
    "alicia","carmen","leah","priscilla","elaine","yolanda","sonya"
}

def infer_gender(first_name):
    name = first_name.strip().lower()
    # Strip titles
    for title in ["mr.", "mrs.", "ms.", "dr.", "mr", "mrs", "ms", "dr"]:
        if name.startswith(title):
            name = name[len(title):].strip()
    if name in MALE_NAMES:
        return "male"
    if name in FEMALE_NAMES:
        return "female"
    return "unknown"

# ============================================================
# A/B VARIANT ASSIGNMENT
# ============================================================

def assign_variant():
    return "A" if random.random() < variant_weights["A"] else "B"

def assign_voice(gender, variant):
    if variant == "A":
        return "male" if gender == "female" else "female"
    else:
        return gender if gender != "unknown" else "female"

# ============================================================
# PHONE CLEANUP
# ============================================================

def clean_phone(phone):
    phone = phone.strip().lstrip("+").lstrip("0")
    if len(phone) == 10:
        return "+1" + phone
    elif len(phone) == 11 and phone.startswith("1"):
        return "+" + phone
    return None

# ============================================================
# LOAD CSV
# ============================================================

def load_csv(path):
    leads = []
    with open(path, "r") as f:
        for row in csv.DictReader(f):
            phone = clean_phone(row.get("phone_number", ""))
            if not phone:
                continue
            row["phone_number"] = phone
            leads.append(row)
    return leads

# ============================================================
# SEND BATCH
# ============================================================

def send_batch(leads):
    call_data = []
    batch_meta = []

    for lead in leads:
        gender = infer_gender(lead.get("first_name", ""))
        variant = assign_variant()
        voice = assign_voice(gender, variant)

        call_entry = {
            "phone_number": lead["phone_number"],
            "request_data": {
                "first_name": str(lead.get("first_name", "")),
                "last_name": str(lead.get("last_name", "")),
                "property_address": str(lead.get("property_address", "")),
                "city": str(lead.get("city", "")),
                "state": str(lead.get("state", "")),
                "zip_code": str(lead.get("zip_code", "")),
                "hail_date": str(lead.get("hail_date", "")),
                "hail_size": str(lead.get("hail_size", "")),
                "storm_type": str(lead.get("storm_type", "")),
                "damage_probability": str(lead.get("damage_probability", "")),
                "structures_hit": str(lead.get("structures_hit", "")),
                "image_findings": str(lead.get("image_findings", "")),
                "lead_priority": str(lead.get("lead_priority", ""))
            },
            "metadata": {
                "gender": gender,
                "variant": variant,
                "voice": voice,
                "campaign": "okc_roofing_storm_response",
                "system": "bbb_roof_hunter_pro"
            }
        }
        call_data.append(call_entry)
        batch_meta.append({
            "phone": lead["phone_number"],
            "name": lead.get("first_name", ""),
            "gender": gender,
            "variant": variant,
            "voice": voice
        })

    resp = requests.post(
        "https://api.bland.ai/v1/batches",
        headers={"Authorization": API_KEY, "Content-Type": "application/json"},
        json={
            "persona_id": PERSONA_ID,
            "from": FROM_NUMBER,
            "record": True,
            "wait_for_greeting": True,
            "max_duration": 8,
            "language": "en-US",
            "webhook": WEBHOOK_URL,
            "label": "OKC Roofing - " + time.strftime("%Y-%m-%d %H:%M"),
            "description": "Storm damage leads batch with A/B voice testing",
            "call_data": call_data
        }
    )
    return resp.json(), batch_meta

# ============================================================
# AUTO-OPTIMIZER
# ============================================================

def update_weights():
    global variant_weights
    if not campaign_results:
        return

    a_total = sum(1 for r in campaign_results if r.get("variant") == "A")
    b_total = sum(1 for r in campaign_results if r.get("variant") == "B")
    a_success = sum(1 for r in campaign_results if r.get("variant") == "A" and r.get("success"))
    b_success = sum(1 for r in campaign_results if r.get("variant") == "B" and r.get("success"))

    a_rate = a_success / a_total if a_total > 0 else 0.5
    b_rate = b_success / b_total if b_total > 0 else 0.5
    total_rate = a_rate + b_rate

    if total_rate > 0:
        variant_weights["A"] = a_rate / total_rate
        variant_weights["B"] = b_rate / total_rate

    print(f"Updated weights: A={variant_weights['A']:.2f} B={variant_weights['B']:.2f}")
    print(f"  A: {a_success}/{a_total} success | B: {b_success}/{b_total} success")

# ============================================================
# WEBHOOK SERVER (receives call results)
# ============================================================

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = flask_request.json
    if not data:
        return {"status": "no data"}, 400

    outcome = data.get("status", data.get("call_status", "unknown"))
    duration = data.get("call_length", data.get("duration", 0))
    metadata = data.get("metadata", {})
    analysis = data.get("analysis", {})

    success = False
    if analysis:
        success = analysis.get("inspection_booked", False)
    elif outcome == "completed" and duration and float(duration) > 60:
        success = True

    result = {
        "variant": metadata.get("variant", "unknown"),
        "voice": metadata.get("voice", "unknown"),
        "gender": metadata.get("gender", "unknown"),
        "outcome": outcome,
        "duration": duration,
        "success": success,
        "phone": data.get("to", ""),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    campaign_results.append(result)

    print(f"Call result: {result['phone']} | {result['variant']} | {result['voice']} | success={result['success']} | {result['duration']}s")

    # Auto-optimize every 20 results
    if len(campaign_results) % 20 == 0:
        update_weights()

    return {"status": "ok"}

@app.route("/stats", methods=["GET"])
def get_stats():
    a_total = sum(1 for r in campaign_results if r.get("variant") == "A")
    b_total = sum(1 for r in campaign_results if r.get("variant") == "B")
    a_success = sum(1 for r in campaign_results if r.get("variant") == "A" and r.get("success"))
    b_success = sum(1 for r in campaign_results if r.get("variant") == "B" and r.get("success"))

    return {
        "total_calls": len(campaign_results),
        "variant_A": {"total": a_total, "success": a_success, "rate": round(a_success/a_total, 2) if a_total else 0},
        "variant_B": {"total": b_total, "success": b_success, "rate": round(b_success/b_total, 2) if b_total else 0},
        "current_weights": variant_weights
    }

@app.route("/run", methods=["POST"])
def trigger_batch():
    csv_file = flask_request.json.get("csv_file", CSV_FILE) if flask_request.json else CSV_FILE
    leads = load_csv(csv_file)
    print(f"Loaded {len(leads)} leads from {csv_file}")

    all_results = []
    all_meta = []

    for i in range(0, len(leads), BATCH_SIZE):
        batch = leads[i:i+BATCH_SIZE]
        print(f"Sending batch {i//BATCH_SIZE+1} ({len(batch)} leads)...")
        result, meta = send_batch(batch)
        all_results.append(result)
        all_meta.extend(meta)
        if i + BATCH_SIZE < len(leads):
            time.sleep(5)

    return {
        "status": "sent",
        "total_leads": len(leads),
        "batches": len(all_results),
        "meta": all_meta[:10],
        "results": all_results
    }

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "send":
        # Direct send mode: python app.py send leads.csv
        csv_file = sys.argv[2] if len(sys.argv) > 2 else CSV_FILE
        leads = load_csv(csv_file)
        print(f"Loaded {len(leads)} leads")

        for i in range(0, len(leads), BATCH_SIZE):
            batch = leads[i:i+BATCH_SIZE]
            print(f"\nBatch {i//BATCH_SIZE+1}: {len(batch)} leads")
            result, meta = send_batch(batch)
            print(json.dumps(result, indent=2))
            for m in meta:
                print(f"  {m['name']:20s} | {m['gender']:7s} | variant {m['variant']} | voice {m['voice']}")
            if i + BATCH_SIZE < len(leads):
                time.sleep(5)

        print("\nDone.")
    else:
        # Server mode: receives webhooks + has /run and /stats endpoints
        print("Starting webhook server on port 5000...")
        print("POST /run        - trigger batch from CSV")
        print("POST /webhook    - receive call results")
        print("GET  /stats      - view A/B test results")
        app.run(host="0.0.0.0", port=5000)
Two ways to use it:

Send leads immediately (no server needed):
pip install requests flask
python app.py send leads.csv
Run as server (webhook + auto-optimizer + API trigger):
python app.py
Then:

POST /run -- triggers batch from CSV
POST /webhook -- receives Bland call results
GET /stats -- shows A/B test performance
What it does on every lead:

Reads CSV
Cleans phone numbers (adds +1)
Infers gender from first name (170+ names built in)
Assigns A/B variant (weighted random)
Assigns voice (A = opposite gender voice, B = same gender voice)
Sends to Bland with full request_data + metadata tracking
Webhook receives results, logs success/failure
Every 20 calls, auto-adjusts A/B weights toward the winning variant
