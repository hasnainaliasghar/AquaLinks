"""Historian agent — context briefing for the Analyst.

Combines DB-backed tools and live web search in a single Groq tool loop:

- **Function calling** over DB tools (history, memory recall, memory
  write) and the local trend math.
- **Web search** via DuckDuckGo (no API key) for live regional
  water-quality news and events.

Note: Google Search grounding and Code Execution are Gemini-only
features. Web search is now handled by the ``web_search`` tool which
calls DuckDuckGo directly.

The agent also writes one or two short notes back into
``agent_memory`` so future Historian runs for the same water body
already know what we learned today. That's the persistent-memory
half of the product's over-time continuity model.
"""

from __future__ import annotations

from importlib.resources import files
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.logging import get_logger
from app.models import MemoryKind, WaterBody
from app.services.agent.gemini_runtime import (
    ToolSpec,
    run_tool_loop,
    to_json,
)
from app.services.agent.tools import history_tools, memory_tools, web_search_tools
from app.services.agent.trace import AgentTraceBuilder

LOGGER = get_logger(__name__)

HISTORIAN_NAME = "historian"
HISTORIAN_MAX_TURNS = 8


# ----------------------------------------------------------------------
# Output schema
# ----------------------------------------------------------------------


class TrendSummary(BaseModel):
    metric: str
    slope_per_day: float | None = None
    mann_kendall_p: float | None = None
    summary: str


class RecalledNote(BaseModel):
    kind: str
    note: str
    confidence: float
    created_at: str | None = None


class GroundedFinding(BaseModel):
    claim: str | None = None
    title: str | None = None
    uri: str | None = None
    published_at: str | None = None
    snippet: str | None = None


class PersistentNoteSummary(BaseModel):
    kind: str
    note: str
    confidence: float


class HistorianBriefing(BaseModel):
    """The Historian's final structured output."""

    trend: TrendSummary | None = None
    recalled_notes: list[RecalledNote] = Field(default_factory=list)
    grounded_findings: list[GroundedFinding] = Field(default_factory=list)
    new_persistent_notes_written: list[PersistentNoteSummary] = Field(default_factory=list)
    briefing_text: str


# ----------------------------------------------------------------------
# Prompt
# ----------------------------------------------------------------------


_SYSTEM_INSTRUCTION_JSON: dict[str, Any] = json.loads(
    files("app.services.agent.prompts").joinpath("historian.json").read_text(encoding="utf-8")
)


def _serialise_system() -> str:
    return json.dumps(_SYSTEM_INSTRUCTION_JSON, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------
# Tool specs (closed over the per-run DB session + IDs)
# ----------------------------------------------------------------------


def _tool_specs(*, db: Session, water_body_id: UUID, source_session_id: UUID) -> list[ToolSpec]:
    def t_get_history(**kw: Any) -> dict[str, Any]:
        return history_tools.get_session_history(
            db=db,
            water_body_id=water_body_id,
            limit=int(kw.get("limit", 20)),
        )

    def t_compute_trend(**kw: Any) -> dict[str, Any]:
        return history_tools.compute_trend(
            metric=str(kw.get("metric", "NDCI")),
            sessions=kw.get("sessions") or [],
        )

    def t_recall(**kw: Any) -> dict[str, Any]:
        kinds_raw = kw.get("kinds") or []
        kinds = [MemoryKind(k) for k in kinds_raw] if kinds_raw else None
        return memory_tools.recall_persistent_notes(
            db=db,
            water_body_id=water_body_id,
            kinds=kinds,
            limit=int(kw.get("limit", 10)),
        )

    def t_semantic(**kw: Any) -> dict[str, Any]:
        return memory_tools.semantic_recall_notes(
            db=db,
            water_body_id=water_body_id,
            query=str(kw.get("query", "")),
            top_k=int(kw.get("top_k", 5)),
        )

    def t_write_note(**kw: Any) -> dict[str, Any]:
        kind = kw.get("kind") or "observation"
        return memory_tools.write_persistent_note(
            db=db,
            water_body_id=water_body_id,
            source_session_id=source_session_id,
            kind=kind,
            note=str(kw.get("note", "")),
            confidence=float(kw.get("confidence", 0.5)),
        )

    return [
        ToolSpec(
            name="get_session_history",
            description=(
                "Return prior completed sessions for the current water body, newest first, "
                "joined with their risk row and aggregated indices. Use this once at the "
                "start of the run."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max prior sessions to return (default 20).",
                    }
                },
            },
            handler=t_get_history,
        ),
        ToolSpec(
            name="compute_trend",
            description=(
                "Linear regression slope per day for ``metric`` across the given list of "
                "prior sessions. ``metric`` is one of NDWI, MNDWI, NDTI, NDCI, NDVI, WRI, "
                "or 'risk_score'."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "sessions": {
                        "type": "array",
                        "description": "Pass the 'sessions' field from get_session_history.",
                        "items": {"type": "object"},
                    },
                },
                "required": ["metric", "sessions"],
            },
            handler=t_compute_trend,
        ),
        ToolSpec(
            name="recall_persistent_notes",
            description=(
                "Return prior Historian notes for this water body. Use to surface "
                "observations the Analyst would benefit from but cannot derive from this "
                "session's indices alone."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "kinds": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "observation",
                                "escalation",
                                "false_alarm",
                                "evidence_pattern",
                            ],
                        },
                    },
                    "limit": {"type": "integer"},
                },
            },
            handler=t_recall,
        ),
        ToolSpec(
            name="semantic_recall_notes",
            description=(
                "Like recall_persistent_notes but ranks by semantic similarity to a "
                "free-text query."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer"},
                },
                "required": ["query"],
            },
            handler=t_semantic,
        ),
        ToolSpec(
            name="write_persistent_note",
            description=(
                "Persist one short observation (<=500 chars) about this water body so "
                "the next Historian run sees it. Reserve for non-obvious observations "
                "that wouldn't be re-derived from the indices."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": [
                            "observation",
                            "escalation",
                            "false_alarm",
                            "evidence_pattern",
                        ],
                    },
                    "note": {"type": "string", "maxLength": 500},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                },
                "required": ["kind", "note", "confidence"],
            },
            handler=t_write_note,
        ),
        ToolSpec(
            name="web_search",
            description=(
                "Search the web via DuckDuckGo for live news and reports about "
                "water quality, algal blooms, pollution events, or environmental "
                "incidents near the current water body. Use when you need regional "
                "context beyond what the DB history provides. Pass a specific, "
                "targeted query such as: "
                "'algal bloom [water body name] [region] 2024 water quality'."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query. Be specific: include the water body name, "
                            "location, and the type of event you are looking for."
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results to return (1–8, default 5).",
                    },
                },
                "required": ["query"],
            },
            handler=lambda **kw: web_search_tools.web_search(
                query=str(kw.get("query", "")),
                max_results=int(kw.get("max_results", 5)),
            ),
        ),
    ]


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------


def run_historian(
    *,
    builder: AgentTraceBuilder,
    db: Session,
    water_body: WaterBody,
    source_session_id: UUID,
    current_indices: list[dict[str, Any]],
    scene_capture_date: str | None,
    aoi_type: str | None,
    place_hint: str | None = None,
    max_turns: int = HISTORIAN_MAX_TURNS,
) -> HistorianBriefing:
    """Run the Historian and return its briefing.

    The caller wraps this in ``trace.record_agent("historian")`` so all
    tool calls get captured in the session trace.
    """
    user_payload = {
        "water_body": {
            "id": str(water_body.id),
            "name": water_body.name,
            "centroid": water_body.centroid,
            "area_km2": water_body.area_km2,
        },
        "current_session": {
            "session_id": str(source_session_id),
            "scene_capture_date": scene_capture_date,
            "indices": current_indices,
        },
        "aoi_type": aoi_type,
        "place_hint": place_hint,
    }

    specs = _tool_specs(
        db=db,
        water_body_id=water_body.id,
        source_session_id=source_session_id,
    )

    result = run_tool_loop(
        builder=builder,
        system_instruction=_serialise_system(),
        user_message=to_json(user_payload),
        tools=specs,
        response_schema=HistorianBriefing,
        max_turns=max_turns,
        temperature=0.25,
        # Note: Google Search grounding and code execution are Gemini-only
        # features not supported on the Groq backend. The Historian still
        # runs with its DB-backed tools (history, memory, trend).
    )

    if isinstance(result.parsed, HistorianBriefing):
        briefing = result.parsed
    else:
        briefing = _fallback_briefing(builder)

    # Surface grounding citations and code-execution output into the
    # builder's outputs so the trace UI can render them next to the
    # briefing without the Analyst having to echo them back.
    outputs: dict[str, Any] = briefing.model_dump()
    outputs["extras"] = result.extras
    builder.set_outputs(outputs)
    return briefing


def _fallback_briefing(builder: AgentTraceBuilder) -> HistorianBriefing:
    """Salvage a briefing when the Historian failed to emit schema-valid JSON."""
    last_history = next(
        (
            call.result
            for call in reversed(builder.record.tool_calls)
            if call.name == "get_session_history" and isinstance(call.result, dict)
        ),
        None,
    )
    n = (last_history or {}).get("count", 0)
    text = (
        f"Historian fallback: {n} prior session(s) found for this water body, "
        "no structured briefing was produced. Analyst should rely on the "
        "current-session indices alone."
    )
    return HistorianBriefing(trend=None, briefing_text=text)


__all__ = [
    "HISTORIAN_NAME",
    "GroundedFinding",
    "HistorianBriefing",
    "PersistentNoteSummary",
    "RecalledNote",
    "TrendSummary",
    "run_historian",
]
