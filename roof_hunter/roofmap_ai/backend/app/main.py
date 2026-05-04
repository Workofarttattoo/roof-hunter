from __future__ import annotations

import csv
import io
import json
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, init_db
from app.enrich import enrich_property, geocode_stub
from app.models import Lead, StormReport
from app import noaa_ingest
from app.schemas import (
    DamagePredictRequest,
    IngestResult,
    LeadCreate,
    LeadRead,
    PropertyRequest,
    PropertyResponse,
)
from app.scoring import compute_lead_score
from app.vision import get_model

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()


def _storms_as_tuples(db: Session) -> list[tuple[float, float, float]]:
    rows = db.execute(select(StormReport.lat, StormReport.lng, StormReport.hail_inches)).all()
    return [(float(r[0]), float(r[1]), float(r[2])) for r in rows]


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


@app.post("/property", response_model=PropertyResponse)
def post_property(body: PropertyRequest, db: Session = Depends(get_db)):
    lat, lng = geocode_stub(body.address)
    enrichment = enrich_property(body.address)
    model = get_model(settings.vision_backend)
    vis = model.predict(body.image_url or body.address)
    damage_prob = float(vis.get("hail_damage", 0.5))

    storms = _storms_as_tuples(db)
    dmg_idx, lead_sc = compute_lead_score(
        damage_prob_0_1=damage_prob,
        lat=lat,
        lng=lng,
        storms=storms,
    )

    lead_id = None
    if body.save:
        row = Lead(
            address=body.address,
            name=body.name,
            lat=lat,
            lng=lng,
            damage_index=dmg_idx,
            lead_score=lead_sc,
            image_url=body.image_url,
            extra={"vision": vis, "enrichment": enrichment},
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        lead_id = row.id

    return PropertyResponse(
        address=body.address,
        lat=lat,
        lng=lng,
        roof_size_sqft=2400.0,
        damage_score=round(damage_prob, 4),
        damage_index=dmg_idx,
        lead_score=lead_sc,
        owner=enrichment.get("owner"),
        estimated_value=enrichment.get("estimated_value"),
        roof_age=enrichment.get("roof_age"),
        lead_id=lead_id,
    )


@app.get("/imagery")
def get_imagery(lat: float = Query(...), lng: float = Query(...)):
    return {
        "tile_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "lat": lat,
        "lng": lng,
        "note": "Swap for Nearmap/Mapbox tiles with your API key on the frontend or signed URLs here.",
    }


@app.get("/damage-score")
def damage_score(
    property_id: str,
    image_url: str | None = None,
    db: Session = Depends(get_db),
):
    model = get_model(settings.vision_backend)
    key = (image_url or "").strip() or f"property:{property_id}"
    vis = model.predict(key)
    prob = float(vis.get("hail_damage", 0.5))
    lat, lng = geocode_stub(property_id)
    storms = _storms_as_tuples(db)
    dmg_idx, lead_sc = compute_lead_score(
        damage_prob_0_1=prob,
        lat=lat,
        lng=lng,
        storms=storms,
    )
    risk = "HIGH" if prob >= 0.75 else "MEDIUM" if prob >= 0.55 else "LOW"
    return {
        "property_id": property_id,
        "image_url": image_url,
        "damage_probability": prob,
        "damage_index": dmg_idx,
        "lead_score": lead_sc,
        "risk": risk,
        "vision": vis,
    }


@app.post("/damage/predict")
def damage_predict(body: DamagePredictRequest):
    model = get_model(settings.vision_backend)
    return model.predict(body.image_url)


@app.post("/ingest/noaa/hail-snapshot", response_model=IngestResult)
def ingest_noaa_hail(db: Session = Depends(get_db)):
    db.execute(delete(StormReport).where(StormReport.source == "spc_csv"))
    db.commit()
    rows = noaa_ingest.fetch_spc_hail_rows_sync()
    inserted = 0
    for r in rows:
        if r.get("hail_inches", 0) < 1.0:
            continue
        db.add(
            StormReport(
                source="spc_csv",
                observed_label=r.get("label"),
                lat=float(r["lat"]),
                lng=float(r["lon"]),
                hail_inches=float(r["hail_inches"]),
                location=r.get("location"),
                state=r.get("state"),
                raw_row=json.dumps(r)[:2000],
            )
        )
        inserted += 1
    db.commit()
    return IngestResult(inserted=inserted, source="spc_filtered_hail", message="Today+yesterday CSV merge")


@app.get("/leads/map", response_model=list[LeadRead])
def leads_map(db: Session = Depends(get_db), limit: int = Query(500, le=2000)):
    q = select(Lead).order_by(Lead.created_at.desc()).limit(limit)
    rows = db.execute(q).scalars().all()
    return rows


@app.get("/leads/{lead_id}", response_model=LeadRead)
def get_lead(lead_id: UUID, db: Session = Depends(get_db)):
    row = db.get(Lead, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    return row


@app.post("/leads", response_model=LeadRead)
def create_lead(body: LeadCreate, db: Session = Depends(get_db)):
    row = Lead(
        address=body.address,
        name=body.name,
        lat=body.lat,
        lng=body.lng,
        damage_index=body.damage_index,
        lead_score=body.lead_score,
        image_url=body.image_url,
        script_type=body.script_type,
        priority=body.priority,
        extra=body.extra,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.get("/export/csv")
def export_csv_call_agents(db: Session = Depends(get_db)):
    q = select(Lead).order_by(Lead.lead_score.desc())
    rows = db.execute(q).scalars().all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "id",
            "name",
            "address",
            "lat",
            "lng",
            "damage_index",
            "lead_score",
            "priority",
            "script_type",
            "image_url",
            "created_at",
        ]
    )
    for r in rows:
        w.writerow(
            [
                str(r.id),
                r.name or "",
                r.address,
                r.lat,
                r.lng,
                r.damage_index,
                r.lead_score,
                r.priority or "",
                r.script_type or "",
                r.image_url or "",
                r.created_at.isoformat() if r.created_at else "",
            ]
        )
    return PlainTextResponse(buf.getvalue(), media_type="text/csv")
