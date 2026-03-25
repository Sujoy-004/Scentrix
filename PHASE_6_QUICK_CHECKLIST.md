# Phase 6 Deployment Quick Reference Checklist

## ✅ Pre-Deployment Setup (Completed)

- [x] `frontend/vercel.json` — Vercel configuration
- [x] `backend/railway.toml` — Railway configuration  
- [x] `backend/Procfile` — Process definitions
- [x] `.github/workflows/frontend-build.yml` — Frontend CI
- [x] `.github/workflows/backend-test.yml` — Backend CI
- [x] `.github/workflows/deploy-production.yml` — Auto-deploy
- [x] `backend/app/sentry_config.py` — Error tracking integration
- [x] `PHASE_6_DEPLOYMENT_GUIDE.md` — Complete guide

---

## 🚀 Deployment Checklist (Do These)

### 1️⃣ Vercel Frontend Deployment
- [ ] Go to https://vercel.com/new
- [ ] Import KIIT0001/scentscape repository
- [ ] Framework: Next.js (auto-detected)
- [ ] Build: `npm run build`
- [ ] Set env var: `NEXT_PUBLIC_API_URL` = (your Railway URL)
- [ ] Click Deploy
- [ ] Get Vercel URL: `https://scentscape-xxxxx.vercel.app`
- [ ] Test: `curl -I https://scentscape-xxxxx.vercel.app`

### 2️⃣ Railway Backend Deployment
- [ ] `npm install -g @railway/cli`
- [ ] `railway login`
- [ ] `cd backend && railway init`
- [ ] `railway up`
- [ ] Get Railway URL from dashboard
- [ ] Update Vercel's `NEXT_PUBLIC_API_URL`
- [ ] Test: `curl https://your-railway-api.railway.app/health`

### 3️⃣ Neo4j AuraDB (Knowledge Graph)
- [ ] Go to https://console.neo4j.io
- [ ] Create instance: "scentscape-prod"
- [ ] Wait for provisioning
- [ ] Copy URI, username, password
- [ ] Add to Railway env vars: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`

### 4️⃣ PostgreSQL (User Data)
- [ ] In Railway dashboard: New → Database → PostgreSQL
- [ ] Copy DATABASE_URL from Railway variables
- [ ] Add to backend .env: `DATABASE_URL=postgresql://...`
- [ ] Add to Railway env vars

### 5️⃣ Redis (Cache)
- [ ] In Railway dashboard: New → Database → Redis
- [ ] Copy REDIS_URL from Railway variables
- [ ] Add to backend .env: `REDIS_URL=redis://...`
- [ ] Add to Railway env vars

### 6️⃣ Pinecone (Embeddings)
- [ ] Go to https://www.pinecone.io
- [ ] Create index: "scentscape-fragrances"
  - Dimension: 128
  - Metric: cosine
  - Environment: Starter (free)
- [ ] Copy API key
- [ ] Add to Railway env vars: `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT`

### 7️⃣ Sentry (Error Monitoring)
- [ ] Go to https://sentry.io
- [ ] Create project (Python)
- [ ] Copy DSN
- [ ] Add to Railway env vars: `SENTRY_DSN`, `SENTRY_ENVIRONMENT=production`
- [ ] Test: Send error from backend, verify in Sentry dashboard

### 8️⃣ GitHub Secrets (CI/CD)
In repo Settings → Secrets and variables → Actions:
- [ ] `VERCEL_TOKEN` = (from vercel.com/account/tokens)
- [ ] `VERCEL_ORG_ID` = (from Vercel project)
- [ ] `VERCEL_PROJECT_ID` = (from Vercel project)
- [ ] `RAILWAY_TOKEN` = (from railway.app/account)
- [ ] `NEXT_PUBLIC_API_URL` = (your Railway domain)

### 9️⃣ Environment Variables Setup
- [ ] Create `.env` file from `.env.example`
- [ ] Fill all database URLs
- [ ] Fill all API keys
- [ ] Generate `SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Copy to Railway environment variables dashboard

---

## 🔍 Verification Checklist (Test These)

### Frontend Verification
```bash
# Health check
curl -I https://scentscape-xxxxx.vercel.app
# Expected: 200 OK

# Open in browser
# Expected: Fragrance app homepage loads with mock data
```

### Backend Verification
```bash
# Health check
curl https://your-railway-api.railway.app/health
# Expected: {"status": "ok"}

# API info
curl https://your-railway-api.railway.app/
# Expected: JSON with version info
```

### Database Verification
```bash
# Neo4j (test via Railway console or Python driver)
# Expected: Connection successful

# PostgreSQL (Railway admin panel)
# Expected: Can see database listed

# Redis (Railway admin panel)
# Expected: Connected status

# Pinecone (dashboard)
# Expected: Index created with 0 vectors to start
```

### Sentry Verification
```bash
# Trigger test error (in backend code):
import sentry_sdk
sentry_sdk.capture_message("Test message from ScentScape")

# Check https://sentry.io/organizations/yourorg/
# Expected: Event appears in project
```

### CI/CD Verification
```bash
# Push to main branch
git push origin main

# Check GitHub Actions
# Expected: All workflows succeed
# - frontend-build.yml ✅
# - backend-test.yml ✅  
# - deploy-production.yml ✅

# Check Vercel & Railway dashboards
# Expected: Auto-deployments triggered and succeeded
```

---

## 📊 Final Status Board

| Component | Deployed | Verified | Notes |
|-----------|----------|----------|-------|
| Frontend (Vercel) | [ ] | [ ] | URL: _________________ |
| Backend (Railway) | [ ] | [ ] | URL: _________________ |
| Neo4j AuraDB | [ ] | [ ] | Connected: [ ] |
| PostgreSQL | [ ] | [ ] | Connected: [ ] |
| Redis | [ ] | [ ] | Connected: [ ] |
| Pinecone | [ ] | [ ] | Index created: [ ] |
| Sentry | [ ] | [ ] | Receiving events: [ ] |
| GitHub Actions | [ ] | [ ] | All workflows pass: [ ] |

---

## 🚨 Troubleshooting Quick Links

- Vercel build fails → Check `frontend/next.config.ts` and dependencies
- Railway startup fails → Check `backend/requirements.txt` and Procfile
- Database connection fails → Verify credentials and IP whitelist
- Sentry not working → Check DSN in environment variables
- CI/CD not triggering → Check GitHub secrets are set correctly

---

## 🎉 When All Done

```bash
# Your production URLs:
Frontend:  https://scentscape-xxxxx.vercel.app
Backend:   https://your-railway-api.railway.app
Graph DB:  neo4j+s://xxxxx.databases.neo4j.io
Monitoring: https://sentry.io/organizations/yourorg/

# All systems healthy:
✅ Frontend live and responsive
✅ Backend API responding  
✅ Databases connected
✅ CI/CD auto-deploying
✅ Monitoring active
✅ Health checks passing
```

**Phase 6 Complete. Ready for production users.**
