"""Full execution trace of the multi-agent run for one session.

One row per ``MonitoringSession``. Holds the Coordinator's plan, every
sub-agent's tool calls and observations, total token usage, and total
latency. Powers the **Agent Trace** card in the frontend and the
agent-decisions appendix in the PDF.

The agent-run payload is stored as JSONB so the schema can evolve
without migrations — every record carries a ``schema_version`` field
inside ``agent_runs`` so older traces remain readable.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column, ForeignKey, Integer, String
from sqlmodel import Field, SQLModel

from app.models.base import IDMixin, TimestampMixin

# Bump when the agent_runs JSONB shape changes in a breaking way.
TRACE_SCHEMA_VERSION = 1


class AgentTrace(IDMixin, TimestampMixin, SQLModel, table=True):
    """A complete record of the multi-agent run for one session."""

    __tablename__ = "agent_traces"

    session_id: UUID = Field(
        sa_column=Column(
            ForeignKey("monitoring_sessions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        )
    )

    # Coordinator output: { plan: [...], rationale: str, estimated_complexity: str }
    coordinator_plan: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )

    # Per-agent execution records. Each entry shape:
    #   {
    #     "schema_version": 1,
    #     "agent": "scout" | "historian" | "analyst" | "reporter"
    #              | "field_liaison" (legacy),
    #     "started_at": iso8601,
    #     "completed_at": iso8601,
    #     "latency_ms": int,
    #     "tokens_in": int,
    #     "tokens_out": int,
    #     "tool_calls": [
    #       {
    #         "name": str,
    #         "arguments": dict,
    #         "result": dict | None,
    #         "error": str | None,
    #         "latency_ms": int,
    #         "started_at": iso8601,
    #       }, ...
    #     ],
    #     "outputs": dict,           # agent's final structured output
    #     "error": str | None,       # set when the agent failed entirely
    #   }
    agent_runs: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )

    total_tokens_in: int = Field(sa_column=Column(Integer, nullable=False, default=0))
    total_tokens_out: int = Field(sa_column=Column(Integer, nullable=False, default=0))
    total_latency_ms: int = Field(sa_column=Column(Integer, nullable=False, default=0))
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        sa_column=Column(String(80), nullable=False),
    )
