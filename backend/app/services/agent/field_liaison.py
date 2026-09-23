"""Field Liaison agent — turns the Analyst narrative into an ops handoff.

Single structured-output Gemini call. No tools. The output schema is
:class:`~app.schemas.field_brief.FieldBrief`, which the API layer
returns to the frontend as the "Field Brief" card and which the PDF
renders as a clean action plan in the agent appendix.

On failure (Gemini error, schema parse rejection) the agent returns a
deterministic fallback brief built from the risk level + evidence
focus, so the rest of the pipeline keeps moving.
"""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from app.core.logging import get_logger
from app.schemas.field_brief import FieldBrief, FieldLocation, FieldTask
from app.services.agent.analyst import EvidenceFocus
from app.services.agent.gemini_runtime import call_structured, to_json
from app.services.agent.trace import AgentTraceBuilder

LOGGER = get_logger(__name__)

FIELD_LIAISON_NAME = "field_liaison"


_SYSTEM_JSON: dict[str, Any] = json.loads(
    files("app.services.agent.prompts").joinpath("field_liaison.json").read_text(encoding="utf-8")
)


def _serialise_system() -> str:
    return json.dumps(_SYSTEM_JSON, indent=2, ensure_ascii=False)


_TURNAROUND_BY_URGENCY = {
    "routine": 168,
    "elevated": 72,
    "immediate": 24,
}


def run_field_liaison(
    *,
    builder: AgentTraceBuilder,
    water_body: dict[str, Any],
    centroid_lng_lat: tuple[float, float] | None,
    risk_level: str,
    urgency: str,
    narrative: dict[str, str],
    evidence_focus: list[EvidenceFocus] | list[dict[str, Any]],
) -> FieldBrief:
    """Run the Field Liaison and return its structured action plan."""
    # Normalise evidence_focus to plain dicts so the prompt sees a
    # clean JSON payload either way.
    focus_payload: list[dict[str, Any]] = []
    for entry in evidence_focus or []:
        if isinstance(entry, EvidenceFocus):
            focus_payload.append(entry.model_dump())
        elif isinstance(entry, dict):
            focus_payload.append(entry)

    centroid = (
        [float(centroid_lng_lat[0]), float(centroid_lng_lat[1])]
        if centroid_lng_lat is not None
        else None
    )
    user_payload = {
        "water_body": water_body,
        "centroid": centroid,
        "risk": {"level": risk_level, "urgency": urgency},
        "narrative": narrative,
        "evidence_focus": focus_payload,
    }

    try:
        parsed = call_structured(
            builder=builder,
            system_instruction=_serialise_system(),
            user_message=to_json(user_payload),
            response_schema=FieldBrief,
            temperature=0.2,
        )
    except Exception as exc:
        LOGGER.warning("Field Liaison call failed (%s); using deterministic fallback", exc)
        parsed = _fallback_brief(
            centroid=centroid,
            risk_level=risk_level,
            urgency=urgency,
            evidence_focus=focus_payload,
        )

    if not isinstance(parsed, FieldBrief):
        # call_structured guarantees a FieldBrief on success; this is
        # defensive in case a future code path returns a sibling type.
        parsed = FieldBrief.model_validate(parsed.model_dump())

    builder.set_outputs(parsed.model_dump())
    return parsed


def _fallback_brief(
    *,
    centroid: list[float] | None,
    risk_level: str,
    urgency: str,
    evidence_focus: list[dict[str, Any]],
) -> FieldBrief:
    """Deterministic brief assembled from inputs alone.

    Used when the Gemini call fails. Keeps the pipeline shippable and
    gives the field team a usable plan even when the agent layer is
    degraded.
    """
    turnaround = _TURNAROUND_BY_URGENCY.get(urgency, 72)
    lat = centroid[1] if centroid else 0.0
    lng = centroid[0] if centroid else 0.0
    base_location = FieldLocation(
        lat=lat,
        lng=lng,
        description="Centre of the chosen area (no specific spot was flagged).",
    )

    tasks: list[FieldTask] = []
    for focus in evidence_focus:
        target = str(focus.get("target") or "Centre of the chosen area")
        reason = str(focus.get("reason") or "follow-up requested by the analyst")
        priority = "p0" if risk_level == "high" else "p1"
        tasks.append(
            FieldTask(
                priority=priority,  # type: ignore[arg-type]
                location=FieldLocation(
                    lat=lat,
                    lng=lng,
                    description=f"{target} — coordinates are the centre of the chosen area.",
                ),
                sample_type=f"Take a water sample at {target.lower()}",
                equipment=["1 L sample bottle", "ice pack", "field notebook"],
                photo_prompts=[
                    f"Wide shot showing {target}",
                    f"Close-up of the feature flagged: {reason}",
                ],
                estimated_minutes=45,
            )
        )

    if not tasks:
        if risk_level == "high":
            tasks.append(
                FieldTask(
                    priority="p0",
                    location=base_location,
                    sample_type="Take a water sample",
                    equipment=["1 L sample bottle", "ice pack", "Secchi disk"],
                    photo_prompts=[
                        "Wide shot of the whole area",
                        "Shoreline included for scale reference",
                    ],
                    estimated_minutes=60,
                )
            )
        else:
            tasks.append(
                FieldTask(
                    priority="p2",
                    location=base_location,
                    sample_type="Walk-around visual check",
                    equipment=["field notebook", "phone camera"],
                    photo_prompts=["Wide shot of the whole area"],
                    estimated_minutes=20,
                )
            )

    escalate = (
        "local water authority"
        if risk_level == "high" and any(t.priority == "p0" for t in tasks)
        else None
    )
    return FieldBrief(tasks=tasks, turnaround_hours=turnaround, escalate_to=escalate)


__all__ = ["FIELD_LIAISON_NAME", "run_field_liaison"]
