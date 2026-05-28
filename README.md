# Scentrix

Graph-based cold-start fragrance recommendation research platform.

## What This Is

Hybrid research + engineering project. Research contribution: graph construction methodology is the critical determinant of GNN cold-start performance — embedding-derived similarity graphs introduce feature circularity that degrades NDCG by 63%, while structurally independent Jaccard edges recover 2.7× improvement. Engineering: full-stack production system with FastAPI, Neo4j, PostgreSQL, Redis, and a Next.js frontend.

## Research Findings

| Model | Precision@10 | NDCG@10 | Recall@10 | Notes |
|---|---|---|---|---|
| GraphSAGE-Jaccard (pure_cold) | 0.0745 | **0.504** | 0.0926 | Primary result — Jaccard graph |
| GraphSAGE-Embedding (pure_cold) | 0.0306 | **0.197** | 0.0216 | Circular KNN graph — 63% relative degradation |
| GraphSAGE-Jaccard (quiz_init) | 0.063 | **0.405** | 0.057 | Quiz-preference reranker (α=0.3) |
| Feature-Only | 0.0782 | **0.557** | 0.0932 | Near-oracle — same embedding space as ground truth |
| Content-Only (oracle) | 0.0860 | **0.581** | 0.1225 | Oracle — Jaccard on notes |
| Popularity | 0.0019 | **0.008** | 0.0010 | Naive baseline |
| Random | 0.0045 | **0.021** | 0.0011 | Absolute floor |

**Key finding:** embedding-derived graph construction introduces feature circularity that degrades NDCG by 63% relative to the corrected Jaccard baseline. Replacing circular edges with structurally independent Jaccard similarity over fragrance notes recovers 2.7× improvement (NDCG 0.183 → 0.494, p≤0.001, d=0.93, n=10000 bootstrap). GraphSAGE-Jaccard does not statistically beat Feature-Only (p=1.000, d=-0.149) — the claim is scoped to structural independence, not absolute performance.

**Second finding:** stricter Jaccard thresholds improve representation quality at cost of coverage. Threshold=0.20 selected: 99.2% cold item coverage (836/843 items connected). Group A NDCG at 0.20 = 0.494; at 0.30 = 0.642 but coverage drops to 65.4%.

**quiz_init result:** Simulated quiz reranking does NOT reliably beat pure_cold. Mean NDCG 0.496 vs 0.504 (std=0.023), beats baseline only 2/5 seeds. Improvement at α=0.3 was seed-dependent. Requires real user data to outperform pure cold-start.

**Stratification (coldness level):** Feature-Only leads at all levels. GraphSAGE-Jaccard follows monotonic trend (warmth → better NDCG). GraphSAGE-Embedding is non-monotonic — drops from Level 0 (0.198) to Level 1 (0.161) — revealing connectivity weakness for low-popularity items. (Caveat: Levels 1-2 optimistic due to training leakage.)

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
docs/            Architecture documentation, research paper, interview study guide
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
# Full evaluation pipeline (canonical seed)
python -m ml.eval.pipeline --mode pure_cold --seed 42

# Bootstrap significance tests (n=10000)
python -m ml.eval.run_bootstrap

# Threshold degree-split analysis
python ml/scripts/sweep_degree_split.py

# Quiz sensitivity curve
python -m ml.eval.pipeline --mode quiz_sensitivity

# Stratification grid (coldness-level breakdown)
python -m ml.eval.pipeline --mode stratification
```

## Reproducibility

The entire evaluation is reproducible via a single command: `python -m ml.eval.pipeline --mode pure_cold --seed 42`. A packaged demo bundle (`mext_demo_package_*.zip`) includes both model checkpoints (`graphsage_model.pt`, `graphsage_jaccard.pt`), config, splits, plots, and a self-contained HTML demo page.

## Phase Status

| Phase | Status |
|---|---|
| 1 — Pipeline & Data Foundation | ✅ Complete |
| 2 — Evaluation Infrastructure | ✅ Complete |
| 3 — Baselines & Comparison | ✅ Complete |
| 4 — GraphSAGE Pipeline | ✅ Complete (with rework) |
| 5 — Research Differentiators | ✅ Complete |
| 6 — MEXT Demo | ✅ Complete |
