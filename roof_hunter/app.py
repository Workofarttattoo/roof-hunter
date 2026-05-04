from flask import Flask, request, jsonify
import requests
import random
import os
import datetime
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration from Environment
BLAND_API_KEY = os.getenv("BLAND_AI_API_KEY")
AGENT_MALE = os.getenv("AGENT_MALE", os.getenv("BLAND_AGENT_ID"))  # Fallback to general ID
AGENT_FEMALE = os.getenv("AGENT_FEMALE", os.getenv("BLAND_AGENT_ID"))
SHEETS_WEBHOOK = os.getenv("GOOGLE_SHEETS_WEBHOOK")

# Persistence for weights (Simple JSON file)
WEIGHTS_FILE = "variant_weights.json"

def load_weights():
    if os.path.exists(WEIGHTS_FILE):
        try:
            with open(WEIGHTS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading weights: {e}")
    return {"A": 0.5, "B": 0.5}

def save_weights(weights):
    try:
        with open(WEIGHTS_FILE, 'w') as f:
            json.dump(weights, f)
    except Exception as e:
        logger.error(f"Error saving weights: {e}")

# Global state for weights
variant_weights = load_weights()

def infer_gender(name):
    if not name:
        return "unknown"
    name = name.lower()
    male_names = ["john", "mike", "david", "chris", "robert", "michael", "james", "william"]
    female_names = ["sarah", "emily", "jessica", "ashley", "linda", "barbara", "elizabeth", "susan"]
    
    if any(m in name for m in male_names): return "male"
    if any(f in name for f in female_names): return "female"
    return "unknown"

def choose_variant():
    return "A" if random.random() < variant_weights["A"] else "B"

def assign_voice(gender, variant):
    # A/B logic: Variant A might favor opposite gender voices, Variant B favors same gender
    if variant == "A":
        return "male" if gender == "female" else "female"
    return gender if gender != "unknown" else "female"

def select_agent(voice):
    return AGENT_MALE if voice == "male" else AGENT_FEMALE

def log_to_sheets(row):
    if not SHEETS_WEBHOOK:
        logger.warning("Sheets webhook URL not set. Skipping log.")
        return
    try:
        requests.post(SHEETS_WEBHOOK, json=row)
    except Exception as e:
        logger.error(f"Error logging to sheets: {e}")

def update_weights(results):
    global variant_weights
    # Logic based on success rates
    a_success = sum(1 for r in results if r["variant"] == "A" and r.get("success"))
    b_success = sum(1 for r in results if r["variant"] == "B" and r.get("success"))
    a_total = sum(1 for r in results if r["variant"] == "A")
    b_total = sum(1 for r in results if r["variant"] == "B")
    
    if a_total == 0 or b_total == 0:
        return # Need data from both to optimize
    
    rate_a = a_success / a_total
    rate_b = b_success / b_total
    
    total_rate = rate_a + rate_b
    if total_rate == 0:
        variant_weights["A"] = 0.5
        variant_weights["B"] = 0.5
    else:
        variant_weights["A"] = rate_a / total_rate
        variant_weights["B"] = rate_b / total_rate
    
    save_weights(variant_weights)
    logger.info(f"Updated weights: {variant_weights}")

def call_lead(lead):
    gender = infer_gender(lead.get("name", "Unknown"))
    variant = choose_variant()
    voice = assign_voice(gender, variant)
    agent_id = select_agent(voice)
    
    payload = {
        "phone_number": lead["phone"],
        "agent_id": agent_id,
        "dynamic_variables": {
            "first_name": lead.get("name", "Homeowner"),
            "city": lead.get("city", "your area"),
            "storm_date": lead.get("storm_date", "recent storm")
        },
        "metadata": {
            "lead_id": lead.get("id"),
            "variant": variant,
            "voice": voice
        }
    }
    
    logger.info(f"Calling lead {lead.get('name')} with variant {variant} and voice {voice}")
    
    res = requests.post(
        "https://api.bland.ai/v1/calls",
        json=payload,
        headers={"Authorization": BLAND_API_KEY}
    )
    
    result = {
        "variant": variant, 
        "voice": voice, 
        "response": res.json(),
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Initial log to sheets
    log_to_sheets({
        "timestamp": result["timestamp"],
        "lead_id": lead.get("id"),
        "name": lead.get("name"),
        "status": "DISPATCHED",
        "variant": variant,
        "voice": voice
    })
    
    return result

@app.route("/run_campaign", methods=["POST"])
def run_campaign():
    leads = request.json.get("leads", [])
    results = []
    for lead in leads:
        try:
            result = call_lead(lead)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to call lead {lead.get('id')}: {e}")
            results.append({"lead_id": lead.get("id"), "error": str(e)})
    return jsonify(results)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    metadata = data.get("metadata", {})
    lead_id = metadata.get("lead_id")
    variant = metadata.get("variant")
    status = data.get("call_status")
    duration = data.get("duration")
    
    logger.info(f"Webhook Received: {lead_id} | {variant} | {status} | {duration}")
    
    # Determine success (e.g., completed and duration > 30s or specific outcome)
    # This logic can be tuned
    success = status == "completed" and duration and duration > 20
    
    # Store in history for optimizer (In-memory for this run, but we could use DB)
    # For now, let's just trigger a weight update if we have enough data or just log it
    
    log_to_sheets({
        "timestamp": datetime.datetime.now().isoformat(),
        "lead_id": lead_id,
        "status": status,
        "duration": duration,
        "variant": variant,
        "success": success
    })
    
    return jsonify({"status": "ok"})

@app.route("/")
def health():
    return jsonify({
        "status": "healthy",
        "weights": variant_weights,
        "timestamp": datetime.datetime.now().isoformat()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
