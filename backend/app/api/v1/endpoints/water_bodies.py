"""Water body endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.water_body import WaterBody
from app.schemas.water_body import (
    WaterBodyBulkDelete,
    WaterBodyBulkDeleteResult,
    WaterBodyCreate,
    WaterBodyRead,
    WaterBodyUpdate,
)
from app.utils.geo import area_km2, centroid_geojson

router = APIRouter(prefix="/water-bodies", tags=["water-bodies"])


@router.get("", response_model=list[WaterBodyRead])
def list_water_bodies(
    db: Session = Depends(get_session),
    limit: int = 50,
    offset: int = 0,
) -> list[WaterBody]:
    statement = select(WaterBody).order_by(WaterBody.created_at.desc()).offset(offset).limit(limit)
    return list(db.exec(statement).all())


@router.post(
    "",
    response_model=WaterBodyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_water_body(payload: WaterBodyCreate, db: Session = Depends(get_session)) -> WaterBody:
    geometry = payload.geometry.model_dump()
    wb = WaterBody(
        name=payload.name,
        description=payload.description,
        geometry=geometry,
        centroid=centroid_geojson(geometry),
        area_km2=area_km2(geometry),
        source=payload.source or "user_drawn",
    )
    db.add(wb)
    db.commit()
    db.refresh(wb)
    return wb


@router.get("/{water_body_id}", response_model=WaterBodyRead)
def get_water_body(water_body_id: UUID, db: Session = Depends(get_session)) -> WaterBody:
    wb = db.get(WaterBody, water_body_id)
    if wb is None:
        raise HTTPException(status_code=404, detail="Water body not found")
    return wb


@router.patch("/{water_body_id}", response_model=WaterBodyRead)
def update_water_body(
    water_body_id: UUID,
    payload: WaterBodyUpdate,
    db: Session = Depends(get_session),
) -> WaterBody:
    wb = db.get(WaterBody, water_body_id)
    if wb is None:
        raise HTTPException(status_code=404, detail="Water body not found")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return wb

    if "name" in data and data["name"] is not None:
        wb.name = data["name"]
    if "description" in data:
        wb.description = data["description"]

    db.add(wb)
    db.commit()
    db.refresh(wb)
    return wb


@router.delete(
    "/{water_body_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    response_class=Response,
)
def delete_water_body(water_body_id: UUID, db: Session = Depends(get_session)) -> Response:
    """Delete a water body and (via FK cascade) all of its sessions, indices,
    field evidence, risk assessments, and reports.

    The cascade is enforced at the database level by the ``ON DELETE CASCADE``
    foreign keys declared in the initial migration; SQLAlchemy issues a single
    DELETE for the parent row.
    """
    wb = db.get(WaterBody, water_body_id)
    if wb is None:
        raise HTTPException(status_code=404, detail="Water body not found")
    db.delete(wb)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bulk-delete", response_model=WaterBodyBulkDeleteResult)
def bulk_delete_water_bodies(
    payload: WaterBodyBulkDelete, db: Session = Depends(get_session)
) -> WaterBodyBulkDeleteResult:
    """Delete many water bodies in a single transaction.

    Behavior is intentionally all-or-nothing: if any requested id does
    not exist, nothing is deleted and the endpoint returns 404 with the
    missing ids in the error payload.
    """
    requested_count = len(payload.ids)
    unique_ids = list(dict.fromkeys(payload.ids))
    rows = list(db.exec(select(WaterBody).where(WaterBody.id.in_(unique_ids))).all())
    found_ids = {row.id for row in rows}
    missing_ids = [str(wb_id) for wb_id in unique_ids if wb_id not in found_ids]
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "One or more water bodies were not found; no rows were deleted.",
                "missing_ids": missing_ids,
            },
        )

    for row in rows:
        db.delete(row)
    db.commit()
    return WaterBodyBulkDeleteResult(
        requested_count=requested_count,
        deleted_count=len(rows),
    )
