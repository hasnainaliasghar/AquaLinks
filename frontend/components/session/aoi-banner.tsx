import { AlertTriangle, Droplet, Mountain } from "lucide-react";

import type { AOIType } from "@/lib/api-types";
import { cn } from "@/lib/utils";

/**
 * Surfaces the result of the combined NDWI ∧ MNDWI water-fraction sanity
 * check. When the AOI is mostly land we shout about it loudly so the user
 * doesn't read the spectral indices as a water-quality measurement.
 */
export function AOIBanner({
  aoiType,
  waterFraction,
  className,
}: {
  aoiType: AOIType | null;
  waterFraction: number | null;
  className?: string;
}) {
  if (!aoiType || aoiType === "water") return null;

  const isLand = aoiType === "land";
  const Icon = isLand ? Mountain : AlertTriangle;
  const fractionLabel =
    waterFraction !== null ? `${Math.round(waterFraction * 100)}% water pixels` : null;

  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-3 rounded-md border px-4 py-3 text-sm",
        isLand
          ? "border-risk-high/40 bg-risk-high/10 text-risk-high-fg dark:text-risk-high"
          : "border-risk-medium/40 bg-risk-medium/10 text-risk-medium-fg dark:text-risk-medium",
        className,
      )}
    >
      <Icon className={cn("mt-0.5 size-5 shrink-0")} aria-hidden />
      <div className="space-y-1">
        <p className="font-semibold">
          {isLand ? "This AOI is mostly land" : "Mixed water and land AOI"}
        </p>
        <p className="text-foreground/85">
          {isLand ? (
            <>
              Less than 20% of the polygon passes the open-water test
              (NDWI &gt; 0 <em>and</em> MNDWI &gt; 0). Spectral water-quality
              indices like NDCI and NDTI are <em>not</em> measuring water here —
              they reflect vegetation, soil, or built-up surfaces. Move the AOI
              over an actual water body and re-run before relying on the risk
              score.
            </>
          ) : (
            <>
              Only part of the polygon passes the open-water test
              (NDWI &gt; 0 <em>and</em> MNDWI &gt; 0). Water-quality indices over
              the water portion still apply, but land pixels dilute the signal —
              treat the score as approximate.
            </>
          )}
        </p>
        {fractionLabel ? (
          <p className="font-mono text-2xs uppercase tracking-wider opacity-80">
            {fractionLabel}
          </p>
        ) : null}
      </div>
    </div>
  );
}

/** Compact pill-style version for chips and metadata strips. */
export function AOITypeBadge({
  aoiType,
  className,
}: {
  aoiType: AOIType | null;
  className?: string;
}) {
  if (!aoiType) return null;
  const Icon = aoiType === "land" ? Mountain : Droplet;
  const tone =
    aoiType === "land"
      ? "border-risk-high/45 bg-risk-high/15 text-risk-high-fg dark:text-risk-high"
      : aoiType === "mixed"
        ? "border-risk-medium/45 bg-risk-medium/15 text-risk-medium-fg dark:text-risk-medium"
        : "border-risk-low/45 bg-risk-low/15 text-risk-low-fg dark:text-risk-low";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-2xs font-medium uppercase tracking-wider",
        tone,
        className,
      )}
    >
      <Icon className="size-3" aria-hidden />
      {aoiType === "water" ? "Water AOI" : aoiType === "mixed" ? "Mixed AOI" : "Land AOI"}
    </span>
  );
}
