#!/usr/bin/env python3
"""
Rebuild low-trust `contacts` rows and optionally mint new addresses from storm lat/lon.

Workflow
--------
1. **Purge** — Delete contacts matching shared synthetic heuristics in
   ``address_quality.contact_synthetic_reasons`` (after timestamped DB backup
   under ``leads_manifests/backups/``). Optional CSV of purged IDs + reasons.

2. **Ingest** — For each storm with coordinates, fetch Census **geoLookup** at
   the strike point::

       GET https://geocoding.geo.census.gov/geocoder/geographies/coordinates
           ?x=<lon>&y=<lat>&benchmark=Public_AR_Current&vintage=Current_Current
           &layers=all&format=json

   That returns state, county, place, and **ZCTA5** (via ``layers=all``).
   Census documents that coordinate queries only return geography layers, not
   a street-level ``matchedAddress``; we therefore obtain a **house-level line**
   from OpenStreetMap Nominatim reverse (rate-limited), then **forward-validate**
   with :func:`src.address_resolver.resolve_one` so the stored
   ``matchedAddress`` is Census MAF/TIGER-backed.

3. **PII** — New rows never invent names or phones; email/phone/name fields are
   cleared.

Limitations
-----------
Reverse geocoding yields the **nearest** interpolated address along a segment,
not a verified parcel owner; skip-trace / enrichment is still required for
dialable numbers and ownership proof. When OSM returns a route without a house
number, the script probes a small ladder of numeric prefixes so Census can
anchor a real TIGER range — the resulting number is a **segment reference**,
not field-verified premise ID.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOF_PKG = Path(__file__).resolve().parent.parent
REPO = ROOF_PKG.parent
for p in (str(REPO), str(ROOF_PKG)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.address_quality import (  # noqa: E402
    contact_synthetic_reasons,
    normalize_address_key,
    normalize_state_abbr,
)
from src.address_resolver import (  # noqa: E402
    AddressCache,
    ResolvedAddress,
    fetch_census_geography_context,
    resolve_one,
)

DEFAULT_DB = ROOF_PKG / "leads_manifests" / "authoritative_storms.db"
BACKUP_DIR = ROOF_PKG / "leads_manifests" / "backups"
NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
_ZIP_TAIL = re.compile(r"\b(\d{5})(?:-\d{4})?\s*$")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def offset_latlon(lat: float, lon: float, bearing_deg: float, dist_m: float) -> tuple[float, float]:
    br = math.radians(bearing_deg)
    dx = dist_m * math.sin(br)
    dy = dist_m * math.cos(br)
    dlat = dy / 111_320.0
    dlon = dx / (111_320.0 * max(0.2, math.cos(math.radians(lat))))
    return lat + dlat, lon + dlon


def zip_from_matched(matched: str) -> str:
    m = _ZIP_TAIL.search((matched or "").strip())
    return m.group(1) if m else ""


def backup_database(db_path: Path) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"authoritative_storms_backup_{ts}.db"
    shutil.copy2(db_path, dest)
    return dest


def iter_contacts_with_storm(conn: sqlite3.Connection) -> Iterable[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.id, c.street_address, c.zip_code, c.homeowner_name,
               c.phone_number, c.email, c.event_id,
               COALESCE(s.state, '') AS storm_state
        FROM contacts c
        LEFT JOIN storms s ON s.id = c.event_id
        """
    )
    yield from cur.fetchall()


def count_synthetic_contacts(conn: sqlite3.Connection) -> tuple[int, dict[str, int]]:
    reason_counts: dict[str, int] = defaultdict(int)
    n = 0
    for row in iter_contacts_with_storm(conn):
        reasons = contact_synthetic_reasons(
            street_address=row["street_address"],
            zip_code=row["zip_code"],
            homeowner_name=row["homeowner_name"],
            phone_number=row["phone_number"],
            email=row["email"],
            storm_state=row["storm_state"],
        )
        if reasons:
            n += 1
            for r in reasons:
                reason_counts[r] += 1
    return n, dict(reason_counts)


def nominatim_reverse(lat: float, lon: float, timeout: float = 15.0) -> dict[str, Any] | None:
    qs = urllib.parse.urlencode({"lat": str(lat), "lon": str(lon), "format": "json", "addressdetails": "1"})
    url = f"{NOMINATIM_REVERSE}?{qs}"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "roof_hunter_rebuild_contacts/1.0 (storm ingest; +https://github.com/)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def pick_locality(addr: dict[str, Any], census_place: str, storm_city: str) -> str:
    for key in ("city", "town", "village", "hamlet", "municipality", "suburb"):
        v = addr.get(key)
        if v:
            return str(v)
    if census_place:
        return census_place
    return storm_city or ""


def build_street_line_from_nominatim(addr: dict[str, Any]) -> str:
    house = (addr.get("house_number") or "").strip()
    road = (addr.get("road") or addr.get("pedestrian") or addr.get("path") or "").strip()
    if house and road:
        return f"{house} {road}"
    if road:
        return road
    return ""


def census_resolve_nearest_on_road(
    road: str,
    city: str,
    state: str,
    zip5: str,
    strike_lat: float,
    strike_lon: float,
    cache: AddressCache,
    max_offset_km: float,
) -> tuple[ResolvedAddress | None, str]:
    """
    When OSM gives only a route name (no house number), try a short ladder of
    probe numbers. Census/TIGER returns a real range anchor; we keep the first
    candidate within max_offset_km of the strike.
    """
    road = road.strip()
    if not road:
        return None, "empty_road"
    probes = (1, 10, 50, 100, 500, 1000, 2500, 5000, 10000)
    best: tuple[float, ResolvedAddress] | None = None
    for hn in probes:
        cand = f"{hn} {road}"
        res = resolve_one(cand, city, state, zip5, cache=cache)
        if res.resolution_status not in ("resolved", "resolved_municipal"):
            continue
        if res.latitude == 0.0 and res.longitude == 0.0:
            continue
        dist = haversine_km(strike_lat, strike_lon, res.latitude, res.longitude)
        if dist <= max_offset_km and res.resolution_status == "resolved":
            return res, f"probe_ok:{hn}"
        if best is None or dist < best[0]:
            if res.resolution_status == "resolved":
                best = (dist, res)
    if best is not None and best[0] <= max_offset_km * 1.5:
        return best[1], "probe_best_effort"
    return None, "probe_no_match_in_radius"


def strike_to_resolved_address(
    lat: float,
    lon: float,
    storm_state_raw: str,
    storm_city: str,
    storm_zip: str | None,
    cache: AddressCache,
    max_offset_km: float,
) -> tuple[ResolvedAddress | None, str]:
    ctx = fetch_census_geography_context(lon, lat)
    if ctx is None:
        return None, "census_geographies_failed"

    payload = nominatim_reverse(lat, lon)
    if not payload:
        return None, "nominatim_failed"
    addr = payload.get("address") or {}
    street_line = build_street_line_from_nominatim(addr)
    if not street_line:
        return None, "nominatim_no_street"

    city = pick_locality(addr, ctx.place_name, storm_city)
    st = ctx.state_stusab or normalize_state_abbr(storm_state_raw)
    z = (addr.get("postcode") or "").strip()
    if len(z) >= 5 and z[:5].isdigit():
        z = z[:5]
    elif ctx.zcta5:
        z = ctx.zcta5
    elif storm_zip and len(str(storm_zip).strip()) == 5:
        z = str(storm_zip).strip()
    else:
        z = ctx.zcta5

    resolved = resolve_one(street_line, city, st, z, cache=cache)
    note_extra = ""
    if resolved.resolution_status == "unresolvable_no_street" and street_line:
        probed, pnote = census_resolve_nearest_on_road(
            street_line, city, st, z, lat, lon, cache, max_offset_km
        )
        if probed is not None:
            resolved = probed
            note_extra = pnote
        else:
            return None, f"nominatim_road_only:{pnote}"

    if resolved.resolution_status not in ("resolved", "resolved_municipal"):
        return None, f"census_forward:{resolved.resolution_status}"

    dist = haversine_km(lat, lon, resolved.latitude, resolved.longitude)
    if dist > max_offset_km:
        return None, f"too_far_from_strike:{dist:.2f}km"

    if resolved.resolution_status == "resolved_municipal":
        return None, "census_forward_municipal_only"

    tag = "ok" if not note_extra else note_extra
    return resolved, tag


def parse_states(s: str | None) -> set[str] | None:
    if not s:
        return None
    parts = {normalize_state_abbr(x.strip()) for x in s.split(",") if x.strip()}
    return {p for p in parts if p}


def load_existing_address_keys(conn: sqlite3.Connection) -> dict[int, set[str]]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT event_id, street_address FROM contacts WHERE event_id IS NOT NULL")
    out: dict[int, set[str]] = defaultdict(set)
    for r in cur.fetchall():
        eid = r["event_id"]
        if eid is None:
            continue
        out[int(eid)].add(normalize_address_key(r["street_address"]))
    return out


def run_purge(
    db_path: Path,
    dry_run: bool,
    audit_csv: Path | None,
) -> tuple[int, int, Path | None]:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM contacts")
    before = int(cur.fetchone()[0])

    purge_ids: list[tuple[int, str]] = []
    for row in iter_contacts_with_storm(conn):
        reasons = contact_synthetic_reasons(
            street_address=row["street_address"],
            zip_code=row["zip_code"],
            homeowner_name=row["homeowner_name"],
            phone_number=row["phone_number"],
            email=row["email"],
            storm_state=row["storm_state"],
        )
        if reasons:
            purge_ids.append((int(row["id"]), ";".join(reasons)))

    if dry_run:
        conn.close()
        return before, before, None

    if not purge_ids:
        conn.close()
        return before, before, None

    backup_path = backup_database(db_path)

    if audit_csv:
        audit_csv.parent.mkdir(parents=True, exist_ok=True)
        with audit_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["contact_id", "reasons"])
            w.writerows(purge_ids)

    placeholders = ",".join("?" for _ in purge_ids)
    cur.execute(f"DELETE FROM contacts WHERE id IN ({placeholders})", [p[0] for p in purge_ids])
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM contacts")
    after = int(cur.fetchone()[0])
    conn.close()
    return before, after, backup_path


def run_ingest(
    db_path: Path,
    states: set[str] | None,
    limit: int | None,
    per_storm: int,
    max_offset_km: float,
    dry_run: bool,
) -> tuple[int, int, int]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM contacts")
    contacts_before = int(cur.fetchone()[0])

    cur.execute(
        """
        SELECT id, latitude, longitude, state, city, zipcode
        FROM storms
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY id
        """
    )
    storms = cur.fetchall()
    existing_keys = load_existing_address_keys(conn)

    cache = AddressCache(ROOF_PKG / ".rebuild_contacts_address_cache.json")
    inserted = 0
    storms_with_inserts = 0
    considered = 0

    for row in storms:
        if limit is not None and considered >= limit:
            break
        sid = int(row["id"])
        lat, lon = float(row["latitude"]), float(row["longitude"])
        st_raw = row["state"] or ""
        st = normalize_state_abbr(st_raw)
        if states and st not in states:
            continue
        considered += 1

        if dry_run:
            continue

        storm_city = (row["city"] or "").strip()
        storm_z = (row["zipcode"] or "").strip()
        storm_zip = storm_z if len(storm_z) == 5 and storm_z.isdigit() else None
        storm_keys = existing_keys[sid]
        got_this_storm = 0

        for i in range(per_storm):
            if i == 0:
                olat, olon = lat, lon
            else:
                olat, olon = offset_latlon(lat, lon, bearing_deg=(i * 72) % 360, dist_m=120.0 * i)

            resolved, tag = strike_to_resolved_address(
                olat, olon, st_raw, storm_city, storm_zip, cache, max_offset_km
            )
            time.sleep(1.1)

            if resolved is None:
                continue
            key = normalize_address_key(resolved.matched_address)
            if key in storm_keys:
                continue

            zip_ins = zip_from_matched(resolved.matched_address)
            proof = f"ingest:census_geo+nominatim+census_forward:{tag}"
            cur.execute(
                """
                INSERT INTO contacts (
                    event_id, street_address, homeowner_name, phone_number, email,
                    zip_code, proof_msg
                ) VALUES (?, ?, '', '', '', ?, ?)
                """,
                (sid, resolved.matched_address, zip_ins, proof),
            )
            storm_keys.add(key)
            existing_keys[sid] = storm_keys
            inserted += 1
            got_this_storm += 1

        if got_this_storm:
            storms_with_inserts += 1

    if not dry_run:
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM contacts")
        contacts_after = int(cur.fetchone()[0])
    else:
        contacts_after = contacts_before
    conn.close()
    cache.flush()
    return contacts_before, contacts_after, (considered if dry_run else storms_with_inserts)


def main() -> int:
    ap = argparse.ArgumentParser(description="Purge synthetic contacts; ingest Census-validated addresses from storms.")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB, help="Path to authoritative_storms.db")
    ap.add_argument("--dry-run", action="store_true", help="Counts only; no deletes or inserts")
    ap.add_argument("--purge-synthetic", action="store_true", help="Delete synthetic contacts (backup first)")
    ap.add_argument("--ingest-from-storms", action="store_true", help="Insert contacts from storm lat/lon")
    ap.add_argument("--ingest-per-storm", type=int, default=1, metavar="N", help="Max contacts per storm (default 1)")
    ap.add_argument("--states", type=str, default=None, help="Comma-separated USPS states e.g. TX,OK,KS")
    ap.add_argument("--limit", type=int, default=None, help="Max storms to consider (after state filter)")
    ap.add_argument("--max-offset-km", type=float, default=2.0, help="Reject census match if this far from strike")
    ap.add_argument("--audit-csv", type=Path, default=None, help="Write purged contact IDs + reasons")
    args = ap.parse_args()

    db_path = args.db.resolve()
    if not db_path.exists():
        print(f"[error] database not found: {db_path}", file=sys.stderr)
        return 1

    states = parse_states(args.states)
    conn = sqlite3.connect(str(db_path))
    total_contacts = int(conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0])
    synth_n, synth_breakdown = count_synthetic_contacts(conn)
    conn.close()

    print(f"contacts_total={total_contacts}")
    print(f"synthetic_contact_rows={synth_n}")
    if synth_breakdown:
        top = sorted(synth_breakdown.items(), key=lambda kv: -kv[1])[:12]
        print("synthetic_reasons_top=" + json.dumps({k: v for k, v in top}))

    if args.dry_run and not args.purge_synthetic and not args.ingest_from_storms:
        return 0

    if args.purge_synthetic:
        before, after, backup = run_purge(db_path, dry_run=args.dry_run, audit_csv=args.audit_csv)
        print(f"purge contacts_before={before} after={after} dry_run={args.dry_run}")
        if backup:
            print(f"backup_db={backup}")

    if args.ingest_from_storms:
        cb, ca, storms_metric = run_ingest(
            db_path,
            states=states,
            limit=args.limit,
            per_storm=max(1, args.ingest_per_storm),
            max_offset_km=args.max_offset_km,
            dry_run=args.dry_run,
        )
        label = "storms_eligible" if args.dry_run else "storms_with_new_contacts"
        print(f"ingest contacts_before={cb} after={ca} {label}={storms_metric} dry_run={args.dry_run}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
