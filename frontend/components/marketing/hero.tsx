"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { RiskLevel } from "@/lib/api-types";
import { cn } from "@/lib/utils";

export function Hero() {
  const reduce = useReducedMotion();
  return (
    <section className="relative isolate overflow-hidden">
      <div className="absolute inset-0 -z-10 grid-bg opacity-60" aria-hidden />
      <div
        className="absolute inset-x-0 -top-32 -z-10 mx-auto h-[600px] w-[700px] max-w-full rounded-full bg-aqua-500/20 blur-[120px]"
        aria-hidden
      />

      <div className="container relative flex flex-col items-center pt-24 pb-20 text-center sm:pt-32 sm:pb-28">
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-2xs font-medium uppercase tracking-wider text-muted-foreground shadow-elev-1"
        >
          <span className="size-1.5 animate-pulse rounded-full bg-risk-low" />
          Live remote-sensing pipeline · advisory only
        </motion.div>

        <motion.h1
          initial={reduce ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 0.08 }}
          className="max-w-4xl font-display text-balance text-5xl leading-[1.05] tracking-tight sm:text-6xl"
        >
          The water you can{" "}
          <span className="bg-gradient-to-br from-aqua-300 via-aqua-500 to-aqua-700 bg-clip-text text-transparent">
            actually monitor
          </span>
          .
        </motion.h1>

        <motion.p
          initial={reduce ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 0.16 }}
          className="mt-5 max-w-2xl text-balance text-base text-muted-foreground sm:text-lg"
        >
          AquaLinks pulls recent Sentinel-2 imagery, computes six water-quality indices,
          fuses optional field evidence, and writes a grounded risk brief — so the field
          team knows where to sample first.
        </motion.p>

        <motion.div
          initial={reduce ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 0.22 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <Button asChild size="lg">
            <Link href="/monitor" className="group">
              Start monitoring
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/methodology">View methodology</Link>
          </Button>
        </motion.div>

        <motion.div
          initial={reduce ? false : { opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.32 }}
          className="mt-14 w-full max-w-5xl"
        >
          <HeroScene />
        </motion.div>
      </div>
    </section>
  );
}

/**
 * A frozen example session used for the marketing hero. These are the
 * real numbers from a Sentinel-2 run on a 4 km² AOI near 48.893°N · 16.543°E
 * (session 7b7bf413), captured on 2026-05-03 at 4.0% cloud cover. We
 * deliberately don't wire the hero to live API data — pinning a known
 * session means the marketing card is consistent across visits and the
 * numbers can be cross-checked against the matching PDF report.
 */
type Tone = "low" | "medium" | "high";

type ExampleSession = {
  heading: string;
  level: RiskLevel;
  scoreLabel: string;
  urgency: string;
  rows: { key: string; label: string; value: string; tone: Tone }[];
  recommendation: string;
};

const EXAMPLE: ExampleSession = {
  heading: "aqualinks · session 8599f3 · 49.239°N · 16.510°E",
  level: "medium",
  scoreLabel: "Medium · 0.46",
  urgency: "Routine urgency",
  rows: [
    { key: "NDCI", label: "NDCI", value: "+0.122", tone: "medium" },
    { key: "NDVI", label: "NDVI shore", value: "+0.326", tone: "medium" },
    { key: "MNDWI", label: "MNDWI", value: "-0.174", tone: "high" },
    { key: "NDTI", label: "NDTI", value: "-0.048", tone: "low" },
  ],
  recommendation:
    "“Given the conflicting spectral signals and the indication of elevated chlorophyll-a, we recommend a follow-up investigation — potentially including in-situ sampling — to clarify the water body's conditions and confirm any algal activity.”",
};

function HeroScene() {
  return (
    <div className="relative overflow-hidden rounded-xl border border-border bg-card shadow-elev-4">
      <div className="flex items-center gap-1.5 border-b border-border bg-surface-2 px-4 py-2">
        <span className="size-2.5 rounded-full bg-risk-high/80" />
        <span className="size-2.5 rounded-full bg-risk-medium/80" />
        <span className="size-2.5 rounded-full bg-risk-low/80" />
        <span className="ml-3 truncate font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          {EXAMPLE.heading}
        </span>
        <span className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-muted px-2 py-0.5 font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          <span className="size-1.5 rounded-full bg-muted-foreground" />
          Sample
        </span>
      </div>
      <div className="grid gap-px bg-border sm:grid-cols-[1.4fr_1fr]">
        <div className="aspect-[16/10] bg-surface-1 p-6">
          <Heatmap />
        </div>
        <div className="space-y-4 bg-surface-0 p-6 text-left">
          <div>
            <p className="text-2xs font-medium uppercase tracking-wider text-muted-foreground">
              Risk
            </p>
            <p
              className={cn(
                "font-display text-2xl",
                EXAMPLE.level === "high" && "text-risk-high",
                EXAMPLE.level === "medium" && "text-risk-medium",
                EXAMPLE.level === "low" && "text-risk-low",
              )}
            >
              {EXAMPLE.scoreLabel}
            </p>
            <p className="text-xs text-muted-foreground">{EXAMPLE.urgency}</p>
          </div>
          <div className="space-y-2 text-xs">
            {EXAMPLE.rows.map((row) => (
              <Row key={row.key} label={row.label} value={row.value} tone={row.tone} />
            ))}
          </div>
          <div className="rounded-sm border border-border bg-surface-1 p-3 text-xs text-muted-foreground">
            {EXAMPLE.recommendation}
          </div>
        </div>
      </div>
    </div>
  );
}

function Heatmap() {
  // Bias the heatmap intensity to match the example session's risk level
  // — a Medium · 0.39 run shouldn't read as red-dominant.
  const intensityBias =
    EXAMPLE.level === "high" ? 1 : EXAMPLE.level === "medium" ? 0.55 : 0.3;
  return (
    <div className="grid h-full grid-cols-6 grid-rows-6 gap-1">
      {Array.from({ length: 36 }).map((_, i) => {
        const row = Math.floor(i / 6);
        const col = i % 6;
        const dx = col - 2.5;
        const dy = row - 2.5;
        const r = Math.sqrt(dx * dx + dy * dy);
        const intensity = Math.max(0, 1 - r / 4) * intensityBias;
        const color =
          intensity > 0.66
            ? "var(--risk-high)"
            : intensity > 0.33
              ? "var(--risk-medium)"
              : "var(--risk-low)";
        return (
          <div
            key={i}
            className="rounded-xs"
            style={{ background: color, opacity: 0.18 + intensity * 0.55 }}
          />
        );
      })}
    </div>
  );
}

function Row({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "low" | "medium" | "high";
}) {
  const color =
    tone === "high"
      ? "bg-risk-high/30 text-risk-high-fg dark:text-risk-high"
      : tone === "medium"
        ? "bg-risk-medium/30 text-risk-medium-fg dark:text-risk-medium"
        : "bg-risk-low/30 text-risk-low-fg dark:text-risk-low";
  return (
    <div className="flex items-center justify-between gap-3 rounded-xs border border-border bg-card px-3 py-2">
      <span className={cn("font-mono text-2xs uppercase tracking-wider text-muted-foreground")}>
        {label}
      </span>
      <span className={`rounded-full px-2 py-0.5 font-mono text-2xs ${color}`}>{value}</span>
    </div>
  );
}
