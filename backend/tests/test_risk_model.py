"""Tests for the deterministic risk model."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.models.evidence import FieldEvidence, Odor, WaterColor
from app.models.risk_assessment import RiskLevel, Urgency
from app.models.spectral_index import IndexName
from app.services.indices import IndexAggregate
from app.services.risk_model import score_risk


def _agg(name: IndexName, value: float) -> IndexAggregate:
    return IndexAggregate(
        name=name,
        value=value,
        min_value=value,
        max_value=value,
        stddev=0.0,
        sample_count=100,
        interpretation="test",
        bands=["b1"],
    )


def test_clean_water_yields_low_risk():
    indices = [
        _agg(IndexName.NDWI, 0.45),
        _agg(IndexName.MNDWI, 0.40),
        _agg(IndexName.NDTI, -0.05),
        _agg(IndexName.NDCI, -0.05),
        _agg(IndexName.NDVI, 0.0),
        _agg(IndexName.WRI, 2.6),
    ]
    score = score_risk(indices)
    assert score.level is RiskLevel.LOW
    assert score.urgency is Urgency.ROUTINE
    assert 0.0 <= score.score <= 1.0


def test_bloom_indices_push_to_high_risk():
    indices = [
        _agg(IndexName.NDWI, 0.20),
        _agg(IndexName.MNDWI, 0.20),
        _agg(IndexName.NDTI, 0.45),
        _agg(IndexName.NDCI, 0.40),
        _agg(IndexName.NDVI, 0.45),
        _agg(IndexName.WRI, 1.2),
    ]
    score = score_risk(indices)
    assert score.level in (RiskLevel.MEDIUM, RiskLevel.HIGH)
    assert score.score > 0.4


def test_field_evidence_increases_risk_score():
    indices = [
        _agg(IndexName.NDWI, 0.30),
        _agg(IndexName.MNDWI, 0.30),
        _agg(IndexName.NDTI, 0.15),
        _agg(IndexName.NDCI, 0.10),
        _agg(IndexName.NDVI, 0.10),
        _agg(IndexName.WRI, 1.8),
    ]
    baseline = score_risk(indices)
    evidence = FieldEvidence(
        id=uuid4(),
        session_id=uuid4(),
        water_color=WaterColor.GREEN,
        odor=Odor.ROTTEN,
        algae_present=True,
        dead_fish_count=6,
        rainfall_mm=25.0,
        complaints_count=2,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    bumped = score_risk(indices, [evidence])
    assert bumped.score > baseline.score
    assert bumped.urgency in (Urgency.ELEVATED, Urgency.IMMEDIATE)


def test_score_is_clamped_between_zero_and_one():
    extreme_indices = [
        _agg(IndexName.NDWI, -1.0),
        _agg(IndexName.MNDWI, -1.0),
        _agg(IndexName.NDTI, 1.0),
        _agg(IndexName.NDCI, 1.0),
        _agg(IndexName.NDVI, 1.0),
        _agg(IndexName.WRI, 0.0),
    ]
    evidence = [
        FieldEvidence(
            id=uuid4(),
            session_id=uuid4(),
            water_color=WaterColor.BLACK,
            odor=Odor.CHEMICAL,
            algae_present=True,
            dead_fish_count=50,
            rainfall_mm=200.0,
            complaints_count=100,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    ]
    score = score_risk(extreme_indices, evidence)
    assert 0.0 <= score.score <= 1.0
    assert score.level is RiskLevel.HIGH
