# Architecture

Current system runs locally via Docker Compose with 5 containers.

## Services

| Service | Image | Purpose |
|---------|-------|---------|
| `postgres` | postgres:15-alpine | Primary store: auth, user profiles, ratings, saved fragrances, interaction events |
| `neo4j` | neo4j:5-community | Knowledge graph: fragrance nodes, notes, accords, brand relationships |
| `redis` | redis:7-alpine | Cache: recommendation results, ephemeral quiz session store |
| `backend` | Custom (FastAPI) | REST API: authentication, catalog serving, recommendation engine, quiz orchestration |
| `frontend` | Custom (Next.js) | Web UI: fragrance browsing, quiz onboarding, recommendation display |

## Data Flow

```
User request → FastAPI → PostgreSQL (auth/ratings/profiles)
                       → Neo4j (fragrance catalog + knowledge graph)
                       → Redis (cached recommendations)

FastAPI → optional → TextEncoder (Sentence-Transformers) → Pinecone (semantic search)
         → optional → Google Gemini (Sommelier insights)
```

The recommendation engine (`app/services/hybrid_search.py`) uses a rule-based scorer (note overlap, accord overlap, category match, occasion match, popularity) with optional semantic embedding enhancement. GraphSAGE embeddings are not currently served online — the GNN evaluation is an offline research pipeline in `ml/eval/`.

## ML Pipeline

```
scentrix_master.json → clean.py → filter_elite.py → cleaned dataset
                                                    ↓
                              ingest.py → Neo4j fragrance graph
                                                    ↓
                              eval/pipeline.py → cold-start split
                                                → build graphs (embedding + Jaccard)
                                                → train GraphSAGE
                                                → evaluate (NDCG@10, Precision@10)
                                                → threshold sweep
                                                → significance tests
```

## Offline Validation

- Integration tests: `ml/tests/` — graph validation, pipeline integrity
- Diversity audit: `ml/pipeline/diversity_audit.py` — olfactive coverage analysis
- Bootstrap significance: `ml/eval/run_bootstrap.py` — paired BCa bootstrap (n=10000)

## Design Principles

- **Derived state is cacheable.** Embeddings, graph edges, and recommendation scores are stored in Neo4j/Redis, not PostgreSQL. User-owned data (profiles, ratings, consent) lives in PostgreSQL only.
- **Graceful degradation.** Every external dependency (Neo4j, Redis, Pinecone, Gemini) has a fallback path. If Neo4j is down, the catalog loads from a local JSON file.
- **Research rigour.** All eval claims backed by bootstrap significance tests with Cohen's d effect sizes. Cold-start split is stratified by primary accord.

## Not Yet Implemented

- Production deployment (no Railway/Vercel/Supabase production config)
- Online GraphSAGE inference (model runs only in eval pipeline)
- CI/CD pipeline
- Monitoring/alerting
