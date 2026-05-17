"""
Optional Azure Digital Twins (ADT) state-graph sink for Roof Hunter.

When ADT credentials and instance URL are not configured, updates are appended as
JSON lines to ``AZURE_DT_SNAPSHOT_LOG`` (default: ``roof_hunter_adt_snapshots.jsonl``)
so you can replay or forward them later.

Environment (optional live push):
  AZURE_ADT_INSTANCE_URL   e.g. https://<name>.api.<region>.digitaltwins.azure.net
  AZURE_ADT_TWIN_ID        Digital twin ID (UUID or custom model id path)
  AZURE_ADT_MODEL_ID       Optional, for create operations (not used in patch-only mode)

For ``DefaultAzureCredential`` you need Azure CLI login, managed identity, or env vars
as documented by Microsoft — install ``azure-digitaltwins-core`` and ``azure-identity``.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def build_state_patch(
    *,
    latitude: float,
    longitude: float,
    run_label: str,
    nexrad_dual_pol_summary: Dict[str, Any],
    noaa_forecast_summary: Dict[str, Any],
    nws_alert_summary: Dict[str, Any],
    iot_summary: Dict[str, Any],
    satellite_property_summary: Dict[str, Any],
    calibration_summary: Dict[str, Any],
    twin_history_tail: list[Dict[str, Any]],
) -> Dict[str, Any]:
    """Shape a DTDL-compatible JSON-merge patch fragment (telemetry-style properties)."""
    return {
        "lastRunUtc": datetime.now(timezone.utc).isoformat(),
        "runLabel": run_label,
        "location": {"lat": latitude, "lon": longitude},
        "noaaForecast": noaa_forecast_summary,
        "nwsActiveAlerts": nws_alert_summary,
        "nexradDualPolFeatures": nexrad_dual_pol_summary,
        "iotNeighborhood": iot_summary,
        "satelliteRoofSurface": satellite_property_summary,
        "calibrationInspectionOrClaim": calibration_summary,
        "twinHistoryTail": twin_history_tail[:48],
    }


def persist_or_patch_twin(patch: Dict[str, Any]) -> None:
    log_path = Path(os.getenv("AZURE_DT_SNAPSHOT_LOG") or "roof_hunter_adt_snapshots.jsonl").resolve()
    adt_url = (os.getenv("AZURE_ADT_INSTANCE_URL") or "").strip().rstrip("/")
    twin_id = (os.getenv("AZURE_ADT_TWIN_ID") or "").strip()

    line = json.dumps(patch, separators=(",", ":"), default=str)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    logger.info("ADT snapshot written to %s", log_path)

    if not adt_url or not twin_id:
        return

    try:
        from azure.digitaltwins.core import DigitalTwinsClient  # type: ignore[import-untyped]
        from azure.identity import DefaultAzureCredential  # type: ignore[import-untyped]
    except ImportError:
        logger.warning(
            "AZURE_ADT_INSTANCE_URL set but azure-digitaltwins-core/azure-identity not installed; skipping live patch."
        )
        return

    patch_doc = [{"op": "replace", "path": "/lastRoofHunterTelemetry", "value": patch}]
    try:
        client = DigitalTwinsClient(adt_url, DefaultAzureCredential())
        client.update_digital_twin(twin_id, patch_doc)
        logger.info("Patched twin %s on %s", twin_id, adt_url)
    except Exception as e:
        try:
            client.update_digital_twin(
                twin_id, [{"op": "add", "path": "/lastRoofHunterTelemetry", "value": patch}]
            )
            logger.info("Added lastRoofHunterTelemetry on twin %s", twin_id)
        except Exception as e2:
            logger.warning("ADT patch failed (snapshot still on disk): %s | fallback: %s", e, e2)
