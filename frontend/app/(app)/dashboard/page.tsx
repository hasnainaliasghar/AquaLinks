"use client";

import Link from "next/link";
import { ArrowRight, Droplet, Loader2 } from "lucide-react";

import { SessionCard } from "@/components/session/session-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { FadeIn } from "@/components/motion/fade-in";
import { AnimatedNumber } from "@/components/motion/animated-number";
import { useSessions } from "@/hooks/use-sessions";
import { useWaterBodies } from "@/hooks/use-water-bodies";
import { formatArea } from "@/lib/format";
import { formatLocationLabel, pointToLatLng } from "@/lib/location";

export default function DashboardPage() {
  const sessions = useSessions({ limit: 12 });
  const waterBodies = useWaterBodies();

  const totalSessions = sessions.data?.length ?? 0;
  const totalWaterBodies = waterBodies.data?.length ?? 0;
  const averageRisk =
    sessions.data && sessions.data.length > 0
      ? sessions.data.reduce((acc, s) => acc + (s.risk_score ?? 0), 0) /
        Math.max(1, sessions.data.filter((s) => s.risk_score !== null).length)
      : 0;

  return (
    <div className="container max-w-7xl py-10">
      <FadeIn>
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
              Overview
            </p>
            <h1 className="mt-1 font-display text-3xl tracking-tight sm:text-4xl">
              Dashboard
            </h1>
            <p className="mt-2 max-w-xl text-muted-foreground">
              A glance at the freshest pipeline runs, the water bodies you’re watching,
              and the average risk across active sessions.
            </p>
          </div>
          <Button asChild>
            <Link href="/monitor">
              Start a session
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        </header>
      </FadeIn>

      <section className="mt-8 grid gap-3 sm:grid-cols-3">
        <FadeIn>
          <Stat
            label="Sessions tracked"
            value={
              <AnimatedNumber
                value={totalSessions}
                format={(n) => Math.round(n).toString()}
              />
            }
          />
        </FadeIn>
        <FadeIn delay={0.05}>
          <Stat
            label="Water bodies"
            value={
              <AnimatedNumber
                value={totalWaterBodies}
                format={(n) => Math.round(n).toString()}
              />
            }
          />
        </FadeIn>
        <FadeIn delay={0.1}>
          <Stat
            label="Average risk"
            value={
              <AnimatedNumber
                value={averageRisk * 100}
                format={(n) => `${Math.round(n)} / 100`}
              />
            }
          />
        </FadeIn>
      </section>

      <section className="mt-10 grid gap-6 lg:grid-cols-[2fr_1fr]">
        <FadeIn>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Recent sessions</CardTitle>
              <Link
                href="/sessions"
                className="font-mono text-2xs uppercase tracking-wider text-muted-foreground hover:text-foreground"
              >
                View all
              </Link>
            </CardHeader>
            <CardContent className="space-y-3">
              {sessions.isLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-28 w-full rounded-md" />
                ))
              ) : sessions.data && sessions.data.length > 0 ? (
                sessions.data.slice(0, 5).map((s) => <SessionCard key={s.id} session={s} />)
              ) : (
                <EmptyState />
              )}
            </CardContent>
          </Card>
        </FadeIn>
        <FadeIn delay={0.1}>
          <Card>
            <CardHeader>
              <CardTitle>Water bodies</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {waterBodies.isLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-3.5 animate-spin" />
                  Loading…
                </div>
              ) : waterBodies.data && waterBodies.data.length > 0 ? (
                waterBodies.data.map((wb) => {
                  const centroid = pointToLatLng(wb.centroid);
                  const locationLabel = formatLocationLabel({
                    name: wb.name,
                    lat: centroid?.lat ?? null,
                    lng: centroid?.lng ?? null,
                    digits: 3,
                  });
                  return (
                    <Link
                      key={wb.id}
                      href={`/water-bodies/${wb.id}`}
                      className="flex items-center justify-between gap-3 rounded-sm border border-border bg-surface-1 px-3 py-2 text-sm transition-colors hover:border-aqua-500/40"
                    >
                      <span className="inline-flex items-center gap-2">
                        <Droplet className="size-3.5 text-aqua-500" />
                        <span className="line-clamp-1">{locationLabel}</span>
                      </span>
                      <span className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                        {formatArea(wb.area_km2)}
                      </span>
                    </Link>
                  );
                })
              ) : (
                <p className="text-sm text-muted-foreground">
                  No water bodies yet. Pick an area on the monitor page to save one.
                </p>
              )}
            </CardContent>
          </Card>
        </FadeIn>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Card>
      <CardContent className="space-y-1 p-5">
        <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          {label}
        </p>
        <p className="font-display text-3xl tracking-tight">{value}</p>
      </CardContent>
    </Card>
  );
}

function EmptyState() {
  return (
    <div className="rounded-md border border-dashed border-border bg-surface-1 p-8 text-center">
      <p className="font-display text-lg tracking-tight">Start your first session</p>
      <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
        Pick a lake or river on the map — search a place, paste coordinates, or tap
        the map. The pipeline runs in under a minute on a clean scene.
      </p>
      <Button asChild className="mt-4">
        <Link href="/monitor">Open monitor</Link>
      </Button>
    </div>
  );
}
