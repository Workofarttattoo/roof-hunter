#!/usr/bin/env python3
"""
Sequential skip-trace via RentCast property API (free developer tier — low monthly cap).

Use case: contacts in OK / TX / NE that still have placeholder or 555-style phones.
Priority order (one HTTP request at a time):
  1) Edmond, OK — highest damage_score / median_home_value first
  2) Rest of Oklahoma — same ordering
  3) Texas — same ordering (proxy “high value” = damage + median_home_value)
  4) Nebraska — same ordering

Requires:
  RENTCAST_API_KEY in .env (see https://developers.rentcast.io — free tier is ~50 calls/mo; plan upgrades for volume)

Usage (repo root):
  python3 scripts/skip_trace_rentcast_geo.py --dry-run --limit 5
  python3 scripts/skip_trace_rentcast_geo.py --sleep 2.5 --limit 40

Phone is taken from any plausible field in the JSON (owner.*phone*, nested strings, 10-digit patterns).
Only writes numbers that pass NANP via to_us_e164 and are not 555 placeholders.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("rentcast_skip")

DEFAULT_DB = REPO / "leads_manifests" / "authoritative_storms.db"
RENTCAST_URL = "https://api.rentcast.io/v1/properties"

_DIGIT_RUN = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?[2-9]\d{2}\)?[-.\s]?)(?:[2-9]\d{2}|\d{3})[-.\s]?\d{4}\b")
_TEN_DIG = re.compile(r"\d{10}")


def _norm_state(state_raw: str) -> str:
    s = (state_raw or "").strip().upper()
    if s in ("OK", "OKLAHOMA"):
        return "OK_GROUP"
    if s in ("TX", "TEXAS"):
        return "TX_GROUP"
    if s in ("NE", "NEBRASKA"):
        return "NE_GROUP"
    return "OTHER"


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


def _gather_strings(obj: Any, out: list[str]) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            _gather_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _gather_strings(v, out)
    elif isinstance(obj, str) and obj.strip():
        out.append(obj.strip())


def extract_phones_from_rentcast_payload(payload: Any) -> list[str]:
    """Collect candidate phone strings from RentCast property JSON (full tree walk)."""
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, dict):
        return []
    candidates: list[str] = []
    _gather_strings(payload, candidates)

    seen: set[str] = set()
    for s in candidates:
        for m in _DIGIT_RUN.findall(s):
            seen.add(m)
        for m in _TEN_DIG.findall(re.sub(r"\D", "", s)):
            if len(m) == 10:
                seen.add(m)

    e164s: list[str] = []
    for raw in seen:
        e = to_us_e164(raw)
        if not e:
            continue
        d = re.sub(r"\D", "", e)
        nat = d[-10:]
        if nat[:3] == "555" or nat[3:6] == "555":
            continue
        if e not in e164s:
            e164s.append(e)
    return e164s


def fetch_rentcast_property(address: str, api_key: str) -> dict | list | None:
    clean = address.replace(", ,", ",").strip()
    url = f"{RENTCAST_URL}?address={requests.utils.quote(clean)}"
    r = requests.get(
        url,
        headers={"accept": "application/json", "X-Api-Key": api_key},
        timeout=45,
    )
    if r.status_code == 200:
        return r.json()
    if r.status_code == 429:
        logger.warning("RentCast rate limit (429). Increase --sleep or upgrade plan.")
    else:
        logger.warning("RentCast %s: %s", r.status_code, (r.text or "")[:300])
    return None


def row_phase_rank(city: str, state_raw: str) -> int:
    c = (city or "").strip().upper()
    g = _norm_state(state_raw)
    if c == "EDMOND" and g == "OK_GROUP":
        return 0
    if g == "OK_GROUP":
        return 1
    if g == "TX_GROUP":
        return 2
    if g == "NE_GROUP":
        return 3
    return 9


def load_candidates(conn: sqlite3.Connection, limit: int) -> list[tuple]:
    """
    Rows: id, street_address, phone_number, homeowner_name, city, state, zipcode,
          damage_score, median_home_value, phase_rank
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.id, c.street_address, c.phone_number, c.homeowner_name,
               s.city, s.state, s.zipcode, c.damage_score, s.median_home_value
        FROM contacts c
        JOIN storms s ON c.event_id = s.id
        WHERE
          UPPER(TRIM(s.state)) IN (
            'OK','OKLAHOMA','TX','TEXAS','NE','NEBRASKA'
          )
        ORDER BY COALESCE(c.damage_score, 0) DESC,
                 COALESCE(s.median_home_value, 0) DESC,
                 c.id ASC
        """
    )
    raw_rows = cur.fetchall()
    enriched: list[tuple] = []
    for row in raw_rows:
        if not needs_enrichment(row[2]):
            continue
        pr = row_phase_rank(row[4] or "", row[5] or "")
        if pr >= 9:
            continue
        enriched.append(row + (pr,))

    enriched.sort(key=lambda r: (r[-1], -float(r[7] or 0), -float(r[8] or 0), r[0]))
    return enriched[:limit]


def build_lookup_address(street: str, city: str, state: str, zipcode: str | None) -> str:
    parts = [street or "", city or "", state or ""]
    core = ", ".join(p.strip() for p in parts if p and str(p).strip())
    z = (zipcode or "").strip()
    if z:
        return f"{core} {z}".strip()
    return core


def main() -> None:
    ap = argparse.ArgumentParser(description="RentCast sequential skip-trace for OK/TX/NE contacts")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--limit", type=int, default=50, help="Max contacts to process (default 50)")
    ap.add_argument("--sleep", type=float, default=2.0, help="Seconds between RentCast calls")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    api_key = (os.environ.get("RENTCAST_API_KEY") or "").strip()
    if not api_key and not args.dry_run:
        logger.error("Set RENTCAST_API_KEY in .env (get a key at https://developers.rentcast.io).")
        sys.exit(1)

    db_path = args.db.resolve()
    if not db_path.is_file():
        logger.error("DB not found: %s", db_path)
        sys.exit(1)

    conn = sqlite3.connect(str(db_path), timeout=60)
    try:
        rows = load_candidates(conn, args.limit)
    finally:
        conn.close()

    if not rows:
        logger.info("No contacts need phone enrichment in OK/TX/NE with current filters.")
        return

    phase_names = {0: "Edmond_OK", 1: "Oklahoma", 2: "Texas", 3: "Nebraska"}
    logger.info(
        "Queued %s contacts (phase order: Edmond OK -> OK -> TX -> NE; high damage / home value first).",
        len(rows),
    )
    for i, r in enumerate(rows[: min(5, len(rows))]):
        logger.info(
            "  sample: id=%s phase=%s dmg=%s mhv=%s %s",
            r[0],
            phase_names.get(r[-1], r[-1]),
            r[7],
            r[8],
            build_lookup_address(r[1], r[4], r[5], r[6]),
        )

    if args.dry_run:
        logger.info("Dry run — no API calls or DB updates.")
        return

    updated = 0
    no_phone = 0
    errors = 0
    conn = sqlite3.connect(str(db_path), timeout=60)
    cur = conn.cursor()
    try:
        for idx, row in enumerate(rows, start=1):
            cid, street, _old_phone, owner, city, state, zipc, dmg, mhv, phase = row
            addr = build_lookup_address(street, city, state, zipc)
            if not addr or len(addr) < 8:
                logger.warning("[%s/%s] id=%s skip — weak address", idx, len(rows), cid)
                no_phone += 1
                continue
            logger.info(
                "[%s/%s] id=%s phase=%s RentCast: %s",
                idx,
                len(rows),
                cid,
                phase_names.get(phase, phase),
                addr[:120],
            )
            payload = fetch_rentcast_property(addr, api_key)
            if payload is None:
                errors += 1
                time.sleep(max(0.0, args.sleep))
                continue

            rec: Any = payload[0] if isinstance(payload, list) and payload else payload
            prop_owner: str | None = None
            if isinstance(rec, dict):
                o = rec.get("owner") or {}
                names = o.get("names")
                if isinstance(names, list) and names:
                    prop_owner = str(names[0]).strip() or None
                elif isinstance(names, str) and names.strip():
                    prop_owner = names.strip()

            phones = extract_phones_from_rentcast_payload(payload)
            best = phones[0] if phones else None
            if not best:
                logger.info("  no phone in response%s", f"; owner hint={prop_owner!r}" if prop_owner else "")
                no_phone += 1
            else:
                placeholder_owner = not owner or str(owner).strip() in (
                    "",
                    "Homeowner",
                    "DEEP SEARCH REQ",
                )
                new_owner = prop_owner if prop_owner and placeholder_owner else owner
                cur.execute(
                    """
                    UPDATE contacts
                    SET phone_number = ?, homeowner_name = ?, status = 'RENTCAST_SKIPTRACE'
                    WHERE id = ?
                    """,
                    (best, new_owner, cid),
                )
                conn.commit()
                updated += 1
                logger.info("  -> %s", best)
            time.sleep(max(0.0, args.sleep))
    finally:
        conn.close()

    logger.info(
        "Done. updated=%s no_new_phone=%s errors=%s (RentCast free tier is small — upgrade for bulk).",
        updated,
        no_phone,
        errors,
    )


if __name__ == "__main__":
    main()