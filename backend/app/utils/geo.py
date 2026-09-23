"""GeoJSON / shapely helpers."""

from __future__ import annotations

from typing import Any

from pyproj import Geod
from shapely.geometry import Polygon, mapping, shape


def polygon_from_geojson(geometry: dict[str, Any]) -> Polygon:
    """Return a Shapely polygon for a GeoJSON ``Polygon`` geometry."""
    geom = shape(geometry)
    if geom.geom_type != "Polygon":
        raise ValueError(f"expected GeoJSON Polygon, got {geom.geom_type}")
    return geom


def centroid_geojson(geometry: dict[str, Any]) -> dict[str, Any]:
    """Return the centroid as a GeoJSON ``Point``."""
    poly = polygon_from_geojson(geometry)
    return mapping(poly.centroid)


_GEOD = Geod(ellps="WGS84")


def area_km2(geometry: dict[str, Any]) -> float:
    """Approximate the polygon area in km² using the WGS84 ellipsoid."""
    poly = polygon_from_geojson(geometry)
    area_m2, _ = _GEOD.geometry_area_perimeter(poly)
    return abs(area_m2) / 1_000_000.0


def bounds(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return ``(minx, miny, maxx, maxy)`` of the geometry."""
    poly = polygon_from_geojson(geometry)
    minx, miny, maxx, maxy = poly.bounds
    return float(minx), float(miny), float(maxx), float(maxy)
