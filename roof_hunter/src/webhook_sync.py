import os
import csv
import requests
import json
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

WEBHOOK_URL = os.getenv("GOOGLE_SHEETS_WEBHOOK")

def send_lead_to_sheets(lead_data):
    """Sends a single lead to the Google Sheets webhook."""
    if not WEBHOOK_URL:
        logger.error("GOOGLE_SHEETS_WEBHOOK not found in .env")
        return False
    
    try:
        # Standardize for the webhook (usually expects Bland AI callback format or simple KV)
        # We'll send the full dict
        response = requests.post(WEBHOOK_URL, json=lead_data, timeout=10)
        if response.status_code == 200:
            return True
        else:
            logger.warning(f"Webhook returned status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to send lead to webhook: {e}")
        return False

def sync_csv_to_sheets(csv_path):
    """Reads a CSV and sends every row to the Google Sheets webhook."""
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return
    
    logger.info(f"Syncing {csv_path} to Google Sheets via Webhook...")
    
    count = 0
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if send_lead_to_sheets(row):
                count += 1
            if count % 10 == 0:
                logger.info(f"Synced {count} rows...")
                
    logger.info(f"Sync complete. Total rows synced: {count}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        sync_csv_to_sheets(sys.argv[1])
    else:
        # Default: sync the catastrophic batch
        cat_path = os.path.join(os.path.dirname(__file__), '..', 'leads_manifests', 'CATASTROPHIC_OK_TX_1YR.csv')
        if os.path.exists(cat_path):
            sync_csv_to_sheets(cat_path)
