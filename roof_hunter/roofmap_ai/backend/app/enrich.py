from __future__ import annotations


def enrich_property(address: str) -> dict:
    _ = address
    return {
        "owner": "UNKNOWN",
        "estimated_value": 350_000,
        "roof_age": 12,
    }


def geocode_stub(address: str) -> tuple[float, float]:
    """Replace with Google/Mapbox geocoding using server key."""
    _ = address
    return 35.4676, -97.5164
