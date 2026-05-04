import os
import sqlite3
import csv
from datetime import datetime

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, 'leads_manifests', 'authoritative_storms.db')

def export_premium_200_leads():
    """Extracts top 200 leads from last 30 days with >= 60% damage."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Query for Top 200, 60%+, Last 30 Days
    query = """
    SELECT c.first_name, c.homeowner_name, c.street_address, s.city, s.state, s.magnitude, c.damage_score, c.insurance_company, s.event_date
    FROM contacts c
    JOIN storms s ON c.event_id = s.id
    WHERE c.damage_score >= 60.0 
    AND s.event_date >= date('now', '-30 days')
    ORDER BY c.damage_score DESC
    LIMIT 200
    """
    
    c.execute(query)
    leads = c.fetchall()
    
    if not leads:
        print("[ERROR] No high-damage leads found in the last 30 days.")
        conn.close()
        return
        
    filename = f"TOP_200_EMERGENCY_LEADS_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    filepath = os.path.join(BASE_DIR, 'leads_manifests', filename)
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        # Standard ElevenLabs Header with First_Name and customer_name duplicated
        writer.writerow(['First_Name', 'customer_name', 'Street Address', 'City', 'State', 'Storm Magnitude', 'AI Damage Score %', 'Likely Insurance', 'Event Date'])
        
        for lead in leads:
            first = lead[0] or lead[1] or "Homeowner"
            # Normalize first name if it contains full name
            if " " in first:
                first = first.split(" ")[0]
                
            row = [first, first] + list(lead[2:])
            writer.writerow(row)
            
    conn.close()
    print(f"[SUCCESS] Exported {len(leads)} premium leads to {filepath}")
    return filepath

if __name__ == "__main__":
    export_premium_200_leads()
