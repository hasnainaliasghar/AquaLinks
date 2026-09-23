"""Tests for spectral index band math."""

from __future__ import annotations

import numpy as np

from app.models.spectral_index import IndexName
from app.services.indices import (
    aggregate_index,
    compute_all,
    compute_mndwi,
    compute_ndci,
    compute_ndti,
    compute_ndvi,
    compute_ndwi,
    compute_wri,
    water_mask,
)
from app.services.satellite.base import BandStack


def _stack(**overrides) -> BandStack:
    # Derive the target shape from the first overridden band array so that
    # callers can pass small (1×2 / 2×2) fixtures without having to also
    # supply a matching ``valid`` mask. Defaults to 4×4 when none is given.
    shape: tuple[int, ...] = (4, 4)
    for key in ("blue", "green", "red", "red_edge", "nir", "swir"):
        arr = overrides.get(key)
        if isinstance(arr, np.ndarray):
            shape = arr.shape
            break
    base = np.full(shape, 0.1, dtype=np.float32)
    blue = overrides.get("blue", base)
    green = overrides.get("green", base)
    red = overrides.get("red", base)
    red_edge = overrides.get("red_edge", base)
    nir = overrides.get("nir", base)
    swir = overrides.get("swir", base)
    valid = overrides.get("valid", np.ones(shape, dtype=bool))
    return BandStack(
        blue=blue,
        green=green,
        red=red,
        red_edge=red_edge,
        nir=nir,
        swir=swir,
        valid_mask=valid,
    )


def test_ndwi_water_is_positive():
    stack = _stack(
        nir=np.full((4, 4), 0.4, dtype=np.float32), swir=np.full((4, 4), 0.1, dtype=np.float32)
    )
    arr = compute_ndwi(stack)
    # NDWI = (0.4-0.1)/(0.4+0.1) = 0.6
    assert np.allclose(arr, 0.6, atol=1e-6)


def test_mndwi_uses_green_minus_swir():
    stack = _stack(
        green=np.full((4, 4), 0.3, dtype=np.float32), swir=np.full((4, 4), 0.1, dtype=np.float32)
    )
    arr = compute_mndwi(stack)
    assert np.allclose(arr, 0.5, atol=1e-6)


def test_ndti_red_over_green():
    stack = _stack(
        red=np.full((4, 4), 0.25, dtype=np.float32), green=np.full((4, 4), 0.15, dtype=np.float32)
    )
    arr = compute_ndti(stack)
    assert np.allclose(arr, 0.25, atol=1e-6)


def test_ndci_red_edge_minus_red():
    stack = _stack(
        red_edge=np.full((4, 4), 0.18, dtype=np.float32),
        red=np.full((4, 4), 0.10, dtype=np.float32),
    )
    arr = compute_ndci(stack)
    # (0.18 - 0.10) / (0.18 + 0.10) = 0.2857
    assert np.allclose(arr, 0.08 / 0.28, atol=1e-6)


def test_ndvi_nir_minus_red():
    stack = _stack(
        nir=np.full((4, 4), 0.6, dtype=np.float32), red=np.full((4, 4), 0.1, dtype=np.float32)
    )
    arr = compute_ndvi(stack)
    assert np.allclose(arr, 0.5 / 0.7, atol=1e-6)


def test_wri_strong_water_signal():
    stack = _stack(
        green=np.full((4, 4), 0.2, dtype=np.float32),
        red=np.full((4, 4), 0.15, dtype=np.float32),
        nir=np.full((4, 4), 0.05, dtype=np.float32),
        swir=np.full((4, 4), 0.05, dtype=np.float32),
    )
    arr = compute_wri(stack)
    assert np.all(arr >= 2.5)


def test_safe_div_produces_nan_for_zero_denominator():
    stack = _stack(nir=np.zeros((2, 2), dtype=np.float32), swir=np.zeros((2, 2), dtype=np.float32))
    arr = compute_ndwi(stack)
    assert np.all(np.isnan(arr))


def test_water_mask_requires_both_ndwi_and_mndwi_positive():
    # Pixel A: water-like (NIR > SWIR, Green > SWIR) → both indices positive.
    # Pixel B: dry land (NIR < SWIR, Green < SWIR) → both negative.
    nir = np.array([[0.4, 0.05]], dtype=np.float32)
    swir = np.array([[0.05, 0.4]], dtype=np.float32)
    green = np.array([[0.3, 0.05]], dtype=np.float32)
    stack = _stack(nir=nir, swir=swir, green=green)
    mask = water_mask(stack)
    assert mask[0, 0]
    assert not mask[0, 1]


def test_water_mask_filters_vegetation_false_positives():
    # Vegetation: high NIR (so NDWI > 0) but low Green relative to SWIR
    # (so MNDWI < 0). The combined mask should reject these pixels.
    nir = np.full((2, 2), 0.40, dtype=np.float32)
    swir = np.full((2, 2), 0.20, dtype=np.float32)
    green = np.full((2, 2), 0.10, dtype=np.float32)
    stack = _stack(nir=nir, swir=swir, green=green)

    # Sanity: NDWI alone is positive (the false positive we're guarding against).
    ndwi_only = np.all(compute_ndwi(stack) > 0)
    assert ndwi_only

    # Combined mask must reject these pixels because MNDWI is negative.
    assert not water_mask(stack).any()


def test_aggregate_index_returns_masked_mean():
    stack = _stack(
        nir=np.full((4, 4), 0.5, dtype=np.float32), swir=np.full((4, 4), 0.1, dtype=np.float32)
    )
    arr = compute_ndwi(stack)
    mask = np.ones_like(arr, dtype=bool)
    agg = aggregate_index(IndexName.NDWI, arr, mask)
    assert agg.name is IndexName.NDWI
    assert agg.sample_count == 16
    assert agg.interpretation


def test_compute_all_returns_six_indices():
    stack = _stack(
        nir=np.full((4, 4), 0.4, dtype=np.float32),
        swir=np.full((4, 4), 0.1, dtype=np.float32),
        red_edge=np.full((4, 4), 0.2, dtype=np.float32),
    )
    bundle = compute_all(stack)
    names = {agg.name for agg in bundle.aggregates}
    assert names == set(IndexName)
    assert 0.0 <= bundle.water_fraction <= 1.0


def test_compute_all_reports_water_fraction_for_water():
    # An obviously-water scene (high NIR, low SWIR → NDWI > 0 everywhere).
    stack = _stack(
        nir=np.full((4, 4), 0.45, dtype=np.float32),
        swir=np.full((4, 4), 0.05, dtype=np.float32),
    )
    bundle = compute_all(stack)
    assert bundle.water_fraction == 1.0


def test_compute_all_reports_water_fraction_for_land():
    # Land-dominated scene (low NIR, high SWIR → NDWI < 0 everywhere).
    stack = _stack(
        nir=np.full((4, 4), 0.05, dtype=np.float32),
        swir=np.full((4, 4), 0.30, dtype=np.float32),
    )
    bundle = compute_all(stack)
    assert bundle.water_fraction == 0.0
