"""Persistent memory written by the Historian agent across sessions.

Each row is a short, Gemini-distilled observation about a specific
water body. The Historian reads these notes at the start of a session
and writes new ones at the end so the agent layer manages multi-step
tasks over time across repeated monitoring runs.

The ``embedding`` column holds a 768-dim ``text-embedding-004`` vector
of the note text so the Historian can recall semantically related
notes (``semantic_recall_notes`` tool), not just the most recent ones.
The column type degrades gracefully on SQLite (used in tests) — the
vector is stored as JSON and the similarity search falls back to a
straight recency query.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime, Enum, Float, ForeignKey, Index, String
from sqlmodel import Field, SQLModel

from app.models.base import IDMixin, TimestampMixin


def _enum_values(enum_class: type[StrEnum]) -> list[str]:
    """Persist enum .value strings (DB enum labels), not enum member names."""
    return [member.value for member in enum_class]


class MemoryKind(StrEnum):
    """What kind of note this is.

    Used by the Historian to filter recall queries — e.g. when looking
    at a new high-risk session it can ask "any prior escalations on
    this water body?" without sifting through routine observations.
    """

    OBSERVATION = "observation"
    ESCALATION = "escalation"
    FALSE_ALARM = "false_alarm"
    EVIDENCE_PATTERN = "evidence_pattern"


class AgentMemory(IDMixin, TimestampMixin, SQLModel, table=True):
    """A single distilled note about a water body, written by the Historian."""

    __tablename__ = "agent_memory"
    __table_args__ = (
        # Compound index supports the "most recent notes by kind" query
        # the Historian runs at the start of every session.
        Index(
            "ix_agent_memory_water_body_kind_created",
            "water_body_id",
            "kind",
            "created_at",
        ),
    )

    water_body_id: UUID = Field(
        sa_column=Column(
            ForeignKey("water_bodies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    source_session_id: UUID = Field(
        sa_column=Column(
            ForeignKey("monitoring_sessions.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    kind: MemoryKind = Field(
        sa_column=Column(
            Enum(
                MemoryKind,
                name="memory_kind",
                values_callable=_enum_values,
            ),
            nullable=False,
        )
    )
    note: str = Field(sa_column=Column(String(500), nullable=False))
    confidence: float = Field(
        sa_column=Column(Float, nullable=False),
        ge=0.0,
        le=1.0,
    )
    # 768-dim text-embedding-004 vector. Stored as JSON for cross-dialect
    # portability — the Postgres migration adds a pgvector column on top
    # of this for ANN search; on SQLite the JSON column is read directly
    # and similarity is computed in Python.
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    archived_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    def as_recall_payload(self) -> dict[str, Any]:
        """Serialise for the ``recall_persistent_notes`` tool output."""
        return {
            "kind": self.kind.value,
            "note": self.note,
            "confidence": round(self.confidence, 3),
            "created_at": self.created_at.isoformat(),
            "source_session_id": str(self.source_session_id),
        }
