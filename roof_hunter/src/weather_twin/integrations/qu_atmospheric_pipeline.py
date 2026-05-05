"""QuLab end-to-end forecast row enrichment before ``RoofHunterWeatherTwin`` simulation."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from roof_hunter.integrations.global_outlook_engine import enrich_forecast_outlook
from roof_hunter.integrations.satellite_nowcast_engine import enrich_forecast_satellite


async def enrich_forecast_payload_async(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run enrichment engines in parallel to reduce lead time.
    """
    rows = list(payload.get("forecast", []))

    # Create copies of rows for each engine to ensure thread safety
    # as each engine might try to create its own dict copies.
    rows_for_outlook = [dict(r) for r in rows]
    rows_for_satellite = [dict(r) for r in rows]

    # Run both heavy-compute enrichments at the same time
    # This effectively cuts the processing lead time in half
    task_outlook = asyncio.to_thread(enrich_forecast_outlook, rows_for_outlook)
    task_satellite = asyncio.to_thread(enrich_forecast_satellite, rows_for_satellite)

    # Wait for both to finish
    rows_outlook, rows_satellite = await asyncio.gather(task_outlook, task_satellite)

    # Merge the results back into a single row set
    for i in range(len(rows)):
        rows[i].update(rows_outlook[i])
        rows[i].update(rows_satellite[i])

    return {"forecast": rows}


def enrich_forecast_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Apply QuLab global outlook + satellite nowcast enrichment to each forecast row."""
    return asyncio.run(enrich_forecast_payload_async(payload))
