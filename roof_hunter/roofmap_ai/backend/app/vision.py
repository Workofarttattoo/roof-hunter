"""
Computer-vision interface for roof damage. Replace StubRoofDamageModel with YOLO weights later.
"""

from __future__ import annotations

import os
import random
import sys
from typing import Any, Protocol


class RoofDamageModel(Protocol):
    def predict(self, image_url: str) -> dict[str, Any]: ...


class StubRoofDamageModel:
    """Deterministic-enough stub; swap for YOLO without changing API contracts."""

    def predict(self, image_url: str) -> dict[str, Any]:
        seed = sum(ord(c) for c in image_url) % 997
        rng = random.Random(seed)
        hail = rng.uniform(0.45, 0.94)
        return {
            "hail_damage": hail,
            "missing_shingles": rng.choice([True, False]),
            "confidence": 0.87,
            "backend": "stub",
        }


class YoloRoofDamageModel:
    """
    Production path: same stack as aws_discovery_worker / ai_damage_engine.
    Requires: pip install -r requirements-vision.txt and optional ROOF_YOLO_WEIGHTS.
    """

    def predict(self, image_url: str) -> dict[str, Any]:
        root = os.getenv("ROOF_HUNTER_ROOT", "").strip()
        if root:
            src = os.path.join(root, "src")
            if src not in sys.path:
                sys.path.insert(0, src)
        from yolo_detector import infer_from_url

        out = infer_from_url(image_url)
        dp = float(out.get("damage_percent", 0))
        hm = max(0.0, min(1.0, float(out.get("hail_damage", dp / 100.0))))
        return {
            "hail_damage": hm,
            "missing_shingles": dp > 38.0,
            "confidence": float(out.get("confidence_score", 0.75)),
            "backend": out.get("backend", "vision"),
            "damage_percent": dp,
            "detection_count": len(out.get("detections") or []),
            "note": out.get("note"),
        }


def get_model(backend: str) -> RoofDamageModel:
    b = (backend or "stub").lower()
    if b == "yolo":
        try:
            return YoloRoofDamageModel()
        except Exception:
            return StubRoofDamageModel()
    return StubRoofDamageModel()
