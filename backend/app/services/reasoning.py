"""LLM-powered narrative for risk assessments (Groq backend).

The deterministic risk score from :mod:`app.services.risk_model` is the
source of truth for the numeric level and urgency. This module produces
the human-readable text that wraps the numbers: a recommendation,
reasoning trace, and a limitations note.

Why a separate module:
- Keeps LLM I/O out of the deterministic scoring path so the score is
  always reproducible and testable without API access.
- Forces a structured-output contract (``ReasoningBundle``) the rest of
  the application can rely on.
- Provides a single seam where tests can mock or set
  ``AQUALENS_FAKE_GEMINI=1`` for offline CI runs.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from importlib.resources import files
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.evidence import FieldEvidence
from app.models.risk_assessment import RiskLevel
from app.models.water_body import WaterBody
from app.services.indices import IndexAggregate
from app.services.risk_model import RiskScore

LOGGER = get_logger(__name__)


class ConfigurationError(RuntimeError):
    """Raised when reasoning is requested but the LLM is not configured."""


class ReasoningBundle(BaseModel):
    """Validated LLM output.

    Length constraints are intentionally absent: when this model is handed to
    the google-genai SDK as a ``response_schema`` the SDK emits the bundled
    ``minLength`` / ``maxLength`` annotations as ints, while its own internal
    ``Schema`` class types those fields as strings — that's what produced the
    "6 validation errors for Schema" failure. The prompt already pins the
    response shape; we trust the model to keep things short.
    """

    recommendation: str
    reasoning: str
    limitations: str


# The full prompt is split into two structured-JSON channels:
#
#   • system_instruction.json  →  Gemini's system_instruction channel.
#     Persona, input schema, hard rules, AOI handling, and the output
#     contract — all expressed as a single JSON document so the rules
#     are versionable, diff-friendly, and unambiguous to both humans
#     and the model.
#
#   • the user contents         →  a pure JSON facts payload built
#     from _build_facts.
#
# This is a stronger separation than embedding facts inside a prose
# template: the model sees rules-as-data and facts-as-data, never one
# bleeding into the other.
_SYSTEM_INSTRUCTION_JSON: dict[str, Any] = json.loads(
    files("app.services.prompts").joinpath("system_instruction.json").read_text(encoding="utf-8")
)

# Appended to the system instruction on a retry after a parse / schema
# failure. We don't change the rules — we just bolt on a "STRICT MODE"
# directive so the next attempt doesn't drift into prose or code fences.
_RETRY_DIRECTIVE_JSON: dict[str, Any] = json.loads(
    files("app.services.prompts").joinpath("retry_directive.json").read_text(encoding="utf-8")
)


def _serialize_system_instruction(extra: dict[str, Any] | None = None) -> str:
    """Render the structured system instruction as a JSON string.

    Gemini's ``system_instruction`` channel is plain text from the
    SDK's perspective. We hand it the canonical JSON document so the
    LLM sees the rules as data with explicit field names rather than
    free-form prose. On a retry we splice in a ``retry_directive``
    field so the strict-mode directive lives in the same document.
    """
    payload = dict(_SYSTEM_INSTRUCTION_JSON)
    if extra:
        payload["retry_directive"] = extra
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _build_facts(
    score: RiskScore,
    indices: Iterable[IndexAggregate],
    evidence: Iterable[FieldEvidence],
    water_body: WaterBody,
    *,
    water_fraction: float | None = None,
    aoi_type: str | None = None,
) -> dict[str, Any]:
    return {
        "water_body": {
            "name": water_body.name,
            "centroid": water_body.centroid,
            "area_km2": water_body.area_km2,
        },
        "aoi": {
            "type": aoi_type,
            "water_fraction": (round(water_fraction, 3) if water_fraction is not None else None),
        },
        "risk": {
            "score": round(score.score, 3),
            "level": score.level.value,
            "urgency": score.urgency.value,
            "contributors": {k: round(v, 4) for k, v in score.contributors.items()},
        },
        "indices": [
            {
                "name": idx.name.value,
                "value": round(idx.value, 4),
                "interpretation": idx.interpretation,
                "bands": idx.bands,
                "sample_count": idx.sample_count,
            }
            for idx in indices
        ],
        "evidence": [
            {
                "water_color": ev.water_color.value,
                "odor": ev.odor.value,
                "algae_present": ev.algae_present,
                "dead_fish_count": ev.dead_fish_count,
                "rainfall_mm": ev.rainfall_mm,
                "complaints_count": ev.complaints_count,
                "notes": ev.notes,
                "reported_at": ev.created_at.isoformat() if ev.created_at else None,
            }
            for ev in evidence
        ],
    }


def _render_user_contents(facts: dict[str, Any]) -> str:
    """Serialize the facts dict as a JSON string for Gemini's ``contents``.

    The model receives a pure JSON payload with no surrounding prose, so
    there is no chance of confusing facts with instructions. The system
    instruction (loaded once at import) tells the model how to read it.
    """
    return json.dumps(facts, indent=2, ensure_ascii=False)


def _fake_bundle(
    score: RiskScore,
    indices: Iterable[IndexAggregate],
    *,
    aoi_type: str | None = None,
) -> ReasoningBundle:
    """Deterministic narrative used by tests / CI when GROQ_API_KEY is unavailable."""
    idx_list = list(indices)
    ndci = next((i for i in idx_list if i.name.value == "NDCI"), None)
    ndti = next((i for i in idx_list if i.name.value == "NDTI"), None)
    level = score.level.value
    urgency = score.urgency.value
    recommendation_map: dict[RiskLevel, str] = {
        RiskLevel.LOW: "Maintain the routine monitoring cadence and re-image in 14 days.",
        RiskLevel.MEDIUM: "Send a field team to collect a grab sample at the north and south shores within seven days.",
        RiskLevel.HIGH: "Dispatch a sampling team within 48 hours, alert the local water authority, and re-image once a clear pass is available.",
    }
    if aoi_type == "land":
        intro = (
            "The selected AOI is mostly land (NDWI ≤ 0 across the polygon), so "
            "these spectral indices reflect vegetation and bare ground rather than "
            "water quality. Treat the score as a ground reflectance summary, not a "
            "water assessment. "
        )
        recommendation = (
            "Move the AOI over an actual water body and re-run before drawing conclusions."
        )
    elif aoi_type == "mixed":
        intro = (
            "The AOI includes a mix of water and land. Water-quality indices over "
            "the water portion still apply, but land pixels dilute the signal. "
        )
        recommendation = recommendation_map[score.level]
    else:
        intro = ""
        recommendation = recommendation_map[score.level]
    body = (
        f"The deterministic model assigned a {level} risk with {urgency} urgency. "
        f"NDCI={ndci.value:.3f} ({ndci.interpretation}) and "
        f"NDTI={ndti.value:.3f} ({ndti.interpretation}) drive the bulk of the score. "
        "Field observations were folded in where available."
        if ndci and ndti
        else f"The deterministic model assigned a {level} risk with {urgency} urgency."
    )
    return ReasoningBundle(
        recommendation=recommendation,
        reasoning=intro + body,
        limitations=(
            "This report is advisory and not a substitute for laboratory testing. "
            "Spectral indices are sensitive to cloud cover, sun angle, and water depth."
        ),
    )


class QuotaExceededError(RuntimeError):
    """Raised when a Gemini call hits a quota / rate-limit error.

    We use a typed exception so :func:`generate_reasoning` can fall over to
    the next configured API key instead of giving up on the user.
    """


class CredentialRejectedError(RuntimeError):
    """Raised when a Gemini key is invalid / expired.

    We treat this as key-scoped so the caller can fail over to the next
    configured key instead of aborting the entire reasoning path.
    """


# Substrings we look for inside the SDK's exception messages to decide a
# call was rejected for quota reasons. The SDK doesn't expose a stable
# error-code enum across versions, so we sniff the textual signal that
# the underlying HTTP response carried a 429 / RESOURCE_EXHAUSTED.
_QUOTA_SIGNALS = (
    "RESOURCE_EXHAUSTED",
    "resource_exhausted",
    "quota",
    "Quota",
    "rate limit",
    "Rate limit",
    "rate_limit",
    "RateLimitError",
    "429",
)

_CREDENTIAL_SIGNALS = (
    "API_KEY_INVALID",
    "api key invalid",
    "api key expired",
    "key expired",
    "invalid api key",
    "invalid_api_key",
    "AuthenticationError",
)


def _looks_like_quota_error(exc: BaseException) -> bool:
    text = str(exc)
    return any(signal in text for signal in _QUOTA_SIGNALS)


def _looks_like_credential_error(exc: BaseException) -> bool:
    text = str(exc)
    lowered = text.lower()
    return any(signal in text for signal in _CREDENTIAL_SIGNALS) or any(
        signal in lowered for signal in _CREDENTIAL_SIGNALS
    )


def _call_groq(
    *,
    user_json: str,
    system_instruction: str,
    model: str,
    api_key: str,
) -> str:
    """Issue a single Groq call with system + user channels.

    ``system_instruction`` carries the rules. ``user_json`` carries the
    facts as a pure JSON object. JSON mode is requested so the model
    returns a parseable ReasoningBundle.
    """
    from groq import AuthenticationError, Groq, RateLimitError

    schema_hint = (
        f"\n\nRespond with a JSON object matching this schema:\n"
        f"{json.dumps(ReasoningBundle.model_json_schema(), indent=2)}\n"
        "Return ONLY the JSON object, no markdown fences, no prose."
    )
    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction + schema_hint},
                {"role": "user", "content": user_json},
            ],
            temperature=0.3,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
    except RateLimitError as exc:
        raise QuotaExceededError(str(exc)) from exc
    except AuthenticationError as exc:
        raise CredentialRejectedError(str(exc)) from exc
    except Exception as exc:
        if _looks_like_quota_error(exc):
            raise QuotaExceededError(str(exc)) from exc
        if _looks_like_credential_error(exc):
            raise CredentialRejectedError(str(exc)) from exc
        raise
    text = (response.choices[0].message.content or "") if response.choices else ""
    if not text:
        raise RuntimeError("Groq returned an empty response")
    return text


def generate_reasoning(
    *,
    score: RiskScore,
    indices: Iterable[IndexAggregate],
    evidence: Iterable[FieldEvidence],
    water_body: WaterBody,
    water_fraction: float | None = None,
    aoi_type: str | None = None,
) -> ReasoningBundle:
    """Produce the narrative for a risk assessment.

    ``water_fraction`` and ``aoi_type`` describe how much of the AOI is
    actually open water. When the AOI is mostly land, the LLM is told to
    open with that disclosure so the user knows the spectral indices are
    not measuring water quality.
    """

    settings = get_settings()
    indices_list = list(indices)
    evidence_list = list(evidence)

    if settings.aqualens_fake_gemini:
        LOGGER.info("AQUALENS_FAKE_GEMINI=1, returning deterministic narrative")
        return _fake_bundle(score, indices_list, aoi_type=aoi_type)

    api_keys = settings.gemini_api_keys
    if not api_keys:
        raise ConfigurationError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com "
            "and add it to your .env file, or set AQUALENS_FAKE_GEMINI=1 for offline runs."
        )

    facts = _build_facts(
        score,
        indices_list,
        evidence_list,
        water_body,
        water_fraction=water_fraction,
        aoi_type=aoi_type,
    )
    user_json = _render_user_contents(facts)

    last_error: Exception | None = None

    # Outer loop walks the configured keys (primary, then fallback).
    # Inner loop retries the same key on a parse / format failure with a
    # tightened system instruction. Quota errors break the inner loop
    # immediately so we move on to the next key without burning the
    # retry budget.
    for key_index, api_key in enumerate(api_keys):
        system_instruction = _serialize_system_instruction()
        key_label = "primary" if key_index == 0 else f"fallback-{key_index}"
        for attempt in range(2):
            try:
                text = _call_groq(
                    user_json=user_json,
                    system_instruction=system_instruction,
                    model=settings.gemini_model,
                    api_key=api_key,
                )
                return ReasoningBundle.model_validate_json(text)
            except (QuotaExceededError, CredentialRejectedError) as exc:
                last_error = exc
                if isinstance(exc, QuotaExceededError):
                    LOGGER.warning(
                        "Groq quota exhausted on %s key — switching to next key. (%s)",
                        key_label,
                        exc,
                    )
                else:
                    LOGGER.warning(
                        "Groq key rejected on %s key — switching to next key. (%s)",
                        key_label,
                        exc,
                    )
                break  # don't retry this key, move to the next one
            except (ValidationError, RuntimeError) as exc:
                last_error = exc
                LOGGER.warning(
                    "Groq call failed on %s key, attempt %d: %s",
                    key_label,
                    attempt + 1,
                    exc,
                )
                system_instruction = _serialize_system_instruction(_RETRY_DIRECTIVE_JSON)

    raise RuntimeError(
        f"Groq reasoning failed after exhausting {len(api_keys)} key(s): {last_error}"
    )
