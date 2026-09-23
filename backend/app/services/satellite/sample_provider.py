"""Deterministic in-process imagery provider used by tests and CI E2E.

Generates a small, physically plausible 6-band reflectance stack from
the AOI geometry so that the rest of the pipeline can run without
network access. Real deployments use :mod:`planetary_provider`.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, time
from typing import Any

import numpy as np

from app.services.satellite.base import BandStack, ImageryBundle


class SampleProvider:
    """Synthetic Sentinel-2-shaped imagery for offline runs."""

    name = "aqualens-sample"

    def fetch(
        self,
        *,
        geometry: dict[str, Any],
        start_date: date,
        end_date: date,
        max_cloud_cover: float,
    ) -> ImageryBundle:
        # Derive a deterministic seed from the geometry so each AOI yields
        # the same indices across runs.
        seed_bytes = hashlib.sha256(repr(geometry).encode("utf-8")).digest()
        seed = int.from_bytes(seed_bytes[:4], "big")
        rng = np.random.default_rng(seed)

        rows, cols = 64, 64
        # Base reflectance map mostly representing water (low NIR/SWIR, moderate green).
        blue = rng.uniform(0.04, 0.10, size=(rows, cols)).astype(np.float32)
        green = rng.uniform(0.06, 0.14, size=(rows, cols)).astype(np.float32)
        red = rng.uniform(0.04, 0.12, size=(rows, cols)).astype(np.float32)
        red_edge = rng.uniform(0.04, 0.15, size=(rows, cols)).astype(np.float32)
        nir = rng.uniform(0.02, 0.10, size=(rows, cols)).astype(np.float32)
        swir = rng.uniform(0.02, 0.08, size=(rows, cols)).astype(np.float32)

        # Add a chlorophyll signal modulated by the seed so different polygons
        # produce different "risk" stories.
        chlorophyll = (seed % 100) / 100.0  # 0..1
        red_edge = red_edge + 0.15 * chlorophyll
        green = green + 0.05 * chlorophyll

        valid = np.ones((rows, cols), dtype=bool)
        stack = BandStack(
            blue=blue,
            green=green,
            red=red,
            red_edge=red_edge,
            nir=nir,
            swir=swir,
            valid_mask=valid,
        )

        scene_dt = datetime.combine(end_date, time(10, 30))
        return ImageryBundle(
            bands=stack,
            scene_id=f"sample-{seed:08x}",
            capture_date=scene_dt,
            cloud_cover=min(5.0 + (seed % 10), max_cloud_cover),
            provider=self.name,
            thumbnail_url=None,
            metadata={
                "synthetic": True,
                "chlorophyll_drive": chlorophyll,
                "datetime": scene_dt.isoformat(),
            },
        )
