#!/usr/bin/env python3
"""
Dial roofing companies (B2B) with the Ridgeline / Roof Hunter Pro ElevenLabs agent.

The agent is deployed via:
  python scripts/deploy_ridgeline_elevenlabs_agent.py --create|--update
Prompt: prompts/ridgeline_lead_sales_elevenlabs.md

Input: CSV from an Apollo.io **Organizations** export (or similar). Mapped columns include:
  Company / Organization Name, Company Phone / Organization Phone, City, State,
  optional contact first/last for {{contact_name}}.

Requires:
  ELEVENLABS_API_KEY
  RIDGELINE_ELEVENLABS_AGENT_ID  (default: production sales agent id in deploy script)
  ELEVENLABS_B2B_CALLER_PHONE_NUMBER_ID  — ElevenLabs phone resource id (phnum_...) for outbound SIP

Usage:
  1. Export **Organizations** (or People with org phone) from Apollo as CSV.
  2. Push prompt to ElevenLabs (OK/TX example):
       python scripts/deploy_ridgeline_elevenlabs_agent.py --update \\
         --prompt prompts/ridgeline_ok_tx_territory_sales_elevenlabs.md
  3. Dial (dry-run first):
       PYTHONPATH=src python scripts/dispatch_b2b_roofers_elevenlabs.py \\
         -i ~/Downloads/apollo-export.csv --states OK,TX --limit 5 --dry-run
       PYTHONPATH=src python scripts/dispatch_b2b_roofers_elevenlabs.py \\
         -i ~/Downloads/apollo-export.csv --states OK,TX --limit 50 --sleep 2
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from normalize_lead_phones_e164 import to_us_e164  # noqa: E402

load_dotenv(REPO / ".env")

DEFAULT_AGENT = os.getenv(
    "RIDGELINE_ELEVENLABS_AGENT_ID",
    "agent_9601kq1b8dxkeh6snk5cjf4wb70h",
)
OUTBOUND_URL = "https://api.elevenlabs.io/v1/convai/sip-trunk/outbound-call"

_STATE_TO_ABBR = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "district of columbia": "DC",
}


def state_to_abbr(raw: str) -> str | None:
    s = (raw or "").strip()
    if not s:
        return None
    if len(s) == 2 and s.isalpha():
        return s.upper()
    return _STATE_TO_ABBR.get(s.lower().replace(".", ""))


def _norm_field(s: str) -> str:
    return re.sub(r"\s+", "_", str(s).strip().lower())


def _inv(row: dict) -> dict[str, str]:
    return {_norm_field(k): (str(v).strip() if v is not None else "") for k, v in row.items()}


def _pick(inv: dict[str, str], *candidates: str) -> str:
    for c in candidates:
        v = inv.get(_norm_field(c))
        if v:
            return v
    return ""


def apollo_row_to_b2b(inv: dict[str, str]) -> dict[str, str] | None:
    company = _pick(
        inv,
        "company_name",
        "organization_name",
        "account_name",
        "company",
        "name",
        "organization",
    )
    phone_raw = _pick(
        inv,
        "company_phone",
        "organization_phone",
        "primary_phone",
        "phone",
        "corporate_phone",
        "organization_primary_phone",
        "sanitized_phone",
    )
    city = _pick(inv, "city", "company_city", "organization_city", "headquarters_city")
    state = _pick(inv, "state", "company_state", "organization_state", "headquarters_state")
    fn = _pick(inv, "first_name", "contact_first_name", "primary_contact_first_name")
    ln = _pick(inv, "last_name", "contact_last_name", "primary_contact_last_name")
    title = _pick(
        inv,
        "title",
        "job_title",
        "contact_title",
        "person_title",
        "seniority",
        "headline",
    )

    e164 = to_us_e164(phone_raw)
    if not e164 or not company:
        return None

    contact_name = (f"{fn} {ln}".strip() or company).strip()
    metro = ", ".join(p for p in [city, state] if p)

    return {
        "to_number": e164,
        "company_name": company,
        "contact_name": contact_name,
        "title": title or "",
        "city": city,
        "state": state,
        "metro_area": metro or "your area",
        "agent_name": os.getenv("RIDGELINE_B2B_AGENT_FIRST_NAME", "Alex"),
        "owner_transfer_e164": os.getenv("RIDGELINE_TRANSFER_E164", "+17252241240"),
        "campaign": os.getenv("RIDGELINE_B2B_CAMPAIGN", "apollo_ok_tx_territory_outbound"),
        "lead_tier": os.getenv(
            "RIDGELINE_B2B_LEAD_TIER",
            "storm-verified and scored homeowner leads",
        ),
        "notes": os.getenv(
            "RIDGELINE_B2B_NOTES",
            "Oklahoma and Texas markets; lead packs or exclusive territory where inventory allows.",
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True, help="Apollo org export CSV")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=1.0, help="Seconds between calls")
    ap.add_argument(
        "--states",
        default="",
        help="Comma-separated USPS codes, e.g. OK,TX — only dial rows whose State normalizes into this set (skip others).",
    )
    args = ap.parse_args()

    st_allow: set[str] | None = None
    if args.states.strip():
        st_allow = {s.strip().upper() for s in args.states.split(",") if s.strip()}
    agent_id = os.getenv("RIDGELINE_ELEVENLABS_AGENT_ID", DEFAULT_AGENT).strip()
    ph_id = os.getenv("ELEVENLABS_B2B_CALLER_PHONE_NUMBER_ID", "").strip()

    if not api_key:
        sys.exit("Set ELEVENLABS_API_KEY")
    if not ph_id and not args.dry_run:
        sys.exit(
            "Set ELEVENLABS_B2B_CALLER_PHONE_NUMBER_ID to an ElevenLabs phone number id (phnum_...) "
            "from Conversational AI → Phone numbers."
        )

    rows_out: list[dict[str, str]] = []
    with open(args.input, newline="", encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            b2b = apollo_row_to_b2b(_inv(raw))
            if not b2b:
                continue
            if st_allow:
                ab = state_to_abbr(b2b.get("state") or "")
                if not ab or ab not in st_allow:
                    continue
            rows_out.append(b2b)
            if len(rows_out) >= args.limit:
                break

    print(f"Prepared {len(rows_out)} dialable B2B rows (limit {args.limit}).", file=sys.stderr)

    for i, rv in enumerate(rows_out):
        payload = {
            "agent_id": agent_id,
            "agent_phone_number_id": ph_id,
            "to_number": rv["to_number"],
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "contact_name": rv["contact_name"],
                    "company_name": rv["company_name"],
                    "title": rv["title"],
                    "city": rv["city"],
                    "state": rv["state"],
                    "metro_area": rv["metro_area"],
                    "agent_name": rv["agent_name"],
                    "owner_transfer_e164": rv["owner_transfer_e164"],
                    "campaign": rv["campaign"],
                    "lead_tier": rv["lead_tier"],
                    "notes": rv["notes"],
                }
            },
        }
        print(f"[{i + 1}/{len(rows_out)}] {rv['to_number']} {rv['company_name']}", file=sys.stderr)
        if args.dry_run:
            continue
        r = requests.post(
            OUTBOUND_URL,
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if r.status_code != 200:
            print(f"  ERROR {r.status_code}: {r.text[:500]}", file=sys.stderr)
        time.sleep(max(0.0, args.sleep))

    if args.dry_run:
        print("Dry run — no calls sent. Unset --dry-run after configuring caller phone id.", file=sys.stderr)


if __name__ == "__main__":
    main()
