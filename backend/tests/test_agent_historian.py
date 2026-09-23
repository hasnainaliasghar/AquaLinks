"""Stage 5: Historian agent.

Verifies:
- The agent invokes its DB tools in the right order, writes one
  persistent note, and emits a schema-valid HistorianBriefing.
- The runtime forwards Google Search citations, URL Context
  citations, and code-execution output through ``result.extras`` so
  the trace UI can render them.
- Fallback briefing kicks in when Gemini fails to return valid JSON.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from sqlmodel import Session

from app.models import (
    AgentMemory,
    MonitoringSession,
    SessionStatus,
    WaterBody,
)
from app.services.agent.historian import HistorianBriefing, run_historian
from app.services.agent.trace import TraceRecorder

UTC = UTC


# ----------------------------------------------------------------------
# Fake Gemini SDK
# ----------------------------------------------------------------------


def _fc(name: str, args: dict[str, Any]) -> Any:
    return SimpleNamespace(name=name, args=args)


def _text_part(text: str) -> Any:
    return SimpleNamespace(
        text=text,
        function_call=None,
        executable_code=None,
        code_execution_result=None,
    )


def _fc_part(name: str, args: dict[str, Any]) -> Any:
    return SimpleNamespace(
        text=None,
        function_call=_fc(name, args),
        executable_code=None,
        code_execution_result=None,
    )


def _candidate(parts: list[Any], grounding: Any = None) -> Any:
    return SimpleNamespace(
        content=SimpleNamespace(role="model", parts=parts),
        finish_reason=SimpleNamespace(value="STOP"),
        grounding_metadata=grounding,
    )


def _response(
    candidates: list[Any],
    text: str = "",
    tokens_in: int = 30,
    tokens_out: int = 15,
) -> Any:
    return SimpleNamespace(
        candidates=candidates,
        text=text,
        usage_metadata=SimpleNamespace(
            prompt_token_count=tokens_in,
            candidates_token_count=tokens_out,
        ),
    )


def _grounding(citations: list[dict[str, Any]], queries: list[str]) -> Any:
    chunks = [
        SimpleNamespace(web=SimpleNamespace(title=c["title"], uri=c["uri"])) for c in citations
    ]
    return SimpleNamespace(grounding_chunks=chunks, web_search_queries=queries)


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
        GoogleSearch=lambda: SimpleNamespace(),
        UrlContext=lambda: SimpleNamespace(),
        ToolCodeExecution=lambda: SimpleNamespace(),
        GenerateContentConfig=lambda **kw: SimpleNamespace(**kw),
        ThinkingConfig=lambda **kw: SimpleNamespace(**kw),
        Content=lambda role, parts: SimpleNamespace(role=role, parts=parts),
        Part=SimpleNamespace(
            from_text=lambda text: SimpleNamespace(
                text=text, function_call=None, executable_code=None, code_execution_result=None
            ),
            from_function_response=lambda name, response: SimpleNamespace(
                function_response=SimpleNamespace(name=name, response=response),
                executable_code=None,
                code_execution_result=None,
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
# Fixtures
# ----------------------------------------------------------------------


def _seed(db: Session) -> tuple[WaterBody, MonitoringSession]:
    wb = WaterBody(
        name="Lake Historian",
        description="Stage 5 fixture",
        geometry={
            "type": "Polygon",
            "coordinates": [[[9.0, 45.0], [9.1, 45.0], [9.1, 45.1], [9.0, 45.1], [9.0, 45.0]]],
        },
        centroid={"type": "Point", "coordinates": [9.05, 45.05]},
        area_km2=4.0,
        source="test",
    )
    db.add(wb)
    db.commit()
    db.refresh(wb)

    base = datetime(2026, 4, 1, tzinfo=UTC)
    for delta in (0, 7, 14):
        prior = MonitoringSession(
            water_body_id=wb.id,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 5, 1),
            max_cloud_cover=30.0,
            status=SessionStatus.COMPLETE,
            scene_capture_date=base + timedelta(days=delta),
            scene_id=f"S2A_OLD_{delta}",
            scene_cloud_cover=15.0 + delta,
        )
        db.add(prior)
    db.commit()

    current = MonitoringSession(
        water_body_id=wb.id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 16),
        max_cloud_cover=30.0,
        status=SessionStatus.PROCESSING,
        scene_capture_date=datetime(2026, 5, 14, tzinfo=UTC),
        scene_id="S2A_CURRENT",
        scene_cloud_cover=8.0,
    )
    db.add(current)
    db.commit()
    db.refresh(current)
    return wb, current


# ----------------------------------------------------------------------
# Happy path
# ----------------------------------------------------------------------


def test_historian_pulls_history_writes_note_returns_briefing(
    db_session: Session, fake_gemini
) -> None:
    wb, current = _seed(db_session)

    briefing_json = (
        '{"trend":{"metric":"NDCI","slope_per_day":0.003,"mann_kendall_p":0.04,'
        '"summary":"NDCI rising; trend is significant."},'
        '"recalled_notes":[],'
        '"grounded_findings":[{"title":"Lake Como bloom warning",'
        '"uri":"https://example.test/news/como-bloom",'
        '"snippet":"Authorities reported elevated chlorophyll on the north shore."}],'
        '"new_persistent_notes_written":[{"kind":"escalation","note":"NDCI trending up across last 14d",'
        '"confidence":0.78}],'
        '"briefing_text":"NDCI on this water body has risen consistently over the past two weeks '
        "(trend significant at p=0.04). Recent reporting from example.test corroborates an "
        'observed bloom warning."}'
    )

    fake_gemini.extend(
        [
            _response([_candidate([_fc_part("get_session_history", {"limit": 20})])]),
            _response(
                [_candidate([_fc_part("compute_trend", {"metric": "NDCI", "sessions": []})])]
            ),
            _response([_candidate([_fc_part("recall_persistent_notes", {"limit": 10})])]),
            _response(
                [
                    _candidate(
                        [
                            _fc_part(
                                "write_persistent_note",
                                {
                                    "kind": "escalation",
                                    "note": "NDCI trending up across last 14d",
                                    "confidence": 0.78,
                                },
                            )
                        ]
                    )
                ]
            ),
            _response(
                [
                    _candidate(
                        [_text_part(briefing_json)],
                        grounding=_grounding(
                            citations=[
                                {
                                    "title": "Lake Como bloom warning",
                                    "uri": "https://example.test/news/como-bloom",
                                }
                            ],
                            queries=["Lake Como algal bloom 2026"],
                        ),
                    )
                ],
                text=briefing_json,
            ),
        ]
    )

    rec = TraceRecorder()
    with rec.record_agent("historian") as builder:
        briefing = run_historian(
            builder=builder,
            db=db_session,
            water_body=wb,
            source_session_id=current.id,
            current_indices=[{"name": "NDCI", "value": 0.32}],
            scene_capture_date=(
                current.scene_capture_date.isoformat() if current.scene_capture_date else None
            ),
            aoi_type="water",
        )

    assert isinstance(briefing, HistorianBriefing)
    assert briefing.trend is not None
    assert briefing.trend.summary.startswith("NDCI rising")
    assert briefing.grounded_findings[0].uri == "https://example.test/news/como-bloom"
    assert len(briefing.new_persistent_notes_written) == 1

    # The historian's write_persistent_note tool call actually persisted to the DB.
    persisted = db_session.exec(
        AgentMemory.__table__.select().where(AgentMemory.water_body_id == wb.id)
    ).all()
    assert len(persisted) == 1

    compiled = rec.compile()["agent_runs"][0]
    tool_names = [tc["name"] for tc in compiled["tool_calls"]]
    assert tool_names == [
        "get_session_history",
        "compute_trend",
        "recall_persistent_notes",
        "write_persistent_note",
    ]
    # Grounding extras surfaced into the agent outputs for the trace UI.
    extras = compiled["outputs"]["extras"]
    assert extras["citations"][0]["uri"] == "https://example.test/news/como-bloom"
    assert extras["search_queries"] == ["Lake Como algal bloom 2026"]


# ----------------------------------------------------------------------
# Fallback path
# ----------------------------------------------------------------------


def test_historian_falls_back_when_model_emits_garbage(db_session: Session, fake_gemini) -> None:
    wb, current = _seed(db_session)

    fake_gemini.extend(
        [
            _response([_candidate([_fc_part("get_session_history", {"limit": 20})])]),
            _response([_candidate([_text_part("not a valid briefing")])], text="not valid"),
        ]
    )

    rec = TraceRecorder()
    with rec.record_agent("historian") as builder:
        briefing = run_historian(
            builder=builder,
            db=db_session,
            water_body=wb,
            source_session_id=current.id,
            current_indices=[],
            scene_capture_date=None,
            aoi_type=None,
        )

    assert briefing.trend is None
    assert "fallback" in briefing.briefing_text.lower()
