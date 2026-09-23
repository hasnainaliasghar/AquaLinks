"""Risk assessment per session."""

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


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Urgency(StrEnum):
    ROUTINE = "routine"
    ELEVATED = "elevated"
    IMMEDIATE = "immediate"


class RiskAssessment(IDMixin, TimestampMixin, SQLModel, table=True):
    """The risk model output and its LLM-generated narrative."""

    __tablename__ = "risk_assessments"

    session_id: UUID = Field(
        sa_column=Column(
            ForeignKey("monitoring_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    score: float = Field(nullable=False, ge=0.0, le=1.0)
    level: RiskLevel = Field(
        sa_column=Column(
            Enum(
                RiskLevel,
                name="risk_level",
                values_callable=_enum_values,
            ),
            nullable=False,
        )
    )
    urgency: Urgency = Field(
        sa_column=Column(
            Enum(
                Urgency,
                name="risk_urgency",
                values_callable=_enum_values,
            ),
            nullable=False,
        )
    )
    recommendation: str = Field(sa_column=Column(String(1200), nullable=False))
    reasoning: str = Field(sa_column=Column(String(4000), nullable=False))
    limitations: str = Field(sa_column=Column(String(2000), nullable=False))
    contributors: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    model_id: str = Field(default="gemini-2.5-flash", sa_column=Column(String(80), nullable=False))

    # Optional link to the multi-agent execution trace for this session.
    # NULL on rows produced by the deterministic-only path
    # (AQUALENS_AGENTIC_MODE=false or AQUALENS_FAKE_GEMINI=true).
    agent_trace_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("agent_traces.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # Legacy JSON slot from the retired Field Liaison stage. New runs
    # store Reporter summary payloads here so we can ship citizen copy
    # with the risk row in one query. The /field-brief endpoint treats
    # non-FieldBrief payloads as absent for backward compatibility.
    field_brief: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
