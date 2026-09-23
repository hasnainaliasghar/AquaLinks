"use client";

/**
 * Field Brief card.
 *
 * Renders the Field Liaison agent's structured ops handoff: a list of
 * prioritised sampling tasks, recommended equipment, photo prompts,
 * the turnaround target and any escalation note.
 *
 * Gracefully renders nothing when no brief exists — happens for
 * legacy sessions, sessions processed with the agent layer off, or
 * runs where the Field Liaison failed AND the deterministic fallback
 * was also unavailable.
 */
import {
  AlertOctagon,
  AlertTriangle,
  Camera,
  CheckCircle2,
  ClipboardList,
  Clock,
  Hourglass,
  MapPin,
  Wrench,
  type LucideIcon,
} from "lucide-react";

import type { FieldBrief, FieldTask, SessionStatus, UUID } from "@/lib/api-types";
import { cn } from "@/lib/utils";

import { useFieldBrief } from "@/hooks/use-agent-trace";

type PriorityMeta = {
  label: string;
  description: string;
  icon: LucideIcon;
  tone: string;
};

/**
 * Priority chips: lucide icon + plain-English subtitle so the field
 * team doesn't have to translate "P0/P1/P2" in their head. The
 * underlying priority codes are still emitted by the agent for any
 * downstream system that expects them.
 */
const PRIORITY: Record<FieldTask["priority"], PriorityMeta> = {
  p0: {
    label: "Do today",
    description: "Highest priority — within 24 hours",
    icon: AlertOctagon,
    tone: "border-risk-high/60 bg-risk-high/10 text-risk-high",
  },
  p1: {
    label: "Do this week",
    description: "Important — within a few days",
    icon: AlertTriangle,
    tone: "border-risk-medium/60 bg-risk-medium/10 text-risk-medium",
  },
  p2: {
    label: "Routine check",
    description: "Standard cadence — next planned visit",
    icon: CheckCircle2,
    tone: "border-risk-low/60 bg-risk-low/10 text-risk-low",
  },
};

export function FieldBriefCard({
  sessionId,
  sessionStatus,
}: {
  sessionId: UUID;
  sessionStatus?: SessionStatus;
}) {
  const { data } = useFieldBrief(sessionId, sessionStatus);
  if (!data) return null;

  return <FieldBriefView brief={data} />;
}

export function FieldBriefView({ brief }: { brief: FieldBrief }) {
  return (
    <section
      className="rounded-lg border border-border bg-card p-5"
      aria-label="Plan for the field team"
    >
      <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="flex items-center gap-2.5">
          <ClipboardList className="size-5 text-emerald-300" aria-hidden />
          <div>
            <h3 className="font-medium text-foreground">Plan for the field team</h3>
            <p className="text-xs text-muted-foreground">
              What to check, where to check it, and what to bring.
            </p>
          </div>
        </div>
        <span
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background/60 px-2 py-1 text-xs text-muted-foreground"
          aria-label={`Recommended finish-by window: ${friendlyTurnaround(brief.turnaround_hours)}`}
        >
          <Hourglass className="size-3.5" aria-hidden />
          Finish within {friendlyTurnaround(brief.turnaround_hours)}
        </span>
      </header>

      {brief.escalate_to ? (
        <p className="mt-3 flex items-center gap-2 rounded-md border border-risk-high/50 bg-risk-high/10 p-2 text-sm text-risk-high">
          <AlertOctagon className="size-4 shrink-0" aria-hidden />
          Let the {brief.escalate_to} know — this needs eyes today.
        </p>
      ) : null}

      <ol className="mt-4 space-y-3">
        {brief.tasks.map((task, i) => (
          <TaskCard key={`task-${i}`} task={task} index={i + 1} />
        ))}
      </ol>
    </section>
  );
}

function TaskCard({ task, index }: { task: FieldTask; index: number }) {
  const meta = PRIORITY[task.priority];
  const Icon = meta.icon;
  return (
    <li className="rounded-md border border-border bg-background/40 p-3">
      <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-2xs font-medium",
              meta.tone,
            )}
          >
            <Icon className="size-3.5" aria-hidden />
            {meta.label}
          </span>
          <span className="text-2xs uppercase tracking-wider text-muted-foreground">
            Step {index}
          </span>
        </div>
        <span className="inline-flex items-center gap-1 text-2xs text-muted-foreground">
          <Clock className="size-3" aria-hidden />
          ~{task.estimated_minutes} min
        </span>
      </div>

      <p className="mt-2 text-sm font-medium text-foreground">{prettySampleType(task.sample_type)}</p>

      <p className="mt-1.5 flex items-start gap-1.5 text-xs text-muted-foreground">
        <MapPin className="mt-0.5 size-3 shrink-0" aria-hidden />
        <span>
          {prettyLocation(task.location.description)}
          <br />
          <span className="font-mono text-2xs">
            {task.location.lat.toFixed(4)}, {task.location.lng.toFixed(4)}
          </span>
        </span>
      </p>

      {task.equipment.length > 0 ? (
        <div className="mt-2 text-xs text-muted-foreground">
          <span className="mr-1 inline-flex items-center gap-1 font-medium text-foreground">
            <Wrench className="size-3" aria-hidden /> Bring
          </span>
          {task.equipment.join(", ")}
        </div>
      ) : null}

      {task.photo_prompts.length > 0 ? (
        <div className="mt-2 text-xs text-muted-foreground">
          <p className="mb-1 flex items-center gap-1 font-medium text-foreground">
            <Camera className="size-3" aria-hidden /> Photos to capture
          </p>
          <ul className="space-y-1 pl-4">
            {task.photo_prompts.map((prompt, j) => (
              <li key={`prompt-${j}`} className="list-disc">
                {prompt}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className="mt-2 text-2xs italic text-muted-foreground" title={meta.description}>
        {meta.description}
      </p>
    </li>
  );
}

/** Turn 24/48/72/168 into "1 day"/"2 days"/"3 days"/"a week". */
function friendlyTurnaround(hours: number): string {
  if (hours <= 24) return "24 hours";
  if (hours <= 48) return "2 days";
  if (hours <= 72) return "3 days";
  if (hours <= 168) return "a week";
  const days = Math.round(hours / 24);
  return `${days} days`;
}

/** Replace common jargon with plain-English equivalents. */
function prettySampleType(value: string): string {
  const v = value.toLowerCase();
  if (v.includes("grab water sample")) {
    return "Take a water sample" + (v.includes("chlorophyll") ? " (for chlorophyll-a test)" : "");
  }
  if (v.includes("baseline visual inspection") || v.includes("visual inspection")) {
    return "Walk-around visual check";
  }
  return value;
}

/** Replace "AOI centroid" with plain language; keep coordinates as-is. */
function prettyLocation(description: string): string {
  return description
    .replace(/AOI centroid/gi, "Centre of the chosen area")
    .replace(/\(fallback[^)]*\)/i, "")
    .trim();
}
