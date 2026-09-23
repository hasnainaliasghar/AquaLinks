"""Monitoring session schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.session import AOIType, SessionStatus
from app.schemas.evidence import EvidenceRead
from app.schemas.indices import SpectralIndexRead
from app.schemas.risk import RiskAssessmentRead
from app.schemas.water_body import GeoJSONPolygon, WaterBodyRead


class SessionCreate(BaseModel):
    """Create a new monitoring session.

    Provide either ``water_body_id`` (use an existing record) or
    ``new_water_body`` (create one on the fly from the AOI polygon
    the wizard built from a place search, coordinate input, or
    map click).
    """

    water_body_id: UUID | None = None
    new_water_body: NewWaterBody | None = None
    start_date: date | None = None
    end_date: date | None = None
    max_cloud_cover: float = Field(default=30.0, ge=0.0, le=100.0)

    @model_validator(mode="after")
    def _exactly_one_source(self) -> SessionCreate:
        if (self.water_body_id is None) == (self.new_water_body is None):
            raise ValueError("Provide exactly one of water_body_id or new_water_body.")
        return self


class NewWaterBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    geometry: GeoJSONPolygon
    source: str = Field(default="user_drawn", max_length=80)


SessionCreate.model_rebuild()


class SessionStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: SessionStatus
    status_message: str | None
    updated_at: datetime


class SessionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    water_body_id: UUID
    water_body_name: str
    water_body_latitude: float | None = None
    water_body_longitude: float | None = None
    start_date: date
    end_date: date
    status: SessionStatus
    risk_level: str | None
    risk_score: float | None
    scene_capture_date: datetime | None
    created_at: datetime
    updated_at: datetime


class CitizenCitationRead(BaseModel):
    title: str | None = None
    uri: str
    published_at: str | None = None


class CitizenSummaryRead(BaseModel):
    """Mirror of :class:`app.services.citizen_summary.CitizenSummary`
    expressed via Pydantic so FastAPI emits the type in the OpenAPI schema."""

    tone: Literal["safe", "caution", "avoid", "not_water", "unknown"]
    headline: str
    bottom_line: str
    safety_for_humans: str
    safety_for_pets_and_kids: str
    what_we_could_not_check: str
    citations: list[CitizenCitationRead] = Field(default_factory=list)


class SessionDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    water_body: WaterBodyRead
    start_date: date
    end_date: date
    max_cloud_cover: float
    status: SessionStatus
    status_message: str | None
    scene_id: str | None
    scene_capture_date: datetime | None
    scene_cloud_cover: float | None
    scene_provider: str | None
    scene_thumbnail_url: str | None
    scene_metadata: dict[str, Any] | None
    water_fraction: float | None = None
    aoi_type: AOIType | None = None
    indices: list[SpectralIndexRead] = Field(default_factory=list)
    evidence: list[EvidenceRead] = Field(default_factory=list)
    risk: RiskAssessmentRead | None = None
    # Plain-English verdict rendered on the session page and PDF.
    # Produced by Reporter when available, otherwise computed
    # deterministically from risk + AOI + evidence
    # (see app/services/citizen_summary.py).
    citizen_summary: CitizenSummaryRead | None = None
    report_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
