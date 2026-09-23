"""Water body geometry record."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Column, String
from sqlmodel import Field, SQLModel

from app.models.base import IDMixin, TimestampMixin


class WaterBody(IDMixin, TimestampMixin, SQLModel, table=True):
    """A named area of interest (lake, river, reservoir, custom polygon).

    Geometry is stored as a GeoJSON ``Polygon`` document. For deployments
    with PostGIS enabled the polygon is duplicated into a typed column
    via a database trigger declared in the migration; queries that need
    spatial ops use the typed column, while application code reads the
    GeoJSON.
    """

    __tablename__ = "water_bodies"

    name: str = Field(sa_column=Column(String(160), nullable=False, index=True))
    description: str | None = Field(default=None, sa_column=Column(String(1000)))
    geometry: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    centroid: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    area_km2: float | None = Field(default=None)
    source: str | None = Field(
        default=None,
        sa_column=Column(String(80)),
        description="Origin of the polygon (user_drawn, osm, custom_import).",
    )
