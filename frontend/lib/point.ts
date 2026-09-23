import type { GeoJSONPolygon } from "@/lib/api-types";

/**
 * Build a square polygon roughly ``radiusKm`` km on each side around a
 * lat/lng. Used by the click-to-analyze flow so a single tap on the map
 * is enough to start a session.
 *
 * This is intentionally a crude box rather than a geodesic circle — at
 * the spatial scales AquaLens analyses (hundreds of metres to a few
 * kilometres) the latitude-corrected box is accurate to within a few
 * percent and avoids a Turf dependency we don't otherwise need.
 */
export function pointToBufferPolygon(
  lng: number,
  lat: number,
  radiusKm = 1,
): GeoJSONPolygon {
  const latDelta = radiusKm / 111;
  const lngDelta = radiusKm / (111 * Math.cos((lat * Math.PI) / 180));
  return {
    type: "Polygon",
    coordinates: [
      [
        [lng - lngDelta, lat - latDelta],
        [lng + lngDelta, lat - latDelta],
        [lng + lngDelta, lat + latDelta],
        [lng - lngDelta, lat + latDelta],
        [lng - lngDelta, lat - latDelta],
      ],
    ],
  };
}

/** Pretty-print a lat/lng as ``45.987°N · 9.252°E``. */
export function formatLatLng(lng: number, lat: number, digits = 4): string {
  const lonHemi = lng >= 0 ? "E" : "W";
  const latHemi = lat >= 0 ? "N" : "S";
  return `${Math.abs(lat).toFixed(digits)}°${latHemi} · ${Math.abs(lng).toFixed(digits)}°${lonHemi}`;
}
