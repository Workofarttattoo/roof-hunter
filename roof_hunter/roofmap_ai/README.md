# RoofMap AI / Ridgeline AI

Nearmap-style **map + AI lead scoring** stack: **FastAPI** (Render), **React + Leaflet** (Vercel), **PostgreSQL** (Supabase). NOAA **SPC filtered hail** CSVs seed storm context for scoring.

## Architecture

| Layer | Stack |
|--------|--------|
| API | FastAPI, SQLAlchemy 2, `DATABASE_URL` (Supabase Postgres) |
| Map UI | Vite, React 19, react-leaflet, dark Carto basemap (swap for Nearmap/Mapbox tiles + key) |
| Vision | `app/vision.py` — **stub** today; implement `YoloRoofDamageModel` when weights exist |
| Ingest | `POST /ingest/noaa/hail-snapshot` pulls SPC today+yesterday hail ≥1″ into `storm_reports` |
| Scoring | `app/scoring.py` — damage probability + distance to recent hail |

## Backend API (`roofmap_ai/backend`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| POST | `/property` | Geocode stub + vision + **lead_score**; optional `save: true` → `leads` |
| GET | `/imagery` | Tile URL template (+ lat/lng) |
| GET | `/damage-score` | Vision + scoring by `property_id` |
| POST | `/damage/predict` | Raw vision dict from `image_url` |
| POST | `/ingest/noaa/hail-snapshot` | Replace SPC snapshot in DB |
| GET | `/leads/map` | Pins for the map |
| GET | `/leads/{id}` | One lead |
| POST | `/leads` | Create lead |
| GET | `/export/csv` | **Call-agent** CSV (sorted by `lead_score`) |

### Local run

Use **Python 3.11 or 3.12** (3.14 may fail to build `pydantic-core` until wheels ship).

```bash
cd roofmap_ai/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set DATABASE_URL to Supabase (Session mode URI recommended for serverless pools)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Supabase:** Project → Settings → Database → copy **URI** (SQLAlchemy: `postgresql+psycopg2://...`). If SSL required, append `?sslmode=require` as needed.

Tables are created on startup (`Base.metadata.create_all`). For production migrations, add Alembic later.

### Deploy — Render

1. New **Web Service** → connect repo.
2. **Root directory:** `roofmap_ai/backend`
3. **Build:** `pip install -r requirements.txt`
4. **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. **Environment:** `DATABASE_URL`, `CORS_ORIGINS=https://your-vercel-app.vercel.app` (comma-separated if multiple)

Optional: connect [Blueprint](https://render.com/docs/blueprint-spec) using `roofmap_ai/render.yaml` at repo root (adjust `rootDir` if your layout differs).

## Frontend (`roofmap_ai/frontend`)

```bash
cd roofmap_ai/frontend
npm install
cp .env.example .env.local
# VITE_API_URL=https://roofmap-ai-api.onrender.com
npm run dev
```

### Deploy — Vercel

- **Root directory:** `roofmap_ai/frontend`
- **Build:** `npm run build`
- **Output:** `dist`
- **Env:** `VITE_API_URL` = your Render API URL

`vercel.json` includes SPA rewrites.

## Integrating Ridgeline Python workers

The main `roof_hunter` repo already has `src/live_hail_ingest.py`, `src/aws_lead_sync.py`, etc. You can:

- Run NOAA ingest on a schedule and `POST` batches into RoofMap, or
- Share one Postgres and read `contacts` / `storms` from SQLAlchemy models in a follow-up PR.

## Real roof CV (YOLO + texture)

The legacy path used **COCO `yolov8n`** boxes as “damage,” which is misleading on aerial roofs.

1. On AWS / workers: `pip install -r requirements-vision.txt` (repo root).
2. Train or obtain a **roof/hail/shingle** Ultralytics `.pt` (Roboflow, internal fine-tune, etc.).
3. Set **`ROOF_YOLO_WEIGHTS=/path/to/best.pt`**.
4. Optional: **`ROOF_DAMAGE_CLASS_IDS=0,1`** (class indices that count as damage).
5. Without weights, `RoofDeepLens` in `src/yolo_detector.py` runs **mask + Laplacian heuristic** only (no fake COCO scores).

`src/ai_damage_engine.py` and Ridgeline `POST /damage/predict` use the same stack for **http(s) image URLs**.

### RoofMap API (`app/vision.py`)

Set **`ROOF_HUNTER_ROOT`** to this monorepo root on the server so `VISION_BACKEND=yolo` can import `src/yolo_detector.py`, and add the vision packages alongside `roofmap_ai/backend/requirements.txt`.

## License / compliance

Outbound dialing and PII use are your responsibility; CSV export is for licensed call workflows.
