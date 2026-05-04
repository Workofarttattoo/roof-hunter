# Train roof / storm damage YOLO (for `ROOF_YOLO_WEIGHTS`)

**GPU:** the script picks **CUDA → Apple MPS → CPU** automatically (`--device auto`, default).

```bash
cd /path/to/roof_hunter
python3 -m venv .venv-train && source .venv-train/bin/activate   # Windows: .venv-train\Scripts\activate
pip install -r requirements-vision.txt
python3 scripts/train_roof_damage_yolo.py --preflight   # optional: shows device + image counts
```

### Verify GPU (optional)

Short run on built-in COCO128 (not your roof classes — only checks the stack):

```bash
python3 scripts/train_roof_damage_yolo.py --demo-gpu --epochs 2
```

### Real roof training

1. **Collect & label** — [labeling_guide.md](./labeling_guide.md); **where to find hi-res imagery** — [IMAGE_SOURCES.md](./IMAGE_SOURCES.md)
   - **Ida-BD (DesignSafe PRJ-3563):** fully download the archive so you have `data/images/` and `data/masks/` (a `manifest-sha512.txt`–only folder is not enough). Then:
     `python3 scripts/ingest_ida_bd_to_yolo.py --ida-root /path/to/unzipped/project --schema ida`
     or `--schema roof` for proxy labels into [dataset_ida_roof_proxy.yaml](./dataset_ida_roof_proxy.yaml). Train with `--data training/dataset_ida_bd.yaml` or `dataset_ida_roof_proxy.yaml`.
2. **Files:** `training_data/yolo/images/train/`, `.../val/`, matching `labels/train/*.txt`, `labels/val/*.txt`
3. **Train**

```bash
python3 scripts/train_roof_damage_yolo.py --epochs 100 --model yolov8n.pt
# NVIDIA: uses CUDA device 0 automatically
# Apple Silicon: uses MPS; if OOM use `--batch 4` or `--imgsz 512`
```

4. **Use weights**

```bash
export ROOF_YOLO_WEIGHTS="$PWD/runs/damage/train/weights/best.pt"
./scripts/run_discovery_worker.sh
```

**Roboflow:** YOLOv8 export → merge into `training_data/yolo/` (match class order in [dataset.yaml](./dataset.yaml) or edit the yaml).
