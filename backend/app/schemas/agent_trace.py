"""Response DTOs for the agent-trace API endpoint."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentTraceRead(BaseModel):
    """JSON shape returned by ``GET /sessions/{id}/trace``."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    coordinator_plan: dict[str, Any]
    agent_runs: list[dict[str, Any]]
    total_tokens_in: int
    total_tokens_out: int
    total_latency_ms: int
    gemini_model: str
    created_at: datetime
    updated_at: datetime


__all__ = ["AgentTraceRead"]
