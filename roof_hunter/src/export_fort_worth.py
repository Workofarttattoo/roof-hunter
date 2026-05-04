import os
import sqlite3
import csv
from datetime import datetime

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, 'leads_manifests', 'authoritative_storms.db')

def export_fort_worth_leads():
    """Extracts leads specifically from Fort Worth for targeted outreach."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Query for Fort Worth leads, sorted by damage
    query = """
    SELECT c.first_name, c.homeowner_name, c.street_address, s.city, s.state, s.magnitude, c.damage_score, c.insurance_company, s.event_date
    FROM contacts c
    JOIN storms s ON c.event_id = s.id
    WHERE s.city LIKE '%Fort Worth%'
    ORDER BY c.damage_score DESC
    LIMIT 500
    """
    
    c.execute(query)
    leads = c.fetchall()
    
    if not leads:
        print("[ERROR] No leads found in Fort Worth.")
        conn.close()
        return
        
    filename = f"FORT_WORTH_TARGET_BATCH_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    filepath = os.path.join(BASE_DIR, 'leads_manifests', filename)
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        # ElevenLabs Ready Header
        writer.writerow(['First_Name', 'customer_name', 'Street Address', 'City', 'State', 'Storm Magnitude', 'AI Damage Score %', 'Likely Insurance', 'Event Date'])
        
        for lead in leads:
            first = lead[0] or lead[1] or "Homeowner"
            if " " in first:
                first = first.split(" ")[0]
                
            row = [first, first] + list(lead[2:])
            writer.writerow(row)
            
    conn.close()
    print(f"[SUCCESS] Exported {len(leads)} Fort Worth leads to {filepath}")
    return filepath

if __name__ == "__main__":
    export_fort_worth_leads()
