import type { UUID } from "@/lib/api-types";

export const queryKeys = {
  waterBodies: ["water-bodies"] as const,
  waterBody: (id: UUID) => ["water-bodies", id] as const,
  sessions: (filter?: { water_body_id?: UUID }) =>
    ["sessions", filter ?? {}] as const,
  session: (id: UUID) => ["sessions", id] as const,
  indices: (id: UUID) => ["sessions", id, "indices"] as const,
  risk: (id: UUID) => ["sessions", id, "risk"] as const,
  evidence: (id: UUID) => ["sessions", id, "evidence"] as const,
  agentTrace: (id: UUID) => ["sessions", id, "agent-trace"] as const,
  fieldBrief: (id: UUID) => ["sessions", id, "field-brief"] as const,
};
