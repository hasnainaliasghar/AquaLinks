"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { SessionCreatePayload, UUID } from "@/lib/api-types";
import { queryKeys } from "@/lib/query-keys";

export function useSessions(params?: { water_body_id?: UUID; limit?: number }) {
  return useQuery({
    queryKey: queryKeys.sessions(params),
    queryFn: () => api.listSessions(params),
  });
}

export function useSession(id: UUID, options?: { polling?: boolean }) {
  return useQuery({
    queryKey: queryKeys.session(id),
    queryFn: () => api.getSession(id),
    refetchInterval: (query) => {
      if (!options?.polling) return false;
      const status = query.state.data?.status;
      return status === "processing" || status === "pending" ? 2_000 : false;
    },
  });
}

export function useCreateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: SessionCreatePayload) => api.createSession(payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: queryKeys.sessions() });
      qc.setQueryData(queryKeys.session(data.id), data);
    },
  });
}
