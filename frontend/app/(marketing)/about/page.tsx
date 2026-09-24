import type { Metadata } from "next";

import { FadeIn } from "@/components/motion/fade-in";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "About",
  description:
    "AquaLinks is an open-source freshwater monitoring platform with a deterministic remote-sensing core and a traceable Groq agent workflow.",
  path: "/about",
});

export default function AboutPage() {
  return (
    <article className="container max-w-3xl py-20">
      <FadeIn>
        <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          About
        </p>
        <h1 className="mt-2 font-display text-4xl tracking-tight sm:text-5xl">
          Built for the field. Built to be inspected.
        </h1>
      </FadeIn>

      <div className="mt-10 space-y-8 text-lg text-muted-foreground">
        <FadeIn as="section">
          <p>
            AquaLinks helps municipalities, environmental consultants, lake
            managers, NGOs, and researchers triage freshwater monitoring
            work. It runs a deterministic remote-sensing core first
            (Sentinel-2 retrieval, six water-quality spectral indices, a
            weighted risk score), then a five-agent Groq layer — Coordinator,
            Scout, Historian, Analyst, Reporter — that adds context and
            writes the brief and citizen-facing summary.
          </p>
        </FadeIn>

        <FadeIn as="section">
          <h2 className="font-display text-2xl text-foreground tracking-tight">
            Why it exists
          </h2>
          <p>
            Freshwater bodies suffer from pollution, eutrophication, and harmful algal
            blooms — and many regions can’t afford continuous in-situ monitoring.
            Satellite indices fill part of the gap, but extracting actionable insight
            from spectral data requires domain expertise. AquaLinks reduces that gap by
            handling the pipeline end to end and producing an honest, advisory output
            the field team can act on.
          </p>
        </FadeIn>

        <FadeIn as="section">
          <h2 className="font-display text-2xl text-foreground tracking-tight">
            Project context
          </h2>
          <p>
            AquaLinks is designed as a deployment-ready product: deterministic
            where numbers must be reproducible, agentic where context and
            communication matter. The repository is open-source under the MIT
            License and structured for real-world pilots in municipal,
            environmental, and enterprise workflows.
          </p>
        </FadeIn>

        <FadeIn as="section">
          <h2 className="font-display text-2xl text-foreground tracking-tight">
            Author
          </h2>
          <p>
            Talha Abid —{" "}
            <a
              className="text-foreground underline decoration-aqua-500 underline-offset-4"
              href="https://github.com/talhaabidj1"
              rel="noreferrer"
            >
              github.com/talhaabidj1
            </a>
            .
          </p>
        </FadeIn>
      </div>
    </article>
  );
}
