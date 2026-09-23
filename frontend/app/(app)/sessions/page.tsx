"use client";

import { Suspense } from "react";
import { useQueryState } from "nuqs";

import { SessionCard } from "@/components/session/session-card";
import { Skeleton } from "@/components/ui/skeleton";
import { FadeIn } from "@/components/motion/fade-in";
import { useSessions } from "@/hooks/use-sessions";
import type { RiskLevel, SessionStatus } from "@/lib/api-types";
import { cn } from "@/lib/utils";

const STATUS_FILTERS: { value: SessionStatus | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "processing", label: "Processing" },
  { value: "complete", label: "Complete" },
  { value: "failed", label: "Failed" },
];
const RISK_FILTERS: { value: RiskLevel | "all"; label: string }[] = [
  { value: "all", label: "All risk" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

export default function SessionsPage() {
  return (
    <Suspense fallback={<SessionsPageSkeleton />}>
      <SessionsPageContent />
    </Suspense>
  );
}

function SessionsPageContent() {
  const [status, setStatus] = useQueryState("status", { defaultValue: "all" });
  const [risk, setRisk] = useQueryState("risk", { defaultValue: "all" });
  const sessions = useSessions({ limit: 100 });

  const filtered = (sessions.data ?? []).filter((s) => {
    const statusOk = status === "all" || s.status === status;
    const riskOk = risk === "all" || s.risk_level === risk;
    return statusOk && riskOk;
  });

  return (
    <div className="container max-w-7xl py-10">
      <FadeIn>
        <header>
          <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
            Library
          </p>
          <h1 className="mt-1 font-display text-3xl tracking-tight sm:text-4xl">
            Sessions
          </h1>
        </header>
      </FadeIn>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <FilterGroup
          label="Status"
          value={status}
          options={STATUS_FILTERS}
          onChange={(v) => setStatus(v)}
        />
        <FilterGroup
          label="Risk"
          value={risk}
          options={RISK_FILTERS}
          onChange={(v) => setRisk(v)}
        />
      </div>

      <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {sessions.isLoading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-36 w-full rounded-xl" />
          ))
        ) : filtered.length === 0 ? (
          <div className="col-span-full rounded-md border border-dashed border-border bg-surface-1 p-10 text-center">
            <p className="font-display text-lg tracking-tight">
              Nothing matches that filter.
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Try clearing the chips above or start a new session.
            </p>
          </div>
        ) : (
          filtered.map((s) => (
            <FadeIn key={s.id}>
              <SessionCard session={s} />
            </FadeIn>
          ))
        )}
      </section>
    </div>
  );
}

function SessionsPageSkeleton() {
  return (
    <div className="container max-w-7xl py-10">
      <header>
        <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          Library
        </p>
        <h1 className="mt-1 font-display text-3xl tracking-tight sm:text-4xl">Sessions</h1>
      </header>
      <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-36 w-full rounded-xl" />
        ))}
      </section>
    </div>
  );
}

function FilterGroup<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T | null;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="inline-flex items-center gap-2">
      <span className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <div className="inline-flex rounded-md border border-border bg-card p-1">
        {options.map((option) => {
          const active = (value ?? options[0]?.value) === option.value;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onChange(option.value)}
              className={cn(
                "rounded-xs px-2.5 py-1 text-xs transition-colors",
                active ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
