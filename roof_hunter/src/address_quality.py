"""
Shared heuristics for address / contact trust scoring and synthetic-data detection.

ZIP–state validation and phone grading are used by forecasting scripts; richer
contact-level rules feed lead cleanup (Faker placeholders, municipal rows, etc.).
"""

from __future__ import annotations

import re
from typing import Any

# Full state name → USPS abbreviation (storm ingest sometimes uses full names).
STATE_NORM: dict[str, str] = {
    "TEXAS": "TX",
    "OKLAHOMA": "OK",
    "KANSAS": "KS",
    "NEBRASKA": "NE",
    "COLORADO": "CO",
    "MISSOURI": "MO",
    "ARKANSAS": "AR",
    "LOUISIANA": "LA",
    "MISSISSIPPI": "MS",
    "ALABAMA": "AL",
    "GEORGIA": "GA",
    "WYOMING": "WY",
    "IOWA": "IA",
    "MINNESOTA": "MN",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "OHIO": "OH",
    "KENTUCKY": "KY",
    "TENNESSEE": "TN",
    "NEW MEXICO": "NM",
    "ARIZONA": "AZ",
    "NEVADA": "NV",
    "FLORIDA": "FL",
    "SOUTH CAROLINA": "SC",
    "NORTH CAROLINA": "NC",
    "VIRGINIA": "VA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "SOUTH DAKOTA": "SD",
    "NORTH DAKOTA": "ND",
    "MONTANA": "MT",
    "IDAHO": "ID",
    "WASHINGTON": "WA",
    "OREGON": "OR",
    "CALIFORNIA": "CA",
    "PENNSYLVANIA": "PA",
    "NEW YORK": "NY",
    "MAINE": "ME",
    "VERMONT": "VT",
    "NEW HAMPSHIRE": "NH",
    "MASSACHUSETTS": "MA",
    "RHODE ISLAND": "RI",
    "CONNECTICUT": "CT",
    "NEW JERSEY": "NJ",
    "DELAWARE": "DE",
    "MARYLAND": "MD",
    "DISTRICT OF COLUMBIA": "DC",
    "UTAH": "UT",
    "ALASKA": "AK",
    "HAWAII": "HI",
}

# USPS ZIP first-two-digit prefixes by state (same source as predict_24h_hail_strikes).
STATE_ZIP_PREFIX: dict[str, set[str]] = {
    "TX": {"73", "75", "76", "77", "78", "79", "88"},
    "OK": {"73", "74"},
    "KS": {"66", "67"},
    "NE": {"68", "69"},
    "CO": {"80", "81"},
    "MO": {"63", "64", "65"},
    "AR": {"71", "72"},
    "LA": {"70", "71"},
    "MS": {"38", "39"},
    "AL": {"35", "36"},
    "GA": {"30", "31", "39"},
    "WY": {"82", "83"},
    "IA": {"50", "51", "52"},
    "MN": {"55", "56"},
    "IL": {"60", "61", "62"},
    "IN": {"46", "47"},
    "OH": {"43", "44", "45"},
    "KY": {"40", "41", "42"},
    "TN": {"37", "38"},
    "NM": {"87", "88"},
    "AZ": {"85", "86"},
    "NV": {"88", "89"},
    "FL": {"32", "33", "34"},
    "SC": {"29"},
    "NC": {"27", "28"},
    "VA": {"20", "22", "23", "24"},
    "WI": {"53", "54"},
    "SD": {"57", "58"},
    "ND": {"58", "59"},
    "MT": {"59"},
    "ID": {"83"},
    "WA": {"98", "99"},
    "OR": {"97"},
    "CA": {"90", "91", "92", "93", "94", "95", "96"},
}

# Faker / generator placeholders
SYNTHETIC_ZIPS: frozenset[str] = frozenset({"73000", "00000", "12345", "99999", "11111"})

_RE_HOUSE_NUM_LEAD = re.compile(r"^\s*\d+[A-Za-z]?\s+\S+")
_RE_FAKER_PHONE_EXT = re.compile(r"\bx\d{3,}\b", re.IGNORECASE)
_RE_ROUND_CIVIC = re.compile(
    r"^\s*(100|200|300|400|500)\s+"
    r"(MAIN|MARKET|CENTER|CENTRE|COURT|FIRST|1ST|SECOND|2ND|THIRD|3RD|FOURTH|4TH|FIFTH|5TH)\b",
    re.IGNORECASE,
)
_RE_RURAL_OK_PREFIX = re.compile(
    r"^\s*(Highway|Hwy|FM\s|CR\s|County\s|RD|Route|US\s|State\s|State\s?Hwy)",
    re.IGNORECASE,
)


def normalize_state_abbr(state: str) -> str:
    if not state:
        return ""
    s = state.strip().upper()
    if len(s) == 2 and s.isalpha():
        return s
    return STATE_NORM.get(s, s)


def grade_address(zip_code: str, state: str, phone: str) -> tuple[str, list[str]]:
    """
    Return (grade, reasons). Grade is one of:
      "real", "no_phone", "fake_zip", "fake_phone", "unusable"
    """
    reasons: list[str] = []
    z = (zip_code or "").strip()
    if not z:
        reasons.append("zip_empty")
    elif z in SYNTHETIC_ZIPS:
        reasons.append(f"zip_synthetic({z})")
    elif not (len(z) == 5 and z.isdigit()):
        reasons.append("zip_malformed")
    else:
        prefix = z[:2]
        allowed = STATE_ZIP_PREFIX.get(state)
        if allowed is not None and prefix not in allowed:
            reasons.append(f"zip_state_mismatch({prefix}!~{state})")

    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    p_norm = (phone or "").strip().upper()
    if not p_norm:
        phone_grade = "absent"
    elif "UNVERIFIED" in p_norm or "UNK" in p_norm:
        phone_grade = "fake"
        reasons.append("phone_unverified")
    elif len(digits) < 10:
        phone_grade = "fake"
        reasons.append("phone_too_short")
    elif digits.startswith("555") or digits[1:4] == "555" or digits[3:6] == "555":
        phone_grade = "fake"
        reasons.append("phone_555")
    else:
        phone_grade = "ok"

    addr_bad = any(r.startswith("zip_") for r in reasons)
    if addr_bad and phone_grade == "fake":
        return "unusable", reasons
    if addr_bad:
        return "fake_zip", reasons
    if phone_grade == "fake":
        return "fake_phone", reasons
    if phone_grade == "absent":
        return "no_phone", reasons
    return "real", reasons


def phone_synthetic_signals(phone: str | None) -> list[str]:
    """Reason tokens when phone should not be treated as a real lead number."""
    out: list[str] = []
    p = (phone or "").strip()
    if not p:
        return out
    pu = p.upper()
    if "UNVERIFIED" in pu or "UNK" in pu:
        out.append("phone_unverified")
    digits = "".join(ch for ch in p if ch.isdigit())
    if len(digits) < 10:
        out.append("phone_too_short")
    elif digits.startswith("555") or digits[1:4] == "555" or digits[3:6] == "555":
        out.append("phone_555")
    if _RE_FAKER_PHONE_EXT.search(p):
        out.append("phone_faker_extension")
    return out


def email_synthetic_signals(email: str | None) -> list[str]:
    e = (email or "").strip().lower()
    if not e:
        return []
    if e.endswith("@example.com") or e.endswith("@example.org"):
        return ["email_example_domain"]
    return []


def is_county_or_region_only_street(street_address: str) -> bool:
    sa = (street_address or "").strip().upper()
    if not sa:
        return True
    if "UNITED STATES" in sa and "," in sa:
        return True
    if re.search(r"\bCOUNTY\b", sa) and "," in sa and not _RE_HOUSE_NUM_LEAD.match(sa.split(",")[0]):
        return True
    return False


def street_missing_house_number_when_expected(street_address: str) -> bool:
    """
    True when the line looks like a numbered civic street but has no leading house #.
    Rural/highway-only rows are exempt.
    """
    sa = (street_address or "").strip()
    if not sa:
        return True
    head = sa.split(",", 1)[0]
    if _RE_RURAL_OK_PREFIX.match(head):
        return False
    if _RE_HOUSE_NUM_LEAD.match(head):
        return False
    # Has typical street suffix but no number at start
    if re.search(
        r"\b(ST|STREET|RD|ROAD|AVE|AVENUE|DR|DRIVE|LN|LANE|CT|COURT|CIR|CIRCLE|WAY|BLVD)\b\.?$",
        head,
        re.IGNORECASE,
    ):
        return True
    return False


def is_placeholder_homeowner(name: str | None) -> bool:
    n = (name or "").strip()
    return n.upper() in ("HOMEOWNER",) or n == ""


def is_round_civic_placeholder_street(street_address: str) -> bool:
    head = (street_address or "").split(",", 1)[0]
    return bool(_RE_ROUND_CIVIC.match(head))


def empty_zip_with_junk_street(zip_code: str | None, street_address: str) -> bool:
    z = (zip_code or "").strip()
    if z:
        return False
    return is_county_or_region_only_street(street_address) or street_missing_house_number_when_expected(
        street_address
    )


def contact_synthetic_reasons(
    *,
    street_address: str | None,
    zip_code: str | None,
    homeowner_name: str | None,
    phone_number: str | None,
    email: str | None,
    storm_state: str | None,
) -> list[str]:
    """
    Consolidated low-trust / synthetic detection. Non-empty list → purge candidate.
    """
    reasons: list[str] = []
    st = normalize_state_abbr(storm_state or "")

    reasons.extend(email_synthetic_signals(email))
    reasons.extend(phone_synthetic_signals(phone_number))

    z = (zip_code or "").strip()
    if z in SYNTHETIC_ZIPS:
        reasons.append(f"zip_synthetic({z})")
    elif z and (len(z) != 5 or not z.isdigit()):
        reasons.append("zip_malformed")

    if empty_zip_with_junk_street(zip_code, street_address or ""):
        reasons.append("empty_zip_junk_street")

    if z and len(z) == 5 and z.isdigit() and z not in SYNTHETIC_ZIPS and st:
        allowed = STATE_ZIP_PREFIX.get(st)
        prefix = z[:2]
        if allowed is not None and prefix not in allowed:
            reasons.append(f"zip_state_mismatch({prefix}!~{st})")

    if is_county_or_region_only_street(street_address or ""):
        reasons.append("region_or_county_only_address")

    if street_missing_house_number_when_expected(street_address or ""):
        reasons.append("street_missing_house_number")

    if is_placeholder_homeowner(homeowner_name) and is_round_civic_placeholder_street(street_address or ""):
        reasons.append("placeholder_homeowner_round_civic")

    # de-dupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def normalize_address_key(street_address: str | None) -> str:
    t = (street_address or "").upper()
    t = re.sub(r"[^A-Z0-9]+", " ", t)
    return " ".join(t.split())


__all__ = [
    "STATE_NORM",
    "STATE_ZIP_PREFIX",
    "SYNTHETIC_ZIPS",
    "normalize_state_abbr",
    "grade_address",
    "contact_synthetic_reasons",
    "normalize_address_key",
    "phone_synthetic_signals",
    "email_synthetic_signals",
]
