import type { Metadata } from "next";

import { FadeIn } from "@/components/motion/fade-in";
import { Badge } from "@/components/ui/badge";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "Changelog",
  description: "Release notes for AquaLinks.",
  path: "/changelog",
});

type ReleaseGroup = {
  title: string;
  items: string[];
};

type Release = {
  version: string;
  date: string;
  headline: string;
  summary: string;
  groups: ReleaseGroup[];
};

const RELEASES: Release[] = [
  {
    version: "1.0.0",
    date: "2026-05-16",
    headline: "Initial release",
    summary:
      "Production-grade rewrite. Real Sentinel-2 retrieval via Microsoft Planetary Computer, six band-math indices over an NDWI ∧ MNDWI water mask, deterministic risk scoring, Groq AI narrative grounded in the numbers, branded WeasyPrint PDF reports, and a polished Next.js 15 frontend.",
    groups: [
      {
        title: "Pipeline",
        items: [
          "Real Sentinel-2 L2A retrieval via Microsoft Planetary Computer STAC; signed COG reads with native-resolution alignment for the mixed 10 m / 20 m bands.",
          "Six band-math indices (NDWI · MNDWI · NDTI · NDCI · NDVI · WRI), masked-mean aggregated over the water polygon.",
          "Combined NDWI ∧ MNDWI water mask (Xu 2006) — defeats the well-known NDWI-only false positive over vegetation.",
          "Deterministic weighted risk model with bounded field-evidence bonus; numeric band is auditable, unit-tested, and never moved by the LLM.",
          "Groq AI narrative bound to the deterministic numbers; automatic fallback to a second API key on quota / 429 errors; deterministic fallback for offline CI.",
          "Land-vs-water sanity check classifies every AOI as water · mixed · land and surfaces a prominent banner + LLM disclosure when the AOI isn't a water body.",
        ],
      },
      {
        title: "Agent layer",
        items: [
          "Coordinator (Groq AI reasoning) plans a workflow over four specialist agents and adapts to whether the water body has prior history.",
          "Scout uses Groq function calling + multimodal vision on the real Sentinel-2 RGB thumbnail; re-queries STAC with a tighter cloud bound when Vision flags haze over the AOI.",
          "Historian combines Google Search grounding, URL Context, code execution (Mann-Kendall trend significance) and long-context history into a single briefing the Analyst quotes verbatim.",
          "Analyst drafts the narrative, runs a self-critique pass against the hard rules, and rewrites once when the critique rejects the draft.",
          "Reporter turns the multi-agent outputs into a structured citizen summary card (tone, guidance, limitations, and citations).",
          "Full per-session execution captured in agent_traces (JSONB) and surfaced in the Agent Trace UI card and the PDF appendix.",
          "AQUALENS_AGENTIC_MODE flag preserves the single-call deterministic narrative path for CI and offline runs.",
        ],
      },
      {
        title: "Memory & adaptation",
        items: [
          "agent_memory table persists Historian-distilled notes per water body across sessions — the literal 'manages multi-step tasks over time' criterion.",
          "text-embedding-004 vectors stored on each note (768 dims); pgvector(768) + HNSW cosine index on Postgres for fast semantic recall.",
          "Soft-archives older notes past 50 active rows per water body so recall queries stay focused on recent context.",
          "Same recall code path runs on SQLite (tests) and Postgres (production) — pgvector just makes it faster at scale.",
        ],
      },
      {
        title: "Frontend",
        items: [
          "Next.js 15 app router, Tailwind 4, TypeScript strict mode.",
          "Custom shadcn primitives hand-tuned to OKLCH design tokens, dark and light themes.",
          "MapLibre map with street · satellite · terrain basemaps (collapsible switcher), Nominatim place search, decimal-coords input, click-to-pin AOI.",
          "Animated hero, command palette (Ctrl K / Cmd K), motion system with `prefers-reduced-motion` support.",
          "Session detail page with synced index charts, animated risk badge, evidence timeline, AOI banner, and live processing skeletons.",
          "Mobile-first field-evidence companion form with EXIF-stripped photo upload and one-tap GPS capture.",
          "Water-bodies library with rename + cascading delete and per-AOI session history with index trends.",
        ],
      },
      {
        title: "Reporting",
        items: [
          "WeasyPrint + Jinja2 PDF reports with embedded matplotlib SVG charts.",
          "Three-column risk row (pill ‖ score ‖ urgency) with page-break-safe glossary.",
          "PDF re-renders on every download so template fixes ship instantly to existing sessions.",
          "Banner above the risk card when the AOI is mostly land — matches the in-app warning.",
        ],
      },
      {
        title: "Platform",
        items: [
          "FastAPI 0.115 backend with SQLModel, Alembic migrations, BackgroundTasks.",
          "PostgreSQL 16 + PostGIS in production, SQLite for tests via the same SQLModel metadata.",
          "Two Alembic migrations: 0001_initial bootstraps the schema; 0002_aoi_type adds the water-fraction / AOI-type classifier fields.",
          "GitHub Actions CI running ruff, black, pytest, vitest, typecheck, eslint, stylelint, and a Playwright E2E job against the compose stack.",
          "Docker Compose for local dev, Render Blueprint for the backend, vercel.json for the frontend.",
        ],
      },
      {
        title: "Licensing & docs",
        items: [
          "Code and documentation licensed under MIT.",
          "NOTICE.md catalogues every third-party Python and Node dependency plus the data sources.",
          "COMMERCIAL_LICENSE.md clarifies that MIT already permits commercial use.",
          "Methodology, risk model, API contract, user manual, and frontend design notes shipped under docs/.",
        ],
      },
    ],
  },
];

export default function ChangelogPage() {
  return (
    <article className="container max-w-3xl py-20">
      <FadeIn>
        <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          Changelog
        </p>
        <h1 className="mt-2 font-display text-4xl tracking-tight sm:text-5xl">
          What changed, when.
        </h1>
      </FadeIn>

      <div className="mt-12 space-y-10">
        {RELEASES.map((release) => (
          <FadeIn key={release.version} as="section" className="grid gap-4 sm:grid-cols-[10rem_1fr]">
            <div className="space-y-2">
              <Badge variant="aqua">v{release.version}</Badge>
              <p className="font-mono text-xs text-muted-foreground">{release.date}</p>
            </div>
            <div className="space-y-5 rounded-md border border-border bg-card p-6">
              <div className="space-y-2">
                <h2 className="font-display text-xl tracking-tight">{release.headline}</h2>
                <p className="text-sm text-muted-foreground">{release.summary}</p>
              </div>
              <div className="space-y-5">
                {release.groups.map((group) => (
                  <div key={group.title} className="space-y-2">
                    <h3 className="font-mono text-2xs uppercase tracking-wider text-foreground/80">
                      {group.title}
                    </h3>
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      {group.items.map((item) => (
                        <li key={item} className="flex gap-2">
                          <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-aqua-500" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          </FadeIn>
        ))}
      </div>
    </article>
  );
}
