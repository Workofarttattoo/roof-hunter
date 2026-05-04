from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PropertyRequest(BaseModel):
    address: str = Field(..., min_length=3)
    save: bool = False
    name: str | None = None
    image_url: str | None = None


class PropertyResponse(BaseModel):
    address: str
    lat: float
    lng: float
    roof_size_sqft: float = 2400.0
    damage_score: float = Field(description="Model or heuristic 0–1")
    damage_index: float = Field(description="Indexed 0–100 for UI parity with Ridgeline")
    lead_score: float
    owner: str | None = None
    estimated_value: int | None = None
    roof_age: int | None = None
    lead_id: UUID | None = None


class LeadCreate(BaseModel):
    address: str
    lat: float
    lng: float
    name: str | None = None
    damage_index: float = 0.0
    lead_score: float = 0.0
    image_url: str | None = None
    script_type: str | None = None
    priority: str | None = None
    extra: dict[str, Any] | None = None


class LeadRead(BaseModel):
    id: UUID
    address: str
    name: str | None
    lat: float
    lng: float
    damage_index: float
    lead_score: float
    image_url: str | None
    script_type: str | None
    priority: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DamagePredictRequest(BaseModel):
    image_url: str = Field(..., min_length=8)


class IngestResult(BaseModel):
    inserted: int
    source: str
    message: str | None = None
