"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TermInfo } from "@/components/ui/term-info";
import type { IndexName, SpectralIndex } from "@/lib/api-types";
import { formatNumber } from "@/lib/format";
import type { GlossaryKey } from "@/lib/glossary";
import { cn } from "@/lib/utils";

const RANGE: Record<IndexName, [number, number]> = {
  NDWI: [-1, 1],
  MNDWI: [-1, 1],
  NDTI: [-1, 1],
  NDCI: [-1, 1],
  NDVI: [-1, 1],
  WRI: [0, 3],
};

export const INDEX_GLOSSARY: Record<IndexName, GlossaryKey> = {
  NDWI: "ndwi",
  MNDWI: "mndwi",
  NDTI: "ndti",
  NDCI: "ndci",
  NDVI: "ndvi",
  WRI: "wri",
};

export function IndexGrid({ indices }: { indices: SpectralIndex[] }) {
  if (indices.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          Indices will appear here once the pipeline finishes.
        </CardContent>
      </Card>
    );
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {indices.map((idx) => (
        <IndexCard key={idx.id} index={idx} />
      ))}
    </div>
  );
}

function IndexCard({ index }: { index: SpectralIndex }) {
  const [min, max] = RANGE[index.name];
  // Synthesize a small distribution from the aggregate stats so the chart
  // shows where the masked-mean sits within the index's typical range.
  const series = synthesise(index, min, max);

  return (
    <Card>
      <CardHeader className="gap-1">
        <div className="flex items-center justify-between">
          <CardTitle className="inline-flex items-center gap-1.5 text-base">
            {index.name}
            <TermInfo termKey={INDEX_GLOSSARY[index.name]} />
          </CardTitle>
          <span className={cn("font-mono text-sm", toneFromInterpretation(index.interpretation))}>
            {formatNumber(index.value)}
          </span>
        </div>
        <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          {index.bands.join(" · ")}
        </p>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="h-24 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={series} margin={{ left: 0, right: 0, top: 4, bottom: 0 }}>
              <defs>
                <linearGradient id={`grad-${index.id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--aqua-500)" stopOpacity={0.5} />
                  <stop offset="95%" stopColor="var(--aqua-500)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--border)" strokeDasharray="2 4" vertical={false} />
              <XAxis dataKey="x" hide />
              <YAxis hide domain={[min, max]} />
              <Tooltip
                contentStyle={{
                  background: "var(--popover)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                }}
                labelFormatter={() => ""}
                formatter={(v: number) => [formatNumber(v), index.name]}
              />
              <ReferenceLine y={index.value} stroke="var(--aqua-500)" strokeDasharray="3 3" />
              <Area
                type="monotone"
                dataKey="y"
                stroke="var(--aqua-500)"
                strokeWidth={1.5}
                fill={`url(#grad-${index.id})`}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">{index.interpretation}</p>
      </CardContent>
    </Card>
  );
}

function synthesise(index: SpectralIndex, min: number, max: number) {
  const center = index.value;
  const sd = index.stddev ?? (max - min) * 0.05;
  return Array.from({ length: 24 }).map((_, i) => {
    const t = i / 23;
    const x = min + (max - min) * t;
    const y = Math.exp(-0.5 * Math.pow((x - center) / Math.max(sd, 0.02), 2));
    return { x, y };
  });
}

function toneFromInterpretation(interpretation: string | null): string {
  if (!interpretation) return "text-foreground";
  const lower = interpretation.toLowerCase();
  if (
    lower.includes("high") ||
    lower.includes("bloom") ||
    lower.includes("turbid")
  )
    return "text-risk-high";
  if (lower.includes("elevated") || lower.includes("moderate") || lower.includes("sparse"))
    return "text-risk-medium-fg dark:text-risk-medium";
  return "text-risk-low-fg dark:text-risk-low";
}
