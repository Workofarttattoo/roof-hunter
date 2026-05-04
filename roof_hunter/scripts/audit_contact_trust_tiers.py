#!/usr/bin/env python3
"""
Classify contacts in authoritative_storms.db for export safety.

Tiers (trust_rank 0–3, higher is safer):

  0  T0_blocked              Placeholder / synthetic name, bad phone (555, too short,
                            UNVERIFIED*, known harvester labels), or missing phone when
                            name is junk — do not use for outbound.

  1  T1_needs_phone           Real-looking owner name but missing or invalid US phone;
                            append / manual lookup before dialing.

  2  T2_automated_identity   Usable US phone + non-placeholder owner name (likely
                            matcher/OSINT/Apollo/RentCast — still verify before relying
                            on name↔number linkage).

  3  T3_verified_timestamp   Row has verified_at set (manual/ingest checkpoint) and
                            passes phone + name gates — best available in DB without a
                            dedicated human_verified boolean.

Usage:
  python3 scripts/audit_contact_trust_tiers.py --summary
  python3 scripts/audit_contact_trust_tiers.py --csv leads_manifests/trust_audit.csv
  python3 scripts/audit_contact_trust_tiers.py --csv out.csv --min-rank 2
  python3 scripts/audit_contact_trust_tiers.py --csv gold.csv --min-rank 3
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO / "leads_manifests" / "authoritative_storms.db"

sys.path.insert(0, str(REPO / "src"))
from normalize_lead_phones_e164 import to_us_e164  # noqa: E402

_PLACEHOLDER_EXACT = frozenset(
    {
        "",
        "HOMEOWNER",
        "OWNER",
        "LOCAL RESIDENT",
        "OKC HOMEOWNER",
        "EDMOND HOMEOWNER",
        "DEEP SEARCH REQ",
        "STORM IMPACT DETECTED",
        "LOCAL",
        "RESIDENT",
    }
)

_PLACEHOLDER_SUBSTR = (
    "HOMEOWNER",
    "DATABROKER",
    "PROTECTED",
    "FAKE",
    "TEST LEAD",
    "SAMPLE",
)


def _digits(s: str) -> str:
    return re.sub(r"\D", "", str(s or ""))


def is_placeholder_name(raw: str | None) -> bool:
    s = (raw or "").strip()
    if not s:
        return True
    u = s.upper().strip()
    if u in _PLACEHOLDER_EXACT:
        return True
    for frag in _PLACEHOLDER_SUBSTR:
        if frag in u:
            return True
    return False


def phone_analysis(digits: str) -> tuple[bool, str]:
    """Returns (usable_for_dial, reason_flag)."""
    if not digits:
        return False, "no_digits"
    nat = digits[-10:] if len(digits) >= 10 else digits
    if len(nat) < 10:
        return False, "short_phone"
    if nat[:3] == "555" or nat[3:6] == "555":
        return False, "fake_555"
    e = to_us_e164(digits)
    if not e:
        return False, "invalid_nanp"
    return True, "ok"


def looks_like_real_person_name(homeowner: str | None, first: str | None, last: str | None) -> bool:
    fn = (first or "").strip()
    ln = (last or "").strip()
    if fn and ln:
        if is_placeholder_name(fn) or is_placeholder_name(ln):
            return False
        if len(fn) < 2 or len(ln) < 2:
            return False
        return True
    full = (homeowner or "").strip()
    if not full or is_placeholder_name(full):
        return False
    parts = full.split()
    if len(parts) < 2:
        return False
    if all(len(p) < 2 for p in parts):
        return False
    return True


def classify_row(
    homeowner_name: str | None,
    phone_number: str | None,
    first_name: str | None,
    last_name: str | None,
    verified_at: str | None,
) -> tuple[int, str, str]:
    """
    Returns (trust_rank, tier_code, flags_semicolon_separated).
    """
    flags: list[str] = []
    d = _digits(phone_number or "")
    ph_ok, ph_reason = phone_analysis(d)
    if not ph_ok:
        flags.append(f"phone:{ph_reason}")

    pl_name = is_placeholder_name(homeowner_name)
    if pl_name:
        flags.append("name:placeholder")

    real_name = looks_like_real_person_name(homeowner_name, first_name, last_name)
    if not real_name:
        flags.append("name:not_structured_person")

    u = (phone_number or "").upper()
    if "UNVERIFIED" in u:
        flags.append("phone:unverified_marker")
        ph_ok = False

    bad_phone = not ph_ok
    bad_name = pl_name or not real_name

    if bad_name:
        if bad_phone:
            flags.append("gate:identity_and_phone_bad")
        else:
            flags.append("gate:identity_bad_phone_ok_still_block")
        return 0, "T0_blocked", ";".join(sorted(set(flags)))

    if bad_phone:
        flags.append("gate:needs_phone")
        return 1, "T1_needs_phone", ";".join(sorted(set(flags)))

    has_verified_at = bool((verified_at or "").strip())
    if has_verified_at:
        flags.append("gate:verified_at")
        return 3, "T3_verified_timestamp", ";".join(sorted(set(flags)))

    flags.append("gate:automated_ok")
    return 2, "T2_automated_identity", ";".join(sorted(set(flags)))


def main() -> None:
    ap = argparse.ArgumentParser(description="Trust tiers for contacts (export safety).")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--summary", action="store_true", help="Print counts by tier and rank.")
    ap.add_argument("--csv", type=Path, help="Write full audit CSV.")
    ap.add_argument(
        "--min-rank",
        type=int,
        default=0,
        choices=(0, 1, 2, 3),
        help="With --csv, only rows with trust_rank >= this (default 0 = all).",
    )
    args = ap.parse_args()

    db = args.db.resolve()
    conn = sqlite3.connect(str(db), timeout=60)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.id, c.event_id, c.street_address, c.homeowner_name, c.first_name, c.last_name,
               c.phone_number, c.email, c.status, c.qualification_status, c.verified_at,
               c.damage_score, s.city, s.state, s.zipcode
        FROM contacts c
        LEFT JOIN storms s ON c.event_id = s.id
        """
    )
    rows = cur.fetchall()
    conn.close()

    enriched: list[dict[str, object]] = []
    summary: dict[str, int] = {}

    for r in rows:
        rank, tier, fl = classify_row(
            r["homeowner_name"],
            r["phone_number"],
            r["first_name"],
            r["last_name"],
            r["verified_at"],
        )
        summary[tier] = summary.get(tier, 0) + 1
        enriched.append(
            {
                "id": r["id"],
                "trust_rank": rank,
                "trust_tier": tier,
                "trust_flags": fl,
                "homeowner_name": r["homeowner_name"],
                "first_name": r["first_name"],
                "last_name": r["last_name"],
                "phone_number": r["phone_number"],
                "email": r["email"],
                "street_address": r["street_address"],
                "city": r["city"],
                "state": r["state"],
                "zipcode": r["zipcode"],
                "status": r["status"],
                "qualification_status": r["qualification_status"],
                "verified_at": r["verified_at"],
                "damage_score": r["damage_score"],
                "event_id": r["event_id"],
            }
        )

    if args.summary:
        print(f"Database: {db}")
        print("By tier:")
        for k in sorted(summary.keys(), key=lambda x: (x.startswith("T0"), x)):
            print(f"  {k:28} {summary[k]}")
        print("By min rank (cumulative):")
        for m in (0, 1, 2, 3):
            n = sum(1 for e in enriched if e["trust_rank"] >= m)
            print(f"  rank >= {m}: {n}")

    if args.csv:
        out_path = args.csv.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        min_r = args.min_rank
        subset = [e for e in enriched if int(e["trust_rank"]) >= min_r]
        if not subset:
            print(f"No rows with trust_rank >= {min_r}; wrote nothing.")
            return
        fieldnames = list(subset[0].keys())
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(subset)
        print(f"Wrote {len(subset)} rows to {out_path} (trust_rank >= {min_r}).")

    if not args.summary and not args.csv:
        ap.print_help()
        print(f"\nHint: run with --summary or --csv (see --help). Total contacts: {len(enriched)}")


if __name__ == "__main__":
    main()
