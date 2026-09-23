/**
 * TypeScript mirrors of the backend's Pydantic schemas.
 *
 * Keep this file in sync with `backend/app/schemas/*`. The CI e2e job
 * fails if the live OpenAPI schema drifts from this declaration.
 */

export type UUID = string;
export type ISODateTime = string;
export type ISODate = string;

export type GeoJSONPolygon = {
  type: "Polygon";
  coordinates: number[][][];
};

export type GeoJSONPoint = {
  type: "Point";
  coordinates: [number, number];
};

export type WaterBody = {
  id: UUID;
  name: string;
  description: string | null;
  geometry: GeoJSONPolygon;
  centroid: GeoJSONPoint | null;
  area_km2: number | null;
  source: string | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
};

export type WaterBodyCreate = {
  name: string;
  description?: string | null;
  geometry: GeoJSONPolygon;
  source?: string | null;
};

export type WaterBodyUpdate = {
  name?: string;
  description?: string | null;
};

export type WaterBodyBulkDelete = {
  ids: UUID[];
};

export type WaterBodyBulkDeleteResult = {
  requested_count: number;
  deleted_count: number;
};

export type SessionStatus =
  | "pending"
  | "processing"
  | "awaiting_evidence"
  | "complete"
  | "failed";

export type IndexName = "NDWI" | "MNDWI" | "NDTI" | "NDCI" | "NDVI" | "WRI";

export type SpectralIndex = {
  id: UUID;
  session_id: UUID;
  name: IndexName;
  value: number;
  min_value: number | null;
  max_value: number | null;
  stddev: number | null;
  interpretation: string | null;
  bands: string[];
  sample_count: number | null;
  extra: Record<string, unknown> | null;
  created_at: ISODateTime;
};

export type WaterColor =
  | "clear"
  | "blue"
  | "green"
  | "brown"
  | "yellow"
  | "red"
  | "black"
  | "other";

export type Odor =
  | "none"
  | "earthy"
  | "musty"
  | "fishy"
  | "rotten"
  | "chemical"
  | "sewage"
  | "other";

export type FieldEvidence = {
  id: UUID;
  session_id: UUID;
  water_color: WaterColor;
  odor: Odor;
  algae_present: boolean;
  dead_fish_count: number;
  rainfall_mm: number;
  complaints_count: number;
  notes: string | null;
  photo_url: string | null;
  latitude: number | null;
  longitude: number | null;
  reporter_name: string | null;
  created_at: ISODateTime;
};

export type EvidenceCreate = {
  water_color: WaterColor;
  odor: Odor;
  algae_present?: boolean;
  dead_fish_count?: number;
  rainfall_mm?: number;
  complaints_count?: number;
  notes?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  reporter_name?: string | null;
};

export type RiskLevel = "low" | "medium" | "high";
export type Urgency = "routine" | "elevated" | "immediate";

export type RiskAssessment = {
  id: UUID;
  session_id: UUID;
  score: number;
  level: RiskLevel;
  urgency: Urgency;
  recommendation: string;
  reasoning: string;
  limitations: string;
  contributors: Record<string, number>;
  model_id: string;
  // Multi-agent layer additions. Both nullable for legacy sessions.
  // `field_brief` is a legacy JSON slot: old runs store FieldBrief,
  // newer runs may store Reporter summary payloads.
  agent_trace_id: UUID | null;
  field_brief: Record<string, unknown> | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
};

// ---------------------------------------------------------------------
// Agent trace + reporter summary (multi-agent layer)
// ---------------------------------------------------------------------

export type AgentName =
  | "coordinator"
  | "scout"
  | "historian"
  | "analyst"
  | "reporter"
  | "field_liaison";

export type AgentToolCall = {
  name: string;
  arguments: Record<string, unknown>;
  result: unknown | null;
  error: string | null;
  latency_ms: number;
  started_at: string;
};

export type AgentRun = {
  schema_version: number;
  agent: AgentName | string;
  started_at: string;
  completed_at: string | null;
  latency_ms: number;
  tokens_in: number;
  tokens_out: number;
  tool_calls: AgentToolCall[];
  outputs: Record<string, unknown> | null;
  error: string | null;
};

export type AgentTrace = {
  id: UUID;
  session_id: UUID;
  coordinator_plan: {
    plan?: Array<{
      agent: AgentName | string;
      reason: string;
      budget?: { max_tool_calls?: number; max_seconds?: number };
    }>;
    rationale?: string;
    estimated_complexity?: "low" | "medium" | "high";
  };
  agent_runs: AgentRun[];
  total_tokens_in: number;
  total_tokens_out: number;
  total_latency_ms: number;
  gemini_model: string;
  created_at: ISODateTime;
  updated_at: ISODateTime;
};

export type FieldTaskPriority = "p0" | "p1" | "p2";

export type FieldTask = {
  priority: FieldTaskPriority;
  location: { lat: number; lng: number; description: string };
  sample_type: string;
  equipment: string[];
  photo_prompts: string[];
  estimated_minutes: number;
};

export type FieldBrief = {
  tasks: FieldTask[];
  turnaround_hours: number;
  escalate_to: string | null;
};

export type AOIType = "water" | "mixed" | "land";

/**
 * Plain-English verdict shown to the citizen reading the session page.
 *
 * Produced by the Reporter agent when available, with deterministic
 * fallback server-side from risk + AOI classification + evidence.
 */
export type CitizenSummaryTone = "safe" | "caution" | "avoid" | "not_water" | "unknown";

export type CitizenSummary = {
  tone: CitizenSummaryTone;
  headline: string;
  bottom_line: string;
  safety_for_humans: string;
  safety_for_pets_and_kids: string;
  what_we_could_not_check: string;
  citations: Array<{
    title: string | null;
    uri: string;
    published_at: string | null;
  }>;
};

export type MonitoringSessionDetail = {
  id: UUID;
  water_body: WaterBody;
  start_date: ISODate;
  end_date: ISODate;
  max_cloud_cover: number;
  status: SessionStatus;
  status_message: string | null;
  scene_id: string | null;
  scene_capture_date: ISODateTime | null;
  scene_cloud_cover: number | null;
  scene_provider: string | null;
  scene_thumbnail_url: string | null;
  scene_metadata: Record<string, unknown> | null;
  water_fraction: number | null;
  aoi_type: AOIType | null;
  indices: SpectralIndex[];
  evidence: FieldEvidence[];
  risk: RiskAssessment | null;
  citizen_summary: CitizenSummary | null;
  report_id: UUID | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
};

export type MonitoringSessionListItem = {
  id: UUID;
  water_body_id: UUID;
  water_body_name: string;
  water_body_latitude: number | null;
  water_body_longitude: number | null;
  start_date: ISODate;
  end_date: ISODate;
  status: SessionStatus;
  risk_level: RiskLevel | null;
  risk_score: number | null;
  scene_capture_date: ISODateTime | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
};

export type SessionCreatePayload = {
  water_body_id?: UUID;
  new_water_body?: {
    name: string;
    description?: string | null;
    geometry: GeoJSONPolygon;
    source?: string;
  };
  start_date?: ISODate;
  end_date?: ISODate;
  max_cloud_cover?: number;
};

export type BackendErrorBody = {
  detail: string | Array<{ loc: (string | number)[]; msg: string; type: string }>;
};
