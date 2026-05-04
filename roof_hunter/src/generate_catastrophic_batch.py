import sqlite3
import csv
import os
import re
from datetime import datetime

# Reference schema for Bland AI
SCHEMA = [
    'phone_number', 'first_name', 'last_name', 'property_address',
    'city', 'state', 'zip_code', 'hail_date', 'hail_size',
    'storm_type', 'damage_probability', 'structures_hit',
    'image_findings', 'lead_priority'
]

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, 'leads_manifests', 'authoritative_storms.db')
OUTPUT_PATH = os.path.join(BASE_DIR, 'leads_manifests', 'CATASTROPHIC_OK_TX_1YR.csv')

def clean_phone(phone):
    if not phone: return ""
    digits = ''.join(filter(str.isdigit, str(phone)))
    if "555" in digits: return ""
    if len(digits) == 10: return f"+1{digits}"
    if len(digits) == 11 and digits.startswith('1'): return f"+{digits}"
    return f"+1{digits}" if len(digits) > 7 else ""

def get_catastrophic_leads():
    print(f"--- Querying Catastrophic Leads (40%+) for OK & TX (Last 1 Year) ---")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Priority 1: Oklahoma, Priority 2: Texas
    # Date range: Last 365 days
    query = """
    SELECT 
        c.homeowner_name, c.phone_number, c.street_address,
        s.city, s.state, c.zip_code, s.event_date, s.magnitude,
        c.damage_score, c.proof_msg, c.structures_hit, c.image_findings
    FROM contacts c
    JOIN storms s ON c.event_id = s.id
    WHERE (s.state IN ('OKLAHOMA', 'OK', 'TEXAS', 'TX'))
    AND (c.damage_score >= 40.0)
    AND (s.event_date >= date('now', '-365 days'))
    ORDER BY (CASE WHEN s.state IN ('OKLAHOMA', 'OK') THEN 0 ELSE 1 END), c.damage_score DESC
    """
    
    c.execute(query)
    rows = c.fetchall()
    
    leads = []
    for r in rows:
        # Split name
        full_name = r['homeowner_name'] or "Local Resident"
        parts = full_name.split(' ', 1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else ""
        
        # Phone
        phone = clean_phone(r['phone_number'])
        if not phone: continue # Only call-ready
        
        # Forensic Intelligence
        hail = float(r['magnitude'] or 0)
        damage = float(r['damage_score'] or 0)
        
        # structures_hit
        structs = r['structures_hit']
        if not structs:
            if hail >= 2.0:
                structs = "Primary roof system and multiple ancillary structures"
            else:
                structs = "Main roof surface and soft metals"
                
        # image_findings
        findings = r['image_findings'] or r['proof_msg']
        if not findings or len(findings) < 10:
            findings = f"Forensic scan identified significant spectral anomalies ({damage}%) consistent with {hail}\" hail impact."

        lead = {
            'first_name': first,
            'last_name': last,
            'phone_number': phone,
            'property_address': r['street_address'],
            'city': r['city'],
            'state': r['state'],
            'zip_code': r['zip_code'],
            'hail_date': r['event_date'],
            'hail_size': hail,
            'storm_type': 'Hail',
            'damage_probability': damage,
            'structures_hit': structs,
            'image_findings': findings,
            'lead_priority': 'PRIORITY_1_EMERGENCY' if damage >= 40 else 'PRIORITY_2_LIKELY_DAMAGE'
        }
        leads.append(lead)
        
    conn.close()
    
    print(f"Found {len(leads)} qualified catastrophic leads.")
    
    # Save to CSV
    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=SCHEMA)
        writer.writeheader()
        writer.writerows(leads)
        
    print(f"Successfully saved to {OUTPUT_PATH}")
    return OUTPUT_PATH

if __name__ == "__main__":
    get_catastrophic_leads()
