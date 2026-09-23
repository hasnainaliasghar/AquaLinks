"""Stage 8: Coordinator + orchestrator.

End-to-end agent run with mocked Gemini. Verifies:
- Coordinator plan is captured in the trace.
- Scout selection is forwarded into the trace.
- Historian runs only when prior history exists.
- Analyst produces a ReasoningBundle.
- Reporter produces the citizen-facing summary payload.
- Compiled trace payload matches the AgentTrace JSONB shape.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest
from sqlmodel import Session

from app.models import MonitoringSession, SessionStatus, WaterBody
from app.services.agent import orchestrator as orch_mod
from app.services.agent.orchestrator import run_orchestrator
from app.services.reasoning import ReasoningBundle

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


def _seed(db: Session) -> tuple[WaterBody, MonitoringSession]:
    wb = WaterBody(
        name="Lake Orchestrator",
        description="Stage 8 fixture",
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
    sess = MonitoringSession(
        water_body_id=wb.id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 16),
        max_cloud_cover=30.0,
        status=SessionStatus.PROCESSING,
        scene_id="S2A_TEST",
        scene_cloud_cover=8.0,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return wb, sess


_RISK = {
    "score": 0.62,
    "level": "medium",
    "urgency": "elevated",
    "contributors": {"ndci": 0.18, "ndti": 0.12},
}
_INDICES: list[dict[str, Any]] = [
    {
        "name": "NDCI",
        "value": 0.21,
        "interpretation": "elevated chlorophyll",
        "min_value": 0.0,
        "max_value": 0.4,
        "stddev": 0.05,
        "sample_count": 128,
        "bands": ["B05", "B04"],
    },
    {
        "name": "NDTI",
        "value": 0.15,
        "interpretation": "moderate turbidity",
        "min_value": 0.0,
        "max_value": 0.3,
        "stddev": 0.05,
        "sample_count": 128,
        "bands": ["B04", "B03"],
    },
]
_AOI = {"type": "water", "water_fraction": 0.95}


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


@pytest.fixture()
def stub_agents(monkeypatch) -> Iterator[dict[str, Any]]:
    """Replace each agent's run_* with a deterministic stub."""
    calls: dict[str, int] = {"coordinator": 0, "historian": 0, "analyst": 0, "reporter": 0}

    # Coordinator: skip Gemini, return a fixed plan.
    def fake_call_structured(*, builder, system_instruction, user_message, response_schema, **_kw):
        calls["coordinator"] += 1
        if response_schema is orch_mod.CoordinatorPlan:
            payload = json.loads(user_message)
            prior_count = int(payload.get("prior_session_count", 0))
            steps: list[orch_mod.PlanStep] = [
                orch_mod.PlanStep(
                    agent="scout",
                    reason="scout baseline step",
                    budget=orch_mod.PlanBudget(max_tool_calls=6, max_seconds=30),
                ),
            ]
            if prior_count > 0:
                steps.append(
                    orch_mod.PlanStep(
                        agent="historian",
                        reason="historian runs when prior history exists",
                        budget=orch_mod.PlanBudget(max_tool_calls=8, max_seconds=45),
                    )
                )
            steps.extend(
                [
                    orch_mod.PlanStep(
                        agent="analyst",
                        reason="analyst always writes the narrative",
                        budget=orch_mod.PlanBudget(max_tool_calls=3, max_seconds=30),
                    ),
                    orch_mod.PlanStep(
                        agent="reporter",
                        reason="reporter always writes public summary",
                        budget=orch_mod.PlanBudget(max_tool_calls=2, max_seconds=20),
                    ),
                ]
            )
            return orch_mod.CoordinatorPlan(
                plan=steps,
                rationale="stub plan",
                estimated_complexity="medium",
            )
        raise AssertionError(f"unexpected response_schema {response_schema}")

    monkeypatch.setattr(orch_mod, "call_structured", fake_call_structured)

    # Historian.
    def fake_historian(*, builder, db, water_body, source_session_id, **_kw):
        calls["historian"] += 1
        return SimpleNamespace(
            model_dump=lambda: {
                "trend": None,
                "recalled_notes": [],
                "grounded_findings": [],
                "new_persistent_notes_written": [],
                "briefing_text": "Stub briefing.",
            }
        )

    monkeypatch.setattr(orch_mod.historian_mod, "run_historian", fake_historian)

    # Analyst.
    from app.services.agent.analyst import AnalystOutput, EvidenceFocus

    def fake_analyst(*, builder, water_body, aoi, risk, indices, **_kw):
        calls["analyst"] += 1
        bundle = ReasoningBundle(
            recommendation="Send a team within seven days.",
            reasoning=("NDCI 0.21 and NDTI 0.15 sit in the elevated band; cloud cover acceptable."),
            limitations="Cloud cover; no in-situ sampling.",
        )
        return AnalystOutput(
            bundle=bundle,
            evidence_focus=[EvidenceFocus(target="north shore", reason="NDCI peak")],
            drafts=[],
            critique=None,
            rewrote=False,
        )

    monkeypatch.setattr(orch_mod.analyst_mod, "run_analyst", fake_analyst)

    # Reporter.
    from app.services.citizen_summary import CitizenSummary

    def fake_reporter(
        *,
        builder,
        water_body,
        aoi,
        risk,
        indices,
        evidence,
        scout_outputs,
        historian_briefing,
        analyst_narrative,
        fallback_summary,
    ):
        calls["reporter"] += 1
        return CitizenSummary(
            tone="caution",
            headline="Use caution today",
            bottom_line="Signals are elevated but not extreme.",
            safety_for_humans="Avoid swallowing water.",
            safety_for_pets_and_kids="Keep pets supervised.",
            what_we_could_not_check="No in-situ sample yet.",
            citations=[],
        )

    monkeypatch.setattr(orch_mod.reporter_mod, "run_reporter", fake_reporter)

    yield calls


def test_orchestrator_full_run_with_history(db_session: Session, stub_agents) -> None:
    wb, sess = _seed(db_session)

    result = run_orchestrator(
        db=db_session,
        water_body=wb,
        session_id=sess.id,
        aoi_geojson=wb.geometry,
        start_date="2026-04-01",
        end_date="2026-05-16",
        max_cloud_cover=30.0,
        indices=_INDICES,
        risk=_RISK,
        aoi=_AOI,
        evidence=[],
        prior_session_count=3,
        scene_id="S2A_TEST",
        scene_capture_date="2026-05-14T10:00:00",
        scene_cloud_cover=8.0,
    )

    assert isinstance(result.bundle, ReasoningBundle)
    assert "NDCI" in result.bundle.reasoning
    assert result.reporter_summary is not None
    assert result.reporter_summary.headline == "Use caution today"
    assert result.scene_id == "S2A_TEST"
    # Coordinator + Scout + Historian + Analyst + Reporter recorded in trace.
    runs = result.trace_payload["agent_runs"]
    agents_seen = [r["agent"] for r in runs]
    assert "coordinator" in agents_seen
    assert "scout" in agents_seen
    assert "historian" in agents_seen
    assert "analyst" in agents_seen
    assert "reporter" in agents_seen
    assert "field_liaison" not in agents_seen
    # Coordinator plan persisted on the trace.
    assert result.trace_payload["coordinator_plan"]["estimated_complexity"] == "medium"
    # Stub counters confirm the dispatch path.
    assert stub_agents["coordinator"] == 1
    assert stub_agents["historian"] == 1
    assert stub_agents["analyst"] == 1
    assert stub_agents["reporter"] == 1


def test_orchestrator_skips_historian_for_fresh_water_body(
    db_session: Session, stub_agents
) -> None:
    wb, sess = _seed(db_session)

    result = run_orchestrator(
        db=db_session,
        water_body=wb,
        session_id=sess.id,
        aoi_geojson=wb.geometry,
        start_date="2026-04-01",
        end_date="2026-05-16",
        max_cloud_cover=30.0,
        indices=_INDICES,
        risk=_RISK,
        aoi=_AOI,
        prior_session_count=0,  # fresh water body
        scene_id="S2A_TEST",
        scene_capture_date="2026-05-14T10:00:00",
        scene_cloud_cover=8.0,
    )

    runs = result.trace_payload["agent_runs"]
    agents_seen = [r["agent"] for r in runs]
    assert "historian" in agents_seen
    historian_row = next(r for r in runs if r["agent"] == "historian")
    assert historian_row["outputs"]["skipped"] is True
    assert stub_agents["historian"] == 0
    assert stub_agents["analyst"] == 1
    assert stub_agents["reporter"] == 1


def test_orchestrator_uses_default_plan_when_coordinator_fails(
    db_session: Session, monkeypatch
) -> None:
    wb, sess = _seed(db_session)

    def boom_call_structured(**_kw):
        raise RuntimeError("Coordinator exploded")

    monkeypatch.setattr(orch_mod, "call_structured", boom_call_structured)

    # Stub the other agents minimally.
    from app.services.agent.analyst import AnalystOutput, EvidenceFocus

    monkeypatch.setattr(
        orch_mod.historian_mod,
        "run_historian",
        lambda **kw: SimpleNamespace(model_dump=lambda: {"briefing_text": "x"}),
    )
    monkeypatch.setattr(
        orch_mod.analyst_mod,
        "run_analyst",
        lambda **kw: AnalystOutput(
            bundle=ReasoningBundle(
                recommendation="r",
                reasoning="NDCI and NDTI both elevated.",
                limitations="cloud cover",
            ),
            evidence_focus=[EvidenceFocus(target="t", reason="r")],
            drafts=[],
            critique=None,
            rewrote=False,
        ),
    )
    # Field Liaison stub is no longer needed — the agent was retired.

    result = run_orchestrator(
        db=db_session,
        water_body=wb,
        session_id=sess.id,
        aoi_geojson=wb.geometry,
        start_date="2026-04-01",
        end_date="2026-05-16",
        max_cloud_cover=30.0,
        indices=_INDICES,
        risk=_RISK,
        aoi=_AOI,
        prior_session_count=2,
        scene_id="S2A_TEST",
        scene_capture_date="2026-05-14T10:00:00",
        scene_cloud_cover=8.0,
    )

    # Default plan kicked in: coordinator step recorded, plan rationale set.
    assert result.trace_payload["coordinator_plan"]["estimated_complexity"] == "medium"
    assert isinstance(result.bundle, ReasoningBundle)


def test_orchestrator_uses_deterministic_fallback_when_analyst_fails(
    db_session: Session, monkeypatch
) -> None:
    wb, sess = _seed(db_session)

    monkeypatch.setattr(
        orch_mod,
        "call_structured",
        lambda **kw: orch_mod.CoordinatorPlan(
            plan=[
                orch_mod.PlanStep(
                    agent="scout",
                    reason="scout baseline step",
                    budget=orch_mod.PlanBudget(max_tool_calls=6, max_seconds=30),
                ),
                orch_mod.PlanStep(
                    agent="analyst",
                    reason="analyst always writes the narrative",
                    budget=orch_mod.PlanBudget(max_tool_calls=3, max_seconds=30),
                ),
                orch_mod.PlanStep(
                    agent="reporter",
                    reason="reporter always writes the public summary",
                    budget=orch_mod.PlanBudget(max_tool_calls=2, max_seconds=20),
                ),
            ],
            rationale="minimal plan",
            estimated_complexity="low",
        ),
    )

    monkeypatch.setattr(
        orch_mod.analyst_mod,
        "run_analyst",
        lambda **kw: (_ for _ in ()).throw(RuntimeError("Analyst exploded")),
    )
    monkeypatch.setattr(
        orch_mod.reporter_mod,
        "run_reporter",
        lambda **kw: kw["fallback_summary"],
    )

    result = run_orchestrator(
        db=db_session,
        water_body=wb,
        session_id=sess.id,
        aoi_geojson=wb.geometry,
        start_date="2026-04-01",
        end_date="2026-05-16",
        max_cloud_cover=30.0,
        indices=_INDICES,
        risk=_RISK,
        aoi=_AOI,
        prior_session_count=0,
        scene_id="S2A_TEST",
    )

    # Deterministic fallback narrative kicks in — bundle still populated.
    assert isinstance(result.bundle, ReasoningBundle)
    # Fallback narrative cites the level + urgency from the risk payload.
    assert "medium" in result.bundle.reasoning.lower()
