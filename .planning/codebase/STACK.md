# Tech Stack: Scentrix

## Backend (Python 3.11+)
- **Framework**: FastAPI (Async)
- **Database**: 
  - PostgreSQL (via SQLAlchemy/Alembic)
  - Neo4j (via official python driver)
- **Task Queue**: Celery + Redis
- **Security**: AES-256 Fernet (DataVault) for PII encryption at rest
- **Linting**: Ruff, MyPy

## Frontend (Next.js 15+)
- **Framework**: Next.js (App Router, TypeScript)
- **Styling**: TailwindCSS (or Vanilla CSS per cinematic standards)
- **Auth**: Supabase Auth (integrated with custom backend profile sync)

## ML & AI Engine
- **Search**: Hybrid dual-vector search (Text DNA + Graph DNA)
- **Models**: Sentence-Transformers (Sentence-BERT), PyTorch Geometric (GraphSAGE)
- **Vector DB**: Pinecone
- **Persona**: Aethera (Atmospheric neural quiz)

## Infrastructure
- **Containerization**: Docker & Docker Compose
- **Monitoring**: Sentry (Error tracking), custom Sentinel (DB polling)
