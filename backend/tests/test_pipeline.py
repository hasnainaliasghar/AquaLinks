"""End-to-end pipeline test using the sample satellite provider."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from app.core.database import get_engine
from app.models.evidence import FieldEvidence, Odor, WaterColor
from app.models.report import Report
from app.models.risk_assessment import RiskAssessment
from app.models.session import MonitoringSession, SessionStatus
from app.models.spectral_index import SpectralIndex
from app.models.water_body import WaterBody
from app.services.pipeline import rescore_with_new_evidence, run_full
from app.utils.geo import area_km2, centroid_geojson


def _seed_water_body(db: Session, sample_polygon: dict) -> WaterBody:
    wb = WaterBody(
        name="Test Lake",
        description=None,
        geometry=sample_polygon,
        centroid=centroid_geojson(sample_polygon),
        area_km2=area_km2(sample_polygon),
        source="test",
    )
    db.add(wb)
    db.commit()
    db.refresh(wb)
    return wb


def _seed_session(db: Session, wb: WaterBody) -> MonitoringSession:
    sess = MonitoringSession(
        water_body_id=wb.id,
        start_date=date.today() - timedelta(days=14),
        end_date=date.today(),
        max_cloud_cover=30.0,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def test_run_full_creates_indices_risk_and_report(db_engine, sample_polygon):
    with Session(get_engine()) as db:
        wb = _seed_water_body(db, sample_polygon)
        sess = _seed_session(db, wb)
        session_id: UUID = sess.id

    run_full(session_id)

    with Session(get_engine()) as db:
        refreshed = db.get(MonitoringSession, session_id)
        assert refreshed is not None
        assert refreshed.status is SessionStatus.COMPLETE
        assert refreshed.scene_id is not None
        assert refreshed.scene_provider == "aqualens-sample"

        indices = db.query(SpectralIndex).filter(SpectralIndex.session_id == session_id).all()
        assert len(indices) == 6

        risk = db.query(RiskAssessment).filter(RiskAssessment.session_id == session_id).one()
        assert risk.recommendation
        assert risk.reasoning
        assert risk.limitations

        report = db.query(Report).filter(Report.session_id == session_id).one()
        assert Path(report.file_path).exists()
        assert report.byte_size > 0
        assert Path(report.file_path).read_bytes().startswith(b"%PDF")


def test_rescore_uses_new_evidence(db_engine, sample_polygon):
    with Session(get_engine()) as db:
        wb = _seed_water_body(db, sample_polygon)
        sess = _seed_session(db, wb)
        session_id = sess.id

    run_full(session_id)

    with Session(get_engine()) as db:
        baseline = db.query(RiskAssessment).filter(RiskAssessment.session_id == session_id).one()
        baseline_score = baseline.score

        # Add severe evidence.
        ev = FieldEvidence(
            session_id=session_id,
            water_color=WaterColor.GREEN,
            odor=Odor.ROTTEN,
            algae_present=True,
            dead_fish_count=12,
            rainfall_mm=18.0,
            complaints_count=4,
        )
        db.add(ev)
        db.commit()

    rescore_with_new_evidence(session_id)

    with Session(get_engine()) as db:
        updated = db.query(RiskAssessment).filter(RiskAssessment.session_id == session_id).one()
        assert updated.score >= baseline_score
