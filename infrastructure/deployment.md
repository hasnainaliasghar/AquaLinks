# Deployment — Vercel + Render + Supabase (free tier)

AquaLens runs end-to-end on free-tier infrastructure with three vendors:

| Layer | Service | Plan | Cost |
| --- | --- | --- | --- |
| Frontend | **Vercel** | Hobby | Free |
| Backend API | **Render** Web Service (Docker) | Free | Free |
| Database | **Supabase** Postgres + PostGIS + pgvector | Free | Free |
| Satellite imagery | Microsoft Planetary Computer STAC | — | Free, no key |
| LLM reasoning | Google AI Studio Gemini 2.5 Flash | — | Free tier |
| Map base tiles | OpenFreeMap | — | Free, no key |

You can swap any of these for paid equivalents (Fly.io, AWS RDS, S3, Sentinel Hub) without code changes — everything is wired through env vars.

> **Free-tier caveats**
> * Render's free Web Service plan **does not support persistent disks**. The blueprint writes uploads + cached PDFs to `/tmp` instead. PDFs are regenerated on every download, so losing the cache is harmless. Field-evidence photo uploads are best-effort across cold starts — if persistence matters, upgrade to Render Starter and re-add the `disk:` block.
> * Render free sleeps after 15 minutes idle; the first request after wake-up takes ~30 s.
> * Supabase free pauses inactive projects after a week. Open the dashboard once a week, or upgrade.

---

## 1. Provision Supabase

1. Sign up at <https://supabase.com> and create a new project. Region: pick the one nearest your Render region (Render's free Docker tier is in **Oregon**; pick `us-west-1` for lowest latency).
2. Wait for the project to finish provisioning (~2 min).
3. **Enable extensions** — Database → Extensions, toggle ON:
   - `postgis` — required for the geometry columns on `water_bodies`.
   - `vector` — required for the Historian's pgvector(768) memory recall.
4. **Copy the connection string** — Project Settings → Database → *Connection string* → tab **`Session pooler`**.
   - ⚠️ Use the **session pooler** (port `5432`), not the transaction pooler (port `6543`). The transaction pooler does not support prepared statements and breaks SQLAlchemy.
   - ⚠️ Render's free tier is **IPv4-only**; Supabase's direct connection (`db.<ref>.supabase.co`) is IPv6-only. The session pooler hostname `aws-0-<region>.pooler.supabase.com` is dual-stack and works from Render.
   - Replace `[YOUR-PASSWORD]` with your project's DB password.

   The URL looks like:

   ```text
   postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
   ```

   The backend auto-coerces this to `postgresql+psycopg://…` at runtime, so you can paste it verbatim.

5. Save it as `DATABASE_URL` — you'll paste it into Render in step 3.

> Migrations (`alembic upgrade head`) run automatically on every Render deploy. The first deploy creates all eight tables.

## 2. Get a Gemini API key

1. Open <https://aistudio.google.com/apikey>.
2. Click *Create API key* in an existing or new Google Cloud project.
3. Save the value as `GOOGLE_API_KEY`. The free tier allows millions of tokens per month — more than enough.
4. *(Optional but recommended)* Repeat once or twice to mint `GOOGLE_API_KEY_FALLBACK` and `GOOGLE_API_KEY_FALLBACK_2`. The agent runtime rolls over to these on 429 / quota errors.

## 3. Deploy the backend to Render

1. Fork the repository to your GitHub account (or use your own clone).
2. In Render, choose **New → Blueprint** and point it at the fork.
3. **Blueprint Path** → `infrastructure/render.yaml`.
4. Render reads the blueprint and creates the web service. Fill in the secrets the blueprint marks `sync: false`:

   | Key | Value |
   | --- | --- |
   | `DATABASE_URL` | The Supabase session-pooler URL from step 1. |
   | `GOOGLE_API_KEY` | Your Gemini key from step 2. |
   | `GOOGLE_API_KEY_FALLBACK` | *(optional)* Second Gemini key for quota rollover. |
   | `GOOGLE_API_KEY_FALLBACK_2` | *(optional)* Third Gemini key. |
   | `CORS_ALLOW_ORIGINS` | Comma-separated list of allowed origins. Set to your Vercel URL, e.g. `https://aqualens.vercel.app`. Add Vercel preview URLs (`https://aqualens-*.vercel.app`) if you want previews to call the prod API. |

5. Click **Apply**. Render builds the Docker image, runs `alembic upgrade head`, and starts `uvicorn`. The health check at `/api/v1/health` should turn green within ~90 s.

   First-time deploy logs you should see in order:

   ```text
   INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial …
   INFO  [alembic.runtime.migration] Running upgrade 0001_initial -> 0002_aoi_type …
   INFO  [alembic.runtime.migration] Running upgrade 0002_aoi_type -> 0003_agent_layer …
   INFO     Application startup complete.
   ```

6. Copy the Render service URL — looks like `https://aqualens-backend.onrender.com`. You'll paste it into Vercel in step 4.

## 4. Deploy the frontend to Vercel

1. In Vercel, choose **Add New… → Project** and import the same repository.
2. **Root Directory** → `frontend`. (Vercel auto-detects `pnpm` from `pnpm-lock.yaml`.)
3. Add the environment variables:

   | Key | Value |
   | --- | --- |
   | `NEXT_PUBLIC_API_URL` | Render URL from step 3, e.g. `https://aqualens-backend.onrender.com` |
   | `NEXT_PUBLIC_SITE_URL` | Your eventual Vercel URL, e.g. `https://aqualens.vercel.app` |

4. Click **Deploy**. Vercel runs `pnpm install --frozen-lockfile` then `pnpm build` and publishes the app.
5. Once deployed, copy the final Vercel URL and **add it to `CORS_ALLOW_ORIGINS`** on Render (Project → Environment → edit → save → service restarts).

## 5. Verify

```bash
# Health
curl https://aqualens-backend.onrender.com/api/v1/health
# → {"status":"ok"}

# Public stats (zero on a fresh DB; ticks up as you run sessions)
curl https://aqualens-backend.onrender.com/api/v1/sessions
# → []
```

Then open the Vercel URL, pick a water body (search, paste coordinates, or tap the map), and walk through **landing → monitor → session detail → evidence → report**. On the session detail page, the **Agentic workflow** card should stream in once Coordinator → Scout → (optional Historian) → Analyst → Reporter finish.

---

## Notes

- **Cold starts.** Render free sleeps after 15 minutes idle. The first request after wake-up takes ~30 s. Bump to Render Starter for hot uptime.
- **Ephemeral storage.** PDFs are re-rendered on every `/report` download (see `app/services/report_generator.py`), so cold starts don't lose anything user-facing. Field-evidence photo uploads live in `/tmp/aqualens/uploads` and may disappear after a restart — point `UPLOAD_DIR` at Supabase Storage or S3 for production-grade persistence.
- **Planetary Computer signed URLs** expire after 30 minutes. AquaLens reads bands inside that window during the pipeline run and only persists the derived numeric indices, so expiry never affects existing sessions.
- **WeasyPrint native deps** (`libcairo`, `libpango`, `gdk-pixbuf`) are installed by `backend/Dockerfile` and are present in Render's Docker runtime — no extra setup needed.
- **CORS during local dev.** `CORS_ALLOW_ORIGINS` defaults to `http://localhost:3000` so `pnpm dev` against a local backend works without config.
- **Database migrations.** Every Render deploy runs `alembic upgrade head` before starting `uvicorn`. To run them manually against Supabase:

  ```bash
  cd backend
  DATABASE_URL='postgresql://postgres.<ref>:<pwd>@aws-0-<region>.pooler.supabase.com:5432/postgres' \
    .venv/bin/alembic upgrade head
  ```
