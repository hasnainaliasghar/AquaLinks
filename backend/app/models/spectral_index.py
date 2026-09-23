"""Computed spectral index per session."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column, Enum, ForeignKey, String
from sqlmodel import Field, SQLModel

from app.models.base import IDMixin, TimestampMixin


def _enum_values(enum_class: type[StrEnum]) -> list[str]:
    """Persist enum .value strings (DB enum labels), not enum member names."""
    return [member.value for member in enum_class]


class IndexName(StrEnum):
    NDWI = "NDWI"
    MNDWI = "MNDWI"
    NDTI = "NDTI"
    NDCI = "NDCI"
    NDVI = "NDVI"
    WRI = "WRI"


class SpectralIndex(IDMixin, TimestampMixin, SQLModel, table=True):
    """The masked-mean value of one spectral index for one session."""

    __tablename__ = "spectral_indices"

    session_id: UUID = Field(
        sa_column=Column(
            ForeignKey("monitoring_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    name: IndexName = Field(
        sa_column=Column(
            Enum(
                IndexName,
                name="index_name",
                values_callable=_enum_values,
            ),
            nullable=False,
        )
    )
    value: float = Field(nullable=False)
    min_value: float | None = Field(default=None)
    max_value: float | None = Field(default=None)
    stddev: float | None = Field(default=None)
    interpretation: str | None = Field(
        default=None,
        sa_column=Column(String(280)),
        description="Human-readable band interpretation (e.g. 'high turbidity').",
    )
    bands: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    sample_count: int | None = Field(default=None)
    extra: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
