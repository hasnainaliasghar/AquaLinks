"use client";

import { Check, Copy } from "lucide-react";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TermInfo } from "@/components/ui/term-info";
import type { MonitoringSessionDetail } from "@/lib/api-types";
import { formatDateTime, formatPercent, formatSceneId } from "@/lib/format";
import { formatLocationLabel, pointToLatLng } from "@/lib/location";
import type { GlossaryKey } from "@/lib/glossary";
import { cn } from "@/lib/utils";

export function SceneMetadata({ session }: { session: MonitoringSessionDetail }) {
  const sceneId = formatSceneId(session.scene_id);
  const centroid = pointToLatLng(session.water_body.centroid);
  const aoiLabel = formatLocationLabel({
    name: session.water_body.name,
    lat: centroid?.lat ?? null,
    lng: centroid?.lng ?? null,
    digits: 3,
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle className="inline-flex items-center gap-2">
          Scene metadata
          <TermInfo termKey="sentinel2" />
        </CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
          <Item label="Provider" termKey="provider">
            <span>{session.scene_provider ?? "—"}</span>
          </Item>
          <Item label="Scene ID" termKey="sceneId">
            <span className="block font-medium">{sceneId.compact}</span>
            {session.scene_id && sceneId.compact !== sceneId.full ? (
              <span className="mt-1 flex items-start gap-2">
                <span className="block min-w-0 flex-1 break-all font-mono text-2xs text-muted-foreground">
                  {sceneId.full}
                </span>
                <CopyButton value={sceneId.full} label="scene ID" />
              </span>
            ) : null}
          </Item>
          <Item label="Captured">
            <span>{formatDateTime(session.scene_capture_date)}</span>
          </Item>
          <Item label="Cloud cover" termKey="cloudCover">
            <span>{formatPercent(session.scene_cloud_cover, 1)}</span>
          </Item>
          <Item label="AOI" termKey="aoi">
            <span>{aoiLabel}</span>
          </Item>
          <Item label="Window">
            <span>
              {session.start_date} → {session.end_date}
            </span>
          </Item>
        </dl>
      </CardContent>
    </Card>
  );
}

function Item({
  label,
  termKey,
  children,
}: {
  label: string;
  termKey?: GlossaryKey;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-0.5 border-b border-border/60 pb-2 last:border-b-0">
      <dt className="inline-flex items-center gap-1.5 font-mono text-2xs uppercase tracking-wider text-muted-foreground">
        {label}
        {termKey ? <TermInfo termKey={termKey} /> : null}
      </dt>
      <dd className="text-sm text-foreground">{children}</dd>
    </div>
  );
}

function CopyButton({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      aria-label={`Copy ${label}`}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          toast.success("Copied to clipboard");
          window.setTimeout(() => setCopied(false), 1600);
        } catch {
          toast.error("Couldn't copy to clipboard");
        }
      }}
      className={cn(
        "inline-flex size-5 shrink-0 items-center justify-center rounded-xs border border-border text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground",
        copied && "border-aqua-500/50 text-aqua-500",
      )}
    >
      {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
    </button>
  );
}
