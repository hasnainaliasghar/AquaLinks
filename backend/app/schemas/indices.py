"""Spectral index response schema."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.spectral_index import IndexName


class SpectralIndexRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    name: IndexName
    value: float
    min_value: float | None
    max_value: float | None
    stddev: float | None
    interpretation: str | None
    bands: list[str]
    sample_count: int | None
    extra: dict[str, Any] | None
    created_at: datetime
