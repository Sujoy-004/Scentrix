# Architecture: Cold-Start Recommendation Evaluation Pipeline

**Domain:** Graph-based cold-start fragrance recommendation
**Researched:** 2026-05-15
**Overall confidence:** HIGH (based on multiple peer-reviewed papers + codebase analysis)

---

## Executive Summary

Cold-start recommendation evaluation pipelines follow a **retrieve-then-evaluate** paradigm with four distinct phases: (1) data preparation and graph construction, (2) cold-start-aware data splitting, (3) model inference (candidate generation + scoring), and (4) metrics computation and comparison against baselines. The Scentrix codebase has the first phase partially built (graph construction, GraphSAGE models) but is **completely missing phases 2–4** — no cold-start splitting strategy, no evaluation harness, no baseline implementations, and no metrics computation.

This document defines the architecture that connects the existing components into a complete evaluation pipeline and integrates with the web application's backend.

---

## The Two-Stage Paradigm

The cold-start recommendation evaluation pipeline follows a **retrieve-then-rank** paradigm (standard in the recommender systems literature — see arxiv 2604.16318):

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EVALUATION PIPELINE                               │
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐         │
│  │  DATA    │   │  COLD    │   │  MODEL   │   │ METRICS  │         │
│  │  PREP    │ → │  SPLIT   │ → │ INFERENCE│ → │ & COMPARE│         │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘         │
│       │              │              │              │                │
│       ▼              ▼              ▼              ▼                │
│  scentrix_master   temporal/      GraphSAGE      Precision@10      │
│  .json → Neo4j     leave-cold     Popularity     NDCG@10           │
│  graph             splitting      Random         statistical tests │
└─────────────────────────────────────────────────────────────────────┘
```

Stage 1 (**candidate generation**): Given a cold-start user's quiz responses, generate candidate items using GraphSAGE embeddings, popularity ranking, or random sampling.

Stage 2 (**scoring/ranking**): Score and rank candidates. For the GraphSAGE model this is embedding similarity; for baselines it's popularity score or random shuffle.

---

## Component Boundaries

### 1. Data Preparation Module (`ml/pipeline/`)

**Status:** Partially exists. `clean.py`, `filter_elite.py`, `dataset_gate.py` handle cleaning. **Missing:** graph edge construction for evaluation purposes.

| Component | Status | Responsibility |
|-----------|--------|---------------|
| `FragranceDataCleaner` | ✓ EXISTS | Normalize, validate, deduplicate raw fragrances |
| `FragranceGraphIngestor` | ✓ EXISTS | Create Neo4j nodes + relationships |
| Graph edge builder | ⚠ PARTIAL | Builds edges from shared notes (v1), but this is disconnected from evaluation |
| Cold-start profile generator | ✗ MISSING | Simulates cold-start users from existing data |

**Boundary with the web app:**
```
ML pipeline (Python scripts, run via make enrich or cli)
    │
    ▼
Neo4j database (shared between ML and backend)
    │
    ▼
Backend API (FastAPI) reads Neo4j for serving recommendations
```

**Critical architectural decision:** The ML pipeline should NOT depend on the backend API. It runs as a standalone Python process that:
1. Reads data from `ml/data/scentrix_master.json`
2. Writes graph data to Neo4j
3. Trains GraphSAGE and writes embeddings
4. Runs evaluation and writes results to `ml/eval/runs/`

The backend then reads from Neo4j and the embedding index independently.

### 2. Cold-Start Data Split Module (`ml/eval/split.py`) — ✗ NEEDS BUILD

**This is the most architecturally critical missing component.** The cold-start evaluation requires a fundamentally different splitting strategy than standard ML train/val/test splits.

The existing `GraphEmbedder._build_split_masks()` (graph_sage.py lines 111–165) uses a **random node split** on fragrance nodes. This is incorrect for cold-start evaluation because:
- It treats all fragrances as equally "known" — there's no cold-start scenario
- There's no user-item interaction split (no user simulation at all)
- The split is on nodes, not on the user-item interaction matrix

**Correct architecture** for cold-start splitting:

```
Standard ML split:          Cold-start split:
┌────────────────────┐     ┌────────────────────────────┐
│ Train  │ Val│ Test │     │ Warm items │ Cold items    │
│ (70%)  │15% │ 15%  │     │ (known to model)  │(unseen)│
│ random │    │      │     │                         │  │
│ node   │    │      │     │ temporal or random       │  │
│ shuffle│    │      │     │ split of items           │  │
└────────────────────┘     └────────────────────────────┘
                                    │
                                    ▼
                           Simulated cold-start users:
                           - Quiz interaction only on warm items
                           - Ground truth: held-out interactions on cold items
```

**Two splitting strategies** (both needed for the research paper):

#### Strategy A: Temporal Split (Global Temporal Split / GTS)
Used to prevent data leakage. Defined in arxiv 2507.16289:
```
All interactions timestamped
│                                       │
├─────────────────────────────┬─────────┤
       Training set (pre-90%)   Test set (post-90%)
```
- All interactions before cutoff date → training (warm items visible to model)
- All interactions after cutoff date → test (cold items, held out)
- Completely prevents data leakage
- Controls test period duration

#### Strategy B: Leave-Cold-Out Split (for the Scentrix dataset)
Since the scentrix_master.json has no user interaction timestamps, the correct approach is:
```
1. Randomly select N% of fragrances as "cold-start items"
2. Remove all "interactions" with those items from training
3. All cold items are held out for evaluation
4. The model must recommend from cold items using only their features
```

**For Scentrix specifically** (no user interaction history exists):
- Simulate users by treating quiz responses as ground truth
- Hold out a subset of fragrances from the graph
- The GraphSAGE model should generate embeddings for cold items using their features (inductive capability)
- Evaluate whether cold items are recommended appropriately

**Component interface:**
```python
class ColdStartSplitter:
    def split(self, data: dict) -> SplitResult:
        """
        Returns:
            SplitResult with:
            - warm_items: items visible during training
            - cold_items: items held out for evaluation
            - train_interactions: simulated user-item pairs for warm items
            - test_interactions: simulated user-item pairs for cold items
        """
```

### 3. Model Inference Module (`ml/eval/`) — ✗ NEEDS BUILD

This module orchestrates running inference across all models and collecting predictions.

**Three models to evaluate:**

| Model | Type | Input | Output |
|-------|------|-------|--------|
| **GraphSAGE** (research hypothesis) | GNN-inductive | User quiz → embedding → cosine sim | Top-K ranked items |
| **Popularity** (baseline 1) | Non-personalized | None | Items sorted by popularity score |
| **Random** (baseline 2) | Non-personalized | None | Randomly shuffled items |

**For each cold-start user, the pipeline must:**
1. Generate their preference profile (from quiz responses on warm items)
2. Run all three models
3. Collect top-K recommendations from each
4. Compare against ground truth (held-out interactions on cold items)

**Inference flow:**

```
Cold-start user profile
         │
         ├───────────────────────────────────────────┐
         │                                           │
         ▼                                           ▼
   ┌───────────┐   ┌──────────────┐   ┌──────────┐
   │ GraphSAGE │   │  Popularity  │   │  Random  │
   │  embed +  │   │  rank all    │   │  shuffle │
   │  cosine   │   │  items by    │   │  all     │
   │  sim to   │   │  popularity  │   │  items   │
   │  profile  │   │  score       │   │          │
   └─────┬─────┘   └──────┬───────┘   └────┬─────┘
         │                │                │
         ▼                ▼                ▼
   ┌─────────────────────────────────────────────┐
   │         Top-K Recommendation Lists          │
   │  (each model produces ranked list of items) │
   └─────────────────────────────────────────────┘
```

### 4. Metrics Module (`ml/eval/metrics.py`) — ✗ NEEDS BUILD

Computes standard recommendation metrics.

**Required metrics:**

| Metric | Definition | Why for Cold-Start |
|--------|-----------|-------------------|
| **Precision@K** | fraction of recommended items that are relevant | Standard ranking metric, used by target labs |
| **NDCG@K** | position-aware: higher weight for relevant items ranked earlier | Standard ranking metric, used by target labs |
| **Recall@K** | fraction of relevant items that were recommended | Diagnostic — measures coverage of cold items |

**Implementation note:** The BATCH evaluation protocol is critical. Per arxiv 2209.04185, ranking ALL items (not just a sampled subset) is required for fair comparison. The existing `GraphEmbedder._build_split_masks()` only computes reconstruction loss (MSE on node features) — this gives NO information about recommendation quality.

**Interface:**
```python
class RecommendationMetrics:
    @staticmethod
    def precision_at_k(recommended: list[str], ground_truth: list[str], k: int) -> float
    @staticmethod
    def ndcg_at_k(recommended: list[str], ground_truth: list[str], k: int) -> float
    @staticmethod
    def recall_at_k(recommended: list[str], ground_truth: list[str], k: int) -> float
```

### 5. Results Aggregator (`ml/eval/aggregator.py`) — ✗ NEEDS BUILD

Collects metrics across all runs and produces comparison tables.

**Output format:**
```
┌────────────┬──────────────┬──────────┬──────────┐
│   Model    │ Precision@10 │ NDCG@10  │ Recall@10│
├────────────┼──────────────┼──────────┼──────────┤
│ GraphSAGE  │    0.XX      │  0.XX    │  0.XX    │
│ Popularity │    0.XX      │  0.XX    │  0.XX    │
│ Random     │    0.XX      │  0.XX    │  0.XX    │
└────────────┴──────────────┴──────────┴──────────┘
```

**Statistical significance:** Use bootstrap resampling or paired t-test to determine if GraphSAGE significantly outperforms baselines. This is a research paper requirement.

### 6. Orchestration Module (`ml/eval/pipeline.py`) — ✗ NEEDS BUILD

The top-level pipeline that ties everything together.

```python
def run_evaluation(
    config: EvalConfig,
) -> EvalReport:
    # 1. Data prep & build graph
    data = load_master_json(config.data_path)
    graph = build_graph(data)
    
    # 2. Split data for cold-start evaluation
    split = ColdStartSplitter(strategy=config.split_strategy).split(graph)
    
    # 3. Train GraphSAGE on warm items
    model = train_graphsage(split.warm_items)
    
    # 4. For each cold-start profile: run inference across all models
    metrics_collector = MetricsCollector()
    for profile in split.cold_start_profiles:
        for model_name, model_fn in [("graphsage", model), ("popularity", pop_model), ("random", random_model)]:
            predictions = model_fn.recommend(profile, k=10)
            metrics_collector.add(model_name, profile.id, predictions, profile.ground_truth)
    
    # 5. Aggregate and report
    report = metrics_collector.aggregate()
    report.to_json("ml/eval/runs/latest.json")
    report.to_markdown("ml/eval/runs/latest_report.md")
    return report
```

---

## Data Flow (How Information Moves)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          ML EVALUATION PIPELINE                         │
│                           (standalone Python)                           │
└─────────────────────────────────────────────────────────────────────────┘
         │
         │  python -m ml.eval.pipeline --config eval_config.yaml
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 1. Data Preparation                                                │
│    ├─ Read: ml/data/scentrix_master.json                          │
│    ├─ Clean: normalize + validate (FragranceDataCleaner)          │
│    ├─ Build graph: note-shared edges → PyG Data                   │
│    └─ Write: in-memory PyG graph object                           │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 2. Cold-Start Split                                                │
│    ├─ Select 15-30% of items as "cold" (temporal or random)       │
│    ├─ Remove cold items from graph edges                           │
│    ├─ Generate simulated user profiles from warm items             │
│    └─ Output: warm_graph, cold_items, profiles_with_ground_truth  │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 3. Model Training (GraphSAGE only)                                │
│    ├─ Train on warm_graph with reconstruction loss                │
│    ├─ Generate embeddings for ALL items (including cold, via       │
│    │  inductive inference — cold items use their features)        │
│    └─ Output: trained model + embeddings                         │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 4. Inference — Per Cold-Start User Profile                         │
│                                                                    │
│    For each simulated user:                                        │
│    ├─ GraphSAGE: embed quiz items → aggregate → cosine sim        │
│    │           → rank → Top-K                                     │
│    ├─ Popularity: rank all cold items by popularity_score         │
│    │           → take Top-K                                       │
│    └─ Random: shuffle all cold items → take Top-K                 │
│                                                                    │
│    All models produce top-K lists for the same items              │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 5. Metrics Computation                                            │
│    ├─ For each model: Precision@10, NDCG@10, Recall@10            │
│    ├─ Average across all cold-start users                          │
│    └─ Output: per-model metrics table                             │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 6. Results Persistence                                            │
│    ├─ Write: ml/eval/runs/{timestamp}/metrics.json               │
│    ├─ Write: ml/eval/runs/{timestamp}/report.md                  │
│    ├─ Write: ml/eval/runs/{timestamp}/config_used.yaml           │
│    └─ Update: ml/eval/runs/latest → symlink to latest run       │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 7. Web App Integration (separate code path)                       │
│                                                                    │
│ backend/app/routers/recommendations.py                             │
│    ├─ /guest: reads GraphSAGE embeddings from Pinecone            │
│    ├─ /personalized: reads from Postgres ratings + Pinecone       │
│    └─ Uses HybridRecommender (hybrid_search.py)                   │
│                                                                    │
│ The web app serves recommendations using the TRAINED model.       │
│ The evaluation pipeline validates the model QUALITY offline.      │
│ These are SEPARATE code paths sharing the Neo4j graph.            │
└────────────────────────────────────────────────────────────────────┘
```

---

## Component Dependency Graph (Build Order)

```
Phase 1: Data Foundation                 Phase 2: Evaluation Harness
┌──────────────────────┐                 ┌──────────────────────────┐
│ scentrix_master.json │                 │ ml/eval/metrics.py      │
│         │            │                 │    └─ Precision@K       │
│         ▼            │                 │    └─ NDCG@K            │
│ FragranceDataCleaner │                 │    └─ Recall@K          │
│         │            │                 └──────────┬───────────────┘
│         ▼            │                            │
│ FragranceGraph       │                 ┌──────────▼───────────────┐
│ Ingestor             │                 │ ml/eval/split.py         │
│         │            │                 │    └─ ColdStartSplitter  │
│         ▼            │                 │       (temporal + leave) │
│ Neo4j Graph          │                 └──────────┬───────────────┘
└──────────────────────┘                            │
                                    ┌───────────────▼───────────────┐
Phase 3: GraphSAGE Training        │ ml/eval/models/              │
┌──────────────────────┐           │    ├─ graphsage_eval_wrapper │
│ ml/models/           │           │    ├─ popularity_baseline    │
│ graph_sage.py        │           │    └─ random_baseline        │
│ graph_sage_v2.py     │           └──────────┬───────────────────┘
└──────────┬───────────┘                      │
           │                                  │
           └──────────────┬───────────────────┘
                          ▼
           ┌──────────────────────────────┐
           │ ml/eval/pipeline.py          │
           │    └─ run_evaluation()       │
           │    └─ orchestrate metrics    │
           └──────────────┬───────────────┘
                          ▼
           ┌──────────────────────────────┐
           │ ml/eval/aggregator.py        │
           │    └─ ResultsAggregator      │
           │    └─ ReportWriter           │
           └──────────────────────────────┘
```

**Build order rationale:**
1. **Metrics first** (no dependencies) — can be unit tested in isolation, defines the API contracts
2. **Splitting second** (depends on understanding the data structure, but not on models)
3. **Baselines third** (Popularity and Random are trivial, validate the metrics + split are working)
4. **GraphSAGE evaluation wrapper fourth** (wraps existing model code for the evaluation interface)
5. **Pipeline + Aggregator last** (depends on all components being ready)
6. **Web integration is parallel** — the API continues to serve recommendations independently

---

## Integration with Web Application Architecture

The evaluation pipeline is a **separate, offline process** from the web app. They share data through Neo4j.

```
┌─────────────────────┐       ┌──────────────────────┐
│  ML Evaluation      │       │  Web App (FastAPI)   │
│  (standalone,       │       │  (serving users)     │
│   run manually)     │       │                      │
│                     │       │                      │
│  ┌───────────────┐  │       │  ┌────────────────┐  │
│  │ Data Prep     │  │       │  │ Auth (JWT)     │  │
│  └───────┬───────┘  │       │  └────────────────┘  │
│          │          │       │                      │
│  ┌───────▼───────┐  │       │  ┌────────────────┐  │
│  │ Cold Split    │  │       │  │ Quiz Router    │  │
│  └───────┬───────┘  │       │  │ (confidence-   │  │
│          │          │       │  │  scored)       │  │
│  ┌───────▼───────┐  │       │  └────────────────┘  │
│  │ Train + Eval  │──┼───────┼──▶ Neo4j (graph   │  │
│  └───────┬───────┘  │       │  │  + embeddings)  │  │
│          │          │       │  └────────────────┘  │
│  ┌───────▼───────┐  │       │                      │
│  │ Results       │  │       │  ┌────────────────┐  │
│  │ ml/eval/runs/ │  │       │  │ HybridSearch  │  │
│  └───────────────┘  │       │  │ (Pinecone +    │  │
│                     │       │  │  Neo4j)        │  │
└─────────────────────┘       │  └────────────────┘  │
                               │                      │
                               │  ┌────────────────┐  │
                               │  │ Recommend      │  │
                               │  │ Routes         │  │
                               │  └────────────────┘  │
                               └──────────────────────┘
```

**Key architectural principle:** The evaluation runs GraphSAGE as a standalone PyTorch process. The web app uses the **resulting embeddings** (stored in Pinecone/Neo4j) for serving. They don't need to share runtime.

---

## Evaluation Protocol (for Reproducibility)

Based on the standard cold-start evaluation protocol from the literature (combined from arxiv 2209.04185, 2507.16289, and SimpleRec):

1. **All-ranking protocol**: Rank ALL items (not a sampled subset). This prevents metric inflation from easy negative sampling.

2. **Full cold-start**: Users have ZERO interaction history with cold items. Their profile is constructed from quiz responses on warm items only.

3. **Multiple random seeds**: Run each experiment with 5 different random seeds and report mean ± std.

4. **Statistical testing**: Bootstrap paired test or Wilcoxon signed-rank to check if GraphSAGE is significantly better than baselines.

5. **Cold-start difficulty levels** (optional, if data permits):
   - "Easy" cold-start: items with many feature overlap to known items
   - "Hard" cold-start: items with minimal feature overlap

---

## Files and Directory Structure (Proposed)

```
ml/
├── eval/                          # NEW — evaluation pipeline
│   ├── __init__.py
│   ├── pipeline.py                # Main orchestration
│   ├── split.py                   # ColdStartSplitter
│   ├── metrics.py                 # Precision@K, NDCG@K, Recall@K
│   ├── aggregator.py              # ResultsAggregator + ReportWriter
│   ├── models/                    # NEW — evaluation wrappers
│   │   ├── __init__.py
│   │   ├── popularity.py          # Popularity baseline
│   │   ├── random_baseline.py     # Random baseline
│   │   └── graphsage_wrapper.py   # Wraps GraphSAGE for eval interface
│   └── runs/                      # Evaluation results (gitignored except latest)
│       ├── latest/ → symlink
│       └── 20260515_120000/
├── models/
│   ├── graph_sage.py              # EXISTING — keep as-is
│   └── graph_sage_v2.py           # EXISTING — keep as-is
├── pipeline/                      # EXISTING — data prep pipeline
│   ├── clean.py
│   ├── filter_elite.py
│   └── dataset_gate.py
├── tests/
│   ├── test_graph.py              # EXISTING — graph integrity
│   └── test_integration.py        # EXISTING — data pipeline integration
└── data/
    └── scentrix_master.json       # EXISTING — dataset source
```

---

## Web App Integration Points (Minimal)

The backend already reads Neo4j and Pinecone for serving. **Minimal changes needed** to connect to evaluation:

| Component | What Changes | Why |
|-----------|-------------|-----|
| `backend/app/routers/recommendations.py` | Keep as-is | Already reads embeddings from HybridRecommender |
| `backend/app/services/hybrid_search.py` | Minor: add cold-start user path | The `recommend_by_profile` endpoint (currently 503) needs to call GraphSAGE embeddings |
| Celery worker | Fix PIPE-01 | Async job for cold-start inference if needed |
| No new API routes needed | — | Evaluation runs offline |

---

## Pitfalls to Avoid

1. **Random node split ≠ cold-start split.** The existing `_build_split_masks()` treats all nodes symmetrically. Cold-start requires holding out ENTIRE items (and their interactions) from training. Using random node split gives unrealistically optimistic results.

2. **Reconstruction loss ≠ recommendation quality.** The existing GraphSAGE code computes MSE on reconstructed node features. This measures feature prediction, not whether the model recommends the right items. These are uncorrelated — a model can have great reconstruction loss and terrible recommendations.

3. **Don't rank a subset.** The "all-ranking protocol" (arxiv 2209.04185) requires ranking all items. Sampling a subset artificially inflates NDCG. The existing `recommender.get_recommendations()` returns top-K but doesn't support full-catalog evaluation.

4. **Cold-start evaluation requires simulated users.** Since the dataset has no real user interactions, you must create synthetic ground truth by holding out items and checking if the model recommends them. The evaluation results should explicitly state that this is a simulated cold-start setting.

5. **The evaluation pipeline must be deterministic.** Fix all random seeds. The research value is in the comparison (GraphSAGE vs baselines), not in absolute numbers. Deterministic runs ensure the comparison is fair.

---

## Sources

- **SimpleRec (arxiv 2209.04185)**: Cold-start GraphSAGE baselines, importance of all-ranking protocol — high confidence (peer-reviewed)
- **Cold-start evaluation protocol (arxiv 2507.16289)**: Temporal vs leave-one-out splitting for rec sys evaluation — high confidence (peer-reviewed)
- **ColdStartBench (github nikita-zmanovskiy/cold-start-algorithm)**: Reference implementation of cold-start eval pipeline — medium confidence (single implementation, but well-documented)
- **GNP/GPatch (arxiv 2410.14241, 2209.12215)**: Patching GNNs for cold start — high confidence (peer-reviewed, includes cold-start dropout masking)
- **Existing codebase analysis (graph_sage.py, test_graph.py, test_integration.py)**: Direct examination — high confidence

---

## Build Order Implications for Roadmap

| Component | Estimated Effort | Depends On | Blocks |
|-----------|-----------------|------------|--------|
| `ml/eval/metrics.py` | Small (1 day) | Nothing | All later components |
| `ml/eval/split.py` | Medium (2 days) | `metrics.py` | Pipeline |
| `ml/eval/models/popularity.py` | Small (1 day) | Nothing | Pipeline |
| `ml/eval/models/random_baseline.py` | Trivial (0.5 day) | Nothing | Pipeline |
| `ml/eval/models/graphsage_wrapper.py` | Medium (2-3 days) | Existing graph_sage.py | Pipeline |
| `ml/eval/pipeline.py` | Medium (2 days) | All of the above | Report generation |
| `ml/eval/aggregator.py` | Small (1 day) | `pipeline.py` | Paper-ready output |
| **TOTAL** | **~10-11 days** | | |

**Critical path:** `metrics.py` → `split.py` → `pipeline.py` (these must be built in order). Baselines and GraphSAGE wrapper can be built in parallel once metrics are done.
