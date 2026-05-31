# Scentrix Backend API

FastAPI-based REST API for fragrance discovery, direct rating onboarding, and state-driven recommendation serving.

## What It Does

- User authentication (local + Supabase JWT) with PII encryption at rest
- Fragrance catalog search and detail from Neo4j knowledge graph
- State-driven 5-state recommendation dispatcher (Cold Exploration → Taste Initialising → Taste Active → Taste Mature)
- Direct rating via Star button on FragranceCards — replaces quiz as primary initialization path
- Legacy adaptive quiz (implemented but superseded — quiz ratings never reach the recommendation pipeline)
- Lead capture and GDPR data deletion
- Sommelier AI insight generation for fragrance collections

## Stack

- **Framework:** FastAPI with Uvicorn
- **Databases:** PostgreSQL (auth, ratings, saved fragrances), Neo4j (knowledge graph, catalog)
- **Cache:** Redis (recommendation caching)
- **Auth:** Supabase JWTs verified by FastAPI, with local fallback
- **ML Integration:** Optional — TextEncoder (Sentence-Transformers) and Pinecone vector index loaded on demand

## Local Development

```bash
# Install dependencies
pip install -e ".[dev,runtime,ml]"

# Run dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest --cov=app

# Lint
ruff check . --fix
mypy .
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app instance, lifespan, routes
│   ├── config.py            # Pydantic settings (env-based)
│   ├── routers/             # auth, fragrances, recommendations, quiz, users, leads
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # catalog, graph, dispatcher, feature_based, popularity, gs_embeddings, hybrid_search, quiz_store, supabase_auth, sommelier
│   ├── auth/                # JWT, encryption, dependencies
│   ├── database.py          # Async SQLAlchemy engine + session
│   ├── cache.py             # Redis cache client
│   └── limiter.py           # Rate limiting
├── tests/                   # Pytest test suite
├── migrations/              # Alembic DB migrations
├── Dockerfile
├── pyproject.toml
├── ruff.toml
└── mypy.ini
```

## API Routes

| Prefix | Endpoints | Description |
|--------|-----------|-------------|
| `/auth` | register, login, refresh, logout, me | User auth |
| `/fragrances` | catalog, search, detail, recommend/interactions | Fragrance discovery |
| `/recommendations` | rate, batch-rate, guest, personalized, sommelier/insight | Recommendations |
| `/fragrances/quiz/session` | start, answer, finalize, evaluate, next-questions | Adaptive quiz |
| `/users` | profile, preferences, ratings, saved, delete | User management |
| `/leads` | capture, feed | Lead capture |

See `/docs` when the backend is running for OpenAPI documentation.

## Service Architecture

See [ARCHITECTURE-FREEZE.md](../ARCHITECTURE-FREEZE.md) for the canonical 5-state dispatch architecture.

| Service | Role |
|---------|------|
| `dispatcher.py` | 5-state dispatcher — routes requests based on `rating_count` |
| `gs_embeddings.py` | GraphSAGE centroid + KNN retrieval on precomputed Jaccard embeddings |
| `feature_based.py` | Accord/note overlap scoring from rated items |
| `popularity.py` | Global popularity ranking (State 0 fallback) |
| `hybrid_search.py` | Legacy hybrid search (retained as fallback) |
| `quiz_store.py` | Quiz session management (superseded — ratings never reach recommendations) |

## Configuration

Key environment variables (see `.env.example`):

- `DATABASE_URL` — PostgreSQL connection string (asyncpg)
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` — Knowledge graph
- `REDIS_URL` — Recommendation cache
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` — Auth
- `JWT_SECRET_KEY` — Local token signing
- `DATA_ENCRYPTION_KEY` — AES-256 Fernet key for PII
- `GOOGLE_API_KEY` — Gemini for Sommelier insights
