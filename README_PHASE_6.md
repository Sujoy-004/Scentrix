# Phase 6: Production Deployment & Monitoring

> **Status:** ✅ All infrastructure configuration complete and ready for deployment
>
> **Phase Goal:** Deploy frontend to Vercel, backend to Railway, provision cloud databases, configure CI/CD, and activate monitoring
>
> **Expected Duration:** 1-2 hours (mostly waiting for service provisioning)  
> **Estimated Cost:** $0 (free tiers available for all services)

---

## 📋 Quick Navigation

| Document | Purpose |
|----------|---------|
| [PHASE_6_QUICK_CHECKLIST.md](PHASE_6_QUICK_CHECKLIST.md) | ✅ Copy-paste friendly checklist |
| [PHASE_6_DEPLOYMENT_GUIDE.md](PHASE_6_DEPLOYMENT_GUIDE.md) | 📖 Detailed step-by-step guide with code blocks |
| [PHASE_6_SETUP_COMPLETE.md](PHASE_6_SETUP_COMPLETE.md) | 📊 Status of infrastructure configs |
| This file | 🎯 Overview and architecture |

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRODUCTION DEPLOYMENT                        │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐
│  Next.js App     │         │   FastAPI API    │
│  (Vercel)        │         │   (Railway)      │
│  ─────────────   │         │  ─────────────   │
│ ✅ Auto-deploy   │         │ ✅ Docker ready  │
│ ✅ Global CDN    │         │ ✅ Auto-scaling  │
│ ✅ SSL cert      │         │ ✅ Health checks │
│                  │         │                  │
└────────┬─────────┘         └────────┬─────────┘
         │                           │
         │   NEXT_PUBLIC_API_URL    │
         └──────────────────────────┘
                      ▼
         ┌──────────────────────────┐
         │   Databases & Queues     │
         ├──────────────────────────┤
         │ 📊 Neo4j AuraDB (Graph)  │
         │ 🗄️  PostgreSQL (Relational)
         │ 🔴 Redis (Cache/Queue)   │
         │ 📌 Pinecone (Embeddings) │
         └──────────────────────────┘
                      ▼
         ┌──────────────────────────┐
         │ Monitoring & Observability│
         ├──────────────────────────┤
         │ 🔴 Sentry (Error tracking)│
         │ 📊 GitHub Actions (CI/CD) │
         │ ✅ Health Checks         │
         └──────────────────────────┘
```

---

## 📦 Configuration Files Created

### ✅ Frontend (Next.js)
```
frontend/
├── vercel.json              ← Vercel build config (created)
├── package.json             ← Dependencies
├── next.config.ts           ← Next.js config
└── tsconfig.json            ← TypeScript config
```

**Key Features:**
- Auto-build on git push
- Security headers (CSP, X-Frame-Options)
- Environment variable substitution
- API rewrites

### ✅ Backend (FastAPI)
```
backend/
├── railway.toml             ← Railway config (created)
├── Procfile                 ← Process definitions (created)
├── pyproject.toml           ← Dependencies
├── app/
│   ├── main.py              ← FastAPI app (Sentry integrated)
│   ├── config.py            ← Settings
│   ├── sentry_config.py     ← Error tracking config (created)
│   ├── database.py          ← SQLAlchemy setup
│   └── ...
└── Dockerfile               ← Containerization
```

**Key Features:**
- Health check endpoint: `/health`
- Async database sessions
- Celery async tasks support
- Sentry error monitoring
- CORS configured for frontend

### ✅ CI/CD Pipeline
```
.github/workflows/
├── frontend-build.yml       ← Node.js lint & build (created)
├── backend-test.yml         ← Python tests & type-check (created)
└── deploy-production.yml    ← Auto-deploy on main push (created)
```

**Key Features:**
- Runs on every push to feature branches
- Full tests on PRs
- Auto-deploy on main branch push
- Coverage reporting
- Type checking (mypy, eslint)

### ✅ Documentation
```
.env.example                           ← Environment template (created)
PHASE_6_QUICK_CHECKLIST.md            ← Quick reference
PHASE_6_DEPLOYMENT_GUIDE.md           ← Detailed instructions
PHASE_6_SETUP_COMPLETE.md             ← Status summary
verify_deployment.py                  ← Verification script
```

---

## 🚀 Execution Roadmap

### Phase 6.1: Frontend Deployment (15 mins)
**Goal:** Get frontend live on Vercel

**Steps:**
1. Go to vercel.com/new
2. Import GitHub repository
3. Set `NEXT_PUBLIC_API_URL` environment variable
4. Click Deploy
5. Verify live at returned Vercel domain

**Success Criteria:**
- ✅ Frontend loads at HTTPS URL
- ✅ Mock fragrance data displays
- ✅ No build errors in Vercel dashboard

---

### Phase 6.2: Backend Deployment (15 mins)
**Goal:** Get FastAPI running on Railway

**Steps:**
1. Connect Railway to GitHub repo
2. Create PostgreSQL database
3. Create Redis instance
4. Deploy backend code
5. Verify `/health` endpoint

**Success Criteria:**
- ✅ GET `/health` returns `{"status": "ok"}`
- ✅ GET `/` returns API version info
- ✅ Railway logs show successful startup

---

### Phase 6.3: Databases (30 mins)
**Goal:** Provision all data stores and vector DB

**Steps:**
1. Neo4j AuraDB — Knowledge graph
2. PostgreSQL — User data
3. Redis — Caching & Celery
4. Pinecone — Embeddings

**Success Criteria:**
- ✅ Neo4j responds to queries
- ✅ PostgreSQL accessible via connection string
- ✅ Redis ping returns True
- ✅ Pinecone index created

---

### Phase 6.4: Monitoring (10 mins)
**Goal:** Activate error tracking and metrics

**Steps:**
1. Create Sentry project
2. Get DSN and add to Railway env vars
3. Verify Sentry receives errors

**Success Criteria:**
- ✅ Test error appears in Sentry dashboard
- ✅ Error details show stack trace

---

### Phase 6.5: CI/CD Secrets (10 mins)
**Goal:** Wire GitHub Actions to auto-deploy

**Steps:**
1. Add GitHub secrets (Vercel, Railway tokens)
2. Push to main branch
3. Verify workflows trigger

**Success Criteria:**
- ✅ GitHub Actions workflows all pass
- ✅ Vercel deployment triggered
- ✅ Railway deployment triggered

---

### Phase 6.6: Verification (15 mins)
**Goal:** Confirm all systems operational

**Steps:**
1. Run `python verify_deployment.py`
2. Test frontend URL
3. Test backend API
4. Check database connections
5. Verify Sentry receiving events

**Success Criteria:**
- ✅ All 8 verification tests pass
- ✅ Frontend and backend both respond
- ✅ All databases communicate

---

## 🔧 Environment Variables Required

Fill in these before deploying:

**Vercel (frontend only):**
```env
NEXT_PUBLIC_API_URL=https://your-railway-api.railway.app
```

**Railway & Local .env (backend):**
```env
# PostgreSQL (from Railway)
DATABASE_URL=postgresql://user:password@host:5432/scentscape

# Neo4j AuraDB
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# Redis (from Railway)
REDIS_URL=redis://default:password@host:6379

# Pinecone
PINECONE_API_KEY=your-api-key
PINECONE_ENVIRONMENT=us-west1-gcp

# Security
SECRET_KEY=your-secret-32-character-string

# Sentry
SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
SENTRY_ENVIRONMENT=production

# Frontend URL (for redirects)
FRONTEND_URL=https://scentscape-xxxxx.vercel.app
```

> See `.env.example` for complete list

---

## 📊 Deployment Status Template

Track your progress with this table:

| Phase | Component | Status | URL | Verified |
|-------|-----------|--------|-----|----------|
| 6.1 | Frontend (Vercel) | [ ] pending | _____ | [ ] |
| 6.2 | Backend (Railway) | [ ] pending | _____ | [ ] |
| 6.3 | Neo4j AuraDB | [ ] pending | _____ | [ ] |
| 6.3 | PostgreSQL | [ ] pending | _____ | [ ] |
| 6.3 | Redis | [ ] pending | _____ | [ ] |
| 6.3 | Pinecone | [ ] pending | _____ | [ ] |
| 6.4 | Sentry | [ ] pending | _____ | [ ] |
| 6.5 | GitHub Actions | [ ] pending | n/a | [ ] |

---

## ✅ Verification Checklist

After deployment, verify each component:

### Frontend (Vercel)
```bash
curl -I https://your-vercel-domain.vercel.app
# Expected: HTTP/1.1 200 OK
# Open in browser → Should see fragrance app
```

### Backend (Railway)
```bash
curl https://your-railway-api.railway.app/health
# Expected: {"status": "ok"}

curl https://your-railway-api.railway.app/
# Expected: {"name": "ScentScape API", "version": "0.1.0", ...}
```

### Database Connections
```bash
# Test all 4 databases via:
python verify_deployment.py

# All 8 tests should pass
```

### GitHub Actions
```bash
# Go to GitHub repo → Actions
# Push any change to main → Workflows trigger
# All three should succeed:
#   ✅ frontend-build.yml
#   ✅ backend-test.yml
#   ✅ deploy-production.yml
```

---

## 🎯 Success Criteria (Phase 6 Complete)

- [x] All infrastructure config files created
- [ ] Frontend deployed to Vercel
- [ ] Backend deployed to Railway
- [ ] All 4 databases provisioned
- [ ] Sentry configured and receiving errors
- [ ] GitHub Actions CI/CD active
- [ ] All health checks passing
- [ ] Verification script: `python verify_deployment.py` → All pass

---

## 📚 Resources & Documentation

### Official Docs
- **Vercel:** https://vercel.com/docs
- **Railway:** https://docs.railway.app
- **Neo4j AuraDB:** https://neo4j.com/cloud/aura/
- **Pinecone:** https://docs.pinecone.io
- **Sentry:** https://docs.sentry.io

### Guides in This Repo
- [PHASE_6_DEPLOYMENT_GUIDE.md](PHASE_6_DEPLOYMENT_GUIDE.md) — Complete walkthrough
- [PHASE_6_QUICK_CHECKLIST.md](PHASE_6_QUICK_CHECKLIST.md) — Copy-paste checklist
- [.env.example](.env.example) — Environment variables template

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Vercel build fails | Check Node.js version in `package.json`, run `npm install` locally |
| Railway health check fails | Check Procfile syntax, review Railway logs with `railway logs` |
| Database connection fails | Verify credentials, check IP whitelist, test URL locally |
| GitHub Actions not triggering | Verify branch name is `main`, check workflow files in `.github/workflows/` |
| Sentry not receiving errors | Check DSN is set, verify Sentry init code in main.py, send test error |

---

## 🚩 Next Steps After Phase 6

Once all systems are live and verified:

1. **Load Testing** — Test with 100+ concurrent users
2. **Data Seeding** — Populate Neo4j with fragrance data
3. **Feature Completion** — Implement recommendation engine
4. **Security Audit** — Run security scan on API
5. **Performance Tuning** — Optimize database queries
6. **Scaling** — Set up Celery workers, scale databases
7. **Monitoring** — Create dashboards, set up alerts

---

## 📞 Support

If something fails:
1. Check Railway/Vercel dashboards for error logs
2. Run `verify_deployment.py` to identify which service is down
3. Review guide steps in [PHASE_6_DEPLOYMENT_GUIDE.md](PHASE_6_DEPLOYMENT_GUIDE.md)
4. Check official docs links above

---

**Phase 6 is now ready for execution. Follow [PHASE_6_QUICK_CHECKLIST.md](PHASE_6_QUICK_CHECKLIST.md) step-by-step.**

🚀 **Let's deploy to production.**
