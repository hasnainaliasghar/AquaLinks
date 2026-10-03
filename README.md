<div align="center">

<a href="https://github.com/hasnainaliasghar/AquaLinks">
  <img src="assets/logo-animated.svg" width="720" alt="AquaLinks — autonomous freshwater monitoring" />
</a>

AquaLinks monitors freshwater for the OneAquaHealth Global Hackathon. It connects a deterministic remote-sensing core to a traceable Groq agent workflow.

[![License: MIT](https://img.shields.io/badge/license-MIT-facc15.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab.svg)](https://python.org)
[![Next.js 15](https://img.shields.io/badge/next.js-15-000000.svg)](https://nextjs.org)
[![FastAPI 0.115](https://img.shields.io/badge/fastapi-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL 16 + PostGIS](https://img.shields.io/badge/postgres-16%20%2B%20postgis-336791.svg)](https://postgis.net)
[![Groq](https://img.shields.io/badge/llm-groq-f55036.svg)](https://console.groq.com)

[Architecture](docs/architecture.md) · [Agent Layer](docs/agent_layer.md) · [Risk Model](docs/risk_model.md) · [Spectral Indices](docs/spectral_indices.md) · [API Contract](docs/api_contract.md) · [User Manual](docs/user_manual.md) · [Deployment](DEPLOY.md)

</div>

> Advisory notice. AquaLinks does not certify water safety, detect toxins, or replace laboratory testing. It is a triage tool that tells citizen scientists and field teams where to look first.

---

## Table of contents

- [What AquaLinks does](#what-aqualinks-does)
- [Why it fits OneAquaHealth](#why-it-fits-oneaquahealth)
- [How it works: two linked pipelines](#how-it-works-two-linked-pipelines)
- [The five agents](#the-five-agents)
- [Risk model](#risk-model)
- [System architecture](#system-architecture)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [API surface](#api-surface)
- [Data model](#data-model)
- [Failure modes and fallbacks](#failure-modes-and-fallbacks)
- [Known limitations](#known-limitations)
- [Tests and quality gates](#tests-and-quality-gates)
- [Deployment](#deployment)
- [License and attribution](#license-and-attribution)

---

## What AquaLinks does

You select an area of interest with a place search, decimal coordinates, or a map click. For a map click, AquaLinks builds a square polygon of about 1 km around the point. It downloads a recent low-cloud Sentinel-2 scene from the Microsoft Planetary Computer and computes six spectral indices over the water mask. Then it calculates a deterministic risk score. If the area is mostly water, the system sends the results to a multi-agent workflow that runs on Groq. The agents write the analysis and a citizen summary.

The spectral indices, risk score, level, and urgency are deterministic, unit-tested, and reproducible. The agent layer writes prose and gathers context, but it cannot change the risk band. AI supports the assessment. It does not replace the measurement.

The system stores all session data:

- Postgres stores the spectral indices and the risk row.
- The `agent_traces` table (`JSONB`) stores the plan, tool calls, outputs, latency, and token usage for each agent run.
- The `agent_memory` table stores short notes from the Historian agent for each water body. Later sessions over the same water body read these notes back.

---

## Why it fits OneAquaHealth

AquaLinks supports three tracks in the IEEE OneAquaHealth Global Hackathon:

| Track | How AquaLinks addresses the track |
|---|---|
| AI-Supported Assessment | Computes a deterministic score first. AI agents explain the context. Stores full trace data. Re-scores a session when field evidence arrives. |
| Data-to-Insight | Shows a dashboard, trend context from past sessions, and plain-language summaries from the Historian and Reporter agents. |
| Resilience Informatics | Assigns an urgency band (routine, elevated, immediate) to every session to support early warning. |

---

## How it works: two linked pipelines

```mermaid
flowchart LR
    subgraph P1[Pipeline 1 · Deterministic core]
        direction LR
        A[Pick area<br/>search · coords · map] --> B[Fetch Sentinel-2 L2A<br/>Planetary Computer STAC]
        B --> C[Compute 6 indices<br/>NDWI · MNDWI · NDTI<br/>NDCI · NDVI · WRI]
        C --> D[Risk score 0–1<br/>level · urgency]
    end

    subgraph P2[Pipeline 2 · Groq agent workflow]
        direction LR
        E[Coordinator<br/>plans the run] --> F[Scout<br/>place name lookup]
        E --> G[Historian<br/>history · memory · web search]
        F --> H[Analyst<br/>draft → critique → rewrite]
        G --> H
        H --> I[Reporter<br/>citizen summary]
    end

    D --> E
    I --> J[Session detail + agent trace + branded PDF]
```

- Pipeline 1 is the numeric core. Pure Python functions compute deterministic numpy band math. The language model cannot change the risk number.
- Pipeline 2 is the agent layer. Five agents plan the run, gather context, draft and critique the report, and write the citizen summary. If one agent fails, the session continues with a deterministic fallback.
- Pipeline 2 runs only when the area of interest is classified as water. The system skips it for land and mixed areas to save tokens.

---

## The five agents

All agents call Groq through one shared runtime (`backend/app/services/agent/gemini_runtime.py`). The file name is a leftover from an earlier version. The runtime handles tool loops, JSON-schema outputs, retries on rate limits, and trace recording.

| # | Agent | What it does | How |
|---|---|---|---|
| 1 | Coordinator | Plans which agents run and sets a budget for each | One structured JSON call |
| 2 | Scout | Resolves a readable place name when the water body name is weak, such as bare coordinates | One structured JSON call from the model's own knowledge, with no tools. The deterministic pipeline chooses the scene. |
| 3 | Historian | Builds a context briefing from past sessions and the web | Database tools, linear trend slope per metric, persistent memory notes, web search (Tavily when a key is set, otherwise DuckDuckGo) |
| 4 | Analyst | Writes the recommendation, reasoning, and limitations | Draft, then critique, then at most one rewrite |
| 5 | Reporter | Writes the citizen summary card | Structured JSON output with a deterministic fallback |

The Historian runs only when the water body has at least one earlier session. The Agentic Workflow card on the session page shows each run with its tool calls, JSON output, latency, and token usage. For more details, read [`docs/agent_layer.md`](docs/agent_layer.md).

---

## Risk model

The score is a weighted sum of normalized index values. It is stored as a number from 0 to 1 and shown in the UI as a percentage.

| Factor | Weight | Meaning |
|---|---|---|
| NDCI | 0.40 | Chlorophyll signal (bloom risk) |
| NDTI | 0.25 | Turbidity |
| NDWI floor | 0.15 | Low value means a weak water signal |
| NDVI | 0.10 | Floating biomass or shoreline encroachment |
| MNDWI floor | 0.10 | Low value means a weak water signal |

Field evidence (algae, water color, odor, dead fish, complaints, rainfall) adds a bonus of at most 0.5. The final score maps to a level: low below 0.33, medium below 0.66, and high above that. Level and evidence together set the urgency: routine, elevated, or immediate. For the full model, read [`docs/risk_model.md`](docs/risk_model.md).

The system classifies each area by water fraction: 0.50 or more is water, 0.20 to 0.50 is mixed, and below 0.20 is land. These thresholds are constants in `backend/app/services/pipeline.py`.

---

## System architecture

```mermaid
flowchart TB
    subgraph Client[Browser]
        UI[Next.js 15 app router<br/>Tailwind · TS strict · MapLibre]
        TRACE[Agentic Workflow card<br/>live polling]
        PDFBTN[Download PDF]
    end

    subgraph Backend[FastAPI 0.115 · SQLModel · Alembic]
        API[/api/v1 router/]
        PIPE[Pipeline 1<br/>deterministic core]
        ORCH[Pipeline 2 orchestrator]
        REPORT[WeasyPrint + Jinja2<br/>branded PDF]
    end

    subgraph Data[Persistence]
        PG[(PostgreSQL 16 + PostGIS)]
        TR[(agent_traces JSONB)]
        MEM[(agent_memory · pgvector)]
        DISK[/uploads + reports on disk/]
    end

    subgraph External[External providers]
        STAC[Microsoft Planetary Computer<br/>Sentinel-2 L2A STAC]
        GROQ[Groq API<br/>chat completions]
        WEB[Tavily or DuckDuckGo<br/>web search]
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
    ORCH --> GROQ
    ORCH --> WEB
    API --> REPORT
    REPORT --> DISK
```

---

## Repository layout

```
AquaLinks/
├── assets/                  # Logo (animated SVG)
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # sessions · evidence · water_bodies · report · health
│   │   ├── core/              # config · logging · database · background tasks
│   │   ├── models/            # SQLModel tables
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── pipeline.py        # Deterministic core (Pipeline 1)
│   │   │   ├── indices.py · risk_model.py · reasoning.py
│   │   │   ├── citizen_summary.py · report_generator.py
│   │   │   ├── satellite/         # Planetary Computer provider + offline sample provider
│   │   │   └── agent/             # Pipeline 2: orchestrator, agents, prompts, tools
│   │   └── utils/
│   ├── alembic/             # Database migrations (0001 to 0003)
│   ├── tests/               # pytest suite
│   ├── Dockerfile
│   └── railway.toml
├── frontend/
│   ├── app/                 # (marketing) pages and (app) dashboard, monitor, sessions, water bodies
│   ├── components/
│   ├── hooks/ · lib/
│   └── tests/               # Vitest unit tests + Playwright E2E
├── docs/                    # Architecture · agent layer · risk model · API contract · user manual
├── infrastructure/          # Deployment config files
├── scripts/                 # run-backend.sh · run-frontend.sh · run-docker.sh
├── DEPLOY.md                # Step-by-step deployment guide
├── docker-compose.yml
└── .env.example
```

---

## Quick start

### 1. Environment

```bash
cp .env.example .env
```

Set these values in `.env`:

| Variable | Notes |
|---|---|
| `GROQ_API_KEY` | Groq API key from [console.groq.com](https://console.groq.com). Required for the agent layer. |
| `DATABASE_URL` | Postgres connection string, such as `postgresql+psycopg://aqualens:aqualens@localhost:5432/aqualens`. If you leave it unset, the backend uses a local SQLite file. |
| `NEXT_PUBLIC_API_URL` | Backend URL for the frontend, such as `http://localhost:8000` in development |

Optional values:

| Variable | Notes |
|---|---|
| `TAVILY_API_KEY` | Better web search for the Historian. Without it, the Historian uses DuckDuckGo. |
| `AQUALENS_AGENTIC_MODE` | `true` by default. Set to `false` to skip Pipeline 2. |
| `AQUALENS_FAKE_GEMINI` | Set to `1` to skip real LLM calls and use the deterministic narrator. Used in CI. |
| `AQUALENS_USE_SAMPLE_PROVIDER` | Set to `1` to use built-in sample imagery instead of the network. |

### 2. Run with Docker

```bash
docker compose up --build
```

The command starts the frontend at `http://localhost:3000`, the backend at `http://localhost:8000`, and Postgres with PostGIS. Docker Compose reads `GROQ_API_KEY` from your shell or from `.env`. The first build installs GDAL and WeasyPrint libraries and can take several minutes.

### 3. Run without Docker

Run the backend with Python 3.11 or newer:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
```

Run the frontend with pnpm and Node 20 or newer:

```bash
cd frontend
pnpm install
pnpm dev
```

When the backend runs, open `http://localhost:8000/docs` for interactive API documentation.

---

## Configuration

The backend reads these variables through `backend/app/core/config.py`.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./aqualens.db` | SQLAlchemy connection URL |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000` | Comma-separated origins allowed to call the API |
| `GROQ_API_KEY` | none | Primary Groq key |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Model for all agents |
| `GROQ_VISION_MODEL` | `openai/gpt-oss-120b` | Model for the thumbnail vision tool (not called in a normal run) |
| `GROQ_QUOTA_RETRY_PASSES` | `2` | Retry passes before giving up on a rate-limited request |
| `GROQ_QUOTA_COOLDOWN_SECONDS` | `8` | Wait before retrying a key that hit its quota |
| `TAVILY_API_KEY` | none | Optional web search key for the Historian |
| `PC_STAC_URL` | Planetary Computer STAC URL | Satellite catalog endpoint |
| `DEFAULT_LOOKBACK_DAYS` | `30` | Default imagery window |
| `MAX_CLOUD_COVER` | `30` | Default cloud-cover ceiling in percent |
| `UPLOAD_DIR` | `data/uploads` | Field evidence photos |
| `REPORT_DIR` | `data/reports` | Cached PDF reports |
| `AQUALENS_AGENTIC_MODE` | `true` | Enables the five-agent workflow |
| `AQUALENS_AGENT_STEP_DELAY_MS` | `0` | Optional pause between agents for demos |
| `AQUALENS_FAKE_GEMINI` | `0` | Skips real LLM calls |
| `AQUALENS_USE_SAMPLE_PROVIDER` | `0` | Uses sample imagery instead of Planetary Computer |

The frontend reads `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_SITE_URL`. It also reads the optional `NEXT_PUBLIC_CARTO_API_KEY`, which it appends to CARTO basemap tile requests when set.

---

## API surface

The backend mounts all endpoints under `/api/v1`. To view full schemas, read [`docs/api_contract.md`](docs/api_contract.md).

| Area | Endpoints |
|---|---|
| Water bodies | `GET/POST /water-bodies`, `GET/PATCH/DELETE /water-bodies/{id}`, `POST /water-bodies/bulk-delete` |
| Sessions | `POST /sessions`, `GET /sessions`, `GET /sessions/{id}`, `GET /sessions/{id}/indices`, `GET /sessions/{id}/risk`, `GET /sessions/{id}/trace`, `GET /sessions/{id}/field-brief` (legacy) |
| Evidence | `POST/GET /sessions/{id}/evidence` (a new submission queues a re-score) |
| Report | `GET /sessions/{id}/report` (PDF) |
| System | `GET /health` |

`POST /sessions` returns immediately with a pending session. The pipeline runs as a background task, and the frontend polls `GET /sessions/{id}` for status.

---

## Data model

The database contains these tables: `water_bodies`, `monitoring_sessions`, `spectral_indices`, `risk_assessments`, `field_evidence`, `agent_traces`, `agent_memory`, and `reports`.

The migrations in `backend/alembic/versions/` enable PostGIS when available. They also try to enable pgvector and, if it is present, add a vector mirror column with an HNSW index. Memory embeddings are always stored in a JSON column, and recall computes cosine similarity in Python. Without the extensions the schema falls back to JSON columns, so it also works on SQLite for local runs and tests. To view the entity descriptions, read [`docs/architecture.md`](docs/architecture.md). Apply migrations with `alembic upgrade head`.

---

## Failure modes and fallbacks

Each layer includes a deterministic fallback so every session produces a usable result:

| Failure | Fallback |
|---|---|
| Groq key hits a rate limit | Waits for the cooldown, then retries |
| Coordinator error | Uses a baseline plan |
| Historian error | Analyst runs without historical context |
| Analyst error | Uses the deterministic narrator from `reasoning.py` |
| Reporter error | Uses the deterministic citizen summary |
| Area is land or mixed | Skips Pipeline 2 and shows a "Not water" badge |
| No Groq key configured | Agent calls fail and the system falls back to deterministic output |
| Report not ready | `GET /sessions/{id}/report` returns 404 until indices and the risk row exist. The PDF is re-rendered on every request and sent with `no-store`. |

The system records agent failures in the session trace.

---

## Known limitations

- Memory recall uses a deterministic hash-based pseudo-embedding because Groq has no embeddings API. Similarity scores are therefore not semantically meaningful yet.
- Groq has no native search grounding or code execution. The Historian uses web search through Tavily or DuckDuckGo, and it computes trends with a linear regression slope.
- The Scout currently resolves place names only. The scene-picking loop with STAC and vision tools exists in `scout.py`, but the orchestrator does not call it, so `GROQ_VISION_MODEL` is unused in a normal run.
- The model name `gemini_model` still appears in some API fields and the trace UI. It holds the Groq model ID.

---

## Tests and quality gates

```bash
# Backend
cd backend
pytest -q
ruff check . && black --check .

# Frontend
cd frontend
pnpm typecheck
pnpm lint
pnpm stylelint
pnpm test
pnpm e2e
```

The backend has about 100 tests. GitHub Actions runs backend lint and tests, frontend typecheck, lint, tests, and build, and a Playwright end-to-end job. The end-to-end job uses the sample imagery provider and the fake LLM mode, so it needs no network or API key.

---

## Deployment

| Surface | Provider | Notes |
|---|---|---|
| Backend | Railway (Docker) | Config in `backend/railway.toml` |
| Frontend | Vercel | Config in `frontend/vercel.json` |
| Database | Supabase Postgres | Enable the `postgis` extension. The `vector` extension is optional. |

For step-by-step instructions, read [`DEPLOY.md`](DEPLOY.md).

---

## Roadmap ideas

- Add a forecasting layer to the urgency score for early warnings (Track 6).
- Export session risk data in FHIR format for public-health systems (Track 7).
- Add engagement features for citizen contributors (Track 5).
- Replace the pseudo-embeddings with a real embeddings endpoint.

---

## License and attribution

Source code and documentation are licensed under [MIT](LICENSE). Copyright (c) 2026 Hasnain Ali Asghar.
