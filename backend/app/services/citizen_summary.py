"""Deterministic citizen-facing analysis summary.

Turns the technical risk-assessment + AOI classification into a short,
plain-English verdict aimed at a non-expert reading the session page or
PDF: *Is this water safe? What about my pets or kids? What couldn't we
check?* The output is computed without any LLM call — it's a templated
rewrite of values the risk model already produced, so it's free,
deterministic, and never mid-string-truncated.

The shape lives in :class:`CitizenSummary` and is rendered on:

* ``GET /api/v1/sessions/{id}`` → ``risk.citizen_summary`` (web UI)
* The PDF report's "What this means for you" panel.

The summary is intentionally cautious: AquaLens is advisory, never
certifying — every "likely safe" branch reminds the reader that
satellite indices can't detect invisible chemical contaminants without
in-situ sampling.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.models.session import AOIType
from app.schemas.risk import RiskAssessmentRead

CitizenTone = Literal["safe", "caution", "avoid", "not_water", "unknown"]


class CitizenCitation(BaseModel):
    """One external source linked to the summary."""

    title: str | None = None
    uri: str
    published_at: str | None = None


class CitizenSummary(BaseModel):
    """Plain-English verdict shown to the end user."""

    tone: CitizenTone
    headline: str
    bottom_line: str
    safety_for_humans: str
    safety_for_pets_and_kids: str
    what_we_could_not_check: str
    citations: list[CitizenCitation] = Field(default_factory=list)


# ---------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------


def build_citizen_summary(
    *,
    risk: RiskAssessmentRead | None,
    aoi_type: AOIType | str | None,
    water_fraction: float | None,
    evidence_count: int,
    reporter_payload: dict[str, Any] | None = None,
) -> CitizenSummary | None:
    """Build a citizen summary for one session, or ``None`` if there's
    nothing meaningful to say yet (session still processing, no risk
    row, no AOI classification)."""
    aoi = _coerce_aoi(aoi_type)

    # AOI is land → the indices below describe vegetation/soil, not
    # water. We don't run the agent layer on land AOIs so the risk row
    # may exist but its narrative is the deterministic fallback; in
    # either case the user-facing message is the same.
    if aoi in (AOIType.LAND, AOIType.MIXED):
        return _not_water_summary(aoi=aoi, water_fraction=water_fraction)

    if risk is None:
        return None

    reporter_summary = _reporter_summary_or_none(
        reporter_payload=reporter_payload,
        risk=risk,
    )
    if reporter_summary is not None:
        return reporter_summary

    level = str(risk.level)
    if level == "low":
        return _low_summary(risk=risk, evidence_count=evidence_count)
    if level == "high":
        return _high_summary(risk=risk, evidence_count=evidence_count)
    # Default: medium.
    return _medium_summary(risk=risk, evidence_count=evidence_count)


# ---------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------


def _not_water_summary(
    *,
    aoi: AOIType,
    water_fraction: float | None,
) -> CitizenSummary:
    pct = (
        f"Only about {water_fraction * 100:.0f}% of the area you picked is water."
        if water_fraction is not None and water_fraction > 0
        else "The area you picked doesn't appear to contain open water."
    )
    if aoi == AOIType.MIXED:
        headline = "The area you picked is part land, part water"
        bottom_line = (
            "The reading below mixes water and land, so the water-quality "
            "numbers aren't reliable. Pick a tighter area over the water itself "
            "for a real reading."
        )
    else:
        headline = "The area you picked is land, not water"
        bottom_line = (
            "We can't tell you about water quality here — there's no water for the "
            "satellite to measure. Pick a lake, river, or coastal patch and try again."
        )
    return CitizenSummary(
        tone="not_water",
        headline=headline,
        bottom_line=bottom_line,
        safety_for_humans=(
            "Nothing to assess: the indices below describe vegetation or soil, "
            "not water quality."
        ),
        safety_for_pets_and_kids=("Same — there's no aquatic exposure to evaluate from this area."),
        what_we_could_not_check=(
            f"{pct} We skipped the full multi-agent analysis to save compute, "
            "since running it over land wouldn't produce a meaningful reading."
        ),
    )


def _low_summary(*, risk: RiskAssessmentRead, evidence_count: int) -> CitizenSummary:
    return CitizenSummary(
        tone="safe",
        headline="Likely safe today, based on what the satellite can see",
        bottom_line=(
            "Indicators are in the calm range — no signs of an active algal "
            "bloom, heavy sediment plume, or other visible disturbance from "
            "above. Treat this as a green light to proceed with normal "
            "precautions."
        ),
        safety_for_humans=(
            "Typical recreational contact (paddling, fishing, brief swimming) "
            "looks reasonable. Don't drink untreated water — satellites can't "
            "detect bacteria, dissolved chemicals, or invisible contaminants."
        ),
        safety_for_pets_and_kids=(
            "Pets and children should be fine with normal supervision. Rinse "
            "off after contact and keep an eye out for floating scum or "
            "unusual smells, which can appear between satellite passes."
        ),
        what_we_could_not_check=_limitations_paragraph(risk=risk, evidence_count=evidence_count),
    )


def _medium_summary(*, risk: RiskAssessmentRead, evidence_count: int) -> CitizenSummary:
    return CitizenSummary(
        tone="caution",
        headline="Use caution — some indicators are elevated",
        bottom_line=(
            "One or more water-quality indicators are above the calm range. "
            "It's not a full alarm, but conditions warrant a closer look "
            "before significant contact."
        ),
        safety_for_humans=(
            "Avoid swallowing the water and limit prolonged immersion. If "
            "you notice green/brown discoloration, scum on the surface, or a "
            "musty smell up close, treat that as a stronger signal to stay "
            "out until a local sample confirms it's safe."
        ),
        safety_for_pets_and_kids=(
            "Don't let pets drink directly from this water and keep small "
            "children from putting their hands in their mouths after contact. "
            "Dogs are especially sensitive to cyanobacteria toxins."
        ),
        what_we_could_not_check=_limitations_paragraph(risk=risk, evidence_count=evidence_count),
    )


def _high_summary(*, risk: RiskAssessmentRead, evidence_count: int) -> CitizenSummary:
    immediate = str(risk.urgency) == "immediate"
    bottom = (
        "Indicators suggest an active water-quality problem — possible algal "
        "bloom, pollution plume, or major sediment event. "
    )
    if immediate:
        bottom += (
            "This warrants immediate action: notify the relevant local "
            "authority and avoid contact until a field sample confirms it's safe."
        )
    else:
        bottom += "Avoid contact until you can confirm conditions with a field sample."
    return CitizenSummary(
        tone="avoid",
        headline="Avoid contact — conditions look unsafe today",
        bottom_line=bottom,
        safety_for_humans=(
            "Don't swim, don't wade, and don't drink — even after boiling, "
            "since some cyanotoxins survive heat. If you've already been in "
            "the water and feel unwell, contact a clinician and mention the "
            "potential exposure."
        ),
        safety_for_pets_and_kids=(
            "Keep pets and children completely away from this water. Pets "
            "that lick wet fur after contact can ingest toxins; a single "
            "drink can be fatal for dogs during a severe cyanobacteria bloom."
        ),
        what_we_could_not_check=_limitations_paragraph(risk=risk, evidence_count=evidence_count),
    )


# ---------------------------------------------------------------------
# Shared bits
# ---------------------------------------------------------------------


def _limitations_paragraph(
    *,
    risk: RiskAssessmentRead,
    evidence_count: int,
) -> str:
    """Combine the model's structured limitations with the obvious gaps.

    The risk model already produces a ``limitations`` string, but it
    tends to be technical. We prepend a citizen-readable lead-in and
    fall back to a generic note when the field is empty.
    """
    base = (
        "Satellites can't see dissolved chemicals, bacteria, or anything "
        "underneath the water's surface — so a clean satellite reading "
        "isn't a certificate."
    )
    if evidence_count == 0:
        base += (
            " No one has submitted on-the-ground evidence for this session yet, "
            "which would normally tighten the verdict."
        )
    raw = (risk.limitations or "").strip()
    if raw:
        base += f" Model notes: {raw}"
    return base


def _coerce_aoi(value: AOIType | str | None) -> AOIType | None:
    if value is None:
        return None
    if isinstance(value, AOIType):
        return value
    try:
        return AOIType(str(value))
    except ValueError:
        return None


def _reporter_summary_or_none(
    *,
    reporter_payload: dict[str, Any] | None,
    risk: RiskAssessmentRead,
) -> CitizenSummary | None:
    """Validate and normalise a Reporter-produced summary payload.

    The Reporter output is optional and lives in a legacy JSON column.
    If it is malformed (or not present) we fall back to deterministic
    copy so the UI and PDF always have a stable summary.
    """
    if not isinstance(reporter_payload, dict) or not reporter_payload:
        return None

    try:
        summary = CitizenSummary.model_validate(reporter_payload)
    except ValidationError:
        return None

    # Guardrail: Reporter copy must respect the deterministic risk band.
    expected_tone: CitizenTone = {
        "low": "safe",
        "medium": "caution",
        "high": "avoid",
    }.get(str(risk.level), "unknown")
    if summary.tone != expected_tone:
        summary.tone = expected_tone

    # Keep only URL-like citations so we never render junk links.
    filtered: list[CitizenCitation] = []
    for c in summary.citations:
        uri = (c.uri or "").strip()
        if uri.startswith("http://") or uri.startswith("https://"):
            filtered.append(c)
    summary.citations = filtered
    return summary


__all__ = [
    "CitizenCitation",
    "CitizenSummary",
    "CitizenTone",
    "build_citizen_summary",
]
