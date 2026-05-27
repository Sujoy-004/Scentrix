# Scentrix

Graph-based cold-start fragrance recommendation research platform.

## What This Is

Hybrid research + engineering project. Research contribution: graph construction methodology is the critical determinant of GNN cold-start performance — embedding-derived similarity graphs introduce feature circularity that degrades NDCG by 63%, while structurally independent Jaccard edges recover 2.7× improvement. Engineering: full-stack production system with FastAPI, Neo4j, PostgreSQL, Redis, and a Next.js frontend.

## Research Findings

| Model | NDCG@10 | Notes |
|---|---|---|
| GraphSAGE-Jaccard | 0.494–0.523 | Primary result |
| GraphSAGE-Embedding | 0.183–0.191 | Circular graph — baseline |
| Feature-Only | 0.557 | Near-oracle, not fair comparison |
| Popularity | 0.008 | Naive baseline |
| Random | 0.031 | Naive baseline |

Key finding: embedding-derived graph construction introduces feature circularity that degrades NDCG by 63%. Jaccard-based independent edges recover 2.7× improvement (p≤0.001, d=0.93, n=10000 bootstrap).

Second finding: stricter Jaccard thresholds improve representation quality at cost of coverage. Threshold=0.20 selected: 99.2% cold item coverage.

## Stack

Backend: FastAPI, PostgreSQL, Neo4j, Redis
Frontend: Next.js
ML: PyTorch, GraphSAGE (2-layer, 128-dim), custom Jaccard graph builder
Eval: ranx, bootstrap significance testing (n=10000)
Infra: Docker (5 containers)

## Project Structure

```
backend/         FastAPI REST API (auth, catalog, recommendations, quiz)
frontend/        Next.js web UI
ml/              ML pipeline (GraphSAGE, eval, graph construction, data pipeline)
docs/            Architecture documentation
scripts/         Utility scripts (demo generation, packaging, normalization)
Makefile         Docker orchestration commands
docker-compose.yml  Service definitions (postgres, neo4j, redis, backend, frontend)
```

## Evaluation

Cold-start split: 920 cold items, 843 evaluated (77 excluded — zero ground truth).
Ground truth: primary accord match + Jaccard(notes) > 0.20.
Metrics: Precision@10, NDCG@10, Recall@10 via ranx.

## Running Eval

```bash
# Run evaluation pipeline (cold-start split → GraphSAGE → baselines → Jaccard sweep)
python -m ml.eval.pipeline

# Run bootstrap significance tests (n=10000)
python -m ml.eval.run_bootstrap

# Run threshold degree-split analysis
python ml/scripts/sweep_degree_split.py
```

## Phase Status

| Phase | Status |
|---|---|
| 1 — Pipeline & Data Foundation | ✅ Complete |
| 2 — Evaluation Infrastructure | ✅ Complete |
| 3 — Baselines & Comparison | ✅ Complete |
| 4 — GraphSAGE Pipeline | ✅ Complete (with rework) |
| 5 — Research Differentiators | 🔲 In progress |
| 6 — MEXT Demo | 🔲 Planned |
