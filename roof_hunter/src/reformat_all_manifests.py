import os
import csv
import logging

from lead_csv_schema import CANONICAL_LEAD_CSV_FIELDS, coerce_lead_row, is_preserved_extra_column

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MANIFEST_DIR = os.path.join(BASE_DIR, 'leads_manifests')

def reformat_csv(file_path):
    if not file_path.endswith('.csv'): return
    
    logger.info(f"Reformatting: {os.path.basename(file_path)}")
    
    rows = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            fieldnames_in = list(reader.fieldnames or [])
            extra_cols = [h for h in fieldnames_in if is_preserved_extra_column(h)]
            out_fieldnames = list(CANONICAL_LEAD_CSV_FIELDS) + extra_cols
            for row in reader:
                base = coerce_lead_row(row or {})
                merged = {**base}
                for h in extra_cols:
                    merged[h] = (row or {}).get(h, "")
                rows.append(merged)
        
        # Write back with the canonical schema (includes hail_size for upload validators)
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=out_fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            
    except Exception as e:
        logger.error(f"Failed to reformat {file_path}: {e}")

def reformat_all():
    for filename in os.listdir(MANIFEST_DIR):
        if filename.endswith('.csv'):
            reformat_csv(os.path.join(MANIFEST_DIR, filename))
    logger.info("🏁 All manifests reformatted.")

if __name__ == "__main__":
    reformat_all()
