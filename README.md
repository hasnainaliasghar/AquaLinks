<div align="center">

<a href="https://github.com/talhaabidj/aqualens">
  <img src="https://raw.githubusercontent.com/talhaabidj/aqualens/main/assets/logo-animated.svg?v=3" width="720" alt="AquaLens — autonomous freshwater monitoring" />
</a>

**Autonomous freshwater monitoring with two linked pipelines: a deterministic remote-sensing core, and a traceable Gemini agent workflow.**

[![License: MIT](https://img.shields.io/badge/license-MIT-facc15.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab.svg)](https://python.org)
[![Next.js 15](https://img.shields.io/badge/next.js-15-000000.svg)](https://nextjs.org)
[![FastAPI 0.115](https://img.shields.io/badge/fastapi-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL 16 + PostGIS](https://img.shields.io/badge/postgres-16%20%2B%20postgis-336791.svg)](https://postgis.net)
[![Gemini 2.5 Flash](https://img.shields.io/badge/gemini-2.5%20flash-4285f4.svg)](https://ai.google.dev/gemini-api/docs)

[Architecture](docs/architecture.md) · [Agent Layer](docs/agent_layer.md) · [Risk Model](docs/risk_model.md) · [Spectral Indices](docs/spectral_indices.md) · [API Contract](docs/api_contract.md) · [User Manual](docs/user_manual.md) · [Deployment](infrastructure/deployment.md)

</div>

> **Advisory only.** AquaLens does not certify water safety, detect toxins, or replace laboratory testing. It is a triage tool that tells field teams *where to sample first*.

---

## Table of contents

- [What AquaLens does](#what-aqualens-does)
- [How it works — two pipelines](#how-it-works--two-pipelines)
- [The five Gemini agents](#the-five-gemini-agents)
- [System architecture](#system-architecture)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [API surface](#api-surface)
- [Data model](#data-model)
- [Failure modes &amp; fallbacks](#failure-modes--fallbacks)
- [Tests &amp; quality gates](#tests--quality-gates)
- [Deployment](#deployment)
- [License](#license)

---

## What AquaLens does

A user picks an area of interest — by place-name search, decimal coordinates, or a map click. AquaLens buffers the point into a ~1&nbsp;km monitoring polygon, pulls a fresh Sentinel-2 scene, computes six water-quality spectral indices on the water mask, produces a deterministic risk score, and then hands the bundle to a multi-agent Gemini workflow that writes the human-facing narrative and a citizen-friendly summary card.

The **numbers** (indices, score, level, urgency) are deterministic, unit-tested, and reproducible. The **agent layer** can pick inputs and write prose — it can never move the risk band.

Every session is captured end-to-end:

- Spectral indices and the risk row land in Postgres.
- Each agent's tool calls, arguments, results, latency, and tokens land in `agent_traces` (JSONB).
- Cross-session notes the Historian distills land in `agent_memory` with text-embedding-004 vectors and a pgvector HNSW index, so future runs over the same water body recall semantically related context.

---

## How it works — two pipelines

```mermaid
flowchart LR
    subgraph P1[Pipeline 1 · Deterministic core]
        direction LR
        A[Pick area<br/>search · coords · map] --> B[Fetch Sentinel-2 L2A<br/>Planetary Computer STAC]
        B --> C[Compute 6 indices<br/>NDWI · MNDWI · NDTI<br/>NDCI · NDVI · WRI]
        C --> D[Risk score 0–100<br/>level · urgency]
    end

    subgraph P2[Pipeline 2 · Gemini agent workflow]
        direction LR
        E[Coordinator<br/>thinking mode] --> F[Scout<br/>function calling + Vision]
        E --> G[Historian<br/>search · memory · code exec]
        F --> H[Analyst<br/>draft → critique → rewrite]
        G --> H
        H --> I[Reporter<br/>citizen summary]
    end

    D --> E
    I --> J[Session detail + agent trace + branded PDF]

    classDef det fill:#0e3c2f,stroke:#34d399,color:#d1fae5,stroke-width:1.4px;
    classDef agent fill:#33205a,stroke:#a78bfa,color:#ede9fe,stroke-width:1.4px;
    classDef out fill:#1e293b,stroke:#94a3b8,color:#e2e8f0,stroke-width:1.4px;
    class A,B,C,D det;
    class E,F,G,H,I agent;
    class J out;
```

**Pipeline 1 is the trusted numeric core.** Pure-Python functions with deterministic numpy band math; the LLM has no influence over the risk number itself.

**Pipeline 2 is the agent layer.** Five specialist Gemini agents choose inputs, gather grounded context, draft the brief, and emit the citizen summary. They can degrade individually without taking the session down — every agent has a deterministic fallback.

---

## The five Gemini agents

| # | Agent | Action | Capability |
|---|-------|--------|------------|
| **1** | Coordinator | plans the workflow | Gemini thinking mode |
| **2** | Scout | picks the satellite scene | Function calling + Gemini Vision on the real RGB tile |
| **3** | Historian | pulls trends &amp; grounded context | History + Google Search grounding + URL Context + code execution + pgvector memory |
| **4** | Analyst | writes &amp; self-critiques the brief | Structured output + critique-then-rewrite loop |
| **5** | Reporter | writes the citizen summary | Structured response schema (deterministic fallback) |

Each agent run lands in the **Agentic Workflow** card on the session page with its tool calls, JSON outputs, latency, and token usage. The card has the same colour vocabulary as this README and the live PDF appendix:

- Coordinator — aqua · Scout — sky · Historian — amber · Analyst — violet · Reporter — emerald

Deep dive: [`docs/agent_layer.md`](docs/agent_layer.md).

---

## System architecture

```mermaid
flowchart TB
    subgraph Client[Browser]
        direction TB
        UI[Next.js 15 app router<br/>Tailwind 4 · TS strict]
        TRACE[Agentic Workflow card<br/>live SWR polling]
        PDFBTN[Download PDF]
    end

    subgraph Backend[FastAPI 0.115 · SQLModel · Alembic]
        direction TB
        API[/api/v1 router/]
        PIPE[Pipeline 1<br/>deterministic core]
        ORCH[Pipeline 2 orchestrator<br/>Coordinator → Scout → Historian → Analyst → Reporter]
        REPORT[WeasyPrint + Jinja2<br/>branded PDF]
    end

    subgraph Data[Persistence]
        PG[(PostgreSQL 16 + PostGIS<br/>monitoring_sessions · water_bodies<br/>spectral_indices · risk_assessments)]
        TR[(agent_traces<br/>JSONB tool-call log)]
        MEM[(agent_memory<br/>pgvector 768 · HNSW cosine)]
        DISK[/uploads + reports on disk/]
    end

    subgraph External[External providers]
        STAC[Microsoft Planetary Computer<br/>Sentinel-2 L2A STAC]
        GEMINI[Gemini API<br/>2.5 Flash · embeddings]
    end

    UI --> API
    TRACE --> API
    PDFBTN --> API
    API --> PIPE
    PIPE --> ORCH
    PIPE --> PG
    ORCH --> TR
    ORCH --> MEM
    PIPE --> STAC
    ORCH --> GEMINI
    API --> REPORT
    REPORT --> DISK

    classDef client fill:#0f172a,stroke:#38bdf8,color:#e0f2fe,stroke-width:1.3px;
    classDef backend fill:#0e3c2f,stroke:#34d399,color:#d1fae5,stroke-width:1.3px;
    classDef data fill:#1e1b4b,stroke:#a78bfa,color:#ede9fe,stroke-width:1.3px;
    classDef ext fill:#3a2a0c,stroke:#fbbf24,color:#fef3c7,stroke-width:1.3px;
    class UI,TRACE,PDFBTN client;
    class API,PIPE,ORCH,REPORT backend;
    class PG,TR,MEM,DISK data;
    class STAC,GEMINI ext;
```

---

## Session lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as Next.js frontend
    participant API as FastAPI /sessions
    participant PIPE as Deterministic core
    participant ORCH as Agent orchestrator
    participant GEM as Gemini
    participant DB as Postgres

    U->>FE: Pick AOI + window + cloud ceiling
    FE->>API: POST /sessions
    API->>DB: Insert session (status=processing)
    API-->>FE: 201 session
    API->>PIPE: BackgroundTask: run_full

    PIPE->>PIPE: STAC search · COG read · index math
    PIPE->>DB: Persist indices + risk row
    PIPE->>ORCH: run_orchestrator(...) when AOI is water
    ORCH->>GEM: Coordinator plan
    ORCH->>GEM: Scout (function calling + vision)
    opt history exists
        ORCH->>GEM: Historian (search · memory · code exec)
    end
    ORCH->>GEM: Analyst draft → critique → rewrite
    ORCH->>GEM: Reporter structured citizen summary
    ORCH->>DB: Persist agent_traces (incremental)
    PIPE->>DB: status=complete + risk.field_brief = reporter

    loop while status != complete
        FE->>API: GET /sessions/{id}
        API-->>FE: status_message + partial trace
    end
    FE->>API: GET /sessions/{id}/report
    API-->>FE: WeasyPrint PDF
```

---

## Repository layout

```text
aqualens/
├── assets/                  # Brand assets (animated SVG wordmark used in README + landing)
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI routers (sessions · evidence · water_bodies · report · health)
│   │   ├── core/            # config · logging · database · BackgroundTask runner
│   │   ├── models/          # SQLModel tables (sessions · water_bodies · risk · indices · agent_traces · agent_memory · evidence · report)
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── pipeline.py          # Deterministic core (Pipeline 1)
│   │   │   ├── indices.py · risk_model.py · reasoning.py
│   │   │   ├── citizen_summary.py   # Deterministic citizen summary fallback
│   │   │   ├── report_generator.py  # Jinja2 + WeasyPrint
│   │   │   └── agent/               # Pipeline 2 — orchestrator + 5 agents + tool layer
│   │   │       ├── orchestrator.py  # Coordinator → Scout → Historian → Analyst → Reporter
│   │   │       ├── coordinator (prompts/coordinator.json)
│   │   │       ├── scout.py · historian.py · analyst.py · reporter.py · field_liaison.py (legacy)
│   │   │       ├── gemini_runtime.py  # Shared runtime: tool loop · structured calls · key rollover
│   │   │       ├── trace.py           # Per-session trace recorder
│   │   │       └── tools/             # STAC · memory · history tool implementations
│   │   ├── utils/           # Geo · charts · location formatting · PDF helpers
│   │   └── main.py
│   ├── alembic/             # Database migrations (initial · aoi_type · agent_memory · agent_layer)
│   └── tests/               # 90+ pytest tests covering pipeline, agents, PDFs, API, citizen summary
├── frontend/
│   ├── app/
│   │   ├── (marketing)/     # Landing · methodology · about · changelog · limitations
│   │   └── (app)/           # Dashboard · monitor · sessions · water-bodies · settings
│   ├── components/
│   │   ├── marketing/       # Hero · Workflow · AgentConstellation · CTA · Citations · IndicesShowcase
│   │   ├── session/         # AgentTraceCard · AnalysisSummaryCard · IndexGrid · RiskCard · ProcessingSkeleton
│   │   ├── map/             # MapLibre wrapper · basemap switcher · search · mini-map
│   │   ├── evidence/        # Field evidence form + list
│   │   └── ui/              # Brand-tuned shadcn primitives
│   ├── lib/                 # api-client · api-types · query-client · seo · location · env
│   └── tests/               # Vitest unit tests + Playwright E2E
├── docs/                    # Architecture · agent_layer · risk_model · spectral_indices · api_contract · user_manual · prd
├── infrastructure/          # render.yaml · vercel.json · deployment.md
├── docker-compose.yml
└── README.md
```

---

## Quick start

### 1. Environment

```bash
cp .env.example .env
```

Minimum required values:

| Variable | Notes |
|---|---|
| `DATABASE_URL` | Postgres connection string. `postgres://user:pass@host:5432/aqualens` |
| `GOOGLE_API_KEY` | Gemini 2.5 Flash + embeddings. Free tier works for demos. |
| `NEXT_PUBLIC_API_URL` | Origin the frontend should hit. `http://localhost:8000` in dev. |

Optional but recommended:

| Variable | Notes |
|---|---|
| `GOOGLE_API_KEY_FALLBACK` · `GOOGLE_API_KEY_FALLBACK_2` | Extra keys the runtime rolls over to on quota / 429. |
| `AQUALENS_AGENTIC_MODE` | `true` (default). Set `false` to skip Pipeline 2 entirely. |
| `AQUALENS_FAKE_GEMINI` | `1` for deterministic offline mode (CI / no-network demos). |

### 2. Run with Docker

```bash
docker compose up --build
```

Frontend at <http://localhost:3000>, backend at <http://localhost:8000>, Postgres + PostGIS as a sidecar.

### 3. Run without Docker

**Backend** — Python 3.11+:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
```

**Frontend** — pnpm + Node 20+:

```bash
cd frontend
pnpm install
pnpm dev
```

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `AQUALENS_AGENTIC_MODE` | `true` | Enables the Coordinator → Scout → Historian → Analyst → Reporter orchestration. When off, only Pipeline 1 + the deterministic narrator run. |
| `AQUALENS_FAKE_GEMINI` | `0` | Skips real Gemini calls; uses the deterministic narrator and a canned citizen summary. Used by CI. |
| `AQUALENS_AGENT_STEP_DELAY_MS` | `0` | Optional delay between agent stages for visible live-sequencing in demos. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Runtime Gemini model ID. |
| `GEMINI_EMBED_MODEL` | `text-embedding-004` | Used by the Historian's pgvector memory. |
| `REPORT_DIR` | `backend/data/reports` | Where regenerated PDFs are cached on disk. |
| `MAX_UPLOAD_BYTES` | `8388608` (8 MB) | Field-evidence photo upload ceiling. |
| `WATER_FRACTION_LAND_THRESHOLD` | `0.2` | Below this, the AOI is classified as land; agents are skipped. |
| `WATER_FRACTION_MIXED_THRESHOLD` | `0.7` | Below this (and ≥ land), the AOI is classified as mixed. |

Full schema: [`backend/app/core/config.py`](backend/app/core/config.py).

---

## API surface

All endpoints are mounted under **`/api/v1`**. Full payload schemas in [`docs/api_contract.md`](docs/api_contract.md); the live OpenAPI document is at `/docs` when the backend is running.

### Water bodies

| Verb | Path | Notes |
|---|---|---|
| `GET` | `/water-bodies` | List saved AOIs. |
| `POST` | `/water-bodies` | Create from a GeoJSON polygon or a buffered point. |
| `GET` | `/water-bodies/{id}` | Single AOI with centroid + area. |
| `PATCH` | `/water-bodies/{id}` | Rename / re-describe. |
| `DELETE` | `/water-bodies/{id}` | Cascade-deletes child sessions. |
| `POST` | `/water-bodies/bulk-delete` | Transactional multi-select delete. |

### Sessions

| Verb | Path | Notes |
|---|---|---|
| `POST` | `/sessions` | Kick off a new monitoring run. Returns immediately; pipeline runs in the background. |
| `GET` | `/sessions` | Paginated list, optionally filtered by `water_body_id`. |
| `GET` | `/sessions/{id}` | Full detail (status, indices, risk, citizen summary, evidence). |
| `GET` | `/sessions/{id}/indices` | The six computed indices with provenance. |
| `GET` | `/sessions/{id}/risk` | The risk row (level, urgency, recommendation, reasoning, limitations). |
| `POST` `GET` | `/sessions/{id}/evidence` | Submit / list field-evidence rows (re-scores the session). |
| `GET` | `/sessions/{id}/trace` | Multi-agent execution trace (404 when the agent layer was off). |
| `GET` | `/sessions/{id}/field-brief` | Legacy compatibility endpoint (404 when absent). |
| `GET` | `/sessions/{id}/report` | WeasyPrint PDF, re-rendered on every request so template fixes ship instantly. Downloads as `aqualens-analysis-YYYYMMDD.pdf`. |

### System

| Verb | Path | Notes |
|---|---|---|
| `GET` | `/health` | Liveness probe. Returns `{"status":"ok"}`. |

---

## Data model

```mermaid
erDiagram
    WATER_BODIES ||--o{ MONITORING_SESSIONS : has
    MONITORING_SESSIONS ||--o{ SPECTRAL_INDICES : produces
    MONITORING_SESSIONS ||--o| RISK_ASSESSMENTS : has
    MONITORING_SESSIONS ||--o{ FIELD_EVIDENCE : has
    MONITORING_SESSIONS ||--o| REPORTS : has
    MONITORING_SESSIONS ||--o| AGENT_TRACES : has
    WATER_BODIES ||--o{ AGENT_MEMORY : remembers
    RISK_ASSESSMENTS ||--o| AGENT_TRACES : linked_to

    WATER_BODIES {
        UUID id PK
        string name
        geometry polygon
        point centroid
        float area_km2
        string source
    }
    MONITORING_SESSIONS {
        UUID id PK
        UUID water_body_id FK
        date start_date
        date end_date
        float max_cloud_cover
        string status
        string status_message
        string scene_id
        datetime scene_capture_date
        float scene_cloud_cover
        float water_fraction
        string aoi_type
    }
    SPECTRAL_INDICES {
        UUID id PK
        UUID session_id FK
        string name
        float value
        float min_value
        float max_value
        float stddev
        int sample_count
        json bands
        string interpretation
    }
    RISK_ASSESSMENTS {
        UUID id PK
        UUID session_id FK
        UUID agent_trace_id FK
        float score
        string level
        string urgency
        string recommendation
        string reasoning
        string limitations
        json contributors
        json field_brief
        string model_id
    }
    AGENT_TRACES {
        UUID id PK
        UUID session_id FK
        json coordinator_plan
        json agent_runs
        int total_tokens_in
        int total_tokens_out
        int total_latency_ms
        string gemini_model
    }
    AGENT_MEMORY {
        UUID id PK
        UUID water_body_id FK
        string note
        vector embedding
        datetime created_at
        bool archived
    }
    FIELD_EVIDENCE {
        UUID id PK
        UUID session_id FK
        string water_color
        string odor
        bool algae_present
        int dead_fish_count
        float rainfall_mm
        int complaints_count
        string photo_path
        string notes
    }
    REPORTS {
        UUID id PK
        UUID session_id FK
        string file_path
        int byte_size
    }
```

Migrations live in `backend/alembic/versions/` and are applied via `alembic upgrade head`.

---

## Failure modes &amp; fallbacks

Every layer has a deterministic safety net so a session always produces a usable brief:

| Failure | Fallback |
|---|---|
| Gemini primary key 429 / quota | Roll over to `GOOGLE_API_KEY_FALLBACK[_2]`. |
| Coordinator parse error | Baseline plan: Scout + Analyst + Reporter (Historian when history exists). |
| Scout vision timeout | Use freshest STAC candidate under the cloud-cover ceiling. |
| Historian failure | Analyst runs without the briefing; memory write is skipped. |
| Analyst failure | Deterministic narrator from `app.services.reasoning._fake_bundle`. |
| Reporter failure | Deterministic citizen summary from `app.services.citizen_summary`. |
| AOI classified as land or mixed | Pipeline 2 is skipped entirely (no Gemini cost); UI shows a *Not water* badge and the citizen summary explains why. |
| WeasyPrint render error | API returns 500 with the original message; cached PDFs are never served stale because regeneration happens on every download. |

All failures are recorded in the per-session trace — degraded behaviour is never silent.

---

## Tests &amp; quality gates

```bash
# Backend
cd backend
.venv/bin/python -m pytest -q            # ~90 tests in <10s on SQLite
.venv/bin/ruff check . && .venv/bin/black --check app/ tests/ alembic/

# Frontend
cd frontend
pnpm typecheck      # tsc --noEmit (strict)
pnpm lint           # next lint
pnpm test           # vitest unit tests
pnpm e2e            # Playwright against the compose stack
```

CI runs every gate plus the WeasyPrint smoke test on each PR.

---

## Deployment

| Surface | Provider | Notes |
|---|---|---|
| Backend | Render (Docker) | Blueprint in [`infrastructure/render.yaml`](infrastructure/render.yaml). |
| Frontend | Vercel | Config in [`infrastructure/vercel.json`](infrastructure/vercel.json). |
| Database | Postgres 16 + PostGIS + pgvector | Pinned in `docker-compose.yml` for local; managed Postgres in production. |

Walkthrough: [`infrastructure/deployment.md`](infrastructure/deployment.md).

---

## License

Source code and documentation are licensed under [MIT](LICENSE). Third-party notices in [NOTICE.md](NOTICE.md).

Sentinel-2 imagery © European Union, contains modified Copernicus Sentinel data accessed via the Microsoft Planetary Computer.

---

## Author

**Talha Abid** — GitHub [@talhaabidj](https://github.com/talhaabidj)
