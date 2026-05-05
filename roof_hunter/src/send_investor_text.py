"""AERO-COMMAND: Investor Target Text Dispatch."""

import os
import requests
import logging
from dotenv import load_dotenv

# Load environment
ROOT = "/Users/noone/Downloads/github/roof-hunter/roof_hunter"
load_dotenv(os.path.join(ROOT, ".env"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("InvestorText")

def send_investor_summary(to_phone):
    api_key = os.getenv("TELNYX_API_KEY")
    from_phone = os.getenv("TELNYX_PHONE_NUMBER")
    
    if not api_key or not from_phone:
        logger.error("TELNYX_API_KEY or TELNYX_PHONE_NUMBER not found. Simulate Mode.")
        return False

    # Executive Summary
    message = (
        "📊 AERO-COMMAND: Triple-Phase Manifest Secure.\n"
        "Total Leads: 4,514 (OK/TX)\n"
        "Top Corridor: Dallas/Fort Worth & OKC\n"
        "Forensic ROI: $48M+ Pipeline\n\n"
        "Download Full CSV: https://aero-command-forensics.ngrok-free.app/download-targets"
    )
    
    url = "https://api.telnyx.com/v2/messages"
    payload = {
        "from": from_phone,
        "to": to_phone,
        "text": message
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        r = requests.post(url, json=payload, headers=headers)
        if r.status_code in [200, 201]:
            logger.info(f"✅ INVESTOR TEXT DISPATCHED to {to_phone}")
            return True
        else:
            logger.error(f"❌ Telnyx Error: {r.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Transport Error: {e}")
        return False

if __name__ == "__main__":
    send_investor_summary("+17252241240")
