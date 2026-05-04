import os
import sqlite3
import csv
from datetime import datetime

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, 'leads_manifests', 'authoritative_storms.db')

# Targeted High-Value Zip Codes (Edmond & Nichols Hills areas)
RICH_ZIPS = ['73034', '73116', '73120', '73013', '73003']

def export_prioritized_ok_leads():
    """Extracts OK leads >= 60% damage, prioritizing Edmond and affluent zip codes."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Priority 1: Edmond & Nichols Hills (Top Affluence)
    # Priority 2: Other OK areas with high damage
    query = """
    SELECT c.phone_number, c.first_name, c.homeowner_name, c.street_address, s.city, s.state, c.zip_code, s.magnitude, c.damage_score, c.insurance_company, s.event_date
    FROM contacts c
    JOIN storms s ON c.event_id = s.id
    WHERE s.state LIKE '%OK%' 
    AND c.damage_score >= 60.0
    ORDER BY 
        CASE WHEN c.zip_code IN ('73034', '73116', '73120', '73013', '73003') THEN 0 ELSE 1 END,
        c.damage_score DESC
    LIMIT 1000
    """
    
    c.execute(query)
    leads = c.fetchall()
    
    if not leads:
        print("[ERROR] No high-damage leads found in Oklahoma.")
        conn.close()
        return
        
    filename = f"OKLAHOMA_CATASTROPHIC_RICH_BATCH_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    filepath = os.path.join(BASE_DIR, 'leads_manifests', filename)
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        # ElevenLabs Header
        writer.writerow(['phone_number', 'First_Name', 'customer_name', 'Street Address', 'City', 'State', 'Zip', 'Storm Magnitude', 'AI Damage Score %', 'Likely Insurance', 'Event Date'])
        
        for lead in leads:
            phone = lead[0] or ""
            if not phone: continue
            
            first = lead[1] or lead[2] or "Homeowner"
            if " " in first: first = first.split(" ")[0]
            
            row = [phone, first, first] + list(lead[3:])
            writer.writerow(row)
            
    conn.close()
    print(f"[SUCCESS] Exported {len(leads)} prioritized OK leads to {filepath}")
    return filepath

if __name__ == "__main__":
    export_prioritized_ok_leads()
