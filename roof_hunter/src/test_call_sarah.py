import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BLAND_AI_API_KEY")
AGENT_ID = os.getenv("BLAND_AGENT_ID")
TEST_NUMBER = "+17252241240"
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwRj73u0wSyabbFbdVOeEvn5toXP7GI0Y7eeB5xxCDfeNMOnfMGu2zU3XgDZlkTr5aA/exec"

def trigger_test_call():
    payload = {
        "phone_number": TEST_NUMBER,
        "task": """You are Sarah, a professional agent for Better Business Builder & Roof Hunter Pro. Your goal: book free roof inspections using forensic data.
        ### DYNAMIC INTEL (Metadata):
        {{first_name}}, {{property_address}}, {{city}}, {{hail_date}}, {{hail_size}}, {{damage_probability}}%, {{structures_hit}}, {{image_findings}}
        ### OPENING:
        "Hi {{first_name}}? Sarah with Roof Hunter Pro. I'm calling because {{property_address}} was flagged after the {{hail_date}} storm. Our forensic scan detected anomalies on the {{structures_hit}}, specifically {{image_findings}}. We're booking free inspections in {{city}} today—would morning or afternoon work best?"
        ### DAMAGE TIER LOGIC:
        - 80%+: Use high urgency. "Significant risk. Emergency dispatch suggested."
        - 60%+: Focus on verified "Signature Damage" in {{image_findings}}.
        - 40%+: Focus on "Hidden Damage" not visible from the ground.
        ### OBJECTIONS:
        - "No damage": "Commonly hidden from the ground. {{image_findings}} suggests it's best to verify."
        ### RULES:
        - Never hallucinate. Use "Flagged," "Likely," or "Anomalies."
        - Keep responses short and focused on BOOKING.""",
        "wait_for_greeting": True,
        "record": True,
        "request_data": {
            "first_name": "Joshua",
            "property_address": "123 Forensic Way",
            "city": "Edmond",
            "state": "OK",
            "hail_date": "April 25, 2026",
            "hail_size": "2.5",
            "storm_type": "Severe Hail Storm",
            "damage_probability": "84",
            "structures_hit": "Main roof and detached workshop",
            "image_findings": "High-density spectral anomalies on south-facing slope",
            "lead_priority": "PRIORITY_1_EMERGENCY"
        },
        "webhook": WEBHOOK_URL,
        "analysis_schema": {
            "lead_priority": "string",
            "homeowner_name": "string",
            "property_address": "string",
            "inspection_booked": "boolean",
            "call_outcome": "string",
            "notes": "string"
        }
    }
    
    print(f"🚀 Triggering Intelligent Test Call to {TEST_NUMBER}...")
    response = requests.post(
        "https://api.bland.ai/v1/calls",
        headers={
            "Authorization": API_KEY,
            "Content-Type": "application/json"
        },
        json=payload
    )
    
    if response.status_code == 200:
        print(f"✅ Call Dispatched! ID: {response.json().get('call_id')}")
    else:
        print(f"❌ Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    trigger_test_call()
