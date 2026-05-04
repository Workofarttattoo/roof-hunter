"""Lead score from damage signals + proximity to ingested NOAA/SPC hail reports."""

from __future__ import annotations

import math
from typing import Sequence


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def nearest_hail_miles(lat: float, lng: float, storms: Sequence[tuple[float, float, float]]) -> tuple[float, float]:
    """
    storms: list of (lat, lng, hail_inches)
    Returns (distance_miles, max_hail_nearby_inches within 50mi consider)
    """
    if not storms:
        return 999.0, 0.0
    best_d = 1e9
    best_hail = 0.0
    for slat, slng, inches in storms:
        d = haversine_miles(lat, lng, slat, slng)
        if d < best_d:
            best_d = d
        if d <= 50 and inches > best_hail:
            best_hail = inches
    return best_d, best_hail


def compute_lead_score(
    *,
    damage_prob_0_1: float,
    lat: float,
    lng: float,
    storms: Sequence[tuple[float, float, float]],
    priority_boost: float = 0.0,
) -> tuple[float, float]:
    """
    Returns (damage_index_0_100, lead_score_0_1).
    """
    dmg = max(0.0, min(1.0, float(damage_prob_0_1)))
    idx = round(dmg * 100, 2)

    dist, hail = nearest_hail_miles(lat, lng, storms)
    storm_factor = 0.0
    if dist <= 15:
        storm_factor = 0.25 + min(0.2, hail / 20.0)
    elif dist <= 40:
        storm_factor = 0.12 + min(0.1, hail / 25.0)

    score = min(1.0, dmg * 0.55 + storm_factor + min(0.15, priority_boost))
    return idx, round(score, 4)
