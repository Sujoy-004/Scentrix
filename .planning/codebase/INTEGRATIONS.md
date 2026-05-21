# External Integrations

**Analysis Date:** 2026-05-21

## APIs & External Services

### AI / ML
- **Google Gemini 1.5 Flash** — AI-powered "Digital Sommelier" (Aethera persona) for generating atmospheric fragrance insights
  - SDK/Client: `httpx` (raw REST API call)
  - Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent`
  - Auth: `GOOGLE_API_KEY` env var
  - Implementation: `backend/app/services/sommelier.py`
  - Fallback: Returns hardcoded atmospheric text when API key is absent

- **Sentence-Transformers** (`all-MiniLM-L6-v2`) — Local text embedding model for fragrance descriptions
  - Used offline in `ml/models/text_encoder.py`
  - Dim: 384, loaded with `local_files_only=True`
  - Cached embeddings: `ml/data/text_embeddings.pkl` / `ml/data/embedding_index.json`

### Vector Search
- **Pinecone** — Vector database for ANN similarity search on fragrance embeddings
  - SDK/Client: `pinecone>=5.0.0` (Python SDK, serverless spec)
  - Indexes:
    - `scentrix-fragrances` (384-dim, cosine) — Text embeddings
    - `scentrix-graph` (128-dim) — Graph embeddings
  - Auth: `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT` env vars
  - Implementation:
    - Backend: `backend/app/services/hybrid_search.py` (warming, query)
    - ML: `ml/models/text_encoder.py` (populate), `ml/models/graph_sage.py` (graph embeddings)
  - Fallback: Graceful degradation — recommendation falls back to catalog-only when Pinecone unavailable
  - Use case: `<100ms ANN search for 1K nearest neighbors`

## Data Storage

**Databases:**
- **PostgreSQL 15** (via `postgres:15-alpine` image) — Primary relational store
  - Connection: `DATABASE_URL` (asyncpg driver: `postgresql+asyncpg://`)
  - Client: SQLAlchemy 2.0+ async engine
  - Pool: 20 pool size / 10 overflow
  - Usage: User accounts, ratings, interactions, lead capture, quiz sessions
  - Migration: Alembic (`backend/app/migrations/`)
  - ORM models: `backend/app/models/models.py`
  - Target production: Supabase Postgres
  - Has graceful offline fallback (`DB_AVAILABLE` flag in `backend/app/database.py`)

- **Neo4j 5** (via `neo4j:5-community` image) — Knowledge graph for fragrance relationships
  - Connection: `NEO4J_URI` (bolt/neo4j protocol, port 7687)
  - Auth: `NEO4J_USERNAME` / `NEO4J_PASSWORD`
  - Web UI: port 7474
  - Usage: Fragrance entities, brands, note relationships, graph traversal for recommendations
  - Implementation:
    - Backend catalog: `backend/app/services/catalog.py`
    - ML ingestion: `ml/pipeline/ingest.py`, `ml/graph/`
    - Validation: `ml/tests/test_graph.py`
  - Target production: Neo4j AuraDB
  - Has fallback: catalog loads from JSON when Neo4j is offline

**File Storage:**
- **Cloudflare R2** — S3-compatible object storage for raw scraped data
  - SDK/Client: `boto3>=1.26.165` (AWS SDK for S3)
  - Auth: `CLOUDFLARE_R2_ACCESS_KEY`, `CLOUDFLARE_R2_SECRET_KEY`, `CLOUDFLARE_R2_BUCKET`
  - Endpoint: Account-specific R2 endpoint URL
  - Usage: Storing Fragrantica scrapes as JSONL, embeddings backup
  - Pipeline: `ml/scraper/scraper/pipelines.py` (CloudflareR2Pipeline)
  - Path format: `raw/fragrantica/YYYY-MM-DD/fragrances.jsonl`

- **Local filesystem** — Primary data source
  - SSOT: `ml/data/scentrix_master.json` (24K fragrance dataset)
  - Seed data: `ml/data/seed_fragrances.json`
  - Embeddings cache: `ml/data/embeddings.npy`, `ml/data/embedding_index.json`

**Caching:**
- **Redis 7** (via `redis:7-alpine` image) — In-memory cache and job store
  - Connection: `REDIS_URL` (redis:// protocol, default port 6379, DB 0)
  - SDK/Client: `redis>=5.0.0` with `redis.asyncio`
  - Usage:
    - Recommendation results cache (24h TTL via `backend/app/cache.py`)
    - Quiz session store with in-memory fallback (`backend/app/services/quiz_store.py`)
    - Async job tracking for recommendation lifecycle (`backend/app/services/job_store.py`)
    - Celery broker (documented but Celery currently broken — `celery_app.py` missing)
  - Fallback: In-memory Python dict used when Redis is unavailable

## Authentication & Identity

**Auth Provider:**
- **Supabase Auth** — Primary authentication provider
  - SDK/Client: Raw `httpx` calls to `{SUPABASE_URL}/auth/v1/*`
  - Implementation: `backend/app/services/supabase_auth.py` (281 lines)
  - Endpoints used: signup, token refresh, user lookup via admin API
  - Auth flow: JWT tokens (access + refresh) via `python-jose`
  - Dual auth: Supabase JWT OR local JWT (fallback when Supabase not configured)
  - Config: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
  - Frontend config: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
  - Dependencies: `backend/app/auth/dependencies.py` — `get_current_user_id`, `get_optional_user_id`

- **Local Auth** — Fallback when Supabase not configured
  - Password hashing: bcrypt via `passlib` (`backend/app/auth/auth.py`)
  - JWT signing: HS256 via `python-jose`
  - Token expiration: 15 min access / 7 day refresh

- **PII Encryption** — AES-256 Fernet (`cryptography` library)
  - Implementation: `backend/app/auth/encryption.py` + `backend/app/services/vault.py`
  - Encrypts: `full_name`, `email` at rest in PostgreSQL
  - Uses `DATA_ENCRYPTION_KEY` env var (32 base64-encoded bytes)

## Monitoring & Observability

**Error Tracking:**
- **Sentry** — Error and performance monitoring
  - SDK/Client: `sentry-sdk>=1.39.0`
  - Integrations: FastAPI, SQLAlchemy, Redis
  - Config: `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE`
  - Implementation: `backend/app/sentry_config.py`
  - Performance: 10% traces sample rate in production, 100% in development
  - Privacy: PII redaction via `before_send_filter` (strips auth headers, sensitive query params)

**Logs:**
- Python `logging` module — structured logging throughout backend
  - Format: `%(asctime)s [%(name)s] %(levelname)s: %(message)s`
  - Memory monitoring via `psutil` in hybrid search

**Product Analytics:**
- **PostHog** (commented out) — `posthog-js` v1.372.1 in frontend dependencies
  - Reference: `frontend/src/app/layout.tsx` line 9 — `// import PostHogPageView`
  - Not currently active

## CI/CD & Deployment

**Hosting:**
- **Frontend:** Vercel (production deployment via `vercel deploy --prod`)
  - Preview deploys on PR via GitHub Actions (`ci.yml`)
  - Project references in GitHub secrets: `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`
- **Backend:** Railway (`railway up --service backend`)
  - Auth: `RAILWAY_TOKEN` GitHub secret
  - Procfile referenced in Dockerfile but file missing on disk

**CI Pipeline:**
- **GitHub Actions** — 4 workflows in `.github/workflows/`:
  - `ci.yml` — PR quality gates: ruff → mypy → pytest (backend); ESLint → tsc → build → Playwright (frontend); Vercel preview deploy
  - `backend-test.yml` — Backend-only CI
  - `frontend-build.yml` — Frontend-only CI
  - `deploy-production.yml` — Production deploy on push to main: quality gates → Vercel deploy → Railway deploy → tag release
  - All backend CI requires PostgreSQL 15 + Redis 7 service containers

## Web Scraping & Data Ingestion

**Scraping:**
- **Scrapy** >=2.11.0 — Web scraping framework for Fragrantica
  - Config: `ml/scraper/scraper/settings.py`
  - Spider: `ml/scraper/scraper/spiders/fragrantica.py`
  - Rate limiting: 1 request/sec, rotating user agents, random delays
  - Respects robots.txt
  - Status: Fragrantica and Basenotes currently return 403 — automated scraping blocked

**Data Pipeline Orchestration:**
- **Prefect** >=2.14.0 — Weekly ETL workflow orchestration
  - Workflow: `ml/flows/weekly_refresh.py`
  - Tasks: scrape → clean → ingest → validate → log results
  - Scheduled: Sundays at 2:00 AM UTC
  - Local alternative: `make enrich` triggers `ml/pipeline/clean.py` + `ml/pipeline/ingest.py`

## Environment Configuration

**Required env vars:**
- `DATABASE_URL` — PostgreSQL async connection string
- `JWT_SECRET_KEY` — 32+ char secret for token signing
- `DATA_ENCRYPTION_KEY` — Fernet key for PII encryption

**Critical (no fallback):**
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` — Graph database
- `REDIS_URL` — Caching and job store

**Optional but recommended:**
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` — Auth provider
- `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` — Vector search
- `SENTRY_DSN` — Error tracking
- `GOOGLE_API_KEY` — Gemini AI insights

**Secrets location:**
- `.env` file at project root (ignored by git)
- `backend/.env` (ignored by git)
- GitHub Actions secrets (CI/CD)
- `.env.example` documents all expected vars

## Webhooks & Callbacks

**Incoming:**
- None detected — no explicit webhook endpoints defined in router files

**Outgoing:**
- None detected — system does not register outgoing webhooks

## Data Source of Truth (SSOT)

- **Primary dataset:** `ml/data/scentrix_master.json` — 24K fragrance catalog (the sole source of truth for fragrance data)
- **Seed dataset:** `ml/data/seed_fragrances.json` — 100 hand-curated fragrances for bootstrapping
- Target production: Licensed feed via `ml/scraper/import_licensed_feed.py`

## Architecture Target State (from `docs/architecture.md`)

```
User → Vercel (Next.js frontend) → FastAPI on Railway
  → Supabase (auth, profile, preferences, consent)
  → Redis/Celery (async jobs, short-lived caches)
  → Neo4j (derived recommendation knowledge graph)
  → Pinecone (derived vector embeddings)
```

**Data ownership split:**
- User records → Supabase (identity, profile, consent)
- Derived artifacts → Neo4j + Pinecone (embeddings, graph edges, scores)
- Recommendation cache → Redis

---

*Integration audit: 2026-05-21*
