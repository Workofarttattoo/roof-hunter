import os
import sqlite3
import csv
from datetime import datetime

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, 'leads_manifests', 'authoritative_storms.db')

def export_reformatted_leads():
    """Extracts leads and includes First_Name and customer_name fields."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Select leads that have been marked as notified (or use notified = 0 for the absolute newest)
    # We'll pull the ones that were just processed by cloud_notifier.py (notified=1)
    query = """
    SELECT c.first_name, c.homeowner_name, c.street_address, s.city, s.state, s.magnitude, c.damage_score, c.insurance_company, s.event_date
    FROM contacts c
    JOIN storms s ON c.event_id = s.id
    WHERE c.notified = 1
    ORDER BY c.damage_score DESC
    """
    
    c.execute(query)
    leads = c.fetchall()
    
    if not leads:
        print("[ERROR] No leads found to export.")
        conn.close()
        return
        
    filename = f"ELEVEN_LABS_READY_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    filepath = os.path.join(BASE_DIR, 'leads_manifests', filename)
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        # Add First_Name and customer_name as the first two columns
        writer.writerow(['First_Name', 'customer_name', 'Street Address', 'City', 'State', 'Storm Magnitude', 'AI Damage Score %', 'Likely Insurance', 'Event Date'])
        
        for lead in leads:
            first = lead[0] or "Homeowner"
            full = lead[1] or first
            # Duplicate the info as requested
            row = [first, first] + list(lead[2:])
            writer.writerow(row)
            
    conn.close()
    print(f"[SUCCESS] Exported {len(leads)} leads to {filepath}")
    return filepath

if __name__ == "__main__":
    export_reformatted_leads()
