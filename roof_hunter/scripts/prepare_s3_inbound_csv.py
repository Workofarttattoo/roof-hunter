#!/usr/bin/env python3
"""
Normalize any lead CSV to the canonical column layout before uploading to S3
(so aws_lead_sync + dialers always see the same categories).

  PYTHONPATH=src python scripts/prepare_s3_inbound_csv.py -i messy.csv -o leads_manifests/s3_ready.csv

Then: aws s3 cp leads_manifests/s3_ready.csv s3://$AWS_LEADS_BUCKET/$AWS_LEADS_OBJECT_KEY
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from lead_csv_schema import write_canonical_leads_csv  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Rewrite inbound lead CSV to canonical Ridgeline headers.")
    ap.add_argument("-i", "--input", required=True, help="Source CSV (any headers)")
    ap.add_argument("-o", "--output", default="", help="Destination CSV (default: stdout)")
    ap.add_argument(
        "--extra",
        nargs="*",
        default=[],
        help="Additional columns to preserve after canonical block (e.g. apollo_id notes)",
    )
    args = ap.parse_args()

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        rows = [dict(r) for r in csv.DictReader(f)]

    dest = open(args.output, "w", newline="", encoding="utf-8") if args.output else sys.stdout
    try:
        n = write_canonical_leads_csv(dest, rows, extras_headers=list(args.extra))
    finally:
        if args.output:
            dest.close()

    if args.output:
        print(f"Wrote {n} rows → {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
