from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address: Mapped[str] = mapped_column(String(512))
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    damage_index: Mapped[float] = mapped_column(Float, default=0.0)  # 0–100
    lead_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0–1
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    script_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class StormReport(Base):
    """NOAA SPC LSR-style points ingested for scoring context."""

    __tablename__ = "storm_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(32), default="spc_csv")
    observed_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    hail_inches: Mapped[float] = mapped_column(Float)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    state: Mapped[str | None] = mapped_column(String(8), nullable=True)
    raw_row: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
