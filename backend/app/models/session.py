"""Monitoring session record."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, String
from sqlmodel import Field, SQLModel

from app.models.base import IDMixin, TimestampMixin


def _enum_values(enum_class: type[StrEnum]) -> list[str]:
    """Persist enum .value strings (DB enum labels), not enum member names."""
    return [member.value for member in enum_class]


class SessionStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_EVIDENCE = "awaiting_evidence"
    COMPLETE = "complete"
    FAILED = "failed"


class AOIType(StrEnum):
    """Coarse classification of what's actually inside the AOI.

    Derived from the fraction of NDWI-positive pixels: a high fraction
    means the polygon is over open water and AquaLens's water-quality
    indices are meaningful; a low fraction means it's mostly land and
    the indices are measuring vegetation, soil, or built-up surfaces
    instead.
    """

    WATER = "water"
    MIXED = "mixed"
    LAND = "land"


class MonitoringSession(IDMixin, TimestampMixin, SQLModel, table=True):
    """A single monitoring run for one water body over one date window."""

    __tablename__ = "monitoring_sessions"

    water_body_id: UUID = Field(
        sa_column=Column(
            ForeignKey("water_bodies.id", ondelete="CASCADE"), nullable=False, index=True
        ),
    )

    start_date: date = Field(nullable=False)
    end_date: date = Field(nullable=False)
    max_cloud_cover: float = Field(default=30.0, ge=0.0, le=100.0)

    status: SessionStatus = Field(
        default=SessionStatus.PENDING,
        sa_column=Column(
            Enum(
                SessionStatus,
                name="session_status",
                values_callable=_enum_values,
            ),
            nullable=False,
        ),
    )
    status_message: str | None = Field(default=None, sa_column=Column(String(500)))

    # Imagery metadata populated by the satellite step.
    scene_id: str | None = Field(default=None, sa_column=Column(String(120)))
    scene_capture_date: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    scene_cloud_cover: float | None = Field(default=None)
    scene_provider: str | None = Field(default=None, sa_column=Column(String(60)))
    scene_thumbnail_url: str | None = Field(default=None, sa_column=Column(String(500)))
    scene_metadata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    # Land-vs-water classification computed from the NDWI mask.
    water_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    aoi_type: AOIType | None = Field(
        default=None,
        sa_column=Column(
            Enum(
                AOIType,
                name="aoi_type",
                values_callable=_enum_values,
            )
        ),
    )
