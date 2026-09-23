# User manual

This is a quick tour of AquaLens from the user’s point of view. The
audience is anyone who lands on the live deployment for the first time:
field teams, environmental analysts, and technical evaluators.

## 1. Land on the marketing page

Hit `/`. You should see the hero with the animated globe, the indices
showcase, the two-pipeline workflow section, the agent-surface deep
dive, and a citations marquee. The top nav has a theme toggle and an
*Open app* button.

Switch themes with the toggle in the top-right. Both dark and light
variants are fully designed — light is not just an inverted dark.

## 2. Open the app

Click *Open app* or press `Ctrl K` (or `Cmd K` on macOS) and type "dashboard". The dashboard
shows session totals, the most recent five sessions as cards, and the
water bodies you’ve saved.

## 3. Start a session

Click *Start monitoring* (or `/monitor`). The page is split:

- **Left** — a full-bleed MapLibre map with a street / satellite /
  terrain basemap switcher. Pick an AOI three ways: type a place name
  into the search bar (Nominatim autocomplete), paste decimal
  coordinates as `lat, lng`, or click anywhere on the map to drop a
  pin. AquaLens turns the point into a ~1 km buffer polygon for you;
  the wizard shows the live area readout.
- **Right** — a three-step wizard:
  1. *Area*: confirm the AOI name (auto-filled from the place search
     or the coordinates) and review the polygon on the mini-map.
  2. *Window*: choose a start date, an end date (defaults: last 30
     days), and a maximum cloud-cover threshold (default 30%).
  3. *Review*: confirm the AOI, window, and provider, then *Launch
     session*.

The session is created and the page routes to `/sessions/{id}` with
`status="processing"`.

## 4. Watch the pipeline

The session detail page polls the backend every two seconds. While
the pipeline runs:

- A progress bar at the top walks through *Fetching imagery* → *Computing
  indices* → *Scoring risk* → *Handover to coordinator*.
- The page shows skeleton cards in the same layout as the final
  content, so there is no layout shift when the data arrives.
- Immediately after handover, the Agentic workflow card starts filling
  in live as Coordinator → Scout → (optional Historian) → Analyst →
  Reporter run.

When the run completes, the page shows:

- **Scene metadata** — provider, scene ID, capture date, cloud cover.
- **Index grid** — six Recharts area charts, one per index, with the
  masked-mean annotated.
- **Index table** — sortable list with copy-to-CSV.
- **Risk assessment** — animated 0–100 ring, level pill, recommendation,
  reasoning narrative, and a red-bordered limitations callout.
- **Evidence timeline** — empty initially.
- **Mini-map** (sticky right rail) and quick metrics.

## 5. Add field evidence

Click *Add evidence* (or visit `/sessions/{id}/evidence`). The form is
mobile-first: pick a water colour and odour, toggle algae, type the
counts, optionally attach a photo, optionally tap *Use device GPS* to
fill coordinates. Submit.

Toasts confirm the submission. The risk model re-scores; Gemini
re-writes the narrative; the report regenerates. Back on the session
detail page the new numbers and prose appear after the next poll.

## 6. Read the Agentic workflow card

Below the risk card you'll find **Agentic workflow** — a collapsible
timeline of the five Gemini agents that ran on this session:

- **Coordinator** plans the workflow.
- **Scout** picks the Sentinel-2 scene; uses Gemini Vision on the
  actual RGB thumbnail to flag haze or sun glint over the AOI.
- **Historian** pulls prior sessions for this water body, computes a
  trend, runs a Mann-Kendall significance test via Gemini code
  execution, and cites real news with Google Search grounding +
  URL Context. Writes a short note to per-water-body memory for next
  time.
- **Analyst** drafts the narrative, runs a self-critique pass, and
  rewrites once when the critique catches a violation. The trace
  shows draft v1 and v2 side by side.
- **Reporter** turns the narrative into a plain-English public summary
  card with clear guidance and limitations.

Each row expands to show its individual tool calls, arguments, and
results. If any agent failed, the failure is visible there too —
degraded behaviour is never silent.

## 7. Read the citizen summary card

Below the agent trace, the **What this means for you** summary card
gives clear guidance for people and for pets/kids, plus a "what we
couldn't check" section and source links when external context was
used. Read in plain English — no remote-sensing jargon.

## 8. Export a report

On the session detail page click *Download PDF* or *Open report*. The
PDF mirrors the in-browser report view exactly — same risk card,
indices, scene metadata, evidence table, advisory disclaimer, and the
MIT license footer. When the agent layer ran, the PDF also includes
a short appendix listing the agents that contributed and any external
sources the Historian cited.

## 9. Track trends

Visit `/water-bodies/{id}` to compare every session for the same AOI:
line charts across all six indices with a shared time axis.

## What you should NOT use AquaLens for

- Certified water-quality reports.
- Public-safety decisions about drinking water.
- Toxin or pathogen detection.
- Real-time monitoring with sub-day latency.

The model is a *triage* tool: it tells you where to spend your sampling
budget first.
