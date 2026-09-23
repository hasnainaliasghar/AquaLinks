import { ShieldAlert } from "lucide-react";

import { RiskBadge } from "@/components/session/risk-badge";
import { RiskLegend } from "@/components/session/risk-legend";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TermInfo } from "@/components/ui/term-info";
import type { RiskAssessment, RiskLevel } from "@/lib/api-types";
import type { GlossaryKey } from "@/lib/glossary";

const LEVEL_KEY: Record<RiskLevel, GlossaryKey> = {
  low: "riskLow",
  medium: "riskMedium",
  high: "riskHigh",
};

export function RiskCard({ risk }: { risk: RiskAssessment }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="inline-flex items-center gap-2 text-lg">
          Risk assessment
          <TermInfo termKey="riskScore" />
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
          <RiskBadge level={risk.level} score={risk.score} />
          <div className="flex flex-1 flex-col gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge
                variant={badgeVariantForLevel(risk.level)}
                className="inline-flex items-center gap-1 px-3 py-1 text-xs"
              >
                {risk.level}
                <TermInfo termKey={LEVEL_KEY[risk.level]} className="text-current" />
              </Badge>
              <span className="inline-flex items-center gap-1.5 font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                <ShieldAlert className="size-3.5" />
                Urgency · {risk.urgency}
                <TermInfo termKey="urgency" />
              </span>
            </div>
            <p className="text-sm font-medium leading-relaxed">{risk.recommendation}</p>
            <p className="flex items-start gap-1.5 text-sm text-muted-foreground leading-relaxed">
              <span className="flex-1">{risk.reasoning}</span>
              <TermInfo termKey="reasoning" />
            </p>
          </div>
        </div>

        <RiskLegend className="mt-6" />

        <div className="mt-4 rounded-md border border-risk-high/30 bg-risk-high/10 p-4 text-sm">
          <p className="inline-flex items-center gap-1.5 font-mono text-2xs uppercase tracking-wider text-risk-high">
            Limitations
            <TermInfo termKey="limitations" />
          </p>
          <p className="mt-1 text-foreground/85">{risk.limitations}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function badgeVariantForLevel(level: string) {
  if (level === "high") return "danger" as const;
  if (level === "medium") return "warning" as const;
  return "success" as const;
}
