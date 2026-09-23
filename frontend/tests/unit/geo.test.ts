import { describe, expect, it } from "vitest";

import { isValidPolygon, polygonAreaKm2, polygonCentroid } from "@/lib/geo";
import type { GeoJSONPolygon } from "@/lib/api-types";

const SQUARE: GeoJSONPolygon = {
  type: "Polygon",
  coordinates: [
    [
      [9.2, 45.95],
      [9.3, 45.95],
      [9.3, 46.02],
      [9.2, 46.02],
      [9.2, 45.95],
    ],
  ],
};

describe("geo helpers", () => {
  it("computes a positive area in km²", () => {
    expect(polygonAreaKm2(SQUARE)).toBeGreaterThan(0);
  });

  it("returns a centroid inside the polygon", () => {
    const [lon, lat] = polygonCentroid(SQUARE);
    expect(lon).toBeGreaterThan(9.2);
    expect(lon).toBeLessThan(9.3);
    expect(lat).toBeGreaterThan(45.95);
    expect(lat).toBeLessThan(46.02);
  });

  it("rejects unclosed rings", () => {
    const broken: GeoJSONPolygon = {
      type: "Polygon",
      coordinates: [
        [
          [0, 0],
          [1, 0],
          [1, 1],
        ],
      ],
    };
    expect(isValidPolygon(broken)).toBe(false);
    expect(isValidPolygon(SQUARE)).toBe(true);
  });
});
