# Scentrix Backend API

FastAPI-based REST API for the Scentrix fragrance discovery platform.

## Architecture

- **Framework:** FastAPI with Uvicorn
- **Database:** Supabase for auth/profile/preference data; Neo4j for knowledge graph data
- **Cache/Queue:** Redis (Celery broker, recommendations cache)
- **Vector DB:** Pinecone (derived fragrance embeddings)
- **Auth:** Supabase JWTs verified by FastAPI
- **Task Queue:** Celery (async recommendation generation, GDPR deletion, cache warmups)

## Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest --cov=app

# Lint and format
ruff check . --fix
mypy .
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app instance
│   ├── config.py            # Configuration (settings)
│   ├── routers/             # Route handlers (auth, fragrances, recommendations, ratings)
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── tasks/               # Celery async tasks
│   └── core/                # Shared utilities (auth, db, neo4j, etc.)
├── tests/                   # Pytest test suite
├── migrations/              # Alembic DB migrations
├── Dockerfile               # Container image
├── pyproject.toml          # Dependencies and config
├── ruff.toml               # Linting rules
├── mypy.ini                # Type checking rules
└── README.md
```

## API Endpoints

See the generated OpenAPI docs at `/docs` when the backend is running.

### Health Check
```
GET /health
{
  "status": "ok"
}
```

## Configuration

All configuration is loaded from environment variables. See `.env.example` for required keys.

Key settings:
- `DATABASE_URL` — PostgreSQL connection string for the relational store; in production this can point to Supabase Postgres
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` — Auth/profile/preference integration
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` — Knowledge graph
- `REDIS_URL` — Cache and Celery broker
- `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` — Vector embeddings
- `JWT_SECRET_KEY` — Legacy/local token signing during migration

## Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_health.py

# Run tests matching pattern
pytest -k "test_auth"
```

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add user_table"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

## Celery Tasks

Async tasks are executed by Celery workers:

```bash
# Start Celery worker (in separate terminal)
celery -A app.celery_app worker --loglevel=info

# Monitor tasks
celery -A app.celery_app events
```

## Security

- All endpoints require HTTPS in production
- Input validation and sanitization on all endpoints
- Rate limiting on auth and search endpoints
- SQL injection protection via SQLAlchemy ORM
- CORS configured per environment

## Deployment

Target production deployment keeps FastAPI on Railway, the frontend on Vercel,
and user-owned data in Supabase. The repo-level architecture note lives in
[docs/architecture.md](../docs/architecture.md).

## Contributing

- Follow PEP 8 style guide (enforced by ruff)
- Add type hints to all functions
- Write tests for new endpoints
- Update this README if adding new modules
