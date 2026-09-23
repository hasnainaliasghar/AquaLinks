"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api-client";
import type { UUID, WaterBodyBulkDelete, WaterBodyUpdate } from "@/lib/api-types";
import { queryKeys } from "@/lib/query-keys";

export function useWaterBodies() {
  return useQuery({ queryKey: queryKeys.waterBodies, queryFn: api.listWaterBodies });
}

export function useUpdateWaterBody(id: UUID) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: WaterBodyUpdate) => api.updateWaterBody(id, payload),
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.waterBody(id), data);
      qc.invalidateQueries({ queryKey: queryKeys.waterBodies });
      qc.invalidateQueries({ queryKey: queryKeys.sessions() });
    },
  });
}

export function useDeleteWaterBody() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: UUID) => api.deleteWaterBody(id),
    onSuccess: (_data, id) => {
      qc.removeQueries({ queryKey: queryKeys.waterBody(id) });
      qc.invalidateQueries({ queryKey: queryKeys.waterBodies });
      qc.invalidateQueries({ queryKey: queryKeys.sessions() });
    },
  });
}

export function useBulkDeleteWaterBodies() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: WaterBodyBulkDelete) => api.bulkDeleteWaterBodies(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.waterBodies });
      qc.invalidateQueries({ queryKey: queryKeys.sessions() });
    },
  });
}
