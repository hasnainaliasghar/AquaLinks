"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { FadeIn } from "@/components/motion/fade-in";
import { SessionCard } from "@/components/session/session-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { WaterBodyActions } from "@/components/water-body/water-body-actions";
import { api } from "@/lib/api-client";
import type { IndexName, SpectralIndex } from "@/lib/api-types";
import { formatArea, formatDate } from "@/lib/format";
import { formatLocationLabel, pointToLatLng } from "@/lib/location";
import { queryKeys } from "@/lib/query-keys";

const MiniMap = dynamic(() => import("@/components/map/mini-map").then((m) => m.MiniMap), {
  ssr: false,
});

const INDEX_ORDER: IndexName[] = ["NDCI", "NDTI", "NDWI", "MNDWI", "NDVI", "WRI"];

export default function WaterBodyDetail() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const waterBody = useQuery({
    queryKey: queryKeys.waterBody(id),
    queryFn: () => api.getWaterBody(id),
  });
  const sessions = useQuery({
    queryKey: queryKeys.sessions({ water_body_id: id }),
    queryFn: () => api.listSessions({ water_body_id: id, limit: 100 }),
  });

  const trendsQuery = useQuery({
    queryKey: ["water-body-trends", id, sessions.data?.length ?? 0],
    enabled: Boolean(sessions.data && sessions.data.length > 0),
    queryFn: async () => {
      const indicesBySession = await Promise.all(
        (sessions.data ?? []).map(async (s) => ({
          session: s,
          indices: await api.getIndices(s.id),
        })),
      );
      return indicesBySession;
    },
  });

  if (!waterBody.data) {
    return (
      <div className="container max-w-5xl py-10 text-sm text-muted-foreground">
        Loading water body…
      </div>
    );
  }

  const wb = waterBody.data;
  const centroid = pointToLatLng(wb.centroid);
  const locationLabel = formatLocationLabel({
    name: wb.name,
    lat: centroid?.lat ?? null,
    lng: centroid?.lng ?? null,
    digits: 3,
  });
  const trendData = (trendsQuery.data ?? [])
    .map(({ session, indices }) => ({
      session,
      indices,
    }))
    .sort(
      (a, b) =>
        new Date(a.session.created_at).getTime() -
        new Date(b.session.created_at).getTime(),
    );

  return (
    <div className="container max-w-7xl py-10">
      <FadeIn>
        <Link
          href="/water-bodies"
          className="inline-flex items-center gap-1 font-mono text-2xs uppercase tracking-wider text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3" /> Water bodies
        </Link>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="font-display text-3xl tracking-tight sm:text-4xl">{locationLabel}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {formatArea(wb.area_km2)} · added {formatDate(wb.created_at)}
            </p>
          </div>
          <WaterBodyActions waterBody={wb} />
        </div>
      </FadeIn>

      <div className="mt-8 grid gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="space-y-6">
          <FadeIn>
            <Card>
              <CardHeader>
                <CardTitle>Index trends</CardTitle>
              </CardHeader>
              <CardContent className="h-72">
                {trendData.length < 2 ? (
                  <p className="grid h-full place-items-center text-sm text-muted-foreground">
                    Add a few more sessions to see trends here.
                  </p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={trendData.map(({ session, indices }) => {
                        const row: Record<string, number | string> = {
                          date: formatDate(session.scene_capture_date ?? session.created_at),
                        };
                        for (const name of INDEX_ORDER) {
                          const idx = indices.find((i: SpectralIndex) => i.name === name);
                          row[name] = idx?.value ?? Number.NaN;
                        }
                        return row;
                      })}
                    >
                      <CartesianGrid strokeDasharray="2 4" stroke="var(--border)" />
                      <XAxis dataKey="date" stroke="var(--muted-foreground)" fontSize={10} />
                      <YAxis stroke="var(--muted-foreground)" fontSize={10} />
                      <Tooltip
                        contentStyle={{
                          background: "var(--popover)",
                          border: "1px solid var(--border)",
                          borderRadius: 8,
                          fontFamily: "var(--font-mono)",
                          fontSize: 11,
                        }}
                      />
                      {INDEX_ORDER.map((name, i) => (
                        <Line
                          key={name}
                          type="monotone"
                          dataKey={name}
                          stroke={`oklch(0.6 0.13 ${180 + i * 20})`}
                          strokeWidth={1.5}
                          dot={false}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </FadeIn>

          <FadeIn>
            <Card>
              <CardHeader>
                <CardTitle>Sessions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {sessions.data && sessions.data.length > 0 ? (
                  sessions.data.map((s) => <SessionCard key={s.id} session={s} />)
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No sessions yet for this water body. Start one from the monitor page.
                  </p>
                )}
              </CardContent>
            </Card>
          </FadeIn>
        </section>

        <aside className="lg:sticky lg:top-6 lg:self-start">
          <FadeIn>
            <Card>
              <CardContent className="space-y-3 p-5">
                <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                  Area of interest
                </p>
                <MiniMap polygon={wb.geometry} />
              </CardContent>
            </Card>
          </FadeIn>
        </aside>
      </div>
    </div>
  );
}
