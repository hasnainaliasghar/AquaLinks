"""Risk assessment response schema."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.risk_assessment import RiskLevel, Urgency


class RiskAssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    score: float
    level: RiskLevel
    urgency: Urgency
    recommendation: str
    reasoning: str
    limitations: str
    contributors: dict[str, Any]
    model_id: str
    # Multi-agent layer additions (Stage 9). Both nullable so legacy
    # rows that pre-date the agent layer still serialise cleanly.
    agent_trace_id: UUID | None = None
    # Legacy JSON slot: older sessions may contain FieldBrief shape,
    # newer sessions may contain Reporter summary payloads.
    field_brief: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
