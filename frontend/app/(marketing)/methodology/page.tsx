import type { Metadata } from "next";

import { FadeIn } from "@/components/motion/fade-in";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "Methodology",
  description:
    "Two linked pipelines: a deterministic numeric core, then a five-agent Gemini layer that writes the brief and the citizen summary.",
  path: "/methodology",
});

const INDICES = [
  {
    key: "NDWI",
    name: "Normalized Difference Water Index",
    formula: "(NIR − SWIR) / (NIR + SWIR)",
    bands: "B08 · B11",
    interpretation: "Open-water signal. Values above zero indicate water cover.",
  },
  {
    key: "MNDWI",
    name: "Modified NDWI",
    formula: "(Green − SWIR) / (Green + SWIR)",
    bands: "B03 · B11",
    interpretation: "Water signal that holds up in urban / built-up settings.",
  },
  {
    key: "NDTI",
    name: "Normalized Difference Turbidity",
    formula: "(Red − Green) / (Red + Green)",
    bands: "B04 · B03",
    interpretation: "Higher values indicate more turbid water columns.",
  },
  {
    key: "NDCI",
    name: "Normalized Difference Chlorophyll",
    formula: "(RedEdge − Red) / (RedEdge + Red)",
    bands: "B05 · B04",
    interpretation: "Proxy for chlorophyll-a, a bloom precursor.",
  },
  {
    key: "NDVI",
    name: "Normalized Difference Vegetation",
    formula: "(NIR − Red) / (NIR + Red)",
    bands: "B08 · B04",
    interpretation: "Shoreline vegetation health; useful as a stress co-signal.",
  },
  {
    key: "WRI",
    name: "Water Ratio Index",
    formula: "(Green + Red) / (NIR + SWIR)",
    bands: "B03 · B04 · B08 · B11",
    interpretation: "Strong open-water signature when values exceed 2.5.",
  },
];

const RISK_WEIGHTS = [
  { name: "NDCI (chlorophyll proxy)", w: "0.40" },
  { name: "NDTI (turbidity)", w: "0.25" },
  { name: "NDVI shoreline stress", w: "0.10" },
  { name: "MNDWI water-signal floor", w: "0.10" },
  { name: "NDWI water-signal floor", w: "0.15" },
];

export default function MethodologyPage() {
  return (
    <article className="container max-w-3xl py-20">
      <FadeIn>
        <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          Methodology
        </p>
        <h1 className="mt-2 font-display text-4xl tracking-tight sm:text-5xl">
          How AquaLinks reads water from space.
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
          AquaLinks runs two linked pipelines. The deterministic numeric core
          pulls a fresh Sentinel-2 scene, computes six band-math indices over
          the water mask, and produces a 0–100 risk score that is unit-tested
          and never moved by the LLM. The Gemini agent layer wraps that core
          with five specialist agents that choose inputs, gather grounded
          context, write the brief, and publish a citizen-facing summary.
          Every step is reproducible and recorded.
        </p>
      </FadeIn>

      <FadeIn>
        <section className="mt-14 space-y-6">
          <h2 className="font-display text-2xl tracking-tight">Imagery acquisition</h2>
          <p className="text-muted-foreground">
            We query the Microsoft Planetary Computer STAC API for the
            <code className="mx-1 rounded-xs bg-muted px-1.5 py-0.5 font-mono text-xs">sentinel-2-l2a</code>
            collection, intersected with the polygon and filtered by
            <code className="mx-1 rounded-xs bg-muted px-1.5 py-0.5 font-mono text-xs">eo:cloud_cover &lt; threshold</code>.
            The most recent matching scene is selected, the asset URLs are signed, and the
            relevant bands (B02 · B03 · B04 · B05 · B08 · B11) are streamed as Cloud-Optimized
            GeoTIFFs and clipped to the AOI.
          </p>
        </section>
      </FadeIn>

      <FadeIn>
        <section className="mt-14 space-y-6">
          <h2 className="font-display text-2xl tracking-tight">Spectral indices</h2>
          <p className="text-muted-foreground">
            Each index is a pure numpy function over the band stack. We mask non-water
            pixels using NDWI &gt; 0, then aggregate to a masked-mean per index.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {INDICES.map((idx) => (
              <Card key={idx.key}>
                <CardHeader className="gap-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{idx.name}</CardTitle>
                    <Badge variant="aqua">{idx.key}</Badge>
                  </div>
                  <p className="font-mono text-xs text-muted-foreground">
                    bands · {idx.bands}
                  </p>
                </CardHeader>
                <CardContent>
                  <p className="font-mono text-sm">{idx.formula}</p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {idx.interpretation}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      </FadeIn>

      <FadeIn>
        <section className="mt-14 space-y-6">
          <h2 className="font-display text-2xl tracking-tight">Risk model</h2>
          <p className="text-muted-foreground">
            The numeric score is deterministic and audit-friendly. Each contributing
            factor is normalized into{" "}
            <code className="rounded-xs bg-muted px-1.5 py-0.5 font-mono text-xs">[0, 1]</code>{" "}
            and multiplied by its weight. Field-evidence flags then add a bonus up to{" "}
            <code className="rounded-xs bg-muted px-1.5 py-0.5 font-mono text-xs">0.5</code>,
            and the result is clamped.
          </p>
          <div className="rounded-md border border-border bg-card p-5">
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Weights
            </p>
            <dl className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
              {RISK_WEIGHTS.map((row) => (
                <div
                  key={row.name}
                  className="flex items-center justify-between rounded-xs border border-border bg-surface-1 px-3 py-2 text-sm"
                >
                  <dt>{row.name}</dt>
                  <dd className="font-mono text-muted-foreground">{row.w}</dd>
                </div>
              ))}
            </dl>
          </div>
          <p className="text-muted-foreground">
            Levels bucket at{" "}
            <code className="rounded-xs bg-muted px-1.5 py-0.5 font-mono text-xs">&lt; 0.33</code>{" "}
            (low) and{" "}
            <code className="rounded-xs bg-muted px-1.5 py-0.5 font-mono text-xs">&lt; 0.66</code>{" "}
            (medium); the rest is high. Urgency is a function of the level plus severity of
            the latest evidence (algae presence, dead-fish count, complaints).
          </p>
        </section>
      </FadeIn>

      <FadeIn>
        <section className="mt-14 space-y-6">
          <h2 className="font-display text-2xl tracking-tight">Agentic hand-over</h2>
          <p className="text-muted-foreground">
            Once deterministic scoring is complete, the runtime hands the
            session bundle to the agent layer. Agents can pick inputs,
            gather context, and write prose, but they cannot override the
            deterministic level or urgency. Each agent is a focused Gemini
            call constrained by a domain-specific system prompt and a
            structured-output contract that forbids overclaiming.
          </p>
        </section>
      </FadeIn>

      <FadeIn>
        <section className="mt-14 space-y-6">
          <h2 className="font-display text-2xl tracking-tight">Multi-agent workflow</h2>
          <p className="text-muted-foreground">
            When a session runs, a small graph of specialised Gemini agents
            plans the work, gathers context, drafts the brief, and turns it
            into a citizen-facing summary. Agent colour and action-label
            wording match the in-app Agentic workflow card so the marketing
            surface and the live trace describe exactly the same thing.
          </p>

          <ol className="space-y-3">
            {AGENT_STEPS.map((step) => (
              <li
                key={step.name}
                className="rounded-md border border-border bg-card p-5"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <h3 className="font-display text-lg tracking-tight">
                    {step.name}{" "}
                    <span className="text-muted-foreground">·</span>{" "}
                    <span className={step.tint}>{step.action}</span>
                  </h3>
                  <span className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                    {step.label}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">{step.capability}</p>
                <p className="mt-2 text-sm text-muted-foreground">{step.body}</p>
              </li>
            ))}
          </ol>

          <p className="text-muted-foreground">
            Every step is captured in a per-session trace (the Agent
            decisions card on the session page). Failed agents leave the
            failure in the trace and the pipeline falls back to a
            deterministic path — Reporter falls back to a deterministic
            citizen summary, Analyst falls back to a deterministic
            narrator — so every session produces a usable brief.
          </p>
        </section>
      </FadeIn>
    </article>
  );
}

type AgentStep = {
  label: string;
  name: string;
  action: string;
  capability: string;
  body: string;
  tint: string;
};

// Agent order + action labels + tints match
// `components/session/agent-trace.tsx` AGENTS and the workflow /
// agent-constellation sections. Coordinator is Agent 1.
const AGENT_STEPS: AgentStep[] = [
  {
    label: "Agent 1",
    name: "Coordinator",
    action: "plans the workflow",
    capability: "Gemini thinking mode",
    body: "Reads the AOI + history and decides per-agent budgets. Always schedules Scout, Analyst, and Reporter for water AOIs; schedules Historian when prior sessions exist.",
    tint: "text-aqua-300",
  },
  {
    label: "Agent 2",
    name: "Scout",
    action: "picks the satellite scene",
    capability: "Function calling + Gemini Vision",
    body: "Calls Planetary Computer for Sentinel-2 candidates, then asks Gemini Vision to look at the actual RGB thumbnail. If the freshest scene is hazy over the AOI, the Scout re-queries with a tighter cloud bound.",
    tint: "text-sky-300",
  },
  {
    label: "Agent 3",
    name: "Historian",
    action: "pulls trends and grounded context",
    capability: "History + Search grounding + memory",
    body: "Reads prior sessions, runs a Mann-Kendall significance test in Gemini's Python sandbox, cites real local news via Google Search grounding + URL Context, and writes a distilled note back to per-water-body memory (text-embedding-004 + pgvector) for next time.",
    tint: "text-amber-300",
  },
  {
    label: "Agent 4",
    name: "Analyst",
    action: "writes and self-critiques the brief",
    capability: "Structured output + critique loop",
    body: "Drafts recommendation + reasoning + limitations against the deterministic numbers. A separate Gemini call critiques the draft against the hard rules (cites two indices, names a real limitation, no overclaiming). If anything fails the Analyst rewrites once. Both drafts land in the trace.",
    tint: "text-violet-300",
  },
  {
    label: "Agent 5",
    name: "Reporter",
    action: "writes the citizen summary",
    capability: "Structured response schema",
    body: "Turns the deterministic numbers + Scout / Historian / Analyst outputs into the public-facing card: likely-safe · use caution · avoid tone, guidance for adults and for pets and kids, explicit limitations, and citations when grounded context exists. Falls back to a deterministic summary if the call fails.",
    tint: "text-emerald-300",
  },
];
