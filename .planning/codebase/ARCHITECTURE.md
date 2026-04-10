# System Architecture

## Pattern & Layers
- **Client-Server Separation**: Hard decoupled Next.js SSR/CSR frontend relying on REST HTTP endpoints from Python FastAPI.
- **Backend Service Layer**: Clean architecture separating `schemas`, `services`, and `main` entrypoints.
- **ML Pipeline Orchestration**: Modular training/generation logic partitioned in `/ml/pipeline` mapped to Neo4j/Pinecone integrations.

## Data Flow
1. Client issues request to FastAPI via Next.js server actions or React Query.
2. FastAPI processes via Pydantic (`app/schemas/schemas.py`), passes to business logic (`app/services/catalog.py`).
3. Services interact with DB (Postgres) or Vector store (Pinecone) / Graph (Neo4j).
4. Long-running ingestion or synthetic generation runs async via Celery/Redis.

## Directory Boundaries
- `/frontend` completely isolated via `package.json` boundaries.
- `/backend` isolated via `pyproject.toml`.
- `/ml` isolated but dependent on backend data models, executing via standalone `flows` and `generate_synthetic_data.py`.
