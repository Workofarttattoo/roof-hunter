"""AERO-COMMAND: Triple-Phase Target Export (OK/TX)."""

import sqlite3
import csv
import os
from datetime import datetime, timedelta

DB_PATH = 'leads_manifests/authoritative_storms.db'
OUTPUT_CSV = 'AERO_COMMAND_OK_TX_TARGETS.csv'

def export_targets():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Define Regions
    # Note: In a real query, we'd use lat/lon bounding boxes or county names.
    # Here we filter for OK and TX leads.
    
    query = """
        SELECT 
            c.street_address as address, 
            c.homeowner_name as owner, 
            c.phone_number as phone,
            c.damage_score as damage_prob,
            c.forensic_tag as storm_tag,
            s.event_type as intensity,
            s.event_date as strike_date
        FROM contacts c
        JOIN storms s ON c.event_id = s.id
        WHERE (c.street_address LIKE '%OK%' OR c.street_address LIKE '%TX%')
        AND c.phone_number IS NOT NULL
        ORDER BY c.damage_score DESC
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    fieldnames = ['address', 'owner', 'phone', 'damage_prob', 'storm_tag', 'intensity', 'strike_date', 'dispatch_status']
    
    with open(OUTPUT_CSV, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        count = 0
        for row in rows:
            # Simulate date filtering for demo (Yesterday/Today/Tomorrow)
            writer.writerow({
                'address': row['address'],
                'owner': row['owner'],
                'phone': row['phone'],
                'damage_prob': f"{float(row['damage_prob']) * 100:.1f}%",
                'storm_tag': row['storm_tag'],
                'intensity': row['intensity'],
                'strike_date': row['strike_date'],
                'dispatch_status': 'QUEUED_FOR_BLAND_AI'
            })
            count += 1
            
    conn.close()
    return count

if __name__ == "__main__":
    count = export_targets()
    print(f"Manifest Exported: {count} High-ROI targets secured in {OUTPUT_CSV}")
