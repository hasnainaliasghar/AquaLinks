import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { FieldBriefView } from "@/components/session/field-brief-card";
import type { FieldBrief } from "@/lib/api-types";

const BRIEF: FieldBrief = {
  tasks: [
    {
      priority: "p0",
      location: {
        lat: 45.985,
        lng: 9.25,
        description: "North shore inlet",
      },
      sample_type: "grab water sample for chlorophyll-a",
      equipment: ["dark sample bottle", "0.45 um filter", "ice pack"],
      photo_prompts: ["wide shot of north shore", "close-up of any algal mats"],
      estimated_minutes: 60,
    },
  ],
  turnaround_hours: 24,
  escalate_to: "local water authority",
};

describe("FieldBriefView", () => {
  it("renders task, equipment, plain-English turnaround and escalation", () => {
    render(<FieldBriefView brief={BRIEF} />);
    // "grab water sample for chlorophyll-a" gets rewritten to plain English.
    expect(screen.getByText(/take a water sample/i)).toBeInTheDocument();
    expect(screen.getByText(/north shore inlet/i)).toBeInTheDocument();
    expect(screen.getByText(/finish within 24 hours/i)).toBeInTheDocument();
    expect(screen.getAllByText(/local water authority/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/do today/i)).toBeInTheDocument();
    expect(screen.getByText(/dark sample bottle/i)).toBeInTheDocument();
  });
});
