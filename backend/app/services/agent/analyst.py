"""Analyst agent — writes the narrative with a self-critique loop.

Three Gemini calls maximum:

1. **Draft** — schema-typed first pass that produces a
   ``ReasoningBundle``-shaped narrative plus an ``evidence_focus`` list
   for the Reporter.
2. **Critique** — a separate Gemini call inspects the draft against
   the Analyst's hard rules and emits ``accept_draft`` plus a list of
   violations and suggested edits.
3. **Rewrite (conditional)** — when the critique rejects the draft we
   run a single rewrite pass with the critique appended. Maximum one
   rewrite per session; the trace records both drafts so the UI can
   show the diff.

Returns a fully-populated :class:`AnalystOutput` whose ``bundle`` is
shape-compatible with :class:`app.services.reasoning.ReasoningBundle`
so the existing pipeline can persist it without any change.
"""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.agent.gemini_runtime import call_structured, to_json
from app.services.agent.trace import AgentTraceBuilder
from app.services.reasoning import ReasoningBundle

LOGGER = get_logger(__name__)

ANALYST_NAME = "analyst"


# ----------------------------------------------------------------------
# Output schema
# ----------------------------------------------------------------------


class EvidenceFocus(BaseModel):
    target: str = Field(description="What to sample / photograph / measure on site.")
    reason: str = Field(description="Why this matters given the spectral indices.")


class AnalystDraft(BaseModel):
    """Shape of each draft Gemini emits.

    Matches ``ReasoningBundle`` on the three narrative fields plus the
    ``evidence_focus`` array consumed by the Reporter.
    """

    recommendation: str
    reasoning: str
    limitations: str
    evidence_focus: list[EvidenceFocus] = Field(default_factory=list)


class CritiqueReport(BaseModel):
    """The Critic's verdict on a draft."""

    accept_draft: bool
    rule_violations: list[str] = Field(default_factory=list)
    suggested_edits: list[str] = Field(default_factory=list)


class AnalystOutput(BaseModel):
    """Final result returned to the orchestrator."""

    bundle: ReasoningBundle
    evidence_focus: list[EvidenceFocus]
    drafts: list[AnalystDraft]
    critique: CritiqueReport | None
    rewrote: bool


# ----------------------------------------------------------------------
# Prompts
# ----------------------------------------------------------------------


_DRAFT_SYSTEM_JSON: dict[str, Any] = json.loads(
    files("app.services.agent.prompts").joinpath("analyst_draft.json").read_text(encoding="utf-8")
)
_CRITIQUE_SYSTEM_JSON: dict[str, Any] = json.loads(
    files("app.services.agent.prompts")
    .joinpath("analyst_critique.json")
    .read_text(encoding="utf-8")
)


def _serialise(d: dict[str, Any]) -> str:
    return json.dumps(d, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------


def run_analyst(
    *,
    builder: AgentTraceBuilder,
    water_body: dict[str, Any],
    aoi: dict[str, Any],
    risk: dict[str, Any],
    indices: list[dict[str, Any]],
    evidence: list[dict[str, Any]] | None = None,
    historian_briefing: dict[str, Any] | None = None,
) -> AnalystOutput:
    """Run the Analyst draft → critique → optional rewrite loop."""
    facts = {
        "water_body": water_body,
        "aoi": aoi,
        "risk": risk,
        "indices": indices,
        "evidence": evidence or [],
        "historian_briefing": historian_briefing,
    }

    draft_v1 = _draft(builder, facts)
    drafts: list[AnalystDraft] = [draft_v1]

    critique: CritiqueReport | None = _critique(builder, facts, draft_v1)
    rewrote = False
    final_draft = draft_v1

    if critique is not None and not critique.accept_draft:
        rewritten = _rewrite(builder, facts, draft_v1, critique)
        if rewritten is not None:
            drafts.append(rewritten)
            final_draft = rewritten
            rewrote = True

    bundle = ReasoningBundle(
        recommendation=final_draft.recommendation,
        reasoning=final_draft.reasoning,
        limitations=final_draft.limitations,
    )
    output = AnalystOutput(
        bundle=bundle,
        evidence_focus=final_draft.evidence_focus,
        drafts=drafts,
        critique=critique,
        rewrote=rewrote,
    )
    builder.set_outputs(output.model_dump())
    return output


# ----------------------------------------------------------------------
# Individual passes
# ----------------------------------------------------------------------


def _draft(builder: AgentTraceBuilder, facts: dict[str, Any]) -> AnalystDraft:
    user_message = to_json(facts)
    parsed = call_structured(
        builder=builder,
        system_instruction=_serialise(_DRAFT_SYSTEM_JSON),
        user_message=user_message,
        response_schema=AnalystDraft,
        temperature=0.25,
    )
    if isinstance(parsed, AnalystDraft):
        return parsed
    # call_structured returns a BaseModel; defensive cast for older callers.
    return AnalystDraft.model_validate(parsed.model_dump())


def _critique(
    builder: AgentTraceBuilder, facts: dict[str, Any], draft: AnalystDraft
) -> CritiqueReport | None:
    try:
        parsed = call_structured(
            builder=builder,
            system_instruction=_serialise(_CRITIQUE_SYSTEM_JSON),
            user_message=to_json({"facts": facts, "draft": draft.model_dump()}),
            response_schema=CritiqueReport,
            temperature=0.1,
        )
    except Exception as exc:
        LOGGER.warning("Analyst critique pass failed (%s); shipping draft as-is", exc)
        return None
    if isinstance(parsed, CritiqueReport):
        return parsed
    return CritiqueReport.model_validate(parsed.model_dump())


def _rewrite(
    builder: AgentTraceBuilder,
    facts: dict[str, Any],
    draft_v1: AnalystDraft,
    critique: CritiqueReport,
) -> AnalystDraft | None:
    # Append the critique to the system instruction so the rewrite pass
    # sees the violations it needs to fix without losing the original
    # rules. We re-use the draft system prompt verbatim and graft a new
    # ``rewrite_directive`` field onto its top level.
    augmented_system = dict(_DRAFT_SYSTEM_JSON)
    augmented_system["rewrite_directive"] = {
        "reason": "Critic rejected the prior draft.",
        "violations": critique.rule_violations,
        "suggested_edits": critique.suggested_edits,
        "instruction": (
            "Produce a new draft that fixes every listed violation while still "
            "satisfying every rule in hard_rules. Do not echo the prior draft. "
            "Do not include any commentary outside the JSON."
        ),
    }

    try:
        parsed = call_structured(
            builder=builder,
            system_instruction=_serialise(augmented_system),
            user_message=to_json(
                {
                    "facts": facts,
                    "prior_draft": draft_v1.model_dump(),
                }
            ),
            response_schema=AnalystDraft,
            temperature=0.2,
        )
    except Exception as exc:
        LOGGER.warning("Analyst rewrite pass failed (%s); keeping draft v1", exc)
        return None
    if isinstance(parsed, AnalystDraft):
        return parsed
    return AnalystDraft.model_validate(parsed.model_dump())


__all__ = [
    "ANALYST_NAME",
    "AnalystDraft",
    "AnalystOutput",
    "CritiqueReport",
    "EvidenceFocus",
    "run_analyst",
]
