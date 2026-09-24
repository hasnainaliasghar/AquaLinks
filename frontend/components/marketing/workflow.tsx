/**
 * Landing-page "How it works" — the two-pipeline tour.
 *
 * Pipeline 1 is the deterministic numeric core: pick an AOI, fetch a
 * Sentinel-2 scene, compute the six band-math indices, score risk.
 * Those numbers are unit-tested, replayable Python — the agent layer
 * is never allowed to move them.
 *
 * Pipeline 2 is the multi-agent Groq layer that wraps the core:
 * Coordinator plans the run, Scout/Historian/Analyst/Reporter each do
 * a focused, structured job. Each agent is numbered (Agent 1 …
 * Agent 5) and gets a colour-coded action label that matches the
 * palette used in the in-app Agentic workflow card.
 *
 * No emojis; all lucide icons.
 */
"use client";

import {
  BookOpenText,
  CheckCircle2,
  Compass,
  Gauge,
  Microscope,
  Network,
  Newspaper,
  Satellite,
  Sparkles,
  Waves,
  type LucideIcon,
} from "lucide-react";

import { FadeIn } from "@/components/motion/fade-in";
import { cn } from "@/lib/utils";

type DeterministicStep = {
  n: string;
  title: string;
  subtitle: string;
  body: string;
  icon: LucideIcon;
  tint: string;
};

type AgentStep = {
  n: string;
  name: string;
  action: string;
  capability: string;
  body: string;
  icon: LucideIcon;
  tint: string;
  ring: string;
  chip: string;
};

const DETERMINISTIC_STEPS: DeterministicStep[] = [
  {
    n: "01",
    title: "Pick an area",
    subtitle: "search, paste coordinates, or tap the map",
    body: "AquaLinks turns the chosen point into a ~1 km buffer polygon and records a date window. A water-mask check classifies the AOI as water, mixed, or land.",
    icon: Compass,
    tint: "text-aqua-300",
  },
  {
    n: "02",
    title: "Fetch Sentinel-2 imagery",
    subtitle: "Microsoft Planetary Computer · STAC query",
    body: "The backend searches the Sentinel-2 L2A archive for the freshest scene that intersects the AOI under the cloud-cover ceiling, signs the COG asset URLs, and reads only the bands it needs.",
    icon: Satellite,
    tint: "text-sky-300",
  },
  {
    n: "03",
    title: "Compute spectral indices",
    subtitle: "deterministic numpy + audit-friendly weights",
    body: "Six band-math indices (NDWI · MNDWI · NDTI · NDCI · NDVI · WRI) are computed over the water mask, with full provenance for every value.",
    icon: Waves,
    tint: "text-emerald-300",
  },
  {
    n: "04",
    title: "Score the risk",
    subtitle: "weighted, unit-tested, reproducible",
    body: "A deterministic weighted model turns the index aggregates into a 0–100 score, a level (low / medium / high), and an urgency tier. The agent layer is never allowed to move these numbers.",
    icon: Gauge,
    tint: "text-emerald-300",
  },
];

// Agent order + palette matches `components/session/agent-trace.tsx`
// AGENTS map so the marketing surface and the in-app trace use the
// same colours and action labels.
const AGENT_STEPS: AgentStep[] = [
  {
    n: "1",
    name: "Coordinator",
    action: "plans the workflow",
    capability: "Groq AI reasoning",
    body: "Reads the AOI plus its history and decides per-agent budgets. Always schedules Scout, Analyst, and Reporter; schedules Historian only when prior sessions exist.",
    icon: Network,
    tint: "text-aqua-300",
    ring: "ring-aqua-400/30",
    chip: "border-aqua-400/30 bg-aqua-400/5 text-aqua-300",
  },
  {
    n: "2",
    name: "Scout",
    action: "picks the satellite scene",
    capability: "Function calling + Groq Vision",
    body: "Evaluates candidate scenes and asks Groq Vision to look at the actual RGB thumbnail. If haze sits over the AOI it re-queries with a tighter cloud bound.",
    icon: Satellite,
    tint: "text-sky-300",
    ring: "ring-sky-400/30",
    chip: "border-sky-400/30 bg-sky-400/5 text-sky-300",
  },
  {
    n: "3",
    name: "Historian",
    action: "pulls trends and grounded context",
    capability: "History + Search grounding + memory",
    body: "Pulls prior sessions, runs a Mann-Kendall significance test in Groq's Python sandbox, cites real local news via Search grounding + URL Context, and writes a distilled note back to per-water-body memory for next time.",
    icon: BookOpenText,
    tint: "text-amber-300",
    ring: "ring-amber-400/30",
    chip: "border-amber-400/30 bg-amber-400/5 text-amber-300",
  },
  {
    n: "4",
    name: "Analyst",
    action: "writes and self-critiques the brief",
    capability: "Structured output + critique loop",
    body: "Drafts recommendation + reasoning + limitations against the deterministic numbers. A separate Groq call critiques the draft against the hard rules; the Analyst rewrites once if anything fails. Both drafts land in the trace.",
    icon: Microscope,
    tint: "text-violet-300",
    ring: "ring-violet-400/30",
    chip: "border-violet-400/30 bg-violet-400/5 text-violet-300",
  },
  {
    n: "5",
    name: "Reporter",
    action: "writes the citizen summary",
    capability: "Structured response schema",
    body: "Turns the deterministic numbers plus Scout / Historian / Analyst outputs into the public-facing card: likely-safe · use caution · avoid, guidance for adults and for pets and kids, explicit limitations, and citations when grounded context exists. Falls back to a deterministic summary if the Groq call fails.",
    icon: Newspaper,
    tint: "text-emerald-300",
    ring: "ring-emerald-400/30",
    chip: "border-emerald-400/30 bg-emerald-400/5 text-emerald-300",
  },
];

export function Workflow() {
  return (
    <section className="border-y border-border bg-surface-1/60 py-24 sm:py-32">
      <div className="container">
        <FadeIn>
          <header className="mx-auto max-w-3xl text-center">
            <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
              How it works
            </p>
            <h2 className="mt-2 font-display text-3xl tracking-tight sm:text-4xl">
              Two pipelines. One session trace.
            </h2>
            <p className="mt-4 text-balance text-muted-foreground">
              The deterministic numeric core runs first and produces the
              auditable numbers. The Groq agent layer wraps it: agents
              choose inputs and write prose, but they can&apos;t move the
              risk band. Every decision lands in the per-session trace.
            </p>
            <div className="mt-5 flex flex-wrap items-center justify-center gap-2 text-xs">
              <KindLegend kind="deterministic" />
              <KindLegend kind="agent" />
            </div>
          </header>
        </FadeIn>

        {/* Pipeline 1 — deterministic core */}
        <FadeIn delay={0.06}>
          <div className="mt-12 rounded-2xl border border-border bg-card/70 p-5 sm:p-7">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="font-display text-xl tracking-tight">
                Pipeline 1
                <span className="text-muted-foreground"> · deterministic core</span>
              </h3>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-emerald-400/30 bg-emerald-400/5 px-2 py-0.5 text-2xs font-medium text-emerald-300">
                <CheckCircle2 className="size-3" aria-hidden />
                Source of truth for the numbers
              </span>
            </div>
            <ol className="mt-5 grid gap-3 md:grid-cols-2">
              {DETERMINISTIC_STEPS.map((step, idx) => (
                <FadeIn key={step.n} delay={0.08 + idx * 0.04}>
                  <DeterministicCard step={step} />
                </FadeIn>
              ))}
            </ol>
          </div>
        </FadeIn>

        {/* Hand-off connector */}
        <FadeIn delay={0.22}>
          <div
            aria-hidden
            className="mx-auto my-5 h-7 w-px bg-gradient-to-b from-emerald-400/40 to-aqua-400/40"
          />
        </FadeIn>

        {/* Pipeline 2 — Groq agent layer */}
        <FadeIn delay={0.26}>
          <div className="rounded-2xl border border-border bg-card/70 p-5 sm:p-7">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="font-display text-xl tracking-tight">
                Pipeline 2
                <span className="text-muted-foreground"> · Groq agent layer</span>
              </h3>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-aqua-400/30 bg-aqua-400/5 px-2 py-0.5 text-2xs font-medium text-aqua-300">
                <Sparkles className="size-3" aria-hidden />
                Agents choose inputs &amp; write prose
              </span>
            </div>
            <ol className="mt-5 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {AGENT_STEPS.map((agent, idx) => (
                <FadeIn key={agent.n} delay={0.3 + idx * 0.04}>
                  <AgentCard agent={agent} />
                </FadeIn>
              ))}
            </ol>
          </div>
        </FadeIn>

        <FadeIn delay={0.5}>
          <p className="mt-10 text-center text-sm text-muted-foreground">
            Every agent run is captured in the{" "}
            <span className="text-foreground">Agentic workflow</span> card on the
            session page. If any agent fails the orchestrator records the
            failure and falls back to a deterministic path, so a session always
            produces a usable brief.
          </p>
        </FadeIn>
      </div>
    </section>
  );
}

function DeterministicCard({ step }: { step: DeterministicStep }) {
  const Icon = step.icon;
  return (
    <li className="h-full rounded-xl border border-border bg-surface-0 p-5">
      <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
        Step {step.n}
      </p>
      <div className="mt-3 flex items-start gap-3">
        <Icon className={cn("mt-0.5 size-5 shrink-0", step.tint)} aria-hidden />
        <div className="min-w-0">
          <h4 className="font-display text-xl tracking-tight">{step.title}</h4>
          <p className="text-xs text-muted-foreground">{step.subtitle}</p>
        </div>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{step.body}</p>
    </li>
  );
}

function AgentCard({ agent }: { agent: AgentStep }) {
  const Icon = agent.icon;
  return (
    <li
      className={cn(
        "group relative h-full overflow-hidden rounded-xl border border-border bg-surface-0 p-5 transition-[transform,box-shadow,border-color] duration-300",
        "hover:-translate-y-0.5 hover:shadow-elev-2 hover:border-transparent hover:ring-1",
        agent.ring,
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          Agent {agent.n}
        </p>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-2xs font-medium",
            agent.chip,
          )}
        >
          Groq
        </span>
      </div>
      <div className="mt-3 flex items-start gap-3">
        <Icon className={cn("mt-0.5 size-5 shrink-0", agent.tint)} aria-hidden />
        <div className="min-w-0">
          <h4 className="font-display text-xl tracking-tight">
            {agent.name}{" "}
            <span className="text-muted-foreground">·</span>{" "}
            <span className={agent.tint}>{agent.action}</span>
          </h4>
          <p className="text-xs text-muted-foreground">{agent.capability}</p>
        </div>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{agent.body}</p>
    </li>
  );
}

const KIND_BADGE = {
  deterministic: {
    label: "Deterministic core",
    className: "border-emerald-400/30 bg-emerald-400/5 text-emerald-300",
    icon: CheckCircle2,
  },
  agent: {
    label: "Groq agent",
    className: "border-aqua-400/30 bg-aqua-400/5 text-aqua-300",
    icon: Sparkles,
  },
} as const;

function KindLegend({ kind }: { kind: keyof typeof KIND_BADGE }) {
  const badge = KIND_BADGE[kind];
  const Icon = badge.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-2xs",
        badge.className,
      )}
    >
      <Icon className="size-3" aria-hidden />
      {badge.label}
    </span>
  );
}
