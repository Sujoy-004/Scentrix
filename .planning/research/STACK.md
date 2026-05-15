# Technology Stack — Cold-Start Recommendation Evaluation

**Project:** Scentrix
**Researched:** 2026-05-15
**Mode:** Ecosystem (cold-start recommendation evaluation)
**Overall confidence:** HIGH

## Context

Scentrix already has a working stack for recommendation *generation* (PyTorch Geometric + Neo4j for GraphSAGE, sentence-transformers for text encoding, Pinecone for vector search). This document covers **evaluation only** — the stack needed to measure Precision@10 and NDCG@10, compare against baselines (Popularity, Random), and produce statistically meaningful results for the MEXT research plan.

**Do not re-install what already exists.** The additions below are small, focused packages.

---

## Recommended Evaluation Stack

### Core Evaluation (add these)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **ranx** | `>=0.3.21` | Metric computation (Precision@k, NDCG@k) | Fastest pure-Python implementation (Numba-accelerated). Tested against TREC Eval for correctness. Supports per-query scores, mean/std aggregation, and LaTeX table export for papers. Much lighter than LensKit or RecBole. |
| **scipy** | `>=1.11` (already present) | Bootstrap confidence intervals (BCa method) | `scipy.stats.bootstrap` with `method='BCa'` is the standard for RecSys confidence intervals. No extra dependency. |
| **pandas** | `>=2.1` (already present) | Data wrangling, recommendation list handling | Already in the dependency tree. Used to format qrels/runs for ranx. |
| **numpy** | `>=1.26` (already present) | Numerical operations | Already in the dependency tree. |
| **matplotlib** | `>=3.7` (already present) | Result plots (bar charts with confidence intervals) | Already available in Docker image. |
| **seaborn** | `>=0.12` | Statistical plots (styled bar charts, heatmaps) | Optional but recommended for paper-quality figures. |

### Baselines (already partially present)

| Baseline | How | Why |
|----------|-----|-----|
| **Popularity** | Custom: rank items by total interaction count in training set | Standard cold-start baseline. No library needed — ~10 lines of pandas. |
| **Random** | Custom: shuffle all items, take top-k | Trivial to implement. Used as lower-bound sanity check. |

### Statistical Significance

| Method | Library | Why |
|--------|---------|-----|
| **Paired BCa bootstrap** | `scipy.stats.bootstrap(method='BCa')` | Gold standard for RecSys significance (Koren, 2021; paired bootstrap protocol). Handles skewed distributions. |
| **Sign-flip permutation test** | Custom (scipy helper) | Conservative guardrail when few seeds are available. From cold-start-algorithm repo (Zmanovskiy, 2026). |

---

## Installation

Add to `backend/pyproject.toml` under `[project.optional-dependencies] ml`:

```toml
ml = [
    "torch-geometric>=2.4.0",
    "pinecone>=5.0.0",
    "sentence-transformers>=3.0.0",
    "neo4j>=5.14.0",
    "prefect>=2.14.0",
    # --- Evaluation additions ---
    "ranx>=0.3.21",
    "seaborn>=0.12",
]
```

Then:

```bash
pip install -e ".[ml]"
```

That is **everything**. Three new lines in pyproject.toml.

---

## Evaluation Pipeline Architecture

### Data Flow

```
GraphSAGE inference (PyG) ─┐
                            ├──> recommendation lists (user → [item_id, ...])
Popularity baseline ───────┤
                            ├──> ranx.evaluate(qrels, run, ["ndcg@10", "precision@10"])
Random baseline ───────────┘
                                      │
                                      ▼
                          Per-user metric scores (DataFrame)
                                      │
                                      ▼
                   scipy.stats.bootstrap(method='BCa') → CI
                   sign-flip permutation test → p-value
                                      │
                                      ▼
                          matplotlib/seaborn → publication-ready figures
```

### ranx API (concrete usage)

```python
from ranx import Qrels, Run, evaluate

# Qrels = ground-truth: {user_id: {item_id: relevance_score}}
qrels = Qrels(test_data)

# Run = recommendations: {user_id: {item_id: score}}
baseline_run = Run({"user_1": {"item_42": 0.95, "item_17": 0.88, ...}, ...})
graphsage_run = Run({"user_1": {"item_99": 0.73, "item_55": 0.71, ...}, ...})

# Compute metrics
results = evaluate(
    qrels,
    graphsage_run,
    ["ndcg@10", "precision@10"],
    return_mean=True,
    return_std=True,
)
# Returns: {"ndcg@10": 0.234, "precision@10": 0.127}
```

### Bootstrap Significance (concrete usage)

```python
from scipy.stats import bootstrap
import numpy as np

# deltas = per-user NDCG@10 differences across seeds (or across runs)
# e.g., deltas = ndcg_graphsage - ndcg_popularity for each user
deltas = np.array([...])

ci = bootstrap(
    (deltas,),
    np.mean,
    n_resamples=9999,
    method="BCa",       # bias-corrected and accelerated
    confidence_level=0.95,
)
# ci.confidence_interval = (low, high)
# If low > 0 → GraphSAGE significantly better at α=0.05
```

---

## Alternatives Considered (and Rejected)

| Library | Why NOT |
|---------|---------|
| **LensKit 2025.7.0** | Overkill. LensKit is a full recommender framework with training, prediction, and evaluation pipelines. We already have training (PyG). We only need metrics. LensKit adds complexity with its own data format, `RecListAnalysis`, and batch inference infrastructure. Also requires Python 3.11 (we have it) but has a Rust dependency that complicates Docker builds on Windows. Use ranx instead. |
| **RecBole 1.2.1** | Designed for reproducing published models (94 built-in algorithms). Not for evaluating custom models. Has bugs with non-accuracy metrics (Issue #2194, fixed in PR #2209 Mar 2026). Heavy PyTorch dependency duplication. Zero benefit over ranx for this use case. |
| **Cornac 2.3.5** | Framework for multimodal recommendation comparison. Has good metrics but designed for A/B comparisons between algorithms, not evaluating a single custom model against simple baselines. Cython dependency complicates Docker builds. |
| **Elliot 0.3.1** | Stale (last release 2021). TensorFlow 2 dependency. Not maintained. |
| **ColdRec** | Designed for training cold-start models (20+ built-in models). We need evaluation, not model implementation. Overkill. |
| **RePlay** | Requires PySpark for distributed computing. Massive dependency. Designed for production-scale systems. Local Docker experiments don't need Spark. |
| **ir_measures 0.4.3** | Primarily an interface layer to TREC eval tools (pytrec_eval, trectools, ranx). Adds an abstraction layer without providing metric implementations itself. Use ranx directly instead. |
| **scikit-learn metrics** | `sklearn.metrics.ndcg_score` exists but operates on dense arrays, not the ranked list format we need. No built-in top-k cutoff handling for RecSys. Manual implementation of NDCG@k in scikit-learn is error-prone (many papers get it wrong — see Scholz, 2022). ranx does it correctly. |

---

## Why ranx Wins for This Project

1. **Precision@10 and NDCG@10 are first-class citizens** — just pass `"precision@10"` and `"ndcg@10"` as strings.
2. **TREC Eval validated** — metric implementations cross-checked against the official trec_eval tool. This matters for the MEXT research plan: you don't want a reviewer to question your metric implementation.
3. **Per-query (per-user) scores** — `return_mean=False` gives you per-user scores, which feeds directly into bootstrap testing.
4. **Comparison/statistical testing built-in** — `ranx.compare()` and `ranx.report()` produce ready-to-publish LaTeX tables with significance stars.
5. **Zero ML framework dependency** — pure Python + Numba, no PyTorch/TensorFlow needed in the evaluation script.
6. **Lightweight install** — 99KB wheel, no build step on Windows.

### When you might want LensKit instead

If future work adds online evaluation, A/B testing, or needs to train/evaluate new models (not just GraphSAGE), LensKit becomes more attractive. But for the current scope (offline evaluation of a single GraphSAGE model vs baselines), ranx is strictly better.

---

## Sources

| Finding | Source | Confidence |
|---------|--------|------------|
| ranx 0.3.21 latest release, Numba-accelerated metrics | [PyPI](https://pypi.org/project/ranx/), [GitHub](https://github.com/AmenRa/ranx) | HIGH |
| ranx tested against TREC Eval | [ranx docs](https://amenra.github.io/ranx/) | HIGH |
| scipy.stats.bootstrap with BCa for RecSys significance | [SciPy docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html) | HIGH |
| Paired BCa+perm protocol for small improvements | [arXiv 2511.19794](https://arxiv.org/pdf/2511.19794) (Nov 2025) | HIGH |
| Cold-start evaluation pipeline (reference implementation) | [cold-start-algorithm](https://github.com/nikita-zmanovskiy/cold-start-algorithm) v1.0.0 (Feb 2026) | MEDIUM (single repo, but well-documented) |
| LensKit 2025.7.0 release notes | [LensKit docs](https://lkpy.lenskit.org/stable/releases/2025.html) | HIGH |
| RecBole cold-start bug with non-accuracy metrics | [GitHub Issue #2194](https://github.com/RUCAIBox/RecBole/issues/2194) | HIGH |
| Cornac 2.3.5 supports cold-start via default_score() | [Cornac docs](https://cornac.readthedocs.io/en/v2.3.5/) | HIGH |
| Existing Scentrix stack (PyG, Neo4j, etc.) | `backend/pyproject.toml`, `AGENTS.md` | HIGH |

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Metric library (ranx) | HIGH | Current (2025-08), well-maintained, specifically designed for this task |
| Statistical testing (scipy BCa) | HIGH | Standard in RecSys literature, documented by SciPy, SOTA per recent papers |
| Baseline implementation | HIGH | Both are trivial (< 20 lines each), standard in every RecSys paper |
| Rejected alternatives | HIGH | Each was evaluated against specific criteria; documentation confirms limitations |
