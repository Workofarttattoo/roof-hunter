import csv
import os
import re

from lead_csv_schema import CANONICAL_LEAD_CSV_FIELDS as SCHEMA

MANIFEST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'leads_manifests'))

def clean_phone(phone):
    if not phone:
        return ""
    phone = str(phone).split('x')[0].split('ext')[0]
    digits = ''.join(filter(str.isdigit, phone))
    if "555" in digits:
        return ""
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    return f"+1{digits}" if len(digits) > 7 else ""

def split_name(full_name):
    if not full_name:
        return "", ""
    parts = str(full_name).strip().split(' ', 1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else ""
    return first, last

def get_mapping(headers):
    mapping = {}
    
    # Common variations
    name_vars = ['homeowner_name', 'Owner', 'Homeowner', 'owner_name']
    phone_vars = ['phone_number', 'Phone', 'phone']
    addr_vars = ['street_address', 'Address', 'property_address', 'Verified_Address', 'Original_Address']
    damage_vars = ['damage_score', 'Intensity', 'damage_probability']
    hail_vars = ['hail_size', 'hail_size_in', 'magnitude', 'Hail_Magnitude']
    date_vars = ['hail_date', 'Date', 'Event_Date']
    
    for h in headers:
        if h is None:
            continue
        h_lower = h.lower()
        hk = re.sub(r'\s+', '_', str(h).strip().lower())
        if hk in SCHEMA:
            mapping[hk] = h
            continue
        elif any(v.lower() == h_lower for v in name_vars):
            mapping['full_name'] = h
        elif any(v.lower() == h_lower for v in phone_vars):
            mapping['phone_number'] = h
        elif any(v.lower() == h_lower for v in addr_vars):
            mapping['property_address'] = h
        elif any(v.lower() == h_lower for v in damage_vars):
            mapping['damage_probability'] = h
        elif any(v.lower() == h_lower for v in hail_vars):
            mapping['hail_size'] = h
        elif any(v.lower() == h_lower for v in date_vars):
            mapping['hail_date'] = h
        elif h_lower == 'city':
            mapping['city'] = h
        elif h_lower == 'last_name':
            mapping['last_name'] = h
        elif h_lower == 'state':
            mapping['state'] = h
        elif h_lower == 'zip_code' or h_lower == 'zip':
            mapping['zip_code'] = h

    return mapping

def standardize_file(filename):
    input_path = os.path.join(MANIFEST_DIR, filename)
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    print(f"Standardizing: {filename}")
    
    rows = []
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        mapping = get_mapping(reader.fieldnames)
        
        for row in reader:
            out = {k: "" for k in SCHEMA}
            
            # Name
            if 'first_name' in mapping:
                out['first_name'] = row.get(mapping['first_name'], "")
                out['last_name'] = row.get(mapping['last_name'], "") if 'last_name' in mapping else ""
            elif 'full_name' in mapping:
                first, last = split_name(row.get(mapping['full_name'], ""))
                out['first_name'] = first
                out['last_name'] = last
            
            # Phone
            if 'phone_number' in mapping:
                out['phone_number'] = clean_phone(row.get(mapping['phone_number'], ""))
            
            # Address
            if 'property_address' in mapping:
                out['property_address'] = row.get(mapping['property_address'], "")
            
            # Location
            out['city'] = row.get(mapping.get('city', ''), "")
            out['state'] = row.get(mapping.get('state', ''), "")
            out['zip_code'] = row.get(mapping.get('zip_code', ''), "")
            
            # Storm Info
            out['hail_date'] = row.get(mapping.get('hail_date', ''), "")
            out['hail_size'] = row.get(mapping.get('hail_size', ''), "")
            out['storm_type'] = row.get('storm_type', 'Hail')
            
            # Damage
            dmg = row.get(mapping.get('damage_probability', ''), "0")
            try:
                # Remove non-numeric chars like %
                dmg_clean = re.sub(r'[^\d.]', '', str(dmg))
                out['damage_probability'] = float(dmg_clean) if dmg_clean else 0.0
            except:
                out['damage_probability'] = 0.0
            
            # Forensic Mappings
            try:
                hail = float(out['hail_size'] or 0)
            except:
                hail = 0.0
            
            damage = out['damage_probability']
            
            # structures_hit
            if hail >= 2.0:
                out['structures_hit'] = "Primary roof system and ancillary structures"
            else:
                out['structures_hit'] = "Main roof surface"
                
            # image_findings
            proof = row.get('proof_msg', "")
            if proof and len(proof) > 10:
                out['image_findings'] = proof
            else:
                out['image_findings'] = f"Forensic scan flagged property following {out['storm_type']} event."
                
            # lead_priority
            if damage > 80:
                out['lead_priority'] = "PRIORITY_1_EMERGENCY"
            elif hail >= 1.5 or damage > 30:
                out['lead_priority'] = "PRIORITY_2_LIKELY_DAMAGE"
            else:
                out['lead_priority'] = "PRIORITY_3_LOW_INTENT"
            
            # Vetting Layer
            is_valid = True
            if "DEEP SEARCH" in out['first_name'].upper() or "DEEP SEARCH" in out['last_name'].upper():
                is_valid = False
            if not out['phone_number'] or len(out['phone_number']) < 10:
                is_valid = False
            if not out['property_address'] or "STORM IMPACT" in out['property_address'].upper():
                is_valid = False
                
            if is_valid:
                rows.append(out)

    # Overwrite original
    with open(input_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=SCHEMA)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Done standardizing {filename}. Total rows: {len(rows)}")

if __name__ == "__main__":
    files_to_standardize = [
        'oklahoma_call_ready_leads.csv',
        'texas_call_ready_leads.csv',
        'wichita_falls_batch.csv',
        'alpha_leads_VERIFIED.csv',
        'ROOF_HUNTER_MASTER_MANIFEST_2026.csv'
    ]
    
    for f in files_to_standardize:
        standardize_file(f)
