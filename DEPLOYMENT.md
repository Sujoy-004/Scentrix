# Deployment Guide

## Prerequisites

- Docker and Docker Compose v2
- Git
- A machine with at least 2 GB RAM (4 GB recommended)

## Quick Start (Full Stack)

```bash
git clone <repo-url>
cd Scentrix

# Configure environment
cp .env.example .env
# Edit .env: set JWT_SECRET_KEY, DATA_ENCRYPTION_KEY, and DATABASE_URL

# Build and start everything
docker compose up --build -d

# Verify
curl http://localhost:3000        # Frontend
curl http://localhost:8000/health # Backend API
curl http://localhost:8000/docs   # API documentation
```

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DATABASE_URL` | Yes | — | PostgreSQL async connection string |
| `JWT_SECRET_KEY` | Yes | — | Secret for signing auth tokens |
| `DATA_ENCRYPTION_KEY` | Yes | — | Secret for encrypting PII data |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | Comma-separated CORS origins |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection string |
| `NEO4J_URI` | No | `neo4j://localhost:7687` | Neo4j connection string |
| `NEO4J_USERNAME` | No | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | No | `neo4j_password` | Neo4j password |
| `SENTRY_DSN` | No | — | Sentry error tracking DSN |
| `PINECONE_API_KEY` | No | — | Pinecone vector search key |
| `ML_ENABLED` | No | `false` | Enable ML features |

## Required Services

### PostgreSQL 15

Required for all persistent data (users, ratings, quiz responses, saved fragrances).

**Free options:**
- Self-hosted via Docker Compose (included in `docker-compose.yml`)
- Supabase free tier (500 MB)
- Neon free tier (500 MB)

### Redis 7

Required for rate limiting and caching. The backend logs a warning but continues without Redis.

**Free options:**
- Self-hosted via Docker Compose (included in `docker-compose.yml`)
- Upstash free tier (100 MB, no credit card)
- Redis Cloud free tier (30 MB)

### Neo4j 5 (Optional)

Used for graph-based fragrance relationships. The backend falls back to the local `scentrix_master.json` file when Neo4j is unavailable. All features work without it.

**Free options:**
- Self-hosted via Docker Compose (included in `docker-compose.yml`)
- Skip entirely — the JSON fallback is sufficient for basic operation

## Deployment Approaches

### Option A: Docker Compose (Simplest)

Everything runs in containers on a single machine.

**Requirements:** Machine with Docker + 4 GB RAM.

```bash
docker compose up --build -d
```

**Pros:** One command, no external services, fully self-contained.
**Cons:** Single point of failure, manual updates, no auto-scaling.

### Option B: Service-by-Service (Most Flexible)

Each component on its own free-tier service.

| Component | Free Option | Notes |
|-----------|-------------|-------|
| Frontend | Cloudflare Pages, Netlify, GitHub Pages | Build with `npm run build`, deploy `.next/` |
| Backend | Docker-capable VM (Oracle Cloud free, Google Cloud Run free tier) | Use `backend/Dockerfile` |
| PostgreSQL | Supabase (500 MB), Neon (500 MB) | Connection string goes in `DATABASE_URL` |
| Redis | Upstash (100 MB), Redis Cloud (30 MB) | Connection string goes in `REDIS_URL` |
| Neo4j | Skip (JSON fallback) | No setup needed |

### Option C: Minimal (No Docker)

For constrained environments without Docker.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install ".[runtime]"
cp .env.example .env   # edit DATABASE_URL
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm ci
npm run build
npm start
```

## Database Setup

### First-time initialization

```bash
# Start databases only
docker compose up -d postgres redis

# Wait for them to be healthy, then run migrations
docker compose run --rm backend alembic upgrade head

# Seed fragrance data
docker compose run --rm backend python -m scripts.seed_data
```

## Production Checklist

- [ ] Generate unique `JWT_SECRET_KEY` (`openssl rand -hex 32`)
- [ ] Generate unique `DATA_ENCRYPTION_KEY` (`openssl rand -base64 32`)
- [ ] Set `ALLOWED_ORIGINS` to your frontend domain(s)
- [ ] Configure PostgreSQL with a strong password
- [ ] Enable HTTPS via a reverse proxy (Caddy, Nginx, or Traefik recommended)
- [ ] Set up regular database backups
- [ ] Configure Sentry for error monitoring (optional, free tier available)

## Troubleshooting

### Backend won't start — "Database unavailable"

Ensure PostgreSQL is running and `DATABASE_URL` is correct. The backend logs the connection attempt — check `docker compose logs backend`.

### CORS errors in browser

The `ALLOWED_ORIGINS` env var must include the exact origin (protocol + domain + port) of your frontend. Example: `ALLOWED_ORIGINS=https://myapp.com`.

### Frontend shows blank page

Check `NEXT_PUBLIC_API_URL` — the frontend needs the browser-accessible URL of the backend API. For Docker Compose this is `http://localhost:8000`. For production, use your backend domain.
