"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { EvidenceForm } from "@/components/evidence/evidence-form";
import { FadeIn } from "@/components/motion/fade-in";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function EvidencePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;

  return (
    <div className="container max-w-2xl py-10">
      <FadeIn>
        <Link
          href={`/sessions/${id}`}
          className="inline-flex items-center gap-1 font-mono text-2xs uppercase tracking-wider text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3" /> Session
        </Link>
        <h1 className="mt-2 font-display text-3xl tracking-tight sm:text-4xl">
          Field evidence
        </h1>
        <p className="mt-2 text-muted-foreground">
          Submit what the field team observed. The risk model re-runs immediately and
          Gemini rewrites the brief on the next refresh.
        </p>
      </FadeIn>

      <div className="mt-8">
        <FadeIn>
          <Card>
            <CardHeader>
              <CardTitle>New observation</CardTitle>
            </CardHeader>
            <CardContent>
              <EvidenceForm
                sessionId={id}
                onSubmitted={() => {
                  router.push(`/sessions/${id}`);
                }}
              />
            </CardContent>
          </Card>
        </FadeIn>
      </div>
    </div>
  );
}
