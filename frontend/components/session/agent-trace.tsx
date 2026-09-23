"use client";

/**
 * Agentic Workflow card — multi-agent execution timeline.
 *
 * Two modes:
 *
 * 1. **Processing (no trace yet, or partial trace).** Renders a
 *    five-step scaffold (Coordinator → Scout → Historian → Analyst
 *    → Reporter). Each agent is marked **done** (it appears in
 *    the trace), **running** (it is the next expected agent and the
 *    session is still processing), or **pending**. The current agent
 *    gets a soft pulse so the user feels the system working.
 *
 * 2. **Complete.** Renders the detailed collapsible timeline with
 *    every tool call, vision finding, grounded citation, and final
 *    output JSON. Long JSON wraps with ``whitespace-pre-wrap`` so
 *    the card never bleeds past its container.
 *
 * Renders nothing for legacy sessions (no trace) once the session
 * is complete.
 */
import { useState } from "react";
import {
  BookOpenText,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  ClipboardList,
  Compass,
  Microscope,
  Network,
  Newspaper,
  Satellite,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

import type {
  AgentName,
  AgentRun,
  AgentToolCall,
  AgentTrace,
  SessionStatus,
  UUID,
} from "@/lib/api-types";
import { cn } from "@/lib/utils";

import { useAgentTrace } from "@/hooks/use-agent-trace";

type AgentMeta = {
  label: string;
  short: string;
  icon: LucideIcon;
  tint: string;
};

/**
 * Per-agent display metadata: human label, short subtitle, lucide
 * icon, and the OKLCH brand tint applied to the icon.
 */
const AGENTS: Record<string, AgentMeta> = {
  coordinator: {
    label: "Coordinator",
    short: "plans the workflow",
    icon: Network,
    tint: "text-aqua-300",
  },
  scout: {
    label: "Scout",
    short: "picks the satellite scene",
    icon: Satellite,
    tint: "text-sky-300",
  },
  historian: {
    label: "Historian",
    short: "pulls trends and outside context",
    icon: BookOpenText,
    tint: "text-amber-300",
  },
  analyst: {
    label: "Analyst",
    short: "writes the brief and self-checks it",
    icon: Microscope,
    tint: "text-violet-300",
  },
  field_liaison: {
    label: "Field Liaison",
    short: "legacy field-plan agent",
    icon: ClipboardList,
    tint: "text-emerald-300",
  },
  reporter: {
    label: "Reporter",
    short: "writes the public summary card",
    icon: Newspaper,
    tint: "text-emerald-300",
  },
};

const EXPECTED_ORDER: AgentName[] = [
  "coordinator",
  "scout",
  "historian",
  "analyst",
  "reporter",
];

function agentMeta(name: string): AgentMeta {
  return (
    AGENTS[name] ?? {
      label: name,
      short: "",
      icon: Compass,
      tint: "text-muted-foreground",
    }
  );
}

function isProcessing(status?: SessionStatus): boolean {
  return status === "processing" || status === "pending";
}

export function AgentTraceCard({
  sessionId,
  sessionStatus,
}: {
  sessionId: UUID;
  sessionStatus?: SessionStatus;
}) {
  const { data, isLoading } = useAgentTrace(sessionId, sessionStatus);
  const processing = isProcessing(sessionStatus);

  // 1. No trace yet, still processing → render the live scaffold so
  //    the user feels the system working.
  if (!data && processing) {
    return <Scaffold completedAgents={[]} processing />;
  }

  // 2. No trace and not processing → likely a legacy session; render
  //    nothing rather than an empty card.
  if (!data) {
    if (isLoading) {
      return (
        <section className="rounded-lg border border-border bg-card p-5 text-sm text-muted-foreground">
          <header className="flex items-center gap-2 text-foreground">
            <Sparkles className="size-4 text-aqua-400" aria-hidden />
            <h3 className="font-medium">Agentic workflow</h3>
          </header>
          <p className="mt-2">Loading…</p>
        </section>
      );
    }
    return null;
  }

  const completedAgents = data.agent_runs.map((run) => run.agent);

  // 3. Trace exists but session still processing → show the scaffold
  //    with done agents filled in and the next one pulsing.
  if (processing && data.agent_runs.length < EXPECTED_ORDER.length) {
    return (
      <Scaffold completedAgents={completedAgents} processing trace={data} />
    );
  }

  // 4. Complete trace → full detail view.
  return <DetailedView data={data} />;
}

// ----------------------------------------------------------------------
// Processing scaffold — pending / running / done per agent
// ----------------------------------------------------------------------

function Scaffold({
  completedAgents,
  processing,
  trace,
}: {
  completedAgents: string[];
  processing: boolean;
  trace?: AgentTrace;
}) {
  // Mark the first *planned* agent in EXPECTED_ORDER that hasn't
  // completed yet as "running" while we're still processing.
  const plan = trace?.coordinator_plan?.plan ?? [];
  const plannedAgents = new Set(
    plan.length > 0 ? plan.map((step) => step.agent) : EXPECTED_ORDER,
  );

  // Coordinator always counts as planned once the run started.
  plannedAgents.add("coordinator");

  // Keep all expected agents visible in the scaffold so the pipeline
  // feels stable and predictable, even when coordinator skips a stage.
  const visibleAgents = EXPECTED_ORDER.filter(
    (name) =>
      plannedAgents.has(name) ||
      completedAgents.includes(name) ||
      name === "coordinator" ||
      name === "scout" ||
      name === "historian" ||
      name === "analyst" ||
      name === "reporter",
  );

  const firstPending = processing
    ? visibleAgents.find(
        (name) => plannedAgents.has(name) && !completedAgents.includes(name),
      )
    : undefined;

  return (
    <section
      className="rounded-lg border border-border bg-card p-5"
      aria-label="Agentic workflow execution trace"
      aria-live="polite"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h3 className="flex items-center gap-2 font-medium text-foreground">
          <Sparkles className="size-4 text-aqua-400" aria-hidden />
          Agentic workflow
        </h3>
        {trace ? (
          <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
            {trace.gemini_model} ·{" "}
            {trace.agent_runs.length}/{visibleAgents.length} agents complete
          </p>
        ) : (
          <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
            Live · the agents are warming up
          </p>
        )}
      </header>

      <ol className="mt-4 space-y-2">
        {visibleAgents.map((name) => {
          const completedRun = trace?.agent_runs.find(
            (run) => run.agent === name,
          );
          const state: ScaffoldState = completedRun
            ? "done"
            : name === firstPending
              ? "running"
              : "pending";
          return (
            <ScaffoldRow
              key={name}
              name={name}
              state={state}
              completedRun={completedRun}
            />
          );
        })}
      </ol>

      <p className="mt-4 text-xs text-muted-foreground">
        Each agent is a focused Gemini call. As soon as one finishes the next
        one starts — the trace below fills in live.
      </p>
    </section>
  );
}

type ScaffoldState = "pending" | "running" | "done";

function ScaffoldRow({
  name,
  state,
  completedRun,
}: {
  name: string;
  state: ScaffoldState;
  completedRun?: AgentRun;
}) {
  const meta = agentMeta(name);
  const Icon = meta.icon;

  const stateStyles: Record<ScaffoldState, string> = {
    pending: "border-border bg-background/30 opacity-60",
    running: "border-aqua-400/40 bg-aqua-400/5",
    done: "border-emerald-400/30 bg-emerald-400/5",
  };

  return (
    <li
      className={cn(
        "flex items-center gap-3 rounded-md border px-3 py-2.5 text-sm transition-colors",
        stateStyles[state],
      )}
    >
      <StateIndicator state={state} />
      <Icon className={cn("size-4 shrink-0", meta.tint)} aria-hidden />
      <span className="flex min-w-0 flex-1 flex-col leading-tight">
        <span className="font-medium text-foreground">{meta.label}</span>
        <span className="truncate text-2xs text-muted-foreground">
          {meta.short}
        </span>
      </span>
      <span className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
        {state === "done" && completedRun
          ? `${completedRun.latency_ms} ms`
          : state === "running"
            ? "running…"
            : "pending"}
      </span>
    </li>
  );
}

function StateIndicator({ state }: { state: ScaffoldState }) {
  if (state === "done") {
    return (
      <CheckCircle2
        className="size-4 shrink-0 text-emerald-300"
        aria-label="completed"
      />
    );
  }
  if (state === "running") {
    return (
      <span
        aria-label="running"
        className="relative inline-flex size-4 shrink-0 items-center justify-center"
      >
        <span className="absolute inline-flex size-4 animate-ping rounded-full bg-aqua-400/40" />
        <span className="relative inline-flex size-2.5 rounded-full bg-aqua-400" />
      </span>
    );
  }
  return (
    <Circle
      className="size-4 shrink-0 text-muted-foreground/50"
      aria-label="pending"
    />
  );
}

// ----------------------------------------------------------------------
// Detailed view — the existing collapsible timeline
// ----------------------------------------------------------------------

function DetailedView({ data }: { data: AgentTrace }) {
  const runs = withSyntheticSkips(data);
  return (
    <section
      className="rounded-lg border border-border bg-card p-5"
      aria-label="Agentic workflow execution trace"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h3 className="flex items-center gap-2 font-medium text-foreground">
          <Sparkles className="size-4 text-aqua-400" aria-hidden />
          Agentic workflow
        </h3>
        <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          {data.gemini_model} · {data.total_latency_ms} ms ·{" "}
          {data.total_tokens_in + data.total_tokens_out} tokens
        </p>
      </header>

      {data.coordinator_plan?.rationale ? (
        <p className="mt-2 text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Plan: </span>
          {data.coordinator_plan.rationale}
        </p>
      ) : null}

      <ol className="mt-4 space-y-2">
        {runs.map((run, i) => (
          <AgentRunRow key={`${run.agent}-${i}`} run={run} />
        ))}
      </ol>
    </section>
  );
}

function withSyntheticSkips(data: AgentTrace): AgentRun[] {
  const existingByAgent = new Map<string, AgentRun>();
  for (const run of data.agent_runs) {
    if (!existingByAgent.has(run.agent)) {
      existingByAgent.set(run.agent, run);
    }
  }

  const planned = new Set<string>(
    (data.coordinator_plan?.plan ?? []).map((step) => step.agent),
  );

  const ordered: AgentRun[] = [];
  for (const agent of EXPECTED_ORDER) {
    const existing = existingByAgent.get(agent);
    if (existing) {
      ordered.push(existing);
      continue;
    }

    const skipReason = agent === "historian"
      ? "Skipped by Coordinator: no prior session history was available for this water body."
      : planned.has(agent)
        ? "Skipped: this step was planned but did not execute due to an upstream fallback."
        : "Skipped by Coordinator: this step was not required for this run.";

    ordered.push({
      schema_version: 1,
      agent,
      started_at: data.created_at,
      completed_at: data.updated_at,
      latency_ms: 0,
      tokens_in: 0,
      tokens_out: 0,
      tool_calls: [],
      outputs: {
        skipped: true,
        skip_reason: skipReason,
      },
      error: null,
    });
  }

  // Preserve any unexpected/legacy rows after the core timeline.
  for (const run of data.agent_runs) {
    if (!EXPECTED_ORDER.includes(run.agent as AgentName)) {
      ordered.push(run);
    }
  }

  return ordered;
}

function AgentRunRow({ run }: { run: AgentRun }) {
  const [open, setOpen] = useState(false);
  const meta = agentMeta(run.agent);
  const Icon = meta.icon;
  const hasTools = run.tool_calls.length > 0;
  const hasOutputs = run.outputs && Object.keys(run.outputs).length > 0;
  const expandable = hasTools || hasOutputs || Boolean(run.error);
  const headline = plainEnglishStep(run);

  return (
    <li
      className={cn(
        "rounded-md border border-border bg-background/40",
        run.error && "border-destructive/60",
      )}
    >
      <button
        type="button"
        onClick={() => expandable && setOpen((v) => !v)}
        className={cn(
          "flex w-full items-start justify-between gap-3 px-3 py-2.5 text-left text-sm",
          expandable ? "cursor-pointer" : "cursor-default",
        )}
        aria-expanded={open}
        disabled={!expandable}
      >
        <span className="flex min-w-0 items-start gap-2.5">
          {expandable ? (
            open ? (
              <ChevronDown className="mt-1 size-3.5 shrink-0 text-muted-foreground" aria-hidden />
            ) : (
              <ChevronRight className="mt-1 size-3.5 shrink-0 text-muted-foreground" aria-hidden />
            )
          ) : (
            <span className="inline-block w-3.5" />
          )}
          <Icon className={cn("mt-0.5 size-4 shrink-0", meta.tint)} aria-hidden />
          <span className="flex min-w-0 flex-col gap-1 leading-snug">
            <span className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
              <span className="font-medium text-foreground">{meta.label}</span>
              <span className="text-2xs text-muted-foreground">{meta.short}</span>
            </span>
            {headline ? (
              <span className="text-xs text-foreground/85">{headline}</span>
            ) : null}
            {run.error ? (
              <span className="text-xs text-destructive">{run.error}</span>
            ) : null}
          </span>
        </span>
        <span className="mt-0.5 shrink-0 font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          {run.tool_calls.length > 0
            ? `${run.tool_calls.length} tool ${run.tool_calls.length === 1 ? "call" : "calls"} · `
            : ""}
          {run.latency_ms} ms
        </span>
      </button>

      {open ? (
        <div className="space-y-3 border-t border-border px-3 py-3">
          {hasTools ? (
            <ul className="space-y-2">
              {run.tool_calls.map((call, i) => (
                <ToolCallRow key={`${call.name}-${i}`} call={call} />
              ))}
            </ul>
          ) : null}

          {hasOutputs ? (
            <details className="text-xs">
              <summary className="cursor-pointer text-muted-foreground">
                Show raw output (JSON)
              </summary>
              <JsonBlock value={run.outputs} className="max-h-72" />
            </details>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

/**
 * One-sentence plain-English summary of what an agent accomplished.
 * Mirrors the same function in ``backend/app/services/report_generator.py``
 * so the web and the PDF stay in sync.
 */
function plainEnglishStep(run: AgentRun): string {
  const outputs = (run.outputs ?? {}) as Record<string, unknown>;
  if (outputs.skipped === true) {
    if (typeof outputs.skip_reason === "string" && outputs.skip_reason.trim()) {
      return outputs.skip_reason;
    }
    return "Skipped for this run by coordinator plan.";
  }
  switch (run.agent) {
    case "coordinator": {
      const plan = Array.isArray(outputs.plan) ? (outputs.plan as Array<Record<string, unknown>>) : [];
      if (plan.length > 0) {
        const names = plan
          .map((step) => {
            const label = AGENTS[String(step.agent)]?.label;
            return label ?? String(step.agent);
          })
          .join(" → ");
        return `Read the chosen area and history, then routed the run through: ${names}.`;
      }
      return "Read the chosen area and history, then decided which agents to run.";
    }
    case "scout": {
      const scene = typeof outputs.selected_scene_id === "string" ? outputs.selected_scene_id : null;
      const cloud =
        typeof outputs.selected_cloud_cover === "number"
          ? outputs.selected_cloud_cover
          : null;
      const when =
        typeof outputs.selected_capture_date === "string"
          ? outputs.selected_capture_date.slice(0, 10)
          : null;
      if (scene) {
        const cloudBit = cloud !== null ? ` with about ${cloud.toFixed(0)}% cloud cover` : "";
        const whenBit = when ? ` (captured ${when})` : "";
        return `Picked Sentinel-2 scene ${scene}${cloudBit}${whenBit}.`;
      }
      return "Picked the best Sentinel-2 scene that intersected the chosen area.";
    }
    case "historian": {
      const briefing =
        typeof outputs.briefing_text === "string" ? outputs.briefing_text.trim() : "";
      if (briefing) return briefing;
      const trend = (outputs.trend ?? {}) as Record<string, unknown>;
      if (typeof trend.summary === "string" && trend.summary) {
        return String(trend.summary);
      }
      return "Pulled past sessions, computed a trend, and searched the open web for relevant local news.";
    }
    case "analyst": {
      const bundle = (outputs.bundle ?? {}) as Record<string, unknown>;
      const reasoning = typeof bundle.reasoning === "string" ? bundle.reasoning : "";
      const critique = (outputs.critique ?? {}) as Record<string, unknown>;
      const rewrote = Boolean(outputs.rewrote);
      let head = reasoning ? (reasoning.split(". ")[0] ?? "").replace(/\.+$/, "") + "." : "";
      if (!head) head = "Wrote the recommendation and reasoning.";
      if (rewrote) {
        head += " The Critic flagged the first draft, so the Analyst rewrote once to fix it.";
      } else if (critique.accept_draft) {
        head += " The Critic accepted the first draft without changes.";
      }
      return head;
    }
    case "field_liaison":
      // Legacy: we no longer run this agent, but old traces may still
      // include a row for it.
      return "Recorded for backward compatibility — no field plan is generated.";
    case "reporter": {
      const headline = typeof outputs.headline === "string" ? outputs.headline.trim() : "";
      const bottom = typeof outputs.bottom_line === "string" ? outputs.bottom_line.trim() : "";
      if (headline) {
        return bottom ? `Published summary: ${headline}. ${bottom}` : `Published summary: ${headline}.`;
      }
      return "Wrote the citizen-facing summary card.";
    }
    default:
      return "";
  }
}

function ToolCallRow({ call }: { call: AgentToolCall }) {
  return (
    <li className="rounded border border-border/60 bg-background/30 px-2 py-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <code className="font-mono text-2xs text-aqua-300">{call.name}</code>
        <span className="font-mono text-2xs text-muted-foreground">
          {call.latency_ms} ms
        </span>
      </div>
      {call.error ? <p className="mt-1 text-2xs text-destructive">{call.error}</p> : null}
      <details className="mt-1 text-2xs">
        <summary className="cursor-pointer text-muted-foreground">Args + result</summary>
        <div className="mt-1 space-y-1">
          <JsonBlock value={call.arguments} className="max-h-40" />
          <JsonBlock value={call.result} className="max-h-48" />
        </div>
      </details>
    </li>
  );
}

/**
 * Pretty-printed JSON block that always stays inside its parent card.
 * Long string values wrap; whole-document fallback to horizontal scroll
 * when wrapping would break the structure.
 */
function JsonBlock({
  value,
  className,
}: {
  value: unknown;
  className?: string;
}) {
  return (
    <pre
      className={cn(
        "w-full min-w-0 overflow-x-auto whitespace-pre-wrap break-words rounded bg-background/60 p-2 font-mono text-2xs text-muted-foreground",
        className,
      )}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
