# API contract

The full OpenAPI 3 spec is auto-generated and served at `/openapi.json`
with interactive docs at `/docs`. This page is a hand-curated summary of
the public surface under `/api/v1`.

## Conventions

- All requests and responses use JSON unless noted.
- Datetimes are ISO 8601 UTC strings (`2026-05-13T08:00:00Z`).
- Dates are ISO calendar dates (`2026-05-13`).
- UUIDs are version 4.
- Errors follow FastAPI's default shape: `{ "detail": "..." }` for
  string errors, or a list of validation errors keyed by `loc`, `msg`,
  and `type`.

## Health

```
GET /api/v1/health
```

Returns `{ "status": "ok" }`. Always 200.

## Water bodies

```
GET    /api/v1/water-bodies?limit=50&offset=0
POST   /api/v1/water-bodies
GET    /api/v1/water-bodies/{id}
PATCH  /api/v1/water-bodies/{id}
DELETE /api/v1/water-bodies/{id}
POST   /api/v1/water-bodies/bulk-delete
```

`POST` payload:

```json
{
  "name": "Lake Como",
  "description": "Sub-alpine lake in Lombardy.",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[9.20, 45.95], [9.30, 45.95], [9.30, 46.02], [9.20, 46.02], [9.20, 45.95]]]
  },
  "source": "user_drawn"
}
```

Response includes the computed centroid and area:

```json
{
  "id": "…",
  "name": "Lake Como",
  "geometry": { "type": "Polygon", "coordinates": "…" },
  "centroid": { "type": "Point", "coordinates": [9.25, 45.985] },
  "area_km2": 9.3,
  "source": "user_drawn",
  "created_at": "…",
  "updated_at": "…"
}
```

`POST /water-bodies/bulk-delete` accepts:

```json
{
  "ids": ["uuid-1", "uuid-2", "uuid-3"]
}
```

The operation is transactional and all-or-nothing. If any id is
missing, the API returns 404 and deletes nothing.

## Monitoring sessions

```
POST   /api/v1/sessions
GET    /api/v1/sessions?water_body_id={id}&limit=20&offset=0
GET    /api/v1/sessions/{id}
GET    /api/v1/sessions/{id}/indices
GET    /api/v1/sessions/{id}/risk
GET    /api/v1/sessions/{id}/trace        -> AgentTrace, 404 if absent
GET    /api/v1/sessions/{id}/field-brief  -> legacy FieldBrief, 404 if absent
GET    /api/v1/sessions/{id}/report       -> application/pdf
```

`/trace` is produced by the multi-agent layer. `/field-brief` is kept
for backward compatibility with older traces that still persisted the
retired Field Liaison payload; new runs now persist Reporter summary
JSON in the same nullable column.

Both endpoints return 404 for sessions where the relevant payload is
absent (including sessions run with `AQUALENS_AGENTIC_MODE=false` or
`AQUALENS_FAKE_GEMINI=true`).

`POST /sessions` accepts either an existing water body or a new one in
the same payload:

```json
{
  "water_body_id": "00000000-0000-0000-0000-000000000001",
  "start_date": "2026-04-13",
  "end_date": "2026-05-13",
  "max_cloud_cover": 30
}
```

or:

```json
{
  "new_water_body": {
    "name": "Custom AOI",
    "geometry": { "type": "Polygon", "coordinates": [...] }
  },
  "max_cloud_cover": 30
}
```

The session is returned immediately with `status="pending"`, then
transitions through `processing` to `complete` (or `failed`). The
frontend polls `/sessions/{id}` every two seconds while processing.

The detail payload includes the embedded water body, all six computed
indices, every field-evidence row, and the latest risk assessment.

## Field evidence

```
POST /api/v1/sessions/{id}/evidence   (multipart/form-data)
GET  /api/v1/sessions/{id}/evidence
```

`POST` accepts either:

- A single `payload` form field containing a JSON-serialised
  `EvidenceCreate` object, plus an optional `photo` file part.
- Or each evidence field as its own form key (handy for HTML forms
  without JavaScript).

`EvidenceCreate` shape:

```json
{
  "water_color": "green",
  "odor": "rotten",
  "algae_present": true,
  "dead_fish_count": 5,
  "rainfall_mm": 18.0,
  "complaints_count": 2,
  "notes": "Visible scum on the north shore.",
  "latitude": 45.99,
  "longitude": 9.25,
  "reporter_name": "Field Team A"
}
```

Submitting evidence schedules a background rescoring job. Reads of
`/sessions/{id}` and `/sessions/{id}/risk` will reflect the new
assessment within a few hundred milliseconds.

## Reports

```
GET /api/v1/sessions/{id}/report
```

Re-renders the PDF from persisted session rows on every request, then
returns it as `application/pdf` with
`Content-Disposition: attachment; filename=aqualens-analysis-YYYYMMDD.pdf`.

## Static files

Uploaded evidence photos are served at `/uploads/{session_id}/{file}`
directly by FastAPI's static-file mount.

## Errors

| Status | Meaning |
| --- | --- |
| 400 | Malformed request body. |
| 404 | Resource not found. |
| 422 | Validation failure (Pydantic). |
| 500 | Unexpected backend error. |
| 503 | An external dependency (Planetary Computer, Gemini) is unreachable. |
