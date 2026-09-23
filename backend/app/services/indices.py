"""Spectral index band math.

Each ``compute_*`` function is a pure function over numpy arrays. The
formulas follow the standard remote-sensing definitions documented in
``docs/spectral_indices.md``. Division-by-zero is guarded by replacing
zero denominators with NaN so downstream aggregation can mask them out.

The :func:`aggregate_indices` helper computes the masked-mean,
standard deviation, min, and max for one index across the water area
defined by the NDWI water mask.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.models.spectral_index import IndexName
from app.services.satellite.base import BandStack


def _safe_div(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    den_safe = np.where(np.abs(den) < 1e-9, np.nan, den)
    return num / den_safe


def compute_ndwi(stack: BandStack) -> np.ndarray:
    """NDWI = (NIR - SWIR) / (NIR + SWIR)."""
    return _safe_div(stack.nir - stack.swir, stack.nir + stack.swir)


def compute_mndwi(stack: BandStack) -> np.ndarray:
    """MNDWI = (Green - SWIR) / (Green + SWIR)."""
    return _safe_div(stack.green - stack.swir, stack.green + stack.swir)


def compute_ndti(stack: BandStack) -> np.ndarray:
    """NDTI = (Red - Green) / (Red + Green)."""
    return _safe_div(stack.red - stack.green, stack.red + stack.green)


def compute_ndci(stack: BandStack) -> np.ndarray:
    """NDCI = (RedEdge - Red) / (RedEdge + Red)."""
    return _safe_div(stack.red_edge - stack.red, stack.red_edge + stack.red)


def compute_ndvi(stack: BandStack) -> np.ndarray:
    """NDVI = (NIR - Red) / (NIR + Red)."""
    return _safe_div(stack.nir - stack.red, stack.nir + stack.red)


def compute_wri(stack: BandStack) -> np.ndarray:
    """WRI = (Green + Red) / (NIR + SWIR)."""
    return _safe_div(stack.green + stack.red, stack.nir + stack.swir)


@dataclass(slots=True, frozen=True)
class IndexAggregate:
    """Aggregated statistics for one index across the water mask."""

    name: IndexName
    value: float
    min_value: float
    max_value: float
    stddev: float
    sample_count: int
    interpretation: str
    bands: list[str]


_BAND_MAP: dict[IndexName, list[str]] = {
    IndexName.NDWI: ["B08 (NIR)", "B11 (SWIR)"],
    IndexName.MNDWI: ["B03 (Green)", "B11 (SWIR)"],
    IndexName.NDTI: ["B04 (Red)", "B03 (Green)"],
    IndexName.NDCI: ["B05 (Red Edge)", "B04 (Red)"],
    IndexName.NDVI: ["B08 (NIR)", "B04 (Red)"],
    IndexName.WRI: ["B03 (Green)", "B04 (Red)", "B08 (NIR)", "B11 (SWIR)"],
}


def water_mask(
    stack: BandStack,
    ndwi_threshold: float = 0.0,
    mndwi_threshold: float = 0.0,
) -> np.ndarray:
    """Boolean mask for likely-water pixels.

    Combines NDWI **and** MNDWI rather than relying on NDWI alone. NDWI
    above zero is a known false positive over vegetation: plants reflect
    NIR strongly, which inflates ``(NIR - SWIR) / (NIR + SWIR)``. MNDWI
    swaps NIR for Green, so it stays *negative* over vegetation while
    remaining positive over real water — requiring both indices to agree
    filters out forests, wet fields, and floodplain margins that fooled
    the NDWI-only mask.

    Reference: Xu, H. (2006). "Modification of normalised difference
    water index (NDWI) to enhance open water features in remotely sensed
    imagery." International Journal of Remote Sensing, 27(14), 3025–3033.
    """
    ndwi = compute_ndwi(stack)
    mndwi = compute_mndwi(stack)
    return (
        stack.valid_mask
        & np.isfinite(ndwi)
        & np.isfinite(mndwi)
        & (ndwi > ndwi_threshold)
        & (mndwi > mndwi_threshold)
    )


def _interpret(name: IndexName, value: float) -> str:
    match name:
        case IndexName.NDWI:
            if value > 0.3:
                return "clear open water"
            if value > 0.0:
                return "water present, possibly turbid or mixed"
            return "land-dominated; little open water"
        case IndexName.MNDWI:
            if value > 0.3:
                return "strong water signal even in urban context"
            if value > 0.0:
                return "water present; some confusion with built-up surfaces possible"
            return "non-water dominant"
        case IndexName.NDTI:
            if value > 0.4:
                return "high turbidity"
            if value > 0.2:
                return "elevated turbidity"
            if value > 0.0:
                return "moderate clarity"
            return "low turbidity"
        case IndexName.NDCI:
            if value > 0.2:
                return "high chlorophyll-a; possible bloom signal"
            if value > 0.05:
                return "elevated chlorophyll-a"
            if value > -0.05:
                return "background chlorophyll"
            return "very low chlorophyll signal"
        case IndexName.NDVI:
            if value > 0.5:
                return "dense shoreline vegetation"
            if value > 0.2:
                return "active vegetation present"
            if value > 0.0:
                return "sparse vegetation or stressed canopy"
            return "no vegetation signal over the water mask"
        case IndexName.WRI:
            if value > 2.5:
                return "strong open-water moisture signature"
            if value >= 1.0:
                return "wet surface or shallow water"
            return "dry surface dominant"


def aggregate_index(name: IndexName, array: np.ndarray, mask: np.ndarray) -> IndexAggregate:
    """Compute statistics for ``array`` over ``mask`` pixels."""
    if mask.shape != array.shape:
        raise ValueError("mask and array shapes must match")
    valid = mask & np.isfinite(array)
    samples = array[valid]
    if samples.size == 0:
        # Fall back to all-finite pixels when the water mask is empty so we
        # still report a meaningful number; flagged via sample_count.
        samples = array[np.isfinite(array)]
    value = float(np.mean(samples)) if samples.size else float("nan")
    min_val = float(np.min(samples)) if samples.size else float("nan")
    max_val = float(np.max(samples)) if samples.size else float("nan")
    stddev = float(np.std(samples)) if samples.size else float("nan")
    return IndexAggregate(
        name=name,
        value=value,
        min_value=min_val,
        max_value=max_val,
        stddev=stddev,
        sample_count=int(samples.size),
        interpretation=_interpret(name, value if np.isfinite(value) else 0.0),
        bands=_BAND_MAP[name],
    )


_COMPUTERS = {
    IndexName.NDWI: compute_ndwi,
    IndexName.MNDWI: compute_mndwi,
    IndexName.NDTI: compute_ndti,
    IndexName.NDCI: compute_ndci,
    IndexName.NDVI: compute_ndvi,
    IndexName.WRI: compute_wri,
}


@dataclass(slots=True, frozen=True)
class IndexBundle:
    """Aggregated indices for a scene, plus the water-mask coverage stat."""

    aggregates: list[IndexAggregate]
    water_fraction: float
    """Fraction of valid pixels passing the NDWI ∧ MNDWI water test."""


def compute_all(stack: BandStack) -> IndexBundle:
    """Compute every index over the water mask + report water coverage.

    The water fraction lets downstream code decide whether the AOI is
    actually a body of water (high fraction) or a patch of land (low
    fraction). It's computed from the same combined NDWI∧MNDWI mask that
    drives the per-index aggregation, so it costs essentially nothing.
    """
    mask = water_mask(stack)
    ndwi = compute_ndwi(stack)
    mndwi = compute_mndwi(stack)
    # Only count pixels where both indices that decide the mask were
    # finite — anything else can't be classified water vs land.
    valid = stack.valid_mask & np.isfinite(ndwi) & np.isfinite(mndwi)
    valid_count = int(np.count_nonzero(valid))
    water_count = int(np.count_nonzero(mask))
    fraction = water_count / valid_count if valid_count > 0 else 0.0
    aggregates = [aggregate_index(name, fn(stack), mask) for name, fn in _COMPUTERS.items()]
    return IndexBundle(aggregates=aggregates, water_fraction=fraction)
