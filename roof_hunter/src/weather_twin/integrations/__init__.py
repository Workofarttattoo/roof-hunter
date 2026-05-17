"""QuLab proprietary atmospheric engines for Roof Hunter (no third-party model bridges)."""

from .global_outlook_engine import (
    enrich_forecast_outlook,
    hail_potential_from_cape_cin,
    merge_graphcast_into_forecast_dicts,
)
from .mesoscale_downscale_engine import (
    apply_corrdiff_patch_to_state,
    apply_mesoscale_patch_to_state,
    refine_surface_dict,
)
from .qu_atmospheric_pipeline import enrich_forecast_payload
from .satellite_nowcast_engine import (
    enrich_forecast_satellite,
    lightning_severe_hail_boost,
    merge_lightning_severe_into_forecast_dicts,
    satellite_hail_nowcast_boost,
    satellite_hail_nowcast_from_row,
)

__all__ = [
    "enrich_forecast_payload",
    "enrich_forecast_outlook",
    "enrich_forecast_satellite",
    "hail_potential_from_cape_cin",
    "merge_graphcast_into_forecast_dicts",
    "merge_lightning_severe_into_forecast_dicts",
    "lightning_severe_hail_boost",
    "satellite_hail_nowcast_boost",
    "satellite_hail_nowcast_from_row",
    "refine_surface_dict",
    "apply_mesoscale_patch_to_state",
    "apply_corrdiff_patch_to_state",
]
