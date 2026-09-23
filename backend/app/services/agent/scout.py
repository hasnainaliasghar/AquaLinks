"""Scout agent — chooses the Sentinel-2 scene the pipeline will analyse.

The Scout is a Gemini function-calling loop with three tools:

- ``list_recent_scenes``     — STAC search, returns candidates.
- ``inspect_scene``          — single-scene lookup by id.
- ``look_at_thumbnail``      — Gemini Vision pass on the RGB thumbnail.

The loop stops when Gemini emits a final structured ``ScoutSelection``
JSON response (the ``response_schema`` does the validation). The
deterministic pipeline then takes the chosen scene_id and runs the
existing band-reading / index-computation path on it — unchanged.
"""

from __future__ import annotations

import json
import re
from importlib.resources import files
from typing import Any

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.agent.gemini_runtime import (
    ToolSpec,
    run_tool_loop,
    to_json,
)
from app.services.agent.tools import stac_tools, vision_tools
from app.services.agent.trace import AgentTraceBuilder

LOGGER = get_logger(__name__)

SCOUT_NAME = "scout"
SCOUT_MAX_TURNS = 6

_HEMISPHERE_COORDS_RE = re.compile(
    r"^\s*\d{1,3}(?:\.\d+)?°\s*[NS]\s*[·,]\s*\d{1,3}(?:\.\d+)?°\s*[EW]\s*$",
    re.IGNORECASE,
)
_DECIMAL_COORDS_RE = re.compile(r"^\s*-?\d{1,3}(?:\.\d+)?°?\s*,\s*-?\d{1,3}(?:\.\d+)?°?\s*$")


# ----------------------------------------------------------------------
# Output schema
# ----------------------------------------------------------------------


class ConsideredAlternative(BaseModel):
    scene_id: str
    cloud_cover: float | None = None
    why_not: str


class VisionFinding(BaseModel):
    image_url: str
    focus_prompt: str
    summary: str
    haze_visible: bool | None = None
    sun_glint_visible: bool | None = None
    visible_bloom_signature: bool | None = None


class ScoutSelection(BaseModel):
    """The Scout's final structured output."""

    selected_scene_id: str = Field(min_length=1)
    selected_capture_date: str
    selected_cloud_cover: float
    selection_reason: str
    considered_alternatives: list[ConsideredAlternative] = Field(default_factory=list)
    vision_findings: list[VisionFinding] = Field(default_factory=list)


class PlaceNameLookup(BaseModel):
    place_name: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = Field(description="existing_name | google_search | centroid_inference | unknown")
    rationale: str


# ----------------------------------------------------------------------
# System instruction loader
# ----------------------------------------------------------------------

_SYSTEM_INSTRUCTION_JSON: dict[str, Any] = json.loads(
    files("app.services.agent.prompts").joinpath("scout.json").read_text(encoding="utf-8")
)


def _serialise_system() -> str:
    """The Scout receives the JSON document verbatim as its system instruction."""
    return json.dumps(_SYSTEM_INSTRUCTION_JSON, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------
# Tool registry
# ----------------------------------------------------------------------


def _tool_list_recent_scenes(**kwargs: Any) -> dict[str, Any]:
    # Defensive defaulting — Gemini sometimes omits optional args even
    # when the schema marks them required.
    aoi = kwargs.get("aoi_geojson") or kwargs.get("aoi") or {}
    start = kwargs.get("start_date")
    end = kwargs.get("end_date")
    max_cloud = float(kwargs.get("max_cloud_cover", 30.0))
    return stac_tools.list_recent_scenes(
        aoi_geojson=aoi,
        start_date=start,
        end_date=end,
        max_cloud_cover=max_cloud,
    )


def _tool_inspect_scene(**kwargs: Any) -> dict[str, Any]:
    return stac_tools.inspect_scene(scene_id=str(kwargs.get("scene_id", "")))


def _tool_look_at_thumbnail(**kwargs: Any) -> dict[str, Any]:
    return vision_tools.look_at_thumbnail(
        image_url=str(kwargs.get("image_url", "")),
        focus_prompt=str(kwargs.get("focus_prompt", "")),
    )


def _tool_specs() -> list[ToolSpec]:
    return [
        ToolSpec(
            name="list_recent_scenes",
            description=(
                "Search Microsoft Planetary Computer for Sentinel-2 L2A scenes that "
                "intersect the AOI within the given date window and cloud bound. "
                "Returns up to six candidates sorted newest-first. Each entry includes "
                "scene_id, capture_date, cloud_cover, mgrs_tile, and a signed "
                "thumbnail_url that look_at_thumbnail can ingest."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "aoi_geojson": {
                        "type": "object",
                        "description": "GeoJSON polygon of the AOI.",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "ISO date, inclusive lower bound.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "ISO date, inclusive upper bound.",
                    },
                    "max_cloud_cover": {
                        "type": "number",
                        "description": "Upper bound on eo:cloud_cover %, in [0, 100].",
                    },
                },
                "required": ["aoi_geojson", "start_date", "end_date", "max_cloud_cover"],
            },
            handler=_tool_list_recent_scenes,
        ),
        ToolSpec(
            name="inspect_scene",
            description="Look up a single STAC item by its scene_id and return metadata.",
            parameters={
                "type": "object",
                "properties": {
                    "scene_id": {"type": "string"},
                },
                "required": ["scene_id"],
            },
            handler=_tool_inspect_scene,
        ),
        ToolSpec(
            name="look_at_thumbnail",
            description=(
                "Ask Gemini Vision a focused question about a Sentinel-2 RGB thumbnail. "
                "Use to confirm whether haze, sun glint, ice, or a visible bloom "
                "signature affects the AOI before committing to a scene."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "image_url": {
                        "type": "string",
                        "description": "Signed thumbnail URL from list_recent_scenes.",
                    },
                    "focus_prompt": {
                        "type": "string",
                        "description": (
                            "What you want Vision to check. Examples: "
                            "'Is there haze over the AOI?'; "
                            "'Is there visible green discolouration?'"
                        ),
                    },
                },
                "required": ["image_url", "focus_prompt"],
            },
            handler=_tool_look_at_thumbnail,
        ),
    ]


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------


def run_scout(
    *,
    builder: AgentTraceBuilder,
    aoi_geojson: dict[str, Any],
    aoi_summary: dict[str, Any],
    start_date: str,
    end_date: str,
    max_cloud_cover: float,
    prior_history_summary: dict[str, Any] | None = None,
    max_turns: int = SCOUT_MAX_TURNS,
) -> ScoutSelection:
    """Run the Scout agent and return its committed scene selection.

    The caller (orchestrator) is responsible for wrapping this in
    ``trace.record_agent("scout")`` so every tool call gets recorded.
    """
    user_payload = {
        "aoi_geojson": aoi_geojson,
        "aoi_summary": aoi_summary,
        "window": {"start_date": start_date, "end_date": end_date},
        "max_cloud_cover": max_cloud_cover,
        "prior_history_summary": prior_history_summary,
    }

    result = run_tool_loop(
        builder=builder,
        system_instruction=_serialise_system(),
        user_message=to_json(user_payload),
        tools=_tool_specs(),
        response_schema=ScoutSelection,
        max_turns=max_turns,
        temperature=0.2,
    )

    if isinstance(result.parsed, ScoutSelection):
        selection = result.parsed
    else:
        # Last-resort fallback: pull the most-recent scene off the
        # candidates from the LAST list_recent_scenes call. This keeps
        # the pipeline moving even if the Scout failed to produce
        # schema-valid output (e.g. context cap hit, model confused).
        selection = _fallback_selection(builder)

    builder.set_outputs(selection.model_dump())
    return selection


def name_needs_enrichment(name: str | None) -> bool:
    trimmed = (name or "").strip()
    if not trimmed:
        return True
    if _HEMISPHERE_COORDS_RE.match(trimmed) or _DECIMAL_COORDS_RE.match(trimmed):
        return True
    lowered = trimmed.lower()
    generic_fragments = ("sample", "session", "aoi", "unnamed")
    return any(frag in lowered for frag in generic_fragments)


def run_place_name_lookup(
    *,
    builder: AgentTraceBuilder,
    current_name: str | None,
    centroid: dict[str, Any] | None,
    area_km2: float | None,
) -> PlaceNameLookup | None:
    """Optional Scout enrichment for weak/coordinate-style AOI names."""
    if not name_needs_enrichment(current_name):
        return None

    system_instruction = (
        "You are Scout's place-name resolver. Resolve a human place name for the AOI "
        "using centroid coordinates and context. If uncertain, return the best nearby "
        "water-body or locality name with low confidence. Output strict JSON only."
    )
    user_payload = {
        "current_name": current_name,
        "centroid": centroid,
        "area_km2": area_km2,
        "query_hint": "Find the nearest commonly-used place or water-body name.",
    }
    try:
        result = run_tool_loop(
            builder=builder,
            system_instruction=system_instruction,
            user_message=to_json(user_payload),
            tools=[],
            response_schema=PlaceNameLookup,
            max_turns=2,
            temperature=0.1,
            # Google Search grounding is Gemini-only; Groq will resolve
            # place names from its training knowledge instead.
        )
    except Exception as exc:
        LOGGER.warning("Scout place-name lookup failed (%s); continuing without enrichment", exc)
        return None

    if not isinstance(result.parsed, PlaceNameLookup):
        return None
    return result.parsed


def _fallback_selection(builder: AgentTraceBuilder) -> ScoutSelection:
    """Salvage the most-recent candidate when the Scout fails to emit JSON."""
    for call in reversed(builder.record.tool_calls):
        if call.name != "list_recent_scenes":
            continue
        result = call.result or {}
        candidates = result.get("candidates") or []
        if not candidates:
            continue
        c = candidates[0]
        return ScoutSelection(
            selected_scene_id=str(c.get("scene_id") or ""),
            selected_capture_date=str(c.get("capture_date") or ""),
            selected_cloud_cover=float(c.get("cloud_cover") or 0.0),
            selection_reason=(
                "Fallback: Scout did not emit a valid selection; using the freshest "
                "candidate from the most recent list_recent_scenes call."
            ),
        )
    raise RuntimeError("Scout produced no candidates and no schema-valid selection")


__all__ = [
    "SCOUT_NAME",
    "ConsideredAlternative",
    "PlaceNameLookup",
    "ScoutSelection",
    "VisionFinding",
    "name_needs_enrichment",
    "run_place_name_lookup",
    "run_scout",
]
