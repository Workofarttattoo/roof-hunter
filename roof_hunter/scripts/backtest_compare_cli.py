#!/usr/bin/env python3
"""
Backtest comparison: coarse archive / NOAA-ish baseline vs enriched digital-twin lane.

Feeds the in-process RoofHunterWeatherTwin (state graph parity with Azure Digital Twins
telemetry sink via ``persist_or_patch_twin``).

Baseline (coarse): Open-Meteo hourly archive OR NOAA station hourly — no GLM, no Qu enrich.

Enriched lane: optional GOES GLM flash merge, ``enrich_forecast_payload`` (outlook +
satellite-derived fields), NEXRAD dual-pol snapshot (inject ``updraft_helicity`` when
supported), satellite / IoT / calibration JSON on ``property_metadata``, NWS ``point``
alerts rollup, then ADT JSONL snapshot (+ optional Azure patch when env configured).

Examples::

  PYTHONPATH=. python3 scripts/backtest_compare_cli.py --quick --compare-reports
  PYTHONPATH=. python3 scripts/backtest_compare_cli.py --window-days 3 --glm --satellite-meta /path/to/roof_satellite_stub.json

``/path/to/roof_satellite_stub.json`` — e.g. ``{"roof_material":"asphalt","roof_age_years":18,"tree_cover_pct":22,"annual_solar_exposure_factor_0_1":0.71}``

``MOAA`` in docs is interpreted as NOAA (typo); NOAA-only coarse source is ``--source noaa``.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

# Repo layout: scripts/ sibling to validate_last_week, src/, …
_PKG_ROOT = Path(__file__).resolve().parents[1]
_MONO_ROOT = _PKG_ROOT.parent
for p in (_PKG_ROOT, _MONO_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import validate_last_week as vl  # noqa: E402
from roof_hunter.integrations.radar_engine import fetch_dual_pol_hail  # noqa: E402
from src.nws_hail_alerts import get_active_alerts_for_point  # noqa: E402
from src.weather_twin.azure_digital_twins_sink import (  # noqa: E402
    build_state_patch,
    persist_or_patch_twin,
)
from src.weather_twin.integrations.qu_atmospheric_pipeline import enrich_forecast_payload  # noqa: E402
from src.weather_twin.models import ForecastState  # noqa: E402
from src.weather_twin.roof_hunter_digital_twin import RoofHunterWeatherTwin  # noqa: E402


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("backtest_compare_cli")


def _summarize(history: list[dict[str, Any]]) -> Dict[str, Any]:
    hails = [float(s.get("hail_probability") or 0) for s in history]
    risks = [float(s.get("risk_score") or 0) for s in history]
    return {
        "steps": len(history),
        "max_hail_probability": max(hails) if hails else 0.0,
        "mean_hail_probability": round(sum(hails) / len(hails), 4) if hails else 0.0,
        "hours_hail_ge_0_35": sum(1 for x in hails if x >= 0.35),
        "hours_hail_ge_0_50": sum(1 for x in hails if x >= 0.50),
        "max_risk_score": max(risks) if risks else 0.0,
        "mean_risk_score": round(sum(risks) / len(risks), 4) if risks else 0.0,
    }


def _nws_alert_rollup(lat: float, lon: float) -> Dict[str, Any]:
    try:
        feats = get_active_alerts_for_point(lat, lon)
    except Exception as e:
        logger.warning("NWS point alerts failed: %s", e)
        return {"error": str(e), "featureCount": 0}
    headline = []
    sev_counts: Dict[str, int] = {}
    for f in feats:
        props = (f or {}).get("properties") or {}
        headline.append(props.get("event") or "Unknown")
        s = props.get("severity") or "Unknown"
        sev_counts[s] = sev_counts.get(s, 0) + 1
    return {
        "featureCount": len(feats),
        "severityCounts": sev_counts,
        "eventSample": headline[:12],
    }


def _inject_property_rows(
    rows: list[dict[str, Any]],
    *,
    base_meta: dict[str, Any] | None,
    radar_boost: dict[str, Any] | None,
) -> None:
    mesh = float((radar_boost or {}).get("max_hail_size") or 0.0)
    prob_sv = float((radar_boost or {}).get("prob_severe") or 0.0)
    refl = float((radar_boost or {}).get("reflectivity_dbz") or 0.0)

    uh = None
    if mesh > 0 or prob_sv > 0 or refl > 40:
        uh = min(299.0, 45.0 + mesh * 95.0 + prob_sv * 120.0 + max(0.0, refl - 45.0))

    lat0 = rows[0].get("latitude") if rows else None
    lon0 = rows[0].get("longitude") if rows else None
    meta: dict[str, Any] = {
        "latitude": float(lat0 or 35.0),
        "longitude": float(lon0 or -97.0),
    }
    if base_meta:
        meta.update(base_meta)
    for r in rows:
        r.setdefault("property_metadata", {})
        merged = dict(meta)
        merged.update(r["property_metadata"] or {})
        r["property_metadata"] = merged
        if uh is not None:
            r["updraft_helicity"] = uh


def _build_payload(args: argparse.Namespace, *, start_d: vl.date, end_d: vl.date) -> Dict[str, Any]:
    if args.source == "noaa":
        obs = vl.fetch_noaa_last_week_weather(args.lat, args.lon, end_d, start_d)
        return vl.build_forecast_payload_from_noaa(obs, args.lat, args.lon)
    weather_data = vl.fetch_last_week_weather(args.lat, args.lon, end_d, start_d)
    return vl.build_forecast_payload(weather_data, args.lat, args.lon)


def _run_lane(
    name: str,
    payload_in: Dict[str, Any],
    *,
    glm: bool,
    enrich_qu: bool,
    glm_radius_km: float,
    satellite_meta: dict[str, Any] | None,
    iot_meta: dict[str, Any] | None,
    calibration_meta: dict[str, Any] | None,
    radar_site: str,
    lat: float,
    lon: float,
    compare_reports: bool,
    start_d: vl.date | None,
    end_d: vl.date | None,
    report_radius_km: float,
    report_match_hours: float,
    report_match_radius_km: float,
) -> Dict[str, Any]:
    import datetime as dt

    payload = deepcopy(payload_in)
    glm_lookup = None
    if glm:
        cache = Path(".lightning_cache")
        glm_lookup = vl.build_glm_hourly_flash_lookup(
            payload["forecast"],
            lat,
            lon,
            radius_km=glm_radius_km,
            satellite="goes16",
            cache_dir=cache,
            log=lambda m: logger.info("[GLM] %s", m),
        )
    if glm_lookup:
        vl.apply_lightning_to_forecast_rows(payload["forecast"], glm_lookup, None)

    if enrich_qu:
        payload = enrich_forecast_payload(payload)

    nexrad_prop = {"latitude": lat, "longitude": lon, "nearest_radar": radar_site, "timestamp": None}
    radar_feats = fetch_dual_pol_hail(nexrad_prop) if enrich_qu else {"max_hail_size": 0, "prob_severe": 0, "reflectivity_dbz": 0, "source": "SKIPPED"}

    base_sat: Dict[str, Any] = {}
    if satellite_meta:
        base_sat.update(satellite_meta)
    # Convert 0–1 tree cover fraction to pct for vulnerability_engine if supplied
    if "tree_cover_fraction_0_1" in base_sat and "tree_cover_pct" not in base_sat:
        base_sat["tree_cover_pct"] = float(base_sat.pop("tree_cover_fraction_0_1")) * 100.0
    # IoT tweaks (surfaced on ADT; optional faint pressure imprint)
    iot_roll: Dict[str, Any] = dict(iot_meta or {})
    if iot_roll.get("neighborhood_pressure_hpa_bias"):
        bias = float(iot_roll["neighborhood_pressure_hpa_bias"])
        for row in payload["forecast"]:
            if row.get("surface_pressure_hpa") is not None:
                row["surface_pressure_hpa"] = float(row["surface_pressure_hpa"]) + bias

    cal_roll = dict(calibration_meta or {})
    if enrich_qu:
        merged_meta = {
            **base_sat,
            **{f"iot_{k}": v for k, v in iot_roll.items()},
            **{f"calibration_{k}": v for k, v in cal_roll.items()},
        }
        _inject_property_rows(payload["forecast"], base_meta=merged_meta, radar_boost=radar_feats)

    states = [ForecastState.from_dict(item) for item in payload["forecast"]]
    twin = RoofHunterWeatherTwin(states)
    history = twin.simulate()

    out: Dict[str, Any] = {
        "lane": name,
        "summary": _summarize(history),
        "radar_feats": radar_feats,
    }

    if compare_reports:
        end_eval = end_d if end_d else vl.date.today() - dt.timedelta(days=1)
        start_eval = start_d if start_d else end_eval - dt.timedelta(days=max(1, len(payload["forecast"]) // 24))
        reports = vl.fetch_spc_reports(lat, lon, start_eval, end_eval, radius_km=report_radius_km)
        out["spc_eval"] = vl.match_reports_to_forecast(
            history,
            reports,
            time_window_hours=report_match_hours,
            match_radius_km=report_match_radius_km,
        )

    alerts = _nws_alert_rollup(lat, lon)
    patch = build_state_patch(
        latitude=lat,
        longitude=lon,
        run_label=name,
        nexrad_dual_pol_summary=radar_feats,
        noaa_forecast_summary=out["summary"],
        nws_alert_summary=alerts,
        iot_summary=iot_roll if enrich_qu else {},
        satellite_property_summary=base_sat if enrich_qu else {},
        calibration_summary=cal_roll if enrich_qu else {},
        twin_history_tail=history[-8:],
    )
    persist_or_patch_twin(patch)
    out["adt_snapshot_fields"] = {
        "nwsAlerts": alerts.get("featureCount"),
        "nexrad_source": radar_feats.get("source"),
    }
    return out


def main() -> None:
    import datetime as dt

    parser = argparse.ArgumentParser(description="Compare coarse vs enriched digital-twin backtest lanes.")
    parser.add_argument("--lat", type=float, default=35.4676)
    parser.add_argument("--lon", type=float, default=-97.5164)
    parser.add_argument("--start-date", type=str, default=None, help="YYYY-MM-DD (archive start)")
    parser.add_argument("--end-date", type=str, default=None, help="YYYY-MM-DD window end")

    parser.add_argument(
        "--source",
        choices=("open-meteo", "noaa"),
        default="open-meteo",
        help="Baseline archive provider (coarse = same for both lanes unless you tune below).",
    )
    parser.add_argument("--quick", action="store_true", help="Skip GLM (fast); still can use --glm to force.")

    parser.add_argument("--glm", action="store_true", default=False, dest="glm", help="Enable GOES GLM merge (slow)")
    parser.add_argument("--glm-radius-km", type=float, default=25.0)
    parser.add_argument("--radar-site", type=str, default="KTLX")
    parser.add_argument("--satellite-meta", type=Path, default=None, help="JSON: roof_material, roof_age_years, tree_cover_pct OR tree_cover_fraction_0_1, annual_solar_exposure_factor_0_1 …")
    parser.add_argument("--iot-meta", type=Path, default=None, help="JSON: IoT/neighborhood telemetry")
    parser.add_argument("--calibration-meta", type=Path, default=None, help="JSON: inspection / claim calibration fields")

    parser.add_argument("--compare-reports", action="store_true", help="Evaluate vs SPC storm reports window")
    parser.add_argument("--report-radius-km", type=float, default=100.0)
    parser.add_argument("--report-match-radius-km", type=float, default=40.0)
    parser.add_argument("--report-match-hours", type=float, default=1.5)
    parser.add_argument("--window-days", type=int, default=7, help="Archive inclusive window when --start-date omitted")

    args = parser.parse_args()

    glm_on = args.glm if not args.quick else False

    satellite_meta = json.loads(Path(args.satellite_meta).read_text(encoding="utf-8")) if args.satellite_meta else None
    iot_meta = json.loads(Path(args.iot_meta).read_text(encoding="utf-8")) if args.iot_meta else None
    calibration_meta = (
        json.loads(Path(args.calibration_meta).read_text(encoding="utf-8")) if args.calibration_meta else None
    )

    if calibration_meta:
        yrs = calibration_meta.get("roof_age_years") or calibration_meta.get("inspector_roof_age")
        if yrs is not None:
            merged = dict(satellite_meta or {})
            merged.setdefault("roof_age", int(yrs))
            satellite_meta = merged

    end_d = vl.date.fromisoformat(args.end_date) if args.end_date else vl.date.today() - dt.timedelta(days=1)
    start_d = (
        vl.date.fromisoformat(args.start_date)
        if args.start_date
        else end_d - dt.timedelta(days=max(1, args.window_days) - 1)
    )

    base_payload = _build_payload(args, start_d=start_d, end_d=end_d)

    coarse = _run_lane(
        "baseline_coarse_archive",
        base_payload,
        glm=False,
        enrich_qu=False,
        glm_radius_km=args.glm_radius_km,
        satellite_meta=None,
        iot_meta=None,
        calibration_meta=None,
        radar_site=args.radar_site,
        lat=args.lat,
        lon=args.lon,
        compare_reports=args.compare_reports,
        start_d=start_d,
        end_d=end_d,
        report_radius_km=args.report_radius_km,
        report_match_hours=args.report_match_hours,
        report_match_radius_km=args.report_match_radius_km,
    )

    enriched = _run_lane(
        "enriched_dualpol_noaa_sat_iot_calibration",
        base_payload,
        glm=glm_on,
        enrich_qu=True,
        glm_radius_km=args.glm_radius_km,
        satellite_meta=satellite_meta,
        iot_meta=iot_meta,
        calibration_meta=calibration_meta,
        radar_site=args.radar_site,
        lat=args.lat,
        lon=args.lon,
        compare_reports=args.compare_reports,
        start_d=start_d,
        end_d=end_d,
        report_radius_km=args.report_radius_km,
        report_match_hours=args.report_match_hours,
        report_match_radius_km=args.report_match_radius_km,
    )

    bump = enriched["summary"]["max_hail_probability"] - coarse["summary"]["max_hail_probability"]
    logger.info(
        "--- RESULT --- coarse max_h=%.3f enriched max_h=%.3f Δ=%+.3f | ADT snapshots written ---",
        coarse["summary"]["max_hail_probability"],
        enriched["summary"]["max_hail_probability"],
        bump,
    )
    print(json.dumps({"baseline": coarse, "enriched": enriched}, indent=2, default=str))


if __name__ == "__main__":
    main()
