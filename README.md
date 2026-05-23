# Scentrix — Cold-Start Fragrance Recommendation Research Platform

Research platform for MEXT July 2026. User takes a quiz → GraphSAGE infers preferences → personalized niche recommendations without interaction history.

## Architecture

```
User Quiz ──→ Adaptive Confidence Scorer ──→ Quiz Embedding
                                                 ↓
scentrix_master.json ──→ Neo4j Fragrance Graph ──→ GraphSAGE (inductive inference)
                                                      ↓
                                        Popularity/Random Baselines ──→ Comparison + Significance Tests
```

## Services

| Directory | Tech | Purpose |
|-----------|------|---------|
| `backend/` | FastAPI (Python 3.11+) | REST API |
| `frontend/` | Next.js 16, React 19, Tailwind v4 | Web UI |
| `ml/` | PyTorch, PyG, Sentence-Transformers | GraphSAGE, embeddings, pipeline |

## Quick Start

```bash
make up      # Start all Docker containers (postgres, neo4j, redis, backend, frontend)
make logs    # Tail container logs
make down    # Stop all containers
```

### First-Time Setup

```bash
make migrate  # Run Alembic migrations
make seed     # Seed test data
make enrich   # Clean dataset + update Neo4j graph
```

## Commands

| Command | Description |
|---------|-------------|
| `make test-backend` | Run pytest suite (via Docker) |
| `make test-frontend` | Run Playwright E2E tests |
| `make lint` | ruff + mypy (backend), eslint (frontend) |
| `make audit` | Olfactive diversity audit |
| `make enrich` | Process dataset and update Neo4j |

## What Exists

Auth, Neo4j catalog, GraphSAGE model code, quiz endpoints, Next.js scaffold, Docker infra, graph ingestor, cleaned 4,577-fragrance dataset.

## What's Being Built (6 Phases)

1. Evaluation harness & significance testing
2. Popularity/random baselines
3. GraphSAGE inference pipeline
4. Research differentiators
5. MEXT demo preparation

## Conventions

- Python: ruff format + mypy strict. No `any`. Line-length 100.
- Tests: backend uses SQLite in-memory; frontend uses Playwright E2E + MSW mocking.
- PII encrypted at rest (`backend/app/auth/encryption.py`, AES-256 Fernet).
