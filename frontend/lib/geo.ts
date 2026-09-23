import area from "@turf/area";
import bbox from "@turf/bbox";
import type { Feature, Polygon } from "geojson";

import type { GeoJSONPolygon } from "@/lib/api-types";

export function polygonAreaKm2(polygon: GeoJSONPolygon): number {
  const feature: Feature<Polygon> = {
    type: "Feature",
    geometry: polygon,
    properties: {},
  };
  return area(feature) / 1_000_000;
}

export function polygonCentroid(polygon: GeoJSONPolygon): [number, number] {
  const ring = polygon.coordinates[0];
  if (!ring || ring.length === 0) return [0, 0];
  let sx = 0;
  let sy = 0;
  let count = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const point = ring[i];
    if (!point) continue;
    const [x, y] = point;
    if (typeof x !== "number" || typeof y !== "number") continue;
    sx += x;
    sy += y;
    count++;
  }
  if (count === 0) return [0, 0];
  return [sx / count, sy / count];
}

export function polygonBounds(polygon: GeoJSONPolygon): [number, number, number, number] {
  const feature: Feature<Polygon> = {
    type: "Feature",
    geometry: polygon,
    properties: {},
  };
  const [minX, minY, maxX, maxY] = bbox(feature);
  return [minX, minY, maxX, maxY];
}

export function isValidPolygon(polygon: GeoJSONPolygon): boolean {
  const ring = polygon.coordinates[0];
  if (!ring || ring.length < 4) return false;
  const first = ring[0];
  const last = ring[ring.length - 1];
  return Boolean(first && last && first[0] === last[0] && first[1] === last[1]);
}
