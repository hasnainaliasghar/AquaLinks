"""Vision passes over Sentinel-2 RGB thumbnails (Groq backend).

The Scout agent calls :func:`look_at_thumbnail` as a tool. Internally
this issues a focused Groq vision call using a vision-capable model
(``GROQ_VISION_MODEL``, default ``meta-llama/llama-4-scout-17b-16e-instruct``)
with the image URL and a short prompt asking about a specific visual
concern (haze, glint, visible bloom signature, ice cover, etc.).

The Scout's main loop only sees the textual observation; the trace records
both the URL and the question so the UI can show what the model saw.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.reasoning import QuotaExceededError, _looks_like_quota_error

LOGGER = get_logger(__name__)


class _VisionObservation(BaseModel):
    """Schema the vision model returns. Kept narrow on purpose."""

    summary: str = Field(description="One-sentence verdict on the focus question.")
    haze_visible: bool | None = Field(
        default=None, description="True if any haze/cloud is visible inside the AOI."
    )
    sun_glint_visible: bool | None = Field(default=None)
    visible_bloom_signature: bool | None = Field(default=None)
    notes: str | None = Field(
        default=None, description="Optional extra observations relevant to scene selection."
    )


def look_at_thumbnail(*, image_url: str, focus_prompt: str) -> dict[str, Any]:
    """Ask a vision model a focused question about a Sentinel-2 thumbnail.

    Returns a JSON-safe dict the Scout can feed back into its main
    reasoning loop. On a quota failure or when the LLM is disabled the
    function returns a stub observation flagged ``available=false`` so
    the Scout can still progress.
    """
    settings = get_settings()
    if settings.aqualens_fake_gemini or not settings.gemini_api_keys:
        return _stub_observation(image_url, focus_prompt, reason="fake_or_no_key")

    api_keys = settings.gemini_api_keys
    last_error: Exception | None = None
    for key_index, api_key in enumerate(api_keys):
        try:
            obs = _vision_call(
                api_key=api_key,
                model=settings.groq_vision_model,
                image_url=image_url,
                focus_prompt=focus_prompt,
            )
            return {
                "available": True,
                "image_url": image_url,
                "focus_prompt": focus_prompt,
                **obs.model_dump(),
            }
        except QuotaExceededError as exc:
            last_error = exc
            label = "primary" if key_index == 0 else f"fallback-{key_index}"
            LOGGER.warning("Vision quota on %s key — rolling over (%s)", label, exc)
            continue
        except Exception as exc:
            LOGGER.warning("Vision call failed (%s); returning stub", exc)
            return _stub_observation(image_url, focus_prompt, reason=str(exc))

    return _stub_observation(image_url, focus_prompt, reason=f"all_keys_quota:{last_error}")


def _vision_call(
    *, api_key: str, model: str, image_url: str, focus_prompt: str
) -> _VisionObservation:
    """Issue a Groq multimodal request. Kept tiny so tests can mock it."""
    from groq import Groq, RateLimitError

    client = Groq(api_key=api_key)

    system_instruction = (
        "You are a remote-sensing analyst inspecting a Sentinel-2 RGB "
        "thumbnail. Answer ONLY the focus question. Do not invent measurements "
        "and do not infer water quality from the image — your job is purely "
        "visual: is the AOI obscured by haze, sun glint, ice, or some other "
        "artefact that would make spectral analysis unreliable, and are there "
        "any obvious visible cues (e.g. green discolouration consistent with a "
        "bloom). Respond with a JSON object matching this schema:\n"
        f"{json.dumps(_VisionObservation.model_json_schema(), indent=2)}\n"
        "Return ONLY the JSON object, no markdown fences, no prose."
    )

    # Groq vision API: image passed as a URL content part.
    messages = [
        {"role": "system", "content": system_instruction},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
                {
                    "type": "text",
                    "text": f"Focus question: {focus_prompt}",
                },
            ],
        },
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=512,
            response_format={"type": "json_object"},
        )
    except RateLimitError as exc:
        raise QuotaExceededError(str(exc)) from exc
    except Exception as exc:
        if _looks_like_quota_error(exc):
            raise QuotaExceededError(str(exc)) from exc
        raise

    text = (response.choices[0].message.content or "").strip() if response.choices else ""
    if not text:
        raise RuntimeError("Groq vision returned an empty response")
    return _VisionObservation.model_validate_json(text)


def _stub_observation(image_url: str, focus_prompt: str, *, reason: str) -> dict[str, Any]:
    """Used in tests and during offline runs. Marked ``available=false``."""
    return {
        "available": False,
        "image_url": image_url,
        "focus_prompt": focus_prompt,
        "summary": "vision pass unavailable",
        "haze_visible": None,
        "sun_glint_visible": None,
        "visible_bloom_signature": None,
        "notes": f"reason={reason}",
    }


__all__ = ["look_at_thumbnail"]
