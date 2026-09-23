"""Sentinel-2 retrieval via Microsoft Planetary Computer STAC.

This provider queries the public Planetary Computer STAC API for the
``sentinel-2-l2a`` collection, picks the most recent low-cloud scene
that intersects the AOI, signs the asset URLs, and reads the relevant
bands as Cloud-Optimized GeoTIFFs clipped to the polygon.

No API key is required for STAC search or URL signing.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import numpy as np
import planetary_computer
import rasterio
from pystac_client import Client
from rasterio.mask import mask as rio_mask
from rasterio.warp import transform_geom

from app.core.logging import get_logger
from app.services.satellite.base import (
    BandStack,
    ImageryBundle,
    SatelliteError,
    SceneNotFoundError,
)

LOGGER = get_logger(__name__)

# Sentinel-2 L2A band keys on Planetary Computer.
BAND_KEYS = {
    "blue": "B02",
    "green": "B03",
    "red": "B04",
    "red_edge": "B05",
    "nir": "B08",
    "swir": "B11",
}

# Sentinel-2 L2A surface reflectance scale factor.
REFLECTANCE_SCALE = 10_000.0


class PlanetaryComputerProvider:
    """Real Sentinel-2 imagery via Microsoft Planetary Computer."""

    name = "microsoft-planetary-computer"

    def __init__(self, stac_url: str) -> None:
        self._stac_url = stac_url
        self._client: Client | None = None

    def _client_lazy(self) -> Client:
        if self._client is None:
            self._client = Client.open(self._stac_url)
        return self._client

    def fetch(
        self,
        *,
        geometry: dict[str, Any],
        start_date: date,
        end_date: date,
        max_cloud_cover: float,
    ) -> ImageryBundle:
        client = self._client_lazy()
        date_range = f"{start_date.isoformat()}/{end_date.isoformat()}"
        LOGGER.info(
            "Planetary Computer search: collection=sentinel-2-l2a window=%s cloud<%.1f",
            date_range,
            max_cloud_cover,
        )

        search = client.search(
            collections=["sentinel-2-l2a"],
            intersects=geometry,
            datetime=date_range,
            query={"eo:cloud_cover": {"lt": max_cloud_cover}},
            sortby=[{"field": "properties.datetime", "direction": "desc"}],
            limit=10,
        )

        items = list(search.items())
        if not items:
            raise SceneNotFoundError(
                f"No Sentinel-2 L2A scene with cloud<{max_cloud_cover}% intersects the AOI "
                f"in {date_range}."
            )

        item = items[0]
        signed = planetary_computer.sign(item)
        LOGGER.info(
            "Selected scene id=%s captured=%s cloud=%.2f",
            signed.id,
            signed.datetime,
            signed.properties.get("eo:cloud_cover", float("nan")),
        )

        try:
            stack = _read_bands(signed, geometry)
        except Exception as exc:  # pragma: no cover - exercised via integration
            raise SatelliteError(f"failed to read scene bands: {exc}") from exc

        capture_dt: datetime = signed.datetime or datetime.fromisoformat(
            signed.properties["datetime"].replace("Z", "+00:00")
        )

        return ImageryBundle(
            bands=stack,
            scene_id=signed.id,
            capture_date=capture_dt,
            cloud_cover=float(signed.properties.get("eo:cloud_cover", 0.0)),
            provider=self.name,
            thumbnail_url=(
                signed.assets["rendered_preview"].href
                if "rendered_preview" in signed.assets
                else None
            ),
            metadata={
                "platform": signed.properties.get("platform"),
                "instruments": signed.properties.get("instruments"),
                "mgrs_tile": signed.properties.get("s2:mgrs_tile"),
                "datetime": capture_dt.isoformat(),
                "stac_id": signed.id,
            },
        )


def _read_bands(item: Any, geometry: dict[str, Any]) -> BandStack:
    """Read each Sentinel-2 band, clip to the AOI, resample everyone to the
    highest-resolution grid, and only then build the combined validity mask.

    Sentinel-2 bands have mixed native resolutions: B02 / B03 / B04 / B08 are
    10 m and B05 / B11 are 20 m, so a clip can return arrays of two different
    shapes. We must align them before any element-wise combine, otherwise
    numpy raises a broadcast error.
    """

    raw: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    for friendly, asset_key in BAND_KEYS.items():
        href = item.assets[asset_key].href
        with rasterio.open(href) as src:
            geom_in_band_crs = transform_geom("EPSG:4326", src.crs, geometry)
            clipped, _transform = rio_mask(
                src,
                [geom_in_band_crs],
                crop=True,
                indexes=1,
                filled=False,
            )
            data = np.asarray(clipped, dtype=np.float32) / REFLECTANCE_SCALE
            mask = (
                np.ma.getmaskarray(clipped)
                if np.ma.isMaskedArray(clipped)
                else np.zeros(data.shape, dtype=bool)
            )
            raw[friendly] = (data, mask)

    if not raw:
        raise SatelliteError("no bands could be read")

    # Pick the highest-resolution grid available — usually the 10 m bands.
    target_shape = max((d.shape for d, _ in raw.values()), key=lambda s: s[0] * s[1])

    aligned: dict[str, np.ndarray] = {}
    masks: dict[str, np.ndarray] = {}
    for friendly, (data, mask) in raw.items():
        if data.shape != target_shape:
            data = _resize_nearest(data, target_shape)
            mask = _resize_nearest(mask, target_shape)
        aligned[friendly] = np.where(mask, np.nan, data)
        masks[friendly] = mask

    valid_mask = np.ones(target_shape, dtype=bool)
    for friendly, mask in masks.items():
        valid_mask = valid_mask & (~mask) & np.isfinite(aligned[friendly])

    return BandStack(
        blue=aligned["blue"],
        green=aligned["green"],
        red=aligned["red"],
        red_edge=aligned["red_edge"],
        nir=aligned["nir"],
        swir=aligned["swir"],
        valid_mask=valid_mask,
    )


def _resize_nearest(arr: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Cheap nearest-neighbour resample that preserves dtype (incl. bool)."""
    rows, cols = shape
    src_rows, src_cols = arr.shape
    row_idx = np.linspace(0, src_rows - 1, rows).astype(int)
    col_idx = np.linspace(0, src_cols - 1, cols).astype(int)
    return arr[np.ix_(row_idx, col_idx)]
