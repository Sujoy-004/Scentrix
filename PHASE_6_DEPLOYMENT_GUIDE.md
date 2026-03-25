# Phase 6 Deployment & Monitoring Guide

This document provides step-by-step instructions to complete Phase 6: Production Deployment.

## 🚀 Quick Start

Phase 6 has **four independent deployment tracks** that can be completed in parallel:

1. **Frontend → Vercel** (Next.js hosting)
2. **Backend → Railway** (FastAPI API server)
3. **Cloud Databases** (Neo4j, PostgreSQL, Redis, Pinecone)
4. **Monitoring & CI/CD** (Sentry, GitHub Actions)

---

## Track 1: Frontend Deployment to Vercel

### Prerequisites
- GitHub account with your ScentScape repo pushed
- Vercel account (free tier available)

### Steps

#### 1.1 Connect GitHub Repository to Vercel

```bash
# Navigate to https://vercel.com/dashboard
# Click "Add New → Project"
# Import your GitHub repository "KIIT0001/scentscape"
# Select the project
```

#### 1.2 Configure Vercel Project Settings

In Vercel dashboard for your project:

**Settings → General:**
- Framework: Next.js
- Build command: `npm run build`
- Output directory: `.next`
- Install command: `npm install`

**Settings → Environment Variables:**
Add the following:
```
NEXT_PUBLIC_API_URL = https://your-railway-api.railway.app
```

#### 1.3 Deploy

```bash
# Simply push to main branch
git push origin main

# Vercel will automatically deploy
# Watch progress at https://vercel.com/dashboard
```

**You'll get a live URL like:** `https://scentscape-xxxxx.vercel.app`

---

## Track 2: Backend Deployment to Railway

### Prerequisites
- Railway account (free tier available at railway.app)
- Docker installed locally

### Steps

#### 2.1 Create Railway Project

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project
cd "C:\Users\KIIT0001\Downloads\Telegram Desktop\ScentScapeAI\ScentScape"
railway init

# When prompted:
# - Project name: scentscape-api
# - Select "Backend"
```

#### 2.2 Link GitHub Repository

```bash
# Connect to GitHub for auto-deploy
railway link https://github.com/KIIT0001/scentscape
```

#### 2.3 Deploy Backend

```bash
# Deploy from main branch
cd backend
railway up

# Watch logs
railway logs --follow
```

**You'll get a Railway domain like:** `https://scentscape-api-prod.railway.app`

**Health check:** `curl https://scentscape-api-prod.railway.app/health`

---

## Track 3: Cloud Databases Setup

### 3.1 Neo4j AuraDB (Knowledge Graph)

```bash
# 1. Go to https://console.neo4j.io
# 2. Sign up or log in
# 3. Create instance:
#    - Name: scentscape-prod
#    - Region: US (same as backend)
#    - Plan: Free (1GB) initially
# 4. Accept terms and create
# 5. Get connection details:
#    - Copy URI (looks like: neo4j+s://xxxxx.databases.neo4j.io)
#    - Copy USERNAME (neo4j)
#    - Copy PASSWORD (given once at creation)
# 6. Test connection:
```

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "neo4j+s://xxxxx.databases.neo4j.io",
    auth=("neo4j", "password")
)

# Test it
with driver.session() as session:
    result = session.run("RETURN 1")
    print(result.single()[0])  # Should print 1

driver.close()
```

### 3.2 PostgreSQL (User Data)

**Create on Railway:**
```bash
# In Railway project dashboard:
# 1. New → Database → PostgreSQL
# 2. Configure:
#    - Username: scentscape_user
#    - Password: (generate strong password)
#    - Database: scentscape
# 3. Copy DATABASE_URL from Railway
#    (Format: postgresql://user:pass@host:5432/scentscape)
```

### 3.3 Redis (Caching & Celery)

**Create on Railway:**
```bash
# In Railway project dashboard:
# 1. New → Database → Redis
# 2. Copy REDIS_URL from Railway variables
#    (Format: redis://default:password@host:6379)
```

### 3.4 Pinecone (Vector Embeddings)

```bash
# 1. Go to https://www.pinecone.io
# 2. Sign up (free tier available)
# 3. Create index:
#    - Environment: Starter (free region)
#    - Name: scentscape-fragrances
#    - Dimension: 128 (matches GraphSAGE output)
#    - Metric: cosine
#    - Pod type: s1 (small)
# 4. Copy API key from account settings
# 5. Copy environment name
```

---

## Track 4: Environment Variables & Secrets

### 4.1 Create .env File (Local Development)

```bash
cp .env.example .env
```

Edit `.env` and fill in:
```env
# Database URLs (from Track 3)
DATABASE_URL=postgresql://user:password@host:5432/scentscape
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
REDIS_URL=redis://default:password@host:6379

# Pinecone
PINECONE_API_KEY=your-api-key
PINECONE_ENVIRONMENT=starter
PINECONE_INDEX_NAME=scentscape-fragrances

# Security
SECRET_KEY=your-random-32-character-string-here
JWT_ALGORITHM=HS256

# Frontend
FRONTEND_URL=https://scentscape-xxxxx.vercel.app
```

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4.2 Set Railway Environment Variables

**In Railway project dashboard:**
- Click Variables
- Add all variables from Track 3 database connections
- Add Pinecone credentials
- Add SECRET_KEY

### 4.3 Set Vercel Environment Variables

**In Vercel project dashboard:**
- Settings → Environment Variables
- Add only public variables:
```
NEXT_PUBLIC_API_URL=https://your-railway-api.railway.app
```

---

## Track 5: Sentry Setup (Error Monitoring)

### 5.1 Create Sentry Account

```bash
# 1. Go to https://sentry.io
# 2. Sign up / log in
# 3. Create organization (if new)
# 4. Create project:
#    - Platform: Python
#    - Name: scentscape-backend
```

### 5.2 Get Sentry DSN

```bash
# After creating project, copy the DSN
# Format: https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
```

### 5.3 Configure Sentry in Backend

**Add to .env:**
```env
SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

**Add to Railway variables** (same as .env)

---

## Track 6: GitHub Actions CI/CD

### 6.1 Add Secrets to GitHub

**Go to GitHub repo → Settings → Secrets and variables → Actions**

Add these secrets:
```
VERCEL_TOKEN         = your-vercel-token
VERCEL_ORG_ID        = your-vercel-org-id  
VERCEL_PROJECT_ID    = your-vercel-project-id
RAILWAY_TOKEN        = your-railway-token
NEXT_PUBLIC_API_URL  = https://your-railway-api.railway.app
```

**How to get tokens:**
- **Vercel token:** Account Settings → Tokens → Create Token
- **Vercel Org ID:** Project Settings → General → Org ID
- **Railway token:** Account Settings → Tokens → Create Token

### 6.2 Verify Workflows

**GitHub repo → Actions**

You should see:
- ✅ frontend-build.yml (runs on frontend/ changes)
- ✅ backend-test.yml (runs on backend/ changes) 
- ✅ deploy-production.yml (runs on main branch push)

---

## 🔍 Verification Checklist

After completing all tracks, verify each service is live:

### Frontend
```bash
curl -I https://scentscape-xxxxx.vercel.app
# Expected: 200 OK
# Open in browser to verify UI loads
```

### Backend Health
```bash
curl https://your-railway-api.railway.app/health
# Expected: {"status": "ok"}

curl https://your-railway-api.railway.app/
# Expected: JSON with API info
```

### Database Connections
```python
# Test Neo4j
from neo4j import GraphDatabase
driver = GraphDatabase.driver("neo4j+s://xxxxx.databases.neo4j.io", auth=("neo4j", "pass"))
with driver.session() as s:
    print(s.run("RETURN 1").single()[0])

# Test PostgreSQL
import psycopg2
conn = psycopg2.connect("postgresql://user:pass@host:5432/scentscape")
print("PostgreSQL OK")

# Test Redis
import redis
r = redis.from_url("redis://default:pass@host:6379")
print(r.ping())  # True = OK

# Test Pinecone
import pinecone
pinecone.init(api_key="key", environment="env")
print(pinecone.describe_index("scentscape-fragrances"))
```

### Sentry
Send test error:
```python
import sentry_sdk
sentry_sdk.capture_exception(Exception("Test error from ScentScape"))
```
Check Sentry dashboard for event.

---

## 🚦 CI/CD Pipeline Status

Check GitHub Actions:
```bash
git push origin main
# Watch https://github.com/KIIT0001/scentscape/actions
# All three workflows should pass:
# ✅ frontend-build.yml
# ✅ backend-test.yml  
# ✅ deploy-production.yml
```

---

## 📋 Common Issues & Fixes

### Vercel Build Fails
**Issue:** Next.js build fails with missing dependencies
**Fix:** 
```bash
cd frontend
npm install
npm run build
```

### Railway Health Check Fails
**Issue:** `/health` endpoint returns 502
**Fix:** Check Railway logs for startup errors
```bash
railway logs --follow
```

### Neo4j Connection Timeout
**Issue:** Cannot connect to AuraDB
**Fix:** Check URI and credentials, ensure IP whitelist is open

### Sentry Not Receiving Errors
**Issue:** Errors not appearing in Sentry dashboard
**Fix:** 
- Check SENTRY_DSN is set
- Ensure Sentry integration is initialized in main.py
- Check that exception actually occurs (wrap in try/catch)

---

## 🎯 Final Handoff

Once all checks pass:

1. ✅ Frontend is live on Vercel
2. ✅ Backend is live on Railway
3. ✅ All databases provisioned and connected
4. ✅ CI/CD pipeline auto-deploying
5. ✅ Sentry monitoring errors
6. ✅ Health checks all passing

**Production system is ready for users.**

---

## 📚 Next Steps (Phase 6+)

After verification:
- Load test with realistic fragrance data
- Set up monitoring dashboards
- Create runbook for on-call support
- Plan for scaling (more Celery workers, Redis clustering, etc.)
