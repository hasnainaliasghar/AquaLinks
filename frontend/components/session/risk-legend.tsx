import { cn } from "@/lib/utils";

const TIERS = [
  {
    color: "var(--risk-low)",
    label: "Low",
    range: "0–32",
    hint: "Routine monitoring is fine.",
  },
  {
    color: "var(--risk-medium)",
    label: "Medium",
    range: "33–65",
    hint: "Sample within a week.",
  },
  {
    color: "var(--risk-high)",
    label: "High",
    range: "66–100",
    hint: "Sample within 48 hours.",
  },
] as const;

/**
 * A small, screen-reader-friendly legend explaining what the risk
 * colours mean. Reused by the session detail risk card and the PDF report.
 */
export function RiskLegend({ className }: { className?: string }) {
  return (
    <div
      role="group"
      aria-label="Risk score legend"
      className={cn(
        "flex flex-col gap-2 rounded-md border border-border bg-surface-1/60 p-3 text-xs",
        className,
      )}
    >
      <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
        How to read the score
      </p>
      <ul className="space-y-1.5">
        {TIERS.map((tier) => (
          <li key={tier.label} className="flex items-center gap-2.5">
            <span
              aria-hidden
              className="inline-block size-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: tier.color }}
            />
            <span className="font-medium text-foreground">{tier.label}</span>
            <span className="font-mono text-muted-foreground">{tier.range}</span>
            <span className="text-muted-foreground">— {tier.hint}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
