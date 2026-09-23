"use client";

/**
 * Hooks for the multi-agent UI: the live trace plus a legacy FieldBrief
 * fetch kept for backward compatibility with older sessions.
 *
 * Both poll while the session is processing so the user sees agent
 * decisions stream in without a manual refresh. Once the session is
 * complete (or an endpoint 404s) polling stops.
 */
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { SessionStatus, UUID } from "@/lib/api-types";
import { queryKeys } from "@/lib/query-keys";

const POLL_INTERVAL_MS = 2_000;

/** Polls until the trace appears (and the session is no longer running). */
export function useAgentTrace(
  sessionId: UUID | undefined,
  sessionStatus?: SessionStatus,
) {
  return useQuery({
    queryKey: sessionId ? queryKeys.agentTrace(sessionId) : ["agent-trace", "noop"],
    queryFn: () => api.getAgentTrace(sessionId as UUID),
    enabled: Boolean(sessionId),
    refetchInterval: (query) => {
      // Stop polling once we have a non-null trace AND the session is done.
      const data = query.state.data;
      const stillRunning = sessionStatus === "processing" || sessionStatus === "pending";
      if (!stillRunning && data) return false;
      if (!stillRunning) return false;
      return POLL_INTERVAL_MS;
    },
  });
}

/** Legacy fetch for Field Liaison payloads on older traces. */
export function useFieldBrief(sessionId: UUID | undefined, sessionStatus?: SessionStatus) {
  return useQuery({
    queryKey: sessionId ? queryKeys.fieldBrief(sessionId) : ["field-brief", "noop"],
    queryFn: () => api.getFieldBrief(sessionId as UUID),
    enabled: Boolean(sessionId),
    refetchInterval: (query) => {
      const stillRunning = sessionStatus === "processing" || sessionStatus === "pending";
      if (!stillRunning) return false;
      const data = query.state.data;
      return data ? false : POLL_INTERVAL_MS;
    },
  });
}
