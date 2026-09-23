"use client";

import Link from "next/link";
import { Info } from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { GLOSSARY, type GlossaryKey } from "@/lib/glossary";
import { cn } from "@/lib/utils";

type Side = "top" | "bottom" | "left" | "right";

/**
 * Small info-icon that opens a glossary tooltip on hover or focus. Use
 * this anywhere a technical term shows up in the UI so a non-expert can
 * learn what it means without leaving the screen.
 */
export function TermInfo({
  termKey,
  side = "top",
  className,
}: {
  termKey: GlossaryKey;
  side?: Side;
  className?: string;
}) {
  const entry = GLOSSARY[termKey];
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label={`What is ${entry.term}?`}
          className={cn(
            "inline-flex size-3.5 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            className,
          )}
        >
          <Info className="size-3.5" />
        </button>
      </TooltipTrigger>
      <TooltipContent side={side} className="max-w-xs space-y-1 rounded-md p-3 text-xs">
        <p className="font-medium text-foreground">{entry.term}</p>
        <p className="text-muted-foreground">{entry.short}</p>
        {"detail" in entry && entry.detail ? (
          <p className="text-muted-foreground">{entry.detail}</p>
        ) : null}
        {"link" in entry && entry.link ? (
          <Link
            href={entry.link}
            className="block text-aqua-500 underline-offset-2 hover:underline"
          >
            Learn more →
          </Link>
        ) : null}
      </TooltipContent>
    </Tooltip>
  );
}
