# AGENTS.md (Scentrix)

Multi-service fragrance discovery platform pivoted into a **cold-start recommendation research platform** (MEXT research plan, July 2026). E2E pipeline is broken — parts exist in isolation, full quiz → GraphSAGE → recommendation flow never connected.

## Services

| Dir | Tech | Purpose | Entrypoint |
|-----|------|---------|------------|
| `backend/` | FastAPI (Python 3.11+) | REST API | `app/main.py` |
| `frontend/` | Next.js 16, React 19, Tailwind v4 | Web UI (App Router) | `src/app/` |
| `ml/` | PyTorch, PyG, Sentence-Transformers | GraphSAGE, embeddings, data pipeline | `ml/models/` |

## Quick commands (use root Makefile)

```
make up              # docker-compose up -d (postgres, neo4j, redis, backend, frontend)
make down            # docker-compose down
make logs            # docker-compose logs -f
make migrate         # alembic upgrade head (via Docker)
make seed            # python -m scripts.seed_data (via Docker)
make test-backend    # pytest --cov=app (via Docker)
make lint            # ruff + mypy (backend) + eslint (frontend)
make enrich          # Clean dataset + update Neo4j (via Docker)
make audit           # Run olfactive diversity audit
make clean           # docker-compose down -v + rm __pycache__/node_modules/.next
```

## Known breakages

- **Missing `celery_app.py`**: Referenced in `backend/README.md` but never created. `celery>=5.3.6` is a dependency but no code imports it and no worker container exists in docker-compose.
- **No `npm test` script**: `make test-frontend` runs `npm test` which fails. Use `npm run test:e2e` (Playwright) instead.
- **`ml/training/` never created**: Documented in `ml/README.md` but directory doesn't exist.
- **Startup warmup commented out**: `backend/app/main.py:57-59` — neural engine and catalog never preloaded on startup (lazy-loaded on first request).

## Backend (Python)

- **Install**: `cd backend && pip install -e ".[dev,runtime,ml]"`
- **Run standalone**: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- **Lint/type**: `ruff check app/` / `ruff format --check app/` / `mypy app/`
- **Test**: `pytest tests/` — tests use **SQLite in-memory** via `conftest.py` (`sqlite+aiosqlite:///:memory:`). CI needs postgres+redis services.
- **Test env vars**: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `SENTRY_DSN=""`
- **CI pipeline**: ruff → mypy → pytest (runs on push to main/develop/phase/**)
- **Ruff config**: `backend/ruff.toml` — line-length 100, target py311, select E/W/F/I/C/B/UP, ignore E501/B008
- **Mypy**: `check_untyped_defs`, `warn_return_any`, ignores `neo4j.*`/`pinecone.*`/`ml.*`
- **`ml_enabled`** defaults to `False` in `app/config.py` (`Settings.ml_enabled`)

## Frontend (TypeScript/Next.js)

- Install: `cd frontend && npm ci`
- **Commands**: `npm run dev` / `npm run type-check` (tsc --noEmit) / `npm run lint` (eslint . --fix) / `npm run format` (prettier --write .)
- **E2E**: `npm run test:e2e` / `npm run test:e2e:ui` (Playwright, 5 browser projects: chromium, firefox, webkit, Mobile Chrome, Mobile Safari)
- **API mocking**: MSW handlers at `frontend/tests/mocks/handlers.ts` — covers auth, fragrances, recommendations, quiz, wishlist
- **CI pipeline**: eslint → type-check → build → e2e (chromium only)

## ML pipeline

- Data SSOT: `ml/data/scentrix_master.json` (the sole source of truth)
- GraphSAGE: `ml/models/graph_sage.py` (2-layer, mean aggregation, 128-dim output) — currently uses random node split, **not** cold-start split
- Text encoder: `ml/models/text_encoder.py` (SentenceTransformer `all-MiniLM-L6-v2`)
- Graph validation: `python -m ml.tests.test_graph --profile local`
- Integration test: `python -m ml.tests.test_integration --cleanup --profile local`
- Backend container mounts `./ml` at `/app/ml` (no `:ro` flag)

## Architecture notes

- Backend container mounts: `./backend` → `/app`, `./ml` → `/app/ml`
- Docker service deps: `backend` waits for postgres+neo4j+redis; `frontend` waits for backend
- SSOT is JSON file — system has fallback paths for DB outages (catalog from JSON, graceful degrades for Neo4j/Redis)
- `.github/prompts/` contains brand/persona prompts (`architect-neural.md`, `cinematic-ui.md`, `persona-aethera.md`) — read before implementing frontend features
- Secrets from `.env.example` (repo root) or `backend/.env`

## Repo conventions

- Alembic migrations: `backend/app/migrations/` (configured in `backend/alembic.ini`)
- Python: ruff format + mypy strict. No `any` types.
- API changes must update both backend schemas/routes and frontend client usage
- PII (full_name, email) encrypted at rest via `backend/app/auth/encryption.py` (AES-256 Fernet)
- `.planning/` is in `.gitignore` — planning docs are local-only

## Workflow rules

- **Graphify after every task**: After completing any task (code change, fix, test, doc update), run `/graphify` to update the project knowledge graph.
- **Parallel sub-agents**: When a task can be split into independent subtasks, launch multiple sub-agents in parallel using the `task` tool. Prioritize parallelism wherever dependencies allow — but never at the cost of correctness or quality. Verify each sub-agent's output before declaring the parent task done.
