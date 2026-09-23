"""Field-evidence submission."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from sqlalchemy import Column, Enum, ForeignKey, String
from sqlmodel import Field, SQLModel

from app.models.base import IDMixin, TimestampMixin


def _enum_values(enum_class: type[StrEnum]) -> list[str]:
    """Persist enum .value strings (DB enum labels), not enum member names."""
    return [member.value for member in enum_class]


class WaterColor(StrEnum):
    CLEAR = "clear"
    BLUE = "blue"
    GREEN = "green"
    BROWN = "brown"
    YELLOW = "yellow"
    RED = "red"
    BLACK = "black"
    OTHER = "other"


class Odor(StrEnum):
    NONE = "none"
    EARTHY = "earthy"
    MUSTY = "musty"
    FISHY = "fishy"
    ROTTEN = "rotten"
    CHEMICAL = "chemical"
    SEWAGE = "sewage"
    OTHER = "other"


class FieldEvidence(IDMixin, TimestampMixin, SQLModel, table=True):
    """A field observation tied to a monitoring session."""

    __tablename__ = "field_evidence"

    session_id: UUID = Field(
        sa_column=Column(
            ForeignKey("monitoring_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    water_color: WaterColor = Field(
        sa_column=Column(
            Enum(
                WaterColor,
                name="water_color",
                values_callable=_enum_values,
            ),
            nullable=False,
        )
    )
    odor: Odor = Field(
        sa_column=Column(
            Enum(
                Odor,
                name="water_odor",
                values_callable=_enum_values,
            ),
            nullable=False,
        )
    )
    algae_present: bool = Field(default=False, nullable=False)
    dead_fish_count: int = Field(default=0, ge=0)
    rainfall_mm: float = Field(default=0.0, ge=0.0)
    complaints_count: int = Field(default=0, ge=0)
    notes: str | None = Field(default=None, sa_column=Column(String(2000)))
    photo_url: str | None = Field(default=None, sa_column=Column(String(500)))
    latitude: float | None = Field(default=None)
    longitude: float | None = Field(default=None)
    reporter_name: str | None = Field(default=None, sa_column=Column(String(120)))
