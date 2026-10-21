# Scentrix — deployment guide

Target: **$0/month**, three free tiers, no credit card required for two of them.

```
Browser ──► Cloudflare Workers  ──► FastAPI on Koyeb  ──► Neon Postgres
           (Next.js 16, static      (512 MB / 0.1 vCPU,    (1 GB, scales to
            + 2 dynamic routes)      scale to zero)         zero after 5 min)
```

| Piece | Host | Free tier | Limit that bites first |
|---|---|---|---|
| Frontend | Cloudflare Workers | 100,000 req/day, 10 ms CPU/invocation | 100k req/day (~3k page views/day) |
| Backend | Koyeb | 1 service, 512 MB, 0.1 vCPU, 2 GB SSD, 1 region | 0.1 vCPU (latency), 1 h scale-to-zero |
| Database | Neon | 1 GB, 100 CU-hrs/month, 5 GB egress/month | 100 CU-hrs/month |

Why not Vercel: the Hobby plan is **personal, non-commercial use only** (Vercel
ToS §4, Fair Use Guidelines). It also caps Active CPU at 4 hours/month, which
the catalog endpoint alone would exhaust at ~30–70k requests/month.

**Deploy the backend first.** `NEXT_PUBLIC_API_URL` is inlined into the
frontend bundle at build time, so the frontend's build needs the backend's
public URL to already exist.

---

## 1. Neon — the database

1. Sign up at <https://neon.tech> → create a project, pick the closest region.
2. **Connection details → Pooled connection**. Copy the `postgresql://`
   string. It looks like:
   ```
   postgresql://USER:PASSWORD@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require
   ```
3. Keep it. This is `DATABASE_URL` for the backend.
4. Nothing else to do. The API creates its own tables
   (`users`, `fragrance_ratings`, `quiz_sessions`) on first boot via
   `Base.metadata.create_all`. There is no migration step.

Notes:
- Use the **pooled** endpoint (`-pooler` in the host), not the direct one.
- The engine pre-pings and recycles connections, so a compute that resumed
  from scale-to-zero reconnects on its own.
- The app also works with **no database at all**: set
  `DATABASE_URL=sqlite:////tmp/scentrix.db` for a throwaway container. The
  product flow writes nothing; only the quiz sessions need storage, and they
  are disposable.

## 2. Koyeb — the API

1. Sign up at <https://koyeb.com>. A card is required (a $29 pre-authorisation
   hold); the free **Instance type** is what gives you the free service, so
   make sure the service is on `free` and not a paid instance.
2. **Create → App → Dockerfile** (not a buildpack).
   - **Dockerfile path:** `backend/Dockerfile`
   - **Build context:** the repository root (the default)
   - **Instance type:** `free` (512 MB, 0.1 vCPU, 2 GB SSD)
   - **Region:** Frankfurt or Washington, D.C. — the only two on the free tier
   - **Port:** `8000` (the container command reads `$PORT` and falls back to 8000)
   - **Health check path:** `/health`
3. Environment variables:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | the Neon pooled connection string |
   | `ALLOWED_ORIGINS` | the frontend origin, e.g. `https://scentrix.<subdomain>.workers.dev` |

   `ALLOWED_ORIGINS` is a comma-separated list. It **must** contain the
   frontend origin or every browser request is blocked by CORS.

4. Deploy. First boot: ~1.5 s (catalog JSON + embeddings) plus the Neon
   connect. Check `https://<your-service>.koyeb.app/health`:
   ```json
   {"status":"success","data":{"status":"ok","database":"postgresql",
     "database_ready":true,"gs_embeddings":{"initialized":true}}}
   ```

## 3. Cloudflare Workers — the frontend

### Option A: deploy from the CLI (repeatable)

```bash
cd frontend
npm ci
export NEXT_PUBLIC_API_URL="https://<your-service>.koyeb.app"
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
| Build variable | `NEXT_PUBLIC_API_URL` = the Koyeb URL |
| Node version | `22` (Next.js 16 needs Node ≥ 20.9) |

`NEXT_PUBLIC_API_URL` is a **build** variable, not a runtime one. Changing it
requires a rebuild.

### After the first deploy

1. Note the worker URL, e.g. `https://scentrix.<subdomain>.workers.dev`.
2. Add it to the backend's `ALLOWED_ORIGINS` and redeploy the backend.
3. Attach a custom domain under **Workers → Settings → Domains & Routes**.
4. Add the custom domain to `ALLOWED_ORIGINS` too.

## 4. Remove Vercel

The repository contains no `vercel.json` and no `.vercel/` directory, so
nothing needs deleting from git. The rest is account-side:

1. <https://vercel.com/dashboard> → the project → **Settings → General →
   Delete Project**.
2. **GitHub → `Sujoy-004/Scentrix` → Settings → Apps → Vercel → Configure →
   Remove**.
3. Revoke the Vercel API token (Account Settings → Tokens) if one exists.
4. Check the old deployment's domain is not referenced anywhere in your new
   environment variables.

---

## Environment variable reference

### Backend (Koyeb)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | no | `sqlite:///./scentrix.db` | `postgresql://…` for Neon, `sqlite:////tmp/scentrix.db` for a throwaway container |
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
| Workers requests | 100,000/day | requests start failing with 429 |
| Workers CPU | 10 ms/invocation | the dynamic routes (`/families/[family]`, `/fragrances/[id]`) are server-rendered; the static ones cost nothing |
| Worker size | 3 MB gzip / 10 MB raw | currently 1,177 KiB gzip / 5,590 KiB raw |
| Koyeb instance | 512 MB / 0.1 vCPU | slow responses; the API holds the catalog in memory (~60 MB) |
| Koyeb scale-to-zero | 1 hour idle | the first request after an hour wakes the instance (seconds) |
| Koyeb regions | Frankfurt or Washington DC | pick the one nearest your users |
| Neon compute | 100 CU-hrs/month | a suspended project costs no compute |
| Neon idle | suspends after 5 min | reconnects automatically (the engine pre-pings) |
| Neon storage | 1 GB | quiz sessions are swept on expiry; nothing grows unbounded |

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
virtualenv with only `backend/requirements.txt` installed and only
`backend/app/` present.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Every browser request fails, `curl` works | `ALLOWED_ORIGINS` does not include the frontend origin | add the exact origin, no trailing slash |
| Backend returns 500 at boot | `DATABASE_URL` unreachable | check `/health` → `database_ready`; the API still serves the catalog |
| Frontend shows "could not load this fragrance" | `NEXT_PUBLIC_API_URL` points at localhost | it is inlined at build time — set it and rebuild |
| Quiz returns 404 "Quiz session not found" | session expired (30 min) or the database is down | start a new quiz; check `database_ready` |
| Workers returns 404 on a dynamic route | the route was not prerendered | `/families/[family]` and `/fragrances/[id]` are server-rendered, not static |
| Build fails with `Cannot find name 'used'` | a stale `.next/dev` directory | `npm run build` clears it automatically |
