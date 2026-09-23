import { env } from "@/lib/env";
import type {
  AgentTrace,
  BackendErrorBody,
  EvidenceCreate,
  FieldBrief,
  FieldEvidence,
  WaterBodyBulkDelete,
  WaterBodyBulkDeleteResult,
  MonitoringSessionDetail,
  MonitoringSessionListItem,
  SessionCreatePayload,
  SpectralIndex,
  RiskAssessment,
  UUID,
  WaterBody,
  WaterBodyCreate,
  WaterBodyUpdate,
} from "@/lib/api-types";

export class BackendError extends Error {
  readonly status: number;
  readonly detail: BackendErrorBody["detail"] | undefined;

  constructor(status: number, detail: BackendErrorBody["detail"] | undefined, message: string) {
    super(message);
    this.name = "BackendError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  init: RequestInit & { json?: unknown; allow404?: boolean } = {},
): Promise<T> {
  const { json, headers, allow404, ...rest } = init;
  const url = `${env.NEXT_PUBLIC_API_URL}${path}`;
  const finalHeaders = new Headers(headers);
  let body = rest.body;
  if (json !== undefined) {
    finalHeaders.set("content-type", "application/json");
    body = JSON.stringify(json);
  }

  const response = await fetch(url, { ...rest, headers: finalHeaders, body });
  // ``allow404`` lets endpoints that legitimately return 404 (no trace
  // for legacy sessions, no reporter/field-brief payload when the
  // agent layer was off)
  // surface ``null`` to the caller instead of throwing. Used by the
  // multi-agent UI cards.
  if (allow404 && response.status === 404) {
    return null as unknown as T;
  }
  if (!response.ok) {
    let parsed: BackendErrorBody | undefined;
    try {
      parsed = (await response.json()) as BackendErrorBody;
    } catch {
      parsed = undefined;
    }
    const message = parsed
      ? typeof parsed.detail === "string"
        ? parsed.detail
        : `${response.statusText} (${response.status})`
      : `${response.statusText} (${response.status})`;
    throw new BackendError(response.status, parsed?.detail, message);
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => request<{ status: string }>("/api/v1/health"),

  listWaterBodies: () => request<WaterBody[]>("/api/v1/water-bodies"),
  createWaterBody: (payload: WaterBodyCreate) =>
    request<WaterBody>("/api/v1/water-bodies", { method: "POST", json: payload }),
  getWaterBody: (id: UUID) => request<WaterBody>(`/api/v1/water-bodies/${id}`),
  updateWaterBody: (id: UUID, payload: WaterBodyUpdate) =>
    request<WaterBody>(`/api/v1/water-bodies/${id}`, { method: "PATCH", json: payload }),
  deleteWaterBody: (id: UUID) =>
    request<void>(`/api/v1/water-bodies/${id}`, { method: "DELETE" }),
  bulkDeleteWaterBodies: (payload: WaterBodyBulkDelete) =>
    request<WaterBodyBulkDeleteResult>("/api/v1/water-bodies/bulk-delete", {
      method: "POST",
      json: payload,
    }),

  createSession: (payload: SessionCreatePayload) =>
    request<MonitoringSessionDetail>("/api/v1/sessions", {
      method: "POST",
      json: payload,
    }),
  listSessions: (params?: { water_body_id?: UUID; limit?: number; offset?: number }) => {
    const search = new URLSearchParams();
    if (params?.water_body_id) search.set("water_body_id", params.water_body_id);
    if (params?.limit) search.set("limit", String(params.limit));
    if (params?.offset) search.set("offset", String(params.offset));
    const qs = search.toString();
    return request<MonitoringSessionListItem[]>(
      `/api/v1/sessions${qs ? `?${qs}` : ""}`,
    );
  },
  getSession: (id: UUID) => request<MonitoringSessionDetail>(`/api/v1/sessions/${id}`),
  getIndices: (id: UUID) => request<SpectralIndex[]>(`/api/v1/sessions/${id}/indices`),
  getRisk: (id: UUID) => request<RiskAssessment | null>(`/api/v1/sessions/${id}/risk`),
  getAgentTrace: (id: UUID) =>
    request<AgentTrace | null>(`/api/v1/sessions/${id}/trace`, { allow404: true }),
  getFieldBrief: (id: UUID) =>
    request<FieldBrief | null>(`/api/v1/sessions/${id}/field-brief`, { allow404: true }),

  submitEvidence: (id: UUID, payload: EvidenceCreate, photo?: File | null) => {
    const form = new FormData();
    form.set("payload", JSON.stringify(payload));
    if (photo) form.set("photo", photo);
    return request<FieldEvidence>(`/api/v1/sessions/${id}/evidence`, {
      method: "POST",
      body: form,
    });
  },
  listEvidence: (id: UUID) =>
    request<FieldEvidence[]>(`/api/v1/sessions/${id}/evidence`),

  reportUrl: (id: UUID) => `${env.NEXT_PUBLIC_API_URL}/api/v1/sessions/${id}/report`,
};
