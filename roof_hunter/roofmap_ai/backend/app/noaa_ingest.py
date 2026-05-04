"""NOAA SPC filtered hail CSV snapshot (same public feeds as Ridgeline live ingest)."""

from __future__ import annotations

import csv
import io
from typing import Any

import httpx

SPC_TODAY = "https://www.spc.noaa.gov/climo/reports/today_filtered_hail.csv"
SPC_YESTERDAY = "https://www.spc.noaa.gov/climo/reports/yesterday_filtered_hail.csv"

HEADERS = {
    "User-Agent": "RoofMapAI/1.0 (https://github.com/roof-hunter/roof_hunter; storm intel)",
}


def _rows_from_csv(text: str, label: str) -> list[dict[str, Any]]:
    out = []
    r = csv.DictReader(io.StringIO(text))
    for row in r:
        try:
            lat = float(row.get("Lat") or row.get("lat") or 0)
            lon = float(row.get("Lon") or row.get("lon") or 0)
            size_raw = float(row.get("Size") or 0)
        except (TypeError, ValueError):
            continue
        if not lat or not lon:
            continue
        inches = size_raw / 100.0 if size_raw > 0 else 0.0
        out.append(
            {
                "label": label,
                "lat": lat,
                "lon": lon,
                "hail_inches": inches,
                "location": (row.get("Location") or "").strip(),
                "state": (row.get("State") or "").strip(),
                "time": (row.get("Time") or "").strip(),
            }
        )
    return out


async def fetch_spc_hail_rows() -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30.0, headers=HEADERS) as client:
        merged: list[dict[str, Any]] = []
        for url, label in ((SPC_TODAY, "today"), (SPC_YESTERDAY, "yesterday")):
            try:
                res = await client.get(url)
                if res.status_code == 200:
                    merged.extend(_rows_from_csv(res.text, label))
            except httpx.HTTPError:
                continue
        return merged


def fetch_spc_hail_rows_sync() -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    with httpx.Client(timeout=30.0, headers=HEADERS) as client:
        for url, label in ((SPC_TODAY, "today"), (SPC_YESTERDAY, "yesterday")):
            try:
                res = client.get(url)
                if res.status_code == 200:
                    merged.extend(_rows_from_csv(res.text, label))
            except httpx.HTTPError:
                continue
    return merged
