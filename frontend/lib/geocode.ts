/**
 * Place + coordinate search backed by OpenStreetMap Nominatim.
 *
 * We hit `nominatim.openstreetmap.org` directly from the browser. Their
 * usage policy is fine for low-volume autocomplete as long as requests
 * are debounced (we cap to roughly 1 request per typing pause).
 */

const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";

export type GeocodeResult = {
  id: string;
  displayName: string;
  shortName: string;
  category: string;
  type: string;
  lat: number;
  lng: number;
  importance: number;
};

type NominatimItem = {
  place_id: number;
  display_name: string;
  name?: string;
  lat: string;
  lon: string;
  class: string;
  type: string;
  importance: number;
};

export async function geocode(
  query: string,
  signal?: AbortSignal,
): Promise<GeocodeResult[]> {
  const trimmed = query.trim();
  if (!trimmed) return [];

  const url = new URL(NOMINATIM_URL);
  url.searchParams.set("q", trimmed);
  url.searchParams.set("format", "json");
  url.searchParams.set("limit", "8");
  url.searchParams.set("addressdetails", "0");
  url.searchParams.set("dedupe", "1");

  const response = await fetch(url.toString(), {
    signal,
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Nominatim ${response.status}`);
  }
  const data = (await response.json()) as NominatimItem[];

  return data.map((item) => {
    const display = item.display_name;
    return {
      id: String(item.place_id),
      displayName: display,
      shortName: item.name ?? display.split(",")[0]!.trim(),
      category: item.class,
      type: item.type,
      lat: Number(item.lat),
      lng: Number(item.lon),
      importance: item.importance,
    };
  });
}

/** Match `lat, lng` or `lat lng` decimal degrees. */
const COORD_REGEX =
  /^\s*(-?\d{1,3}(?:\.\d+)?)[\s,]+\s*(-?\d{1,3}(?:\.\d+)?)\s*$/;

export function parseCoords(input: string): { lat: number; lng: number } | null {
  const match = COORD_REGEX.exec(input);
  if (!match) return null;
  const lat = Number(match[1]);
  const lng = Number(match[2]);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
  return { lat, lng };
}
