import type { SessionStatus } from "@/lib/api-types";
import { cn } from "@/lib/utils";

const COPY: Record<SessionStatus, string> = {
  pending: "Queued",
  processing: "Processing",
  awaiting_evidence: "Awaiting evidence",
  complete: "Complete",
  failed: "Failed",
};

const TONE: Record<SessionStatus, string> = {
  pending: "bg-muted text-muted-foreground",
  processing: "bg-aqua-500/15 text-aqua-700 dark:text-aqua-200",
  awaiting_evidence: "bg-risk-medium/20 text-risk-medium-fg dark:text-risk-medium",
  complete: "bg-risk-low/25 text-risk-low-fg dark:text-risk-low",
  failed: "bg-risk-high/20 text-risk-high",
};

export function StatusPill({ status, className }: { status: SessionStatus; className?: string }) {
  const isLive = status === "processing" || status === "pending";
  const dotClass =
    status === "complete"
      ? "bg-emerald-500"
      : status === "failed"
        ? "bg-rose-500"
        : isLive
          ? "animate-pulse bg-current"
          : "bg-current/70";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-0.5 text-2xs font-medium uppercase tracking-wider",
        TONE[status],
        className,
      )}
    >
      <span className={cn("size-1.5 rounded-full", dotClass)} />
      {COPY[status]}
    </span>
  );
}
