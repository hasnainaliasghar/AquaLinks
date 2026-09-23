# Agent layer

AquaLens v1.0.0 ships a multi-agent layer over its deterministic
numeric pipeline. The numbers (six spectral indices, the weighted
risk score, the urgency band) are unchanged and remain authoritative.
The agents only **choose the inputs** the deterministic core consumes
and **write the prose** that wraps the numbers — they cannot move the
risk band.

This document is the deep-dive companion to `docs/architecture.md`.
For an at-a-glance view see the README's "Agent layer" section.

---

## Why agents at all

Two reasons:

1. **More Gemini-native depth.** Function calling, multi-turn tool
   loops, multimodal vision, Google Search grounding, URL Context,
   code execution, long context, thinking mode, and embeddings are
   all wired in via dedicated agents — each one earning its keep with
   a job a single Gemini call could not do as well.
2. **Multi-session memory.** The Historian's `agent_memory` table
   persists distilled observations per water body. The next time we
   monitor the same lake, the Historian reads what we learned last
   time — the literal "manages multi-step tasks over time" criterion
   from the Agentic Workflows track.

Everything is feature-flagged behind `AQUALENS_AGENTIC_MODE`. The
deterministic single-call narrative path (`services/reasoning.py`)
remains as the fallback for `AQUALENS_FAKE_GEMINI=1` and CI.

---

## Topology

```
                ┌──────────────────────────────────────────┐
                │ Coordinator  (Gemini, thinkingConfig)    │
                │ plans which sub-agents run + budgets     │
                └─────────────────┬────────────────────────┘
                                  │
        ┌──────────────┬──────────┴──────────┬──────────────────┐
        ▼              ▼                     ▼                  ▼
  ┌──────────┐   ┌────────────┐        ┌──────────┐      ┌─────────────┐
  │ Scout    │   │ Historian  │        │ Analyst  │      │ Reporter    │
  │          │   │            │        │          │      │             │
  │ function │   │ function   │        │ function │      │ function    │
  │ calling  │   │ calling +  │        │ calling +│      │ calling +   │
  │ + Vision │   │ Search +   │        │ critique │      │ structured  │
  │          │   │ URL Ctx +  │        │ + rewrite│      │ schema      │
  │          │   │ Code Exec  │        │          │      │ + citations │
  └──────────┘   └────────────┘        └──────────┘      └─────────────┘
```

---

## Agent specs

### Coordinator
- **Gemini features:** thinking mode (`thinking_budget=2048`),
  structured output (`response_schema=CoordinatorPlan`).
- **Job:** picks the sub-agent execution plan and per-step budgets.
  The orchestrator then enforces the product invariant: Scout, Analyst,
  and Reporter always run for water AOIs; Historian runs when prior
  in-product history exists for that water body.
- **File:** `backend/app/services/agent/orchestrator.py`.

### Scout
- **Gemini features:** function calling (parallel-tool-call capable),
  multimodal vision.
- **Tools:**
  - `list_recent_scenes` — STAC search at Microsoft Planetary Computer.
  - `inspect_scene` — single-scene metadata lookup.
  - `look_at_thumbnail` — passes the actual RGB tile to Gemini Vision.
- **Self-correction:** when Vision sees haze the Scout re-queries with
  a tighter cloud bound before committing.
- **File:** `backend/app/services/agent/scout.py`.

### Historian
- **Gemini features:** function calling, Google Search grounding,
  URL Context, code execution, long context (1M tokens).
- **Python tools:** `get_session_history`, `compute_trend`,
  `recall_persistent_notes`, `semantic_recall_notes` (embeddings),
  `write_persistent_note` (memory write).
- **Gemini-native tools:** `google_search`, `url_context`,
  `code_execution`. The Historian uses code execution specifically
  to run Mann-Kendall trend-significance tests on the index time
  series when our naive slope is non-zero.
- **File:** `backend/app/services/agent/historian.py`.

### Analyst
- **Gemini features:** function calling, structured output, self-
  critique loop. Three Gemini calls maximum (draft → critique →
  optional rewrite).
- **Output:** a `ReasoningBundle` (same shape the deterministic
  narrator produces) plus `evidence_focus` consumed by Reporter.
- **File:** `backend/app/services/agent/analyst.py`.

### Reporter
- **Gemini features:** structured output (`response_schema=CitizenSummary`).
- **Output:** citizen-facing summary card fields (`tone`, `headline`,
  `bottom_line`, safety guidance, limitations, citations).
- **Deterministic fallback:** when Gemini errors the agent falls back
  to `app.services.citizen_summary.build_citizen_summary`, so the UI
  and PDF always have a stable public summary.
- **File:** `backend/app/services/agent/reporter.py`.

---

## Trace + memory

Two tables, both added in Alembic migration `0003_agent_layer`.

| Table | Purpose | Lifespan |
|---|---|---|
| `agent_traces` | One row per session. Stores the Coordinator's plan plus every sub-agent's tool calls, token usage, and latency as JSONB. | Per session. Powers the Agent Trace UI card and the PDF appendix. |
| `agent_memory` | Per-water-body distilled notes written by the Historian. Each row carries a 768-dim `text-embedding-004` vector so `semantic_recall_notes` can rank by similarity, not just recency. | Persistent across sessions. Soft-archived past 50 active notes per water body. |

Postgres deployments get a `pgvector(768)` mirror column plus an HNSW
index for fast cosine similarity. SQLite (used in tests) stores the
embedding as JSON and computes similarity in user-space — same code
path, just slower at scale.

---

## Failure handling

The pipeline must always produce a `RiskAssessment` row. The agent
layer is wrapped so any failure falls back gracefully:

| Failure | Fallback |
|---|---|
| Coordinator Gemini error | Default plan (Scout + Analyst + Reporter, with Historian included when prior history exists). |
| Historian failure | Skipped — Analyst runs without context. |
| Analyst failure | Deterministic narrative from `app.services.reasoning._fake_bundle`. |
| Reporter failure | Deterministic summary from `app.services.citizen_summary`. |
| Whole agent layer failure | Pipeline catches it and uses the single-call `reasoning.generate_reasoning()` path. |

All failures land in the trace as `agent.error` so the UI can show
them — degraded behaviour is visible, not silent.

---

## Tests

Each agent and the orchestrator are tested with a fake-Gemini
fixture that replaces `google.genai.types` at the `sys.modules`
seam, so the suite runs offline. Coverage:

- `tests/test_agent_runtime.py` — TraceRecorder + tool-loop runner.
- `tests/test_agent_tools.py` — STAC, history, memory, embeddings.
- `tests/test_agent_scout.py` — happy path + structured-output fallback.
- `tests/test_agent_historian.py` — DB tools + grounding citations
  surface into the trace.
- `tests/test_agent_analyst.py` — three paths (clean, rewrite,
  critique failure).
- `tests/test_citizen_summary.py` — reporter payload validation +
  deterministic tone guardrails.
- `tests/test_agent_orchestrator.py` — end-to-end agent run.

Backend test suite passes in CI (`pytest`), and style gates remain
enforced by `ruff` + `black`.

---

## Feature flag matrix

| `AQUALENS_AGENTIC_MODE` | `AQUALENS_FAKE_GEMINI` | API key set | Behaviour |
|---|---|---|---|
| true | false | yes | Full multi-agent flow; trace + reporter summary persisted. |
| true | true | * | Deterministic narrator; no agent calls. |
| false | false | yes | Deterministic narrator; no agent calls. |
| any | * | no | Deterministic narrator; no agent calls. |

CI runs both deterministic and agent-aware paths depending on job type
(unit/API/e2e) and uses test-safe Gemini settings for deterministic
reproducibility.
