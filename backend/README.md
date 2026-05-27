# Scentrix Backend API

FastAPI-based REST API for fragrance discovery, quiz onboarding, and recommendation serving.

## What It Does

- User authentication (local + Supabase JWT) with PII encryption at rest
- Fragrance catalog search and detail from Neo4j knowledge graph
- Adaptive confidence-scored onboarding quiz
- Hybrid recommendation engine (rule-based note/accord matching + optional semantic embeddings)
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
│   ├── services/            # catalog, graph, hybrid_search, quiz_store, supabase_auth, sommelier
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

## Configuration

Key environment variables (see `.env.example`):

- `DATABASE_URL` — PostgreSQL connection string (asyncpg)
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` — Knowledge graph
- `REDIS_URL` — Recommendation cache
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` — Auth
- `JWT_SECRET_KEY` — Local token signing
- `DATA_ENCRYPTION_KEY` — AES-256 Fernet key for PII
- `GOOGLE_API_KEY` — Gemini for Sommelier insights
