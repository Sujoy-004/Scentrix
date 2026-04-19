# ScentScape - AI-Driven Fragrance Discovery & Personalization

An intelligent fragrance recommendation platform combining knowledge graphs, graph neural networks, and natural language processing to help users discover their signature scent.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)

### Local Development

```bash
# Start all services (PostgreSQL, Neo4j, Redis, Backend API, Celery worker)
make up

# Seed test data
make seed

# Run tests
make test-backend
make test-frontend

# View logs
make logs

# Stop services
make down
```

## Project Structure

```
scentscape/
├── frontend/          # Next.js 14 frontend (TypeScript, Tailwind)
├── backend/           # FastAPI backend (Python 3.11)
├── ml/                # ML pipeline (GraphSAGE, Sentence-BERT)
├── infra/             # Infrastructure-as-Code (Terraform)
├── docs/              # Documentation
├── docker-compose.yml # Local dev services
└── Makefile          # Development commands
```

## Architecture

### Target production flow

User -> Vercel frontend -> FastAPI on Railway -> Supabase for auth/profile/
preference data only -> background workers and caches -> Pinecone and Neo4j for
derived recommendation work.

### Responsibilities

- **Frontend:** Next.js 14 App Router, Tailwind CSS, Zustand, React Query, Vercel
- **Backend:** FastAPI on Railway, request orchestration, API validation, and
	background job dispatch
- **User data:** Supabase for authentication, profile state, preferences, and
	consent/deletion flows
- **Async layer:** Celery + Redis for warmups, scoring jobs, and cached reads
- **Derived stores:** Pinecone for embeddings and Neo4j for knowledge graph data
- **ML:** GraphSAGE, Sentence-BERT, and ranking models for derived signals

## Features

- **Personalized Discovery:** Rate reference fragrances to build a taste profile
- **Text-Based Search:** "Smoky vanilla with leather notes"
- **Knowledge Graph:** 1,000+ fragrances with note breakdowns and accords
- **Visual Analytics:** Note pyramids, similarity scores, accord breakdowns
- **Collection Management:** Save and organize fragrances you love
- **GDPR Compliant:** One-click data deletion, no unconsented training data use

## Documentation

- [Target Architecture](./docs/architecture.md)

## Development

Each phase of development occurs on a dedicated branch:
- `main` — Production release
- `develop` — Integration branch (staging)
- `phase/0-bootstrap` → `phase/6-deploy` — Feature phases

See [TASK.md](../TASK.md) for full PRD and task breakdown.

## Security

- Supabase-managed authentication with backend token verification
- Input sanitization and rate limiting
- GDPR deletion flow (24-hour SLA)
- Gender-neutral recommendations (default)
- Regular security audits via CodeRabbit

## License

MIT
