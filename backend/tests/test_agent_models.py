"""Smoke tests for the new agent-layer SQLModel tables.

Stage 1 deliverable: prove that ``AgentMemory`` and ``AgentTrace``
round-trip through the SQLite test schema, that the new optional
columns on ``RiskAssessment`` accept both NULL and populated values,
and that the recall payload serialiser produces JSON-safe output.
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from app.models import (
    AgentMemory,
    AgentTrace,
    MemoryKind,
    MonitoringSession,
    RiskAssessment,
    RiskLevel,
    SessionStatus,
    Urgency,
    WaterBody,
)


def _seed_water_body(db: Session) -> WaterBody:
    wb = WaterBody(
        name="Memory Test Lake",
        description="Stage 1 fixture",
        geometry={
            "type": "Polygon",
            "coordinates": [[[9.0, 45.0], [9.1, 45.0], [9.1, 45.1], [9.0, 45.1], [9.0, 45.0]]],
        },
        centroid={"type": "Point", "coordinates": [9.05, 45.05]},
        area_km2=12.5,
        source="test",
    )
    db.add(wb)
    db.commit()
    db.refresh(wb)
    return wb


def _seed_session(db: Session, wb: WaterBody) -> MonitoringSession:
    sess = MonitoringSession(
        water_body_id=wb.id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 16),
        max_cloud_cover=30.0,
        status=SessionStatus.COMPLETE,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def test_agent_memory_round_trip(db_session: Session) -> None:
    wb = _seed_water_body(db_session)
    sess = _seed_session(db_session, wb)

    mem = AgentMemory(
        water_body_id=wb.id,
        source_session_id=sess.id,
        kind=MemoryKind.ESCALATION,
        note="NDCI 0.34, doubled from prior month. Possible early bloom.",
        confidence=0.82,
        embedding=[0.0] * 768,
    )
    db_session.add(mem)
    db_session.commit()

    loaded = db_session.exec(select(AgentMemory).where(AgentMemory.id == mem.id)).one()
    assert loaded.kind is MemoryKind.ESCALATION
    assert loaded.confidence == 0.82
    assert loaded.embedding is not None
    assert len(loaded.embedding) == 768
    payload = loaded.as_recall_payload()
    assert payload["kind"] == "escalation"
    assert "NDCI" in payload["note"]


def test_agent_trace_round_trip(db_session: Session) -> None:
    wb = _seed_water_body(db_session)
    sess = _seed_session(db_session, wb)

    trace = AgentTrace(
        session_id=sess.id,
        coordinator_plan={
            "plan": [{"agent": "scout", "reason": "fresh AOI", "budget": {"max_tool_calls": 6}}],
            "rationale": "default coverage",
            "estimated_complexity": "low",
        },
        agent_runs=[
            {
                "schema_version": 1,
                "agent": "scout",
                "started_at": "2026-05-16T10:00:00Z",
                "completed_at": "2026-05-16T10:00:03Z",
                "latency_ms": 3000,
                "tokens_in": 1200,
                "tokens_out": 180,
                "tool_calls": [],
                "outputs": {"selected_scene": "S2A_TEST"},
                "error": None,
            }
        ],
        total_tokens_in=1200,
        total_tokens_out=180,
        total_latency_ms=3000,
        gemini_model="gemini-2.5-flash",
    )
    db_session.add(trace)
    db_session.commit()

    loaded = db_session.exec(select(AgentTrace).where(AgentTrace.session_id == sess.id)).one()
    assert loaded.coordinator_plan["estimated_complexity"] == "low"
    assert loaded.agent_runs[0]["outputs"]["selected_scene"] == "S2A_TEST"
    assert loaded.total_latency_ms == 3000


def test_risk_assessment_links_to_agent_trace(db_session: Session) -> None:
    wb = _seed_water_body(db_session)
    sess = _seed_session(db_session, wb)

    trace = AgentTrace(
        session_id=sess.id,
        coordinator_plan={"plan": [], "rationale": "x", "estimated_complexity": "low"},
        agent_runs=[],
        total_tokens_in=0,
        total_tokens_out=0,
        total_latency_ms=0,
        gemini_model="gemini-2.5-flash",
    )
    db_session.add(trace)
    db_session.commit()

    risk = RiskAssessment(
        session_id=sess.id,
        score=0.5,
        level=RiskLevel.MEDIUM,
        urgency=Urgency.ELEVATED,
        recommendation="r",
        reasoning="g",
        limitations="l",
        contributors={"ndci": 0.2},
        agent_trace_id=trace.id,
        field_brief={
            "tasks": [{"priority": "p1", "sample_type": "grab", "estimated_minutes": 30}],
            "turnaround_hours": 48,
            "escalate_to": None,
        },
    )
    db_session.add(risk)
    db_session.commit()

    loaded = db_session.exec(select(RiskAssessment).where(RiskAssessment.id == risk.id)).one()
    assert loaded.agent_trace_id == trace.id
    assert loaded.field_brief is not None
    assert loaded.field_brief["turnaround_hours"] == 48


def test_risk_assessment_agent_trace_is_optional(db_session: Session) -> None:
    """Sessions produced by the deterministic-only path must still persist."""
    wb = _seed_water_body(db_session)
    sess = _seed_session(db_session, wb)
    risk = RiskAssessment(
        session_id=sess.id,
        score=0.1,
        level=RiskLevel.LOW,
        urgency=Urgency.ROUTINE,
        recommendation="r",
        reasoning="g",
        limitations="l",
        contributors={},
    )
    db_session.add(risk)
    db_session.commit()

    loaded = db_session.exec(select(RiskAssessment).where(RiskAssessment.id == risk.id)).one()
    assert loaded.agent_trace_id is None
    assert loaded.field_brief is None


def test_agentic_mode_defaults_off_in_tests() -> None:
    """conftest pins AQUALENS_AGENTIC_MODE=0 so the existing suite stays meaningful."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    assert get_settings().aqualens_agentic_mode is False
    # Note: gemini_embedding_model removed after Groq migration (Groq has no embeddings API)


def test_session_with_completed_status_smoke(db_session: Session) -> None:
    """Confirms the existing SessionStatus.COMPLETE still works after the migration."""
    wb = _seed_water_body(db_session)
    sess = _seed_session(db_session, wb)
    loaded = db_session.exec(select(MonitoringSession).where(MonitoringSession.id == sess.id)).one()
    assert loaded.status is SessionStatus.COMPLETE


def test_session_status_enum_uses_value_labels() -> None:
    """Guards against enum-name writes (PENDING) on Postgres enum columns."""
    status_enum = MonitoringSession.__table__.c.status.type
    assert status_enum.enums == [status.value for status in SessionStatus]
