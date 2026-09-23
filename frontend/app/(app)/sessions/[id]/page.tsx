"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertTriangle, ArrowLeft, FileText, Mountain, Plus } from "lucide-react";

import { EvidenceList } from "@/components/evidence/evidence-list";
import { FadeIn } from "@/components/motion/fade-in";
import { DownloadReportButton } from "@/components/report/download-button";
import { AOIBanner, AOITypeBadge } from "@/components/session/aoi-banner";
import { AgentTraceCard } from "@/components/session/agent-trace";
import { AnalysisSummaryCard } from "@/components/session/analysis-summary-card";
import { IndexGrid } from "@/components/session/index-grid";
import { IndexTable } from "@/components/session/index-table";
import { ProcessingSkeleton } from "@/components/session/processing-skeleton";
import { RiskCard } from "@/components/session/risk-card";
import { SceneMetadata } from "@/components/session/scene-metadata";
import { StatusPill } from "@/components/session/status-pill";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useSession } from "@/hooks/use-sessions";
import type { RiskLevel } from "@/lib/api-types";
import { cn } from "@/lib/utils";
import { formatRelative } from "@/lib/format";
import { formatLocationLabel, pointToLatLng } from "@/lib/location";

const MiniMap = dynamic(() => import("@/components/map/mini-map").then((m) => m.MiniMap), {
  ssr: false,
});

export default function SessionDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const { data, isLoading, isError } = useSession(id, { polling: true });

  if (isLoading || !data) {
    return (
      <div className="container max-w-6xl py-10">
        <ProcessingSkeleton status="processing" message="Loading session" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="container max-w-6xl py-10">
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            Couldn’t load this session. Try refreshing the page.
          </CardContent>
        </Card>
      </div>
    );
  }

  const stillRunning = data.status === "processing" || data.status === "pending";
  const isFailed = data.status === "failed";
  const hasIndices = data.indices.length > 0;
  const aoiIsWater = !data.aoi_type || data.aoi_type === "water";
  const centroid = pointToLatLng(data.water_body.centroid);
  const locationLabel = formatLocationLabel({
    name: data.water_body.name,
    lat: centroid?.lat ?? null,
    lng: centroid?.lng ?? null,
    digits: 3,
  });

  return (
    <div className="container max-w-7xl py-10">
      <FadeIn>
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <Link
              href="/sessions"
              className="inline-flex items-center gap-1 font-mono text-2xs uppercase tracking-wider text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="size-3" /> Sessions
            </Link>
            <h1 className="mt-2 font-display text-3xl tracking-tight sm:text-4xl">
              {locationLabel}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Updated {formatRelative(data.updated_at)} ·{" "}
              <span className="font-mono">{data.id}</span>
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill status={data.status} />
            <AOITypeBadge aoiType={data.aoi_type} />
            <Button asChild variant="outline" size="sm">
              <Link href={`/sessions/${data.id}/evidence`}>
                <Plus className="size-3.5" /> Add evidence
              </Link>
            </Button>
            {data.report_id ? (
              <DownloadReportButton sessionId={data.id} className="h-9 px-3 text-xs" />
            ) : null}
            <Button asChild variant="outline" size="sm">
              <Link href={`/sessions/${data.id}/report`}>
                <FileText className="size-3.5" /> Open report
              </Link>
            </Button>
          </div>
        </header>
      </FadeIn>

      <div className="mt-8 grid gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="space-y-6">
          {stillRunning ? (
            <ProcessingSkeleton
              status={data.status}
              message={data.status_message}
              sessionId={data.id}
              aoiType={data.aoi_type}
              waterFraction={data.water_fraction}
            />
          ) : (
            <>
              {isFailed ? (
                <FadeIn>
                  <FailureNotice message={data.status_message} />
                </FadeIn>
              ) : null}
              {data.aoi_type && data.aoi_type !== "water" ? (
                <FadeIn>
                  <AOIBanner aoiType={data.aoi_type} waterFraction={data.water_fraction} />
                </FadeIn>
              ) : null}
              <FadeIn>
                <SceneMetadata session={data} />
              </FadeIn>
              {hasIndices ? (
                <>
                  <FadeIn>
                    <IndexGrid indices={data.indices} />
                  </FadeIn>
                  <FadeIn>
                    <IndexTable indices={data.indices} />
                  </FadeIn>
                </>
              ) : (
                <Card className="border-dashed">
                  <CardContent className="py-8 text-sm text-muted-foreground">
                    No indices were stored before the pipeline failed.
                  </CardContent>
                </Card>
              )}
              {data.risk ? (
                <FadeIn>
                  <RiskCard risk={data.risk} />
                </FadeIn>
              ) : null}
              {data.citizen_summary ? (
                <FadeIn>
                  <AnalysisSummaryCard summary={data.citizen_summary} />
                </FadeIn>
              ) : null}
              {aoiIsWater ? (
                <FadeIn>
                  <AgentTraceCard sessionId={data.id} sessionStatus={data.status} />
                </FadeIn>
              ) : (
                <FadeIn>
                  <NoAgentLayerNotice />
                </FadeIn>
              )}
              <FadeIn>
                <EvidenceList items={data.evidence} />
              </FadeIn>
            </>
          )}
        </section>
        <aside className="space-y-6 lg:sticky lg:top-6 lg:self-start">
          <FadeIn>
            <Card>
              <CardContent className="space-y-3 p-5">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                    Area of interest
                  </p>
                  {!aoiIsWater ? (
                    <span className="inline-flex items-center gap-1 rounded-md border border-amber-500/50 bg-amber-500/10 px-1.5 py-0.5 text-2xs font-medium text-amber-300">
                      <Mountain className="size-3" aria-hidden /> Not water
                    </span>
                  ) : null}
                </div>
                <MiniMap polygon={data.water_body.geometry} />
              </CardContent>
            </Card>
          </FadeIn>
          {!stillRunning && data.risk ? (
            <FadeIn>
              <Card>
                <CardContent className="space-y-3 p-5">
                  <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                    Key metrics
                  </p>
                  <TintedMetric
                    label="Risk score"
                    value={`${(data.risk.score * 100).toFixed(0)} / 100`}
                    level={data.risk.level}
                    emphasis
                  />
                  <TintedMetric
                    label="Level"
                    value={data.risk.level}
                    level={data.risk.level}
                  />
                  <TintedMetric
                    label="Urgency"
                    value={data.risk.urgency}
                    level={data.risk.level}
                    subtle
                  />
                  <Metric label="Model" value={data.risk.model_id} mono />
                </CardContent>
              </Card>
            </FadeIn>
          ) : null}
        </aside>
      </div>
    </div>
  );
}

function FailureNotice({ message }: { message: string | null }) {
  const detail = (message ?? "No backend error message was provided.").trim();
  return (
    <Card className="border-risk-high/35 bg-risk-high/10">
      <CardContent className="space-y-3 p-5">
        <p className="inline-flex items-center gap-1.5 font-mono text-2xs uppercase tracking-wider text-risk-high">
          <AlertTriangle className="size-3.5" /> Pipeline failed
        </p>
        <p className="text-sm text-foreground/90">
          This run stopped before completion. Use these error details to debug the backend.
        </p>
        <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-xs border border-risk-high/30 bg-background/70 p-3 font-mono text-2xs leading-relaxed text-foreground">
          {detail}
        </pre>
      </CardContent>
    </Card>
  );
}

function Metric({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-border/60 pb-2 last:border-b-0">
      <span className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className={mono ? "font-mono text-sm" : "text-sm capitalize"}>{value}</span>
    </div>
  );
}

const LEVEL_TONE: Record<RiskLevel, { value: string; chip: string; dot: string }> = {
  low: {
    value: "text-risk-low",
    chip: "border-risk-low/60 bg-risk-low/15 text-risk-low",
    dot: "bg-risk-low",
  },
  medium: {
    value: "text-risk-medium",
    chip: "border-risk-medium/60 bg-risk-medium/15 text-risk-medium",
    dot: "bg-risk-medium",
  },
  high: {
    value: "text-risk-high",
    chip: "border-risk-high/60 bg-risk-high/15 text-risk-high",
    dot: "bg-risk-high",
  },
};

function TintedMetric({
  label,
  value,
  level,
  emphasis,
  subtle,
}: {
  label: string;
  value: string;
  level: RiskLevel;
  /** Render the value with stronger color weight (used for the score). */
  emphasis?: boolean;
  /** Render the value as a colored dot + capitalized text (urgency). */
  subtle?: boolean;
}) {
  const tone = LEVEL_TONE[level];
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2 last:border-b-0">
      <span className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      {subtle ? (
        <span className="inline-flex items-center gap-1.5 text-sm capitalize text-foreground">
          <span className={cn("inline-block size-1.5 rounded-full", tone.dot)} aria-hidden />
          {value}
        </span>
      ) : emphasis ? (
        <span className={cn("font-mono text-base font-semibold", tone.value)}>{value}</span>
      ) : (
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium capitalize",
            tone.chip,
          )}
        >
          {value}
        </span>
      )}
    </div>
  );
}

function NoAgentLayerNotice() {
  return (
    <Card className="border-amber-500/40 bg-amber-500/[0.04]">
      <CardContent className="flex items-start gap-3 p-5">
        <Mountain className="mt-0.5 size-5 shrink-0 text-amber-300" aria-hidden />
        <div className="space-y-1.5">
          <p className="font-medium text-foreground">
            We skipped the deeper analysis for this area
          </p>
          <p className="text-sm text-muted-foreground">
            The area you picked isn't water, so running the multi-agent layer
            wouldn't add anything useful — and would burn compute we'd rather
            spend on real water bodies. Pick a lake, river, or coastal patch
            and try again.
          </p>
          <Link
            href="/water-bodies"
            className="inline-flex items-center gap-1 text-sm font-medium text-emerald-300 hover:text-emerald-200"
          >
            Pick another area
            <ArrowLeft className="size-3 rotate-180" aria-hidden />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
