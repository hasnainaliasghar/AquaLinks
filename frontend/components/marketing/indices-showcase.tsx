"use client";

import { useState } from "react";

import { FadeIn } from "@/components/motion/fade-in";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TermInfo } from "@/components/ui/term-info";
import type { GlossaryKey } from "@/lib/glossary";
import { cn } from "@/lib/utils";

type Index = {
  key: "NDWI" | "MNDWI" | "NDTI" | "NDCI" | "NDVI" | "WRI";
  title: string;
  formula: string;
  caption: string;
  glossary: GlossaryKey;
  /** Value in (-1..1) used to colorize the heatmap preview. */
  drive: number;
};

const INDICES: Index[] = [
  {
    key: "NDWI",
    title: "Normalized Difference Water Index",
    formula: "(NIR − SWIR) / (NIR + SWIR)",
    caption: "Tells us where water actually is in the scene.",
    glossary: "ndwi",
    drive: 0.55,
  },
  {
    key: "MNDWI",
    title: "Modified NDWI",
    formula: "(Green − SWIR) / (Green + SWIR)",
    caption: "Same idea as NDWI but trustworthy in cities.",
    glossary: "mndwi",
    drive: 0.62,
  },
  {
    key: "NDTI",
    title: "Turbidity",
    formula: "(Red − Green) / (Red + Green)",
    caption: "How murky the water looks — a stand-in for suspended sediment.",
    glossary: "ndti",
    drive: 0.22,
  },
  {
    key: "NDCI",
    title: "Chlorophyll proxy",
    formula: "(RedEdge − Red) / (RedEdge + Red)",
    caption: "An early-warning for algal blooms (not a confirmed measurement).",
    glossary: "ndci",
    drive: 0.46,
  },
  {
    key: "NDVI",
    title: "Shoreline vegetation",
    formula: "(NIR − Red) / (NIR + Red)",
    caption: "Stress in the bordering vegetation often hints at water-quality changes.",
    glossary: "ndvi",
    drive: 0.32,
  },
  {
    key: "WRI",
    title: "Water Ratio Index",
    formula: "(Green + Red) / (NIR + SWIR)",
    caption: "A second water-vs-land moisture signal that complements NDWI.",
    glossary: "wri",
    drive: 0.7,
  },
];

export function IndicesShowcase() {
  const [active, setActive] = useState<Index>(INDICES[0]!);
  return (
    <section className="container py-24 sm:py-32">
      <FadeIn>
        <header className="mx-auto max-w-2xl text-center">
          <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
            Spectral indices
          </p>
          <h2 className="mt-2 font-display text-3xl tracking-tight sm:text-4xl">
            Six band-math views of the same scene.
          </h2>
          <p className="mt-4 text-balance text-muted-foreground">
            Each index isolates a different water-quality signal. AquaLinks computes them
            on the same Sentinel-2 acquisition and aggregates over the water mask.
          </p>
        </header>
      </FadeIn>

      <div className="mt-12 grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <FadeIn className="space-y-2">
          {INDICES.map((idx) => {
            const selected = active.key === idx.key;
            return (
              <div
                key={idx.key}
                className={cn(
                  "flex items-stretch gap-2 rounded-md border transition-[border-color,background-color]",
                  selected
                    ? "border-aqua-500/50 bg-accent"
                    : "border-border bg-card hover:border-aqua-500/30",
                )}
              >
                <button
                  type="button"
                  onClick={() => setActive(idx)}
                  aria-pressed={selected}
                  className="flex flex-1 items-start gap-3 px-4 py-3 text-left text-foreground"
                >
                  <span className="mt-0.5 inline-flex h-6 min-w-12 items-center justify-center rounded-xs border border-border bg-surface-2 px-1.5 font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                    {idx.key}
                  </span>
                  <span className="flex-1">
                    <span className="block text-sm font-medium">{idx.title}</span>
                    <span className="block text-xs text-muted-foreground">{idx.caption}</span>
                  </span>
                </button>
                <div className="flex shrink-0 items-start py-3 pr-3">
                  <TermInfo termKey={idx.glossary} side="right" />
                </div>
              </div>
            );
          })}
        </FadeIn>

        <FadeIn className="overflow-hidden rounded-xl border border-border bg-card shadow-elev-2">
          <div className="grid h-full grid-rows-[1fr_auto]">
            <Heatmap drive={active.drive} indexKey={active.key} />
            <div className="space-y-3 border-t border-border bg-surface-1 p-6">
              <div className="flex items-center justify-between gap-3">
                <h3 className="inline-flex items-center gap-2 font-display text-xl tracking-tight">
                  {active.title}
                  <TermInfo termKey={active.glossary} />
                </h3>
                <Badge variant="aqua">{active.key}</Badge>
              </div>
              <p className="font-mono text-sm">
                <span className="text-muted-foreground">formula · </span>
                {active.formula}
              </p>
              <p className="text-sm text-muted-foreground">{active.caption}</p>
              <div className="flex flex-wrap gap-2 pt-2">
                <Button asChild variant="outline" size="sm">
                  <a href="/methodology">Open methodology</a>
                </Button>
                <Button asChild size="sm">
                  <a href="/monitor">Try with your AOI</a>
                </Button>
              </div>
            </div>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}

function Heatmap({ drive, indexKey }: { drive: number; indexKey: string }) {
  const cells = 12 * 8;
  return (
    <div className="grid h-full min-h-[260px] grid-cols-12 grid-rows-8 gap-px bg-border p-2">
      {Array.from({ length: cells }).map((_, i) => {
        const row = Math.floor(i / 12);
        const col = i % 12;
        const dx = (col - 5.5) / 6;
        const dy = (row - 3.5) / 4;
        const r = Math.sqrt(dx * dx + dy * dy);
        const noise = ((Math.sin(i * 1.3) + Math.cos(i * 0.7)) + 2) / 4;
        const t = Math.max(0, Math.min(1, drive * (1 - r) + 0.3 * noise));
        const hue = indexKey === "NDCI" ? 145 : indexKey === "NDTI" ? 40 : 200;
        return (
          <div
            key={i}
            className="rounded-[2px]"
            style={{ background: `oklch(${0.34 + t * 0.45} ${0.08 + t * 0.12} ${hue})` }}
          />
        );
      })}
    </div>
  );
}
