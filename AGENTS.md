# AGENTS.md (Scentrix)

Cold-start recommendation research platform for MEXT July 2026. Target: user takes a quiz → GraphSAGE infers preferences → personalized niche recs without interaction history.

## Target Architecture

```
User Quiz ──→ Adaptive Confidence Scorer ──→ Quiz Embedding
                                                 ↓
scentrix_master.json ──→ Neo4j Fragrance Graph ──→ GraphSAGE (inductive inference)
                                                      ↓
                                        Popularity/Random Baselines ──→ Comparison + Significance Tests
```

**What exists:** Auth, Neo4j catalog, GraphSAGE model code, quiz endpoints, Next.js scaffold, Docker infra, graph ingestor, cleaned dataset.
**What's being built:** Evaluation harness → Baselines → GraphSAGE pipeline → Research differentiators → MEXT demo (6 phases).

## Services

| Dir | Tech | Purpose |
|-----|------|---------|
| `backend/` | FastAPI (Python 3.11+) | REST API |
| `frontend/` | Next.js 16, React 19, Tailwind v4 | Web UI |
| `ml/` | PyTorch, PyG, Sentence-Transformers | GraphSAGE, embeddings, pipeline |

## Commands

```
make up / down / logs          # Docker lifecycle
make migrate / seed            # DB
make test-backend / test-frontend  # pytest / Playwright
make lint                      # ruff + mypy (backend) + eslint (frontend)
make enrich                    # Clean dataset + update Neo4j
```

## Conventions

- Python: ruff format + mypy strict. No `any`. Line-length 100.
- API changes update both backend routes AND frontend client calls.
- PII encrypted at rest (`backend/app/auth/encryption.py`, AES-256 Fernet).
- `.planning/` is local-only (`.gitignore`).
- Tests: backend uses SQLite in-memory; frontend uses Playwright E2E + MSW mocking.

## Workflow Rules

- **Graphify after every task**: run `/graphify` to update project knowledge graph.
- **Parallel sub-agents**: split independent work across parallel `task()` calls. Verify output before declaring done.
- **UAT via subagent**: spawn a subagent to run tests programmatically (grep, file checks). Never Q&A the user. Surface only the final summary.
- **Always keep graphify-out updated** — refer to it for queries. Save tokens. EVen for UAT sessions.
