"""Scene-discovery tools for the Scout agent.

These wrap the Microsoft Planetary Computer STAC API at the metadata
level only — they do **not** read band data. The Scout agent uses
them to choose which scene the deterministic pipeline should then
download via :func:`app.services.satellite.planetary_provider.PlanetaryComputerProvider.fetch`.

Splitting metadata-only discovery from the (slow, cog-reading) fetch
lets the Scout iterate cheaply: list candidates → look at thumbnails
→ re-list with tighter cloud bounds → commit, all without touching
the COGs until the final scene is locked in.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

import planetary_computer
from pystac_client import Client

from app.core.config import get_settings
from app.core.logging import get_logger

LOGGER = get_logger(__name__)

# Hard cap on candidates returned to the agent. Six is plenty for the
# Scout to pick from while keeping the Gemini context small.
MAX_CANDIDATES = 6


_client_cache: Client | None = None


def _client() -> Client:
    """Lazy STAC client. One per process."""
    global _client_cache
    if _client_cache is None:
        _client_cache = Client.open(get_settings().pc_stac_url)
    return _client_cache


def _scene_record(item: Any) -> dict[str, Any]:
    """Project a STAC item into a JSON-safe agent-facing record."""
    signed = planetary_computer.sign(item)
    capture: datetime = signed.datetime or datetime.fromisoformat(
        signed.properties["datetime"].replace("Z", "+00:00")
    )
    return {
        "scene_id": signed.id,
        "capture_date": capture.isoformat(),
        "cloud_cover": float(signed.properties.get("eo:cloud_cover", 0.0)),
        "mgrs_tile": signed.properties.get("s2:mgrs_tile"),
        "platform": signed.properties.get("platform"),
        "thumbnail_url": (
            signed.assets["rendered_preview"].href if "rendered_preview" in signed.assets else None
        ),
        "stac_link": (
            f"https://planetarycomputer.microsoft.com/api/stac/v1/"
            f"collections/sentinel-2-l2a/items/{signed.id}"
        ),
    }


def list_recent_scenes(
    *,
    aoi_geojson: dict[str, Any],
    start_date: date | str,
    end_date: date | str,
    max_cloud_cover: float = 30.0,
    limit: int = MAX_CANDIDATES,
) -> dict[str, Any]:
    """Return up to ``limit`` Sentinel-2 L2A scenes intersecting the AOI.

    Sorted most-recent first. Each entry includes a signed RGB
    thumbnail URL the Scout can hand to Gemini Vision via
    :func:`app.services.agent.tools.vision_tools.look_at_thumbnail`.
    """
    start = _as_date(start_date)
    end = _as_date(end_date)
    if start > end:
        return {"candidates": [], "reason": "start_date is after end_date"}

    search = _client().search(
        collections=["sentinel-2-l2a"],
        intersects=aoi_geojson,
        datetime=f"{start.isoformat()}/{end.isoformat()}",
        query={"eo:cloud_cover": {"lt": max_cloud_cover}},
        sortby=[{"field": "properties.datetime", "direction": "desc"}],
        limit=max(limit, 1),
    )
    candidates = [_scene_record(it) for it in _take(search.items(), limit)]
    LOGGER.info(
        "Scout list_recent_scenes returned %d candidates (cloud<%.1f)",
        len(candidates),
        max_cloud_cover,
    )
    return {
        "candidates": candidates,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "max_cloud_cover": max_cloud_cover,
    }


def inspect_scene(*, scene_id: str) -> dict[str, Any]:
    """Look up a single STAC item by id and return its agent-facing record."""
    search = _client().search(
        collections=["sentinel-2-l2a"],
        ids=[scene_id],
        limit=1,
    )
    items = list(search.items())
    if not items:
        return {"error": f"scene {scene_id!r} not found"}
    return _scene_record(items[0])


def _take(iterable: Iterable[Any], n: int) -> list[Any]:
    out: list[Any] = []
    for item in iterable:
        out.append(item)
        if len(out) >= n:
            break
    return out


def _as_date(value: date | str) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


# Dependency-injection seam for tests: monkeypatch this module's
# ``_client`` to return a stub instead of a real STAC client.
__all__ = [
    "MAX_CANDIDATES",
    "inspect_scene",
    "list_recent_scenes",
]
