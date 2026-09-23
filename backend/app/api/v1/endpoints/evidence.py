"""Field evidence endpoints."""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.tasks import InProcessJobRunner
from app.models.evidence import FieldEvidence, Odor, WaterColor
from app.models.session import MonitoringSession
from app.schemas.evidence import EvidenceCreate, EvidenceRead
from app.services.evidence_handler import save_photo
from app.services.pipeline import rescore_with_new_evidence

router = APIRouter(prefix="/sessions/{session_id}/evidence", tags=["evidence"])


def _parse_payload(payload_json: str | None, fields: dict[str, str | None]) -> EvidenceCreate:
    """Accept either a JSON blob or discrete form fields."""
    if payload_json:
        try:
            data = json.loads(payload_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid JSON: {exc}") from exc
    else:
        data = {k: v for k, v in fields.items() if v is not None and v != ""}
    try:
        return EvidenceCreate.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


@router.post(
    "",
    response_model=EvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
async def submit_evidence(
    session_id: UUID,
    background: BackgroundTasks,
    db: Session = Depends(get_session),
    payload: str | None = Form(default=None),
    water_color: WaterColor | None = Form(default=None),
    odor: Odor | None = Form(default=None),
    algae_present: bool = Form(default=False),
    dead_fish_count: int = Form(default=0),
    rainfall_mm: float = Form(default=0.0),
    complaints_count: int = Form(default=0),
    notes: str | None = Form(default=None),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    reporter_name: str | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
) -> FieldEvidence:
    sess = db.get(MonitoringSession, session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")

    parsed = _parse_payload(
        payload,
        {
            "water_color": water_color.value if water_color else None,
            "odor": odor.value if odor else None,
            "algae_present": str(algae_present).lower(),
            "dead_fish_count": str(dead_fish_count),
            "rainfall_mm": str(rainfall_mm),
            "complaints_count": str(complaints_count),
            "notes": notes,
            "latitude": str(latitude) if latitude is not None else None,
            "longitude": str(longitude) if longitude is not None else None,
            "reporter_name": reporter_name,
        },
    )

    photo_url: str | None = None
    if photo is not None:
        try:
            photo_url = save_photo(str(session_id), photo)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    record = FieldEvidence(
        session_id=session_id,
        water_color=parsed.water_color,
        odor=parsed.odor,
        algae_present=parsed.algae_present,
        dead_fish_count=parsed.dead_fish_count,
        rainfall_mm=parsed.rainfall_mm,
        complaints_count=parsed.complaints_count,
        notes=parsed.notes,
        latitude=parsed.latitude,
        longitude=parsed.longitude,
        reporter_name=parsed.reporter_name,
        photo_url=photo_url,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    runner = InProcessJobRunner(background)
    runner.enqueue(rescore_with_new_evidence, session_id)

    return record


@router.get("", response_model=list[EvidenceRead])
def list_evidence(session_id: UUID, db: Session = Depends(get_session)) -> list[FieldEvidence]:
    rows = list(
        db.exec(
            select(FieldEvidence)
            .where(FieldEvidence.session_id == session_id)
            .order_by(FieldEvidence.created_at.desc())
        )
    )
    return rows
