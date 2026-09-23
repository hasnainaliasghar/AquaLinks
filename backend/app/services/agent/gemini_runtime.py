"""Shared LLM runtime for the multi-agent layer (Groq backend).

Provides three things every agent needs:

1. :class:`ToolSpec` — bundles a function declaration (handed to
   the LLM) with the Python handler the runtime invokes when the model
   issues a corresponding tool call.
2. :func:`run_tool_loop` — drives the multi-turn conversation until
   either the model emits a final text/structured response or the
   ``max_turns`` cap is reached. Records every step into the active
   :class:`~app.services.agent.trace.AgentTraceBuilder`.
3. :func:`call_structured` — single-shot helper for agents that need
   a Pydantic ``response_schema`` but no tools (Coordinator, Reporter).

Both call paths automatically roll over from the primary Groq API
key to the configured fallback on quota / 429 errors.

Notes on Groq vs. Gemini differences handled here:
- ``thinking_budget`` is silently ignored (Groq has no thinking mode).
- ``gemini_native_tools`` (google_search, url_context, code_execution)
  are silently ignored with a log warning (Groq has no native tools).
- Vision calls use a separate vision-capable model configured via
  ``GROQ_VISION_MODEL``.
- Embeddings are not provided by Groq; the embeddings module falls
  back to the deterministic pseudo-embedding path automatically.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.agent.trace import AgentTraceBuilder
from app.services.reasoning import QuotaExceededError, _looks_like_quota_error

LOGGER = get_logger(__name__)

DEFAULT_MAX_TURNS = 6
DEFAULT_STRUCTURED_OUTPUT_TOKENS = 2048
DEFAULT_TOOL_LOOP_OUTPUT_TOKENS = 4096

# Kept for import compatibility with historian.py / scout.py.
# On Groq these names are accepted but silently no-ops.
NATIVE_TOOL_GOOGLE_SEARCH = "google_search"
NATIVE_TOOL_URL_CONTEXT = "url_context"
NATIVE_TOOL_CODE_EXECUTION = "code_execution"

_KEY_COOLDOWN_UNTIL: dict[str, float] = {}
_T = TypeVar("_T")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def to_json(obj: Any) -> str:
    """Serialise *obj* to a compact JSON string."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# ToolSpec / result types
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ToolSpec:
    """One tool the agent can call."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., dict[str, Any]]


@dataclass(slots=True)
class ToolLoopResult:
    """Final state of a tool-loop run."""

    text: str
    parsed: Any | None = None
    turns: int = 0
    finish_reason: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def run_tool_loop(
    *,
    builder: AgentTraceBuilder,
    system_instruction: str,
    user_message: str,
    tools: list[ToolSpec],
    response_schema: type[BaseModel] | None = None,
    max_turns: int = DEFAULT_MAX_TURNS,
    temperature: float = 0.3,
    thinking_budget: int | None = None,  # ignored on Groq
    gemini_native_tools: list[str] | None = None,  # ignored on Groq
    max_output_tokens: int | None = None,
) -> ToolLoopResult:
    """Drive a multi-turn Groq conversation that may call tools."""
    settings = get_settings()
    if settings.aqualens_fake_gemini:
        raise RuntimeError(
            "run_tool_loop should not be reached when AQUALENS_FAKE_GEMINI=1; "
            "the orchestrator must short-circuit to the deterministic narrator."
        )
    if thinking_budget:
        LOGGER.debug("thinking_budget ignored on Groq backend")
    if gemini_native_tools:
        LOGGER.debug(
            "gemini_native_tools %s are not supported on Groq and will be skipped",
            gemini_native_tools,
        )

    api_keys = settings.gemini_api_keys
    if not api_keys:
        raise RuntimeError("no Groq API keys configured — set GROQ_API_KEY in .env")

    return _call_with_key_failover(
        api_keys=api_keys,
        retry_passes=settings.gemini_quota_retry_passes,
        cooldown_seconds=settings.gemini_quota_cooldown_seconds,
        call=lambda _idx, api_key: _drive_loop(
            builder=builder,
            api_key=api_key,
            model=settings.groq_model,
            system_instruction=system_instruction,
            user_message=user_message,
            tools=tools,
            response_schema=response_schema,
            max_turns=max_turns,
            temperature=temperature,
            max_output_tokens=max_output_tokens or DEFAULT_TOOL_LOOP_OUTPUT_TOKENS,
        ),
    )


def call_structured(
    *,
    builder: AgentTraceBuilder,
    system_instruction: str,
    user_message: str,
    response_schema: type[BaseModel],
    temperature: float = 0.2,
    thinking_budget: int | None = None,  # ignored on Groq
    max_output_tokens: int | None = None,
) -> BaseModel:
    """Single-shot Groq call with a Pydantic schema. No tools."""
    settings = get_settings()
    api_keys = settings.gemini_api_keys
    if not api_keys:
        raise RuntimeError("no Groq API keys configured — set GROQ_API_KEY in .env")

    if thinking_budget:
        LOGGER.debug("thinking_budget ignored on Groq backend")

    return _call_with_key_failover(
        api_keys=api_keys,
        retry_passes=settings.gemini_quota_retry_passes,
        cooldown_seconds=settings.gemini_quota_cooldown_seconds,
        call=lambda _idx, api_key: _call_structured_once(
            builder=builder,
            api_key=api_key,
            model=settings.groq_model,
            system_instruction=system_instruction,
            user_message=user_message,
            response_schema=response_schema,
            temperature=temperature,
            max_output_tokens=max_output_tokens or DEFAULT_STRUCTURED_OUTPUT_TOKENS,
        ),
    )


# ---------------------------------------------------------------------------
# Key failover
# ---------------------------------------------------------------------------


def _call_with_key_failover(
    *,
    api_keys: list[str],
    retry_passes: int,
    cooldown_seconds: float,
    call: Callable[[int, str], _T],
) -> _T:
    total_passes = max(int(retry_passes), 1)
    cooldown = max(float(cooldown_seconds), 0.0)
    last_error: Exception | None = None

    for pass_index in range(total_passes):
        attempted_this_pass = 0
        ready_in_seconds: list[float] = []

        for key_index, api_key in enumerate(api_keys):
            wait_s = _seconds_until_key_ready(api_key)
            if wait_s > 0:
                ready_in_seconds.append(wait_s)
                continue

            attempted_this_pass += 1
            try:
                result = call(key_index, api_key)
                _clear_key_cooldown(api_key)
                return result
            except QuotaExceededError as exc:
                last_error = exc
                _mark_key_cooldown(api_key, cooldown)
                label = _key_label(key_index)
                LOGGER.warning("Groq quota on %s key — rolling over (%s)", label, exc)
                continue

        remaining_passes = total_passes - (pass_index + 1)
        if remaining_passes <= 0:
            break

        wait_s = cooldown
        if attempted_this_pass == 0 and ready_in_seconds:
            wait_s = max(0.0, min(ready_in_seconds))
        if wait_s > 0:
            LOGGER.info(
                "Groq keys exhausted for pass %d/%d; retrying in %.1fs",
                pass_index + 1,
                total_passes,
                wait_s,
            )
            time.sleep(wait_s)

    raise RuntimeError(f"all {len(api_keys)} Groq keys hit quota: {last_error}")


def _key_label(index: int) -> str:
    return "primary" if index == 0 else f"fallback-{index}"


def _seconds_until_key_ready(api_key: str) -> float:
    ready_at = _KEY_COOLDOWN_UNTIL.get(api_key)
    if ready_at is None:
        return 0.0
    return max(0.0, ready_at - time.monotonic())


def _mark_key_cooldown(api_key: str, cooldown_seconds: float) -> None:
    if cooldown_seconds <= 0:
        return
    _KEY_COOLDOWN_UNTIL[api_key] = time.monotonic() + cooldown_seconds


def _clear_key_cooldown(api_key: str) -> None:
    _KEY_COOLDOWN_UNTIL.pop(api_key, None)


# ---------------------------------------------------------------------------
# Internals — Groq tool loop
# ---------------------------------------------------------------------------


def _build_groq_tools(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    """Convert ToolSpec list → Groq/OpenAI tool format."""
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            },
        }
        for spec in tools
    ]


def _drive_loop(
    *,
    builder: AgentTraceBuilder,
    api_key: str,
    model: str,
    system_instruction: str,
    user_message: str,
    tools: list[ToolSpec],
    response_schema: type[BaseModel] | None,
    max_turns: int,
    temperature: float,
    max_output_tokens: int,
) -> ToolLoopResult:
    from groq import Groq
    from groq import RateLimitError

    client = Groq(api_key=api_key)
    handler_index = {spec.name: spec for spec in tools}
    groq_tools = _build_groq_tools(tools) if tools else None

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_message},
    ]

    # When a response schema is requested, ask for JSON mode and embed the
    # schema description in the system prompt so the model knows the shape.
    if response_schema is not None:
        schema_hint = (
            f"\n\nRespond with a JSON object that matches this schema:\n"
            f"{json.dumps(response_schema.model_json_schema(), indent=2)}\n"
            "Return ONLY the JSON object, no markdown fences, no prose."
        )
        messages[0]["content"] += schema_hint

    last_response: Any = None
    finish_reason: str | None = None

    for turn in range(1, max_turns + 1):
        call_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }
        if groq_tools:
            call_kwargs["tools"] = groq_tools
            call_kwargs["tool_choice"] = "auto"
        if response_schema is not None and not groq_tools:
            call_kwargs["response_format"] = {"type": "json_object"}

        try:
            response = client.chat.completions.create(**call_kwargs)
        except RateLimitError as exc:
            raise QuotaExceededError(str(exc)) from exc
        except Exception as exc:
            if _looks_like_quota_error(exc):
                raise QuotaExceededError(str(exc)) from exc
            raise

        _accumulate_token_usage(builder, response)
        last_response = response

        choice = response.choices[0] if response.choices else None
        if choice is None:
            return ToolLoopResult(text="", turns=turn, finish_reason="empty")

        finish_reason = choice.finish_reason
        message = choice.message

        # Check for tool calls.
        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            # Terminal turn — model emitted a final answer.
            text = message.content or ""
            parsed = _try_parse(text, response_schema)
            return ToolLoopResult(
                text=text,
                parsed=parsed,
                turns=turn,
                finish_reason=finish_reason,
            )

        # Echo the model's tool-call message into history.
        messages.append({"role": "assistant", "content": message.content, "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in tool_calls
        ]})

        for tc in tool_calls:
            fn_name = tc.function.name
            try:
                arguments = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}

            spec = handler_index.get(fn_name)
            with builder.record_tool(fn_name, arguments) as record:
                if spec is None:
                    record.error = f"unknown tool {fn_name!r}"
                    payload: dict[str, Any] = {"error": record.error}
                else:
                    try:
                        payload = spec.handler(**arguments)
                    except Exception as exc:
                        record.error = f"{type(exc).__name__}: {exc}"
                        payload = {"error": record.error}
                record.result = payload

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(payload, ensure_ascii=False),
            })

    # Loop budget exhausted.
    final_text = getattr(last_response, "choices", [{}])[0]
    if hasattr(final_text, "message"):
        final_text = final_text.message.content or ""
    else:
        final_text = ""
    return ToolLoopResult(
        text=final_text,
        parsed=_try_parse(final_text, response_schema),
        turns=max_turns,
        finish_reason=finish_reason or "max_turns",
    )


def _call_structured_once(
    *,
    builder: AgentTraceBuilder,
    api_key: str,
    model: str,
    system_instruction: str,
    user_message: str,
    response_schema: type[BaseModel],
    temperature: float,
    max_output_tokens: int,
) -> BaseModel:
    from groq import Groq
    from groq import RateLimitError

    client = Groq(api_key=api_key)

    schema_hint = (
        f"\n\nRespond with a JSON object that matches this schema:\n"
        f"{json.dumps(response_schema.model_json_schema(), indent=2)}\n"
        "Return ONLY the JSON object, no markdown fences, no prose."
    )

    messages = [
        {"role": "system", "content": system_instruction + schema_hint},
        {"role": "user", "content": user_message},
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_output_tokens,
            response_format={"type": "json_object"},
        )
    except RateLimitError as exc:
        raise QuotaExceededError(str(exc)) from exc
    except Exception as exc:
        if _looks_like_quota_error(exc):
            raise QuotaExceededError(str(exc)) from exc
        raise

    _accumulate_token_usage(builder, response)

    text = (response.choices[0].message.content or "").strip() if response.choices else ""
    if not text:
        raise RuntimeError("Groq returned an empty structured response")

    return _parse_structured_response(text=text, response_schema=response_schema)


# ---------------------------------------------------------------------------
# Response parsing helpers
# ---------------------------------------------------------------------------


def _try_parse(text: str, schema: type[BaseModel] | None) -> Any | None:
    if schema is None or not text:
        return None
    for candidate in _json_candidates(text):
        try:
            return schema.model_validate_json(candidate)
        except Exception:
            continue
    return None


def _parse_structured_response(*, text: str, response_schema: type[BaseModel]) -> BaseModel:
    """Parse a Groq JSON response robustly."""
    candidates = _json_candidates(text)
    last_error: Exception | None = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return response_schema.model_validate_json(candidate)
        except Exception as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise ValueError("Groq returned an empty structured response")


def _json_candidates(text: str) -> list[str]:
    if not text:
        return []
    variants: list[str] = [text.strip()]
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2:
            body = "\n".join(lines[1:])
            if body.endswith("```"):
                body = body[:-3]
            variants.append(body.strip())
    first_obj, last_obj = text.find("{"), text.rfind("}")
    if first_obj != -1 and last_obj > first_obj:
        variants.append(text[first_obj : last_obj + 1].strip())
    seen: set[str] = set()
    deduped: list[str] = []
    for item in variants:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _accumulate_token_usage(builder: AgentTraceBuilder, response: Any) -> None:
    """Best-effort token tally from Groq's usage object."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    in_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    out_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    builder.add_tokens(tokens_in=in_tokens, tokens_out=out_tokens)
