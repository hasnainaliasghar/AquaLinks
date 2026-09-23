"""Smoke tests for the deterministic citizen-summary service.

These cover the public-facing branches: AOI-on-land, AOI-on-mixed,
and the three risk levels. They lock in the user-visible tone +
headline so accidental wording changes show up in code review.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.models.session import AOIType
from app.schemas.risk import RiskAssessmentRead
from app.services.citizen_summary import build_citizen_summary


def _risk(
    level: str, urgency: str = "routine", limitations: str = "cloud cover 12%"
) -> RiskAssessmentRead:
    now = datetime.now()
    return RiskAssessmentRead(
        id=uuid4(),
        session_id=uuid4(),
        score=0.4,
        level=level,
        urgency=urgency,
        recommendation="recommendation",
        reasoning="reasoning",
        limitations=limitations,
        contributors={},
        model_id="gemini-2.5-flash",
        agent_trace_id=None,
        field_brief=None,
        created_at=now,
        updated_at=now,
    )


def test_land_aoi_returns_not_water_summary() -> None:
    summary = build_citizen_summary(
        risk=_risk("medium"),
        aoi_type=AOIType.LAND,
        water_fraction=0.05,
        evidence_count=0,
    )
    assert summary is not None
    assert summary.tone == "not_water"
    assert "land" in summary.headline.lower()
    assert "5%" in summary.what_we_could_not_check


def test_mixed_aoi_returns_not_water_with_mixed_copy() -> None:
    summary = build_citizen_summary(
        risk=_risk("medium"),
        aoi_type=AOIType.MIXED,
        water_fraction=0.45,
        evidence_count=0,
    )
    assert summary is not None
    assert summary.tone == "not_water"
    assert "part land" in summary.headline


def test_low_risk_summary_is_safe_branch() -> None:
    summary = build_citizen_summary(
        risk=_risk("low"),
        aoi_type=AOIType.WATER,
        water_fraction=0.98,
        evidence_count=0,
    )
    assert summary is not None
    assert summary.tone == "safe"
    # The "what we couldn't check" paragraph always mentions in-situ gaps.
    assert "satellite" in summary.what_we_could_not_check.lower()
    # When no evidence has been submitted the paragraph calls that out.
    assert "evidence" in summary.what_we_could_not_check.lower()


def test_high_risk_immediate_summary_escalates() -> None:
    summary = build_citizen_summary(
        risk=_risk("high", urgency="immediate", limitations="bloom suspected"),
        aoi_type=AOIType.WATER,
        water_fraction=0.99,
        evidence_count=2,
    )
    assert summary is not None
    assert summary.tone == "avoid"
    assert "immediate" in summary.bottom_line.lower()
    # Evidence count > 0 → drop the "no evidence yet" disclaimer.
    assert "evidence" not in summary.what_we_could_not_check.lower()


def test_returns_none_when_no_risk_and_no_aoi() -> None:
    assert (
        build_citizen_summary(
            risk=None,
            aoi_type=None,
            water_fraction=None,
            evidence_count=0,
        )
        is None
    )


def test_reporter_payload_overrides_deterministic_copy_when_valid() -> None:
    summary = build_citizen_summary(
        risk=_risk("medium"),
        aoi_type=AOIType.WATER,
        water_fraction=0.99,
        evidence_count=1,
        reporter_payload={
            "tone": "caution",
            "headline": "Custom reporter headline",
            "bottom_line": "Reporter-provided copy.",
            "safety_for_humans": "Reporter humans guidance.",
            "safety_for_pets_and_kids": "Reporter pets guidance.",
            "what_we_could_not_check": "Reporter limitations.",
            "citations": [
                {
                    "title": "Local bulletin",
                    "uri": "https://example.com/water-bulletin",
                    "published_at": "2026-05-17",
                }
            ],
        },
    )
    assert summary is not None
    assert summary.headline == "Custom reporter headline"
    assert len(summary.citations) == 1


def test_reporter_payload_tone_is_guarded_by_deterministic_level() -> None:
    summary = build_citizen_summary(
        risk=_risk("high"),
        aoi_type=AOIType.WATER,
        water_fraction=0.98,
        evidence_count=0,
        reporter_payload={
            "tone": "safe",
            "headline": "Conflicting tone",
            "bottom_line": "Copy.",
            "safety_for_humans": "Guidance.",
            "safety_for_pets_and_kids": "Guidance.",
            "what_we_could_not_check": "Limits.",
            "citations": [],
        },
    )
    assert summary is not None
    assert summary.tone == "avoid"
