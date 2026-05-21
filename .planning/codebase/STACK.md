# Technology Stack

**Analysis Date:** 2026-05-21

## Languages

**Primary:**
- Python 3.11+ - Backend API (`backend/`), ML pipeline (`ml/`), data processing
- TypeScript 5.9.3 - Frontend (`frontend/`) - Full type safety, configured in `frontend/tsconfig.json`

**Secondary:**
- HTML/CSS - Frontend rendering with Tailwind CSS v4
- SQL - Database queries via SQLAlchemy ORM (Python) and Cypher - Neo4j graph queries

## Runtime

**Environment:**
- Node.js 20 (Alpine) - Frontend runtime (`frontend/Dockerfile`, GitHub CI)
- Python 3.11 (Slim) - Backend runtime (`backend/Dockerfile`)
- Docker Compose - Local development orchestration (`docker-compose.yml`)

**Package Manager:**
- `pip` - Python packages via `pyproject.toml` (hatchling build backend)
- `npm` - Frontend packages via `frontend/package.json` with `package-lock.json`
- Lockfile: `package-lock.json` present; `pip` uses `pyproject.toml` without freeze file

## Frameworks

**Core:**
- **FastAPI** >=0.104.1 - Async Python REST API framework (OpenAPI docs at `/docs`, `/redoc`)
  - Entry point: `backend/app/main.py`
  - Async lifespan management, CORS middleware, exception handlers
- **Next.js** 16.2.1 - React framework with App Router (`frontend/`)
  - TypeScript, server components, font optimization
  - Config: `frontend/next.config.ts`
- **React** 19.2.4 - UI library
- **Tailwind CSS v4** - Utility-first CSS framework via `@tailwindcss/postcss`
  - Config: `frontend/postcss.config.mjs`

**Testing:**
- **pytest** >=7.4.3 - Backend test runner with pytest-asyncio (auto mode)
  - Coverage: pytest-cov (HTML + term-missing)
  - Config: `backend/pyproject.toml` `[tool.pytest.ini_options]`
  - Location: `backend/tests/`
- **Playwright** ^1.48.0 - Frontend E2E testing
  - Config: `frontend/playwright.config.ts`
  - Tests in `frontend/tests/`
  - Supports Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari
- **pytest** (standalone) - ML pipeline tests in `ml/tests/`

**Build/Dev:**
- **ruff** >=0.1.8 - Python linter + formatter (line-length 100, target py311)
  - Config: `backend/pyproject.toml` `[tool.ruff]` + `backend/ruff.toml`
- **mypy** >=1.7.0 - Python static type checking (strict mode)
  - Config: `backend/pyproject.toml` `[tool.mypy]`
- **ESLint** ^9 - Frontend linting via `eslint-config-next`
  - Config: `frontend/eslint.config.mjs`
- **Prettier** ^3.1.1 - Frontend formatting (single quotes, trailing commas, 100 width)
  - Config: `frontend/.prettierrc`
- **Hatchling** - Python build backend
- **Uvicorn** >=0.24.0 - ASGI server for FastAPI (hot reload in dev)
- **Alembic** >=1.13.0 - Database migrations
  - Config: `backend/alembic.ini`, migrations in `backend/app/migrations/`

## Key Dependencies

### Backend (`backend/pyproject.toml` — dependencies + optional-dependencies)

**Critical:**
- `fastapi>=0.104.1` - REST API framework
- `sqlalchemy>=2.0` - Async ORM for PostgreSQL
- `alembic>=1.13.0` - Database schema migrations
- `python-jose[cryptography]>=3.3.0` - JWT token handling
- `passlib>=1.7.4` + `bcrypt==4.0.1` - Password hashing
- `pydantic-settings>=2.1.0` / `pydantic[email]>=2.0` - Configuration and validation
- `sentry-sdk>=1.39.0` - Error tracking and performance monitoring
- `httpx>=0.25.0` - Async HTTP client (for Supabase API, Gemini API)
- `slowapi>=0.1.9` - Rate limiting middleware

**Database:**
- `asyncpg>=0.29.0` - Async PostgreSQL driver
- `neo4j>=5.14.0` - Neo4j graph database driver (in `runtime` and `ml` extras)
- `redis>=5.0.0` - Redis client (caching + Celery broker in `requirements.txt`)

**Infrastructure:**
- `pinecone>=5.0.0` - Vector database client (ANN similarity search)
- `celery>=5.3.6` - Async task queue (in `backend/requirements.txt`, not in `pyproject.toml`)
- `boto3>=1.26.165` - AWS SDK (used for Cloudflare R2 S3-compatible storage in scraper)
- `scrapy>=2.11.0` - Web scraping framework (in `scraper` extra)
- `prefect>=2.14.0` - Workflow orchestration (in `ml` extra, for weekly ETL)

**ML:**
- `torch-geometric>=2.4.0` - Graph Neural Network framework
- `sentence-transformers>=3.0.0` - Text embeddings (model: `all-MiniLM-L6-v2`)
- `scikit-learn>=1.3.0` - ML utilities
- `numpy>=1.26.0` - Numerical computing

### Frontend (`frontend/package.json`)
- `next@16.2.1` - Framework
- `react@19.2.4` / `react-dom@19.2.4` - UI library
- `@tanstack/react-query@^5.35.0` - Server state management
- `axios@^1.15.0` - HTTP client
- `framer-motion@^12.38.0` - Animation library
- `lucide-react@^1.7.0` - Icon library
- `zustand@^4.4.0` - Client state management (with persist middleware)
- `posthog-js@^1.372.1` - Product analytics (commented out in layout)

### ML Scraper (`ml/scraper/requirements.txt`)
- `requests`, `beautifulsoup4`, `lxml` - Web scraping stack (fallback when Scrapy unavailable)
- Source registry at `ml/scraper/source_registry.json`

## Configuration

**Environment:**
- **`.env`** at project root (not committed) — primary config via `pydantic-settings`
- **`.env.example`** at project root — documented template for all env vars
- **`backend/.env`** — backend-specific overrides
- `RUNNING_IN_DOCKER=true` flag for Docker-specific behavior

**Key configs required:**
- `DATABASE_URL` — PostgreSQL connection string (asyncpg driver)
- `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` — Neo4j graph credentials
- `REDIS_URL` — Redis connection string
- `PINECONE_API_KEY` / `PINECONE_INDEX_NAME` — Pinecone vector search
- `JWT_SECRET_KEY` — Token signing (32+ characters)
- `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` — Auth
- `DATA_ENCRYPTION_KEY` — Fernet key for PII encryption
- `SENTRY_DSN` — Error tracking (optional)
- `GOOGLE_API_KEY` — Gemini API for Digital Sommelier (optional)
- `CLOUDFLARE_R2_*` — Object storage keys (optional)
- `NEXT_PUBLIC_API_URL` — Frontend's backend URL

**Build:**
- Frontend: `tsconfig.json`, `next.config.ts`, `postcss.config.mjs`
- Backend: `pyproject.toml`, `alembic.ini`, `ruff.toml`
- Docker: `backend/Dockerfile`, `frontend/Dockerfile`
- Docker Compose: `docker-compose.yml` (postgres, neo4j, redis, backend, frontend)

## Platform Requirements

**Development:**
- Docker Desktop (or compatible)
- Python 3.11+
- Node.js 20+
- Make (for `Makefile`-based commands)
- 8GB+ RAM recommended (Neo4j + Postgres + ML containers)

**Production:**
- **Frontend:** Vercel (deployed via GitHub Actions)
- **Backend:** Railway (deployed via GitHub Actions)
- **Database:** Supabase Postgres (user data), Neo4j AuraDB (knowledge graph)
- **Cache/Queue:** Redis (Upstash or self-hosted)
- **Vector DB:** Pinecone (serverless, us-west4-gcp)
- **Object Storage:** Cloudflare R2
- **CI/CD:** GitHub Actions with secret injection

---

*Stack analysis: 2026-05-21*
