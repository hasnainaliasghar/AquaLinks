<div align="center">

<a href="https://github.com/hasnainaliasghar/AquaLinks">
  <img src="assets/logo-animated.svg" width="720" alt="AquaLinks — autonomous freshwater monitoring" />
</a>

AquaLinks monitors freshwater for the OneAquaHealth Global Hackathon. It connects a deterministic remote-sensing core to a traceable Gemini agent workflow.

[![License: MIT](https://img.shields.io/badge/license-MIT-facc15.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab.svg)](https://python.org)
[![Next.js 15](https://img.shields.io/badge/next.js-15-000000.svg)](https://nextjs.org)
[![FastAPI 0.115](https://img.shields.io/badge/fastapi-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL 16 + PostGIS](https://img.shields.io/badge/postgres-16%20%2B%20postgis-336791.svg)](https://postgis.net)
[![Gemini 2.5 Flash](https://img.shields.io/badge/gemini-2.5%20flash-4285f4.svg)](https://ai.google.dev/gemini-api/docs)

[Architecture](docs/architecture.md) · [Agent Layer](docs/agent_layer.md) · [Risk Model](docs/risk_model.md) · [Spectral Indices](docs/spectral_indices.md) · [API Contract](docs/api_contract.md) · [User Manual](docs/user_manual.md) · [Deployment](infrastructure/deployment.md)

</div>

> Advisory notice. AquaLinks does not certify water safety, detect toxins, or replace laboratory testing. It is a triage tool that tells citizen scientists and field teams where to look first.

---

## Table of contents

- [What AquaLinks does](#what-aqualinks-does)
- [Why it fits OneAquaHealth](#why-it-fits-oneaquahealth)
- [How it works: two linked pipelines](#how-it-works-two-linked-pipelines)
- [The five Gemini agents](#the-five-gemini-agents)
- [System architecture](#system-architecture)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [API surface](#api-surface)
- [Data model](#data-model)
- [Failure modes and fallbacks](#failure-modes-and-fallbacks)
- [Tests and quality gates](#tests-and-quality-gates)
- [Deployment](#deployment)
- [License and attribution](#license-and-attribution)

---

## What AquaLinks does

You select an area of interest with a location search, decimal coordinates, or a map click. AquaLinks creates a 1 km polygon around the point. It downloads the newest Sentinel-2 satellite image and computes six spectral indices over the water mask. Then, it calculates a deterministic risk score. The system sends that score to a Gemini agent workflow that writes the analysis and a citizen summary.

The spectral indices, risk score, level, and urgency are deterministic, unit-tested, and reproducible. The agent layer chooses inputs and writes prose, but it cannot change the risk band. AI supports the assessment, but it does not replace the measurement.

The system stores all session data:

- Postgres stores spectral indices and the risk score.
- The `agent_traces` table (`JSONB`) stores tool calls, arguments, results, latency, and token usage for each agent.
- The `agent_memory` table stores vector embeddings of notes from the Historian agent. Later runs over the same water body automatically recall this context.

---

## Why it fits OneAquaHealth

AquaLinks supports three tracks in the IEEE OneAquaHealth Global Hackathon:

| Track | How AquaLinks addresses the track |
|---|---|
| AI-Supported Assessment | Computes a deterministic score first. AI agents explain the context. Stores full trace data. Supports re-scoring with field evidence. |
| Data-to-Insight | Generates dashboards, trend context, and risk summaries with the Historian and Reporter agents. |
| Resilience Informatics | Computes urgency scores for each session to build early warnings. |

---

## How it works: two linked pipelines

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
```

- Pipeline 1 is the numeric core. Pure Python functions compute deterministic numpy band math. The language model cannot change the risk number.
- Pipeline 2 is the agent layer. Five Gemini agents select inputs, gather context, draft the report, and create the citizen summary. If one agent fails, the session continues with a fallback.

---

## The five Gemini agents

| # | Agent | Action | Capability |
|---|---|---|---|
| 1 | Coordinator | Plans the workflow | Gemini thinking mode |
| 2 | Scout | Picks the satellite scene | Function calling + Gemini Vision on the RGB tile |
| 3 | Historian | Pulls trends and grounded context | Search grounding + URL context + code execution + pgvector memory |
| 4 | Analyst | Writes and self-critiques the brief | Structured output + critique-then-rewrite loop |
| 5 | Reporter | Writes the citizen summary | Structured response schema with a deterministic fallback |

The Agentic Workflow card on the session page displays each agent run. It shows tool calls, JSON output, latency, and token usage. For more details, read [`docs/agent_layer.md`](docs/agent_layer.md).

---

## System architecture

```mermaid
flowchart TB
    subgraph Client[Browser]
        UI[Next.js 15 app router<br/>Tailwind 4 · TS strict]
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
```

---

## Repository layout

```
AquaLinks/
├── assets/                  # Brand assets (logo, wordmark)
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI routers
│   │   ├── core/            # config · logging · database
│   │   ├── models/          # SQLModel tables
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── pipeline.py  # Deterministic core (Pipeline 1)
│   │   │   ├── indices.py · risk_model.py · reasoning.py
│   │   │   ├── citizen_summary.py
│   │   │   ├── report_generator.py
│   │   │   └── agent/       # Pipeline 2 — orchestrator + 5 agents
│   │   ├── utils/
│   │   └── main.py
│   ├── alembic/             # Database migrations
│   └── tests/               # pytest suite
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── tests/
├── docs/                    # Architecture · agent layer · risk model · API contract · user manual
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

Set these required environment variables in `.env`:

| Variable | Notes |
|---|---|
| `DATABASE_URL` | Postgres connection string, such as `postgres://user:pass@host:5432/aqualinks` |
| `GOOGLE_API_KEY` | Key for Gemini 2.5 Flash and embeddings |
| `NEXT_PUBLIC_API_URL` | Backend URL for the frontend, such as `http://localhost:8000` in development |

Optional environment variables:

| Variable | Notes |
|---|---|
| `GOOGLE_API_KEY_FALLBACK` / `GOOGLE_API_KEY_FALLBACK_2` | Backup API keys for quota limits |
| `AQUALINKS_AGENTIC_MODE` | Set to `true` by default. Set to `false` to disable Pipeline 2. |
| `AQUALINKS_FAKE_GEMINI` | Set to `1` for offline mode in CI and local testing |

### 2. Run with Docker

```bash
docker compose up --build
```

The command starts the frontend at `http://localhost:3000`, the backend at `http://localhost:8000`, and Postgres with PostGIS.

If your machine has limited resources, the first build can take 10 to 20 minutes and requires 4 GB of free RAM. To run without Docker, read [`docs/user_manual.md`](docs/user_manual.md).

### 3. Run without Docker

Run the backend with Python 3.11+:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
```

Run the frontend with pnpm and Node 20+:

```bash
cd frontend
pnpm install
pnpm dev
```

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `AQUALINKS_AGENTIC_MODE` | `true` | Enables the Coordinator, Scout, Historian, Analyst, and Reporter orchestration |
| `AQUALINKS_FAKE_GEMINI` | `0` | Skips real Gemini calls; uses the deterministic narrator and canned citizen summary |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Runtime Gemini model ID |
| `GEMINI_EMBED_MODEL` | `text-embedding-004` | Used by the Historian's pgvector memory |
| `REPORT_DIR` | `backend/data/reports` | Directory where regenerated PDFs are cached on disk |
| `MAX_UPLOAD_BYTES` | `8388608` (8 MB) | Field evidence photo upload limit |
| `WATER_FRACTION_LAND_THRESHOLD` | `0.2` | Below this threshold, the AOI is classified as land and agents are skipped |
| `WATER_FRACTION_MIXED_THRESHOLD` | `0.7` | Below this threshold and above or equal to land, the AOI is classified as mixed |

For the full configuration schema, open `backend/app/core/config.py`.

---

## API surface

The backend mounts all endpoints under `/api/v1`. To view full schemas, read [`docs/api_contract.md`](docs/api_contract.md). When the backend runs, open `/docs` for interactive OpenAPI documentation.

- Water bodies: `GET/POST /water-bodies`, `GET/PATCH/DELETE /water-bodies/{id}`, `POST /water-bodies/bulk-delete`
- Sessions: `POST /sessions`, `GET /sessions`, `GET /sessions/{id}`, `GET /sessions/{id}/indices`, `GET /sessions/{id}/risk`, `POST/GET /sessions/{id}/evidence`, `GET /sessions/{id}/trace`, `GET /sessions/{id}/report`
- System: `GET /health`

---

## Data model

The database contains these core tables: `water_bodies`, `monitoring_sessions`, `spectral_indices`, `risk_assessments`, `field_evidence`, `agent_traces`, `agent_memory`, and `reports`.

To view the entity-relationship diagram and column descriptions, read [`docs/architecture.md`](docs/architecture.md). Database migrations live in `backend/alembic/versions/`. Apply them with `alembic upgrade head`.

---

## Failure modes and fallbacks

Each layer includes a deterministic fallback to ensure the session completes:

| Failure | Fallback |
|---|---|
| Gemini primary key 429 or quota limit | Switches to backup API key |
| Coordinator parse error | Uses baseline plan: Scout, Analyst, Reporter |
| Scout vision timeout | Selects the newest STAC scene under the cloud threshold |
| Historian failure | Analyst runs without historical context and skips memory write |
| Analyst failure | Uses deterministic narrator fallback |
| Reporter failure | Uses deterministic citizen summary fallback |
| AOI classified as land or mixed | Skips Pipeline 2 and displays "Not water" badge |
| PDF render error | API returns an error and does not serve stale cached files |

The system records all failures in the session trace.

---

## Tests and quality gates

```bash
# Backend
cd backend
.venv/bin/python -m pytest -q
.venv/bin/ruff check . && .venv/bin/black --check app/ tests/ alembic/

# Frontend
cd frontend
pnpm typecheck
pnpm lint
pnpm test
pnpm e2e
```

---

## Deployment

| Surface | Provider | Notes |
|---|---|---|
| Backend | Render (Docker) | Blueprint in `infrastructure/render.yaml` |
| Frontend | Vercel | Config in `infrastructure/vercel.json` |
| Database | Postgres 16 + PostGIS + pgvector | Pinned in `docker-compose.yml` for local; managed Postgres in production |

For deployment steps, read [`infrastructure/deployment.md`](infrastructure/deployment.md).

---

## Roadmap ideas

- Add a forecasting layer to the urgency score for early warnings (Track 6).
- Export session risk data in FHIR format for public-health systems (Track 7).
- Add engagement features for citizen contributors (Track 5).

---

## License and attribution

The source code and documentation use the [MIT License](LICENSE). Third-party notices live in `NOTICE.md`.

AquaLinks builds on the architecture of AquaLens, an open-source freshwater monitoring project by Talha Abid ([@talhaabidj](https://github.com/talhaabidj)). This project adapts AquaLens under its MIT license for the OneAquaHealth Global Hackathon.

Sentinel-2 imagery copyright European Union. It contains modified Copernicus Sentinel data accessed through Microsoft Planetary Computer.
