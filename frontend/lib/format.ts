const NUMBER_NEUTRAL = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 3,
  minimumFractionDigits: 3,
});

const INTEGER = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

const DATE = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
});

const DATE_TIME = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short",
});

const RELATIVE = new Intl.RelativeTimeFormat("en-US", { numeric: "auto" });

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return NUMBER_NEUTRAL.format(value);
}

export function formatInt(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return INTEGER.format(value);
}

export function formatPercent(value: number | null | undefined, fraction = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value.toFixed(fraction)}%`;
}

export function formatArea(km2: number | null | undefined): string {
  if (km2 === null || km2 === undefined || Number.isNaN(km2)) return "—";
  if (km2 < 0.01) return `${(km2 * 1_000_000).toFixed(0)} m²`;
  if (km2 < 1) return `${(km2 * 100).toFixed(2)} ha`;
  return `${km2.toFixed(2)} km²`;
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  return DATE.format(d);
}

export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  return DATE_TIME.format(d);
}

/**
 * Sentinel-2 product IDs look like
 * ``S2C_MSIL2A_20260512T055631_R091_T42RUQ_20260512T102111`` — useful for
 * cross-referencing but unreadable in the UI. This helper returns a
 * humanised summary plus the raw value so callers can show both.
 */
export function formatSceneId(id: string | null | undefined): {
  compact: string;
  full: string;
} {
  if (!id) return { compact: "—", full: "—" };
  const parts = id.split("_");
  if (parts.length < 5) return { compact: id, full: id };
  const platform = parts[0];
  const dt = parts[2];
  const tile = parts[4];
  if (!platform || !dt || dt.length < 8 || !tile) return { compact: id, full: id };
  const date = `${dt.slice(0, 4)}-${dt.slice(4, 6)}-${dt.slice(6, 8)}`;
  return { compact: `${platform} · ${date} · ${tile}`, full: id };
}

export function formatRelative(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  const diff = d.getTime() - Date.now();
  const seconds = Math.round(diff / 1_000);
  const minutes = Math.round(seconds / 60);
  const hours = Math.round(minutes / 60);
  const days = Math.round(hours / 24);
  if (Math.abs(seconds) < 60) return RELATIVE.format(seconds, "second");
  if (Math.abs(minutes) < 60) return RELATIVE.format(minutes, "minute");
  if (Math.abs(hours) < 24) return RELATIVE.format(hours, "hour");
  return RELATIVE.format(days, "day");
}
