"""Stage 2 deliverable: agent tool layer.

Covers:
- ``embeddings.embed_text`` deterministic offline mode + cosine similarity.
- ``memory_tools`` recall, semantic recall, and write with retention.
- ``history_tools.compute_trend`` slope math over real session shapes.
- ``stac_tools.list_recent_scenes`` happy path via a stubbed STAC client.

The STAC stub avoids hitting Microsoft Planetary Computer from CI.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from app.models import (
    AgentMemory,
    IndexName,
    MemoryKind,
    MonitoringSession,
    RiskAssessment,
    RiskLevel,
    SessionStatus,
    SpectralIndex,
    Urgency,
    WaterBody,
)
from app.services.agent.tools import (
    embeddings,
    history_tools,
    memory_tools,
    stac_tools,
)

# ----------------------------------------------------------------------
# Embeddings
# ----------------------------------------------------------------------


def test_embed_text_zero_vector_for_empty_input() -> None:
    vec = embeddings.embed_text("")
    assert len(vec) == embeddings.EMBEDDING_DIM
    assert all(v == 0.0 for v in vec)


def test_embed_text_is_deterministic_and_unit_normalised() -> None:
    a = embeddings.embed_text("Lake Como NDCI doubled in 60 days")
    b = embeddings.embed_text("Lake Como NDCI doubled in 60 days")
    assert a == b
    norm_sq = sum(x * x for x in a)
    assert norm_sq == pytest.approx(1.0, abs=1e-6)


def test_embed_text_differs_per_input() -> None:
    a = embeddings.embed_text("escalation: high NDCI on Lake Como")
    b = embeddings.embed_text("routine: low risk on Lake Iseo")
    assert a != b


def test_cosine_similarity_basic_properties() -> None:
    v = embeddings.embed_text("any text")
    assert embeddings.cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)
    # Orthogonal-ish: pseudo-embeddings of unrelated texts should not be ~1.
    other = embeddings.embed_text("a completely different sentence")
    assert embeddings.cosine_similarity(v, other) < 0.99


# ----------------------------------------------------------------------
# Memory tools
# ----------------------------------------------------------------------


def _seed_wb_and_session(db: Session) -> tuple[WaterBody, MonitoringSession]:
    wb = WaterBody(
        name="Lake Tooling",
        description="Stage 2 fixture",
        geometry={
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        },
        centroid={"type": "Point", "coordinates": [0.5, 0.5]},
        area_km2=5.0,
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
        status=SessionStatus.COMPLETE,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return wb, sess


def test_write_and_recall_persistent_notes(db_session: Session) -> None:
    wb, sess = _seed_wb_and_session(db_session)

    written = memory_tools.write_persistent_note(
        db=db_session,
        water_body_id=wb.id,
        source_session_id=sess.id,
        kind=MemoryKind.ESCALATION,
        note="NDCI 0.34 vs 0.18 a month ago — possible early bloom",
        confidence=0.78,
    )
    assert written["created"] is True
    assert written["kind"] == "escalation"

    recalled = memory_tools.recall_persistent_notes(
        db=db_session,
        water_body_id=wb.id,
    )
    assert recalled["count"] == 1
    assert "NDCI" in recalled["notes"][0]["note"]
    assert recalled["notes"][0]["kind"] == "escalation"


def test_write_note_rejects_empty_and_out_of_range(db_session: Session) -> None:
    wb, sess = _seed_wb_and_session(db_session)
    assert (
        memory_tools.write_persistent_note(
            db=db_session,
            water_body_id=wb.id,
            source_session_id=sess.id,
            kind=MemoryKind.OBSERVATION,
            note="   ",
            confidence=0.5,
        )["created"]
        is False
    )
    assert (
        memory_tools.write_persistent_note(
            db=db_session,
            water_body_id=wb.id,
            source_session_id=sess.id,
            kind=MemoryKind.OBSERVATION,
            note="ok",
            confidence=1.7,
        )["created"]
        is False
    )


def test_semantic_recall_ranks_relevant_notes_first(db_session: Session) -> None:
    wb, sess = _seed_wb_and_session(db_session)

    memory_tools.write_persistent_note(
        db=db_session,
        water_body_id=wb.id,
        source_session_id=sess.id,
        kind=MemoryKind.OBSERVATION,
        note="Routine baseline: NDCI low, NDTI low, water clear",
        confidence=0.6,
    )
    memory_tools.write_persistent_note(
        db=db_session,
        water_body_id=wb.id,
        source_session_id=sess.id,
        kind=MemoryKind.ESCALATION,
        note="Algal bloom suspected: NDCI elevated, green discolouration",
        confidence=0.9,
    )

    result = memory_tools.semantic_recall_notes(
        db=db_session,
        water_body_id=wb.id,
        query="algal bloom NDCI rising",
        top_k=2,
    )
    # Shape only: real semantic ranking needs the production
    # text-embedding-004 model. Offline (test) embeddings are
    # hash-derived and deterministic, so we verify the function
    # returns ``top_k`` results, similarity scores are in [-1, 1],
    # and results are sorted descending.
    assert len(result["matches"]) == 2
    sims = [m["similarity"] for m in result["matches"]]
    assert all(-1.0 <= s <= 1.0 for s in sims)
    assert sims == sorted(sims, reverse=True)


def test_memory_retention_archives_overflow(db_session: Session, monkeypatch) -> None:
    monkeypatch.setattr(memory_tools, "MAX_ACTIVE_NOTES_PER_WATER_BODY", 3)
    wb, sess = _seed_wb_and_session(db_session)

    for i in range(5):
        memory_tools.write_persistent_note(
            db=db_session,
            water_body_id=wb.id,
            source_session_id=sess.id,
            kind=MemoryKind.OBSERVATION,
            note=f"observation {i}",
            confidence=0.5,
        )

    active = db_session.exec(
        select(AgentMemory)
        .where(AgentMemory.water_body_id == wb.id)
        .where(AgentMemory.archived_at.is_(None))  # type: ignore[union-attr]
    ).all()
    assert len(active) == 3
    # Total rows kept (active + archived) equals everything we wrote.
    total = db_session.exec(select(AgentMemory).where(AgentMemory.water_body_id == wb.id)).all()
    assert len(total) == 5


# ----------------------------------------------------------------------
# History tools
# ----------------------------------------------------------------------


def test_get_session_history_orders_newest_first(db_session: Session) -> None:
    wb, _ = _seed_wb_and_session(db_session)
    base = datetime(2026, 4, 1, tzinfo=UTC)
    ids: list = []
    for delta in (0, 7, 14):
        sess = MonitoringSession(
            water_body_id=wb.id,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 5, 1),
            max_cloud_cover=30.0,
            status=SessionStatus.COMPLETE,
            scene_capture_date=base + timedelta(days=delta),
            scene_id=f"S2A_TEST_{delta}",
            scene_cloud_cover=10.0 + delta,
        )
        db_session.add(sess)
        db_session.commit()
        db_session.refresh(sess)
        ids.append(sess.id)
        db_session.add(
            RiskAssessment(
                session_id=sess.id,
                score=0.2 + delta * 0.02,
                level=RiskLevel.LOW if delta < 14 else RiskLevel.MEDIUM,
                urgency=Urgency.ROUTINE,
                recommendation="r",
                reasoning="g",
                limitations="l",
                contributors={},
            )
        )
        db_session.add(
            SpectralIndex(
                session_id=sess.id,
                name=IndexName.NDCI,
                value=0.10 + delta * 0.01,
                min_value=0.05,
                max_value=0.30,
                stddev=0.02,
                sample_count=128,
                interpretation="x",
                bands=["B05", "B04"],
            )
        )
        db_session.commit()

    history = history_tools.get_session_history(db=db_session, water_body_id=wb.id)
    capture_dates = [rec["scene_capture_date"] for rec in history["sessions"]]
    assert capture_dates == sorted(capture_dates, reverse=True)
    # Risk and indices joined in.
    assert history["sessions"][0]["risk"]["score"] is not None
    assert history["sessions"][0]["indices"][0]["name"] == "NDCI"


def test_compute_trend_positive_slope_on_rising_ndci() -> None:
    base = datetime(2026, 4, 1, tzinfo=UTC)
    sessions = [
        {
            "scene_capture_date": (base + timedelta(days=d)).isoformat(),
            "indices": [{"name": "NDCI", "value": 0.10 + d * 0.005}],
            "risk": None,
        }
        for d in (0, 14, 28, 42)
    ]
    out = history_tools.compute_trend(metric="NDCI", sessions=sessions)
    assert out["n"] == 4
    assert out["slope_per_day"] > 0
    assert out["first"] < out["last"]


def test_compute_trend_handles_too_few_points() -> None:
    out = history_tools.compute_trend(metric="NDCI", sessions=[])
    assert out["n"] == 0
    assert out["slope_per_day"] is None


def test_compute_trend_unknown_metric_yields_no_points() -> None:
    sessions = [
        {
            "scene_capture_date": "2026-04-01T00:00:00+00:00",
            "indices": [{"name": "NDCI", "value": 0.2}],
            "risk": {"score": 0.4, "level": "low", "urgency": "routine"},
        }
    ]
    out = history_tools.compute_trend(metric="NOT_AN_INDEX", sessions=sessions)
    assert out["n"] == 0
    assert out["slope_per_day"] is None


def test_compute_trend_supports_risk_score_alias() -> None:
    base = datetime(2026, 4, 1, tzinfo=UTC)
    sessions = [
        {
            "scene_capture_date": (base + timedelta(days=d)).isoformat(),
            "indices": [],
            "risk": {"score": 0.1 + d * 0.01, "level": "low", "urgency": "routine"},
        }
        for d in (0, 10, 20)
    ]
    out = history_tools.compute_trend(metric="risk_score", sessions=sessions)
    assert out["n"] == 3
    assert out["slope_per_day"] > 0


# ----------------------------------------------------------------------
# STAC tools — stubbed STAC client
# ----------------------------------------------------------------------


class _FakeSearch:
    def __init__(self, items: list) -> None:
        self._items = items

    def items(self):
        return iter(self._items)


class _FakeClient:
    def __init__(self, items: list) -> None:
        self._items = items

    def search(self, **_):
        return _FakeSearch(self._items)


def _fake_stac_item(scene_id: str, cloud: float, when: datetime) -> SimpleNamespace:
    """A minimal SimpleNamespace shaped like a signed pystac Item."""
    return SimpleNamespace(
        id=scene_id,
        datetime=when,
        properties={
            "datetime": when.isoformat(),
            "eo:cloud_cover": cloud,
            "platform": "sentinel-2a",
            "s2:mgrs_tile": "32TNS",
        },
        assets={
            "rendered_preview": SimpleNamespace(href=f"https://example.test/preview/{scene_id}.png")
        },
    )


def test_list_recent_scenes_returns_candidates(monkeypatch) -> None:
    items = [
        _fake_stac_item("S2A_A", 12.0, datetime(2026, 5, 12, tzinfo=UTC)),
        _fake_stac_item("S2A_B", 8.0, datetime(2026, 5, 9, tzinfo=UTC)),
    ]
    # Bypass STAC client construction entirely.
    monkeypatch.setattr(stac_tools, "_client", lambda: _FakeClient(items))
    # Bypass URL signing — return the item unchanged so the test asset
    # URL flows through.
    monkeypatch.setattr(stac_tools.planetary_computer, "sign", lambda item: item)

    result = stac_tools.list_recent_scenes(
        aoi_geojson={
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        },
        start_date="2026-05-01",
        end_date="2026-05-16",
        max_cloud_cover=30.0,
    )

    assert len(result["candidates"]) == 2
    first = result["candidates"][0]
    assert first["scene_id"] == "S2A_A"
    assert first["thumbnail_url"].endswith("S2A_A.png")
    assert "stac_link" in first


def test_list_recent_scenes_rejects_inverted_window(monkeypatch) -> None:
    monkeypatch.setattr(stac_tools, "_client", lambda: _FakeClient([]))
    result = stac_tools.list_recent_scenes(
        aoi_geojson={"type": "Polygon", "coordinates": [[[0, 0]]]},
        start_date="2026-05-16",
        end_date="2026-05-01",
        max_cloud_cover=30.0,
    )
    assert result["candidates"] == []
    assert "after" in result["reason"]


def test_inspect_scene_returns_not_found_when_empty(monkeypatch) -> None:
    monkeypatch.setattr(stac_tools, "_client", lambda: _FakeClient([]))
    out = stac_tools.inspect_scene(scene_id=str(uuid4()))
    assert "error" in out
