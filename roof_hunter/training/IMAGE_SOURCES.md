# Roof / storm imagery — where to get it (research stitch)

This doc ties **what your model needs** ([labeling_guide.md](./labeling_guide.md), [dataset.yaml](./dataset.yaml)) to **real sources**, ordered roughly by **useful resolution for roof detail** (not all sources show individual shingles).

## What you need (for this repo)

| Need | Why |
|------|-----|
| **Nadir or gently oblique** roof views | Matches drone / ladder / satellite workflows in `labeling_guide.md`. |
| **Post-event preferred** | Hail/wind cues are event-linked; mixing eras without domain tags confuses the model. |
| **6 classes** (`hail_hit`, `wind_uplift`, `shingle_loss`, `ridge_vent_damage`, `metal_dent_crease`, `tree_debris_strike`) | Public sets rarely use this exact taxonomy — plan to **remap labels** or **use unlabeled hi-res + manual box**. |
| **YOLO text labels** per image | Same stem as image under `training_data/yolo/labels/{train,val}/`. |

**Resolution reality check**

- **~0.6 m (NAIP-class)** — good for **building / roof extent**, weak for **granule loss / tab lifts** unless the damage is large (major shingle loss, blown-off sections).
- **~0.3 m or better** — better for **patch-level** damage from above; still not textbook “hail map” close-ups.
- **~5–15 cm (typical open drone ortho)** — often **usable** for hail-ish texture and wind rows if lighting is good.
- **Ground / ladder / near-roof drone** — **best** for the cues in `labeling_guide.md` (pockmarks, seal breaks, ridge cap). These rarely ship as a perfect public benchmark; **Roboflow + partner uploads + your own flights** fill the gap.

---

## 1. Fastest path: pre-labeled object detection (Roboflow Universe)

Good for **bootstrapping**; check **each dataset’s license** on the dataset page before commercial use.

**Search hubs**

- [Roboflow — hail / roof damage search](https://universe.roboflow.com/search?q=hail%20damage)
- [Roboflow — roof damage](https://universe.roboflow.com/search?q=roof%20damage)

**Concrete examples (verify counts & license on the live page)**

- [hail damage batches](https://universe.roboflow.com/remote-roofing/hail-damage-batches) — smaller remote-roof style batch.
- [roof-hail-damage (DelDetect)](https://universe.roboflow.com/deldetect/roof-hail-damage) — larger hail-focused set (often cited in Universe search).
- [roof damage (Chase Omoso)](https://universe.roboflow.com/chase-omoso/roof-damage-vz2qc-8btog/dataset/1) — mixed roof damage boxes; export **YOLOv8** and merge classes to match [dataset.yaml](./dataset.yaml).

**Stitch strategy:** Download YOLOv8 zip → align class indices with `training/dataset.yaml` (or edit the yaml once to match the export) → copy into `training_data/yolo/` train/val split (~85/15 by address or random with seed).

---

## 2. Highest-quality **free** orthophoto you can actually browse (often ~10–30 cm)

**OpenAerialMap (OAM)** — community UAV/satellite uploads; many tiles **list GSD in cm** in metadata.

- Site: [https://openaerialmap.org/](https://openaerialmap.org/)
- Browser: [https://map.openaerialmap.org/](https://map.openaerialmap.org/)
- API metadata pattern (for automation): `https://api.openaerialmap.org/meta/` (filter by bbox; check `gsd`, `uuid`, `license` per image)

**Workflow:** Pick tiles over **residential hail-prone regions** after known events (news + date filter if metadata has acquisition date) → download GeoTIFF → crop chips in QGIS or a small Python script → label in [CVAT](https://www.cvat.ai/) or Roboflow.

---

## 3. Broad US coverage, moderate resolution (good context + weak fine detail)

**NAIP (National Agriculture Imagery Program)** — typically **~0.6 m** GSD (some campaigns / states may vary; coastal programs sometimes finer).

- USGS overview: [https://www.usgs.gov/centers/eros/science/usgs-eros-archive-aerial-photography-national-agriculture-imagery-program-naip](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-aerial-photography-national-agriculture-imagery-program-naip)
- **Download:** [EarthExplorer](https://earthexplorer.usgs.gov/) → select NAIP → AOI by lat/lon or shapefile.

**USGS HRO** — “1 m or finer” ortho in places; still not drone grade for shingle bruising.

- [https://www.usgs.gov/centers/eros/science/usgs-eros-archive-aerial-photography-high-resolution-orthoimagery-hro](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-aerial-photography-high-resolution-orthoimagery-hro)

**State / regional GIS** — often **beats NAIP locally** (Texas STRATMAP, regional hubs across other states). Search: `{your state} orthoimagery GIS download` and prefer **leaf-off / spring** or **post-storm** captures when available.

---

## 4. Coastal US — extra hi-res free ortho stacks

**NOAA Digital Coast — High Resolution Orthoimagery**

- [https://coast.noaa.gov/digitalcoast/data/highresortho.html](https://coast.noaa.gov/digitalcoast/data/highresortho.html)

Useful when your lead geography intersects the coast and you want **sub-meter to decimeter-class** public mosaics where available.

---

## 5. Post-disaster **satellite** chips (roof cues at “major damage” scale)

Labels are usually **damage grade / polygon**, not your six YOLO classes — still valuable for **destroyed roof / debris / missing roof** and for pretraining.

**xBD** (building damage, ordinal labels; large community benchmark)

- Paper: [arXiv:1911.09296](https://arxiv.org/abs/1911.09296)
- Imagery is distributed in **fixed chip sizes** (commonly cited **1024×1024** at varying native GSD depending on source); use official download mirrors you trust (search “xBD dataset download” and prefer **academic / AWS / established mirrors**).
- **Stitch:** treat as **pretrain or auxiliary head**, or mine chips where roofs show **major** loss and hand-relabel a subset into your 6 classes.

**DesignSafe / event collections** — e.g. Hurricane Ida hi-res stacks (search DesignSafe public projects for “Ida” + building damage). Good for **paired pre/post** if you do change detection later.

- **Ida-BD (PRJ-3563)** — [DesignSafe PRJ-3563](https://www.designsafe-ci.org/data/browser/public/designsafe.storage.published/PRJ-3563): ~0.5 m/pixel WorldView-2 pairs; PNG masks with xBD-style damage levels (0–4). After full download you should see `data/images/` and `data/masks/`. In this repo:
  `python3 scripts/ingest_ida_bd_to_yolo.py --ida-root /path/to/unzipped --schema ida`
  then `python3 scripts/train_roof_damage_yolo.py --data training/dataset_ida_bd.yaml …`
  (`--schema roof` + [dataset_ida_roof_proxy.yaml](./dataset_ida_roof_proxy.yaml) maps minor→`wind_uplift`, major/destroyed→`shingle_loss` — a coarse proxy for satellite hurricane context only.)

**Maxar Open Data (disaster releases)** — very high native resolution **when** released for an event; NOT global continuous coverage.

- Registry: [https://registry.opendata.aws/maxar-open-data/](https://registry.opendata.aws/maxar-open-data/)

Use for **specific storm dates**; clip roof-centered tiles; label a small gold set for hail/wind nuance.

---

## 6. “Examples” gallery mindset (not always downloadable training)

- **News / insurer / contractor galleries** — great **visual references** for label consistency; often **not licensed** for model training. Use for **annotate guidelines**, not bulk scraping without rights.
- **Storm chaser video frames** — technically hi-res but **legal + motion blur** issues; only with explicit permission.

---

## 7. Suggested stack (practical order)

1. **Roboflow Universe** exports → get **hundreds** of boxed roof examples quickly; fix class mapping.
2. **OpenAerialMap** drone ortho → add **decimeter-class** geography over your **hail belts** (OK/TX/etc.).
3. **NAIP / state ortho** → **balance geography** and add **healthy vs damaged context** crops.
4. **xBD or Maxar event chips** → **hard negatives / destroyed roof** and severe weather generalization.
5. **Your own drone or contractor feed** → gold standard for **granule / bruise / seal-strip** cues.

---

## 8. Import → train (repo commands)

After images + YOLO `labels/*.txt` are in `training_data/yolo/`:

```bash
source .venv-train/bin/activate   # or your venv
pip install -r requirements-vision.txt
python3 scripts/train_roof_damage_yolo.py --preflight
python3 scripts/train_roof_damage_yolo.py --epochs 100 --model yolov8n.pt
```

---

## Disclaimer

Imagery **licenses differ** (CC-BY, government open data, commercial restrictions). Verify **redistribution and commercial inference** before production. This document is research stitching for engineering planning, not legal advice.
