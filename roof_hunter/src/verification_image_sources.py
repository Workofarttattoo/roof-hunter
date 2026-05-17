"""
Multi-provider verification chips for lead/geo coordinates.

Tries imagery sources in priority order (OpenAerialMap thumbnail, optional Google Static Maps).
Writes bytes to disk callers control; integrates with RoofDeepLens in verify_lead_imagery CLI.

TODO: stitch LiDAR / stereo height products when pipeline is wired (this module is 2D-first).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from oam_harvester import OAMHarvester

logger = logging.getLogger(__name__)

_DEFAULT_UA = "RoofHunter-VerificationImagery/1.0 (+https://github.com/roof-hunter/roof_hunter)"


def _http_headers() -> dict[str, str]:
    return {"User-Agent": os.getenv("ROOF_HTTP_USER_AGENT", _DEFAULT_UA)}


def _looks_like_png(data: bytes) -> bool:
    return len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n"


def _looks_like_jpeg(data: bytes) -> bool:
    return len(data) >= 3 and data[:3] == b"\xff\xd8\xff"


@dataclass(frozen=True)
class VerificationImageResult:
    """First successful imagery fetch."""

    path: Path
    source_id: str
    source_url: str
    license_note: str
    content_type: str | None


def fetch_oam_thumbnail_chip(
    lat: float,
    lon: float,
    *,
    out_path: Path,
    bbox_buffer: float = 0.02,
    timeout_s: float = 60.0,
) -> VerificationImageResult | None:
    """
    Download PNG preview from OpenAerialMap scene metadata when coverage exists.
    """
    harvester = OAMHarvester()
    meta = harvester.get_best_image(lat, lon, buffer=bbox_buffer)
    if not meta or not meta.get("url"):
        return None

    dl = str(meta["url"])
    r = requests.get(dl, headers=_http_headers(), timeout=timeout_s)
    if r.status_code != 200:
        logger.warning("OAM download failed (%s): %s", r.status_code, dl[:160])
        return None
    data = r.content
    if len(data) < 400 or (not _looks_like_png(data) and not _looks_like_jpeg(data)):
        logger.warning("OAM response was tiny or non-image (%s bytes) for %s", len(data), dl[:120])
        return None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)

    suffix = meta.get("download_kind") or "oam"
    vid = f"oam_{suffix}"
    lic = meta.get("license") or "OpenAerialMap scene — verify license on Meta page"
    page = meta.get("scene_page_url") or dl[:500]
    return VerificationImageResult(
        path=out_path,
        source_id=vid,
        source_url=str(page),
        license_note=str(lic),
        content_type=r.headers.get("content-type"),
    )


def fetch_google_static_satellite(
    lat: float,
    lon: float,
    *,
    out_path: Path,
    zoom: int = 20,
    size_px: int = 640,
    api_key: str | None = None,
    timeout_s: float = 45.0,
) -> VerificationImageResult | None:
    api_key = (api_key or os.getenv("GOOGLE_MAPS_API_KEY") or "").strip()
    if not api_key:
        return None

    url = "https://maps.googleapis.com/maps/api/staticmap"
    params = {
        "center": f"{lat},{lon}",
        "zoom": int(zoom),
        "size": f"{size_px}x{size_px}",
        "maptype": "satellite",
        "key": api_key,
    }
    r = requests.get(url, params=params, headers=_http_headers(), timeout=timeout_s)
    if r.status_code != 200:
        logger.warning("[info] verification imagery: google_static_maps http=%s", r.status_code)
        return None
    ctype = r.headers.get("content-type") or ""
    data = r.content
    # Google returns JPEG for satellite static maps frequently
    if not _looks_like_png(data) and not _looks_like_jpeg(data) and "image/" not in ctype.lower():
        logger.warning("[info] verification imagery: google returned non-image content-type=%s", ctype[:80])
        return None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    target = out_path
    if _looks_like_jpeg(data) and out_path.suffix.lower() != ".jpg":
        target = out_path.with_suffix(".jpg")
    elif _looks_like_png(data) and out_path.suffix.lower() not in (".png",):
        target = out_path.with_suffix(".png")

    target.write_bytes(data)
    return VerificationImageResult(
        path=target,
        source_id="google_static_satellite",
        source_url=f"google_static_maps:z{zoom}:{size_px}px@{lat:.5f},{lon:.5f}",
        license_note="Google Maps Static API — adhere to Maps/Google terms for your billing key.",
        content_type=r.headers.get("content-type"),
    )


def fetch_best_verification_image(
    lat: float,
    lon: float,
    *,
    out_path: Path,
    zoom: int = 20,
    size_px: int = 640,
    oam_bbox_buffer: float = 0.02,
) -> VerificationImageResult | None:
    """
    Try imagery providers in order; stop after first usable chip on disk.

    Order: OpenAerialMap thumbnail → Google Static (when ``GOOGLE_MAPS_API_KEY`` is set).
    """
    oam_res = fetch_oam_thumbnail_chip(lat, lon, out_path=out_path, bbox_buffer=oam_bbox_buffer)
    if oam_res:
        logger.info("[info] verification imagery: winning_source=%s wrote=%s", oam_res.source_id, oam_res.path)
        return oam_res

    g_path = Path(out_path)
    gg = fetch_google_static_satellite(lat, lon, out_path=g_path, zoom=zoom, size_px=size_px)
    if gg:
        logger.info("[info] verification imagery: winning_source=%s wrote=%s", gg.source_id, gg.path)
        return gg

    logger.warning("[info] verification imagery: no provider returned imagery for (%s,%s)", lat, lon)
    return None


def append_proof_msg_verification_line(existing: str | None, payload: dict[str, Any]) -> str:
    line = "[VERIFY_IMG] " + json.dumps(payload, separators=(",", ":"), sort_keys=True)
    if not existing:
        return line
    if line in existing:
        return existing
    return existing.rstrip() + "\n" + line


def append_image_findings_verification(existing: str | None, narrative: str) -> str:
    block = narrative.strip()
    if not existing:
        return block
    if block in existing:
        return existing
    return existing.rstrip() + "\n" + block
