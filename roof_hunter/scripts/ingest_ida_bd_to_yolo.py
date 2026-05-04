#!/usr/bin/env python3
"""
Ingest DesignSafe PRJ-3563 (Ida-BD) tiles + semantic masks into YOLO detection format.

Expected layout (after full download / unzip — not manifest-only):
  <ida_root>/data/images/*_post_disaster.png
  <ida_root>/data/masks/<same_basename>.png

Masks follow the xBD-style ordinal damage scale (see Ida-BD_description.pdf):
  0 background, 1 no damage, 2 minor, 3 major, 4 destroyed
  (If your files differ, run once with --inspect to print unique pixel values.)

Schemas:
  ida   — 4 classes: ida_no_damage, ida_minor, ida_major, ida_destroyed
  roof  — map into training/dataset.yaml class ids (proxy): minor→wind_uplift,
          major/destroyed→shingle_loss; no_damage and background skipped.

Example:
  python3 scripts/ingest_ida_bd_to_yolo.py \\
    --ida-root /Users/noone/Downloads/PRJ-3563/Project--ida-bd-.../PRJ-3563 \\
    --schema ida --seed 42

Then train:
  python3 scripts/train_roof_damage_yolo.py --data training/dataset_ida_bd.yaml
  # or --data training/dataset_ida_roof_proxy.yaml for roof-class proxy
"""

from __future__ import annotations

import argparse
import os
import random
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]

# Ida-BD / xBD semantic mask values
BG = 0
NO_DAMAGE = 1
MINOR = 2
MAJOR = 3
DESTROYED = 4

# roof proxy: target class index in training/dataset.yaml (hail_hit=0, wind_uplift=1, …)
ROOF_PROXY = {
    MINOR: 1,  # wind_uplift
    MAJOR: 2,  # shingle_loss
    DESTROYED: 2,  # shingle_loss
}

# native Ida classes → YOLO class index
IDA_NATIVE = {
    NO_DAMAGE: 0,
    MINOR: 1,
    MAJOR: 2,
    DESTROYED: 3,
}


def load_semantic_mask(path: Path) -> np.ndarray:
    m = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if m is None:
        raise FileNotFoundError(path)
    if m.ndim == 3:
        if m.shape[2] >= 3:
            m = cv2.cvtColor(m[:, :, :3], cv2.COLOR_BGR2GRAY)
        else:
            m = m[:, :, 0]
    return m.astype(np.int32)


def yolo_line(cls: int, xyxy: tuple[float, float, float, float], w: int, h: int) -> str:
    x1, y1, x2, y2 = xyxy
    bw = max(1e-6, x2 - x1)
    bh = max(1e-6, y2 - y1)
    cx = (x1 + x2) / 2.0 / w
    cy = (y1 + y2) / 2.0 / h
    nw = bw / w
    nh = bh / h
    cx = min(1.0, max(0.0, cx))
    cy = min(1.0, max(0.0, cy))
    nw = min(1.0, max(0.0, nw))
    nh = min(1.0, max(0.0, nh))
    return f"{cls} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}"


def components_to_boxes(mask: np.ndarray, damage_value: int, min_area: int) -> list[tuple[int, int, int, int]]:
    binm = (mask == damage_value).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(binm, connectivity=8)
    boxes: list[tuple[int, int, int, int]] = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if area < min_area:
            continue
        boxes.append((x, y, x + bw, y + bh))
    return boxes


def ingest(
    ida_root: Path,
    out_root: Path,
    schema: str,
    val_ratio: float,
    seed: int,
    min_area: int,
    dry_run: bool,
) -> None:
    images_dir = ida_root / "data" / "images"
    masks_dir = ida_root / "data" / "masks"
    if not images_dir.is_dir():
        print(
            f"Missing {images_dir}\n"
            "Ida-BD must be fully downloaded (data/images/, data/masks/). "
            "A manifest-only folder is not enough — re-download from DesignSafe PRJ-3563.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not masks_dir.is_dir():
        print(f"Missing {masks_dir}", file=sys.stderr)
        sys.exit(1)

    post_tiles = sorted(images_dir.glob("*_post_disaster.png"))
    if not post_tiles:
        print(f"No *_post_disaster.png under {images_dir}", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    rng.shuffle(post_tiles)
    n_val = max(1, int(len(post_tiles) * val_ratio)) if len(post_tiles) > 5 else 1
    val_set = set(post_tiles[:n_val])

    img_train = out_root / "images" / "train"
    img_val = out_root / "images" / "val"
    lbl_train = out_root / "labels" / "train"
    lbl_val = out_root / "labels" / "val"
    for d in (img_train, img_val, lbl_train, lbl_val):
        if not dry_run:
            d.mkdir(parents=True, exist_ok=True)

    n_files = 0
    n_labels = 0
    for img_path in post_tiles:
        stem = img_path.stem
        mpath = masks_dir / f"{stem}.png"
        if not mpath.is_file():
            print(f"[skip] no mask {mpath.name}", file=sys.stderr)
            continue

        mask = load_semantic_mask(mpath)
        h, w = mask.shape[:2]
        uniq = np.unique(mask)
        if not np.all((uniq >= 0) & (uniq <= 4)):
            print(
                f"[warn] {mpath.name} has values outside 0–4: {uniq.tolist()}. "
                "Check Ida-BD_description.pdf; extend mapping in ingest_ida_bd_to_yolo.py if needed.",
                file=sys.stderr,
            )

        lines: list[str] = []
        if schema == "ida":
            for dv in (NO_DAMAGE, MINOR, MAJOR, DESTROYED):
                cls = IDA_NATIVE[dv]
                for x1, y1, x2, y2 in components_to_boxes(mask, dv, min_area):
                    lines.append(yolo_line(cls, (x1, y1, x2, y2), w, h))
        else:
            for dv in (MINOR, MAJOR, DESTROYED):
                cls = ROOF_PROXY[dv]
                for x1, y1, x2, y2 in components_to_boxes(mask, dv, min_area):
                    lines.append(yolo_line(cls, (x1, y1, x2, y2), w, h))

        split_val = img_path in val_set
        id_dst = img_val if split_val else img_train
        lb_dst = lbl_val if split_val else lbl_train

        if dry_run:
            n_files += 1
            n_labels += len(lines)
            continue

        dest_img = id_dst / img_path.name
        shutil.copy2(img_path, dest_img)
        lab_file = lb_dst / f"{stem}.txt"
        lab_file.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        n_files += 1
        n_labels += len(lines)

    print(
        f"Ingest {'(dry-run) ' if dry_run else ''}schema={schema}: "
        f"{n_files} images → {out_root} | ~{n_labels} total boxes"
    )
    if schema == "roof":
        print(
            "Roof proxy: only minor/major/destroyed become boxes; "
            "minor→wind_uplift, major+destroyed→shingle_loss. "
            "Fine for satellite-scale hurricane damage — not hail granule detail."
        )


def main() -> None:
    p = argparse.ArgumentParser(description="Ida-BD (PRJ-3563) → YOLO bbox labels")
    p.add_argument(
        "--ida-root",
        type=Path,
        default=None,
        help="Folder containing data/images and data/masks (full unzip, not manifest-only)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output dataset root (images/train|val, labels/train|val)",
    )
    p.add_argument("--schema", choices=("ida", "roof"), default="ida", help="ida=native 4-class; roof=proxy to dataset.yaml")
    p.add_argument("--val-ratio", type=float, default=0.15)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--min-area", type=int, default=80, help="Min connected-component area in pixels")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--inspect",
        type=Path,
        default=None,
        help="Print unique values for one mask PNG and exit",
    )
    args = p.parse_args()

    if args.inspect:
        m = load_semantic_mask(args.inspect)
        print(f"{args.inspect}: shape={m.shape} unique={np.unique(m).tolist()}")
        return

    ida = args.ida_root
    if ida is None:
        env = os.environ.get("IDA_BD_ROOT")
        ida = Path(env) if env else Path(
            "/Users/noone/Downloads/PRJ-3563/Project--ida-bd-pre-and-post-disaster-high-resolution-satellite-imagery-for-building-damage-assessment-from-hurricane-ida"
        )
    ida = ida.expanduser().resolve()

    out = args.out
    if out is None:
        out = (
            REPO / "training_data" / "yolo_ida_roof_proxy"
            if args.schema == "roof"
            else REPO / "training_data" / "yolo_ida_bd"
        )
    out = out.expanduser().resolve()

    ingest(ida, out, args.schema, args.val_ratio, args.seed, args.min_area, args.dry_run)


if __name__ == "__main__":
    main()
