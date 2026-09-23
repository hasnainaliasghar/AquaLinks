"use client";

/**
 * Agent surface — deep dive on the multi-agent layer.
 *
 * Three-tier hierarchy:
 *
 *   1. Coordinator as **Agent 1** (full-width hero card) — plans the
 *      workflow. The visual hand-off line below it leads into:
 *   2. The four specialists Agents 2–5 in a 2×2 grid — Scout,
 *      Historian, Analyst, Reporter. Each has a colour-coded action
 *      label that matches the in-app Agentic workflow card, plus the
 *      actual tool surface and Gemini capability it uses.
 *   3. Two persistence rails (agent_traces, agent_memory) below the
 *      grid — what the agents write so the next session can read.
 *
 * No emojis; all lucide icons. The action-label colour for every
 * agent matches `components/session/agent-trace.tsx` AGENTS so the
 * marketing surface and the live trace stay visually identical.
 */
import {
  BookOpenText,
  Database,
  Globe,
  Microscope,
  Network,
  Newspaper,
  Satellite,
  ScrollText,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

import { FadeIn } from "@/components/motion/fade-in";
import { cn } from "@/lib/utils";

type SpecialistAgent = {
  step: string;
  name: string;
  action: string;
  capability: string;
  body: string;
  tools: string[];
  icon: LucideIcon;
  tint: string;
  ring: string;
};

const SPECIALISTS: SpecialistAgent[] = [
  {
    step: "Agent 2",
    name: "Scout",
    action: "picks the satellite scene",
    capability: "Function calling + multimodal vision",
    body: "Calls Planetary Computer for Sentinel-2 candidates, then asks Gemini Vision to look at the actual RGB thumbnail. If haze sits over the AOI it re-queries with a tighter cloud bound.",
    tools: ["list_recent_scenes", "inspect_scene", "look_at_thumbnail"],
    icon: Satellite,
    tint: "text-sky-300",
    ring: "ring-sky-400/30",
  },
  {
    step: "Agent 3",
    name: "Historian",
    action: "pulls trends and grounded context",
    capability: "Code execution + Search grounding + memory",
    body: "Pulls prior sessions, runs a Mann-Kendall significance test in Gemini's Python sandbox, cites real news via Google Search grounding + URL Context, and writes a distilled note back to per-water-body memory for next time.",
    tools: ["get_session_history", "compute_trend", "semantic_recall_notes"],
    icon: BookOpenText,
    tint: "text-amber-300",
    ring: "ring-amber-400/30",
  },
  {
    step: "Agent 4",
    name: "Analyst",
    action: "writes and self-critiques the brief",
    capability: "Structured output + critique loop",
    body: "Drafts recommendation + reasoning + limitations against the deterministic numbers. A separate Gemini call critiques the draft against the hard rules; the Analyst rewrites once if anything fails. Both drafts land in the trace.",
    tools: ["draft_call", "critique_call", "rewrite_call"],
    icon: Microscope,
    tint: "text-violet-300",
    ring: "ring-violet-400/30",
  },
  {
    step: "Agent 5",
    name: "Reporter",
    action: "writes the citizen summary",
    capability: "Structured response schema",
    body: "Turns Scout / Historian / Analyst outputs plus the deterministic risk numbers into the public-facing card: tone (likely-safe / use caution / avoid), guidance for adults and for pets and kids, explicit limitations, and citations when grounded context exists. Falls back to a deterministic citizen summary if the Gemini call fails.",
    tools: ["call_structured", "tone_guardrail", "citation_filter"],
    icon: Newspaper,
    tint: "text-emerald-300",
    ring: "ring-emerald-400/30",
  },
];

const PERSISTENCE = [
  {
    icon: ScrollText,
    title: "agent_traces",
    subtitle: "JSONB log per session",
    body: "Every tool call, argument, result, error, and token count — surfaced live in the Agentic workflow card.",
    tint: "text-aqua-300",
  },
  {
    icon: Database,
    title: "agent_memory",
    subtitle: "vectors per water body",
    body: "text-embedding-004 vectors with a pgvector(768) HNSW cosine index. Next session for the same lake recalls semantically related notes.",
    tint: "text-aqua-300",
  },
];

export function AgentConstellation() {
  return (
    <section className="relative border-y border-border bg-surface-1/40 py-24 sm:py-32">
      {/* Soft brand glow behind the section */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-64 bg-gradient-to-b from-aqua-500/[0.06] to-transparent"
      />

      <div className="container">
        <FadeIn>
          <header className="mx-auto max-w-2xl text-center">
            <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
              Agent surface
            </p>
            <h2 className="mt-2 font-display text-3xl tracking-tight sm:text-4xl">
              Five Gemini agents. One audited workflow.
            </h2>
            <p className="mt-4 text-balance text-muted-foreground">
              The deterministic numeric core is wrapped by a small graph of
              specialist agents. Each one has a focused job, a constrained
              tool surface, and a structured-output contract — and every
              call is captured in a per-session trace.
            </p>
          </header>
        </FadeIn>

        {/* Tier 1 — Coordinator (Agent 1, full-width hero card) */}
        <FadeIn delay={0.05}>
          <article className="mt-12 overflow-hidden rounded-2xl border border-aqua-500/30 bg-card p-6 shadow-elev-2 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-lg bg-aqua-500/15 ring-1 ring-aqua-400/30">
                  <Network className="size-5 text-aqua-300" aria-hidden />
                </span>
                <div>
                  <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                    Agent 1
                  </p>
                  <h3 className="font-display text-2xl tracking-tight">
                    Coordinator <span className="text-muted-foreground">·</span>{" "}
                    <span className="text-aqua-300">plans the workflow</span>
                  </h3>
                </div>
              </div>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-aqua-400/30 bg-aqua-400/5 px-2 py-0.5 text-2xs font-medium text-aqua-300">
                <Sparkles className="size-3" aria-hidden />
                Gemini thinking mode
              </span>
            </div>
            <p className="mt-4 max-w-3xl text-sm text-muted-foreground">
              Reads the AOI plus its history and decides which specialists to
              invoke and what their tool / time budgets are. Always schedules
              Scout, Analyst, and Reporter for water AOIs; schedules Historian
              when prior sessions exist. Failed plan? The orchestrator falls
              back to a baseline schedule so the session still completes.
            </p>
          </article>
        </FadeIn>

        {/* Tier 2 — Four specialists in a 2×2 grid (Agents 2–5) */}
        <div className="relative mt-3 grid gap-3 sm:grid-cols-2">
          {/* Connector line from Coordinator to the grid */}
          <div
            aria-hidden
            className="pointer-events-none absolute -top-3 left-1/2 hidden h-3 w-px -translate-x-1/2 bg-gradient-to-b from-aqua-400/40 to-transparent sm:block"
          />
          {SPECIALISTS.map((agent, idx) => (
            <FadeIn key={agent.name} delay={0.1 + idx * 0.04}>
              <SpecialistCard agent={agent} />
            </FadeIn>
          ))}
        </div>

        {/* Tier 3 — Persistence rails */}
        <FadeIn delay={0.3}>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            {PERSISTENCE.map((row) => (
              <PersistenceCard key={row.title} {...row} />
            ))}
          </div>
        </FadeIn>

        {/* Capability bar */}
        <FadeIn delay={0.35}>
          <div className="mt-10 rounded-xl border border-border bg-card/60 p-5">
            <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
              Gemini capabilities exercised end-to-end
            </p>
            <ul className="mt-3 flex flex-wrap gap-2 text-xs">
              {[
                "function calling",
                "multimodal vision",
                "Google Search grounding",
                "URL Context",
                "code execution",
                "thinking mode",
                "structured output",
                "long context",
                "text-embedding-004",
              ].map((cap) => (
                <li
                  key={cap}
                  className="inline-flex items-center gap-1.5 rounded-md border border-aqua-400/30 bg-aqua-400/5 px-2 py-1 text-aqua-300"
                >
                  <Globe className="size-3" aria-hidden />
                  {cap}
                </li>
              ))}
            </ul>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}

function SpecialistCard({ agent }: { agent: SpecialistAgent }) {
  const Icon = agent.icon;
  return (
    <article
      className={cn(
        "group relative h-full overflow-hidden rounded-xl border border-border bg-card p-6 shadow-elev-1 transition-[transform,box-shadow,border-color] duration-300",
        "hover:-translate-y-0.5 hover:shadow-elev-2",
        "hover:border-transparent hover:ring-1",
        agent.ring,
      )}
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span
            className={cn(
              "inline-flex size-9 shrink-0 items-center justify-center rounded-lg bg-background/60 ring-1",
              agent.ring,
            )}
          >
            <Icon className={cn("size-4", agent.tint)} aria-hidden />
          </span>
          <div>
            <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
              {agent.step}
            </p>
            <h3 className="font-display text-xl tracking-tight">
              {agent.name} <span className="text-muted-foreground">·</span>{" "}
              <span className={agent.tint}>{agent.action}</span>
            </h3>
            <p className="text-xs text-muted-foreground">{agent.capability}</p>
          </div>
        </div>
      </header>

      <p className="mt-4 text-sm text-muted-foreground">{agent.body}</p>

      <p className="mt-4 font-mono text-2xs uppercase tracking-wider text-muted-foreground">
        Tools
      </p>
      <ul className="mt-1 flex flex-wrap gap-1.5">
        {agent.tools.map((tool) => (
          <li
            key={tool}
            className="rounded border border-border bg-background/50 px-1.5 py-0.5 font-mono text-2xs text-muted-foreground"
          >
            {tool}
          </li>
        ))}
      </ul>
    </article>
  );
}

function PersistenceCard({
  icon: Icon,
  title,
  subtitle,
  body,
  tint,
}: {
  icon: LucideIcon;
  title: string;
  subtitle: string;
  body: string;
  tint: string;
}) {
  return (
    <article className="flex items-start gap-3 rounded-xl border border-dashed border-aqua-500/20 bg-background/30 p-5">
      <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-lg bg-aqua-500/10 ring-1 ring-aqua-400/20">
        <Icon className={cn("size-4", tint)} aria-hidden />
      </span>
      <div className="min-w-0">
        <p className="font-mono text-xs text-foreground">{title}</p>
        <p className="text-2xs text-muted-foreground">{subtitle}</p>
        <p className="mt-2 text-sm text-muted-foreground">{body}</p>
      </div>
    </article>
  );
}
