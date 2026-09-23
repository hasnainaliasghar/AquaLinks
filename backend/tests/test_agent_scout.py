"""Stage 4: Scout agent.

Verifies:
- Happy path: list scenes → vision pass flags haze → re-list with
  tighter cloud bound → commit cleaner scene → structured output
  validates as ScoutSelection.
- Fallback: when Gemini fails to emit schema-valid output, the Scout
  salvages the freshest candidate from the most recent
  list_recent_scenes call so the pipeline never stalls.

The Gemini SDK is faked at the same seam as ``test_agent_runtime``.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest

from app.services.agent.scout import ScoutSelection, run_scout
from app.services.agent.trace import TraceRecorder

# ----------------------------------------------------------------------
# Fake Gemini SDK
# ----------------------------------------------------------------------


class _FakeFinish(SimpleNamespace):
    pass


class _FakeCandidate:
    def __init__(self, parts: list[Any], finish: str = "STOP") -> None:
        self.content = SimpleNamespace(role="model", parts=parts)
        self.finish_reason = _FakeFinish(value=finish)
        self.grounding_metadata = None


class _FakeResponse:
    def __init__(
        self,
        parts: list[Any],
        text: str = "",
        tokens_in: int = 30,
        tokens_out: int = 15,
    ) -> None:
        self.candidates = [_FakeCandidate(parts)]
        self.text = text
        self.usage_metadata = SimpleNamespace(
            prompt_token_count=tokens_in,
            candidates_token_count=tokens_out,
        )


def _fc(name: str, args: dict[str, Any]) -> Any:
    return SimpleNamespace(name=name, args=args)


def _text_part(text: str) -> Any:
    return SimpleNamespace(text=text, function_call=None)


def _fc_part(name: str, args: dict[str, Any]) -> Any:
    return SimpleNamespace(text=None, function_call=_fc(name, args))


@pytest.fixture()
def fake_gemini(monkeypatch) -> Iterator[list[Any]]:
    queue: list[Any] = []

    class _FakeModels:
        def generate_content(self, *, model, contents, config):
            if not queue:
                raise AssertionError("Gemini queue exhausted")
            return queue.pop(0)

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
                function_response=SimpleNamespace(name=name, response=response)
            ),
            from_uri=lambda file_uri, mime_type: SimpleNamespace(
                file_data=SimpleNamespace(file_uri=file_uri, mime_type=mime_type)
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

    yield queue

    get_settings.cache_clear()


# ----------------------------------------------------------------------
# STAC + Vision fixtures
# ----------------------------------------------------------------------


@pytest.fixture()
def stub_stac(monkeypatch):
    """Replace stac_tools' list_recent_scenes + inspect_scene with controllable stubs."""
    from app.services.agent.tools import stac_tools

    # Two scripted responses keyed by max_cloud_cover.
    canned: dict[float, dict[str, Any]] = {}

    def fake_list(*, aoi_geojson, start_date, end_date, max_cloud_cover, limit=6):
        key = round(float(max_cloud_cover), 1)
        if key not in canned:
            return {"candidates": [], "reason": f"no fixture for cloud<={key}"}
        return canned[key]

    def fake_inspect(*, scene_id: str):
        return {"scene_id": scene_id, "cloud_cover": 12.0, "capture_date": "2026-05-09T10:00:00"}

    monkeypatch.setattr(stac_tools, "list_recent_scenes", fake_list)
    monkeypatch.setattr(stac_tools, "inspect_scene", fake_inspect)
    return canned


@pytest.fixture()
def stub_vision(monkeypatch):
    """Replace vision_tools.look_at_thumbnail with a deterministic stub."""
    from app.services.agent.tools import vision_tools

    captured: list[dict[str, Any]] = []

    def fake_look(*, image_url: str, focus_prompt: str):
        captured.append({"image_url": image_url, "focus_prompt": focus_prompt})
        if "S2A_A" in image_url:
            return {
                "available": True,
                "image_url": image_url,
                "focus_prompt": focus_prompt,
                "summary": "Visible haze sits over the north shore of the AOI.",
                "haze_visible": True,
                "sun_glint_visible": False,
                "visible_bloom_signature": False,
                "notes": None,
            }
        return {
            "available": True,
            "image_url": image_url,
            "focus_prompt": focus_prompt,
            "summary": "Clear over the AOI; no obvious haze or glint.",
            "haze_visible": False,
            "sun_glint_visible": False,
            "visible_bloom_signature": False,
            "notes": None,
        }

    monkeypatch.setattr(vision_tools, "look_at_thumbnail", fake_look)
    return captured


# ----------------------------------------------------------------------
# Happy path
# ----------------------------------------------------------------------


def test_scout_iterates_with_vision_and_commits_clean_scene(fake_gemini, stub_stac, stub_vision):
    # Round 1 (cloud<=30): freshest is hazy S2A_A, a less-recent S2A_B
    # is borderline.
    stub_stac[30.0] = {
        "candidates": [
            {
                "scene_id": "S2A_A",
                "capture_date": "2026-05-12T10:00:00",
                "cloud_cover": 28.0,
                "mgrs_tile": "32TNS",
                "thumbnail_url": "https://example.test/preview/S2A_A.png",
                "platform": "sentinel-2a",
                "stac_link": "https://example.test/stac/S2A_A",
            },
            {
                "scene_id": "S2A_B",
                "capture_date": "2026-05-09T10:00:00",
                "cloud_cover": 18.0,
                "mgrs_tile": "32TNS",
                "thumbnail_url": "https://example.test/preview/S2A_B.png",
                "platform": "sentinel-2a",
                "stac_link": "https://example.test/stac/S2A_B",
            },
        ],
        "window": {"start": "2026-04-12", "end": "2026-05-12"},
        "max_cloud_cover": 30.0,
    }
    # Round 2 (cloud<=15): one clean scene S2A_C.
    stub_stac[15.0] = {
        "candidates": [
            {
                "scene_id": "S2A_C",
                "capture_date": "2026-05-09T10:00:00",
                "cloud_cover": 8.0,
                "mgrs_tile": "32TNS",
                "thumbnail_url": "https://example.test/preview/S2A_C.png",
                "platform": "sentinel-2a",
                "stac_link": "https://example.test/stac/S2A_C",
            }
        ],
        "window": {"start": "2026-04-12", "end": "2026-05-12"},
        "max_cloud_cover": 15.0,
    }

    # Scripted Gemini turns:
    # 1. call list_recent_scenes(30%)
    # 2. call look_at_thumbnail(S2A_A)  -> vision reports haze
    # 3. call list_recent_scenes(15%)
    # 4. final structured selection naming S2A_C
    selection_json = (
        '{"selected_scene_id":"S2A_C",'
        '"selected_capture_date":"2026-05-09T10:00:00",'
        '"selected_cloud_cover":8.0,'
        '"selection_reason":"S2A_A was hazy over the AOI per Vision; '
        'S2A_C is the cleanest acceptable candidate.",'
        '"considered_alternatives":[{"scene_id":"S2A_A","cloud_cover":28.0,'
        '"why_not":"vision flagged haze over AOI"}],'
        '"vision_findings":[{"image_url":"https://example.test/preview/S2A_A.png",'
        '"focus_prompt":"Is haze visible over the AOI?",'
        '"summary":"haze over north shore","haze_visible":true,'
        '"sun_glint_visible":false,"visible_bloom_signature":false}]}'
    )

    fake_gemini.extend(
        [
            _FakeResponse(
                parts=[
                    _fc_part(
                        "list_recent_scenes",
                        {
                            "aoi_geojson": {"type": "Polygon", "coordinates": []},
                            "start_date": "2026-04-12",
                            "end_date": "2026-05-12",
                            "max_cloud_cover": 30.0,
                        },
                    )
                ]
            ),
            _FakeResponse(
                parts=[
                    _fc_part(
                        "look_at_thumbnail",
                        {
                            "image_url": "https://example.test/preview/S2A_A.png",
                            "focus_prompt": "Is haze visible over the AOI?",
                        },
                    )
                ]
            ),
            _FakeResponse(
                parts=[
                    _fc_part(
                        "list_recent_scenes",
                        {
                            "aoi_geojson": {"type": "Polygon", "coordinates": []},
                            "start_date": "2026-04-12",
                            "end_date": "2026-05-12",
                            "max_cloud_cover": 15.0,
                        },
                    )
                ]
            ),
            _FakeResponse(parts=[_text_part(selection_json)], text=selection_json),
        ]
    )

    rec = TraceRecorder()
    with rec.record_agent("scout") as builder:
        selection = run_scout(
            builder=builder,
            aoi_geojson={"type": "Polygon", "coordinates": []},
            aoi_summary={"name": "Lake Test", "centroid": [9, 45], "area_km2": 5.0},
            start_date="2026-04-12",
            end_date="2026-05-12",
            max_cloud_cover=30.0,
        )

    assert isinstance(selection, ScoutSelection)
    assert selection.selected_scene_id == "S2A_C"
    assert selection.selected_cloud_cover == 8.0
    assert any(alt.scene_id == "S2A_A" for alt in selection.considered_alternatives)
    assert len(selection.vision_findings) == 1
    assert selection.vision_findings[0].haze_visible is True

    # Vision stub was actually invoked with S2A_A's URL.
    assert any("S2A_A" in entry["image_url"] for entry in stub_vision)

    compiled = rec.compile()["agent_runs"][0]
    tool_names = [tc["name"] for tc in compiled["tool_calls"]]
    assert tool_names == [
        "list_recent_scenes",
        "look_at_thumbnail",
        "list_recent_scenes",
    ]
    assert compiled["outputs"]["selected_scene_id"] == "S2A_C"


# ----------------------------------------------------------------------
# Fallback path
# ----------------------------------------------------------------------


def test_scout_falls_back_to_freshest_candidate_when_model_outputs_garbage(
    fake_gemini, stub_stac, stub_vision
):
    stub_stac[30.0] = {
        "candidates": [
            {
                "scene_id": "S2A_FRESH",
                "capture_date": "2026-05-12T10:00:00",
                "cloud_cover": 14.0,
                "mgrs_tile": "32TNS",
                "thumbnail_url": "https://example.test/preview/S2A_FRESH.png",
                "platform": "sentinel-2a",
                "stac_link": "https://example.test/stac/S2A_FRESH",
            }
        ],
        "window": {"start": "2026-04-12", "end": "2026-05-12"},
        "max_cloud_cover": 30.0,
    }

    fake_gemini.extend(
        [
            _FakeResponse(
                parts=[
                    _fc_part(
                        "list_recent_scenes",
                        {
                            "aoi_geojson": {"type": "Polygon", "coordinates": []},
                            "start_date": "2026-04-12",
                            "end_date": "2026-05-12",
                            "max_cloud_cover": 30.0,
                        },
                    )
                ]
            ),
            # Final response is NOT schema-valid JSON.
            _FakeResponse(parts=[_text_part("I think we should pick something")], text="prose"),
        ]
    )

    rec = TraceRecorder()
    with rec.record_agent("scout") as builder:
        selection = run_scout(
            builder=builder,
            aoi_geojson={"type": "Polygon", "coordinates": []},
            aoi_summary={"name": "Fallback Lake", "centroid": [9, 45], "area_km2": 3.0},
            start_date="2026-04-12",
            end_date="2026-05-12",
            max_cloud_cover=30.0,
        )

    assert selection.selected_scene_id == "S2A_FRESH"
    assert "Fallback" in selection.selection_reason
