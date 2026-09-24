"use client";

import maplibregl, {
  AttributionControl,
  type LngLatLike,
  type Map as MapLibreMap,
  type MapMouseEvent,
  NavigationControl,
  type StyleSpecification,
} from "maplibre-gl";
import { useEffect, useRef, type ReactNode } from "react";

import { cn } from "@/lib/utils";

export type Basemap = "street" | "satellite" | "terrain";

const STREET_STYLE: StyleSpecification = {
  version: 8,
  name: "AquaLens Street",
  sources: {
    street: {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      minzoom: 0,
      maxzoom: 19,
      attribution: "Tiles © Esri — Source: USGS, Esri, NAVTEQ, OpenStreetMap contributors",
    },
  },
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#f4efe9" } },
    { id: "street", type: "raster", source: "street" },
  ],
};

const SATELLITE_STYLE: StyleSpecification = {
  version: 8,
  name: "AquaLens Satellite",
  sources: {
    imagery: {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      minzoom: 0,
      maxzoom: 19,
      attribution: "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
    },
    labels: {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      minzoom: 0,
      maxzoom: 19,
      attribution: "Tiles © Esri",
    },
  },
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#0b1024" } },
    { id: "imagery", type: "raster", source: "imagery" },
    { id: "labels", type: "raster", source: "labels", paint: { "raster-opacity": 0.85 } },
  ],
};

const TERRAIN_STYLE: StyleSpecification = {
  version: 8,
  name: "AquaLens Terrain",
  sources: {
    topo: {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      minzoom: 0,
      maxzoom: 19,
      attribution: "Tiles © Esri",
    },
  },
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#e6f0e7" } },
    { id: "topo", type: "raster", source: "topo" },
  ],
};

const STYLES: Record<Basemap, StyleSpecification> = {
  street: STREET_STYLE,
  satellite: SATELLITE_STYLE,
  terrain: TERRAIN_STYLE,
};

export type MapHandle = {
  map: MapLibreMap | null;
};

type Props = {
  className?: string;
  basemap?: Basemap;
  initialCenter?: [number, number];
  initialZoom?: number;
  interactive?: boolean;
  onReady?: (map: MapLibreMap | null) => void;
  onMapClick?: (lngLat: { lng: number; lat: number }) => void;
  children?: ReactNode;
};

export function Map({
  className,
  basemap = "street",
  initialCenter = [10.0, 45.5],
  initialZoom = 4,
  interactive = true,
  onReady,
  onMapClick,
  children,
}: Props) {
  const ref = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const clickHandlerRef = useRef<typeof onMapClick>(onMapClick);
  clickHandlerRef.current = onMapClick;

  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    const cartoApiKey = process.env.NEXT_PUBLIC_CARTO_API_KEY;
    const map = new maplibregl.Map({
      container: ref.current,
      style: STYLES[basemap],
      center: initialCenter as LngLatLike,
      zoom: initialZoom,
      interactive,
      attributionControl: false,
      transformRequest: (url) => {
        if (cartoApiKey && (url.includes("cartocdn.com") || url.includes("carto.com"))) {
          if (!url.includes("api_key=") && !url.includes("key=")) {
            const sep = url.includes("?") ? "&" : "?";
            return { url: `${url}${sep}api_key=${cartoApiKey}` };
          }
        }
        return { url };
      },
    });
    mapRef.current = map;

    map.addControl(new AttributionControl({ compact: true }), "bottom-right");
    if (interactive) {
      map.addControl(new NavigationControl({ visualizePitch: false }), "top-right");
    }

    map.once("load", () => {
      map.resize();
      onReady?.(map);
    });

    const timer1 = setTimeout(() => map.resize(), 100);
    const timer2 = setTimeout(() => map.resize(), 500);

    const handleResize = () => {
      if (mapRef.current) {
        mapRef.current.resize();
      }
    };

    const handleClick = (event: MapMouseEvent) => {
      clickHandlerRef.current?.({ lng: event.lngLat.lng, lat: event.lngLat.lat });
    };
    map.on("click", handleClick);

    const observer = new ResizeObserver(() => handleResize());
    observer.observe(ref.current);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      observer.disconnect();
      map.off("click", handleClick);
      onReady?.(null);
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Swap basemap when the prop changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.setStyle(STYLES[basemap], { diff: false });
  }, [basemap]);

  return (
    <div className={cn("relative h-full w-full min-h-[420px] overflow-hidden", className)}>
      <div
        ref={ref}
        className="h-full w-full min-h-[420px]"
        aria-label="Interactive map"
        role="region"
      />
      {children}
    </div>
  );
}
