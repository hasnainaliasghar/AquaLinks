"""Field evidence schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.evidence import Odor, WaterColor


class EvidenceCreate(BaseModel):
    water_color: WaterColor
    odor: Odor
    algae_present: bool = False
    dead_fish_count: int = Field(default=0, ge=0)
    rainfall_mm: float = Field(default=0.0, ge=0.0)
    complaints_count: int = Field(default=0, ge=0)
    notes: str | None = Field(default=None, max_length=2000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    reporter_name: str | None = Field(default=None, max_length=120)


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    water_color: WaterColor
    odor: Odor
    algae_present: bool
    dead_fish_count: int
    rainfall_mm: float
    complaints_count: int
    notes: str | None
    photo_url: str | None
    latitude: float | None
    longitude: float | None
    reporter_name: str | None
    created_at: datetime
