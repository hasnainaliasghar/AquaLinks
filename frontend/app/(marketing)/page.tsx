import type { Metadata } from "next";

import { AgentConstellation } from "@/components/marketing/agent-constellation";
import { CitationsMarquee } from "@/components/marketing/citations";
import { CTA } from "@/components/marketing/cta";
import { Hero } from "@/components/marketing/hero";
import { IndicesShowcase } from "@/components/marketing/indices-showcase";
import { Workflow } from "@/components/marketing/workflow";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "AquaLinks — autonomous freshwater monitoring",
  description:
    "Pick an area on the map. AquaLinks fetches Sentinel-2, computes water-quality indices, fuses field evidence, and writes an advisory risk brief — wrapped by a five-agent Gemini workflow.",
  path: "/",
});

export default function Landing() {
  // Hero pitches the product, IndicesShowcase explains *what* is
  // measured, Workflow shows *how* the two pipelines run, and
  // AgentConstellation drills into the agent layer. FeatureGrid was
  // dropped — it duplicated the same material as Workflow / agent
  // surface but in shallower form.
  return (
    <>
      <Hero />
      <IndicesShowcase />
      <Workflow />
      <AgentConstellation />
      <CitationsMarquee />
      <CTA />
    </>
  );
}
