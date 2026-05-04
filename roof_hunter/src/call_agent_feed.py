"""
Normalize CRM / pipeline objects into voice-agent payloads (Bland request_data, ElevenLabs vars).

`damage_score` may be a 0–1 probability (e.g. 0.82) or already a 0–100 style index.
"""

from __future__ import annotations

from typing import Any


def damage_as_percent(damage_score: float) -> float:
    """Treat values in (0,1] as fractions; otherwise assume percent already."""
    x = float(damage_score)
    if 0 <= x <= 1.0:
        return round(x * 100, 2)
    return round(x, 2)


def feed_to_bland_request_data(
    *,
    name: str,
    address: str,
    damage_score: float,
    priority: str,
    script_type: str,
) -> dict[str, str]:
    pct = damage_as_percent(damage_score)
    parts = (name or "").strip().split(None, 1)
    first = parts[0] if parts else "Homeowner"
    dmg_str = str(int(pct)) if pct == int(pct) else str(pct)
    return {
        "first_name": first,
        "homeowner_name": name,
        "property_address": address,
        "damage_probability": dmg_str,
        "lead_priority": priority,
        "script_type": script_type,
        "hail_date": "",
        "hail_size": "",
        "city": "",
        "state": "",
        "storm_type": "hail",
        "structures_hit": "",
        "image_findings": "",
    }


def feed_to_elevenlabs_dynamic_variables(
    *,
    name: str,
    address: str,
    damage_score: float,
    priority: str,
    script_type: str,
) -> dict[str, str]:
    pct = damage_as_percent(damage_score)
    return {
        "contact_name": name,
        "property_address": address,
        "damage_probability": str(pct),
        "lead_priority": priority,
        "script_type": script_type,
    }


def normalize_call_agent_feed(payload: dict[str, Any]) -> dict[str, Any]:
    """Build all shapes from a single incoming feed dict."""
    name = str(payload.get("name") or "")
    address = str(payload.get("address") or "")
    damage_score = float(payload.get("damage_score") or 0)
    priority = str(payload.get("priority") or "")
    script_type = str(payload.get("script_type") or "")
    return {
        "bland_request_data": feed_to_bland_request_data(
            name=name,
            address=address,
            damage_score=damage_score,
            priority=priority,
            script_type=script_type,
        ),
        "elevenlabs_dynamic_variables": feed_to_elevenlabs_dynamic_variables(
            name=name,
            address=address,
            damage_score=damage_score,
            priority=priority,
            script_type=script_type,
        ),
    }
