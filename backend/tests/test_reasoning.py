"""Tests for the Gemini-backed narrative generator."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.models.risk_assessment import RiskLevel, Urgency
from app.models.spectral_index import IndexName
from app.models.water_body import WaterBody
from app.services import reasoning
from app.services.indices import IndexAggregate
from app.services.risk_model import RiskScore


def _water_body() -> WaterBody:
    return WaterBody(
        id=uuid4(),
        name="Lake Test",
        description=None,
        geometry={
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        },
        centroid={"type": "Point", "coordinates": [0.5, 0.5]},
        area_km2=12.5,
        source="test",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _aggregates() -> list[IndexAggregate]:
    return [
        IndexAggregate(
            name=name,
            value=0.2,
            min_value=-0.1,
            max_value=0.4,
            stddev=0.05,
            sample_count=100,
            interpretation="elevated",
            bands=["B03", "B11"],
        )
        for name in IndexName
    ]


def _score() -> RiskScore:
    return RiskScore(
        score=0.62,
        level=RiskLevel.MEDIUM,
        urgency=Urgency.ELEVATED,
        contributors={"ndci": 0.18, "ndti": 0.12},
    )


def test_fake_gemini_mode_returns_deterministic_bundle(monkeypatch):
    monkeypatch.setattr(
        reasoning.get_settings(),
        "aqualens_fake_gemini",
        True,
    )
    bundle = reasoning.generate_reasoning(
        score=_score(),
        indices=_aggregates(),
        evidence=[],
        water_body=_water_body(),
    )
    assert bundle.recommendation
    assert bundle.reasoning
    assert bundle.limitations


def test_real_path_parses_json_response(monkeypatch):
    settings = reasoning.get_settings()
    monkeypatch.setattr(settings, "aqualens_fake_gemini", False)
    monkeypatch.setattr(settings, "google_api_key", "fake-key")

    payload = """
    {
      "recommendation": "Send a sampling team within seven days.",
      "reasoning": "NDCI and NDTI are elevated, consistent with an early bloom.",
      "limitations": "Advisory only; no laboratory confirmation has been performed."
    }
    """

    with patch.object(reasoning, "_call_gemini", return_value=payload) as call:
        bundle = reasoning.generate_reasoning(
            score=_score(),
            indices=_aggregates(),
            evidence=[],
            water_body=_water_body(),
        )

    assert call.call_count == 1
    assert "sampling" in bundle.recommendation.lower()


def test_real_path_retries_once_on_invalid_json(monkeypatch):
    settings = reasoning.get_settings()
    monkeypatch.setattr(settings, "aqualens_fake_gemini", False)
    monkeypatch.setattr(settings, "google_api_key", "fake-key")

    good_payload = (
        '{"recommendation": "Investigate", "reasoning": "Both NDCI and NDTI elevated.",'
        ' "limitations": "Advisory only — confirm with field sampling."}'
    )
    side_effect = ["not json at all", good_payload]
    with patch.object(reasoning, "_call_gemini", side_effect=side_effect) as call:
        bundle = reasoning.generate_reasoning(
            score=_score(),
            indices=_aggregates(),
            evidence=[],
            water_body=_water_body(),
        )

    assert call.call_count == 2
    assert bundle.recommendation == "Investigate"


def test_missing_api_key_raises_configuration_error(monkeypatch):
    settings = reasoning.get_settings()
    monkeypatch.setattr(settings, "aqualens_fake_gemini", False)
    monkeypatch.setattr(settings, "google_api_key", None)
    monkeypatch.setattr(settings, "google_api_key_fallback", None)
    monkeypatch.setattr(settings, "google_api_key_fallback_2", None)
    with pytest.raises(reasoning.ConfigurationError):
        reasoning.generate_reasoning(
            score=_score(),
            indices=_aggregates(),
            evidence=[],
            water_body=_water_body(),
        )


def test_quota_error_falls_over_to_fallback_key(monkeypatch):
    settings = reasoning.get_settings()
    monkeypatch.setattr(settings, "aqualens_fake_gemini", False)
    monkeypatch.setattr(settings, "google_api_key", "primary-key")
    monkeypatch.setattr(settings, "google_api_key_fallback", "fallback-key")
    monkeypatch.setattr(settings, "google_api_key_fallback_2", None)

    good_payload = (
        '{"recommendation": "Sample within seven days.",'
        ' "reasoning": "NDCI and NDTI both elevated; treat as advisory.",'
        ' "limitations": "Advisory only; field sampling required."}'
    )

    def fake_call(*, user_json, system_instruction, model, api_key):
        if api_key == "primary-key":
            raise reasoning.QuotaExceededError("429 RESOURCE_EXHAUSTED: quota exceeded for model")
        return good_payload

    with patch.object(reasoning, "_call_gemini", side_effect=fake_call) as call:
        bundle = reasoning.generate_reasoning(
            score=_score(),
            indices=_aggregates(),
            evidence=[],
            water_body=_water_body(),
        )

    # First call to primary (quota), second call to fallback (success).
    assert call.call_count == 2
    assert call.call_args_list[0].kwargs["api_key"] == "primary-key"
    assert call.call_args_list[1].kwargs["api_key"] == "fallback-key"
    assert "sample" in bundle.recommendation.lower()


def test_quota_error_uses_second_fallback_key(monkeypatch):
    settings = reasoning.get_settings()
    monkeypatch.setattr(settings, "aqualens_fake_gemini", False)
    monkeypatch.setattr(settings, "google_api_key", "primary-key")
    monkeypatch.setattr(settings, "google_api_key_fallback", "fallback-key-1")
    monkeypatch.setattr(settings, "google_api_key_fallback_2", "fallback-key-2")

    good_payload = (
        '{"recommendation": "Sample within seven days.",'
        ' "reasoning": "NDCI and NDTI both elevated; treat as advisory.",'
        ' "limitations": "Advisory only; field sampling required."}'
    )

    def fake_call(*, user_json, system_instruction, model, api_key):
        if api_key in {"primary-key", "fallback-key-1"}:
            raise reasoning.QuotaExceededError("429 RESOURCE_EXHAUSTED: quota exceeded for model")
        return good_payload

    with patch.object(reasoning, "_call_gemini", side_effect=fake_call) as call:
        bundle = reasoning.generate_reasoning(
            score=_score(),
            indices=_aggregates(),
            evidence=[],
            water_body=_water_body(),
        )

    assert call.call_count == 3
    assert call.call_args_list[0].kwargs["api_key"] == "primary-key"
    assert call.call_args_list[1].kwargs["api_key"] == "fallback-key-1"
    assert call.call_args_list[2].kwargs["api_key"] == "fallback-key-2"
    assert "sample" in bundle.recommendation.lower()


def test_quota_classifier_recognises_common_signals():
    cases = [
        Exception("429 RESOURCE_EXHAUSTED: quota for 'gemini-2.5-flash'"),
        Exception("Quota exceeded for project"),
        Exception("rate limit reached"),
    ]
    for exc in cases:
        assert reasoning._looks_like_quota_error(exc), exc

    not_quota = [
        Exception("Invalid API key"),
        Exception("ValidationError on response_schema"),
    ]
    for exc in not_quota:
        assert not reasoning._looks_like_quota_error(exc), exc
