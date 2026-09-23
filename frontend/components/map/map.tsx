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

const STYLE_URL: Record<Basemap, string> = {
  street: "/map-styles/basemap-street.json",
  satellite: "/map-styles/basemap-satellite.json",
  terrain: "/map-styles/basemap-terrain.json",
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
    const map = new maplibregl.Map({
      container: ref.current,
      style: STYLE_URL[basemap] as unknown as StyleSpecification,
      center: initialCenter as LngLatLike,
      zoom: initialZoom,
      interactive,
      attributionControl: false,
    });
    mapRef.current = map;

    map.addControl(new AttributionControl({ compact: true }), "bottom-right");
    if (interactive) {
      map.addControl(new NavigationControl({ visualizePitch: false }), "top-right");
    }

    map.once("load", () => {
      // The container is sometimes still settling when the dynamic chunk
      // mounts inside a grid/flex layout. Forcing a resize after load and
      // observing the container guarantees a non-zero canvas.
      map.resize();
      onReady?.(map);
    });

    const handleClick = (event: MapMouseEvent) => {
      clickHandlerRef.current?.({ lng: event.lngLat.lng, lat: event.lngLat.lat });
    };
    map.on("click", handleClick);

    const observer = new ResizeObserver(() => map.resize());
    observer.observe(ref.current);

    return () => {
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
    map.setStyle(STYLE_URL[basemap] as unknown as StyleSpecification, { diff: false });
  }, [basemap]);

  return (
    <div className={cn("relative h-full w-full overflow-hidden", className)}>
      <div
        ref={ref}
        className="absolute inset-0 h-full w-full"
        aria-label="Interactive map"
        role="region"
      />
      {children}
    </div>
  );
}
