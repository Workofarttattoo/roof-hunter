import os
import csv
import requests
import json

API_KEY = "db404127b0d540e61df29639d780181f3bd0670c15fbf8333ab3dcaea08b80dd"
ENRICH_URL = "https://api.peopledatalabs.com/v5/person/enrich"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INPUT_CSV = os.path.join(BASE_DIR, 'leads_manifests', 'wichita_falls_batch.csv')
OUTPUT_CSV = os.path.join(BASE_DIR, 'leads_manifests', 'wichita_falls_batch_PDL_ENRICHED.csv')

def process_batch():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: {INPUT_CSV} not found.")
        return

    found_count = 0
    total_count = 0

    with open(INPUT_CSV, 'r') as infile, open(OUTPUT_CSV, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            total_count += 1
            first_name = row.get('first_name', '').strip()
            last_name = row.get('last_name', '').strip()
            address = row.get('property_address', '').strip()
            city = row.get('city', '').strip()
            state = row.get('state', '').strip()

            params = {
                "api_key": API_KEY,
                "first_name": first_name,
                "last_name": last_name,
                "locality": city,
                "region": state,
                "street_address": address
            }
            
            # If name is missing or "Homeowner", we just search by address
            if not first_name or first_name.lower() == "homeowner":
                del params["first_name"]
                del params["last_name"]

            try:
                response = requests.get(ENRICH_URL, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # extract phones
                    phones = data.get('data', {}).get('phone_numbers', [])
                    
                    if isinstance(phones, bool):
                        if phones is True:
                            print(f"[{total_count}] Match Found! But PDL masked the phone numbers (Returned 'True' instead of data). Check your API key permissions.")
                        else:
                            print(f"[{total_count}] No phones found for {first_name} {last_name}")
                    elif phones:
                        # Grab the first mobile if available, else first number
                        mobile = next((p['number'] for p in phones if p.get('type') == 'mobile'), None)
                        best_phone = mobile if mobile else phones[0]['number']
                        
                        # format to E.164 if needed
                        if not best_phone.startswith('+1'):
                            best_phone = f"+1{best_phone.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')}"
                        
                        row['phone_number'] = best_phone
                        found_count += 1
                        print(f"[{total_count}] Match Found! {first_name} {last_name} @ {address} -> {best_phone}")
                    else:
                        print(f"[{total_count}] No phones found for {first_name} {last_name}")
                elif response.status_code == 404:
                    print(f"[{total_count}] Not Found (404) for {first_name} {last_name}")
                else:
                    print(f"[{total_count}] API Error {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f"[{total_count}] Exception: {e}")
                
            writer.writerow(row)

    print(f"\nProcessing Complete. PDL found phones for {found_count} out of {total_count} leads.")
    print(f"Saved enriched data to: {OUTPUT_CSV}")

if __name__ == "__main__":
    process_batch()
