"""Location label formatting helpers."""

from __future__ import annotations

import re

_HEMISPHERE_COORDS_RE = re.compile(
    r"^\s*\d{1,3}(?:\.\d+)?°\s*[NS]\s*[·,]\s*\d{1,3}(?:\.\d+)?°\s*[EW]\s*$",
    re.IGNORECASE,
)
_DECIMAL_COORDS_RE = re.compile(r"^\s*-?\d{1,3}(?:\.\d+)?°?\s*,\s*-?\d{1,3}(?:\.\d+)?°?\s*$")


def format_lat_lng(lng: float, lat: float, digits: int = 3) -> str:
    lon_hemi = "E" if lng >= 0 else "W"
    lat_hemi = "N" if lat >= 0 else "S"
    return f"{abs(lat):.{digits}f}°{lat_hemi} · {abs(lng):.{digits}f}°{lon_hemi}"


def _looks_like_coords(value: str) -> bool:
    return bool(_HEMISPHERE_COORDS_RE.match(value) or _DECIMAL_COORDS_RE.match(value))


def _strip_trailing_coords(name: str) -> str:
    trimmed = name.strip()
    match = re.match(r"^(.*)\(([^()]*)\)\s*$", trimmed)
    if not match:
        return trimmed
    base = (match.group(1) or "").strip()
    suffix = (match.group(2) or "").strip()
    if not base:
        return trimmed
    return base if _looks_like_coords(suffix) else trimmed


def _centroid_lat_lng(
    centroid: dict[str, object] | None,
) -> tuple[float | None, float | None]:
    if not isinstance(centroid, dict):
        return None, None
    raw = centroid.get("coordinates")
    if not isinstance(raw, list | tuple) or len(raw) < 2:
        return None, None
    lon, lat = raw[0], raw[1]
    if not isinstance(lon, int | float) or not isinstance(lat, int | float):
        return None, None
    return float(lat), float(lon)


def format_location_label(
    *,
    name: str | None,
    centroid: dict[str, object] | None,
    digits: int = 3,
) -> str:
    lat, lng = _centroid_lat_lng(centroid)
    coords = format_lat_lng(lng, lat, digits) if lat is not None and lng is not None else None

    trimmed = (name or "").strip()
    if not trimmed:
        return coords or "—"

    base_name = _strip_trailing_coords(trimmed)
    if _looks_like_coords(base_name):
        return coords or base_name
    if not coords:
        return base_name
    return f"{base_name} ({coords})"
