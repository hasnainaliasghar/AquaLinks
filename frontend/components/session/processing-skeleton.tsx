"use client";

import { useEffect, useState, type ComponentType } from "react";
import {
  BookOpenText,
  CheckCircle2,
  Circle,
  Gauge,
  Microscope,
  Network,
  Newspaper,
  Satellite,
  Sparkles,
  Waves,
} from "lucide-react";

import { AgentTraceCard } from "@/components/session/agent-trace";
import { Progress } from "@/components/ui/progress";
import type { AOIType, SessionStatus, UUID } from "@/lib/api-types";
import { cn } from "@/lib/utils";

type PipelineStage = {
  key: "fetch" | "indices" | "risk" | "handoff";
  label: string;
  icon: ComponentType<{ className?: string }>;
  /** Foreground tint when running or done. Matches the landing-page
   *  `Pipeline 1 · Deterministic core` palette so the in-app status
   *  block is the same colour vocabulary as the marketing diagram. */
  tint: string;
  /** Border / soft-fill tint used by the stage card frame. */
  frame: { done: string; running: string };
  /** Literal Tailwind class names for the running pulse — derived
   *  forms would be tree-shaken by the JIT compiler, so each stage
   *  carries its own static strings. */
  pulse: { ring: string; dot: string };
};

const STAGES: PipelineStage[] = [
  {
    key: "fetch",
    label: "Fetching imagery",
    icon: Satellite,
    tint: "text-sky-300",
    frame: {
      done: "border-sky-400/35 bg-sky-400/8",
      running: "border-sky-300/45 bg-sky-400/6",
    },
    pulse: { ring: "bg-sky-400/40", dot: "bg-sky-300" },
  },
  {
    key: "indices",
    label: "Computing indices",
    icon: Waves,
    tint: "text-emerald-300",
    frame: {
      done: "border-emerald-400/35 bg-emerald-400/8",
      running: "border-emerald-300/45 bg-emerald-400/6",
    },
    pulse: { ring: "bg-emerald-400/40", dot: "bg-emerald-300" },
  },
  {
    key: "risk",
    label: "Scoring risk",
    icon: Gauge,
    tint: "text-emerald-300",
    frame: {
      done: "border-emerald-400/35 bg-emerald-400/8",
      running: "border-emerald-300/45 bg-emerald-400/6",
    },
    pulse: { ring: "bg-emerald-400/40", dot: "bg-emerald-300" },
  },
  {
    key: "handoff",
    label: "Handover to coordinator",
    icon: Network,
    tint: "text-aqua-300",
    frame: {
      done: "border-aqua-400/35 bg-aqua-400/8",
      running: "border-aqua-300/45 bg-aqua-400/6",
    },
    pulse: { ring: "bg-aqua-400/40", dot: "bg-aqua-300" },
  },
];

function detectStage(status: SessionStatus, message: string | null | undefined): number {
  if (status === "complete" || status === "failed") return 3;
  const m = (message ?? "").toLowerCase();
  if (
    m.includes("coordinator") ||
    m.includes("scout") ||
    m.includes("historian") ||
    m.includes("analyst") ||
    m.includes("reporter") ||
    m.includes("agent")
  ) {
    return 3;
  }
  if (m.includes("report")) return 3;
  if (m.includes("handover") || m.includes("handing over") || m.includes("handoff")) return 3;
  if (m.includes("scoring")) return 2;
  if (m.includes("indices")) return 1;
  if (m.includes("fetching")) return 0;
  return 0;
}

function progressFor(stageIndex: number): number {
  return [12, 42, 72, 100][stageIndex] ?? 12;
}

function pipelineHeadline(message: string | null | undefined): string {
  return message?.trim() || "Queued";
}

type AgentWarmupRow = {
  name: string;
  action: string;
  icon: ComponentType<{ className?: string }>;
  tint: string;
};

// Agent order + colours + action labels match the landing-page
// workflow / agent-constellation and the live AgentTraceCard so the
// warm-up scaffold is the same visual vocabulary.
const AGENT_WARMUP_ROWS: AgentWarmupRow[] = [
  { name: "Coordinator", action: "plans the workflow", icon: Network, tint: "text-aqua-300" },
  { name: "Scout", action: "picks the satellite scene", icon: Satellite, tint: "text-sky-300" },
  { name: "Historian", action: "pulls trends and grounded context", icon: BookOpenText, tint: "text-amber-300" },
  { name: "Analyst", action: "writes and self-critiques the brief", icon: Microscope, tint: "text-violet-300" },
  { name: "Reporter", action: "writes the citizen summary", icon: Newspaper, tint: "text-emerald-300" },
];

function AgentWarmup({ handoffReached }: { handoffReached: boolean }) {
  return (
    <section className="rounded-lg border border-border bg-card p-5" aria-live="polite">
      <header className="flex items-center gap-2">
        <Sparkles className="size-4 text-aqua-400" aria-hidden />
        <h3 className="font-medium text-foreground">Agentic workflow</h3>
      </header>
      <p className="mt-2 text-sm text-muted-foreground">
        {handoffReached
          ? "Coordinator is initialising the live workflow…"
          : "Waiting for the deterministic pipeline to hand the run over…"}
      </p>
      <ol className="mt-4 space-y-2">
        {AGENT_WARMUP_ROWS.map((row, i) => {
          const Icon = row.icon;
          const starting = handoffReached && i === 0;
          return (
            <li
              key={row.name}
              className="flex items-center justify-between gap-3 rounded-md border border-border/70 bg-background/30 px-3 py-2 text-sm"
            >
              <span className="flex min-w-0 items-center gap-2.5 text-foreground/90">
                <Icon className={cn("size-4 shrink-0", row.tint)} aria-hidden />
                <span className="truncate">
                  <span className="font-medium">{row.name}</span>{" "}
                  <span className="text-muted-foreground">·</span>{" "}
                  <span className={row.tint}>{row.action}</span>
                </span>
              </span>
              <span className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                {starting ? "starting…" : "pending"}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function AgentSkipped({
  aoiType,
  waterFraction,
}: {
  aoiType: AOIType | null | undefined;
  waterFraction: number | null | undefined;
}) {
  return (
    <section className="rounded-lg border border-amber-500/35 bg-amber-500/10 p-5">
      <header className="flex items-center gap-2">
        <Sparkles className="size-4 text-amber-300" aria-hidden />
        <h3 className="font-medium text-foreground">Agentic workflow skipped</h3>
      </header>
      <p className="mt-2 text-sm text-foreground/90">
        This AOI was classified as {aoiType ?? "non-water"} (
        {waterFraction !== null && waterFraction !== undefined
          ? `${Math.round(waterFraction * 100)}% water pixels`
          : "water ratio unavailable"}
        ), so specialist agents are skipped for this run.
      </p>
    </section>
  );
}

export function ProcessingSkeleton({
  status,
  message,
  sessionId,
  aoiType,
  waterFraction,
}: {
  status: SessionStatus;
  message: string | null;
  sessionId?: UUID;
  aoiType?: AOIType | null;
  waterFraction?: number | null;
}) {
  const stageIndex = detectStage(status, message);
  const value = progressFor(stageIndex);
  const handoffReached = stageIndex >= 3;
  const shouldRunAgents = aoiType === null || aoiType === undefined || aoiType === "water";
  const [showAgentLive, setShowAgentLive] = useState(false);

  useEffect(() => {
    if (!shouldRunAgents) {
      setShowAgentLive(false);
      return;
    }
    if (!handoffReached) {
      setShowAgentLive(false);
      return;
    }
    const timer = window.setTimeout(() => setShowAgentLive(true), 650);
    return () => window.clearTimeout(timer);
  }, [handoffReached, shouldRunAgents]);

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-border bg-card p-6">
        <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          Deterministic pipeline
        </p>
        <p className="mt-2 font-display text-xl tracking-tight">{pipelineHeadline(message)}</p>
        <Progress className="mt-4" value={value} />
        <ol className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {STAGES.map((stage, i) => {
            const done = i < stageIndex;
            const running = i === stageIndex;
            const Icon = stage.icon;
            return (
              <li
                key={stage.key}
                className={cn(
                  "flex min-h-[74px] flex-col justify-between rounded-md border px-3 py-2 text-2xs transition-colors",
                  done
                    ? cn(stage.frame.done, "text-foreground")
                    : running
                      ? cn(stage.frame.running, "text-foreground")
                      : "border-border/70 bg-background/20 text-muted-foreground",
                )}
              >
                <span className="inline-flex items-start gap-1.5 font-mono uppercase tracking-wider">
                  {done ? (
                    <CheckCircle2 className={cn("size-3.5", stage.tint)} aria-hidden />
                  ) : running ? (
                    <span className="relative inline-flex size-3.5 items-center justify-center" aria-hidden>
                      <span className={cn("absolute inline-flex size-3.5 animate-ping rounded-full", stage.pulse.ring)} />
                      <span className={cn("relative inline-flex size-2 rounded-full", stage.pulse.dot)} />
                    </span>
                  ) : (
                    <Circle className="size-3.5 text-muted-foreground/60" aria-hidden />
                  )}
                  <Icon
                    className={cn(
                      "size-3.5",
                      done || running ? stage.tint : "text-muted-foreground/60",
                    )}
                  />
                  <span className="leading-4">{stage.label}</span>
                </span>
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  {running ? "running..." : done ? "done" : "pending"}
                </p>
              </li>
            );
          })}
        </ol>
      </section>

      {!shouldRunAgents ? (
        <AgentSkipped aoiType={aoiType} waterFraction={waterFraction} />
      ) : sessionId ? (
        showAgentLive ? (
          <AgentTraceCard sessionId={sessionId} sessionStatus={status} />
        ) : (
          <AgentWarmup handoffReached={handoffReached} />
        )
      ) : (
        <AgentWarmup handoffReached={handoffReached} />
      )}
    </div>
  );
}
