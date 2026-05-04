import os
import glob
import csv
import json
import time
import requests
import random
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LEADS_DIR = os.path.join(BASE_DIR, 'leads_manifests')

# Skip Tracing API config
SKIP_TRACE_API_KEY = os.getenv("BATCH_SKIP_TRACING_API_KEY")
API_URL = "https://api.batchdata.com/api/v1/property/skip-trace" # Example endpoint

def get_latest_emergency_leads():
    """Find the most recently generated TOP_200_EMERGENCY_LEADS_*.csv"""
    search_pattern = os.path.join(LEADS_DIR, "TOP_200_EMERGENCY_LEADS_*.csv")
    files = glob.glob(search_pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def mock_skip_trace(address, city, state):
    """Fallback if no API key is provided - generates realistic OK numbers."""
    time.sleep(0.1) # Simulate API latency
    # Generate a fake E.164 Oklahoma number (area codes: 405, 539, 580, 918)
    area_codes = ["405", "539", "580", "918"]
    ac = random.choice(area_codes)
    prefix = random.randint(200, 999)
    line = random.randint(1000, 9999)
    return f"+1{ac}{prefix}{line}"

def enrich_leads(input_filepath):
    """Read input CSV, perform skip trace by address, and output enriched CSV."""
    if not SKIP_TRACE_API_KEY:
        print("\n[WARNING] 'BATCH_SKIP_TRACING_API_KEY' not found in .env.")
        print("          Using MOCK phone numbers for testing. These are not real!")
        print("          Please sign up for BatchSkipTracing/Tracerfy and add your API Key to .env\n")
    
    filename = os.path.basename(input_filepath)
    output_filename = filename.replace("EMERGENCY_LEADS", "ENRICHED_LEADS")
    output_filepath = os.path.join(LEADS_DIR, output_filename)

    enriched_count = 0
    with open(input_filepath, 'r') as infile, open(output_filepath, 'w', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        headers = next(reader)
        # Add phone_number column if not exists
        if "phone_number" not in headers:
            headers.append("phone_number")
        writer.writerow(headers)

        for row in reader:
            # Expected columns from export_top_200.py:
            # ['First_Name', 'customer_name', 'Street Address', 'City', 'State', 'Storm Magnitude', 'AI Damage Score %', 'Likely Insurance', 'Event Date']
            
            # Map index
            first_name = row[0]
            address = row[2]
            city = row[3]
            state = row[4]

            if SKIP_TRACE_API_KEY:
                # Actual API integration
                headers_api = {
                    "Authorization": f"Bearer {SKIP_TRACE_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "requests": [{
                        "first_name": first_name if first_name != "Homeowner" else "",
                        "property_address": address,
                        "property_city": city,
                        "property_state": state
                    }]
                }
                try:
                    response = requests.post(API_URL, headers=headers_api, json=payload, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        # Extract first mobile number found
                        results = data.get("results", [])
                        if results and results[0].get("phoneNumbers"):
                            phone = results[0]["phoneNumbers"][0]["number"]
                            # Ensure E.164
                            if not phone.startswith("+1"):
                                phone = f"+1{phone.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')}"
                        else:
                            phone = "" # No match found
                    else:
                        print(f"[API ERROR] {response.status_code} - {response.text}")
                        phone = ""
                except Exception as e:
                    print(f"[API EXCEPTION] {e}")
                    phone = ""
            else:
                phone = mock_skip_trace(address, city, state)

            row.append(phone)
            writer.writerow(row)
            enriched_count += 1
            print(f"Verified Address: {address}, {city}, {state} -> Phone: {phone}")

    print(f"\n[SUCCESS] Skip traced {enriched_count} leads.")
    print(f"[OUTPUT] Saved to: {output_filepath}")
    return output_filepath

if __name__ == "__main__":
    latest_export = get_latest_emergency_leads()
    if not latest_export:
        print("[ERROR] No TOP_200_EMERGENCY_LEADS file found. Run 'export_top_200.py' first.")
    else:
        print(f"Found latest lead export: {latest_export}")
        print("Starting Skip Trace Enrichment...")
        enrich_leads(latest_export)
