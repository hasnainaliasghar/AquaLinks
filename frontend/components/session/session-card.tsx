import Link from "next/link";

import { StatusPill } from "@/components/session/status-pill";
import { Card } from "@/components/ui/card";
import type { MonitoringSessionListItem } from "@/lib/api-types";
import { formatDateTime, formatRelative } from "@/lib/format";
import { formatLocationLabel } from "@/lib/location";
import { cn } from "@/lib/utils";

const LEVEL_TONE: Record<string, string> = {
  high: "ring-risk-high/40 hover:ring-risk-high/70",
  medium: "ring-risk-medium/40 hover:ring-risk-medium/70",
  low: "ring-risk-low/40 hover:ring-risk-low/70",
};

export function SessionCard({ session }: { session: MonitoringSessionListItem }) {
  const tone = session.risk_level ? LEVEL_TONE[session.risk_level] : "ring-border hover:ring-aqua-500/40";
  const locationLabel = formatLocationLabel({
    name: session.water_body_name,
    lat: session.water_body_latitude,
    lng: session.water_body_longitude,
    digits: 3,
  });
  return (
    <Link
      href={`/sessions/${session.id}`}
      className={cn(
        "group block rounded-xl ring-1 ring-inset transition-[transform,box-shadow] duration-200 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-aqua-500",
        tone,
      )}
    >
      <Card className="border-0 ring-0 transition-shadow group-hover:shadow-elev-2">
        <div className="space-y-4 p-5">
          <header className="flex items-center justify-between gap-3">
            <h3 className="line-clamp-1 font-display text-lg tracking-tight">
              {locationLabel}
            </h3>
            <StatusPill status={session.status} />
          </header>
          <div className="flex items-end justify-between gap-4">
            <div className="space-y-1 text-xs text-muted-foreground">
              <p>
                Window <span className="font-mono">{session.start_date}</span> →{" "}
                <span className="font-mono">{session.end_date}</span>
              </p>
              <p>
                {session.scene_capture_date
                  ? `Scene captured ${formatDateTime(session.scene_capture_date)}`
                  : "Awaiting scene"}
              </p>
              <p>Updated {formatRelative(session.updated_at)}</p>
            </div>
            {session.risk_score !== null && session.risk_level ? (
              <div className="text-right">
                <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                  Risk
                </p>
                <p
                  className={cn(
                    "font-display text-2xl tracking-tight",
                    session.risk_level === "high" && "text-risk-high",
                    session.risk_level === "medium" && "text-risk-medium",
                    session.risk_level === "low" && "text-risk-low",
                  )}
                >
                  {(session.risk_score * 100).toFixed(0)}
                </p>
                <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                  / 100
                </p>
              </div>
            ) : null}
          </div>
        </div>
      </Card>
    </Link>
  );
}
