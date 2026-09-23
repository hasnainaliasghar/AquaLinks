import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { RiskCard } from "@/components/session/risk-card";
import { TooltipProvider } from "@/components/ui/tooltip";
import type { RiskAssessment } from "@/lib/api-types";

const RISK: RiskAssessment = {
  id: "00000000-0000-0000-0000-000000000001",
  session_id: "00000000-0000-0000-0000-000000000002",
  score: 0.72,
  level: "high",
  urgency: "immediate",
  recommendation: "Dispatch a sampling team within 48 hours.",
  reasoning: "NDCI and NDTI both elevated; field evidence shows green water and algae.",
  limitations: "Advisory only; not a substitute for laboratory testing.",
  contributors: { ndci: 0.4, ndti: 0.2 },
  model_id: "gemini-2.5-flash",
  agent_trace_id: null,
  field_brief: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe("RiskCard", () => {
  it("renders the level, recommendation, and limitations", () => {
    render(
      <TooltipProvider>
        <RiskCard risk={RISK} />
      </TooltipProvider>,
    );
    expect(screen.getAllByText(/high/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/dispatch a sampling team/i)).toBeInTheDocument();
    expect(screen.getByText(/advisory only/i)).toBeInTheDocument();
  });
});
