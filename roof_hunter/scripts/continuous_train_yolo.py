#!/usr/bin/env python3
"""
Continuous-ish fine-tune orchestrator for roof_hunter YOLO models.

This script:
  1) Finds the newest usable base weights (best.pt) under runs/damage, or falls back to yolov8n.pt
  2) Verifies candidate datasets exist and have training images
  3) Launches repeated fine-tune passes via scripts/train_roof_damage_yolo.py

Usage examples:
  python3 scripts/continuous_train_yolo.py --cycles 2 --epochs 30
  python3 scripts/continuous_train_yolo.py --dataset training/dataset_ida_roof_proxy.yaml --cycles 1
"""

from __future__ import annotations

import argparse
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRAIN_SCRIPT = REPO / "scripts" / "train_roof_damage_yolo.py"
RUNS_DIR = REPO / "runs" / "damage"

DEFAULT_DATASETS = [
    REPO / "training" / "dataset.yaml",
    REPO / "training" / "dataset_ida_roof_proxy.yaml",
    REPO / "training" / "dataset_ida_bd.yaml",
]


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def discover_latest_weights() -> str:
    candidates = sorted(RUNS_DIR.glob("**/weights/best.pt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if candidates:
        return str(candidates[0])
    return "yolov8n.pt"


def parse_dataset_root(dataset_yaml: Path) -> Path | None:
    if not dataset_yaml.exists():
        return None
    root_rel = None
    for line in dataset_yaml.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line.startswith("path:"):
            root_rel = line.split(":", 1)[1].strip()
            break
    if not root_rel:
        return None
    rp = Path(root_rel)
    return rp if rp.is_absolute() else (dataset_yaml.parent / rp).resolve()


def train_image_count(dataset_yaml: Path) -> int:
    root = parse_dataset_root(dataset_yaml)
    if not root:
        return 0
    train_dir = root / "images" / "train"
    if not train_dir.is_dir():
        return 0
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    return sum(1 for p in train_dir.iterdir() if p.suffix.lower() in exts)


def pick_best_dataset(preferred: Path | None) -> Path:
    if preferred:
        return preferred
    scored = []
    for ds in DEFAULT_DATASETS:
        scored.append((train_image_count(ds), ds))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuous fine-tune runner for roof damage YOLO")
    parser.add_argument("--cycles", type=int, default=1, help="How many sequential train runs")
    parser.add_argument("--epochs", type=int, default=25, help="Epochs per cycle")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=-1)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dataset", type=Path, default=None, help="Optional explicit dataset yaml path")
    parser.add_argument("--base-model", default=None, help="Optional explicit base model/weights path")
    parser.add_argument("--dry-run", action="store_true", help="Print planned commands only")
    args = parser.parse_args()

    if not TRAIN_SCRIPT.exists():
        raise SystemExit(f"Missing train script: {TRAIN_SCRIPT}")

    dataset = pick_best_dataset(args.dataset.resolve() if args.dataset else None)
    if not dataset.exists():
        raise SystemExit(f"Dataset yaml missing: {dataset}")

    n_train = train_image_count(dataset)
    if n_train < 1:
        raise SystemExit(f"Dataset has no train images: {dataset}")

    base_model = args.base_model or discover_latest_weights()
    print(f"[verify] dataset: {dataset} (train images: {n_train})")
    print(f"[verify] base model: {base_model}")

    previous = base_model
    for i in range(1, args.cycles + 1):
        run_name = f"cont_{_ts()}_c{i}"
        cmd = [
            "python3",
            str(TRAIN_SCRIPT),
            "--data",
            str(dataset),
            "--model",
            previous,
            "--epochs",
            str(args.epochs),
            "--imgsz",
            str(args.imgsz),
            "--batch",
            str(args.batch),
            "--device",
            str(args.device),
            "--project",
            str(RUNS_DIR),
            "--name",
            run_name,
        ]
        print(f"[cycle {i}] {' '.join(cmd)}")
        if args.dry_run:
            continue

        env = dict(os.environ)
        subprocess.run(cmd, cwd=str(REPO), env=env, check=True)
        produced = RUNS_DIR / run_name / "weights" / "best.pt"
        if not produced.exists():
            raise SystemExit(f"Training cycle {i} did not produce {produced}")
        previous = str(produced)
        print(f"[cycle {i}] best: {produced}")

    print(f"\nDone. Latest fine-tuned weights: {previous}")
    print(f"export ROOF_YOLO_WEIGHTS='{previous}'")


if __name__ == "__main__":
    main()

