"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { FadeIn } from "@/components/motion/fade-in";
import { Button } from "@/components/ui/button";

export function CTA() {
  return (
    <section className="container py-24 sm:py-32">
      <FadeIn>
        <div className="relative isolate overflow-hidden rounded-2xl border border-border bg-card p-10 shadow-elev-3 sm:p-14">
          <div
            aria-hidden
            className="pointer-events-none absolute -inset-1 -z-10 bg-gradient-to-br from-aqua-500/15 via-transparent to-aqua-700/20"
          />
          <div className="grid items-center gap-8 sm:grid-cols-[2fr_1fr]">
            <div>
              <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                Ready when you are
              </p>
              <h2 className="mt-2 max-w-xl font-display text-3xl tracking-tight sm:text-4xl">
                Point AquaLinks at any lake on Earth and watch the pipeline run.
              </h2>
              <p className="mt-3 max-w-xl text-balance text-muted-foreground">
                Drawing the polygon takes ten seconds. The first scene, indices, and risk
                brief land less than a minute later — no account required.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3 sm:justify-end">
              <Button asChild size="lg">
                <Link href="/monitor" className="group">
                  Start monitoring
                  <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/dashboard">Open dashboard</Link>
              </Button>
            </div>
          </div>
        </div>
      </FadeIn>
    </section>
  );
}
