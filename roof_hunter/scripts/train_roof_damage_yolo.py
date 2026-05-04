#!/usr/bin/env python3
"""
Train Ultralytics YOLO on roof / storm damage for ROOF_YOLO_WEIGHTS.

  python3 -m venv .venv-train && source .venv-train/bin/activate
  pip install -r requirements-vision.txt
  python3 scripts/train_roof_damage_yolo.py

GPU is auto-picked: CUDA (NVIDIA) → Apple MPS → CPU.
Use --demo-gpu to run a tiny COCO128 train and confirm the GPU works (not a roof model).

Output: runs/damage/<name>/weights/best.pt — set env ROOF_YOLO_WEIGHTS to that path.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def default_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "0"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def resolve_dataset_root(data_yaml: Path) -> Path | None:
    """Parse dataset YAML for `path:` relative to this yaml file."""
    root_rel = None
    for line in data_yaml.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line.startswith("path:"):
            root_rel = line.split(":", 1)[1].strip()
            break
    if not root_rel:
        return None
    p = Path(root_rel)
    return p.resolve() if p.is_absolute() else (data_yaml.parent / p).resolve()


def count_split_images(root: Path, split: str) -> int:
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    d = root / "images" / split
    if not d.is_dir():
        return 0
    return sum(1 for p in d.iterdir() if p.suffix.lower() in exts)


def main() -> None:
    p = argparse.ArgumentParser(description="Train YOLO for roof storm damage (Ultralytics)")
    p.add_argument(
        "--data",
        type=Path,
        default=REPO / "training" / "dataset.yaml",
        help="YOLO data YAML (default: training/dataset.yaml)",
    )
    p.add_argument("--model", default="yolov8n.pt", help="Base checkpoint (yolov8n/s/m, yolo11n.pt, …)")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=-1, help="-1 = auto batch (recommended for GPU memory)")
    p.add_argument("--project", type=Path, default=REPO / "runs" / "damage")
    p.add_argument("--name", default="train")
    p.add_argument(
        "--device",
        default="auto",
        help="auto | 0 | cuda:0 | mps | cpu",
    )
    p.add_argument(
        "--demo-gpu",
        action="store_true",
        help="Ignore roof dataset; run 2 quick epochs on built-in coco128 to verify GPU (downloads ~1 dataset).",
    )
    p.add_argument(
        "--preflight",
        action="store_true",
        help="Only print device + image counts, then exit.",
    )
    args = p.parse_args()

    try:
        import torch
        from ultralytics import YOLO
    except ImportError:
        print("Install: pip install -r requirements-vision.txt", file=sys.stderr)
        sys.exit(1)

    dev = args.device
    if dev == "auto":
        dev = default_device()

    print(f"PyTorch {torch.__version__} | device selected: {dev}")
    if dev == "0" or str(dev).startswith("cuda"):
        print(f"  CUDA device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'n/a'}")
    elif dev == "mps":
        print("  Using Apple Metal (MPS). If OOM, pass --batch 4 or --imgsz 512.")

    if args.preflight:
        data_path = args.data.resolve()
        if data_path.is_file() and not args.demo_gpu:
            root = resolve_dataset_root(data_path)
            if root:
                nt = count_split_images(root, "train")
                nv = count_split_images(root, "val")
                print(f"Dataset root: {root}")
                print(f"  train images: {nt} | val images: {nv}")
        sys.exit(0)

    if args.demo_gpu:
        model = YOLO(args.model)
        print("Running GPU smoke train on coco128 (not your roof classes — verification only).")
        model.train(
            data="coco128.yaml",
            epochs=min(3, max(1, args.epochs)),
            imgsz=min(416, args.imgsz),
            batch=8 if dev == "mps" else 16,
            project=str(args.project.resolve()),
            name="coco128_gpu_smoke",
            device=dev,
            patience=5,
            exist_ok=True,
        )
        best = args.project.resolve() / "coco128_gpu_smoke" / "weights" / "best.pt"
        print(f"\nSmoke done. Weights: {best}")
        print("Now add labeled images under training_data/yolo/ and run without --demo-gpu.")
        return

    data_path = args.data.resolve()
    if not data_path.is_file():
        print(f"Missing data YAML: {data_path}", file=sys.stderr)
        print("Create images/labels under training_data/yolo/ — see training/labeling_guide.md", file=sys.stderr)
        sys.exit(1)

    root = resolve_dataset_root(data_path)
    if root:
        nt = count_split_images(root, "train")
        nv = count_split_images(root, "val")
        print(f"Dataset root: {root} | train={nt} val={nv} images")
        if nt < 1:
            print(
                "No training images found. Add files to training_data/yolo/images/train/ (+ labels), "
                "or run with --demo-gpu to test your GPU.",
                file=sys.stderr,
            )
            sys.exit(1)
        if nv < 1:
            print("Warning: no val images — split some into images/val/ for meaningful metrics.", file=sys.stderr)

    batch = args.batch
    if batch == -1:
        batch = 4 if dev == "mps" else 16

    model = YOLO(args.model)
    model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=batch,
        project=str(args.project.resolve()),
        name=args.name,
        device=dev,
        patience=25,
        exist_ok=True,
    )

    best = args.project.resolve() / args.name / "weights" / "best.pt"
    print(f"\nDone. Best weights: {best}")
    print(f"export ROOF_YOLO_WEIGHTS={best}")


if __name__ == "__main__":
    main()
