import type { Metadata } from "next";

import { FadeIn } from "@/components/motion/fade-in";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "Limitations",
  description:
    "AquaLinks is an advisory tool. It does not certify water safety, detect toxins, or replace laboratory testing.",
  path: "/limitations",
});

const ITEMS = [
  {
    title: "Not certified.",
    body: "AquaLinks does not produce certified water-quality results. Spectral indices are statistical proxies for water-quality parameters; certification requires accredited laboratory analysis.",
  },
  {
    title: "No toxin detection.",
    body: "AquaLinks does not detect cyanotoxins, heavy metals, or pathogens. Bloom-related indices are precursor signals, not toxin measurements.",
  },
  {
    title: "Scene age and cloud cover.",
    body: "Sentinel-2 revisit time is 5 days at the equator and varies elsewhere. A high-cloud day means the latest usable scene may be a week or two old. Every report shows the capture date and cloud percentage.",
  },
  {
    title: "Mixed pixels.",
    body: "Indices computed over the water mask still mix shallow vegetation, sediment plumes, and shoreline in their tails. Treat individual pixels with skepticism; aggregate means are more robust.",
  },
  {
    title: "Field evidence required.",
    body: "Remote sensing never replaces field sampling. AquaLinks prioritises where to sample. The final assessment still requires a wet-lab measurement.",
  },
  {
    title: "Advisory only.",
    body: "Every report carries an advisory disclaimer. Don’t use AquaLinks to make public-safety decisions on its own.",
  },
];

export default function LimitationsPage() {
  return (
    <article className="container max-w-3xl py-20">
      <FadeIn>
        <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          Limitations
        </p>
        <h1 className="mt-2 font-display text-4xl tracking-tight sm:text-5xl">
          What AquaLinks is not.
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
          We’d rather under-promise than over-claim. AquaLinks is built to help field teams
          decide where to sample first — not to replace the chemistry that comes after.
        </p>
      </FadeIn>

      <div className="mt-12 space-y-4">
        {ITEMS.map((item) => (
          <FadeIn key={item.title}>
            <section className="rounded-md border border-border bg-card p-6">
              <h2 className="font-display text-xl tracking-tight">{item.title}</h2>
              <p className="mt-2 text-muted-foreground">{item.body}</p>
            </section>
          </FadeIn>
        ))}
      </div>
    </article>
  );
}
