#!/usr/bin/env python3
"""
Export storm leads for two regions, split into PAST_7D and NEXT_7D windows
(relative to --as-of, default = today). Writes one CSV per region with a
'section' column so the past/future split is unambiguous.

Regions:
  - FORT_WORTH_AREA = TX, DFW Metroplex (Tarrant + ring counties + named cities)
  - OKLAHOMA        = entire OK / OKLAHOMA state

Default window: as_of - 7 days ... as_of + 7 days

Outputs (in leads_manifests/):
  window_<from>_<to>_FORT_WORTH.csv
  window_<from>_<to>_OKLAHOMA.csv
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO / "leads_manifests" / "authoritative_storms.db"

FW_COUNTIES = ("TARRANT", "PARKER", "JOHNSON", "WISE", "HOOD", "DENTON")
FW_CITIES = (
    "FORT WORTH", "ARLINGTON", "MANSFIELD", "GRAPEVINE", "KELLER", "SOUTHLAKE",
    "COLLEYVILLE", "EULESS", "BEDFORD", "HURST", "NORTH RICHLAND HILLS",
    "HALTOM CITY", "SAGINAW", "WATAUGA", "CROWLEY", "BURLESON", "BENBROOK",
    "WHITE SETTLEMENT", "RIVER OAKS", "FOREST HILL", "EVERMAN", "AZLE",
    "WEATHERFORD", "GRANBURY", "CLEBURNE", "DECATUR", "BRIDGEPORT",
    "GLEN ROSE", "ALEDO", "MILLSAP", "ANNETTA", "ANNETTA SOUTH",
    "RICHLAND HILLS", "KENNEDALE", "PANTEGO", "DALWORTHINGTON GARDENS",
)

ROW_FIELDS = [
    "section", "event_date", "state", "city", "county", "magnitude",
    "zipcode", "source", "contact_id", "homeowner_name", "phone_number",
    "email", "street_address", "damage_score", "qualification_status",
    "status", "verified_at", "event_id",
]


def fetch(
    conn: sqlite3.Connection,
    *,
    where_state_clause: str,
    extra_where: str,
    params: tuple,
    start: str,
    end: str,
) -> list[dict]:
    sql = f"""
        SELECT s.id AS event_id, s.event_date, s.state, s.city, s.county,
               s.magnitude, s.zipcode, s.source,
               c.id AS contact_id, c.homeowner_name, c.phone_number, c.email,
               c.street_address, c.damage_score, c.qualification_status,
               c.status, c.verified_at
        FROM storms s
        LEFT JOIN contacts c ON c.event_id = s.id
        WHERE s.event_date BETWEEN ? AND ?
          AND ({where_state_clause})
          {extra_where}
        ORDER BY s.event_date DESC, s.city, c.id
    """
    cur = conn.cursor()
    cur.execute(sql, (start, end, *params))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def split_section(rows: list[dict], as_of: date) -> list[dict]:
    out: list[dict] = []
    cutoff_iso = as_of.isoformat()
    for r in rows:
        ed = (r.get("event_date") or "")[:10]
        section = "PAST_7D" if ed <= cutoff_iso else "NEXT_7D"
        out.append({**r, "section": section})
    return out


def write_csv(path: Path, rows: list[dict], header_note: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows_sorted = sorted(
        rows,
        key=lambda r: (
            0 if r["section"] == "PAST_7D" else 1,
            r.get("event_date") or "",
            r.get("city") or "",
            r.get("contact_id") or 0,
        ),
    )
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(f"# {header_note}\n")
        w = csv.DictWriter(f, fieldnames=ROW_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows_sorted)
    return len(rows_sorted)


def summarize(rows: list[dict]) -> dict:
    storms = {r["event_id"] for r in rows}
    leads = sum(1 for r in rows if r.get("contact_id"))
    past = sum(1 for r in rows if r["section"] == "PAST_7D")
    future = sum(1 for r in rows if r["section"] == "NEXT_7D")
    past_leads = sum(1 for r in rows if r["section"] == "PAST_7D" and r.get("contact_id"))
    future_leads = sum(1 for r in rows if r["section"] == "NEXT_7D" and r.get("contact_id"))
    return {
        "storms": len(storms),
        "rows": len(rows),
        "leads": leads,
        "past_rows": past,
        "next_rows": future,
        "past_leads": past_leads,
        "next_leads": future_leads,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Export FW + OK lead window CSVs.")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--as-of", default=None, help="ISO date; default today.")
    ap.add_argument("--days-back", type=int, default=7)
    ap.add_argument("--days-forward", type=int, default=7)
    args = ap.parse_args()

    if args.as_of:
        as_of = datetime.fromisoformat(args.as_of).date()
    else:
        as_of = date.today()
    start = (as_of - timedelta(days=args.days_back)).isoformat()
    end = (as_of + timedelta(days=args.days_forward)).isoformat()

    conn = sqlite3.connect(str(args.db.resolve()), timeout=60)

    fw_state_clause = "UPPER(s.state) IN ('TX','TEXAS')"
    fw_county_q = " OR ".join(["UPPER(COALESCE(s.county,'')) LIKE ?"] * len(FW_COUNTIES))
    fw_city_q = ",".join("?" for _ in FW_CITIES)
    fw_extra = f" AND (({fw_county_q}) OR UPPER(s.city) IN ({fw_city_q}))"
    fw_params = tuple(f"{c}%" for c in FW_COUNTIES) + FW_CITIES

    fw_rows = split_section(fetch(conn, where_state_clause=fw_state_clause, extra_where=fw_extra, params=fw_params, start=start, end=end), as_of)
    ok_rows = split_section(fetch(conn, where_state_clause="UPPER(s.state) IN ('OK','OKLAHOMA')", extra_where="", params=tuple(), start=start, end=end), as_of)
    conn.close()

    out_dir = REPO / "leads_manifests"
    fw_csv = out_dir / f"window_{start}_to_{end}_FORT_WORTH.csv"
    ok_csv = out_dir / f"window_{start}_to_{end}_OKLAHOMA.csv"

    fw_note = (
        f"Fort Worth + DFW Metroplex (TX). Window: {start} (7d back) → {end} (7d forward). "
        f"Past=section PAST_7D (≤ {as_of}); Future=section NEXT_7D (> {as_of})."
    )
    ok_note = (
        f"Oklahoma (statewide). Window: {start} (7d back) → {end} (7d forward). "
        f"Past=section PAST_7D (≤ {as_of}); Future=section NEXT_7D (> {as_of})."
    )

    fw_n = write_csv(fw_csv, fw_rows, fw_note)
    ok_n = write_csv(ok_csv, ok_rows, ok_note)
    fw_s = summarize(fw_rows)
    ok_s = summarize(ok_rows)

    def show(label: str, path: Path, s: dict, n: int) -> None:
        print(f"\n=== {label} ===")
        print(f"file: {path}")
        print(f"rows written: {n}  (storms={s['storms']}, leads={s['leads']})")
        print(f"  PAST_7D : rows={s['past_rows']:5d}  leads={s['past_leads']}")
        print(f"  NEXT_7D : rows={s['next_rows']:5d}  leads={s['next_leads']}")

    print(f"as_of={as_of}  window=[{start} … {end}]")
    show("FORT WORTH + SURROUNDING (TX)", fw_csv, fw_s, fw_n)
    show("OKLAHOMA (statewide)", ok_csv, ok_s, ok_n)

    if fw_s["next_rows"] == 0 and ok_s["next_rows"] == 0:
        print(
            "\nNote: NEXT_7D is empty because authoritative_storms.db only ingests "
            "post-event data (NOAA SWDI/SPC/field reports). No forecast feeder is "
            "wired in. Pull a forecast (e.g. NOAA SPC outlooks) into 'storms' if you "
            "want the future window populated."
        )


if __name__ == "__main__":
    main()
