"""Monitoring session endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.database import get_session
from app.core.tasks import InProcessJobRunner
from app.models.agent_trace import AgentTrace
from app.models.evidence import FieldEvidence
from app.models.report import Report
from app.models.risk_assessment import RiskAssessment
from app.models.session import MonitoringSession, SessionStatus
from app.models.spectral_index import SpectralIndex
from app.models.water_body import WaterBody
from app.schemas.agent_trace import AgentTraceRead
from app.schemas.evidence import EvidenceRead
from app.schemas.field_brief import FieldBrief
from app.schemas.indices import SpectralIndexRead
from app.schemas.risk import RiskAssessmentRead
from app.schemas.session import (
    CitizenSummaryRead,
    SessionCreate,
    SessionDetailRead,
    SessionListItem,
)
from app.schemas.water_body import WaterBodyRead
from app.services.citizen_summary import build_citizen_summary
from app.services.pipeline import run_full
from app.utils.geo import area_km2, centroid_geojson

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _resolve_water_body(payload: SessionCreate, db: Session) -> WaterBody:
    if payload.water_body_id is not None:
        wb = db.get(WaterBody, payload.water_body_id)
        if wb is None:
            raise HTTPException(status_code=404, detail="Water body not found")
        return wb

    assert payload.new_water_body is not None
    geometry = payload.new_water_body.geometry.model_dump()
    wb = WaterBody(
        name=payload.new_water_body.name,
        description=payload.new_water_body.description,
        geometry=geometry,
        centroid=centroid_geojson(geometry),
        area_km2=area_km2(geometry),
        source=payload.new_water_body.source,
    )
    db.add(wb)
    db.commit()
    db.refresh(wb)
    return wb


def _default_window() -> tuple[date, date]:
    settings = get_settings()
    end = date.today()
    start = end - timedelta(days=settings.default_lookback_days)
    return start, end


def _centroid_lat_lng(centroid: dict[str, object] | None) -> tuple[float | None, float | None]:
    if not isinstance(centroid, dict):
        return None, None
    raw = centroid.get("coordinates")
    if not isinstance(raw, list | tuple) or len(raw) < 2:
        return None, None
    lon, lat = raw[0], raw[1]
    if not isinstance(lon, int | float) or not isinstance(lat, int | float):
        return None, None
    return float(lat), float(lon)


@router.post(
    "",
    response_model=SessionDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    payload: SessionCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_session),
) -> SessionDetailRead:
    wb = _resolve_water_body(payload, db)

    default_start, default_end = _default_window()
    start_date = payload.start_date or default_start
    end_date = payload.end_date or default_end
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")

    sess = MonitoringSession(
        water_body_id=wb.id,
        start_date=start_date,
        end_date=end_date,
        max_cloud_cover=payload.max_cloud_cover,
        status=SessionStatus.PENDING,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)

    runner = InProcessJobRunner(background)
    runner.enqueue(run_full, sess.id)

    return _build_detail(db, sess, wb, [], [], None, None)


@router.get("", response_model=list[SessionListItem])
def list_sessions(
    db: Session = Depends(get_session),
    water_body_id: UUID | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[SessionListItem]:
    statement = (
        select(MonitoringSession, WaterBody, RiskAssessment)
        .join(WaterBody, MonitoringSession.water_body_id == WaterBody.id)
        .outerjoin(RiskAssessment, RiskAssessment.session_id == MonitoringSession.id)
        .order_by(MonitoringSession.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if water_body_id is not None:
        statement = statement.where(MonitoringSession.water_body_id == water_body_id)

    rows = db.exec(statement).all()
    items: list[SessionListItem] = []
    for sess, wb, risk in rows:
        lat, lng = _centroid_lat_lng(wb.centroid)
        items.append(
            SessionListItem(
                id=sess.id,
                water_body_id=sess.water_body_id,
                water_body_name=wb.name,
                water_body_latitude=lat,
                water_body_longitude=lng,
                start_date=sess.start_date,
                end_date=sess.end_date,
                status=sess.status,
                risk_level=risk.level.value if risk else None,
                risk_score=risk.score if risk else None,
                scene_capture_date=sess.scene_capture_date,
                created_at=sess.created_at,
                updated_at=sess.updated_at,
            )
        )
    return items


@router.get("/{session_id}", response_model=SessionDetailRead)
def get_session_detail(session_id: UUID, db: Session = Depends(get_session)) -> SessionDetailRead:
    sess = db.get(MonitoringSession, session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")
    wb = db.get(WaterBody, sess.water_body_id)
    if wb is None:
        raise HTTPException(status_code=500, detail="Session has no water body")

    indices = list(
        db.exec(
            select(SpectralIndex)
            .where(SpectralIndex.session_id == sess.id)
            .order_by(SpectralIndex.name)
        )
    )
    evidence = list(
        db.exec(
            select(FieldEvidence)
            .where(FieldEvidence.session_id == sess.id)
            .order_by(FieldEvidence.created_at.desc())
        )
    )
    risk = db.exec(select(RiskAssessment).where(RiskAssessment.session_id == sess.id)).one_or_none()
    report = db.exec(select(Report).where(Report.session_id == sess.id)).one_or_none()

    return _build_detail(db, sess, wb, indices, evidence, risk, report)


@router.get("/{session_id}/indices", response_model=list[SpectralIndexRead])
def list_indices(session_id: UUID, db: Session = Depends(get_session)) -> list[SpectralIndex]:
    rows = list(
        db.exec(
            select(SpectralIndex)
            .where(SpectralIndex.session_id == session_id)
            .order_by(SpectralIndex.name)
        )
    )
    return rows


@router.get("/{session_id}/risk", response_model=RiskAssessmentRead | None)
def get_risk(session_id: UUID, db: Session = Depends(get_session)) -> RiskAssessment | None:
    return db.exec(
        select(RiskAssessment).where(RiskAssessment.session_id == session_id)
    ).one_or_none()


@router.get("/{session_id}/trace", response_model=AgentTraceRead)
def get_agent_trace(session_id: UUID, db: Session = Depends(get_session)) -> AgentTrace:
    """Return the multi-agent execution trace for this session.

    404 when the session pre-dates the agent layer or was processed
    with ``AQUALENS_AGENTIC_MODE=false`` / ``AQUALENS_FAKE_GEMINI=1``.
    """
    trace = db.exec(select(AgentTrace).where(AgentTrace.session_id == session_id)).one_or_none()
    if trace is None:
        raise HTTPException(status_code=404, detail="No agent trace for this session")
    return trace


@router.get("/{session_id}/field-brief", response_model=FieldBrief)
def get_field_brief(session_id: UUID, db: Session = Depends(get_session)) -> FieldBrief:
    """Return the Field Liaison's structured action plan (legacy).

    404 when the session has no legacy FieldBrief payload.
    """
    risk = db.exec(
        select(RiskAssessment).where(RiskAssessment.session_id == session_id)
    ).one_or_none()
    if risk is None or not risk.field_brief:
        raise HTTPException(status_code=404, detail="No field brief for this session")
    try:
        return FieldBrief.model_validate(risk.field_brief)
    except Exception:
        # The legacy JSON column now stores Reporter payloads for new
        # runs, so this compatibility endpoint should gracefully return
        # 404 when the row no longer contains a FieldBrief shape.
        raise HTTPException(status_code=404, detail="No field brief for this session") from None


def _build_detail(
    db: Session,
    sess: MonitoringSession,
    wb: WaterBody,
    indices: list[SpectralIndex],
    evidence: list[FieldEvidence],
    risk: RiskAssessment | None,
    report: Report | None,
) -> SessionDetailRead:
    risk_read = RiskAssessmentRead.model_validate(risk) if risk else None
    summary = build_citizen_summary(
        risk=risk_read,
        aoi_type=sess.aoi_type,
        water_fraction=sess.water_fraction,
        evidence_count=len(evidence),
        reporter_payload=risk.field_brief if risk else None,
    )
    return SessionDetailRead(
        id=sess.id,
        water_body=WaterBodyRead.model_validate(wb),
        start_date=sess.start_date,
        end_date=sess.end_date,
        max_cloud_cover=sess.max_cloud_cover,
        status=sess.status,
        status_message=sess.status_message,
        scene_id=sess.scene_id,
        scene_capture_date=sess.scene_capture_date,
        scene_cloud_cover=sess.scene_cloud_cover,
        scene_provider=sess.scene_provider,
        scene_thumbnail_url=sess.scene_thumbnail_url,
        scene_metadata=sess.scene_metadata,
        water_fraction=sess.water_fraction,
        aoi_type=sess.aoi_type,
        indices=[SpectralIndexRead.model_validate(idx) for idx in indices],
        evidence=[EvidenceRead.model_validate(ev) for ev in evidence],
        risk=risk_read,
        citizen_summary=CitizenSummaryRead(**summary.model_dump()) if summary else None,
        report_id=report.id if report else None,
        created_at=sess.created_at,
        updated_at=sess.updated_at,
    )
