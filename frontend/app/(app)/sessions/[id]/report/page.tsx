"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { FadeIn } from "@/components/motion/fade-in";
import { DownloadReportButton } from "@/components/report/download-button";
import { AgentTraceCard } from "@/components/session/agent-trace";
import { AnalysisSummaryCard } from "@/components/session/analysis-summary-card";
import { IndexTable } from "@/components/session/index-table";
import { RiskCard } from "@/components/session/risk-card";
import { SceneMetadata } from "@/components/session/scene-metadata";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSession } from "@/hooks/use-sessions";
import { formatLocationLabel, pointToLatLng } from "@/lib/location";

export default function ReportPage() {
  const params = useParams<{ id: string }>();
  const { data, isLoading } = useSession(params.id);

  if (isLoading || !data) {
    return (
      <div className="container max-w-3xl py-10">
        <p className="text-sm text-muted-foreground">Loading report…</p>
      </div>
    );
  }
  const centroid = pointToLatLng(data.water_body.centroid);
  const locationLabel = formatLocationLabel({
    name: data.water_body.name,
    lat: centroid?.lat ?? null,
    lng: centroid?.lng ?? null,
    digits: 3,
  });

  return (
    <article className="container max-w-3xl py-10 print:py-0">
      <FadeIn>
        <header className="flex flex-wrap items-end justify-between gap-3 print:hidden">
          <Link
            href={`/sessions/${data.id}`}
            className="inline-flex items-center gap-1 font-mono text-2xs uppercase tracking-wider text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-3" /> Session
          </Link>
          <DownloadReportButton sessionId={data.id} />
        </header>
      </FadeIn>

      <FadeIn>
        <div className="mt-6 space-y-2 border-b border-border pb-6">
          <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
            Analysis report
          </p>
          <h1 className="font-display text-4xl tracking-tight">{locationLabel}</h1>
          <p className="text-muted-foreground">
            Window {data.start_date} → {data.end_date}
          </p>
        </div>
      </FadeIn>

      {data.risk ? (
        <FadeIn>
          <div className="mt-8">
            <RiskCard risk={data.risk} />
          </div>
        </FadeIn>
      ) : null}

      {data.citizen_summary ? (
        <FadeIn>
          <div className="mt-8">
            <AnalysisSummaryCard summary={data.citizen_summary} />
          </div>
        </FadeIn>
      ) : null}

      <FadeIn>
        <div className="mt-8">
          <SceneMetadata session={data} />
        </div>
      </FadeIn>

      {data.indices.length > 0 ? (
        <FadeIn>
          <div className="mt-8">
            <IndexTable indices={data.indices} />
          </div>
        </FadeIn>
      ) : null}

      <FadeIn>
        <div className="mt-8">
          <AgentTraceCard sessionId={data.id} sessionStatus={data.status} />
        </div>
      </FadeIn>

      {data.evidence.length > 0 ? (
        <FadeIn>
          <div className="mt-8">
            <Card>
              <CardHeader>
                <CardTitle>Field evidence</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {data.evidence.map((ev) => (
                  <div
                    key={ev.id}
                    className="rounded-sm border border-border bg-surface-1 p-3 text-sm"
                  >
                    <p>
                      <span className="font-medium">{ev.water_color} water</span> ·{" "}
                      {ev.odor} odor · algae {ev.algae_present ? "yes" : "no"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Dead fish: {ev.dead_fish_count} · Rainfall: {ev.rainfall_mm.toFixed(1)} mm ·
                      Complaints: {ev.complaints_count}
                    </p>
                    {ev.notes ? <p className="mt-1 italic">{ev.notes}</p> : null}
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </FadeIn>
      ) : null}

      <footer className="mt-12 border-t border-border pt-6 text-xs text-muted-foreground">
        AquaLinks · advisory only · Sentinel-2 imagery © European Union, contains modified
        Copernicus Sentinel data accessed via the Microsoft Planetary Computer.
      </footer>
    </article>
  );
}
