# Architecture

AquaLens is a small monorepo with three pieces: a FastAPI backend, a
Next.js frontend, and a Postgres + PostGIS database. Everything runs on
free-tier services and can be lifted onto any provider.

```mermaid
flowchart LR
  subgraph Browser
    UI[Next.js / React app]
  end
  subgraph Backend
    API[FastAPI]
    PIPE[Agent pipeline]
  end
  subgraph External
    PC[Microsoft Planetary Computer<br/>Sentinel-2 L2A STAC]
    GEM[Gemini 2.5 Flash]
  end
  subgraph Storage
    DB[(Postgres + PostGIS)]
    DISK[(Local disk · reports + uploads)]
  end

  UI -- REST --> API
  API --> DB
  API -- BackgroundTasks --> PIPE
  PIPE -- STAC search + COG read --> PC
  PIPE -- narrative --> GEM
  PIPE --> DB
  PIPE --> DISK
  UI -- /uploads, /reports --> DISK
```

## Backend modules

| Module | Responsibility |
| --- | --- |
| `app.core.config` | Pydantic-settings env loader. |
| `app.core.database` | SQLAlchemy engine, session factory. |
| `app.core.tasks` | `JobRunner` protocol + `InProcessJobRunner` wrapping `BackgroundTasks`. |
| `app.models.*` | SQLModel tables for water bodies, sessions, indices, evidence, risk assessments, reports. |
| `app.schemas.*` | Pydantic v2 request/response DTOs. |
| `app.services.satellite.*` | Provider protocol + Planetary Computer impl + offline sample impl + factory. |
| `app.services.indices` | Pure numpy band math for six indices. |
| `app.services.risk_model` | Deterministic weighted score, level, urgency. |
| `app.services.reasoning` | Gemini 2.5 narrative with strict JSON schema. |
| `app.services.evidence_handler` | EXIF-stripping photo uploads. |
| `app.services.report_generator` | Jinja2 + WeasyPrint PDF rendering. |
| `app.services.pipeline` | Orchestrates the agent graph end-to-end. |
| `app.api.v1.endpoints.*` | Public REST handlers. |
| `app.utils.*` | GeoJSON helpers, matplotlib chart SVGs, WeasyPrint wrapper. |

## Frontend modules

| Module | Responsibility |
| --- | --- |
| `app/(marketing)/*` | Landing, methodology, limitations, about, changelog. |
| `app/(app)/*` | Dashboard, monitor, sessions, water bodies, settings. |
| `components/ui/*` | shadcn primitives tuned to brand tokens. |
| `components/chrome/*` | Top nav, sidebar, command palette, theme toggle, footer. |
| `components/marketing/*` | Hero, workflow scrollytell, agent-surface deep dive, indices showcase, citations marquee, CTA. |
| `components/map/*` | MapLibre wrapper, basemap switcher, place / coordinate search, mini-map preview. |
| `components/session/*` | New-session wizard, risk badge, risk card, index grid/table, scene metadata, processing skeleton, agent trace, analysis summary, session card. |
| `components/evidence/*` | Field evidence form, evidence list. |
| `components/report/*` | PDF download button. |
| `lib/*` | API client, types, query client, design tokens, env, format, geo, SEO. |
| `hooks/*` | TanStack Query hooks for sessions, water bodies, evidence. |

## Agent pipeline

```mermaid
sequenceDiagram
  autonumber
  participant UI as Frontend
  participant API as FastAPI
  participant PIPE as Pipeline
  participant PC as Planetary Computer
  participant DB as Postgres
  participant GEM as Gemini

  UI->>API: POST /sessions {polygon, window}
  API->>DB: insert MonitoringSession (status=pending)
  API->>PIPE: BackgroundTasks.run_full(session_id)
  API-->>UI: 201 Created
  PIPE->>PC: STAC search + asset signing + COG read
  PIPE->>PIPE: compute_all() → 6 indices
  PIPE->>DB: persist indices
  PIPE->>PIPE: score_risk() (deterministic, untouched by LLM)
  alt AQUALENS_AGENTIC_MODE=true (production default)
    PIPE->>GEM: Coordinator plan (thinking mode)
    PIPE->>GEM: Scout (function calling + vision)
    PIPE->>GEM: Historian (search grounding + URL context + code exec)
    PIPE->>GEM: Analyst (draft → critique → optional rewrite)
    PIPE->>GEM: Reporter (structured citizen summary)
    GEM-->>PIPE: ReasoningBundle + CitizenSummary + agent trace
    PIPE->>DB: insert AgentTrace + write Historian notes to agent_memory
  else AQUALENS_AGENTIC_MODE=false or AQUALENS_FAKE_GEMINI=true
    PIPE->>GEM: single-call narrative request (schema-enforced JSON)
    GEM-->>PIPE: {recommendation, reasoning, limitations}
  end
  PIPE->>DB: upsert RiskAssessment (linked to AgentTrace when present)
  PIPE->>DB: render HTML + WeasyPrint → Report
  PIPE->>DB: status=complete
  UI->>API: GET /sessions/{id} (polling)
  API-->>UI: full detail
```

## Agent layer

The agent layer is a separate package (`backend/app/services/agent/`)
that runs only when both `AQUALENS_AGENTIC_MODE=true` and a Gemini
API key are configured. It plugs into `services/pipeline.py` at the
narrative step and persists two things alongside the existing
`RiskAssessment` row:

- **`agent_traces`** — JSONB log of the Coordinator plan, every
  sub-agent's tool calls, token usage, and latency. One row per
  session.
- **`agent_memory`** — Historian-written distilled observations
  scoped per water body. Each row carries a 768-dim
  `text-embedding-004` vector so future Historian runs can recall
  semantically related notes, not just the most recent ones. On
  Postgres a `pgvector(768)` mirror column + HNSW cosine index makes
  this fast; on SQLite the Python similarity path runs the same
  ranking in user space.

```mermaid
flowchart LR
    subgraph PLAN["Plan"]
      COORD["Coordinator<br/><i>thinking mode</i><br/>plans the workflow"]
    end
    subgraph GATHER["Gather"]
      direction TB
      SCOUT["Scout · Vision<br/>function calling + multimodal"]
      HIST["Historian<br/>function calling + Google Search<br/>+ URL Context + code execution"]
    end
    subgraph WRITE["Write"]
      direction TB
      AN["Analyst<br/>draft → critique → rewrite"]
      RP["Reporter<br/>plain-English citizen summary"]
    end

    COORD --> SCOUT
    COORD --> HIST
    SCOUT --> AN
    HIST --> AN
    AN --> RP
    HIST <-->|text-embedding-004<br/>pgvector HNSW| MEM[(agent_memory)]
    PLAN -.->|JSONB| TR[(agent_traces)]
    GATHER -.->|JSONB| TR
    WRITE -.->|JSONB| TR

    classDef plan   fill:#0b3b66,stroke:#60a5fa,color:#dbeafe,stroke-width:1.5px;
    classDef gather fill:#0b4f55,stroke:#22d3ee,color:#cffafe,stroke-width:1.5px;
    classDef write  fill:#3b1f5a,stroke:#a78bfa,color:#ede9fe,stroke-width:1.5px;
    classDef data   fill:#3b2a1f,stroke:#fbbf24,color:#fef3c7,stroke-width:1.5px;
    class COORD plan
    class SCOUT,HIST gather
    class AN,RP write
    class MEM,TR data
```

### Cross-session memory loop

The same Historian agent both *reads* prior memory at the start of a
new session and *writes* a fresh distilled observation at the end.
That continuity is what lets the agent layer genuinely manage
multi-step work over time instead of acting as a stateless chatbot.

```mermaid
sequenceDiagram
  autonumber
  participant S1 as Session N (past)
  participant DB as agent_memory<br/>(pgvector HNSW)
  participant S2 as Session N+1 (today)
  participant HIST as Historian agent

  S1->>HIST: completes, e.g. NDCI ↑ 40 % over 60 days
  HIST->>DB: write_persistent_note("escalation: bloom suspected", embed)
  Note over DB: 768-d text-embedding-004 vector stored<br/>and indexed with HNSW cosine
  S2->>HIST: new session begins for the same water body
  HIST->>DB: semantic_recall_notes(query about the current state)
  DB-->>HIST: top-k prior notes by cosine similarity
  HIST->>HIST: weaves prior context into the briefing
  HIST->>DB: write_persistent_note(...) for next time
```

Full per-agent specs, tool inventories, and failure-handling rules
live in [`docs/agent_layer.md`](agent_layer.md).

## Data flow guarantees

- The deterministic risk score is computed before any LLM call. The LLM
  cannot move a session up or down a risk band.
- Imagery is streamed; AquaLens never persists raw GeoTIFFs. Only the
  derived numeric indices and provider metadata land in the database.
- Photos uploaded with evidence are stripped of EXIF (including any
  embedded GPS) before being written to disk.
- Every report contains the advisory disclaimer in two places (top
  banner and footer); the same text appears on the in-browser report
  view.
