"""Stage 3 deliverable: trace recorder + Gemini tool-loop runtime.

Tests:
- TraceRecorder captures coordinator plan, agent run nesting, tool
  calls with arguments/results, errors, and aggregate totals.
- run_tool_loop dispatches function calls to the right Python handler,
  feeds results back to Gemini, terminates on a non-tool response, and
  respects the max_turns cap.

The Gemini SDK is faked at the seam (``client.models.generate_content``)
so no network is required.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from app.services.agent import gemini_runtime
from app.services.agent.gemini_runtime import ToolSpec, run_tool_loop
from app.services.agent.trace import TraceRecorder

# ----------------------------------------------------------------------
# TraceRecorder
# ----------------------------------------------------------------------


def test_trace_recorder_records_coordinator_plan_and_agent_runs() -> None:
    rec = TraceRecorder(gemini_model="gemini-2.5-flash")
    rec.set_coordinator_plan(
        {
            "plan": [{"agent": "scout", "reason": "fresh AOI", "budget": {"max_tool_calls": 6}}],
            "rationale": "default",
            "estimated_complexity": "low",
        }
    )

    with rec.record_agent("scout") as scout:
        with scout.record_tool("list_recent_scenes", {"max_cloud_cover": 30}) as tc:
            tc.result = {"candidates": [{"scene_id": "S2A_X"}]}
        scout.add_tokens(tokens_in=500, tokens_out=80)
        scout.set_outputs({"selected_scene": "S2A_X"})

    compiled = rec.compile()
    assert compiled["coordinator_plan"]["estimated_complexity"] == "low"
    assert compiled["total_tokens_in"] == 500
    assert compiled["total_tokens_out"] == 80
    assert compiled["gemini_model"] == "gemini-2.5-flash"
    assert compiled["total_latency_ms"] >= 0
    runs = compiled["agent_runs"]
    assert len(runs) == 1
    assert runs[0]["agent"] == "scout"
    assert runs[0]["outputs"]["selected_scene"] == "S2A_X"
    assert runs[0]["error"] is None
    assert runs[0]["tool_calls"][0]["name"] == "list_recent_scenes"
    assert runs[0]["tool_calls"][0]["result"]["candidates"][0]["scene_id"] == "S2A_X"


def test_trace_recorder_captures_tool_errors() -> None:
    rec = TraceRecorder()
    with rec.record_agent("scout") as scout:
        with pytest.raises(RuntimeError), scout.record_tool("broken") as tc:
            raise RuntimeError("boom")
        assert tc.error is not None
        assert "RuntimeError" in tc.error
        scout.set_outputs({"selected_scene": None})

    compiled = rec.compile()
    assert compiled["agent_runs"][0]["tool_calls"][0]["error"].startswith("RuntimeError")


def test_trace_recorder_records_agent_failure() -> None:
    rec = TraceRecorder()
    with pytest.raises(ValueError), rec.record_agent("scout") as scout:
        scout.set_outputs({"selected_scene": None})
        raise ValueError("scout died")
    runs = rec.compile()["agent_runs"]
    assert runs[0]["error"] == "ValueError: scout died"


# ----------------------------------------------------------------------
# Gemini tool-loop — fake client
# ----------------------------------------------------------------------


class _FakePart:
    def __init__(self, *, text: str | None = None, function_call: Any | None = None) -> None:
        self.text = text
        self.function_call = function_call


class _FakeContent:
    def __init__(self, role: str, parts: list[Any]) -> None:
        self.role = role
        self.parts = parts


class _FakeFinishReason:
    def __init__(self, value: str) -> None:
        self.value = value


class _FakeCandidate:
    def __init__(self, content: _FakeContent, finish_reason: str = "STOP") -> None:
        self.content = content
        self.finish_reason = _FakeFinishReason(finish_reason)
        self.grounding_metadata = None


class _FakeResponse:
    def __init__(
        self,
        candidates: list[_FakeCandidate],
        text: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> None:
        self.candidates = candidates
        self.text = text
        self.usage_metadata = SimpleNamespace(
            prompt_token_count=tokens_in,
            candidates_token_count=tokens_out,
        )


def _function_call(name: str, args: dict[str, Any]) -> Any:
    return SimpleNamespace(name=name, args=args)


def _final_response(text: str, tokens_in: int = 50, tokens_out: int = 20) -> _FakeResponse:
    return _FakeResponse(
        candidates=[_FakeCandidate(_FakeContent("model", [_FakePart(text=text)]))],
        text=text,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )


def _tool_call_response(name: str, args: dict[str, Any]) -> _FakeResponse:
    part = _FakePart(function_call=_function_call(name, args))
    return _FakeResponse(
        candidates=[_FakeCandidate(_FakeContent("model", [part]))],
        text="",
        tokens_in=40,
        tokens_out=15,
    )


@pytest.fixture()
def fake_gemini(monkeypatch) -> Iterator[list[Any]]:
    """Patch the runtime's SDK seam with a queue of canned responses."""
    queue: list[Any] = []
    calls: list[dict[str, Any]] = []

    class _FakeModels:
        def generate_content(self, *, model, contents, config):
            calls.append({"model": model, "contents": contents, "config": config})
            if not queue:
                raise AssertionError("queue exhausted — unexpected extra Gemini call")
            return queue.pop(0)

    class _FakeClient:
        def __init__(self, api_key: str) -> None:
            self.models = _FakeModels()

    # google.genai.types is consumed by the runtime; provide just the
    # shapes it actually instantiates. Set it as an attribute on the
    # genai module so ``from google.genai import types`` resolves it.
    fake_types = SimpleNamespace(
        FunctionDeclaration=lambda **kw: SimpleNamespace(**kw),
        Tool=lambda **kw: SimpleNamespace(**kw),
        GenerateContentConfig=lambda **kw: SimpleNamespace(**kw),
        ThinkingConfig=lambda **kw: SimpleNamespace(**kw),
        Content=lambda role, parts: SimpleNamespace(role=role, parts=parts),
        Part=SimpleNamespace(
            from_text=lambda text: SimpleNamespace(text=text, function_call=None),
            from_function_response=lambda name, response: SimpleNamespace(
                function_response=SimpleNamespace(name=name, response=response)
            ),
        ),
    )
    fake_module = SimpleNamespace(Client=_FakeClient, types=fake_types)

    import sys

    fake_root = SimpleNamespace(genai=fake_module)
    monkeypatch.setitem(sys.modules, "google", fake_root)
    monkeypatch.setitem(sys.modules, "google.genai", fake_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)

    # Ensure the runtime's settings allow the loop to run.
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("AQUALENS_FAKE_GEMINI", "0")
    monkeypatch.setenv("GOOGLE_API_KEY", "primary-test-key")
    get_settings.cache_clear()

    yield queue
    # Reset env so other tests see the conftest defaults again.
    get_settings.cache_clear()


def _enqueue(fake: list[Any], *responses: Any) -> None:
    fake.extend(responses)


def test_tool_loop_terminates_when_model_emits_final_text(fake_gemini) -> None:
    _enqueue(fake_gemini, _final_response("done"))

    def handler(**kw: Any) -> dict[str, Any]:
        return {"unused": True}

    spec = ToolSpec(name="noop", description="", parameters={"type": "object"}, handler=handler)

    rec = TraceRecorder()
    with rec.record_agent("scout") as builder:
        result = run_tool_loop(
            builder=builder,
            system_instruction="be helpful",
            user_message="hi",
            tools=[spec],
            max_turns=3,
        )

    assert result.text == "done"
    assert result.turns == 1
    compiled = rec.compile()
    assert compiled["agent_runs"][0]["tool_calls"] == []
    assert compiled["total_tokens_in"] == 50


def test_tool_loop_dispatches_function_call_then_finalises(fake_gemini) -> None:
    _enqueue(
        fake_gemini,
        _tool_call_response("list_recent_scenes", {"max_cloud_cover": 30}),
        _final_response("picked it"),
    )

    captured_args: dict[str, Any] = {}

    def handler(**kwargs: Any) -> dict[str, Any]:
        captured_args.update(kwargs)
        return {"candidates": [{"scene_id": "S2A_FAKE"}]}

    spec = ToolSpec(
        name="list_recent_scenes",
        description="search scenes",
        parameters={"type": "object", "properties": {"max_cloud_cover": {"type": "number"}}},
        handler=handler,
    )

    rec = TraceRecorder()
    with rec.record_agent("scout") as builder:
        result = run_tool_loop(
            builder=builder,
            system_instruction="be helpful",
            user_message="find a scene",
            tools=[spec],
            max_turns=4,
        )

    assert captured_args == {"max_cloud_cover": 30}
    assert result.turns == 2
    assert result.text == "picked it"
    runs = rec.compile()["agent_runs"]
    assert runs[0]["tool_calls"][0]["name"] == "list_recent_scenes"
    assert runs[0]["tool_calls"][0]["result"]["candidates"][0]["scene_id"] == "S2A_FAKE"


def test_tool_loop_records_unknown_tool_as_error(fake_gemini) -> None:
    _enqueue(
        fake_gemini,
        _tool_call_response("not_a_real_tool", {}),
        _final_response("abandoned"),
    )

    rec = TraceRecorder()
    with rec.record_agent("scout") as builder:
        run_tool_loop(
            builder=builder,
            system_instruction="x",
            user_message="y",
            tools=[],
            max_turns=3,
        )

    tool_record = rec.compile()["agent_runs"][0]["tool_calls"][0]
    assert tool_record["name"] == "not_a_real_tool"
    assert tool_record["error"] is not None and "unknown tool" in tool_record["error"]


def test_tool_loop_respects_max_turns(fake_gemini) -> None:
    # Three function-call responses in a row — the loop should stop
    # after max_turns=2 even though the model never sends a final text.
    _enqueue(
        fake_gemini,
        _tool_call_response("noop", {}),
        _tool_call_response("noop", {}),
    )

    spec = ToolSpec(
        name="noop", description="", parameters={"type": "object"}, handler=lambda **_: {"ok": True}
    )

    rec = TraceRecorder()
    with rec.record_agent("scout") as builder:
        result = run_tool_loop(
            builder=builder,
            system_instruction="x",
            user_message="y",
            tools=[spec],
            max_turns=2,
        )

    assert result.turns == 2
    assert result.finish_reason in {"max_turns", "STOP"}


def test_to_json_helper_is_stable() -> None:
    payload = {"b": 1, "a": [1, 2, 3]}
    assert "\n" in gemini_runtime.to_json(payload)
    assert '"a"' in gemini_runtime.to_json(payload)


def test_gemini_schema_inlines_nested_pydantic_models() -> None:
    """Regression: SDK's Schema validator rejects $ref / $defs.

    Before the fix the Analyst's nested ``EvidenceFocus`` field produced
    a JSON Schema with ``$ref`` indirection that caused Gemini to bail
    with ``Extra inputs are not permitted``. ``_gemini_schema`` flattens
    everything inline so the SDK sees a self-contained object schema.
    """
    from app.schemas.field_brief import FieldBrief
    from app.services.agent.analyst import AnalystDraft
    from app.services.agent.gemini_runtime import _gemini_schema
    from app.services.agent.historian import HistorianBriefing

    for model in (AnalystDraft, HistorianBriefing, FieldBrief):
        schema_text = gemini_runtime.to_json(_gemini_schema(model))
        assert "$ref" not in schema_text, f"{model.__name__} schema still uses $ref"
        assert "$defs" not in schema_text, f"{model.__name__} schema still ships $defs"
        assert (
            "additionalProperties" not in schema_text
        ), f"{model.__name__} schema still carries SDK-incompatible additionalProperties"


def test_maybe_thinking_config_returns_none_when_sdk_missing_it() -> None:
    """Older google-genai builds don't ship ThinkingConfig."""
    from app.services.agent.gemini_runtime import _maybe_thinking_config

    class _FakeTypes:  # no ThinkingConfig attribute
        pass

    assert _maybe_thinking_config(_FakeTypes(), 2048) is None
    # And a budget of None is always a no-op.
    assert (
        _maybe_thinking_config(
            type("X", (), {"ThinkingConfig": lambda **_: object()})(),
            None,
        )
        is None
    )


def test_effective_output_tokens_adds_thinking_budget() -> None:
    """On Gemini 2.5 Flash, ``max_output_tokens`` is the combined ceiling
    for thinking + visible tokens, so the runtime must add the thinking
    budget on top of the caller's visible-response budget — otherwise
    the model can spend the whole allowance thinking and return empty
    JSON (which surfaced as Coordinator ``Unterminated string`` errors)."""
    from app.services.agent.gemini_runtime import _effective_output_tokens

    # No thinking: just the caller's budget (with a small floor).
    assert _effective_output_tokens(2048, None) == 2048
    assert _effective_output_tokens(0, None) == 256  # floor

    # With thinking: thinking budget + visible budget + safety margin.
    assert _effective_output_tokens(2048, 2048) == 2048 + 2048 + 256
    assert _effective_output_tokens(4096, 1024) == 4096 + 1024 + 256


def test_parse_structured_response_prefers_response_parsed() -> None:
    from app.services.agent.gemini_runtime import _parse_structured_response

    class _Schema(BaseModel):
        value: int

    response = SimpleNamespace(parsed={"value": 7}, text="not-json", candidates=[])
    parsed = _parse_structured_response(response=response, response_schema=_Schema)
    assert isinstance(parsed, _Schema)
    assert parsed.value == 7


def test_parse_structured_response_accepts_fenced_json_text() -> None:
    from app.services.agent.gemini_runtime import _parse_structured_response

    class _Schema(BaseModel):
        ok: bool

    response = SimpleNamespace(parsed=None, text='```json\n{"ok": true}\n```', candidates=[])
    parsed = _parse_structured_response(response=response, response_schema=_Schema)
    assert parsed.ok is True


def test_parse_structured_response_falls_back_to_candidate_parts_text() -> None:
    from app.services.agent.gemini_runtime import _parse_structured_response

    class _Schema(BaseModel):
        score: float

    part = SimpleNamespace(text='{"score": 0.46}')
    content = SimpleNamespace(parts=[part])
    candidate = SimpleNamespace(content=content)
    response = SimpleNamespace(parsed=None, text="", candidates=[candidate])
    parsed = _parse_structured_response(response=response, response_schema=_Schema)
    assert parsed.score == pytest.approx(0.46)


def test_key_failover_retries_second_pass_after_quota() -> None:
    from app.services.agent.gemini_runtime import _call_with_key_failover
    from app.services.reasoning import QuotaExceededError

    calls: list[tuple[int, str]] = []

    def _call(key_index: int, api_key: str) -> str:
        calls.append((key_index, api_key))
        # First pass (two keys) hits quota; second pass succeeds on
        # primary after cooldown retry.
        if len(calls) <= 2:
            raise QuotaExceededError("429 RESOURCE_EXHAUSTED")
        return "ok"

    result = _call_with_key_failover(
        api_keys=["primary", "fallback"],
        retry_passes=2,
        cooldown_seconds=0,
        call=_call,
    )
    assert result == "ok"
    assert calls == [(0, "primary"), (1, "fallback"), (0, "primary")]


def test_key_failover_skips_keys_in_cooldown(monkeypatch) -> None:
    from app.services.agent.gemini_runtime import (
        _KEY_COOLDOWN_UNTIL,
        _call_with_key_failover,
    )

    calls: list[tuple[int, str]] = []
    monkeypatch.setattr(gemini_runtime.time, "monotonic", lambda: 100.0)
    _KEY_COOLDOWN_UNTIL.clear()
    _KEY_COOLDOWN_UNTIL["primary"] = 130.0

    def _call(key_index: int, api_key: str) -> str:
        calls.append((key_index, api_key))
        return "served-by-fallback"

    try:
        result = _call_with_key_failover(
            api_keys=["primary", "fallback"],
            retry_passes=1,
            cooldown_seconds=0,
            call=_call,
        )
    finally:
        _KEY_COOLDOWN_UNTIL.clear()

    assert result == "served-by-fallback"
    assert calls == [(1, "fallback")]
