"""
Roof damage inference for aerial/roof tiles.

- Set ROOF_YOLO_WEIGHTS to a trained Ultralytics .pt (hail/shingle classes) for real detections.
- Without weights: **heuristic-only** mode (texture inside a roof-colored mask) — avoids scoring
  COCO unrelated objects as damage (common failure mode with stock yolov8n on AWS).

Env:
  ROOF_YOLO_WEIGHTS   Path to custom .pt or hub id (e.g. yolo11n-seg.pt) — custom roboflow exports OK
  ROOF_YOLO_CONF      Confidence threshold (default 0.25)
  ROOF_DAMAGE_CLASS_IDS  Comma list of class indices to treat as damage (empty = all boxes in custom mode)
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _parse_class_ids(raw: str) -> set[int] | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    out = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out or None


class RoofDeepLens:
    """
    YOLO when custom weights are configured; otherwise roof-masked texture heuristic.
    """

    def __init__(self, model_path: str | None = None):
        self.model_path = (model_path or os.getenv("ROOF_YOLO_WEIGHTS", "")).strip()
        self.conf = float(os.getenv("ROOF_YOLO_CONF", "0.25"))
        self.damage_class_ids = _parse_class_ids(os.getenv("ROOF_DAMAGE_CLASS_IDS", ""))
        self.detector = None

        if self.model_path:
            try:
                from ultralytics import YOLO

                self.detector = YOLO(self.model_path)
                logger.info("YOLO loaded: %s", self.model_path)
            except Exception as e:
                logger.error("YOLO load failed (%s): %s", self.model_path, e)
                self.detector = None

    def detect_and_quantify(self, image_path: str | Path) -> dict[str, Any]:
        path = str(image_path)
        heur_pct = self.calculate_damage_percentage(path)

        if not self.detector:
            return {
                "status": "success",
                "damage_percent": heur_pct,
                "hail_damage": min(1.0, heur_pct / 100.0),
                "detections": [],
                "confidence_score": 0.65,
                "backend": "heuristic",
                "note": "Set ROOF_YOLO_WEIGHTS to your trained roof/hail model for detector-based scoring.",
            }

        results = self.detector(path, conf=self.conf, verbose=False)
        detections: list[dict[str, Any]] = []
        box_score = self._damage_fraction_from_boxes(results, path)

        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cid = int(box.cls)
                if self.damage_class_ids is not None and cid not in self.damage_class_ids:
                    continue
                detections.append(
                    {
                        "class": cid,
                        "conf": float(box.conf),
                        "xyxy": box.xyxy.tolist()[0],
                    }
                )

        # Blend: custom boxes + heuristic texture (helps when model misses diffuse hail)
        if box_score > 0:
            merged = min(100.0, box_score * 0.65 + heur_pct * 0.35)
        else:
            merged = heur_pct

        det_conf = max((d["conf"] for d in detections), default=0.0)
        return {
            "status": "success",
            "damage_percent": round(float(merged), 2),
            "hail_damage": min(1.0, float(merged) / 100.0),
            "detections": detections,
            "confidence_score": round(min(0.97, 0.55 + 0.4 * det_conf + 0.05 * (merged / 100)), 3),
            "backend": "yolo",
            "heuristic_percent": heur_pct,
            "box_percent": round(box_score, 2) if box_score else 0.0,
        }

    def _damage_fraction_from_boxes(self, results, image_path: str) -> float:
        img = cv2.imread(image_path)
        if img is None or not results:
            return 0.0
        h, w = img.shape[:2]
        area_img = float(h * w)
        if area_img <= 0:
            return 0.0

        weighted = 0.0
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cid = int(box.cls)
                if self.damage_class_ids is not None and cid not in self.damage_class_ids:
                    continue
                xyxy = box.xyxy[0].cpu().numpy()
                bw = max(0.0, float(xyxy[2] - xyxy[0]))
                bh = max(0.0, float(xyxy[3] - xyxy[1]))
                ba = bw * bh
                conf = float(box.conf)
                weighted += ba * conf

        return min(100.0, (weighted / area_img) * 100.0)

    def calculate_damage_percentage(self, image_path: str) -> float:
        """
        Texture chaos on roof-colored pixels only (no COCO boxes required).
        Tune `var / 35.0` with your imagery provider (ArcGIS, Nearmap, etc.).
        """
        img = cv2.imread(image_path)
        if img is None:
            return 0.0

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        _h, s, v = cv2.split(hsv)

        roof_mask = cv2.inRange(s, 12, 200)
        roof_mask = cv2.bitwise_and(roof_mask, cv2.inRange(v, 35, 245))
        roof_mask = cv2.morphologyEx(roof_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

        if cv2.countNonZero(roof_mask) < max(80, int(0.002 * img.shape[0] * img.shape[1])):
            roof_mask = np.ones((img.shape[0], img.shape[1]), dtype=np.uint8) * 255

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        roi = lap[roof_mask > 0]
        if roi.size == 0:
            return 0.0
        var = float(np.clip(roi.var(), 0, 5000))
        score = float(np.clip(var / 35.0, 0, 100))
        return round(score, 2)

    def analyze_structural_lean(self, image_path: str) -> float:
        img = cv2.imread(image_path)
        if img is None:
            return 0.0
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
        if lines is None:
            return 0.0
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angles.append(float(np.degrees(np.arctan2(y2 - y1, x2 - x1))))
        return round(float(np.std(angles)), 2)


def infer_from_url(url: str, timeout: float = 45.0) -> dict[str, Any]:
    """Download image to a temp file, run RoofDeepLens, delete temp file."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        lens = RoofDeepLens()
        return lens.detect_and_quantify(url)

    headers = {
        "User-Agent": "RoofHunter-Vision/1.0 (roof damage; +https://github.com/roof-hunter/roof_hunter)",
    }
    r = requests.get(url, timeout=timeout, headers=headers)
    r.raise_for_status()
    ctype = (r.headers.get("content-type") or "").lower()
    suffix = ".jpg"
    if "png" in ctype:
        suffix = ".png"
    elif "webp" in ctype:
        suffix = ".webp"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(r.content)
        tmp.close()
        lens = RoofDeepLens()
        out = lens.detect_and_quantify(tmp.name)
        out["source_url"] = url[:500]
        return out
    finally:
        try:
            Path(tmp.name).unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        print(infer_from_url(sys.argv[1]))
