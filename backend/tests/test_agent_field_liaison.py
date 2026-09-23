"""Stage 7: Field Liaison agent.

Covers:
- Happy path: Gemini returns a schema-valid FieldBrief; the agent
  passes it through unchanged.
- Fallback when Gemini errors: agent produces a deterministic brief
  built from inputs alone, with priority + turnaround mapped from
  risk level + urgency.
- evidence_focus normalisation accepts both EvidenceFocus instances
  and plain dicts.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest

from app.schemas.field_brief import FieldBrief
from app.services.agent.analyst import EvidenceFocus
from app.services.agent.field_liaison import run_field_liaison
from app.services.agent.trace import TraceRecorder

# ----------------------------------------------------------------------
# Fake Gemini
# ----------------------------------------------------------------------


def _candidate(text: str) -> Any:
    return SimpleNamespace(
        content=SimpleNamespace(
            role="model",
            parts=[SimpleNamespace(text=text, function_call=None)],
        ),
        finish_reason=SimpleNamespace(value="STOP"),
        grounding_metadata=None,
    )


def _response(text: str) -> Any:
    return SimpleNamespace(
        candidates=[_candidate(text)],
        text=text,
        usage_metadata=SimpleNamespace(prompt_token_count=70, candidates_token_count=80),
    )


class _GeminiQueues:
    """Holder for the response queue + an error-injection queue."""

    def __init__(self) -> None:
        self.responses: list[Any] = []
        self.raise_next: list[Exception] = []

    def append(self, response: Any) -> None:
        self.responses.append(response)


@pytest.fixture()
def fake_gemini(monkeypatch) -> Iterator[_GeminiQueues]:
    queues = _GeminiQueues()

    class _FakeModels:
        def generate_content(self, *, model, contents, config):
            if queues.raise_next:
                raise queues.raise_next.pop(0)
            if not queues.responses:
                raise AssertionError("Gemini queue exhausted")
            return queues.responses.pop(0)

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.models = _FakeModels()

    fake_types = SimpleNamespace(
        FunctionDeclaration=lambda **kw: SimpleNamespace(**kw),
        Tool=lambda **kw: SimpleNamespace(**kw),
        GenerateContentConfig=lambda **kw: SimpleNamespace(**kw),
        ThinkingConfig=lambda **kw: SimpleNamespace(**kw),
        Content=lambda role, parts: SimpleNamespace(role=role, parts=parts),
        Part=SimpleNamespace(
            from_text=lambda text: SimpleNamespace(text=text, function_call=None),
            from_function_response=lambda name, response: SimpleNamespace(
                function_response=SimpleNamespace(name=name, response=response),
            ),
        ),
    )
    fake_module = SimpleNamespace(Client=_FakeClient, types=fake_types)

    import sys

    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_module))
    monkeypatch.setitem(sys.modules, "google.genai", fake_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)

    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("AQUALENS_FAKE_GEMINI", "0")
    monkeypatch.setenv("GOOGLE_API_KEY", "primary-test-key")
    get_settings.cache_clear()

    yield queues
    get_settings.cache_clear()


# ----------------------------------------------------------------------
# Happy path
# ----------------------------------------------------------------------


def _valid_brief_json() -> str:
    return (
        '{"tasks":['
        '{"priority":"p0",'
        '"location":{"lat":45.985,"lng":9.25,"description":"North shore inlet"},'
        '"sample_type":"grab water sample for chlorophyll-a",'
        '"equipment":["dark sample bottle","0.45 um filter","ice pack"],'
        '"photo_prompts":["wide shot of north shore","close-up of any algal mats"],'
        '"estimated_minutes":60}'
        '],"turnaround_hours":24,"escalate_to":"local water authority"}'
    )


def test_field_liaison_passes_through_valid_brief(fake_gemini) -> None:
    fake_gemini.append(_response(_valid_brief_json()))

    rec = TraceRecorder()
    with rec.record_agent("field_liaison") as builder:
        brief = run_field_liaison(
            builder=builder,
            water_body={"name": "Lake Como", "id": "wb-1"},
            centroid_lng_lat=(9.25, 45.985),
            risk_level="high",
            urgency="immediate",
            narrative={
                "recommendation": "Send a sampling team within 24 hours.",
                "reasoning": "NDCI 0.32 and NDTI 0.18 — escalation justified.",
                "limitations": "Cloud cover; no in-situ sampling.",
            },
            evidence_focus=[
                EvidenceFocus(target="north shore inlet", reason="NDCI peak"),
            ],
        )

    assert isinstance(brief, FieldBrief)
    assert len(brief.tasks) == 1
    assert brief.tasks[0].priority == "p0"
    assert brief.tasks[0].location.description.startswith("North shore")
    assert brief.turnaround_hours == 24
    assert brief.escalate_to == "local water authority"


# ----------------------------------------------------------------------
# Fallback path
# ----------------------------------------------------------------------


def test_field_liaison_falls_back_on_gemini_error(fake_gemini) -> None:
    fake_gemini.raise_next.append(RuntimeError("Gemini exploded"))

    rec = TraceRecorder()
    with rec.record_agent("field_liaison") as builder:
        brief = run_field_liaison(
            builder=builder,
            water_body={"name": "Lake Test"},
            centroid_lng_lat=(9.25, 45.985),
            risk_level="high",
            urgency="immediate",
            narrative={
                "recommendation": "Send a sampling team.",
                "reasoning": "NDCI and NDTI both elevated.",
                "limitations": "Cloud cover.",
            },
            evidence_focus=[{"target": "north shore", "reason": "NDCI spike"}],
        )

    # Fallback runs the same code path regardless of which Gemini failure occurred.
    assert isinstance(brief, FieldBrief)
    assert brief.turnaround_hours == 24  # urgency=immediate -> 24h
    assert len(brief.tasks) == 1
    assert brief.tasks[0].priority == "p0"
    assert brief.escalate_to == "local water authority"
    # Fallback uses AOI centroid for location.
    assert brief.tasks[0].location.lat == 45.985
    assert brief.tasks[0].location.lng == 9.25


def test_field_liaison_fallback_default_low_risk_routine(fake_gemini) -> None:
    fake_gemini.raise_next.append(RuntimeError("Gemini exploded"))

    rec = TraceRecorder()
    with rec.record_agent("field_liaison") as builder:
        brief = run_field_liaison(
            builder=builder,
            water_body={"name": "Lake Test"},
            centroid_lng_lat=(9.25, 45.985),
            risk_level="low",
            urgency="routine",
            narrative={"recommendation": "Maintain cadence.", "reasoning": "x", "limitations": "y"},
            evidence_focus=[],
        )

    assert brief.tasks[0].priority == "p2"
    assert brief.tasks[0].sample_type == "Walk-around visual check"
    assert brief.turnaround_hours == 168
    assert brief.escalate_to is None


def test_evidence_focus_accepts_both_models_and_dicts(fake_gemini) -> None:
    fake_gemini.append(_response(_valid_brief_json()))

    rec = TraceRecorder()
    with rec.record_agent("field_liaison") as builder:
        brief = run_field_liaison(
            builder=builder,
            water_body={"name": "Lake Test"},
            centroid_lng_lat=None,
            risk_level="medium",
            urgency="elevated",
            narrative={"recommendation": "x", "reasoning": "y", "limitations": "z"},
            evidence_focus=[
                EvidenceFocus(target="north shore", reason="NDCI peak"),
                {"target": "south shore", "reason": "NDTI elevated"},
            ],
        )
    assert isinstance(brief, FieldBrief)
