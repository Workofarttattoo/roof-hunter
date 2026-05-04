import csv
import requests
import json
import os
import time

# Configuration
ORCHESTRATOR_URL = "http://localhost:10000/run_campaign"
CSV_PATH = "leads_manifests/CATASTROPHIC_OK_TX_1YR.csv"
BATCH_SIZE = 50

def dispatch_batches():
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        return

    leads = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Format lead for the Orchestrator's expectation
            # Expects: {"name": ..., "phone": ..., "city": ..., "storm_date": ..., "id": ...}
            leads.append({
                "id": f"CSV_{row.get('phone_number')}",
                "name": row.get('first_name', 'Homeowner'),
                "phone": row.get('phone_number'),
                "city": row.get('city'),
                "storm_date": row.get('hail_date')
            })

    print(f"Total leads loaded from CSV: {len(leads)}")

    for i in range(0, len(leads), BATCH_SIZE):
        batch = leads[i:i+BATCH_SIZE]
        print(f"Dispatching batch {i//BATCH_SIZE + 1} ({len(batch)} leads)...")
        
        try:
            response = requests.post(
                ORCHESTRATOR_URL,
                json={"leads": batch},
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"  Successfully dispatched batch {i//BATCH_SIZE + 1}")
                # print(json.dumps(response.json(), indent=2))
            else:
                print(f"  Error: Orchestrator returned status {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"  Error dispatching batch: {e}")
            
        # Small delay between batches
        if i + BATCH_SIZE < len(leads):
            time.sleep(2)

    print("Dispatch complete.")

if __name__ == "__main__":
    dispatch_batches()
