"""Satellite provider protocol and shared types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol

import numpy as np


class SatelliteError(Exception):
    """Base class for satellite retrieval errors."""


class SceneNotFoundError(SatelliteError):
    """Raised when no usable scene is available for the given query."""


@dataclass(slots=True)
class BandStack:
    """A stack of Sentinel-2-compatible bands clipped to the AOI.

    Each array has the same 2-D shape ``(rows, cols)`` and represents
    surface reflectance scaled to ``[0, 1]``. The water/no-data mask
    flags pixels that should be ignored when computing indices.
    """

    blue: np.ndarray
    green: np.ndarray
    red: np.ndarray
    red_edge: np.ndarray
    nir: np.ndarray
    swir: np.ndarray
    valid_mask: np.ndarray

    def shape(self) -> tuple[int, int]:
        return self.green.shape  # type: ignore[return-value]


@dataclass(slots=True)
class ImageryBundle:
    """The output of a successful satellite retrieval."""

    bands: BandStack
    scene_id: str
    capture_date: datetime
    cloud_cover: float
    provider: str
    thumbnail_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SatelliteProvider(Protocol):
    """Discovers and reads imagery for an AOI."""

    name: str

    def fetch(
        self,
        *,
        geometry: dict[str, Any],
        start_date: date,
        end_date: date,
        max_cloud_cover: float,
    ) -> ImageryBundle: ...
