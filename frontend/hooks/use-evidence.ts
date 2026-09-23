"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { EvidenceCreate, UUID } from "@/lib/api-types";
import { queryKeys } from "@/lib/query-keys";

export function useSubmitEvidence(sessionId: UUID) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ payload, photo }: { payload: EvidenceCreate; photo?: File | null }) =>
      api.submitEvidence(sessionId, payload, photo ?? undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.session(sessionId) });
      qc.invalidateQueries({ queryKey: queryKeys.evidence(sessionId) });
      qc.invalidateQueries({ queryKey: queryKeys.risk(sessionId) });
    },
  });
}
