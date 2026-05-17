"""
Predict the worst hail strikes in the next 24 hours against addresses we
already own in authoritative_storms.db, output a CSV ranked worst→least so
the call team has searchable addresses to work.

Pipeline
--------
1. Pull every contact whose linked storm has a lat/lon and a non-empty
   street address (optionally restrict by state, optionally require a
   phone number).
2. Collapse those points into a coarse forecast grid (default 0.25°,
   matching typical global model resolution) so we make one Open-Meteo
   forecast call per cell instead of per contact.
3. For each cell, fetch the Open-Meteo forecast for the next 24 h
   (temperature, dewpoint, RH, surface pressure, wind, precip, CAPE,
   lightning_potential).
4. Run RoofHunterWeatherTwin.simulate() over those hourly states to get
   per-hour hail_probability / risk_score / hail_core sizing. Open-Meteo
   CAPE is fed in via the GraphCast-CAPE override slot so the twin uses
   model CAPE instead of its biased-low parcel approximation.
5. Within each cell take the *peak* hail probability over the next
   --hours window. Apply --min-prob floor.
6. Re-attach the contacts that live in surviving cells, sort the whole
   table by predicted peak probability, slice --top, write CSV.

Output CSV is ranked, with the address columns prominent so a human can
paste them into Google / a CRM / an outbound dialer immediately.

Usage
-----
    python -m scripts.predict_24h_hail_strikes \
        --state TX,OK,KS,NE \
        --top 25 --min-prob 0.5

    python -m scripts.predict_24h_hail_strikes --with-phone --top 50

    python -m scripts.predict_24h_hail_strikes \
        --hours 12 --grid-deg 0.5 --top 100 --out /tmp/strikes.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOF_PKG = Path(__file__).resolve().parent.parent
REPO = ROOF_PKG.parent
for p in (str(REPO), str(ROOF_PKG)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.address_quality import grade_address, normalize_state_abbr  # noqa: E402
from src.address_resolver import AddressCache, resolve_one  # noqa: E402
from src.weather_twin.models import ForecastState  # noqa: E402
from src.weather_twin.roof_hunter_digital_twin import RoofHunterWeatherTwin  # noqa: E402

DEFAULT_DB = ROOF_PKG / "leads_manifests" / "authoritative_storms.db"
DEFAULT_OUT_DIR = ROOF_PKG / "leads_manifests"

OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = ",".join([
    "temperature_2m",
    "relative_humidity_2m",
    "dewpoint_2m",
    "surface_pressure",
    "precipitation",
    "wind_speed_10m",
    "wind_direction_10m",
    "cape",
    "lightning_potential",
])

@dataclass(frozen=True)
class GridCell:
    lat: float
    lon: float

    def key(self) -> str:
        return f"{self.lat:.4f}|{self.lon:.4f}"


@dataclass
class CellForecast:
    cell: GridCell
    peak_hail_probability: float
    peak_risk_score: float
    peak_time_utc: datetime
    peak_hail_core_confidence: float
    peak_hail_core_radius_ft: float
    peak_cape_j_kg: float
    peak_lightning_potential: float | None
    n_hours: int


@dataclass
class ContactRow:
    contact_id: int
    event_id: int | None
    street_address: str
    homeowner_name: str
    phone_number: str
    email: str
    zip_code: str
    damage_score: float | None
    storm_lat: float
    storm_lon: float
    storm_state: str
    storm_city: str
    storm_county: str
    storm_event_date: str
    address_grade: str = "unknown"
    address_grade_reasons: str = ""


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_contacts(
    db_path: Path,
    state_filter: list[str] | None,
    require_phone: bool,
) -> list[ContactRow]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    where = [
        "s.latitude IS NOT NULL",
        "s.longitude IS NOT NULL",
        "c.street_address IS NOT NULL",
        "TRIM(c.street_address) != ''",
    ]
    if require_phone:
        where.append("c.phone_number IS NOT NULL AND TRIM(c.phone_number) != ''")

    sql = f"""
        SELECT
            c.id            AS contact_id,
            c.event_id      AS event_id,
            c.street_address AS street_address,
            COALESCE(c.homeowner_name, '') AS homeowner_name,
            COALESCE(c.phone_number, '')   AS phone_number,
            COALESCE(c.email, '')          AS email,
            COALESCE(c.zip_code, '')       AS zip_code,
            c.damage_score  AS damage_score,
            s.latitude      AS storm_lat,
            s.longitude     AS storm_lon,
            COALESCE(s.state, '')      AS storm_state,
            COALESCE(s.city, '')       AS storm_city,
            COALESCE(s.county, '')     AS storm_county,
            COALESCE(s.event_date, '') AS storm_event_date
        FROM contacts c
        JOIN storms s ON s.id = c.event_id
        WHERE {' AND '.join(where)}
    """
    cur.execute(sql)
    rows: list[ContactRow] = []
    norm_filter = {normalize_state_abbr(x) for x in state_filter} if state_filter else None
    for r in cur.fetchall():
        st = normalize_state_abbr(r["storm_state"])
        if norm_filter and st not in norm_filter:
            continue
        zip_code = r["zip_code"].strip()
        phone = r["phone_number"].strip()
        grade, reasons = grade_address(zip_code, st, phone)
        rows.append(ContactRow(
            contact_id=int(r["contact_id"]),
            event_id=r["event_id"],
            street_address=r["street_address"].strip(),
            homeowner_name=r["homeowner_name"].strip(),
            phone_number=phone,
            email=r["email"].strip(),
            zip_code=zip_code,
            damage_score=float(r["damage_score"]) if r["damage_score"] is not None else None,
            storm_lat=float(r["storm_lat"]),
            storm_lon=float(r["storm_lon"]),
            storm_state=st,
            storm_city=r["storm_city"].strip(),
            storm_county=r["storm_county"].strip(),
            storm_event_date=r["storm_event_date"].strip(),
            address_grade=grade,
            address_grade_reasons=";".join(reasons),
        ))
    conn.close()
    return rows


def bucket_to_grid(lat: float, lon: float, grid_deg: float) -> GridCell:
    return GridCell(
        lat=round(lat / grid_deg) * grid_deg,
        lon=round(lon / grid_deg) * grid_deg,
    )


def fetch_open_meteo(cell: GridCell, hours: int, retries: int = 3) -> dict[str, Any] | None:
    forecast_days = 2 if hours <= 24 else max(2, math.ceil(hours / 24) + 1)
    qs = urllib.parse.urlencode({
        "latitude": f"{cell.lat:.4f}",
        "longitude": f"{cell.lon:.4f}",
        "hourly": HOURLY_VARS,
        "forecast_days": forecast_days,
        "timezone": "UTC",
        "wind_speed_unit": "ms",
    })
    url = f"{OPEN_METEO_FORECAST}?{qs}"
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "roof-hunter/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.load(resp)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_err = e
            time.sleep(1.0 * (attempt + 1))
    print(f"  [warn] open-meteo fetch failed for {cell.key()}: {last_err}", flush=True)
    return None


def open_meteo_to_states(payload: dict[str, Any], cell: GridCell, horizon_end: datetime) -> list[ForecastState]:
    h = payload.get("hourly", {})
    times: list[str] = h.get("time", []) or []
    if not times:
        return []
    n = len(times)

    def col(name: str) -> list:
        v = h.get(name) or []
        return list(v) + [None] * (n - len(v))

    t2m = col("temperature_2m")
    rh = col("relative_humidity_2m")
    td = col("dewpoint_2m")
    p = col("surface_pressure")
    pr = col("precipitation")
    ws = col("wind_speed_10m")
    wd = col("wind_direction_10m")
    cape = col("cape")
    lpi = col("lightning_potential")

    out: list[ForecastState] = []
    prev_p: float | None = None
    prev_dt: datetime | None = None
    now = datetime.now(timezone.utc)
    for i, ts in enumerate(times):
        try:
            dt = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc) if "+" not in ts and "Z" not in ts else datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            continue
        if dt < now - timedelta(hours=1):
            continue
        if dt > horizon_end:
            continue
        if t2m[i] is None or rh[i] is None or td[i] is None or p[i] is None:
            continue

        rh_frac = float(rh[i]) / 100.0 if float(rh[i]) > 1.5 else float(rh[i])
        trend: float | None = None
        if prev_p is not None and prev_dt is not None:
            dt_h = max(1.0, (dt - prev_dt).total_seconds() / 3600.0)
            trend = (float(p[i]) - prev_p) / dt_h

        state = ForecastState.from_dict({
            "timestamp": dt.isoformat(),
            "latitude": cell.lat,
            "longitude": cell.lon,
            "surface_temp_c": float(t2m[i]),
            "relative_humidity": rh_frac,
            "surface_dewpoint_c": float(td[i]),
            "surface_pressure_hpa": float(p[i]),
            "surface_pressure_trend_hpa_per_hour": trend,
            "precipitable_water_mm": None,
            "low_level_moisture_g_m3": None,
            "wind_speed_m_s": float(ws[i]) if ws[i] is not None else 0.0,
            "wind_direction_deg": float(wd[i]) if wd[i] is not None else 0.0,
            "precip_mm": float(pr[i]) if pr[i] is not None else 0.0,
            "lightning_potential_j_kg": float(lpi[i]) if lpi[i] is not None else None,
            "lightning_flashes_per_hour": None,
            "graphcast_cape_j_kg": float(cape[i]) if cape[i] is not None else None,
        })
        out.append(state)
        prev_p = float(p[i])
        prev_dt = dt
    return out


def predict_cell(cell: GridCell, hours: int) -> CellForecast | None:
    horizon_end = datetime.now(timezone.utc) + timedelta(hours=hours)
    payload = fetch_open_meteo(cell, hours)
    if payload is None:
        return None
    states = open_meteo_to_states(payload, cell, horizon_end)
    if not states:
        return None
    twin = RoofHunterWeatherTwin(states)
    history = twin.simulate()
    if not history:
        return None

    peak_idx = max(range(len(history)), key=lambda k: history[k]["hail_probability"])
    peak = history[peak_idx]
    return CellForecast(
        cell=cell,
        peak_hail_probability=float(peak["hail_probability"]),
        peak_risk_score=float(peak["risk_score"]),
        peak_time_utc=datetime.fromisoformat(peak["timestamp"]),
        peak_hail_core_confidence=float(peak["hail_core_confidence"] or 0.0),
        peak_hail_core_radius_ft=float(peak["hail_core_radius_ft"] or 0.0),
        peak_cape_j_kg=float(peak.get("effective_cape_j_kg") or 0.0),
        peak_lightning_potential=peak.get("lightning_potential_j_kg"),
        n_hours=len(history),
    )


def run_forecasts(cells: list[GridCell], hours: int, max_workers: int) -> dict[str, CellForecast]:
    out: dict[str, CellForecast] = {}
    print(f"forecasting {len(cells)} grid cells over the next {hours} h...", flush=True)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(predict_cell, c, hours): c for c in cells}
        done = 0
        for fut in as_completed(futures):
            cell = futures[fut]
            done += 1
            try:
                cf = fut.result()
            except Exception as e:
                print(f"  [warn] cell {cell.key()} failed: {e}", flush=True)
                continue
            if cf is None:
                continue
            out[cell.key()] = cf
            if done % 5 == 0 or done == len(cells):
                print(f"  ... {done}/{len(cells)} cells forecasted", flush=True)
    return out


def write_strike_csv(
    out_path: Path,
    rows: list[dict[str, Any]],
    args: argparse.Namespace,
    n_cells_total: int,
    n_cells_severe: int,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "rank",
        "peak_hail_probability",
        "peak_risk_score",
        "peak_time_utc",
        "hours_until_peak",
        "hail_core_radius_ft",
        "hail_core_confidence",
        "peak_cape_j_kg",
        "peak_lightning_potential",
        "verified_full_address",
        "verified_lat",
        "verified_lon",
        "address_resolution_status",
        "is_residential_likely",
        "gmaps_url",
        "street_address",
        "city",
        "state",
        "zip_code",
        "homeowner_name",
        "phone_number",
        "has_phone",
        "address_grade",
        "address_grade_reasons",
        "email",
        "damage_score",
        "contact_id",
        "event_id",
        "storm_event_date",
        "forecast_cell_lat",
        "forecast_cell_lon",
        "storm_lat",
        "storm_lon",
        "distance_to_cell_km",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        f.write(
            f"# 24h hail-strike call list. Generated {datetime.now(timezone.utc).isoformat()} (UTC). "
            f"--hours={args.hours} --min-prob={args.min_prob} --top={args.top}"
            f"{' --with-phone' if args.with_phone else ''}"
            f"{' --state=' + ','.join(args.state) if args.state else ''}. "
            f"{n_cells_severe}/{n_cells_total} forecast cells crossed the floor.\n"
        )
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in columns})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--state", type=lambda s: [x.strip() for x in s.split(",") if x.strip()], default=None,
                    help="Comma-separated states to include (TX,OK,KS,...)")
    ap.add_argument("--with-phone", action="store_true", help="Only include contacts that have a phone number")
    ap.add_argument("--allow-grades", type=lambda s: {x.strip() for x in s.split(",") if x.strip()},
                    default={"real", "no_phone"},
                    help="Comma-separated address grades to keep: real,no_phone,fake_zip,fake_phone,unusable. "
                         "Default: real,no_phone (drops Faker-generated junk).")
    ap.add_argument("--hours", type=int, default=24, help="Forecast horizon in hours (default 24)")
    ap.add_argument("--grid-deg", type=float, default=0.25, help="Forecast grid resolution in degrees (default 0.25)")
    ap.add_argument("--min-prob", type=float, default=0.5, help="Minimum peak hail probability to keep a cell")
    ap.add_argument("--top", type=int, default=25, help="Cap output rows; 0 = no cap")
    ap.add_argument("--max-contacts-per-cell", type=int, default=10,
                    help="Cap how many contacts to emit from a single forecast cell so one storm doesn't flood the list")
    ap.add_argument("--max-workers", type=int, default=4, help="Concurrent Open-Meteo requests")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true", help="Skip forecast calls, just report cell counts")
    ap.add_argument("--no-resolve-addresses", dest="resolve_addresses", action="store_false",
                    help="Skip Census Geocoder address verification (default: resolve so every row is searchable)")
    ap.set_defaults(resolve_addresses=True)
    ap.add_argument("--keep-unresolvable", action="store_true",
                    help="Keep rows the Census Geocoder cannot resolve (default: drop them so the call list is searchable)")
    ap.add_argument("--keep-municipal", action="store_true",
                    help="Keep municipal/civic placeholder addresses (e.g. '200 3rd St, Manhattan KS') even though they look like city-hall rows")
    args = ap.parse_args()

    if not args.db.exists():
        print(f"ERROR: db not found: {args.db}", file=sys.stderr)
        return 2

    print(f"loading contacts from {args.db.relative_to(REPO) if args.db.is_relative_to(REPO) else args.db}", flush=True)
    contacts_all = load_contacts(args.db, args.state, args.with_phone)
    grade_breakdown: dict[str, int] = {}
    for c in contacts_all:
        grade_breakdown[c.address_grade] = grade_breakdown.get(c.address_grade, 0) + 1
    print(f"  contacts joinable to lat/lon: {len(contacts_all)}", flush=True)
    print(f"  address-quality grades: {dict(sorted(grade_breakdown.items()))}", flush=True)
    contacts = [c for c in contacts_all if c.address_grade in args.allow_grades]
    print(f"  contacts after --allow-grades={sorted(args.allow_grades)}: {len(contacts)}", flush=True)
    if not contacts:
        print("nothing to score after grade filter; widen --allow-grades or check the DB. exiting.", flush=True)
        return 0

    cell_to_contacts: dict[str, list[ContactRow]] = {}
    cells_by_key: dict[str, GridCell] = {}
    for c in contacts:
        cell = bucket_to_grid(c.storm_lat, c.storm_lon, args.grid_deg)
        cell_to_contacts.setdefault(cell.key(), []).append(c)
        cells_by_key.setdefault(cell.key(), cell)
    cells = list(cells_by_key.values())
    print(f"  unique forecast cells: {len(cells)} (grid={args.grid_deg}°)", flush=True)

    if args.dry_run:
        print("dry-run; skipping forecast calls", flush=True)
        return 0

    forecasts = run_forecasts(cells, args.hours, args.max_workers)
    print(f"  forecasts returned for {len(forecasts)}/{len(cells)} cells", flush=True)

    severe = {k: cf for k, cf in forecasts.items() if cf.peak_hail_probability >= args.min_prob}
    print(f"  cells crossing min_prob={args.min_prob}: {len(severe)}", flush=True)
    if not severe:
        print("no cell exceeded the floor; emitting empty CSV anyway for audit", flush=True)

    rows: list[dict[str, Any]] = []
    now_utc = datetime.now(timezone.utc)
    for key, cf in severe.items():
        cell_contacts = cell_to_contacts[key]
        cell_contacts.sort(
            key=lambda c: (
                -(c.damage_score or 0.0),
                -1 if c.phone_number else 0,
                c.contact_id,
            )
        )
        for c in cell_contacts[: args.max_contacts_per_cell]:
            hours_until = round((cf.peak_time_utc - now_utc).total_seconds() / 3600.0, 2)
            rows.append({
                "peak_hail_probability": round(cf.peak_hail_probability, 3),
                "peak_risk_score": round(cf.peak_risk_score, 3),
                "peak_time_utc": cf.peak_time_utc.isoformat(),
                "hours_until_peak": hours_until,
                "hail_core_radius_ft": round(cf.peak_hail_core_radius_ft, 1),
                "hail_core_confidence": round(cf.peak_hail_core_confidence, 3),
                "peak_cape_j_kg": round(cf.peak_cape_j_kg, 1),
                "peak_lightning_potential": (
                    round(cf.peak_lightning_potential, 1) if cf.peak_lightning_potential is not None else ""
                ),
                "street_address": c.street_address,
                "city": c.storm_city,
                "state": c.storm_state,
                "zip_code": c.zip_code,
                "homeowner_name": c.homeowner_name,
                "phone_number": c.phone_number,
                "has_phone": "yes" if c.phone_number else "no",
                "address_grade": c.address_grade,
                "address_grade_reasons": c.address_grade_reasons,
                "email": c.email,
                "damage_score": c.damage_score if c.damage_score is not None else "",
                "contact_id": c.contact_id,
                "event_id": c.event_id,
                "storm_event_date": c.storm_event_date,
                "forecast_cell_lat": round(cf.cell.lat, 4),
                "forecast_cell_lon": round(cf.cell.lon, 4),
                "storm_lat": round(c.storm_lat, 5),
                "storm_lon": round(c.storm_lon, 5),
                "distance_to_cell_km": round(haversine_km(c.storm_lat, c.storm_lon, cf.cell.lat, cf.cell.lon), 2),
            })

    grade_rank = {"real": 0, "no_phone": 1, "fake_zip": 2, "fake_phone": 3, "unusable": 4}
    rows.sort(
        key=lambda r: (
            grade_rank.get(r["address_grade"], 5),
            -float(r["peak_hail_probability"]),
            -float(r["peak_risk_score"]),
            -float(r["damage_score"] or 0),
            0 if r["has_phone"] == "yes" else 1,
        )
    )

    if args.resolve_addresses:
        cache = AddressCache()
        resolved_rows: list[dict[str, Any]] = []
        skipped_unresolvable = 0
        skipped_municipal = 0
        target = args.top if args.top and args.top > 0 else len(rows)
        print(f"resolving addresses against US Census Geocoder (target {target} keepers)...", flush=True)
        for r in rows:
            if len(resolved_rows) >= target:
                break
            res = resolve_one(r["street_address"], r["city"], r["state"], r["zip_code"], cache=cache)
            r["verified_full_address"] = res.matched_address
            r["verified_lat"] = round(res.latitude, 6) if res.matched_address else ""
            r["verified_lon"] = round(res.longitude, 6) if res.matched_address else ""
            r["address_resolution_status"] = res.resolution_status
            r["is_residential_likely"] = "yes" if res.is_residential_likely else "no"
            r["gmaps_url"] = res.gmaps_url() if res.matched_address else ""

            if res.resolution_status in ("unresolvable_no_street", "no_match", "geocoder_unreachable"):
                if not args.keep_unresolvable:
                    skipped_unresolvable += 1
                    continue
            elif res.resolution_status == "resolved_municipal" and not args.keep_municipal:
                skipped_municipal += 1
                continue
            resolved_rows.append(r)
        cache.flush()
        print(
            f"  resolved keepers: {len(resolved_rows)} | "
            f"skipped unresolvable: {skipped_unresolvable} | "
            f"skipped municipal placeholders: {skipped_municipal}",
            flush=True,
        )
        rows = resolved_rows
    else:
        for r in rows:
            r["verified_full_address"] = ""
            r["verified_lat"] = ""
            r["verified_lon"] = ""
            r["address_resolution_status"] = "skipped"
            r["is_residential_likely"] = ""
            r["gmaps_url"] = ""
        if args.top and args.top > 0:
            rows = rows[: args.top]

    for i, row in enumerate(rows, start=1):
        row["rank"] = i

    if args.out is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%MZ")
        args.out = DEFAULT_OUT_DIR / f"predicted_24h_hail_strikes_{stamp}.csv"

    write_strike_csv(args.out, rows, args, len(cells), len(severe))
    print(f"\nwrote {len(rows)} ranked strike rows -> {args.out}", flush=True)
    if rows:
        top5 = rows[: min(5, len(rows))]
        print("\ntop strikes (worst first):")
        print(f"  {'#':>2}  {'p_hail':>6}  {'risk':>5}  {'eta_h':>6}  {'cape':>5}  searchable address")
        for r in top5:
            addr = r.get("verified_full_address") or f"{r['street_address']}, {r['city']} {r['state']} {r['zip_code']}"
            print(
                f"  {r['rank']:>2}  {r['peak_hail_probability']:>6.3f}  "
                f"{r['peak_risk_score']:>5.3f}  {r['hours_until_peak']:>6.2f}  "
                f"{int(r['peak_cape_j_kg']):>5}  {addr}"
            )
            if r.get("gmaps_url"):
                print(f"      {r['gmaps_url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
