import type { GeoJSONPoint } from "@/lib/api-types";
import { formatLatLng } from "@/lib/point";

const HEMISPHERE_COORDS_RE =
  /^\s*\d{1,3}(?:\.\d+)?°\s*[NS]\s*[·,]\s*\d{1,3}(?:\.\d+)?°\s*[EW]\s*$/i;
const DECIMAL_COORDS_RE =
  /^\s*-?\d{1,3}(?:\.\d+)?°?\s*,\s*-?\d{1,3}(?:\.\d+)?°?\s*$/;

function looksLikeCoords(value: string): boolean {
  return HEMISPHERE_COORDS_RE.test(value) || DECIMAL_COORDS_RE.test(value);
}

function stripTrailingCoords(name: string): string {
  const trimmed = name.trim();
  const match = /^(.*)\(([^()]*)\)\s*$/.exec(trimmed);
  if (!match) return trimmed;
  const base = match[1]?.trim() ?? "";
  const suffix = match[2]?.trim() ?? "";
  if (!base) return trimmed;
  return looksLikeCoords(suffix) ? base : trimmed;
}

export function pointToLatLng(
  point: GeoJSONPoint | null | undefined,
): { lng: number; lat: number } | null {
  if (!point || point.type !== "Point") return null;
  const [lng, lat] = point.coordinates;
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null;
  return { lng, lat };
}

export function formatLocationLabel({
  name,
  lng,
  lat,
  digits = 3,
}: {
  name?: string | null;
  lng?: number | null;
  lat?: number | null;
  digits?: number;
}): string {
  const hasCoords = Number.isFinite(lng) && Number.isFinite(lat);
  const coords = hasCoords ? formatLatLng(lng as number, lat as number, digits) : null;
  const trimmed = name?.trim() ?? "";
  if (!trimmed) return coords ?? "—";

  const baseName = stripTrailingCoords(trimmed);
  if (looksLikeCoords(baseName)) {
    return coords ?? baseName;
  }
  if (!coords) return baseName;
  return `${baseName} (${coords})`;
}
