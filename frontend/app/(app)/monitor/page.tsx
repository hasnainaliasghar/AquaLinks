"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { GeoJSONSource, Map as MapLibreMap, Marker } from "maplibre-gl";

import { BasemapSwitcher } from "@/components/map/basemap-switcher";
import type { Basemap } from "@/components/map/map";
import type { MapSearchPick } from "@/components/map/map-search";
import { NewSessionWizard } from "@/components/session/new-session-wizard";
import type { GeoJSONPolygon } from "@/lib/api-types";
import { polygonAreaKm2 } from "@/lib/geo";
import { formatArea } from "@/lib/format";
import { formatLocationLabel } from "@/lib/location";
import { pointToBufferPolygon } from "@/lib/point";

const Map = dynamic(() => import("@/components/map/map").then((m) => m.Map), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse rounded-md bg-surface-2" />,
});

const AOI_SOURCE_ID = "aoi-preview";
const AOI_FILL_LAYER_ID = "aoi-preview-fill";
const AOI_LINE_LAYER_ID = "aoi-preview-line";
const POINT_BUFFER_KM = 1; // Radius of the auto-generated AOI around a clicked point.

const PIN_SVG = `
<svg viewBox="0 0 30 38" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <linearGradient id="aqualens-pin-grad" x1="15" y1="0" x2="15" y2="38" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#3b82f6" />
      <stop offset="55%" stop-color="#06b6d4" />
      <stop offset="100%" stop-color="#0f766e" />
    </linearGradient>
  </defs>
  <path
    d="M15 1 C 22.18 1 28 6.82 28 14 C 28 22 18 33 15 37 C 12 33 2 22 2 14 C 2 6.82 7.82 1 15 1 Z"
    fill="url(#aqualens-pin-grad)"
    stroke="white"
    stroke-width="1.4"
  />
  <circle class="pin-core" cx="15" cy="14" r="4" fill="white" />
</svg>
`;

function createPinElement(): HTMLDivElement {
  // Outer element is what MapLibre transforms each frame; inner element
  // owns the drop-in animation. See `.aqualens-pin` rules in globals.css.
  const outer = document.createElement("div");
  outer.className = "aqualens-pin";
  const inner = document.createElement("div");
  inner.className = "aqualens-pin__inner";
  inner.innerHTML = PIN_SVG;
  outer.appendChild(inner);
  return outer;
}

export default function MonitorPage() {
  const [map, setMap] = useState<MapLibreMap | null>(null);
  const [point, setPoint] = useState<{ lng: number; lat: number } | null>(null);
  const [basemap, setBasemap] = useState<Basemap>("street");
  const [suggestedName, setSuggestedName] = useState<string | null>(null);

  const markerRef = useRef<Marker | null>(null);

  // Derive a buffered polygon from the clicked point so the wizard and
  // the backend always work in terms of a polygon AOI.
  const polygon = useMemo<GeoJSONPolygon | null>(
    () => (point ? pointToBufferPolygon(point.lng, point.lat, POINT_BUFFER_KM) : null),
    [point],
  );
  const area = useMemo(() => (polygon ? polygonAreaKm2(polygon) : 0), [polygon]);
  const locationLabel = useMemo(
    () =>
      point
        ? formatLocationLabel({
            name: suggestedName,
            lng: point.lng,
            lat: point.lat,
            digits: 3,
          })
        : null,
    [point, suggestedName],
  );

  // Keep a faint preview polygon in sync with the latest clicked point.
  useEffect(() => {
    if (!map) return;
    const feature = polygon
      ? { type: "Feature" as const, geometry: polygon, properties: {} }
      : null;
    const empty = { type: "FeatureCollection" as const, features: [] };

    const syncAoiPreview = () => {
      let source: GeoJSONSource | undefined;
      try {
        source = map.getSource(AOI_SOURCE_ID) as GeoJSONSource | undefined;
      } catch {
        // Map style is temporarily unavailable (style swap / HMR teardown).
        return;
      }

      if (!source) {
        if (!feature) return;
        map.addSource(AOI_SOURCE_ID, { type: "geojson", data: feature });
        if (!map.getLayer(AOI_FILL_LAYER_ID)) {
          map.addLayer({
            id: AOI_FILL_LAYER_ID,
            type: "fill",
            source: AOI_SOURCE_ID,
            paint: { "fill-color": "#06b6d4", "fill-opacity": 0.14 },
          });
        }
        if (!map.getLayer(AOI_LINE_LAYER_ID)) {
          map.addLayer({
            id: AOI_LINE_LAYER_ID,
            type: "line",
            source: AOI_SOURCE_ID,
            paint: { "line-color": "#06b6d4", "line-width": 1.6 },
          });
        }
        return;
      }

      source.setData(feature ?? empty);
    };

    syncAoiPreview();
    map.on("style.load", syncAoiPreview);
    return () => {
      map.off("style.load", syncAoiPreview);
    };
  }, [map, polygon]);

  // Replace the dropped pin whenever the selected point changes.
  useEffect(() => {
    if (!map) return;
    markerRef.current?.remove();
    markerRef.current = null;
    if (!point) return;
    let cancelled = false;
    (async () => {
      const { Marker: MarkerCtor } = await import("maplibre-gl");
      if (cancelled || !map) return;
      markerRef.current = new MarkerCtor({ element: createPinElement(), anchor: "bottom" })
        .setLngLat([point.lng, point.lat])
        .addTo(map);
    })();
    return () => {
      cancelled = true;
    };
  }, [map, point]);

  useEffect(() => {
    return () => {
      markerRef.current?.remove();
      markerRef.current = null;
    };
  }, []);

  const handleMapClick = useCallback(
    (lngLat: { lng: number; lat: number }) => {
      setPoint(lngLat);
      setSuggestedName(null);
      // Recentre on the click so the pin is always visibly inside the viewport,
      // even if the user clicked near the edge.
      map?.easeTo({ center: [lngLat.lng, lngLat.lat], duration: 350 });
    },
    [map],
  );

  const handleSearchPick = useCallback(
    (pick: MapSearchPick) => {
      setPoint({ lng: pick.lng, lat: pick.lat });
      setSuggestedName(pick.source === "place" ? pick.name : null);
      map?.flyTo({
        center: [pick.lng, pick.lat],
        zoom: pick.source === "coords" ? 12 : 11,
        duration: 800,
        essential: true,
      });
    },
    [map],
  );

  return (
    <div className="grid h-screen min-h-[640px] grid-rows-[1fr_auto] gap-0 lg:grid-cols-[1fr_400px] lg:grid-rows-1">
      <div className="relative min-h-[420px] overflow-hidden border-b border-border lg:min-h-0 lg:border-b-0 lg:border-r">
        <Map
          basemap={basemap}
          onReady={setMap}
          onMapClick={handleMapClick}
          interactive
          initialCenter={[10.0, 45.5]}
          initialZoom={5}
        />

        {/* Top-left: AOI hint or compact summary. Search lives in the
            right rail so the map area stays uncluttered. */}
        <div className="pointer-events-none absolute left-4 top-4 max-w-xs rounded-md border border-border bg-card px-3 py-2 text-xs text-foreground shadow-elev-2">
          {point === null ? (
            <>
              <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                Pick a target
              </p>
              <p className="mt-0.5 text-foreground/85">
                Search the rail, click the map, or paste coordinates. A {POINT_BUFFER_KM} km
                buffer around the pin becomes your AOI.
              </p>
            </>
          ) : (
            <>
              <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                AOI buffer
              </p>
              <p className="mt-0.5 font-mono text-foreground">{locationLabel}</p>
              <p className="mt-0.5 font-medium">≈ {formatArea(area)}</p>
            </>
          )}
        </div>

        {/* Bottom-left basemap switcher. The chip stays anchored here and
            expands vertically when opened. */}
        <div className="absolute bottom-6 left-4 z-10">
          <BasemapSwitcher value={basemap} onChange={setBasemap} />
        </div>

        <p className="sr-only" aria-live="polite">
          {point
            ? `Point selected at ${locationLabel}. Use the Launch button in the right rail to start a session.`
            : "Click the map to pick a target."}
        </p>
      </div>
      <aside className="flex min-h-0 flex-col bg-surface-1 lg:h-full">
        <NewSessionWizard
          polygon={polygon}
          suggestedName={suggestedName}
          onSearchPick={handleSearchPick}
        />
      </aside>
    </div>
  );
}
