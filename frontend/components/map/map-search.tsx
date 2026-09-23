"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Loader2, MapPin, Navigation, Search, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { useGeocodeSearch } from "@/hooks/use-geocode";
import type { GeocodeResult } from "@/lib/geocode";
import { formatLatLng } from "@/lib/point";
import { cn } from "@/lib/utils";

export type MapSearchPick = {
  name: string;
  lng: number;
  lat: number;
  source: "place" | "coords";
};

export function MapSearch({
  onPick,
  className,
}: {
  onPick: (pick: MapSearchPick) => void;
  className?: string;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const reduce = useReducedMotion();
  const listboxId = useId();

  const { results, coords, loading, error } = useGeocodeSearch(open ? query : "");

  // Reset highlight whenever the result set changes.
  useEffect(() => {
    setActiveIdx(0);
  }, [results, coords]);

  // Close the dropdown when clicking outside or pressing Escape.
  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const pickResult = (result: GeocodeResult) => {
    onPick({
      name: result.shortName,
      lng: result.lng,
      lat: result.lat,
      source: "place",
    });
    setQuery(result.shortName);
    setOpen(false);
    inputRef.current?.blur();
  };

  const pickCoords = () => {
    if (!coords) return;
    onPick({
      name: formatLatLng(coords.lng, coords.lat, 4),
      lng: coords.lng,
      lat: coords.lat,
      source: "coords",
    });
    setOpen(false);
    inputRef.current?.blur();
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (coords) pickCoords();
      else if (results[activeIdx]) pickResult(results[activeIdx]);
    }
  };

  const showDropdown =
    open && (loading || coords !== null || results.length > 0 || error || query.trim().length > 0);
  const activeOptionId =
    !coords && results[activeIdx] ? `${listboxId}-opt-${results[activeIdx].id}` : undefined;

  return (
    <div ref={containerRef} className={cn("relative w-full", className)}>
      <div className="relative">
        <Search
          className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
        <input
          ref={inputRef}
          // Use type="text" not "search" — the latter renders the browser's
          // own clear button on top of ours.
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-activedescendant={open ? activeOptionId : undefined}
          aria-autocomplete="list"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder="Search a place or paste coordinates"
          aria-label="Search a place or paste coordinates"
          className="h-10 w-full rounded-full border border-border bg-card pl-10 pr-10 text-sm font-medium text-foreground shadow-elev-1 placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring"
          spellCheck={false}
          autoCapitalize="off"
          autoComplete="off"
        />
        {query ? (
          <button
            type="button"
            aria-label="Clear search"
            onClick={() => {
              setQuery("");
              inputRef.current?.focus();
            }}
            className="absolute right-2 top-1/2 grid size-7 -translate-y-1/2 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            <X className="size-3.5" />
          </button>
        ) : null}
      </div>

      <AnimatePresence>
        {showDropdown ? (
          <motion.div
            key="results"
            initial={reduce ? { opacity: 0 } : { opacity: 0, y: -4 }}
            animate={reduce ? { opacity: 1 } : { opacity: 1, y: 0 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, y: -4 }}
            transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
            className="absolute left-0 right-0 z-30 mt-2 max-h-80 overflow-y-auto overflow-x-hidden rounded-md border border-border bg-card shadow-elev-3"
            id={listboxId}
            role="listbox"
          >
            {loading ? (
              <div className="flex items-center gap-2 px-3 py-3 text-xs text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin" aria-hidden />
                Searching…
              </div>
            ) : coords ? (
              <button
                type="button"
                onClick={pickCoords}
                className="flex w-full items-center gap-3 bg-accent/40 px-3 py-2.5 text-left transition-colors hover:bg-accent"
              >
                <Navigation className="size-4 shrink-0 text-aqua-500" aria-hidden />
                <span className="flex-1">
                  <span className="block text-sm font-medium">Use coordinates</span>
                  <span className="block font-mono text-xs text-muted-foreground">
                    {formatLatLng(coords.lng, coords.lat, 4)}
                  </span>
                </span>
              </button>
            ) : results.length > 0 ? (
              results.map((result, idx) => {
                const active = idx === activeIdx;
                return (
                    <button
                      key={result.id}
                      id={`${listboxId}-opt-${result.id}`}
                      type="button"
                      role="option"
                    aria-selected={active}
                    onMouseEnter={() => setActiveIdx(idx)}
                    onClick={() => pickResult(result)}
                    className={cn(
                      "flex w-full items-start gap-3 px-3 py-2.5 text-left transition-colors",
                      active ? "bg-secondary" : "hover:bg-secondary/60",
                    )}
                  >
                    <MapPin
                      className="mt-0.5 size-4 shrink-0 text-aqua-500"
                      aria-hidden
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-foreground">
                        {result.shortName}
                      </span>
                      <span className="line-clamp-2 text-xs text-muted-foreground">
                        {result.displayName}
                      </span>
                    </span>
                  </button>
                );
              })
            ) : error ? (
              <p className="px-3 py-3 text-xs text-destructive-foreground">
                Couldn’t reach the geocoder. Try again.
              </p>
            ) : query.trim().length > 0 ? (
              <p className="px-3 py-3 text-xs text-muted-foreground">No matches.</p>
            ) : null}
            <p className="border-t border-border px-3 py-1.5 font-mono text-2xs uppercase tracking-wider text-muted-foreground">
              Powered by OpenStreetMap Nominatim
            </p>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
