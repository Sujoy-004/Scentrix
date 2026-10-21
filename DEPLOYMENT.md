# Scentrix — deployment guide

Target: **$0/month, no credit card required**, three free tiers.

```
Browser ──► Cloudflare Workers  ──► FastAPI on Render   ──► Neon Postgres
           (Next.js 16, static      (0.1 CPU / 512 MB,     (1 GB, scales to
            + 2 dynamic routes)      sleeps after 15 min)   zero after 5 min)
```

| Piece | Host | Free tier | Limit that bites first |
|---|---|---|---|
| Frontend | Cloudflare Workers | 100,000 req/day, 10 ms CPU/invocation | 100k req/day (~3k page views/day) |
| Backend | Render | 1 web service, 0.1 CPU, 512 MB, 750 instance-hours/month | 750 shared instance-hours; 15-min sleep → ~60 s cold start |
| Database | Neon | 1 GB, 100 CU-hrs/month, 5 GB egress/month | 100 CU-hrs/month |

**Deploy the backend first.** `NEXT_PUBLIC_API_URL` is inlined into the
frontend bundle at build time, so the frontend's build needs the backend's
public URL to already exist.

## Why these three

**Not Vercel.** The Hobby plan is *personal, non-commercial use only* (Vercel
ToS §4, Fair Use Guidelines). It also caps Active CPU at 4 hours/month, which
the catalog endpoint alone would exhaust at ~30–70k requests/month.

**Not Koyeb.** Mistral AI acquired Koyeb on 2026-02-17 and **closed the free
tier to new signups**: the free Instance now requires the Starter plan, which
requires a valid payment method, and signup defaults to the $29/month Pro
plan. Existing customers keep their access; new ones do not get it.

**Not Render Postgres.** Free Render Postgres databases expire 30 days after
creation (14-day grace, then the data is deleted). Neon has no expiry.

---

## 1. Neon — the database

1. Sign up at <https://neon.tech> → **Create a project** named `scentrix`.
2. **Region: pick `AWS EU Central 1` (Frankfurt)** to sit next to Render.
3. Click **Connect** in the console nav → the "Connect to your branch" modal:
   - Branch: `main` · Database: `neondb` · Role: `neondb_owner`
   - **Connection pooling: ON**
4. Copy the connection string.

> **The one thing that matters:** the hostname must contain **`-pooler`**.
> ✅ `postgresql://USER:PASS@ep-xxx-pooler.aws-eu-central-1.neon.tech/neondb?sslmode=require`
> ❌ `postgresql://USER:PASS@ep-xxx.aws-eu-central-1.neon.tech/neondb?sslmode=require` ← direct, no pooling

Nothing else to do. The API creates its own tables (`users`,
`fragrance_ratings`, `quiz_sessions`) on first boot via
`Base.metadata.create_all`. There is no migration step.

## 2. Render — the API

1. Sign up at <https://dashboard.render.com/register>. **No credit card
   needed** for the free tier.
2. **New → Blueprint** → connect GitHub → pick `Sujoy-004/Scentrix` → branch
   `feature/free-tier-deploy`.
   Render reads [`render.yaml`](render.yaml) from the repo root, which sets:
   runtime `docker`, `dockerfilePath: ./backend/Dockerfile`, build context
   the repo root, `plan: free`, `region: frankfurt`, health check `/health`.
3. Render prompts for **`DATABASE_URL`** — paste the Neon string from step 1.
   It is stored encrypted and never enters the repository.
4. Click **Apply**. The first build takes a few minutes (it compiles the
   wheels for numpy and psycopg2).
5. Check `https://scentrix-api.onrender.com/health`:
   ```json
   {"status":"success","data":{"status":"ok","database":"postgresql",
     "database_ready":true,"gs_embeddings":{"initialized":true}}}
   ```

<details>
<summary>Prefer the dashboard over a Blueprint?</summary>

**New → Web Service** → pick the repo → branch `feature/free-tier-deploy` →
*Language* **Docker** → *Dockerfile Path* `backend/Dockerfile` → *Region*
**Frankfurt** → compute plan **Free** → *Health Check Path* `/health` →
add env var `DATABASE_URL` (Neon) and `ALLOWED_ORIGINS`.

The build context is the repository root; the root `.dockerignore` keeps the
venv, `node_modules` and the training artifacts out of the image.
</details>

## 3. Cloudflare Workers — the frontend

### Option A: deploy from the CLI (repeatable)

```bash
cd frontend
npm ci
export NEXT_PUBLIC_API_URL="https://scentrix-api.onrender.com"
npx wrangler login
npm run deploy
```

`npm run deploy` runs `opennextjs-cloudflare build && opennextjs-cloudflare deploy`.

### Option B: connect the GitHub repo (auto-deploy)

In the Cloudflare dashboard: **Workers & Pages → Create → Import from GitHub**.

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Build command | `npx opennextjs-cloudflare build` |
| Deploy command | `npx opennextjs-cloudflare deploy` |
| Build variable | `NEXT_PUBLIC_API_URL` = the Render URL |
| Node version | `22` (Next.js 16 needs Node ≥ 20.9) |

`NEXT_PUBLIC_API_URL` is a **build** variable, not a runtime one. Changing it
requires a rebuild.

### After the first deploy

1. Note the worker URL, e.g. `https://scentrix.<subdomain>.workers.dev`.
2. Add it to Render's `ALLOWED_ORIGINS` env var and save — Render redeploys
   automatically. **Until this is done the API is unreachable from a browser.**
3. Attach a custom domain under **Workers → Settings → Domains & Routes**.
4. Add the custom domain to `ALLOWED_ORIGINS` too.

---

## Environment variable reference

### Backend (Render)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | **yes in production** | `sqlite:///./scentrix.db` | `postgresql://…` for Neon, `sqlite:////tmp/scentrix.db` for a throwaway container |
| `ALLOWED_ORIGINS` | **yes in production** | localhost only | comma-separated browser origins |
| `JWT_SECRET_KEY` | no | — | only the retired `/users/*` and rating endpoints use it |

### Frontend (Cloudflare build)

| Variable | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | **yes** | inlined at build time; the browser calls the API directly |
| `NEXT_PUBLIC_POSTHOG_KEY` | no | analytics; leave unset to disable |

---

## Free tier limits in practice

| Limit | Value | What happens when you hit it |
|---|---|---|
| Render instance hours | 750/month/workspace | all free web services suspended until the next month |
| Render sleep | 15 min idle → ~60 s wake | the first request after idle waits; the frontend retries for you |
| Render bandwidth | 5 GB/month (Hobby workspace) | over the limit, services are suspended if no card is on file |
| Render regions | Oregon, Ohio, Virginia, Frankfurt, Singapore | pick the one nearest your users |
| Workers requests | 100,000/day | requests start failing with 429 |
| Workers CPU | 10 ms/invocation | the two dynamic routes are server-rendered; the static ones cost nothing |
| Worker size | 3 MB gzip / 10 MB raw | currently 1,177 KiB gzip / 5,590 KiB raw |
| Neon compute | 100 CU-hrs/month | a suspended project costs no compute |
| Neon idle | suspends after 5 min | reconnects automatically (the engine pre-pings) |
| Neon storage | 1 GB | quiz sessions are swept on expiry; nothing grows unbounded |

### The cold-start problem (and what was done about it)

A free Render instance sleeps 15 minutes after the last request and takes
about a minute to boot. A naive 20 s client timeout would turn that into a
failed request, so the API client does this:

1. Try with a **10 s** timeout — a warm instance answers in ~50 ms.
2. On a timeout, network error, or 502/503/504, assume the instance is
   booting: show a *"Waking up the server — this can take up to a minute"*
   toast and retry once with an **80 s** timeout.

So the first visitor after a quiet period waits up to a minute, and sees why,
instead of an error. Every request after that is fast.

**Optional: keep it warm.** A scheduled ping every 10 minutes stops it ever
sleeping, at the cost of ~720 of the 750 monthly instance-hours — too tight to
recommend. A ping every 16 minutes drops that to ~675 hours and leaves a
1-in-16 chance of a cold start. If you want it, add a GitHub Actions cron
(free on a public repo) or a Cloudflare Worker cron trigger that GETs
`/health`. On GitHub Actions it is a 12-line workflow file.

### Known limits of this architecture

- **The database is on the critical path for the quiz.** If Neon is down, the
  catalog and the recommendations still work, but the quiz fails. This is
  deliberate: the product flow stores nothing, so a database outage degrades
  one feature instead of the whole site.
- **`NEXT_PUBLIC_API_URL` is frozen at build time.** Changing the backend URL
  means rebuilding the frontend.
- **The 10 ms Workers CPU limit applies to the two dynamic routes.** They
  render a client component shell, so the cost is small, but a heavier page
  would need to become static.

---

## Local verification

```bash
# Backend
cd backend
python -m pytest tests -q                      # 57 tests
python -m uvicorn app.main:app --reload

# Frontend
cd frontend
npm ci
npm run build                                  # must pass
npx tsc --noEmit                               # must pass
npm run lint                                   # 0 errors expected

# Cloudflare runtime, locally
npx opennextjs-cloudflare build
npx wrangler dev --port 8787 --local
```

The container image can be checked without Docker by simulating it: a clean
virtualenv with only `backend/requirements.txt` installed, only `backend/app/`
present, and `PORT=10000` exported the way Render sets it.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Every browser request fails, `curl` works | `ALLOWED_ORIGINS` does not include the frontend origin | add the exact origin, no trailing slash, then save (Render redeploys) |
| The frontend shows "could not load this fragrance" | `NEXT_PUBLIC_API_URL` points at localhost | it is inlined at build time — set it and rebuild |
| First request takes ~60 s | the Render instance was asleep | expected; the client retries automatically |
| Backend returns 500 at boot | `DATABASE_URL` unreachable | check `/health` → `database_ready`; the API still serves the catalog |
| Quiz returns 404 "Quiz session not found" | session expired (30 min) or the database is down | start a new quiz; check `database_ready` |
| Workers returns 404 on a dynamic route | the route was not prerendered | `/families/[family]` and `/fragrances/[id]` are server-rendered, not static |
| Build fails with `Cannot find name 'used'` | a stale `.next/dev` directory | `npm run build` clears it automatically |
| Render build fails on `COPY backend/...` | the build context is not the repo root | set *Dockerfile Path* to `backend/Dockerfile` and keep the context at the repo root |
