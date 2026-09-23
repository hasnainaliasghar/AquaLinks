"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { Logo } from "@/components/chrome/logo";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surface to client-side telemetry if present; otherwise console.
    console.error("AquaLens client error", error);
  }, [error]);

  return (
    <main className="grid min-h-screen place-items-center px-6">
      <div className="max-w-md space-y-6 text-center">
        <Logo className="justify-center" />
        <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          Error · client
        </p>
        <h1 className="font-display text-3xl tracking-tight">Something went sideways.</h1>
        <p className="text-muted-foreground">
          We hit an unexpected error rendering this page. Reload to try again, or head back
          to the dashboard.
        </p>
        {error.digest ? (
          <p className="font-mono text-2xs text-muted-foreground">ref · {error.digest}</p>
        ) : null}
        <div className="flex flex-wrap items-center justify-center gap-2">
          <Button onClick={() => reset()}>Try again</Button>
          <Button asChild variant="outline">
            <a href="/dashboard">Back to dashboard</a>
          </Button>
        </div>
      </div>
    </main>
  );
}
