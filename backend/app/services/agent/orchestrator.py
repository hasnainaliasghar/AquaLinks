"""Top-level agent orchestrator.

Drives the full multi-agent flow for a single monitoring session:

1. **Coordinator** (Gemini thinking mode) plans which sub-agents run.
2. **Scout** picks the Sentinel-2 scene (deterministic pipeline then
   reads its bands + computes indices + computes the score — that's
   *not* an agent step, it's the trusted numeric core).
3. **Historian** builds the context briefing with grounding + memory.
4. **Analyst** drafts the narrative and self-critiques.
5. **Reporter** writes the citizen-facing summary card.

The orchestrator never moves the deterministic risk band — agents
only choose inputs and write prose. If any individual agent errors
out the orchestrator records the failure in the trace and falls back
gracefully (Scout fallback → freshest candidate; Historian skipped →
empty briefing; Analyst failure → deterministic narrative from
``app.services.reasoning._fake_bundle``; Reporter fallback →
deterministic summary from ``app.services.citizen_summary``).

Output is :class:`OrchestratorResult`, a single dataclass holding the
narrative bundle, the public summary, and the compiled trace payload the
pipeline persists into :class:`~app.models.AgentTrace`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from importlib.resources import files
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import WaterBody
from app.models.risk_assessment import RiskLevel, Urgency
from app.schemas.risk import RiskAssessmentRead
from app.services.agent import analyst as analyst_mod
from app.services.agent import historian as historian_mod
from app.services.agent import reporter as reporter_mod
from app.services.agent import scout as scout_mod
from app.services.agent.gemini_runtime import call_structured
from app.services.agent.trace import TraceRecorder
from app.services.citizen_summary import CitizenSummary, build_citizen_summary
from app.services.reasoning import ReasoningBundle, _fake_bundle

LOGGER = get_logger(__name__)


# ----------------------------------------------------------------------
# Coordinator plan schema
# ----------------------------------------------------------------------


class PlanBudget(BaseModel):
    max_tool_calls: int = Field(ge=1, le=8)
    max_seconds: int = Field(ge=5, le=60)


class PlanStep(BaseModel):
    agent: Literal["scout", "historian", "analyst", "reporter"]
    reason: str = Field(min_length=8, max_length=220)
    budget: PlanBudget


class CoordinatorPlan(BaseModel):
    plan: list[PlanStep] = Field(default_factory=list)
    rationale: str = Field(default="", max_length=320)
    estimated_complexity: Literal["low", "medium", "high"] = "medium"


# ----------------------------------------------------------------------
# Orchestrator result
# ----------------------------------------------------------------------


@dataclass(slots=True)
class OrchestratorResult:
    """Everything the pipeline needs after the agent layer runs."""

    bundle: ReasoningBundle
    reporter_summary: CitizenSummary | None
    trace_payload: dict[str, Any]
    scene_id: str | None
    scene_capture_date: str | None
    scene_cloud_cover: float | None


# ----------------------------------------------------------------------
# System instruction
# ----------------------------------------------------------------------


_COORDINATOR_SYSTEM_JSON: dict[str, Any] = json.loads(
    files("app.services.agent.prompts").joinpath("coordinator.json").read_text(encoding="utf-8")
)


def _serialise_system() -> str:
    return json.dumps(_COORDINATOR_SYSTEM_JSON, indent=2, ensure_ascii=False)


_COORDINATOR_STRICT_JSON_APPENDIX = (
    "STRICT_JSON_MODE: Return exactly one JSON object matching the response schema. "
    "No markdown fences, no prose before/after the JSON, and no trailing commas."
)


# ----------------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------------


ProgressEvent = dict[str, Any]


def run_orchestrator(
    *,
    db: Session,
    water_body: WaterBody,
    session_id: UUID,
    aoi_geojson: dict[str, Any],
    start_date: str,
    end_date: str,
    max_cloud_cover: float,
    indices: list[dict[str, Any]],
    risk: dict[str, Any],
    aoi: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
    prior_session_count: int = 0,
    # Scout output piped in from the pipeline (the pipeline already ran
    # the deterministic scene fetch + index computation before calling
    # the orchestrator, so the Scout's selection is forwarded for the
    # trace rather than re-run).
    scene_id: str | None = None,
    scene_capture_date: str | None = None,
    scene_cloud_cover: float | None = None,
    # Live progress hook. Called twice per agent — once with
    # ``phase="started"`` before the agent runs (so the UI status
    # pill can name what's about to happen) and once with
    # ``phase="completed"`` after it finishes (so the trace UI can
    # render the new row). The pipeline uses this to update
    # ``status_message`` and persist the partial trace.
    on_progress: Callable[[ProgressEvent], None] | None = None,
) -> OrchestratorResult:
    """Run the full multi-agent flow for one session.

    Returns an :class:`OrchestratorResult` regardless of internal
    agent failures — the deterministic risk row already exists and
    the pipeline must produce a narrative + public summary for the user.
    """
    settings = get_settings()
    recorder = TraceRecorder(gemini_model=settings.gemini_model)
    inter_agent_delay_s = max(settings.aqualens_agent_step_delay_ms, 0) / 1000.0

    def _emit(phase: str, agent: str) -> None:
        if on_progress is None:
            return
        try:
            on_progress(
                {
                    "phase": phase,
                    "agent": agent,
                    "trace": recorder.compile(),
                }
            )
        except Exception as exc:
            LOGGER.warning("on_progress hook raised (%s); continuing", exc)

    def _pause_between_agents() -> None:
        if inter_agent_delay_s <= 0:
            return
        time.sleep(inter_agent_delay_s)

    _emit("started", "coordinator")
    plan = _plan(
        recorder,
        water_body=water_body,
        prior_session_count=prior_session_count,
        evidence_count=len(evidence or []),
    )

    selected_agents = {
        step.agent
        for step in plan.plan
        if step.agent in {"scout", "historian", "analyst", "reporter"}
    }
    if not selected_agents:
        # Defensive: a malformed plan must not strand us. Force the
        # baseline coverage instead.
        plan = _default_plan(prior_session_count)
        selected_agents = {step.agent for step in plan.plan}
    # Legacy behavior requested by product: skip Historian when there is
    # no prior session history for this water body.
    if prior_session_count <= 0:
        selected_agents.discard("historian")

    # Keep the displayed coordinator plan aligned with what we will
    # actually execute in this run.
    plan = CoordinatorPlan(
        plan=[step for step in plan.plan if step.agent in selected_agents],
        rationale=plan.rationale,
        estimated_complexity=plan.estimated_complexity,
    )
    recorder.set_coordinator_plan(plan.model_dump())
    _emit("completed", "coordinator")
    _pause_between_agents()

    def _record_skipped(agent: str, reason: str) -> None:
        with recorder.record_agent(agent) as builder:
            builder.set_outputs({"skipped": True, "skip_reason": reason})

    # ------------------------------------------------------------------
    # Scout — record the selection that was already made by the
    # deterministic pipeline so the trace reflects reality even though
    # we don't re-run scene discovery here.
    # ------------------------------------------------------------------
    scout_outputs: dict[str, Any] = {
        "selected_scene_id": scene_id,
        "selected_capture_date": scene_capture_date,
        "selected_cloud_cover": scene_cloud_cover,
        "note": (
            "Scout selection is forwarded from the deterministic "
            "pipeline step (no re-discovery during orchestrator run)."
        ),
    }
    if "scout" in selected_agents:
        _emit("started", "scout")
        with recorder.record_agent(scout_mod.SCOUT_NAME) as builder:
            lookup = scout_mod.run_place_name_lookup(
                builder=builder,
                current_name=water_body.name,
                centroid=water_body.centroid,
                area_km2=water_body.area_km2,
            )
            if lookup is not None:
                scout_outputs["place_lookup"] = lookup.model_dump()
                if lookup.confidence >= 0.55 and lookup.place_name.strip():
                    scout_outputs["resolved_place_name"] = lookup.place_name.strip()
                    scout_outputs["resolved_place_source"] = lookup.source
            builder.set_outputs(scout_outputs)
        _emit("completed", "scout")
    else:
        _emit("started", "scout")
        _record_skipped("scout", "Skipped by Coordinator: existing deterministic scene was reused.")
        _emit("completed", "scout")
    _pause_between_agents()

    # ------------------------------------------------------------------
    # Historian — context briefing. Selected by the Coordinator only
    # when historical context is needed (default: when prior history
    # exists for this water body). On first-time water bodies, the
    # Historian step is skipped and the trace records that reason.
    # ------------------------------------------------------------------
    historian_briefing_dict: dict[str, Any] | None = None
    if "historian" in selected_agents:
        _emit("started", "historian")
        try:
            with recorder.record_agent(historian_mod.HISTORIAN_NAME) as builder:
                briefing = historian_mod.run_historian(
                    builder=builder,
                    db=db,
                    water_body=water_body,
                    source_session_id=session_id,
                    current_indices=indices,
                    scene_capture_date=scene_capture_date,
                    aoi_type=str(aoi.get("type")) if aoi.get("type") else None,
                    place_hint=(
                        str(scout_outputs.get("resolved_place_name"))
                        if scout_outputs.get("resolved_place_name")
                        else None
                    ),
                )
                historian_briefing_dict = briefing.model_dump()
        except Exception as exc:
            LOGGER.warning("Historian failed (%s); Analyst will run without context", exc)
            historian_briefing_dict = None
        _emit("completed", "historian")
    else:
        _emit("started", "historian")
        reason = (
            "Skipped by Coordinator: no prior session history was available for this water body."
        )
        if prior_session_count > 0:
            reason = "Skipped by Coordinator: this run did not require historical context."
        _record_skipped("historian", reason)
        _emit("completed", "historian")
    _pause_between_agents()

    # ------------------------------------------------------------------
    # Analyst — narrative with self-critique. Must always produce a
    # ReasoningBundle even when Gemini is unreachable.
    # ------------------------------------------------------------------
    bundle: ReasoningBundle
    analyst_narrative: dict[str, str]
    if "analyst" in selected_agents:
        _emit("started", "analyst")
        try:
            with recorder.record_agent(analyst_mod.ANALYST_NAME) as builder:
                analyst_output = analyst_mod.run_analyst(
                    builder=builder,
                    water_body=_water_body_payload(water_body),
                    aoi=aoi,
                    risk=risk,
                    indices=indices,
                    evidence=evidence,
                    historian_briefing=historian_briefing_dict,
                )
                bundle = analyst_output.bundle
                analyst_narrative = {
                    "recommendation": bundle.recommendation,
                    "reasoning": bundle.reasoning,
                    "limitations": bundle.limitations,
                }
        except Exception as exc:
            LOGGER.warning("Analyst failed (%s); using deterministic fallback narrative", exc)
            bundle = _deterministic_fallback_bundle(risk=risk, indices=indices, aoi=aoi)
            analyst_narrative = {
                "recommendation": bundle.recommendation,
                "reasoning": bundle.reasoning,
                "limitations": bundle.limitations,
            }
        _emit("completed", "analyst")
    else:
        _emit("started", "analyst")
        _record_skipped(
            "analyst", "Skipped by Coordinator: deterministic narrator fallback used for this run."
        )
        bundle = _deterministic_fallback_bundle(risk=risk, indices=indices, aoi=aoi)
        analyst_narrative = {
            "recommendation": bundle.recommendation,
            "reasoning": bundle.reasoning,
            "limitations": bundle.limitations,
        }
        _emit("completed", "analyst")
    _pause_between_agents()

    # ------------------------------------------------------------------
    # Reporter — final citizen-facing summary card. Always guarded by a
    # deterministic fallback so the session page and PDF stay stable.
    # ------------------------------------------------------------------
    deterministic_summary = _deterministic_public_summary(
        risk=risk,
        aoi=aoi,
        evidence_count=len(evidence or []),
        analyst_limitations=bundle.limitations,
    )
    reporter_summary: CitizenSummary | None = deterministic_summary
    if "reporter" in selected_agents:
        _emit("started", "reporter")
        try:
            with recorder.record_agent(reporter_mod.REPORTER_NAME) as builder:
                reporter_summary = reporter_mod.run_reporter(
                    builder=builder,
                    water_body=_water_body_payload(water_body),
                    aoi=aoi,
                    risk=risk,
                    indices=indices,
                    evidence=evidence,
                    scout_outputs=scout_outputs,
                    historian_briefing=historian_briefing_dict,
                    analyst_narrative=analyst_narrative,
                    fallback_summary=deterministic_summary,
                )
        except Exception as exc:
            LOGGER.warning("Reporter failed (%s); using deterministic summary", exc)
            reporter_summary = deterministic_summary
        _emit("completed", "reporter")
    else:
        _emit("started", "reporter")
        _record_skipped(
            "reporter", "Skipped by Coordinator: deterministic citizen summary was used instead."
        )
        _emit("completed", "reporter")

    return OrchestratorResult(
        bundle=bundle,
        reporter_summary=reporter_summary,
        trace_payload=recorder.compile(),
        scene_id=scene_id,
        scene_capture_date=scene_capture_date,
        scene_cloud_cover=scene_cloud_cover,
    )


# ----------------------------------------------------------------------
# Internals
# ----------------------------------------------------------------------


def _plan(
    recorder: TraceRecorder,
    *,
    water_body: WaterBody,
    prior_session_count: int,
    evidence_count: int,
) -> CoordinatorPlan:
    """Run the Coordinator once. Falls back to a default plan on failure."""
    default = _default_plan(prior_session_count)

    user_payload = {
        "water_body": _water_body_payload(water_body),
        "prior_session_count": prior_session_count,
        "evidence_submitted": evidence_count,
    }

    with recorder.record_agent("coordinator") as builder:
        attempts: list[dict[str, Any]] = [
            {
                "system": _serialise_system(),
                "temperature": 0.15,
                "thinking_budget": 2048,
                "max_output_tokens": 2048,
            },
            {
                "system": f"{_serialise_system()}\n\n{_COORDINATOR_STRICT_JSON_APPENDIX}",
                "temperature": 0.0,
                "thinking_budget": 0,
                "max_output_tokens": 3072,
            },
        ]
        last_error: Exception | None = None
        for idx, attempt in enumerate(attempts, start=1):
            try:
                parsed = call_structured(
                    builder=builder,
                    system_instruction=attempt["system"],
                    user_message=json.dumps(user_payload, indent=2, ensure_ascii=False),
                    response_schema=CoordinatorPlan,
                    temperature=attempt["temperature"],
                    thinking_budget=attempt["thinking_budget"],
                    max_output_tokens=attempt["max_output_tokens"],
                )
                if isinstance(parsed, CoordinatorPlan) and parsed.plan:
                    builder.set_outputs(parsed.model_dump())
                    return parsed
                LOGGER.info("Coordinator attempt %d returned an empty plan", idx)
            except Exception as exc:
                last_error = exc
                LOGGER.warning("Coordinator attempt %d failed (%s)", idx, exc)

        LOGGER.warning("Coordinator exhausted retries (%s); using default plan", last_error)
        builder.set_outputs(default.model_dump())
        return default


def _default_plan(prior_session_count: int) -> CoordinatorPlan:
    """Baseline plan applied when the Coordinator can't be reached."""
    steps: list[PlanStep] = [
        PlanStep(
            agent="scout",
            reason="Pipeline always needs a Scout selection (forwarded from deterministic fetch).",
            budget=PlanBudget(max_tool_calls=6, max_seconds=30),
        )
    ]
    if prior_session_count > 0:
        steps.append(
            PlanStep(
                agent="historian",
                reason="Historian runs when prior history exists for trend/context enrichment.",
                budget=PlanBudget(max_tool_calls=8, max_seconds=45),
            )
        )
    steps.extend(
        [
            PlanStep(
                agent="analyst",
                reason="Always required — produces the narrative bundle.",
                budget=PlanBudget(max_tool_calls=3, max_seconds=30),
            ),
            PlanStep(
                agent="reporter",
                reason="Always required — produces the citizen-facing public summary card.",
                budget=PlanBudget(max_tool_calls=2, max_seconds=20),
            ),
        ]
    )
    rationale = "Default plan: Scout + Analyst + Reporter always run."
    if prior_session_count > 0:
        rationale = "Default plan: Scout + Historian + Analyst + Reporter (history available)."
    return CoordinatorPlan(
        plan=steps,
        rationale=rationale,
        estimated_complexity="medium",
    )


def _deterministic_public_summary(
    *,
    risk: dict[str, Any],
    aoi: dict[str, Any],
    evidence_count: int,
    analyst_limitations: str | None,
) -> CitizenSummary:
    """Deterministic fallback summary for the Reporter step."""
    level = str(risk.get("level", "medium")).lower()
    urgency = str(risk.get("urgency", "elevated")).lower()
    try:
        risk_level = RiskLevel(level)
    except ValueError:
        risk_level = RiskLevel.MEDIUM
    try:
        risk_urgency = Urgency(urgency)
    except ValueError:
        risk_urgency = Urgency.ELEVATED

    now = datetime.now()
    risk_row = RiskAssessmentRead(
        id=uuid4(),
        session_id=uuid4(),
        score=float(risk.get("score", 0.5)),
        level=risk_level,
        urgency=risk_urgency,
        recommendation="Deterministic fallback recommendation.",
        reasoning="Deterministic fallback reasoning.",
        limitations=(analyst_limitations or "No reporter output was produced."),
        contributors={k: float(v) for k, v in (risk.get("contributors") or {}).items()},
        model_id="deterministic-fallback",
        agent_trace_id=None,
        field_brief=None,
        created_at=now,
        updated_at=now,
    )
    summary = build_citizen_summary(
        risk=risk_row,
        aoi_type=str(aoi.get("type")) if aoi.get("type") else None,
        water_fraction=(
            float(aoi.get("water_fraction"))
            if isinstance(aoi.get("water_fraction"), int | float)
            else None
        ),
        evidence_count=evidence_count,
    )
    if summary is not None:
        return summary
    # Safety net: this branch should be unreachable for water AOIs with risk.
    return CitizenSummary(
        tone="unknown",
        headline="Summary pending",
        bottom_line="We could not build a citizen-facing summary for this run.",
        safety_for_humans="Use normal caution until a valid summary is available.",
        safety_for_pets_and_kids="Keep pets and children supervised around the water.",
        what_we_could_not_check="Reporter output was unavailable and deterministic fallback did not resolve.",
        citations=[],
    )


def _deterministic_fallback_bundle(
    *,
    risk: dict[str, Any],
    indices: list[dict[str, Any]],
    aoi: dict[str, Any],
) -> ReasoningBundle:
    """Wrap the deterministic narrator used by AQUALENS_FAKE_GEMINI mode.

    We rebuild the ``RiskScore`` and ``IndexAggregate`` shapes
    expected by :func:`app.services.reasoning._fake_bundle` from the
    plain dicts the orchestrator received so the fallback path
    doesn't drift from the rest of the codebase.
    """
    from app.models.risk_assessment import RiskLevel, Urgency
    from app.models.spectral_index import IndexName
    from app.services.indices import IndexAggregate
    from app.services.risk_model import RiskScore

    score = RiskScore(
        score=float(risk.get("score", 0.5)),
        level=RiskLevel(str(risk.get("level", "medium"))),
        urgency=Urgency(str(risk.get("urgency", "elevated"))),
        contributors={k: float(v) for k, v in (risk.get("contributors") or {}).items()},
    )
    aggregates: list[IndexAggregate] = []
    for entry in indices:
        try:
            name = IndexName(str(entry.get("name", "")).upper())
        except ValueError:
            continue
        aggregates.append(
            IndexAggregate(
                name=name,
                value=float(entry.get("value", 0.0)),
                min_value=float(entry.get("min_value", 0.0)),
                max_value=float(entry.get("max_value", 0.0)),
                stddev=float(entry.get("stddev", 0.0)),
                sample_count=int(entry.get("sample_count", 0)),
                interpretation=str(entry.get("interpretation", "")),
                bands=list(entry.get("bands") or []),
            )
        )
    return _fake_bundle(score, aggregates, aoi_type=aoi.get("type"))


def _water_body_payload(water_body: WaterBody) -> dict[str, Any]:
    return {
        "id": str(water_body.id),
        "name": water_body.name,
        "centroid": water_body.centroid,
        "area_km2": water_body.area_km2,
    }


def _centroid_from(water_body: WaterBody) -> tuple[float, float] | None:
    centroid = water_body.centroid
    if not isinstance(centroid, dict):
        return None
    coords = centroid.get("coordinates")
    if not isinstance(coords, list | tuple) or len(coords) < 2:
        return None
    try:
        return float(coords[0]), float(coords[1])
    except (TypeError, ValueError):
        return None


__all__ = [
    "CoordinatorPlan",
    "OrchestratorResult",
    "PlanBudget",
    "PlanStep",
    "run_orchestrator",
]
