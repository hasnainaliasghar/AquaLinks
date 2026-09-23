import { describe, expect, it } from "vitest";

import { formatArea, formatNumber, formatPercent } from "@/lib/format";

describe("format helpers", () => {
  it("formatNumber pads to three decimals", () => {
    expect(formatNumber(0.5)).toBe("0.500");
    expect(formatNumber(-0.1234)).toBe("-0.123");
    expect(formatNumber(null)).toBe("—");
    expect(formatNumber(undefined)).toBe("—");
  });

  it("formatPercent appends a % sign", () => {
    expect(formatPercent(12.34, 1)).toBe("12.3%");
    expect(formatPercent(null)).toBe("—");
  });

  it("formatArea chooses sensible units", () => {
    expect(formatArea(0.0001)).toContain("m²");
    expect(formatArea(0.5)).toContain("ha");
    expect(formatArea(7.21)).toContain("km²");
  });
});
