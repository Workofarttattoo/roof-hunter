#!/usr/bin/env python3
"""
Enrich homeowner phones (TX + OK) via EnformionGO API — Contact Enrich + Address ID fallback.

Prerequisites (from https://api.enformion.com — use Access Profile **Name** + **Password**):

  export ENFORMION_AP_NAME='your-profile-key-name'
  export ENFORMION_AP_PASSWORD='your-profile-password'
  Optional: ENFORMION_API_BASE=https://devapi.enformion.com

Selection:
  - States: Oklahoma / Texas (DB values OK, OKLAHOMA, TX, TEXAS)
  - damage_score between --min-damage and --max-damage (default 60–100)
  - Rows that still need a real phone (empty, short, 555, UNVERIFIED, etc.)
  - Priority: highest median_home_value, then highest damage_score

Contact Enrich request body matches Enformion docs (First/Middle/Last, Address addressLine1/2,
Phone, Email, Dob, Age). At least two search criteria are required (Name, Phone, Address, Email);
the script counts categories and skips ContactEnrich if only one is present (AddressID fallback only).

One HTTP request per contact (--sleep between calls).

Usage:
  python3 scripts/enrich_contacts_enformion.py --dry-run --limit 10
  python3 scripts/enrich_contacts_enformion.py --limit 100 --sleep 1.5

Docs: https://enformiongo.readme.io/reference/contact-enrichment
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from normalize_lead_phones_e164 import to_us_e164  # noqa: E402

load_dotenv(REPO / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("enformion_enrich")

DEFAULT_DB = REPO / "leads_manifests" / "authoritative_storms.db"

_FULL_STATE = {
    "OKLAHOMA": "OK",
    "TEXAS": "TX",
    "NEBRASKA": "NE",
    "OK": "OK",
    "TX": "TX",
    "NE": "NE",
}


def state_abbr(raw: str) -> str:
    s = (raw or "").strip().upper()
    return _FULL_STATE.get(s, s[:2] if len(s) == 2 else s)


def needs_enrichment(phone: str | None) -> bool:
    if phone is None or not str(phone).strip():
        return True
    u = str(phone).upper().strip()
    if u.startswith("UNVERIFIED") or "DATABROKER" in u or "PROTECTED" in u:
        return True
    d = re.sub(r"\D", "", str(phone))
    if len(d) < 10:
        return True
    nat = d[-10:]
    if nat[:3] == "555" or nat[3:6] == "555":
        return True
    return False


def split_name(full: str | None) -> tuple[str, str]:
    """First + last only (legacy). Prefer split_name_full for Contact Enrich."""
    f, _m, l = split_name_full(full)
    return f, l


def split_name_full(full: str | None) -> tuple[str, str, str]:
    """
    First, middle, last — matches Enformion examples (e.g. John / T / Lawrence).
    """
    full = (full or "").strip()
    if not full or full.upper() in ("HOMEOWNER", "DEEP SEARCH REQ", "OWNER"):
        return "", "", ""
    parts = full.split()
    if len(parts) == 1:
        return parts[0], "", ""
    if len(parts) == 2:
        return parts[0], "", parts[1]
    return parts[0], parts[1], parts[-1]


def phone_for_enrich(raw: str | None) -> str:
    """Digits-only hint for API (partial OK as second search criterion)."""
    if raw is None or not str(raw).strip():
        return ""
    d = re.sub(r"\D", "", str(raw))
    if len(d) >= 10:
        return d[-10:]
    if len(d) >= 7:
        return d
    return ""


def email_for_enrich(raw: str | None) -> str:
    s = (raw or "").strip()
    if "@" in s and len(s) > 4:
        return s
    return ""


def address_line2(city: str, state: str, zipcode: str | None) -> str:
    st = state_abbr(state)
    z = (zipcode or "").strip()
    tail = f"{st} {z}".strip() if z else st
    parts = [(city or "").strip(), tail]
    return ", ".join(p for p in parts if p)


def contact_enrich_identifier_counts(
    first: str,
    middle: str,
    last: str,
    line1: str,
    line2: str,
    phone: str,
    email: str,
) -> tuple[int, dict[str, bool]]:
    """Enformion requires ≥2 of: Name, Phone, Address, Email."""
    name_ok = bool((first or "").strip() or (last or "").strip() or (middle or "").strip())
    phone_ok = bool((phone or "").strip())
    email_ok = bool((email or "").strip())
    addr_ok = bool((line1 or "").strip()) and bool((line2 or "").strip())
    flags = {"name": name_ok, "phone": phone_ok, "email": email_ok, "address": addr_ok}
    return sum(flags.values()), flags


def build_contact_enrich_body(
    first: str,
    middle: str,
    last: str,
    line1: str,
    city: str,
    state: str,
    zipcode: str | None,
    *,
    phone: str = "",
    email: str = "",
) -> dict[str, Any]:
    """
    Body aligned with Enformion Contact Enrichment docs (search criteria).
    """
    line2 = address_line2(city, state, zipcode)
    return {
        "FirstName": (first or "").strip(),
        "MiddleName": (middle or "").strip(),
        "LastName": (last or "").strip(),
        "Dob": "",
        "Age": 0,
        "Address": {
            "addressLine1": (line1 or "").strip(),
            "addressLine2": line2,
        },
        "Phone": (phone or "").strip(),
        "Email": (email or "").strip(),
    }


def build_contact_enrich_body_if_eligible(
    owner: str | None,
    street: str | None,
    city: str | None,
    state: str | None,
    zipcode: str | None,
    existing_phone: str | None,
    existing_email: str | None,
) -> tuple[dict[str, Any] | None, dict[str, bool], int]:
    """
    Build Contact Enrich JSON only if at least two of Name / Phone / Address / Email
    are present per API rules. Returns (body or None, flags, criterion_count).
    """
    fn, mn, ln = split_name_full(owner)
    line1 = (street or "").strip()
    line2 = address_line2(city or "", state or "", zipcode)
    ph = phone_for_enrich(existing_phone)
    em = email_for_enrich(existing_email)
    n, flags = contact_enrich_identifier_counts(fn, mn, ln, line1, line2, ph, em)
    if n < 2:
        return None, flags, n
    body = build_contact_enrich_body(fn, mn, ln, line1, city or "", state or "", zipcode, phone=ph, email=em)
    return body, flags, n


def _gather(obj: Any, out: list[Any]) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            _gather(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _gather(v, out)
    else:
        out.append(obj)


def extract_strings(obj: Any) -> list[str]:
    acc: list[Any] = []
    _gather(obj, acc)
    return [str(x).strip() for x in acc if isinstance(x, (str, int)) and str(x).strip()]


def extract_phones_from_enformion(obj: Any) -> list[str]:
    phones: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = str(k).lower()
            if any(x in lk for x in ("phone", "mobile", "wireless", "tel")) and v is not None:
                for s in extract_strings(v):
                    e = to_us_e164(s)
                    if e:
                        phones.add(e)
    for s in extract_strings(obj):
        e = to_us_e164(s)
        if e:
            nat = re.sub(r"\D", "", e)[-10:]
            if nat[:3] == "555" or nat[3:6] == "555":
                continue
            phones.add(e)
    return sorted(phones)


def extract_email_from_enformion(obj: Any) -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if "email" in str(k).lower() and isinstance(v, str) and "@" in v:
                return v.strip()
            sub = extract_email_from_enformion(v)
            if sub:
                return sub
    elif isinstance(obj, list):
        for v in obj:
            sub = extract_email_from_enformion(v)
            if sub:
                return sub
    return None


def enformion_post(
    base: str,
    path: str,
    search_type: str,
    body: dict[str, Any],
    ap_name: str,
    ap_password: str,
) -> dict[str, Any] | None:
    url = base.rstrip("/") + "/" + path.lstrip("/")
    headers = {
        "Content-Type": "application/json",
        "galaxy-ap-name": ap_name,
        "galaxy-ap-password": ap_password,
        "galaxy-search-type": search_type,
    }
    ct = os.getenv("ENFORMION_CLIENT_TYPE", "").strip()
    if ct:
        headers["galaxy-client-type"] = ct
    try:
        r = requests.post(url, headers=headers, json=body, timeout=90)
    except requests.RequestException as e:
        logger.warning("HTTP error: %s", e)
        return None
    rid = (r.headers.get("X-GSE-RequestId") or "").strip()
    if r.status_code == 404 and not (r.text or "").strip():
        logger.warning(
            "HTTP 404 (no body) %s requestId=%s — profile may not be entitled to this "
            "product on this host, or routing differs. Try Keys tab at api.enformion.com; "
            "include requestId when contacting supportgo@enformion.com.",
            path,
            rid or "(none)",
        )
        return None
    try:
        return r.json()
    except Exception:
        logger.warning(
            "Non-JSON response %s %s requestId=%s body=%s",
            path,
            r.status_code,
            rid or "(none)",
            (r.text or "")[:300],
        )
        return None


def pick_best_phone(phones: list[str]) -> str | None:
    for p in phones:
        nat = re.sub(r"\D", "", p)[-10:]
        if nat[3:6] == "555":
            continue
        return p
    return None


def load_rows(
    conn: sqlite3.Connection,
    *,
    limit: int,
    min_dmg: float,
    max_dmg: float,
    state_filter: tuple[str, ...],
    state_sql_placeholders: str,
) -> list[tuple]:
    cur = conn.cursor()
    sql = f"""
        SELECT c.id, c.street_address, c.phone_number, c.homeowner_name, c.email,
               s.city, s.state, s.zipcode, c.damage_score, s.median_home_value
        FROM contacts c
        JOIN storms s ON c.event_id = s.id
        WHERE UPPER(TRIM(s.state)) IN ({state_sql_placeholders})
          AND c.damage_score IS NOT NULL
          AND c.damage_score >= ?
          AND c.damage_score <= ?
        ORDER BY COALESCE(s.median_home_value, 0) DESC,
                 COALESCE(c.damage_score, 0) DESC,
                 c.id ASC
        """
    cur.execute(sql, (*state_filter, min_dmg, max_dmg))
    out: list[tuple] = []
    for row in cur.fetchall():
        if needs_enrichment(row[2]):
            out.append(row)
        if len(out) >= limit:
            break
    return out


def build_address_id_body(
    line1: str,
    city: str,
    state: str,
    zipcode: str | None,
) -> dict[str, Any]:
    line2 = address_line2(city, state, zipcode)
    return {
        "addressLine1": (line1 or "").strip(),
        "addressLine2": line2,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Enformion TX/OK phone enrichment (damage tier)")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--min-damage", type=float, default=60.0)
    ap.add_argument("--max-damage", type=float, default=100.0)
    ap.add_argument("--sleep", type=float, default=1.5)
    ap.add_argument(
        "--states",
        default="OK,TX",
        help="Comma-separated: OK, TX, NE (full DB names OKLAHOMA,TEXAS,NEBRASKA also matched)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Load queue and print samples only; no API calls.",
    )
    args = ap.parse_args()

    api_base = (os.getenv("ENFORMION_API_BASE") or "https://devapi.enformion.com").strip().rstrip("/")
    ap_name = (os.getenv("ENFORMION_AP_NAME") or "").strip()
    ap_pass = (os.getenv("ENFORMION_AP_PASSWORD") or "").strip()

    if not ap_name or not ap_pass:
        if args.dry_run:
            logger.warning("Missing credentials — dry-run queue only.")
        else:
            logger.error(
                "Set ENFORMION_AP_NAME and ENFORMION_AP_PASSWORD (Access Profile from api.enformion.com)."
            )
            sys.exit(1)

    codes = {s.strip().upper() for s in args.states.split(",") if s.strip()}
    expand = set()
    for c in codes:
        if c in ("OK", "OKLAHOMA"):
            expand.add("OK")
            expand.add("OKLAHOMA")
        elif c in ("TX", "TEXAS"):
            expand.add("TX")
            expand.add("TEXAS")
        elif c in ("NE", "NEBRASKA"):
            expand.add("NE")
            expand.add("NEBRASKA")
        else:
            expand.add(c)
    placeholders = ",".join("?" * len(expand))
    state_tuple = tuple(sorted(expand))

    db_path = args.db.resolve()
    conn = sqlite3.connect(str(db_path), timeout=60)
    rows = load_rows(
        conn,
        limit=args.limit,
        min_dmg=args.min_damage,
        max_dmg=args.max_damage,
        state_filter=state_tuple,
        state_sql_placeholders=placeholders,
    )
    conn.close()

    if not rows:
        logger.info("No matching contacts need enrichment (check damage band and states).")
        return

    logger.info(
        "Queued %s contacts (states=%s, damage %.0f–%.0f; sort: median_home_value then damage).",
        len(rows),
        ",".join(sorted(expand)),
        args.min_damage,
        args.max_damage,
    )
    for r in rows[:5]:
        logger.info(" sample id=%s mhv=%s dmg=%s %s, %s", r[0], r[9], r[8], r[1], r[5])

    if args.dry_run or not ap_name or not ap_pass:
        logger.info("Dry run — no API calls.")
        return

    updated = 0
    noop = 0
    conn = sqlite3.connect(str(db_path), timeout=60)
    cur = conn.cursor()
    try:
        for i, row in enumerate(rows, start=1):
            cid, street, _ph, owner, email, city, state, zipc, dmg, mhv = row
            data: dict[str, Any] | None = None

            body, _flags, crit_n = build_contact_enrich_body_if_eligible(
                owner, street, city, state, zipc, _ph, email
            )
            if body is None:
                logger.info(
                    "[%s/%s] ContactEnrich skipped id=%s (%s criteria %s — need ≥2 of name/phone/address/email)",
                    i,
                    len(rows),
                    cid,
                    crit_n,
                    _flags,
                )
            if body is not None:
                a = body.get("Address") or {}
                logger.info(
                    "[%s/%s] ContactEnrich id=%s %s %s | %s | phone=%s email=%s",
                    i,
                    len(rows),
                    cid,
                    body.get("FirstName"),
                    body.get("LastName"),
                    (a.get("addressLine1") or "")[:48],
                    "yes" if (body.get("Phone") or "").strip() else "no",
                    "yes" if (body.get("Email") or "").strip() else "no",
                )
                data = enformion_post(
                    api_base,
                    "ContactEnrich",
                    "DevAPIContactEnrich",
                    body,
                    ap_name,
                    ap_pass,
                )

            if not data or not isinstance(data, dict) or data.get("isError"):
                if data and isinstance(data, dict) and data.get("isError"):
                    err = (data.get("error") or {}).get("message") or data.get("error")
                    logger.info("  ContactEnrich error: %s", err)
                body_ad = build_address_id_body(street or "", city or "", state or "", zipc)
                logger.info("[%s/%s] AddressID fallback id=%s", i, len(rows), cid)
                data = enformion_post(
                    api_base,
                    "AddressID",
                    "DevAPIAddressID",
                    body_ad,
                    ap_name,
                    ap_pass,
                )

            if not data or not isinstance(data, dict) or data.get("isError"):
                if data and isinstance(data, dict) and data.get("isError"):
                    err = (data.get("error") or {}).get("message") or data.get("error")
                    logger.info("  AddressID error: %s", err)
                noop += 1
                time.sleep(max(0.0, args.sleep))
                continue

            phones = extract_phones_from_enformion(data)
            best = pick_best_phone(phones)
            new_email = extract_email_from_enformion(data) if not email else None

            if not best:
                logger.info("  no phone in response")
                noop += 1
                time.sleep(max(0.0, args.sleep))
                continue

            set_email = (email or "").strip()
            if new_email:
                set_email = new_email
            cur.execute(
                """
                UPDATE contacts
                SET phone_number = ?, email = ?, status = 'ENFORMION_ENRICH'
                WHERE id = ?
                """,
                (best, set_email or email or "", cid),
            )
            conn.commit()
            updated += 1
            logger.info("  -> %s", best)
            time.sleep(max(0.0, args.sleep))
    finally:
        conn.close()

    logger.info("Done. updated=%s no_phone=%s", updated, noop)


if __name__ == "__main__":
    main()
