import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Logo } from "@/components/chrome/logo";

export default function NotFound() {
  return (
    <main className="grid min-h-screen place-items-center px-6">
      <div className="max-w-md space-y-6 text-center">
        <Logo className="justify-center" />
        <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          Error · 404
        </p>
        <h1 className="font-display text-3xl tracking-tight">Lost at sea.</h1>
        <p className="text-muted-foreground">
          The page you were looking for isn’t here. Head back to the dashboard or start a new
          monitoring session.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-2">
          <Button asChild>
            <Link href="/dashboard">Open the app</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/">Go home</Link>
          </Button>
        </div>
      </div>
    </main>
  );
}
