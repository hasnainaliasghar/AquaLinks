"""Per-session execution trace for the multi-agent run.

The :class:`TraceRecorder` is a small builder that the orchestrator
and each sub-agent push records into as they run. At the end of the
session it produces the dict shape persisted into
:class:`~app.models.AgentTrace.agent_runs`, plus aggregate totals.

The recorder is intentionally framework-free: no DB writes, no
network. Persistence is the orchestrator's job — this module just
captures structured data while the agents work.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.models.agent_trace import TRACE_SCHEMA_VERSION


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def _now_ms() -> int:
    return int(time.perf_counter() * 1000)


def _friendly_error(exc: BaseException) -> str:
    """Render an exception as a short, user-facing sentence.

    The agent trace surface (PDF + web card) is meant for non-engineers
    who shouldn't have to read Python tracebacks. Known failure modes
    get a plain-English translation; anything else falls back to the
    raw ``Type: message`` form so we never hide a real bug.
    """
    name = type(exc).__name__
    message = str(exc) or name

    if isinstance(exc, json.JSONDecodeError):
        return (
            "The model's reply was incomplete or malformed JSON, "
            "so the deterministic fallback was used for this step."
        )

    lowered = message.lower()
    if "invalid_argument" in lowered or "unknown name" in lowered:
        return (
            "The LLM rejected the response schema for this step. "
            "The deterministic fallback was used instead."
        )
    if (
        "resource_exhausted" in lowered
        or "quota" in lowered
        or "429" in lowered
        or "rate_limit" in lowered
    ):
        return (
            "The LLM API quota was exhausted for this key. "
            "The runtime rolled over to the next key (or fallback) where possible."
        )
    if "deadline" in lowered or "timeout" in lowered:
        return "The LLM call timed out before a response arrived."
    if "safety" in lowered and "block" in lowered:
        return "The LLM's safety filter blocked the response for this step."

    # Unknown failure — keep the raw form so debugging is still possible.
    return f"{name}: {message}"


@dataclass
class ToolCallRecord:
    """One tool invocation inside an agent run."""

    name: str
    arguments: dict[str, Any]
    started_at: str = field(default_factory=_utc_iso)
    result: Any | None = None
    error: str | None = None
    latency_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "started_at": self.started_at,
        }


@dataclass
class AgentRunRecord:
    """One sub-agent's full execution record."""

    agent: str
    started_at: str = field(default_factory=_utc_iso)
    completed_at: str | None = None
    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    outputs: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": TRACE_SCHEMA_VERSION,
            "agent": self.agent,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "latency_ms": self.latency_ms,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "outputs": self.outputs,
            "error": self.error,
        }


class AgentTraceBuilder:
    """Per-agent recorder yielded by :meth:`TraceRecorder.record_agent`."""

    def __init__(self, parent: TraceRecorder, agent: str) -> None:
        self._parent = parent
        self.record = AgentRunRecord(agent=agent)
        self._wall_start_ms = _now_ms()

    @contextmanager
    def record_tool(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> Iterator[ToolCallRecord]:
        """Wrap a single tool invocation and capture timing + result."""
        record = ToolCallRecord(name=name, arguments=arguments or {})
        start = _now_ms()
        try:
            yield record
        except Exception as exc:
            record.error = _friendly_error(exc)
            raise
        finally:
            record.latency_ms = _now_ms() - start
            self.record.tool_calls.append(record)

    def add_tokens(self, *, tokens_in: int = 0, tokens_out: int = 0) -> None:
        self.record.tokens_in += int(tokens_in)
        self.record.tokens_out += int(tokens_out)

    def set_outputs(self, outputs: dict[str, Any]) -> None:
        self.record.outputs = outputs

    def fail(self, error: str) -> None:
        self.record.error = error

    def _finalise(self) -> None:
        self.record.completed_at = _utc_iso()
        self.record.latency_ms = _now_ms() - self._wall_start_ms


class TraceRecorder:
    """Top-level recorder for one session's multi-agent run.

    Usage:

        rec = TraceRecorder(gemini_model="gemini-2.5-flash")
        rec.set_coordinator_plan(plan_dict)
        with rec.record_agent("scout") as scout:
            with scout.record_tool("list_recent_scenes", {...}) as tc:
                tc.result = {...}
            scout.set_outputs({"selected_scene": "S2A_..."})
        rec.compile()  # -> dict matching AgentTrace columns
    """

    def __init__(self, *, gemini_model: str = "gemini-2.5-flash") -> None:
        self.gemini_model = gemini_model
        self.coordinator_plan: dict[str, Any] = {}
        self.agent_runs: list[AgentRunRecord] = []
        self._wall_start_ms = _now_ms()

    def set_coordinator_plan(self, plan: dict[str, Any]) -> None:
        self.coordinator_plan = plan

    @contextmanager
    def record_agent(self, agent: str) -> Iterator[AgentTraceBuilder]:
        builder = AgentTraceBuilder(self, agent)
        try:
            yield builder
        except Exception as exc:
            builder.fail(_friendly_error(exc))
            raise
        finally:
            builder._finalise()
            self.agent_runs.append(builder.record)

    def compile(self) -> dict[str, Any]:
        """Produce the dict shape persisted into AgentTrace columns."""
        runs = [r.to_dict() for r in self.agent_runs]
        return {
            "coordinator_plan": self.coordinator_plan,
            "agent_runs": runs,
            "total_tokens_in": sum(r["tokens_in"] for r in runs),
            "total_tokens_out": sum(r["tokens_out"] for r in runs),
            "total_latency_ms": _now_ms() - self._wall_start_ms,
            "gemini_model": self.gemini_model,
        }


__all__ = [
    "AgentRunRecord",
    "AgentTraceBuilder",
    "ToolCallRecord",
    "TraceRecorder",
]
