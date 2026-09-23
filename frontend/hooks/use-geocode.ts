"use client";

import { useEffect, useState } from "react";

import {
  geocode,
  parseCoords,
  type GeocodeResult,
} from "@/lib/geocode";

type State = {
  results: GeocodeResult[];
  coords: { lat: number; lng: number } | null;
  loading: boolean;
  error: string | null;
};

const EMPTY: State = { results: [], coords: null, loading: false, error: null };

/**
 * Debounced place + coordinate search.
 *
 * Detects pure decimal coordinate input ("45.987, 9.252") synchronously
 * and skips the network call. Otherwise debounces 350 ms and queries
 * Nominatim. Aborts in-flight requests when the query changes.
 */
export function useGeocodeSearch(query: string): State {
  const [state, setState] = useState<State>(EMPTY);

  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      setState(EMPTY);
      return;
    }

    const coords = parseCoords(trimmed);
    if (coords) {
      setState({ results: [], coords, loading: false, error: null });
      return;
    }

    const controller = new AbortController();
    setState((prev) => ({ ...prev, loading: true, error: null }));
    const timeout = setTimeout(async () => {
      try {
        const results = await geocode(trimmed, controller.signal);
        setState({ results, coords: null, loading: false, error: null });
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setState({
          results: [],
          coords: null,
          loading: false,
          error: (err as Error).message,
        });
      }
    }, 350);

    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, [query]);

  return state;
}
