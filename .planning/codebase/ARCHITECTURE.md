<!-- refreshed: 2026-05-21 -->
# Architecture

**Analysis Date:** 2026-05-21

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js 16 / React 19)                  │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌─────────────────────┐  │
│  │ App      │  │ Components│  │ Stores   │  │ Lib (API, Hooks,    │  │
│  │ Router   │  │ (18 .tsx) │  │ (Zustand)│  │  QuizTheme, Types)  │  │
│  └────┬─────┘  └───────────┘  └──────────┘  └──────────┬──────────┘  │
│       │                                                 │             │
│       └─────────────────── HTTP (axios) ─────────────────┘             │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI / Python 3.11+)               │
│                                                                       │
│  ┌──────────┐  ┌────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Routers  │  │ Auth Layer │  │ Services     │  │ Schemas + ORM │  │
│  │ (6 src)  │  │ (JWT/Supa) │  │ (10 modules) │  │ Models        │  │
│  └────┬─────┘  └────────────┘  └──────┬───────┘  └───────────────┘  │
│       │                               │                              │
│       └───────────────────────────────┘                              │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │  External Stores: PostgreSQL, Neo4j, Redis, Pinecone          │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        ML LAYER (PyTorch / PyG)                       │
│  ┌──────────┐  ┌────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Models   │  │ Pipeline   │  │ Flows (Pref.)│  │ Scraper       │  │
│  │ (3 src)  │  │ (5 modules)│  │ (weekly_refr)│  │ (scrapy)      │  │
│  └──────────┘  └────────────┘  └──────────────┘  └───────────────┘  │
│  Data SSOT: ml/data/scentrix_master.json (~24k fragrances)           │
└──────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **Routers** | HTTP request handling & response orchestration | `backend/app/routers/*.py` |
| **Services** | Business logic, catalog mgmt, recommendation engine | `backend/app/services/*.py` |
| **Auth** | JWT, Supabase integration, encryption, dependencies | `backend/app/auth/*.py` |
| **Models** | SQLAlchemy ORM entities | `backend/app/models/models.py` |
| **Schemas** | Pydantic request/response models | `backend/app/schemas/schemas.py` |
| **Frontend Pages** | Next.js App Router route segments | `frontend/src/app/*/page.tsx` |
| **Frontend Components** | Reusable React components | `frontend/src/components/*.tsx` |
| **Frontend Store** | Zustand global state (persisted) | `frontend/src/stores/app-store.ts` |
| **Frontend API Client** | Axios HTTP client + hooks | `frontend/src/lib/api.ts`, `frontend/src/lib/hooks.ts` |
| **ML Models** | GraphSAGE, TextEncoder | `ml/models/graph_sage.py`, `ml/models/text_encoder.py` |
| **ML Pipeline** | Data cleaning, validation, enrichment | `ml/pipeline/*.py` |
| **ML Flows** | Prefect workflows for scheduled ETL | `ml/flows/weekly_refresh.py` |
| **ML Scraper** | Scrapy-based Fragrantica scraper | `ml/scraper/` |
| **Infra Scripts** | Normalization, rebranding utilities | `scripts/` |
| **Internal Tools** | Diversity audit, sentinel, personality test | `internal/` |

## Pattern Overview

**Overall:** Multi-service architecture with three standalone codebases (backend, frontend, ML) connected via HTTP API and Docker Compose orchestration. The backend container mounts the `ml/` directory as a read-only volume for direct access to models and data at `/app/ml`.

**Key Characteristics:**
- **Stateless API first**: Backend runs without requiring a database connection — falls back to JSON-based catalog whenever PostgreSQL/Neo4j/Redis are offline
- **Lazy-loaded ML**: Neural engine and text encoder are initialized on first request, not at startup (`backend/app/main.py` lines 57-59)
- **Graceful degradation**: Every external dependency (DB, Neo4j, Redis, Pinecone) has a fallback path that keeps the application functional
- **Guest-first flow**: Users can complete the full quiz and receive recommendations without authentication; data is synced to server upon registration
- **Async-native**: FastAPI async lifespan, async SQLAlchemy sessions, async Redis client, async httpx for Gemini API

## Layers

**Frontend (React/Next.js):**
- Purpose: Web UI for fragrance discovery, quiz, recommendations
- Location: `frontend/`
- Contains: App Router pages, components, zustand store, API client, types
- Depends on: Backend API at `NEXT_PUBLIC_API_URL`
- Used by: End users via browser

**Backend (FastAPI):**
- Purpose: REST API providing auth, catalog, quiz, recommendations
- Location: `backend/app/`
- Contains: Routers, services, auth, ORM models, Pydantic schemas, config
- Depends on: PostgreSQL, Neo4j, Redis, Pinecone (all optional with fallbacks)
- Used by: Frontend, Postman/curl

**ML (PyTorch/PyG):**
- Purpose: Data pipeline, GraphSAGE embeddings, text encoder training/inference
- Location: `ml/`
- Contains: Models, pipeline scripts, Prefect flows, scrapers, data SSOT
- Depends on: `ml/data/scentrix_master.json` (data SSOT), Pinecone (for vector upload)
- Used by: Backend (mounted read-only at `/app/ml`)

## Data Flow

### Primary Request Path — Quiz → Recommendations

1. **Landing page** (`frontend/src/app/page.tsx`) → Hero section with video background
2. **Quiz entry** (`frontend/src/app/quiz/page.tsx`) — guest sees `StandardQuiz`, authenticated sees `FlashcardQuiz`
3. **Quiz answers stored locally** in Zustand store (`frontend/src/stores/app-store.ts`) via `addQuizResponse()`
4. **Submit ratings** via API (`frontend/src/lib/api.ts` `submitRating()` → `POST /recommendations/rate`)
5. **Fetch recommendations** via hook (`frontend/src/lib/hooks.ts` `useRecommendations()`):
   - **Guest**: `POST /recommendations/guest` — ephemeral quiz data sent as payload
   - **Authenticated**: `GET /recommendations/personalized` — server fetches from DB
6. **Backend recommendation engine** (`backend/app/services/hybrid_search.py` `HybridRecommender.get_recommendations()`):
   - Builds target profile from rated fragrances (notes, accords, families)
   - Scores candidates using rule-based weights (note_sim 0.30, accord_sim 0.20, semantic 0.15, cat_match 0.15, occ_match 0.10, popularity 0.10)
   - Applies diversity penalty for final selection of 12 recommendations
   - Falls back to "Popular Choice" if no profile exists
7. **Display** on recommendations page (`frontend/src/app/recommendations/page.tsx`) with `<FragranceCard>` components

### Adaptive Quiz Flow

1. **Start session** (`POST /fragrances/quiz/session/start`) — selects seed questions using "Olfactive Kingdoms" diversity algorithm across 18 scent kingdoms
2. **Submit answer** (`POST /fragrances/quiz/session/{id}/answer`) — stores in Redis/in-memory, syncs to PostgreSQL for authenticated users
3. **Evaluate confidence** (`POST /fragrances/quiz/session/{id}/evaluate`) — computes stability/margin/consistency/coverage scores, determines if extension questions needed
4. **Fetch next questions** (`GET /fragrances/quiz/session/{id}/next-questions`) — scores remaining catalog by uncertainty (0.6), diversity (0.3), engagement (0.1)
5. **Finalize** (`POST /fragrances/quiz/session/{id}/finalize`) — batch-upserts ratings to user profile using PostgreSQL upsert

### Catalog Load Flow

1. **Primary**: `HybridRecommender.__init__()` at module load (`backend/app/services/hybrid_search.py` line 590) — tries Pinecone, Neo4j, pre-computed embeddings
2. **On-demand**: `load_recommendation_catalog()` (`backend/app/services/catalog.py`):
   - Thread-safe double-checked locking for caching
   - Loads from Neo4j via optimized Cypher query (handles deduplication)
   - Falls back to `ml/data/scentrix_master.json` when Neo4j offline
   - Hydrates synthetic `rating`, `match_score`, pre-computed `_notes_set` and `_accords_set`

**State Management:**
- **Frontend**: Zustand store with localStorage persistence for auth tokens, quiz responses, preferences, wishlist, adaptive quiz state
- **Backend**: Module-level singletons for catalog cache (`_catalog_cache`), Neo4j driver (`_driver`), Redis client, recommender instance
- **Quiz sessions**: Redis-backed with in-memory dictionary fallback (`backend/app/services/quiz_store.py`)

## Key Abstractions

**HybridRecommender (Singleton):**
- Purpose: Unified recommendation engine with graceful fallbacks for disconnected environments
- File: `backend/app/services/hybrid_search.py` (line 45-588, instantiated at line 590)
- Pattern: Module-level singleton, lazy initialization of sub-components (Pinecone, Neo4j, SentenceTransformer)
- Key methods: `get_recommendations()` (main entry), `_query_vector_dna()` (Phase 1 recall), `_rerank_genetic_match()` (Phase 2 precision)

**SommelierService (Aethera):**
- Purpose: AI-powered atmospheric insight generation via Google Gemini 1.5 Flash
- File: `backend/app/services/sommelier.py`
- Pattern: Stateless service class instantiated as module-level `sommelier_service` singleton
- Fallback: Hardcoded atmospheric responses when API key or Gemini unavailable

**RedisCache:**
- Purpose: Async Redis wrapper for recommendation caching
- File: `backend/app/cache.py`
- Pattern: Lazy Redis client initialization, JSON serialization, silent failure on Redis unavailability

**FragranceDataCleaner:**
- Purpose: Data validation, deduplication, note name normalization
- File: `ml/pipeline/clean.py`
- Pattern: Mapping dictionary for canonical note name resolution

## Entry Points

**Backend API:**
- Location: `backend/app/main.py`
- Triggers: `uvicorn app.main:app --host 0.0.0.0 --port 8000` (standalone) or `docker-compose up` (Docker)
- Responsibilities: Lifespan management, router registration, CORS, rate limiting, error handling, health checks

**Frontend:**
- Location: `frontend/src/app/layout.tsx` (root layout), `frontend/src/app/page.tsx` (home page)
- Triggers: `npm run dev` (dev), `npm run build && npm start` (prod), or via Docker
- Responsibilities: Font loading, global styles, providers (QueryClient, PostHog stubbed), Navbar, PageTransition, CookieBanner

**ML Scripts:**
- Models: `python -m ml.models.graph_sage` (CLI), `python -m ml.models.text_encoder` (CLI)
- Pipeline: `python -m ml.pipeline.clean` (data cleaning), `python -m ml.pipeline.dataset_gate` (validation)
- Flows: `python -m ml.flows.weekly_refresh` (Prefect)
- Scraper: `python -m ml.scraper.run_scraper` (Scrapy)

## Architectural Constraints

- **Threading:** Single-threaded async event loop with thread-based offloading for synchronous Neo4j calls (`asyncio.to_thread` in `catalog.py`). ML model inference is lazy and runs in-process (no worker isolation).
- **Global state:** Multiple module-level singletons across the backend: `recommender` (`hybrid_search.py:590`), `sommelier_service` (`sommelier.py:111`), `_catalog_cache` (`catalog.py:16`), `_driver` (`catalog.py:17`), `cache` (`cache.py:47`), `limiter` (`limiter.py`), `settings` (`config.py:127`).
- **Circular imports:** Avoided via lazy imports inside function bodies (e.g., `from app.services.sommelier import sommelier_service` inside route handler at `recommendations.py:294`).
- **ML import from backend:** Backend imports ML code at runtime via `from ml.models.text_encoder import TextEncoder` inside `HybridRecommender._get_encoder()` — only works because `ml/` is mounted inside the Docker container.

## Anti-Patterns

### Dead Endpoint Code

**What happens:** `recommend_by_text()` and `recommend_by_profile()` in `backend/app/routers/fragrances.py` immediately raise HTTP 503. All code below is unreachable. These appear to be scaffolding from a previous design.
**Why it's wrong:** Dead code creates confusion and suggests incomplete refactoring.
**Do this instead:** Remove unreachable endpoint code or wire it to the working `HybridRecommender` service.

### Startup Warmup Commented Out

**What happens:** `backend/app/main.py` lines 57-59 comment out `warmup_neural_engine()` and `asyncio.create_task(load_recommendation_catalog_async())`. The first user request pays the cold-start latency for loading catalog + ML model.
**Why it's wrong:** First-request latency spikes create poor UX for real users.
**Do this instead:** Re-enable background warmup on startup, or implement a health-check-triggered warmup in the Docker Compose health check.

### Module-Level Recommender with Side Effects

**What happens:** `HybridRecommender.__init__()` at `hybrid_search.py:590` runs eagerly at module import time — connects to Pinecone, Neo4j, loads embeddings. This blocks the import of any file that imports `recommender`.
**Why it's wrong:** Import-time side effects make testing difficult and slow down application startup.
**Do this instead:** Use a factory function or lazy proxy that initializes sub-components on first use.

## Error Handling

**Strategy:** Graceful degradation with fallbacks at every layer.

**Patterns:**
- Database session dependency yields `None` when DB is offline — routers check and skip DB operations (`backend/app/database.py:43-44`)
- All external service calls wrapped in try/except with silent fallback to defaults
- Unified error response format via `StandardResponse` with `status: "success" | "error"` envelope
- Global exception handlers for HTTPException (returns JSON) and generic Exception (500 with logging)

## Cross-Cutting Concerns

**Logging:** Python `logging` module with `Loguru`-style format. Sentry for error tracking when `SENTRY_DSN` configured. Memory profiling via `psutil` in recommendation endpoints.

**Validation:** Pydantic v2 schemas for all API inputs. SQLAlchemy ORM with typed columns. Field validators for database URL normalization (`config.py:111-124`). Pydantic `AliasChoices` for flexible env var names.

**Authentication:** Dual auth system — local JWT (bcrypt + python-jose) and Supabase JWT. Dependencies provide `get_current_user_id` (requires auth) and `get_optional_user_id` (guest-friendly). Frontend stores token in localStorage and syncs to cookie for Next.js middleware.

**Rate Limiting:** `slowapi` with per-endpoint limit decorators (e.g., `30/minute` on quiz start, `20/minute` on answer submit).

**CORS:** Configured for localhost:3000 and production Vercel domain (`scentrix-one.vercel.app`).

---

*Architecture analysis: 2026-05-21*
