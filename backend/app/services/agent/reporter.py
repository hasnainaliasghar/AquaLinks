"""Reporter agent — writes the citizen-facing public summary.

This is the final agent in the workflow. It consumes deterministic
risk numbers plus specialist outputs (Scout/Historian/Analyst) and
emits the concise plain-English verdict shown on the session page.

Guardrails:
- Reporter never edits deterministic risk numbers.
- If Reporter fails, the orchestrator ships a deterministic fallback
  summary from :mod:`app.services.citizen_summary`.
"""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from app.core.logging import get_logger
from app.services.agent.gemini_runtime import call_structured, to_json
from app.services.agent.trace import AgentTraceBuilder
from app.services.citizen_summary import CitizenSummary

LOGGER = get_logger(__name__)

REPORTER_NAME = "reporter"

_SYSTEM_JSON: dict[str, Any] = json.loads(
    files("app.services.agent.prompts").joinpath("reporter.json").read_text(encoding="utf-8")
)


def _serialise_system() -> str:
    return json.dumps(_SYSTEM_JSON, indent=2, ensure_ascii=False)


def run_reporter(
    *,
    builder: AgentTraceBuilder,
    water_body: dict[str, Any],
    aoi: dict[str, Any],
    risk: dict[str, Any],
    indices: list[dict[str, Any]],
    evidence: list[dict[str, Any]] | None,
    scout_outputs: dict[str, Any] | None,
    historian_briefing: dict[str, Any] | None,
    analyst_narrative: dict[str, str],
    fallback_summary: CitizenSummary,
) -> CitizenSummary:
    """Run Reporter and return a citizen-facing summary.

    ``fallback_summary`` is deterministic copy prepared by the
    orchestrator. It is used on any Reporter failure.
    """
    user_payload = {
        "water_body": water_body,
        "aoi": aoi,
        "risk": risk,
        "indices": indices,
        "evidence": evidence or [],
        "scout_outputs": scout_outputs or {},
        "historian_briefing": historian_briefing,
        "analyst_narrative": analyst_narrative,
    }
    try:
        parsed = call_structured(
            builder=builder,
            system_instruction=_serialise_system(),
            user_message=to_json(user_payload),
            response_schema=CitizenSummary,
            temperature=0.2,
        )
    except Exception as exc:
        LOGGER.warning("Reporter call failed (%s); using deterministic fallback", exc)
        parsed = fallback_summary

    if not isinstance(parsed, CitizenSummary):
        parsed = CitizenSummary.model_validate(parsed.model_dump())

    # Guardrail: keep Reporter tone aligned with deterministic risk band.
    expected_tone = {
        "low": "safe",
        "medium": "caution",
        "high": "avoid",
    }.get(str(risk.get("level", "")).lower(), "unknown")
    if parsed.tone != expected_tone:
        parsed.tone = expected_tone

    # Keep only URL-like citations.
    parsed.citations = [
        c
        for c in parsed.citations
        if (c.uri or "").startswith("http://") or (c.uri or "").startswith("https://")
    ]

    builder.set_outputs(parsed.model_dump())
    return parsed


__all__ = ["REPORTER_NAME", "run_reporter"]
