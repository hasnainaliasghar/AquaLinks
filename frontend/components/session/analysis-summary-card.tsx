/**
 * Citizen-facing analysis summary.
 *
 * Renders the plain-English verdict produced by the backend's
 * deterministic citizen-summary service (see
 * ``backend/app/services/citizen_summary.py``). This is the primary
 * answer the end user is reading the session page to get: *Is this
 * water safe? What about pets and kids? What couldn't we check?*
 *
 * The tone (safe / caution / avoid / not_water) drives the colour
 * accent and icon. The detailed agent appendix lives below this panel
 * for users who want the full reasoning trace.
 */

import {
  AlertTriangle,
  ExternalLink,
  HelpCircle,
  Mountain,
  ShieldAlert,
  ShieldCheck,
  Users,
  type LucideIcon,
} from "lucide-react";

import type { CitizenSummary, CitizenSummaryTone } from "@/lib/api-types";
import { cn } from "@/lib/utils";

type ToneMeta = {
  badge: string;
  tile: string;
  ring: string;
  Icon: LucideIcon;
};

const TONES: Record<CitizenSummaryTone, ToneMeta> = {
  safe: {
    badge: "border-risk-low/60 bg-risk-low/10 text-risk-low",
    tile: "border-risk-low/40 bg-risk-low/[0.06]",
    ring: "ring-risk-low/30",
    Icon: ShieldCheck,
  },
  caution: {
    badge: "border-risk-medium/60 bg-risk-medium/10 text-risk-medium",
    tile: "border-risk-medium/40 bg-risk-medium/[0.06]",
    ring: "ring-risk-medium/30",
    Icon: ShieldAlert,
  },
  avoid: {
    badge: "border-risk-high/60 bg-risk-high/10 text-risk-high",
    tile: "border-risk-high/40 bg-risk-high/[0.07]",
    ring: "ring-risk-high/30",
    Icon: AlertTriangle,
  },
  not_water: {
    badge: "border-amber-500/60 bg-amber-500/10 text-amber-300",
    tile: "border-amber-500/40 bg-amber-500/[0.06]",
    ring: "ring-amber-500/30",
    Icon: Mountain,
  },
  unknown: {
    badge: "border-border/70 bg-muted/30 text-muted-foreground",
    tile: "border-border bg-background/40",
    ring: "ring-border",
    Icon: HelpCircle,
  },
};

const TONE_LABEL: Record<CitizenSummaryTone, string> = {
  safe: "Likely safe",
  caution: "Use caution",
  avoid: "Avoid contact",
  not_water: "Not water",
  unknown: "Pending",
};

export function AnalysisSummaryCard({ summary }: { summary: CitizenSummary }) {
  const meta = TONES[summary.tone] ?? TONES.unknown;
  const HeadlineIcon = meta.Icon;
  return (
    <section
      className={cn(
        "rounded-lg border p-5 ring-1",
        meta.tile,
        meta.ring,
      )}
      aria-label="Analysis summary"
    >
      <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="flex items-start gap-3">
          <span
            className={cn(
              "inline-flex size-9 shrink-0 items-center justify-center rounded-md border",
              meta.badge,
            )}
            aria-hidden
          >
            <HeadlineIcon className="size-4" />
          </span>
          <div>
            <p
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 font-mono text-2xs uppercase tracking-wider",
                meta.badge,
              )}
            >
              {TONE_LABEL[summary.tone]}
            </p>
            <h3 className="mt-1.5 text-lg font-medium text-foreground">
              {summary.headline}
            </h3>
          </div>
        </div>
      </header>

      <p className="mt-3 text-sm leading-relaxed text-foreground/90">
        {summary.bottom_line}
      </p>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <DetailTile
          icon={Users}
          title="For you"
          body={summary.safety_for_humans}
        />
        <DetailTile
          icon={ShieldCheck}
          title="For pets and kids"
          body={summary.safety_for_pets_and_kids}
        />
      </div>

      <div className="mt-3 rounded-md border border-border/60 bg-background/50 p-3 text-xs text-muted-foreground">
        <p className="mb-1 inline-flex items-center gap-1.5 font-mono text-2xs uppercase tracking-wider text-foreground/80">
          <HelpCircle className="size-3" aria-hidden />
          What we couldn't check
        </p>
        <p className="leading-relaxed">{summary.what_we_could_not_check}</p>
      </div>

      {summary.citations.length > 0 ? (
        <div className="mt-3 rounded-md border border-border/60 bg-background/50 p-3 text-xs text-muted-foreground">
          <p className="mb-2 inline-flex items-center gap-1.5 font-mono text-2xs uppercase tracking-wider text-foreground/80">
            <ExternalLink className="size-3" aria-hidden />
            Sources
          </p>
          <ul className="space-y-1.5">
            {summary.citations.slice(0, 4).map((c) => (
              <li key={c.uri}>
                <a
                  className="inline-flex items-center gap-1 text-aqua-300 hover:text-aqua-200 hover:underline"
                  href={c.uri}
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  {c.title?.trim() || c.uri}
                  <ExternalLink className="size-3" aria-hidden />
                </a>
                {c.published_at ? (
                  <p className="mt-0.5 text-2xs text-muted-foreground">{c.published_at}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function DetailTile({
  icon: Icon,
  title,
  body,
}: {
  icon: LucideIcon;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-md border border-border/60 bg-background/50 p-3">
      <p className="inline-flex items-center gap-1.5 font-mono text-2xs uppercase tracking-wider text-foreground/80">
        <Icon className="size-3" aria-hidden />
        {title}
      </p>
      <p className="mt-1.5 text-sm leading-relaxed text-foreground/85">{body}</p>
    </div>
  );
}

export function AnalysisSummaryNotice({ summary }: { summary: CitizenSummary }) {
  // Compact version used in places where a small inline banner is
  // preferable to a full card (e.g. the report page header).
  const meta = TONES[summary.tone] ?? TONES.unknown;
  const Icon = meta.Icon;
  return (
    <p
      className={cn(
        "inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs",
        meta.badge,
      )}
    >
      <Icon className="size-3.5" aria-hidden />
      <span className="font-medium">{TONE_LABEL[summary.tone]}</span>
      <span className="opacity-80">— {summary.headline}</span>
    </p>
  );
}
