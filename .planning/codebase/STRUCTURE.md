# Codebase Structure

**Analysis Date:** 2026-05-21

## Directory Layout

```
Scentrix/
├── backend/              # FastAPI backend (Python 3.11+)
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point, lifespan, router registration
│   │   ├── config.py            # Pydantic Settings from env vars
│   │   ├── database.py          # Async SQLAlchemy engine + session factory
│   │   ├── cache.py             # Async Redis client wrapper
│   │   ├── limiter.py           # SlowAPI rate limiter
│   │   ├── sentry_config.py     # Sentry error tracking init
│   │   ├── auth/
│   │   │   ├── auth.py          # JWT create/verify, password hashing
│   │   │   ├── dependencies.py  # FastAPI Depends: get_current_user_id, get_optional_user_id
│   │   │   └── encryption.py    # AES-256 Fernet for PII encryption
│   │   ├── routers/
│   │   │   ├── auth.py          # Register, login, refresh, logout
│   │   │   ├── fragrances.py    # Catalog, search, detail, interaction ingestion
│   │   │   ├── users.py         # Profile, ratings, saved fragrances, GDPR
│   │   │   ├── recommendations.py # Rate, batch-rate, guest/personalized recs, sommelier
│   │   │   ├── quiz.py          # Adaptive quiz session lifecycle
│   │   │   └── leads.py         # Shadow lead capture
│   │   ├── services/
│   │   │   ├── catalog.py       # Catalog loader (Neo4j primary, JSON fallback), thread-safe cache
│   │   │   ├── hybrid_search.py # HybridRecommender — main rec engine
│   │   │   ├── sommelier.py     # Gemini API-based "Aethera" insight service
│   │   │   ├── quiz_store.py    # Redis-backed quiz session store with in-memory fallback
│   │   │   ├── prompt_loader.py # Loads persona prompts from .github/prompts/
│   │   │   ├── supabase_auth.py # Supabase auth integration
│   │   │   ├── vault.py         # PII encryption helpers
│   │   │   └── job_store.py     # Async job store for long-running tasks
│   │   ├── models/models.py     # SQLAlchemy ORM: User, FragranceRating, SavedFragrance, RefreshToken, UserInteractionEvent
│   │   ├── schemas/schemas.py   # Pydantic v2: Auth, Fragrance, Quiz, Recommendation, Collection schemas
│   │   └── migrations/          # Alembic migration scripts
│   ├── tests/                   # Backend pytest suite
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_health.py
│   │   ├── test_adaptive_quiz.py
│   │   ├── test_recommendation_lifecycle.py
│   │   ├── test_integration.py
│   │   └── benchmark_sla.py
│   ├── Dockerfile
│   ├── pyproject.toml           # Dependencies + ruff + mypy + pytest config
│   ├── ruff.toml                # Ruff linter rules
│   └── alembic.ini             # Alembic config
│
├── frontend/              # Next.js 16 / React 19 (App Router)
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   │   ├── layout.tsx       # Root layout: fonts, providers, navbar, transitions
│   │   │   ├── page.tsx         # Landing page (Hero, HowItWorks, Families, SocialProof, CTA)
│   │   │   ├── globals.css      # Global CSS + Tailwind directives
│   │   │   ├── quiz/page.tsx    # Quiz page (StandardQuiz or FlashcardQuiz based on auth)
│   │   │   ├── recommendations/page.tsx  # Results page with FragranceCard grid
│   │   │   ├── collection/page.tsx       # User's saved fragrance collection
│   │   │   ├── fragrances/page.tsx       # Fragrance catalog browser
│   │   │   ├── families/page.tsx         # Fragrance families explorer
│   │   │   ├── families/[family]/page.tsx # Dynamic family detail page
│   │   │   ├── profile/page.tsx          # User profile page
│   │   │   ├── profile/wishlist/         # Wishlist page
│   │   │   ├── profile/history/          # History page
│   │   │   ├── auth/login/page.tsx       # Login page
│   │   │   ├── auth/register/page.tsx    # Register page
│   │   │   ├── auth/logout/page.tsx      # Logout page
│   │   │   └── internal/overseer/        # Internal admin panel
│   │   ├── components/          # Reusable React components
│   │   │   ├── Providers.tsx            # QueryClientProvider + PostHogProvider (stubbed)
│   │   │   ├── Navbar.tsx               # Top navigation bar
│   │   │   ├── HeroSection.tsx          # Landing page hero
│   │   │   ├── HowItWorks.tsx           # "How it works" section
│   │   │   ├── FragranceCard.tsx        # Fragment card for recommendation grid
│   │   │   ├── FlashcardQuiz.tsx        # Authenticated user quiz UI
│   │   │   ├── StandardQuiz.tsx         # Guest user quiz UI
│   │   │   ├── FragranceFamilies.tsx    # Family explorer component
│   │   │   ├── DiscoveryNeuralLoader.tsx # Loading animation component
│   │   │   ├── SocialProof.tsx          # Social proof section
│   │   │   ├── FinalCTA.tsx             # Call-to-action section
│   │   │   ├── VideoScrubber.tsx        # Video background scrubber
│   │   │   ├── PageTransition.tsx       # Framer motion page transition
│   │   │   ├── CookieBanner.tsx         # GDPR cookie consent banner
│   │   │   ├── ScentrixLogo.tsx         # SVG logo component
│   │   │   ├── StringTuneManager.tsx    # Font/theme tuning
│   │   │   └── PostHogPageView.tsx      # PostHog analytics (commented out)
│   │   ├── lib/
│   │   │   ├── api.ts           # Axios client + all API methods
│   │   │   ├── hooks.ts         # React Query hooks (useRecommendations, useLogin, etc.)
│   │   │   ├── quizTheme.ts     # Fragrance palette/theme mapping
│   │   │   └── family-mapping.ts # Fragrance family data mappings
│   │   ├── stores/
│   │   │   └── app-store.ts     # Zustand store: quiz, auth, preferences, wishlist, adaptive quiz
│   │   ├── types/
│   │   │   ├── collection.ts    # Collection-related type definitions
│   │   │   ├── string-tune.d.ts # Font config type declarations
│   │   │   └── dom.d.ts         # DOM extension type declarations
│   │   └── styles/              # Additional stylesheets
│   ├── middleware.ts            # Next.js middleware: auth redirect logic
│   ├── tests/
│   │   ├── e2e/                 # Playwright E2E tests
│   │   ├── mocks/               # MSW mock handlers
│   │   ├── fixtures.ts          # Test fixtures
│   │   └── visual-regression.spec.ts  # Visual regression tests
│   ├── public/                  # Static assets (videos, images, favicon)
│   ├── next.config.ts
│   ├── tsconfig.json            # Path alias @/ → ./src/
│   ├── tailwind.config.ts
│   ├── eslint.config.mjs
│   ├── playwright.config.ts
│   └── Dockerfile
│
├── ml/                    # ML / Data Science (PyTorch, PyG)
│   ├── models/
│   │   ├── graph_sage.py        # GraphSAGE model (2-layer, mean aggregation, 128-dim hidden)
│   │   ├── graph_sage_v2.py     # GraphSAGE v2 variant
│   │   └── text_encoder.py      # SentenceTransformer (all-MiniLM-L6-v2) + Pinecone upload
│   ├── pipeline/
│   │   ├── clean.py             # FragranceDataCleaner — dedup, rename, normalize
│   │   ├── dataset_gate.py      # Dataset readiness validator (min rows, brands, etc.)
│   │   ├── filter_elite.py      # Elite fragrance filtering
│   │   ├── diversity_audit.py   # Olfactive diversity audit
│   │   └── import_licensed_feed.py # Licensed data feed import
│   ├── flows/
│   │   ├── weekly_refresh.py    # Prefect workflow: scrape → clean → ingest → validate
│   │   └── PREFECT_WORKFLOW.md  # Prefect workflow documentation
│   ├── scraper/                 # Scrapy-based Fragrantica scraper
│   │   ├── run_scraper.py
│   │   ├── fragrantica.py
│   │   ├── scrapy.cfg
│   │   └── ...
│   ├── data/
│   │   ├── scentrix_master.json # SSOT: ~24k fragrances (canonical dataset)
│   │   ├── embeddings.npy       # Pre-computed embeddings (numpy)
│   │   └── embedding_index.json # ID-to-index mapping for embeddings
│   └── tests/
│       ├── test_graph.py        # Graph validation tests
│       └── test_integration.py  # ML pipeline integration tests
│
├── scripts/               # Utility scripts
│   ├── normalize_dataset.py     # Dataset normalization utility
│   └── perform_rebrand.py       # Rebranding/rename utility
│
├── internal/              # Internal tooling (not part of production)
│   ├── diversity_audit.py       # Audit fragrance dataset diversity
│   ├── personality_test.py      # Personality/quiz testing tool
│   └── sentinel.py              # Monitoring/health sentinel
│
├── .github/
│   ├── prompts/                 # Persona prompts (aethera, architect, cinematic)
│   ├── workflows/               # GitHub Actions CI/CD
│   └── copilot-instructions.md
│
├── docker-compose.yml           # 5 services: postgres, neo4j, redis, backend, frontend
├── Makefile                     # up, down, logs, migrate, seed, test-backend, lint, etc.
├── AGENTS.md                    # Project overview for AI agents
├── DESIGN.md                    # Design decisions documentation
├── CHANGELOG.md                 # Release changelog
└── README.md                    # Project README
```

## Directory Purposes

**`backend/app/routers/`:**
- Purpose: HTTP endpoint definitions — thin orchestration layer that delegates to services
- Contains: 6 router files, each with an `APIRouter` instance registered in `main.py`
- Key files: `fragrances.py` (640 lines, largest router), `quiz.py` (685 lines, adaptive quiz lifecycle)

**`backend/app/services/`:**
- Purpose: Business logic, data access, external service integration
- Contains: 8 service modules plus `__init__.py`
- Key files: `hybrid_search.py` (590 lines, the recommendation engine), `catalog.py` (208 lines, Neo4j + JSON catalog loader)

**`backend/app/auth/`:**
- Purpose: Authentication and authorization primitives
- Contains: JWT token handling, Supabase integration, encryption, FastAPI dependency injection

**`frontend/src/app/`:**
- Purpose: Next.js App Router route segments — each subdirectory is a route
- Contains: 11 route segments plus `layout.tsx`, `page.tsx`, `globals.css`
- Pattern: Each route directory `[name]/` has `page.tsx` (client component) and optional `[name].css`

**`frontend/src/components/`:**
- Purpose: Reusable React components used across multiple pages
- Contains: 18 `.tsx` components, 1 `.css` file
- Pattern: Named exports, all components are `'use client'` (client-side interactive)

**`frontend/src/lib/`:**
- Purpose: Shared utilities, API client, custom hooks, theme constants
- Contains: 4 files — `api.ts` (Axios), `hooks.ts` (React Query), `quizTheme.ts`, `family-mapping.ts`

**`frontend/src/stores/`:**
- Purpose: Global state management using Zustand
- Contains: 1 file — `app-store.ts` with full application state

**`ml/models/`:**
- Purpose: ML model definitions + standalone training/embedding scripts
- Contains: 3 model files with `__main__` blocks for CLI execution

**`ml/pipeline/`:**
- Purpose: Data processing and validation pipeline
- Contains: 5 scripts for cleaning, validation, filtering, auditing, and import

**`ml/data/`:**
- Purpose: Static data assets — the single source of truth
- Contains: `scentrix_master.json` (~24k fragrances), pre-computed embeddings, index mapping

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: FastAPI application — lifespan, router registration, error handlers
- `frontend/src/app/layout.tsx`: Next.js root layout — providers, navbar, global styles
- `frontend/src/app/page.tsx`: Home/landing page composition
- `ml/models/graph_sage.py`: GraphSAGE CLI entry (`if __name__ == "__main__"`)
- `ml/models/text_encoder.py`: Text encoder CLI entry (`if __name__ == "__main__"`)
- `ml/flows/weekly_refresh.py`: Prefect workflow entry point
- `ml/scraper/run_scraper.py`: Scrapy scraper CLI entry

**Configuration:**
- `backend/pyproject.toml`: Python dependencies, ruff config, mypy config, pytest config
- `backend/ruff.toml`: Ruff-specific overrides
- `backend/app/config.py`: Pydantic Settings — all env var definitions with defaults
- `frontend/tsconfig.json`: TypeScript config with `@/` path alias
- `frontend/next.config.ts`: Next.js compilation configuration
- `frontend/eslint.config.mjs`: ESLint flat config
- `frontend/.prettierrc`: Prettier formatting rules
- `docker-compose.yml`: All service definitions, networking, volumes, health checks
- `Makefile`: Developer workflow commands

**Core Logic:**
- `backend/app/services/hybrid_search.py`: `HybridRecommender` — the main recommendation engine
- `backend/app/services/catalog.py`: Catalog loading with Neo4j/JSON fallback
- `backend/app/services/sommelier.py`: Gemini API-powered "Aethera" insight generator
- `backend/app/services/quiz_store.py`: Redis/in-memory quiz session storage
- `backend/app/routers/quiz.py`: Adaptive quiz lifecycle (start, answer, evaluate, next-questions, finalize)
- `backend/app/routers/recommendations.py`: Rating submission, guest/personalized recommendations
- `backend/app/auth/auth.py`: JWT token creation, verification, bcrypt password hashing
- `backend/app/auth/dependencies.py`: FastAPI dependency injection for auth
- `frontend/src/lib/api.ts`: All backend API calls via Axios
- `frontend/src/lib/hooks.ts`: React Query hooks for data fetching
- `frontend/src/stores/app-store.ts`: Zustand store with localStorage persistence

**Testing:**
- `backend/tests/`: Pytest suite (6 test files + conftest.py)
- `frontend/tests/e2e/`: Playwright E2E tests
- `frontend/tests/mocks/`: MSW mock handlers for API testing
- `ml/tests/`: ML-specific tests (graph validation, integration)

## Naming Conventions

**Files:**
- Python: `snake_case.py` — e.g., `hybrid_search.py`, `quiz_store.py`, `prompt_loader.py`
- TypeScript/React: `PascalCase.tsx` for components — e.g., `FragranceCard.tsx`, `Navbar.tsx`
- TypeScript/React: `camelCase.ts` for utilities — e.g., `api.ts`, `hooks.ts`, `quizTheme.ts`
- CSS: `camelCase.css` — e.g., `quiz.css`, `profile.css`, `family-mapping.ts`
- Config files: standard formats — `pyproject.toml`, `tsconfig.json`, `ruff.toml`, `.prettierrc`

**Directories:**
- Python packages use `snake_case` — e.g., `app/routers/`, `app/services/`, `app/auth/`
- Next.js route segments use `kebab-case` — e.g., `auth/login/`, `profile/wishlist/`, `families/[family]/`
- ML directories use `snake_case` — e.g., `ml/pipeline/`, `ml/flows/`, `ml/scraper/`

**Functions/Methods:**
- Python: `snake_case` — e.g., `load_recommendation_catalog()`, `get_current_user_id()`, `_compute_confidence_score()`
- TypeScript: `camelCase` — e.g., `submitRating()`, `addQuizResponse()`, `getGuestRecommendations()`

**Types:**
- Python: PascalCase for classes — `HybridRecommender`, `FragranceDataCleaner`, `SommelierService`
- Python: PascalCase for Pydantic models — `RecommendationJob`, `FragranceDetail`, `QuizSessionStartResponse`
- TypeScript: PascalCase for interfaces — `FragranceRecommendation`, `QuizResponse`, `AdaptiveQuizState`
- TypeScript: PascalCase for enums — implicit via string literals in the codebase

## Where to Add New Code

**New Feature (Backend API):**
1. Define Pydantic schemas in `backend/app/schemas/schemas.py`
2. Implement business logic in a new service file in `backend/app/services/`
3. Create/update router in `backend/app/routers/`
4. Register router in `backend/app/main.py`
5. Add tests in `backend/tests/`

**New Feature (Frontend):**
1. Create route page in `frontend/src/app/[route]/page.tsx`
2. Create components in `frontend/src/components/`
3. Add API methods in `frontend/src/lib/api.ts`
4. Add hooks in `frontend/src/lib/hooks.ts`
5. Add state in `frontend/src/stores/app-store.ts`
6. Add types in `frontend/src/types/`
7. Add E2E tests in `frontend/tests/e2e/`

**New Component/Module:**
- UI components: `frontend/src/components/[ComponentName].tsx` (PascalCase)
- Library utilities: `frontend/src/lib/[name].ts` (camelCase)
- Backend services: `backend/app/services/[name].py` (snake_case)
- Backend routers: `backend/app/routers/[name].py` (snake_case), register in `main.py`

**ML Additions:**
- Models: `ml/models/[name].py` (snake_case)
- Pipeline steps: `ml/pipeline/[name].py` (snake_case)
- Data: `ml/data/[name].json` or `.npy`
- Tests: `ml/tests/test_[name].py`
- Flows: `ml/flows/[name].py` (snake_case)

**Utilities:**
- Shared helpers: `frontend/src/lib/` for frontend, `backend/app/services/` for backend
- Internal tooling: `internal/` directory
- Scripts: `scripts/` directory

## Special Directories

**`.github/prompts/`:**
- Purpose: Persona/agent prompts used by the Digital Sommelier (Aethera, architect prompts)
- Generated: No
- Committed: Yes

**`ml/data/`:**
- Purpose: Dataset SSOT and pre-computed ML artifacts
- Contains: `scentrix_master.json` (canonical 24k fragrance dataset), `embeddings.npy` (pre-computed vectors), `embedding_index.json` (ID-to-index lookup)
- Generated: `embeddings.npy` and `embedding_index.json` are generated by ML pipeline
- Committed: Yes

**`frontend/public/`:**
- Purpose: Static assets served directly by Next.js
- Contains: Videos, images, SVG favicon
- Generated: No
- Committed: Yes

**`backend/app/migrations/`:**
- Purpose: Alembic database migration scripts
- Generated: Yes (by `alembic revision --autogenerate`)
- Committed: Yes

**`.planning/`:**
- Purpose: GSD planning artifacts generated by the AI workflow system
- Generated: Yes (by `/gsd-map-codebase`, `/gsd-plan-phase`, etc.)
- Committed: Yes

**`graphify-out/`:**
- Purpose: Knowledge graph output from the graphify skill
- Generated: Yes
- Committed: Likely yes

---

*Structure analysis: 2026-05-21*
