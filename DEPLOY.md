# AquaLinks — Deployment Guide

> **Stack:** Backend → Railway · Frontend → Vercel · Database → Supabase (already attached)
>
> Read every step **completely** before you click anything. Do them in order — each step depends on the one before it.

---

## Prerequisites

Before you start, make sure you have:

- [ ] A [Railway](https://railway.app) account (free tier is fine)
- [ ] A [Vercel](https://vercel.com) account (free tier is fine)
- [ ] Your **Supabase** project is already created and you have the connection string
- [ ] Your **Groq API key** from [console.groq.com](https://console.groq.com)
- [ ] The code pushed to GitHub (it already is)

---

## Step 1 — Get your Supabase connection string

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard) and open your project.
2. Click **Project Settings** → **Database** (left sidebar).
3. Scroll to **Connection string** → choose the **URI** tab.
4. Select **Transaction** mode (port **6543**) — this works best with Railway.
5. Copy the string. It looks like:
   ```
   postgresql://postgres.xxxx:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
6. Keep this string safe — you will use it in Step 2.

---

## Step 2 — Deploy the Backend on Railway

### 2a — Create a new Railway project

1. Go to [railway.app](https://railway.app) and click **New Project**.
2. Choose **Deploy from GitHub repo**.
3. Select the **AquaLinks** repository.
4. When asked **"Which service do you want to configure?"**, click **Add service** → **GitHub Repo** again (Railway may auto-create one).

### 2b — Set the root directory

1. Click on the service Railway just created.
2. Go to **Settings** tab.
3. Under **Root Directory**, type: `backend`
4. Railway will now build from the `backend/` folder and use `backend/railway.toml`.

### 2c — Set environment variables

1. Still on the service, click the **Variables** tab.
2. Click **New Variable** and add each one below:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | Your Supabase URI from Step 1 (e.g. `postgresql://postgres.xxxx:...@...supabase.com:6543/postgres`) |
   | `CORS_ALLOW_ORIGINS` | `https://your-vercel-app.vercel.app` *(use `*` for now, fix after Vercel deploy in Step 4)* |
   | `GROQ_API_KEY` | Your Groq API key |
   | `GROQ_MODEL` | `llama-3.3-70b-versatile` |
   | `GROQ_VISION_MODEL` | `llama-3.3-70b-versatile` |
   | `UPLOAD_DIR` | `/app/data/uploads` |
   | `REPORT_DIR` | `/app/data/reports` |
   | `AQUALENS_AGENTIC_MODE` | `true` |
   | `AQUALENS_FAKE_GEMINI` | `false` |
   | `AQUALENS_USE_SAMPLE_PROVIDER` | `false` |
   | `PC_STAC_URL` | `https://planetarycomputer.microsoft.com/api/stac/v1` |
   | `DEFAULT_LOOKBACK_DAYS` | `30` |
   | `MAX_CLOUD_COVER` | `30` |

   > **Optional:** Add `TAVILY_API_KEY` if you have one from [app.tavily.com](https://app.tavily.com). Free tier gives 1000 searches/month. Without it, Historian falls back to DuckDuckGo.

3. Click **Deploy** (or it deploys automatically after saving variables).

### 2d — Wait for the build to finish

1. Click the **Deployments** tab.
2. Watch the build logs. It will:
   - Install system libraries (GDAL, WeasyPrint fonts, etc.) — this takes **3–6 minutes** on first build.
   - Run `alembic upgrade head` — creates all tables in your Supabase database.
   - Start uvicorn on the Railway-assigned port.
3. When the deployment shows **Active ✓**, click the **Settings** tab.
4. Under **Networking**, click **Generate Domain**. You will get a URL like:
   ```
   https://aqualinks-backend-production.up.railway.app
   ```
5. Copy this URL — you need it in Step 3.

### 2e — Verify the backend is live

Open in your browser:
```
https://your-railway-url.up.railway.app/api/v1/health
```
You should see: `{"status": "ok"}` — backend is alive.

---

## Step 3 — Deploy the Frontend on Vercel

### 3a — Import the project

1. Go to [vercel.com/new](https://vercel.com/new).
2. Click **Import Git Repository** and select **AquaLinks**.
3. On the **Configure Project** screen:
   - **Framework Preset**: Next.js *(Vercel auto-detects this)*
   - **Root Directory**: Click **Edit** and type `frontend`
   - Leave **Build Command** and **Install Command** as default (Vercel reads `vercel.json`).

### 3b — Set environment variables

Still on the configuration screen, expand **Environment Variables** and add:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | Your Railway backend URL from Step 2d (e.g. `https://aqualinks-backend-production.up.railway.app`) |
| `NEXT_PUBLIC_SITE_URL` | Your Vercel URL (you can guess it: `https://aqualinks.vercel.app`, fix after first deploy if wrong) |

> **Note:** Do NOT add `DATABASE_URL` or any backend-only keys here. Those stay on Railway only.

### 3c — Deploy

1. Click **Deploy**.
2. Vercel builds Next.js — usually takes **2–3 minutes**.
3. When done, you see **Congratulations! 🎉** and get a URL like:
   ```
   https://aqualinks.vercel.app
   ```
4. Copy this URL.

---

## Step 4 — Wire frontend ↔ backend (CORS fix)

Now that both are live, update CORS on Railway so the backend only accepts requests from your Vercel domain.

1. Go back to Railway → your backend service → **Variables**.
2. Update `CORS_ALLOW_ORIGINS` from `*` to your actual Vercel URL:
   ```
   https://aqualinks.vercel.app
   ```
3. Railway auto-redeploys. Wait ~30 seconds.

If you also want to keep localhost working during local dev, comma-separate:
```
https://aqualinks.vercel.app,http://localhost:3000
```

---

## Step 5 — Update `NEXT_PUBLIC_SITE_URL` on Vercel

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard) → your project → **Settings** → **Environment Variables**.
2. Find `NEXT_PUBLIC_SITE_URL` and confirm it matches your actual Vercel URL exactly.
3. If you changed it, go to **Deployments** → click **…** on the latest deploy → **Redeploy**.

---

## Step 6 — Smoke test the full stack

Open your Vercel URL and check:

- [ ] Homepage loads without errors.
- [ ] Click **Get Started** or **New Session** — the session form opens.
- [ ] Create a session with a water body (e.g. draw a polygon over a lake).
- [ ] The analysis runs and you see the risk score card.
- [ ] The **Agent Trace** card shows all 5 agent steps.
- [ ] Download the PDF report — it should open without errors.

If anything fails, check:
- Railway logs: **Deployments** → click the deploy → **View Logs**.
- Vercel logs: **Deployments** → click the deploy → **Functions** tab.

---

## Environment Variables Reference

### Backend (Railway)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | Supabase PostgreSQL connection string |
| `CORS_ALLOW_ORIGINS` | ✅ | Comma-separated list of allowed frontend origins |
| `GROQ_API_KEY` | ✅ | Primary Groq API key |
| `GROQ_MODEL` | ✅ | Groq model ID (e.g. `llama-3.3-70b-versatile`) |
| `GROQ_VISION_MODEL` | ✅ | Vision model ID (same value is fine) |
| `UPLOAD_DIR` | ✅ | `/app/data/uploads` |
| `REPORT_DIR` | ✅ | `/app/data/reports` |
| `AQUALENS_AGENTIC_MODE` | ✅ | `true` for full 5-agent workflow |
| `GROQ_API_KEY_FALLBACK` | ❌ | Second Groq key for quota failover |
| `GROQ_API_KEY_FALLBACK_2` | ❌ | Third Groq key for quota failover |
| `TAVILY_API_KEY` | ❌ | Tavily search key (Historian agent) |

### Frontend (Vercel)

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | ✅ | Full Railway backend URL, no trailing slash |
| `NEXT_PUBLIC_SITE_URL` | ✅ | Full Vercel frontend URL, no trailing slash |

---

## Troubleshooting

**Railway build fails with "GDAL not found"**
→ This is a first-time build issue. Click **Redeploy** — it resolves after the apt-get cache is rebuilt.

**`alembic upgrade head` fails with "connection refused"**
→ Your `DATABASE_URL` is wrong. Double-check the Supabase URI — make sure the password is URL-encoded (replace `@` with `%40` if your password contains `@`).

**Frontend shows "Failed to fetch" when creating a session**
→ `NEXT_PUBLIC_API_URL` is wrong or missing on Vercel. Check the variable and redeploy.

**CORS error in browser console**
→ `CORS_ALLOW_ORIGINS` on Railway doesn't match your Vercel URL. They must be identical (including `https://`).

**Agent trace shows all steps failed**
→ `GROQ_API_KEY` is invalid or quota is exhausted. Check [console.groq.com](https://console.groq.com) for usage.
