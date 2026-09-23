"""Water body request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GeoJSONPolygon(BaseModel):
    """Minimal GeoJSON polygon validator.

    Accepts a single-ring polygon with longitude/latitude pairs. The
    first and last vertex must be equal to close the ring.
    """

    type: str = Field(..., pattern="^Polygon$")
    coordinates: list[list[list[float]]]

    @field_validator("coordinates")
    @classmethod
    def _validate_ring(cls, value: list[list[list[float]]]) -> list[list[list[float]]]:
        if not value or not value[0]:
            raise ValueError("polygon must have at least one ring with vertices")
        ring = value[0]
        if len(ring) < 4:
            raise ValueError("polygon ring must have at least 4 positions (3 unique + closure)")
        if ring[0] != ring[-1]:
            raise ValueError("polygon ring must be closed (first and last vertex equal)")
        for vertex in ring:
            if len(vertex) < 2:
                raise ValueError("each vertex must be [lon, lat]")
            lon, lat = vertex[0], vertex[1]
            if not -180 <= lon <= 180:
                raise ValueError(f"longitude out of range: {lon}")
            if not -90 <= lat <= 90:
                raise ValueError(f"latitude out of range: {lat}")
        return value


class WaterBodyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    geometry: GeoJSONPolygon
    source: str | None = Field(default=None, max_length=80)


class WaterBodyUpdate(BaseModel):
    """Partial update — only fields present are applied."""

    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)


class WaterBodyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    geometry: dict[str, Any]
    centroid: dict[str, Any] | None
    area_km2: float | None
    source: str | None
    created_at: datetime
    updated_at: datetime


class WaterBodyBulkDelete(BaseModel):
    """Transactional bulk-delete payload for water bodies."""

    ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Water body ids to delete in one transaction.",
    )


class WaterBodyBulkDeleteResult(BaseModel):
    """Bulk-delete result summary returned to the UI."""

    requested_count: int
    deleted_count: int
