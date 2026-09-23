"use client";

import maplibregl, {
  type Map as MapLibreMap,
  type StyleSpecification,
} from "maplibre-gl";
import { useEffect, useRef } from "react";

import type { GeoJSONPolygon } from "@/lib/api-types";
import { polygonBounds } from "@/lib/geo";
import { cn } from "@/lib/utils";

const INLINE_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    street: {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
      ],
      tileSize: 256,
      minzoom: 0,
      maxzoom: 19,
      attribution:
        "Tiles © Esri — Source: USGS, Esri, TANA, DeLorme, HERE, NAVTEQ, OpenStreetMap",
    },
  },
  glyphs: "https://fonts.openmaptiles.org/{fontstack}/{range}.pbf",
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#f4efe9" } },
    { id: "street", type: "raster", source: "street" },
  ],
};

export function MiniMap({
  polygon,
  className,
}: {
  polygon: GeoJSONPolygon;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);

  useEffect(() => {
    if (!ref.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: ref.current,
      style: INLINE_STYLE,
      center: [0, 0],
      zoom: 2,
      interactive: false,
      attributionControl: false,
    });
    mapRef.current = map;

    map.once("load", () => {
      map.resize();
      const sourceId = "aoi";
      map.addSource(sourceId, {
        type: "geojson",
        data: { type: "Feature", geometry: polygon, properties: {} },
      });
      map.addLayer({
        id: "aoi-fill",
        type: "fill",
        source: sourceId,
        paint: { "fill-color": "#0ea5b7", "fill-opacity": 0.25 },
      });
      map.addLayer({
        id: "aoi-line",
        type: "line",
        source: sourceId,
        paint: { "line-color": "#0ea5b7", "line-width": 2 },
      });
      const [minX, minY, maxX, maxY] = polygonBounds(polygon);
      map.fitBounds(
        [
          [minX, minY],
          [maxX, maxY],
        ],
        { padding: 24, animate: false },
      );
    });

    const observer = new ResizeObserver(() => map.resize());
    observer.observe(ref.current);

    return () => {
      observer.disconnect();
      if (mapRef.current === map) {
        map.remove();
        mapRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      ref={ref}
      role="img"
      aria-label="Polygon preview"
      style={{ backgroundColor: "#f4efe9" }}
      className={cn("h-40 w-full overflow-hidden rounded-md border border-border", className)}
    />
  );
}
