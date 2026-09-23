import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { FieldEvidence } from "@/lib/api-types";
import { formatRelative } from "@/lib/format";
import { env } from "@/lib/env";

export function EvidenceList({ items }: { items: FieldEvidence[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Evidence timeline</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No field evidence yet. The mobile companion lets the team add observations on
            the spot.
          </p>
        ) : (
          <ol className="relative space-y-5 border-l border-border pl-6">
            {items.map((ev) => (
              <li key={ev.id} className="relative">
                <span className="absolute -left-[27px] mt-1 size-2.5 rounded-full bg-aqua-500 ring-4 ring-card" />
                <div className="flex flex-wrap items-baseline gap-x-3">
                  <p className="font-medium">
                    {ev.water_color} water · {ev.odor} odor
                  </p>
                  <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                    {formatRelative(ev.created_at)}
                  </p>
                </div>
                <p className="text-sm text-muted-foreground">
                  Algae: {ev.algae_present ? "yes" : "no"} · Dead fish: {ev.dead_fish_count} ·{" "}
                  Rainfall: {ev.rainfall_mm.toFixed(1)} mm · Complaints: {ev.complaints_count}
                </p>
                {ev.notes ? (
                  <p className="mt-1 rounded-sm border border-border bg-surface-1 p-3 text-sm">
                    {ev.notes}
                  </p>
                ) : null}
                {ev.photo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={`${env.NEXT_PUBLIC_API_URL}${ev.photo_url}`}
                    alt="Field photo"
                    className="mt-2 h-40 w-full rounded-md border border-border object-cover"
                  />
                ) : null}
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
