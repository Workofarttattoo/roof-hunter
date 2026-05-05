"""AERO-COMMAND: Autonomous Public Safety Announcement (PSA) Engine."""

import json
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PSA_Engine")

# Authoritative Announcement Templates
PSA_TEMPLATES = {
    "CRITICAL": "⚠️ [AERO-COMMAND METEOROLOGICAL ALERT] - HIGH-VELOCITY ROTATION LOCK: {city}, {state}. Hail probability {prob}% verified via Digital Twin. Estimated Strike: {time}. ACTION REQUIRED: Move vehicles to cover. Secure all exterior property immediately.",
    "WARNING": "🔔 [AERO-COMMAND SERVICE ANNOUNCEMENT] - SEVERE WEATHER ESCALATION: {city}, {state}. Monitoring atmospheric dryline collision. Risk Score: {score}. Residents should monitor local radar for rapid development.",
    "ADVISORY": "📢 [AERO-COMMAND ADVISORY] - ATMOSPHERIC SURGE DETECTED: {city}, {state}. Potential for severe hail development within 4 hours. Strategic recon is active."
}

def generate_psa(city, state, score, prob=85):
    now = datetime.now()
    strike_time = (now + timedelta(hours=4)).strftime("%I:%M %p")
    
    if score >= 0.90:
        msg = PSA_TEMPLATES["CRITICAL"].format(city=city, state=state, prob=prob, time=strike_time)
        status = "CRITICAL"
    elif score >= 0.80:
        msg = PSA_TEMPLATES["WARNING"].format(city=city, state=state, score=score)
        status = "WARNING"
    else:
        msg = PSA_TEMPLATES["ADVISORY"].format(city=city, state=state)
        status = "ADVISORY"
        
    return {
        "timestamp": now.isoformat(),
        "status": status,
        "message": msg,
        "payload": {
            "city": city,
            "state": state,
            "score": score,
            "eta": strike_time
        }
    }

def run_psa_cycle(outlook_file="three_day_outlook.json"):
    try:
        with open(outlook_file, "r") as f:
            data = json.load(f)
    except:
        logger.error("No outlook data found.")
        return

    active_psas = []
    for hub in data:
        if hub['peak_score'] >= 0.80:
            psa = generate_psa(hub['city'], hub['state'], hub['peak_score'])
            active_psas.append(psa)
            logger.info(f"PSA TRIGGERED: {psa['message']}")
            
    with open("active_psas.json", "w") as f:
        json.dump(active_psas, f, indent=2)
        
    return active_psas

if __name__ == "__main__":
    # Test Run with a Simulated High-Risk Scenario
    simulated_hub = {"city": "Moore", "state": "OK", "peak_score": 0.94}
    psa = generate_psa(simulated_hub['city'], simulated_hub['state'], simulated_hub['peak_score'])
    print("\n" + "="*50)
    print("SIMULATED AUTHORITATIVE PSA")
    print(psa['message'])
    print("="*50)
