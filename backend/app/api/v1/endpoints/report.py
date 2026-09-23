"""Report download endpoint.

The PDF is rebuilt from the persisted session data on every request. This
costs ~1s of WeasyPrint render time but guarantees the user sees the
latest template — including layout fixes shipped after the session was
first analysed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.logging import get_logger
from app.models.evidence import FieldEvidence
from app.models.report import Report
from app.models.risk_assessment import RiskAssessment
from app.models.session import MonitoringSession
from app.models.spectral_index import SpectralIndex
from app.models.water_body import WaterBody
from app.services.report_generator import (
    persist_report,
    render_report_html,
    render_report_pdf,
)

LOGGER = get_logger(__name__)

router = APIRouter(prefix="/sessions/{session_id}/report", tags=["reports"])


@router.get("", response_class=FileResponse)
def get_report(session_id: UUID, db: Session = Depends(get_session)) -> FileResponse:
    sess = db.get(MonitoringSession, session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")

    water_body = db.get(WaterBody, sess.water_body_id)
    if water_body is None:
        raise HTTPException(status_code=500, detail="Session has no water body")

    indices = list(
        db.exec(
            select(SpectralIndex)
            .where(SpectralIndex.session_id == sess.id)
            .order_by(SpectralIndex.name)
        ).all()
    )
    if not indices:
        raise HTTPException(status_code=404, detail="Report data is not ready yet")

    risk = db.exec(select(RiskAssessment).where(RiskAssessment.session_id == sess.id)).one_or_none()
    if risk is None:
        raise HTTPException(status_code=404, detail="Risk assessment is not ready yet")

    evidence = list(
        db.exec(
            select(FieldEvidence)
            .where(FieldEvidence.session_id == sess.id)
            .order_by(FieldEvidence.created_at.desc())
        ).all()
    )

    # Rebuild every time — render cost is low enough for on-demand usage and
    # avoids serving stale layouts once the template has been updated.
    html = render_report_html(
        session=sess,
        water_body=water_body,
        indices=indices,
        evidence=evidence,
        risk=risk,
    )
    pdf_bytes = render_report_pdf(html)
    report: Report = persist_report(db, session=sess, pdf_bytes=pdf_bytes)
    LOGGER.info("Rendered report on demand for session %s (%d bytes)", sess.id, len(pdf_bytes))

    path = Path(report.file_path)
    if not path.exists():
        raise HTTPException(status_code=500, detail="Report file failed to write")

    date_tag = datetime.now(UTC).strftime("%Y%m%d")
    return FileResponse(
        path=path,
        media_type=report.content_type,
        filename=f"aqualinks-analysis-{date_tag}.pdf",
        headers={"Cache-Control": "no-store, max-age=0, must-revalidate"},
    )
