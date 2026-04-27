# AGENTS.md (Scentrix)

This repo is a multi-service app:
- `backend/`: FastAPI API + Celery worker (Python)
- `frontend/`: Next.js app (TypeScript)
- `ml/`: ML + data pipeline code (invoked by backend/tasks or run manually)

## 🛡️ Security & Privacy (Hardening v1.0)
- **PII Encryption**: User `full_name` and `email` are encrypted at rest using AES-256 (via `backend/app/auth/encryption.py`).
- **Data Policy**: Decryption happens on-the-fly in API routers (`auth.py`, `users.py`).
- **Neural Timeouts**: All LLM-backed services have 10s circuit breakers and 5s timeouts.

## 🏺 Feature Map
- **Discovery Engine**: Adaptive neural quiz with "Aethera" atmospheric persona (`.github/prompts/persona-aethera.md`).
- **Virtual Scent Shelf**: Collection management with personal olfactory notes and shelf-based visualization.
- **Universal Context**: All session logic and user profile memory synchronized via `graphify-out/graph.json`.

Prefer commands in the root `Makefile` for day-to-day dev.

## Quick commands (recommended)

- Start the whole stack (Postgres, Neo4j, Redis, API, worker, frontend):
  - `make up`
- Logs:
  - `make logs`
- Stop everything:
  - `make down`
- DB migrations:
  - `make migrate`
- Seed dev/test data:
  - `make seed`
- Backend tests (runs inside Docker backend container):
  - `make test-backend`
- Lint (backend ruff+mypy in Docker, frontend eslint locally):
  - `make lint`
- ML dataset enrichment + Neo4j update (inside Docker backend container):
  - `make enrich`

See: [Makefile](Makefile) and [docker-compose.yml](docker-compose.yml).

## Repo boundaries (where to change what)

- Backend API entrypoint: `backend/app/main.py`
- Backend routes: `backend/app/routers/`
- Backend DB/models/schemas/services/tasks: `backend/app/{models,schemas,services,tasks}/`
- Alembic migrations: `backend/app/migrations/` (configured in [backend/alembic.ini](backend/alembic.ini))
- Frontend app code: `frontend/src/`
- ML pipeline + graph logic: `ml/` (this is the canonical ML tree; `backend/ml/` is not used)
- Internal Utilities: `internal/tools/` (integration tests, persona simulations)
- Historical Records: `docs/history/` (deployment ledgers, audit logs)

More detail:
- Backend docs: [backend/README.md](backend/README.md)
- ML docs: [ml/README.md](ml/README.md)

## Tooling conventions

### Backend (Python)

- Python version: 3.11+ (see [backend/pyproject.toml](backend/pyproject.toml))
- Lint/format:
  - `ruff check ...`
  - `ruff format ...` (CI uses `ruff format --check`)
- Types: `mypy app/`
- Tests: `pytest` (asyncio enabled)

CI is the best “source of truth” for exact gates:
- [Backend + frontend CI](.github/workflows/ci.yml)
- [Backend checks](.github/workflows/backend-test.yml)

### Frontend (Node/Next.js)

- Dev server: `cd frontend && npm run dev`
- Lint: `cd frontend && npm run lint`
- Type-check: `cd frontend && npm run type-check`
- E2E: `cd frontend && npm run test:e2e`

Note: the root `Makefile` target `make test-frontend` runs `npm test`, but `frontend/package.json` does not define a `test` script. Prefer `npm run test:e2e` / `npm run test:e2e:ui` instead.

## Running locally without Docker (backend)

When you need to run the backend directly (e.g., faster iteration than Docker):

- Install:
  - `cd backend && pip install -e ".[dev,runtime,ml]"`
- Run:
  - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

You’ll need env vars from `.env.example` (repo root) or `backend/.env`.

## Environment + services

- Docker services: `postgres`, `neo4j`, `redis`, `backend`, `worker`, `frontend` (see [docker-compose.yml](docker-compose.yml))
- The backend container mounts:
  - `./backend` at `/app`
  - `./ml` at `/app/ml` (read-only)

## When changing code

- If you change API contracts, update both:
  - backend schemas/routes, and frontend client usage.
- Add/adjust tests when behavior changes (pytest for backend; Playwright for e2e if UI flow changes).

## 🦾 Universal AI Context (Portability)

To maintain consistency across different devices and AI sessions, this repo follows a **Context Linkage** protocol:

1.  **Codebase Map:** `graphify-out/graph.json` contains the structural mapping of the codebase. AI agents should load this to understand architecture.
2.  **AI Instructions:** Always read `.github/prompts/` before implementing new features:
    *   `persona-aethera.md`: Atmospheric brand voice.
    *   `architect-neural.md`: Neural engine constraints.
    *   `cinematic-ui.md`: WOW-factor design standards.
3.  **Master Truth:** This file (`AGENTS.md`) is the final authority on project boundaries and dev workflows.
