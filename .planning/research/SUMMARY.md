# Project Research Summary

**Project:** Scentrix — Graph-Based Cold-Start Fragrance Recommendation
**Domain:** Cold-start recommendation evaluation for graph-based preference initialization (MEXT research demo)
**Researched:** 2026-05-15
**Confidence:** HIGH (stack, features, architecture, and pitfalls all verified against multiple peer-reviewed sources)

## Executive Summary

Scentrix is a fragrance discovery platform whose research contribution is **graph-based preference initialization** — using an adaptive confidence-scored quiz to initialize GraphSAGE embeddings on a Neo4j fragrance graph, beating popularity and random baselines for cold-start (zero-history) users. The evaluation infrastructure is the critical evidence path for the July 2026 MEXT research interview. **Currently, zero evaluation infrastructure exists** — no cold-start data splitting, no metrics computation, no baseline implementations, no reproducibility framework, and no analysis pipeline. The existing `graph_sage.py` has a random node split that is architecturally wrong for cold-start evaluation and computes reconstruction loss (MSE on features) which is uncorrelated with recommendation quality.

The recommended approach builds a clean, **standalone offline evaluation pipeline** under `ml/eval/` following the standard retrieve-then-evaluate paradigm from RecSys literature. Stack additions are minimal (ranx for metrics + seaborn for plots — 3 lines in `pyproject.toml`). The pipeline comprises five modules: ColdStartSplitter (temporal + leave-cold-out strategies), metric computation (Precision@10, NDCG@10, Recall@10 via ranx), baseline recommenders (Popularity + Random), GraphSAGE evaluation wrapper (inductive inference support), and a ResultsAggregator producing paper-ready comparison tables with bootstrap confidence intervals.

**Key risks** ranked by severity: (1) Data leakage through temporal contamination or sampled negatives — invalidates all results if wrong. (2) GNN embedding collapse for zero-neighbor cold nodes — undermines the entire research hypothesis. (3) Aggregate-only metrics that mask cold-start degradation — produces misleading confidence. (4) Popularity bias creating a feedback loop where GraphSAGE merely mimics popularity — makes the research claim hollow. (5) Under-powered statistical claims from single-seed runs — unconvincing to MEXT reviewers. All five have documented prevention strategies in the detailed research documents, and all must be addressed before the demo deadline.

## Key Findings

### Recommended Stack

The evaluation stack is intentionally minimal because Scentrix already has a working recommendation *generation* stack (PyTorch Geometric, Neo4j, Pinecone, sentence-transformers). The evaluation adds only what's needed to measure and compare.

See [STACK.md](./STACK.md) for full details.

**Core technologies:**
- **ranx >=0.3.21**: Metric computation (Precision@k, NDCG@k) — fastest pure-Python implementation (Numba-accelerated), validated against TREC Eval, produces per-query scores for bootstrap testing. Replaces heavier frameworks like LensKit or RecBole.
- **scipy >=1.11** (already present): Bootstrap confidence intervals (BCa method) — `scipy.stats.bootstrap(method='BCa')` is the gold standard for RecSys significance testing.
- **seaborn >=0.12**: Statistical plots for publication-ready figures (bar charts with confidence intervals, histograms of per-user scores).
- **Popularity baseline**: Custom ~10 lines of pandas — rank items by total interaction count in training set. Standard cold-start baseline.
- **Random baseline**: Custom ~10 lines — shuffle all items, take top-k. Lower-bound sanity check.

**What was rejected:** LensKit (overkill — full framework when we only need metrics), RecBole (designed for reproducing published models, bugs with non-accuracy metrics), Cornac (Cython dependency complicates Docker builds), Elliot (stale since 2021), RePlay (requires PySpark). All rejected with documented rationale.

**Installation:** 3 new lines in `backend/pyproject.toml` under `[project.optional-dependencies] ml`: `ranx>=0.3.21`, `seaborn>=0.12`.

### Expected Features

See [FEATURES.md](./FEATURES.md) for full details.

**Must have (table stakes):**
- **T1: Cold-Start-Aware Data Splitting** — Split fragrance graph into train/val/test with cold-start simulation. Users in cold-start test set must have ZERO interactions in training. Requires extending existing `_build_split_masks()` from random node split to user-level cold-start split.
- **T2: Baseline Recommenders** — Popularity (rank by global popularity) + Random (shuffle all items). Both <50 lines. Must swap through the same evaluation interface as GraphSAGE.
- **T3: Metric Computation** — Precision@10, NDCG@10, HitRate@10 via ranx. Support K in [1,5,10,20] for sensitivity analysis. Report mean metrics across ALL test users.
- **T4: Reproducibility Infrastructure** — Config-driven evaluation (YAML/JSON config specifying split seed, model hyperparams, metric K), seed control, artifact persistence to timestamped log directories.
- **T5: Results Comparison Dashboard** — Comparison table of all models across metrics with per-user metric histograms.

**Should have (differentiators):**
- **D1: Graph-Based Preference Initialization via Adaptive Quiz** — Core research contribution. Simulate cold-start users who take the adaptive quiz, measure whether quiz-initialized GraphSAGE embeddings beat baselines. Three evaluation modes: pure cold-start, quiz-initialized cold-start, warm-start reference.
- **D2: Cold-Start Stratification Reporting** — Metrics broken down by cold-start severity (absolute cold: 0 interactions, quiz-only: 0 interactions but quiz data, few-shot warm: 1-5 interactions). Produces a 3×3 grid (3 cold-start levels × 3 models) — very effective for MEXT interview visuals.
- **D3: Learning Curve Evaluation** — NDCG@10 vs number of quiz questions answered (k ∈ {1,3,5,7,10}). Shows the dynamic value of preference initialization.
- **D4: Ablation Study: Graph Structure vs. Content Features** — Isolate contribution of graph structure from content features. Content-only, structure-only, full GraphSAGE. Critical for the research narrative.
- **D5: Web-Based Evaluation Demo** — Static HTML page with leaderboard comparison table, cold-start stratification bar chart, learning curve plot, and one "live" recommendation example. Must NOT require Docker to view.

**Defer (post-MEXT):** Beyond-accuracy metrics (diversity, novelty), multi-dataset validation, real-time serving, hyperparameter optimization, user studies, model interpretability (SHAP), deployment to cloud.

### Architecture Approach

The architecture follows a **retrieve-then-evaluate** paradigm with 4 distinct stages: data preparation → cold-start-aware data splitting → model inference (candidate generation + scoring) → metrics computation and baseline comparison. The evaluation pipeline is a **standalone offline process** independent from the web app. They share data through Neo4j but do not share runtime.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for full details and directory structure.

**Major components (all under `ml/eval/`, all need to be built):**
1. **ColdStartSplitter** (`ml/eval/split.py`) — Two strategies: temporal split (by timestamp) and leave-cold-out (randomly select N% of items as cold, remove all interactions with them from training). Must extend existing random node split to user-level cold-start simulation.
2. **Metric Computation** (`ml/eval/metrics.py`) — Precision@K, NDCG@K, Recall@K via ranx. Implements the "all-ranking protocol" (rank ALL items, not a sampled subset) to avoid metric inflation.
3. **Model Inference** (`ml/eval/models/`) — Three evaluation wrappers: `popularity.py` (rank by popularity score), `random_baseline.py` (shuffle), `graphsage_wrapper.py` (wraps existing GraphSAGE for the eval interface). Must handle inductive inference for cold nodes unseen during training.
4. **Results Aggregator** (`ml/eval/aggregator.py`) — Collects metrics across all runs, produces comparison tables (plain-text + Markdown + JSON), computes bootstrap confidence intervals and significance tests.
5. **Orchestration Pipeline** (`ml/eval/pipeline.py`) — `run_evaluation(config)` that ties everything together: load data → build graph → split → train → infer → aggregate → persist results to `ml/eval/runs/{timestamp}/`.

**Key architectural principles:**
- ML pipeline does NOT depend on the backend API. It reads from `ml/data/scentrix_master.json`, writes to Neo4j, trains GraphSAGE, and persists evaluation results independently.
- The web app reads Neo4j and Pinecone for serving recommendations — a separate code path.
- Build order: metrics first (no dependencies, defines API contracts) → splitting second → baselines third → GraphSAGE wrapper fourth → pipeline + aggregator last. Estimated total: ~10-11 days.

### Critical Pitfalls

See [PITFALLS.md](./PITFALLS.md) for full details (13 pitfalls documented with prevention strategies and phase mappings).

1. **Data Leakage Through Temporal & Structural Contamination** (Risk: Invalid results) — Random train/test split leaks future popularity signals; sampled negative evaluation inflates NDCG by 10-20%; including test edges in message-passing graph lets the GNN "cheat." **Prevention:** Use temporal splits, rank ALL items (all-ranking protocol), exclude test edges from GNN message passing. Must be addressed in EVAL-01.

2. **GNN Embedding Collapse for Cold-Start Nodes** (Risk: Model broken) — GraphSAGE requires neighborhood information. A cold-start user/item with zero edges produces degenerate embeddings. **Prevention:** Verify inductive mode in GraphSAGE (`SAGEConv` not transductive lookup), implement feature-only fallback for degree-0 nodes, train with edge dropout (~30%), consider NodeDup augmentation. Must be addressed in EVAL-03.

3. **Aggregate-Only Metrics Masking Cold-Start Degradation** (Risk: Misleading confidence) — Single NDCG@10 hides cold-start problems because warm users dominate the average. A model barely better than random for cold users can look competitive. **Prevention:** Always stratify metrics by coldness level (0, 1-3, 4-10, 11-20 interactions). Track cold-start metrics as a separate dashboard. Must be baked into evaluation harness from day one (EVAL-01).

4. **Popularity Bias Feedback Loop** (Risk: Research claim invalid) — If GraphSAGE merely learns to be a popularity proxy, the claim of "graph-based preference initialization" is hollow. Cold-start models have been shown to inherit AND amplify popularity bias from warm models. **Prevention:** Track popularity exposure as a metric, report long-tail coverage, use popularity-stratified NDCG, exclude popular items from test set for cold-start measurement. Must be addressed in EVAL-03.

5. **Binary Cold-Start Threshold** (Risk: Poor experimental resolution) — Treating "cold-start" as a single binary state (e.g., <5 interactions = cold) obscures the continuum. A model that works at 15 interactions may fail at 0. **Prevention:** Report metrics at multiple coldness levels. Define thresholds empirically using the inflection point method from Gusak et al. (arXiv 2508.07856). Must be addressed in EVAL-01.

## Implications for Roadmap

Based on combined research across stack, features, architecture, and pitfalls, the following phase structure is recommended. Build order is driven by the dependency chain: metrics → split → baselines → GraphSAGE wrapper → pipeline → differentiators.

### Phase 1: Evaluation Infrastructure (EVAL-01)

**Rationale:** Foundation phase. Every subsequent phase depends on correct metrics, proper data splitting, and reproducibility infrastructure. The three most dangerous pitfalls (data leakage, aggregate-only metrics, binary cold-start threshold) are all addressed here. Building this first ensures every experiment run is valid.

**Delivers:**
- `ml/eval/metrics.py` — Precision@K, NDCG@K, Recall@K via ranx with all-ranking protocol
- `ml/eval/split.py` — ColdStartSplitter with temporal split + leave-cold-out strategies
- Config-driven evaluation harness (YAML/JSON config, seed control)
- Artifact persistence to `ml/eval/runs/{timestamp}/`
- Unit tests for metrics and splitting

**Addresses features:** T1 (Cold-Start Data Splitting), T3 (Metric Computation), T4 (Reproducibility Infrastructure)
**Addresses pitfalls:** Pitfall #1 (binary threshold → multi-bucket stratification), #2 (aggregate metrics → stratified reporting), #3 (data leakage → temporal splits, all-ranking protocol)
**Stack additions:** ranx >=0.3.21, seaborn >=0.12
**Estimated effort:** ~3-4 days (metrics: 1 day, split: 2 days, config/reproducibility: 1 day)
**Research flag:** LOW — well-documented patterns, ranx API is straightforward. No deeper research needed.

### Phase 2: Baseline Recommend + Comparison (EVAL-02)

**Rationale:** Popularity and Random baselines are trivial (<50 lines each) but critical — they validate that the metrics and split from Phase 1 are working correctly. Building them next produces the first "real" results (GraphSAGE vs baselines), which may reveal issues with the GraphSAGE wrapper or splitting logic early.

**Delivers:**
- `ml/eval/models/popularity.py` — Popularity baseline
- `ml/eval/models/random_baseline.py` — Random baseline
- `ml/eval/aggregator.py` — ResultsAggregator + ReportWriter with comparison tables
- First results: "GraphSAGE beats Popularity by X% on NDCG@10" (may reveal issues)

**Addresses features:** T2 (Baselines), T5 (Comparison Table)
**Addresses pitfalls:** Pitfall #5 (popularity bias — must track coverage alongside accuracy), #12 (under-powered stats — implement multiple seeds from the start)
**Dependencies:** Phase 1 (metrics + split)
**Estimated effort:** ~2 days (baselines: 0.5 day each, aggregator: 1 day)
**Research flag:** NONE — baselines are standard, trivial implementation

### Phase 3: GraphSAGE Evaluation Wrapper + Full Pipeline (EVAL-03)

**Rationale:** The GraphSAGE wrapper is the most technically complex component. It must wrap existing `graph_sage.py` for the evaluation interface, ensure inductive inference works for cold nodes, and handle edge cases like zero-neighbor nodes. This phase also addresses the GNN-specific pitfalls (embedding collapse, neighbor contamination, hybrid degradation).

**Delivers:**
- `ml/eval/models/graphsage_wrapper.py` — Wraps GraphSAGE for eval interface
- `ml/eval/pipeline.py` — `run_evaluation()` orchestration
- Fixes to GraphSAGE for inductive cold-node inference
- Multi-seed evaluation runs with bootstrap significance testing
- Popularity debiasing (coverage metrics, popularity-stratified NDCG)

**Addresses features:** T5 (full comparison operational), foundation for D1/D4
**Addresses pitfalls:** Pitfall #4 (embedding collapse → verify inductive mode, feature-only fallback), #6 (neighbor contamination → GATConv or adaptive sampling), #8 (hybrid degradation → compare with/without cold training)
**Dependencies:** Phase 1 (metrics + split), Phase 2 (baselines + aggregator)
**Estimated effort:** ~4-5 days (GraphSAGE wrapper: 2-3 days, pipeline orchestration: 2 days)
**Research flag:** MEDIUM — needs codebase analysis of existing GraphSAGE architecture to determine neighbor sampling strategy and inductive support. The `graph_sage.py` file must be read during planning to verify `SAGEConv` usage and identify required changes.

### Phase 4: Research Core Differentiators

**Rationale:** Once the evaluation pipeline is solid and producing correct baseline comparisons, connect the quiz pipeline to enable the core research claims: quiz-initialized recommendations, stratified reporting, and ablation studies. These are the features that make the MEXT research plan compelling.

**Delivers:**
- Quiz-initialized GraphSAGE evaluation (connect quiz → GraphSAGE → recommendation pipeline)
- Cold-start stratification reporting (3×3 grid: 3 coldness levels × 3 models)
- Ablation study: content-only vs. structure-only vs. full GraphSAGE
- Bayesian smoothing for sparse quiz signals
- Statistical significance testing with paired BCa bootstrap + sign-flip permutation

**Addresses features:** D1 (Quiz Initialization), D2 (Stratification), D4 (Ablation Study)
**Addresses pitfalls:** Pitfall #7 (sparse signal overreaction → Bayesian smoothing), #9 (user abandonment → track completion rates as metric)
**Dependencies:** Phase 3 (full pipeline operational), PIPE-03 (quiz → GraphSAGE connection must be operational)
**Estimated effort:** ~4-5 days (quiz connection: 2 days, stratification: 1 day, ablation: 1 day, significance testing: 1 day)
**Research flag:** HIGH — the quiz → GraphSAGE connection (PIPE-03) is a known issue (currently returns 503). Must review `backend/app/routers/quiz.py`, `backend/app/services/hybrid_search.py`, and the Pinecone embedding pipeline during planning to understand what needs fixing.

### Phase 5: Learning Curves + Demo Polish

**Rationale:** Learning curves and the web demo are the final polish layer. They depend on all research results being available. The demo must be built FROM the evaluation framework (not separately) to avoid the overclaiming pitfall.

**Delivers:**
- Learning curve evaluation: NDCG@10 vs quiz length (k ∈ {1,3,5,7,10})
- Static HTML demo page with: comparison table, stratification bar chart, learning curve plot, one live recommendation
- Beyond-accuracy metrics: catalog coverage@k, novelty, diversity (intra-list dissimilarity)
- MEXT-ready demo package with reproducible results

**Addresses features:** D3 (Learning Curves), D5 (Web Demo)
**Addresses pitfalls:** Pitfall #10 (beyond-accuracy metrics → coverage + diversity reporting), #13 (demo overclaiming → build demo FROM evaluation, don't cherry-pick)
**Dependencies:** Phase 4 (research results needed for demo content)
**Estimated effort:** ~4-5 days (learning curves: 2 days, demo page: 2-3 days)
**Research flag:** LOW — learning curve implementation is straightforward (loop over quiz lengths), demo is static HTML with Chart.js or embedded matplotlib PNGs

### Phase Ordering Rationale

The order is driven by a clear dependency chain:

1. **Metrics + Split FIRST** because every evaluation result depends on correct measurement and valid data splitting. You cannot interpret any result without knowing it's free from data leakage and stratified by coldness level. This is the "get it right or nothing else matters" foundation.

2. **Baselines SECOND** because they are the simplest components that validate the infrastructure. If the Popularity baseline gives unexpected results, you know the split or metrics are wrong — and you fix them before introducing GraphSAGE complexity.

3. **GraphSAGE wrapper THIRD** because it's the most technically complex component and depends on all infrastructure being stable. This is where the GNN-specific pitfalls must be addressed.

4. **Research differentiators FOURTH** because they depend on the full pipeline being operational and the quiz pipeline being connected. These are the value-add features that differentiate the research.

5. **Demo + polish LAST** because it depends on having all results available. Building the demo from the evaluation framework (not separately) ensures alignment between claims and evidence.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (GraphSAGE Wrapper):** MEDIUM — must review `ml/models/graph_sage.py` architecture (neighbor sampling strategy, inductive vs transductive, `SAGEConv` usage). The existing model may need architectural changes for cold-start support.
- **Phase 4 (Quiz Initialization):** HIGH — the quiz → GraphSAGE → recommendation connection (PIPE-03) is known to return 503. Must audit `backend/app/routers/quiz.py`, `hybrid_search.py`, and Pinecone integration to plan the fix.

Phases with well-documented patterns (skip research-phase):
- **Phase 1 (Metrics + Split):** LOW — ranx API is well-documented, cold-start splitting follows established RecSys patterns
- **Phase 2 (Baselines):** NONE — Popularity and Random are trivial (under 50 lines each)
- **Phase 5 (Demo):** LOW — static HTML with embedded charts is a well-understood pattern

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | ranx is well-maintained (2025-08), validated against TREC Eval. scipy bootstrap BCa is the RecSys gold standard. All rejected alternatives have documented limitations. |
| Features | HIGH | Table stakes (T1-T5) are universal in cold-start RecSys literature. Differentiators (D1-D5) are directly from the research plan. Anti-features are justified by scope constraints. |
| Architecture | HIGH | Based on multiple peer-reviewed papers (arXiv 2209.04185, 2507.16289, 2410.14241) and direct codebase analysis. The retrieve-then-evaluate paradigm is standard. |
| Pitfalls | HIGH | Every pitfall is backed by 1-4 peer-reviewed sources. Prevention strategies are concrete and actionable. Source quality ranges from HIGH (peer-reviewed arxiv) to MEDIUM (practitioner blogs with citations). |

**Overall confidence:** HIGH

### Gaps to Address

1. **Existing GraphSAGE architecture details:** The research assumes `graph_sage.py` uses `SAGEConv` (inductive), but this must be validated by reading the code during planning. If it uses transductive embedding lookup (`nn.Embedding`), the evaluation pipeline needs significant additional work to support cold-start inductive inference.

2. **Quiz pipeline integration point:** The PIPE-03 task (connect quiz → GraphSAGE → recommendation) is known to be non-functional (returns 503). The research assumes it can be fixed, but the scope of the fix is unknown until the code is audited during planning.

3. **Synthetic ground truth validity:** Since Scentrix has no real user interaction history, the evaluation requires simulated users by holding out items. The research documents this limitation, but the simulation strategy must be refined during planning to ensure it produces realistic cold-start scenarios.

4. **Graph edge quality:** The graph is built from shared fragrance notes (top/middle/base). The research flags this as a potential issue (Pitfall #11) but does not validate edge semantics. A domain-expert review step should be added to DATA-01/DATA-02 to ensure the graph captures meaningful fragrance relationships.

## Sources

### Primary (HIGH confidence)
- [ranx documentation](https://amenra.github.io/ranx/) — Numba-accelerated metric computation, validated against TREC Eval
- [scipy.stats.bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html) — BCa bootstrap confidence intervals
- arXiv 2209.04185 — "On the Pitfalls of NDCG Evaluation" (2022) — all-ranking protocol, flaws in sampled evaluation
- arXiv 2507.16289 — "Cold-Start Evaluation Protocol" — temporal vs leave-one-out splitting
- arXiv 2410.14241 — "Graph Neural Patching for Cold-Start Recommendations" (2024)
- arXiv 2012.07064 — "Pre-training GNNs for Cold-Start Recommendation" (2020)
- arXiv 2402.09711 — "Node Duplication Improves Cold-start Link Prediction" (2024)
- arXiv 2510.11402 — "On Inherited Popularity Bias in Cold-Start Item Recommendation" (2025)
- arXiv 2307.14951 — "Common Pitfalls in Recommendation System Evaluation" (2023)
- arXiv 2308.01118 — "A Survey on Popularity Bias in Recommender Systems" (2023)
- arXiv 2508.07856 — Gusak et al. "Identifying Cold-Start Thresholds" (2025)
- RecBole documentation — Config priority, evaluation settings
- PROJECT.md — Precision@10, NDCG@10, Popularity + Random baselines, MEXT July 2026 deadline

### Secondary (MEDIUM confidence)
- [cold-start-algorithm](https://github.com/nikita-zmanovskiy/cold-start-algorithm) — Reference implementation of cold-start eval pipeline (v1.0.0, Feb 2026)
- ColdRec framework (github.com/YuanchenBei/ColdRec) — Cold-start evaluation framework with 26+ models
- Kumo.ai — "Handling Cold-Start Nodes in Production" and "Temporal Splits" guides
- Amazon Research — "Cold Brew" (openreview.net/pdf?id=1ugNpm7W6E) — Teacher-student approach for isolated nodes
- arXiv 2404.13298 — MARec cold-start paper with bootstrap significance testing
- arXiv 2410.22136 — SimRec cold-start stratification by item frequency
- arXiv 2306.10453 — "Evaluating GNNs for Link Prediction: Current Pitfalls"

### Tertiary (LOW confidence)
- EngineersOfAI "The Cold Start Problem" — Blog post, well-sourced but not peer-reviewed
- System Overflow "Cold Start Failure Modes" — Practitioner experience, no formal validation
- BBC R&D "Bootstrapped Personalised Popularity for Cold Start" (2023) — Notes completion trade-off

---

*Research completed: 2026-05-15*
*Ready for roadmap: YES*
