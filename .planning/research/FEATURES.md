# Feature Landscape: Cold-Start Recommendation Evaluation

**Domain:** Cold-start recommendation evaluation for graph-based preference initialization
**Researched:** 2026-05-15

## Context

**Scentrix** is a fragrance discovery platform whose research contribution is **graph-based preference initialization** using GraphSAGE on Neo4j, initialized via an adaptive confidence-scored quiz. The evaluation system must demonstrate that this approach outperforms popularity-ranking and random baselines in the cold-start (zero interaction history) setting.

**Target audience:** MEXT scholarship interview panel (July 2026) — embassy staff and Japanese professors. The evaluation system IS the evidence that the research plan is sound.

**Current state:** Zero evaluation infrastructure exists. The ML README describes an `ml/training/evaluate.py` file that has never been created. `ml/training/` directory does not exist.

---

## Table Stakes (Must-Have)

These features are the absolute minimum for any cold-start recommendation evaluation. Without them, the system is not credible as research.

### T1: Cold-Start-Aware Data Splitting

| Aspect | Detail |
|--------|--------|
| **What** | Split fragrance graph into train/val/test sets with cold-start simulation. Users in cold-start test set must have ZERO interactions in training. |
| **Why table stakes** | Every cold-start paper uses this. RecBole, ColdRec, DropoutNet all implement it. If the split doesn't isolate cold-start users/items, the evaluation is meaningless. |
| **Complexity** | Medium |
| **Dependencies** | Graph construction (DATA-01, DATA-02 from PROJECT.md), graph dataset loader |

**Required modes:**
- **Random ratio split** (e.g., 70/15/15) — standard for initial experiments
- **Cold-start isolation split** — hold out a subset of users/items entirely from training to simulate true cold-start
- **Inductive node split** — test nodes are completely unseen during GraphSAGE training (matches the PyG inductive pattern already partially implemented in `graph_sage.py`)

**Implementation notes:**
- `graph_sage.py` already has `_build_split_masks()` with random 70/15/10 split and seeded reproducibility
- Must extend to split BY USER (not random nodes) for cold-start simulation
- Split artifacts must be saved to disk for reproducibility across runs

**Sources:**
- ColdRec framework (github.com/YuanchenBei/ColdRec) implements "cold user/item recommendation" as distinct tasks with unified dataset division
- RecBole eval_args `split: {'RS': [0.8,0.1,0.1]}` with `group_by: user` and `order: TO` for temporal ordering

---

### T2: Baseline Recommenders (Popularity + Random)

| Aspect | Detail |
|--------|--------|
| **What** | Implement popularity-based and random recommenders as comparison baselines. |
| **Why table stakes** | PROJECT.md explicitly requires these. CF/MF baselines are dishonest for cold-start (they require interaction history). These are the ONLY honest baselines. |
| **Complexity** | Low |
| **Dependencies** | Fragrance catalog loaded, rating/interaction data available |

**Popularity baseline:**
- Recommend the K most popular fragrances globally (by rating count or average rating)
- Serves as the "dumb but not stupid" baseline — it's what a new user gets on any platform
- Any novel approach must beat this convincingly

**Random baseline:**
- Recommend K random fragrances from the catalog
- Establishes the noise floor
- Any approach that doesn't beat random is worthless

**Implementation notes:**
- Must be able to swap baselines and GraphSAGE through the same evaluation interface
- Both baselines should be < 50 lines of code each

**Sources:**
- PROJECT.md Key Decisions: "Popularity + Random baselines — Only honest baselines for cold-start"
- Sigir 2020, RecSys 2020 papers consistently use popularity as cold-start baseline
- "DropoutNet: Addressing Cold Start in Recommender Systems" (NeurIPS 2017) uses popularity baseline

---

### T3: Metric Computation (Precision@10, NDCG@10)

| Aspect | Detail |
|--------|--------|
| **What** | Compute Precision@K and NDCG@K given ranked recommendation lists and ground-truth interactions. |
| **Why table stakes** | PROJECT.md specifies Precision@10 and NDCG@10 as the evaluation metrics, matching Matsuo/Kashima lab conventions. |
| **Complexity** | Low |
| **Dependencies** | Ground-truth test data, predicted rankings |

**Required:**
- **Precision@K** — fraction of top-K recommendations that are relevant
- **NDCG@K** — normalized discounted cumulative gain (position-sensitive ranking quality)
- **HitRate@K** — did at least one relevant item appear in top-K? (used widely in cold-start literature)

**Implementation notes:**
- ~30-50 lines each; pure NumPy/Torch — no external metric library needed
- Must handle edge cases: empty ground-truth, K larger than candidate pool
- K=10 is primary; support K in [1, 5, 10, 20] for sensitivity analysis
- Report mean metrics across ALL test users (not just users with ground truth — important for cold-start)
- RecBole's approach: `metrics: ['Recall', 'MRR', 'NDCG', 'Hit', 'Precision']` with `topk: 10`

**Sources:**
- RecBole evaluation settings: `valid_metric: MRR@10`, `metric_decimal_place: 4`
- "From Variability to Stability: Advancing RecSys Benchmarking Practices" — NDCG@10 has highest correlation (≥0.9) with accuracy and ranking metrics
- "MARec" paper (arXiv 2404.13298) uses HR@k and NDCG@k with bootstrapping for significance

---

### T4: Reproducibility Infrastructure

| Aspect | Detail |
|--------|--------|
| **What** | Seed control, config files, artifact logging, deterministic execution. |
| **Why table stakes** | Without reproducibility, the results mean nothing. MEXT reviewers will ask "can you replicate this?" |
| **Complexity** | Medium |
| **Dependencies** | T1, T2, T3 |

**Required:**
- **Config-driven evaluation** — YAML or JSON config file specifying: data split seed, model hyperparameters, metric K, which baselines to run
- **Seed control** — Python `random.seed()`, `torch.manual_seed()`, `np.random.seed()` all set from a single config seed
- **Artifact persistence** — save results JSON to timestamped log directory with config snapshot
- **Deterministic graph construction** — already partially done in `graph_sage.py` with seed=42 in `_build_split_masks()`

**Implementation notes:**
- Follow RecBole's config pattern: config files > parameter dicts > command line > defaults
- Each evaluation run produces a directory: `ml/logs/eval/YYYYMMDD_HHMMSS_{model_name}/`
  - `config.json` — frozen config snapshot
  - `results.json` — all metrics per test user + aggregate
  - `predictions.pkl` — full prediction scores for post-hoc analysis

**Sources:**
- RecBole config priority: "Command Line > Parameter Dicts > Config Files > Default Settings"
- Reproducibility standard in RecSys community (see "From Variability to Stability" KDD 2024 paper)

---

### T5: Results Comparison Dashboard

| Aspect | Detail |
|--------|--------|
| **What** | Produce a comparison table of all models (GraphSAGE v1, v2, Popularity, Random) across metrics. |
| **Why table stakes** | The whole point of evaluation is comparison. Without a table showing "our method > baselines," there is no research result. |
| **Complexity** | Low-Medium |
| **Dependencies** | T2, T3, T4 |

**Required output format:**
```
| Model            | Precision@10 | NDCG@10 | HR@10 |
|------------------|-------------|---------|-------|
| Random           | 0.0123      | 0.0089  | 0.045 |
| Popularity       | 0.0456      | 0.0321  | 0.123 |
| GraphSAGE (v1)   | 0.0789      | 0.0567  | 0.198 |
| GraphSAGE (v2)   | 0.0890      | 0.0654  | 0.210 |
```

**Implementation notes:**
- Plain-text table output to console + markdown file in artifact directory
- Also JSON for programmatic use
- Include per-user metric histograms to show distribution (not just mean — critical for understanding cold-start variance)
- The "lifts" format (e.g., "+53.8%") used in cold-start papers like MARec

---

## Differentiators (What Makes Scentrix Novel)

These features are NOT standard in recommendation evaluations. They represent the research contribution and are what makes the MEXT research plan compelling.

### D1: Graph-Based Preference Initialization via Adaptive Quiz

| Aspect | Detail |
|--------|--------|
| **What** | Simulate cold-start users who take the adaptive quiz, then measure whether quiz-initialized GraphSAGE embeddings produce better recommendations than baseline. |
| **Why differentiating** | Standard cold-start evaluation assumes users have NO information. Scentrix's research hypothesis is that a short quiz CAN provide enough preference signal to initialize graph embeddings. No other cold-start eval framework tests this. |
| **Complexity** | High |
| **Dependencies** | T1, T2, T3, T4, PIPE-03 (quiz → inference → recommendation pipeline) |

**Required evaluation modes:**
- **"Pure cold-start":** Test users have zero quiz data, zero interaction history → GraphSAGE uses only quiz-derived features (simulates real cold-start)
- **"Quiz-initialized cold-start":** Test users complete the adaptive quiz → GraphSAGE uses quiz confidence scores + graph structure
- **"Warm-start reference":** (For contrast only) Users with interaction history — demonstrates that graph-based approach doesn't sacrifice warm performance

**Implementation notes:**
- This is the CORE research contribution — spend implementation effort here
- Must produce a clear ablation: "Without quiz" vs "With quiz" vs "Popularity" vs "Random"
- Quiz simulation: for offline evaluation, use user clusters from the graph as synthetic quiz profiles
- The confidence-scored adaptive quiz (`backend/app/routers/quiz.py`) must be connected to the evaluation pipeline

---

### D2: Cold-Start Stratification Reporting

| Aspect | Detail |
|--------|--------|
| **What** | Report metrics broken down by cold-start severity — "how cold was the user?" |
| **Why differentiating** | Standard cold-start evaluation reports one aggregate number. Stratified reporting shows WHERE the method works and where it fails, which is more informative and shows deeper analysis. |
| **Complexity** | Medium |
| **Dependencies** | T1, T3 |

**Stratification buckets:**
- **Absolute cold-start:** No interactions, no quiz data
- **Quiz-only cold-start:** Quiz completed but zero interaction history
- **Few-shot warm:** 1-5 interactions (shows learning curve)

**Metrics per bucket:** Precision@10, NDCG@10, HR@10

**Implementation notes:**
- Inspired by "SimRec" (arXiv 2410.22136) which breaks down cold-start by item frequency: "occurring <10 times", "frequency = 0"
- Also by MARec's warm/cold split analysis
- Results in a 3x3 grid (3 cold-start levels × 3 models) — very effective for MEXT interview visuals

---

### D3: Learning Curve Evaluation

| Aspect | Detail |
|--------|--------|
| **What** | Measure how recommendation quality improves as the quiz collects more confidence signals. |
| **Why differentiating** | Shows the DYNAMIC value of preference initialization, not just static comparison. Demonstrates the concept of "preference initialization through interaction." |
| **Complexity** | Medium-High |
| **Dependencies** | D1, T3 |

**Plot:** NDCG@10 vs Number of quiz questions answered

**Implementation:**
- For each quiz length k ∈ {1, 3, 5, 7, 10}:
  - Simulate quiz completion up to k questions
  - Generate recommendations from quiz-derived embeddings
  - Measure NDCG@10
- Expected result: NDCG improves with more quiz questions, ideally plateauing after 5-7 questions

**Related work:**
- "Few-shot learning curves" in cold-start algorithms (github.com/nikita-zmanovskiy/cold-start-algorithm)
- SASRec with content initialization (arXiv 2507.19473) — NDCG vs delta_max curves

---

### D4: Ablation Study: Graph Structure vs. Content Features

| Aspect | Detail |
|--------|--------|
| **What** | Compare GraphSAGE performance using only node features (content-based) vs. only graph structure vs. both. |
| **Why differentiating** | Isolates the contribution of graph structure from content features. If graph structure alone beats content-only, that's a strong result. If not, the research needs to investigate why. |
| **Complexity** | Medium |
| **Dependencies** | T1, T2, T3 |

**Ablation modes:**
- **Content-only:** GraphSAGE with all node features, but graph is identity (no neighbor aggregation)
- **Structure-only:** GraphSAGE with random/constant node features, full graph structure
- **Full:** Both content and structure (the proposed method)

**Expected insight:** Determines whether graph structure contributes meaningfully beyond content-based recommendations. Critical for the research narrative in the MEXT plan.

---

### D5: Web-Based Evaluation Demo

| Aspect | Detail |
|--------|--------|
| **What** | A minimal web UI showing evaluation results — comparison tables, stratification, learning curves. |
| **Why differentiating** | MEXT interviewers may not read code. A visual demo showing "this is what we found" makes the research tangible. |
| **Complexity** | Medium |
| **Dependencies** | T5, D2, D3 |

**What to show:**
1. Leaderboard-style comparison table (GraphSAGE vs baselines)
2. Bar chart of cold-start stratification
3. Learning curve plot (NDCG@K vs quiz length)
4. One "live" recommendation: "Here's what GraphSAGE recommends for a new user who likes floral scents"

**Implementation notes:**
- Static HTML is sufficient — no backend needed for demo
- Use Chart.js or simple matplotlib → export as PNG/HTML
- Should NOT require Docker to view (standalone HTML or PDF)

---

## Anti-Features (Deliberately NOT Build)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Matrix Factorization / Collaborative Filtering baselines** | They require user-item interaction history. For cold-start evaluation, they are meaningless and dishonest. The PROJECT.md explicitly forbids this. | Use only Popularity + Random baselines. In a paper, you could note "CF baselines are inapplicable to pure cold-start." |
| **Online A/B testing** | Requires deployed system with real traffic and user tracking. Overkill for offline research demos. MEXT doesn't expect production deployment. | Offline evaluation + a screenshot of the demo is sufficient. |
| **Real-time model serving** | Web-scale recommendation serving (sub-10ms, FAISS, etc.) is irrelevant to demonstrating research results. | Batch inference during evaluation runs. |
| **Hyperparameter optimization (Optuna/grid search)** | Tempting but scope creep. For a research demo, default or hand-tuned hyperparameters are acceptable. | Manual hyperparameter choices documented in research plan. Sensitivity analysis can be future work. |
| **Multiple datasets / cross-domain validation** | The research is specific to the fragrance domain. MEXT expects depth, not breadth. A single, well-curated dataset with rigorous evaluation is better than sloppy multi-dataset. | Focus on `scentrix_master.json` and graph quality. Extend to other domains only if explicitly requested. |
| **Beyond-accuracy metrics (diversity, novelty, coverage)** | These are secondary concerns. The primary hypothesis is about ACCURACY of cold-start recommendations. | Mention in "future work" section of research plan. Don't implement. |
| **User study / human evaluation** | Takes weeks, requires recruiting participants, introduces confounding variables. Not feasible for a 3rd-year undergrad demo. | Offline evaluation with ground-truth data from the fragrance catalog. |
| **Model interpretability (SHAP, attention visualization)** | While cool for demos, adds significant implementation complexity with minimal research value for a cold-start eval. | Skip. Could be future work. |
| **Deployment to Railway/Vercel** | PROJECT.md explicitly out of scope. Creates maintenance burden and possible cost. | Local Docker is sufficient. |
| **Real-time data stream evaluation (prequential)** | Meant for production systems, not offline experiments. | Standard holdout evaluation is the research norm. |

---

## Feature Dependencies

```
T1 (Data Splitting)
├── T2 (Baselines)            — depends on T1 for train/test data
├── T3 (Metrics)              — depends on T1 for ground-truth
├── T4 (Reproducibility)      — depends on T1 (config includes split params)
│   └── T5 (Comparison Table) — depends on T2, T3, T4
│
D1 (Quiz Initialization)      — depends on T1, PIPE-03 pipeline fix
├── D2 (Stratification)       — depends on D1 (can extend split definitions)
├── D3 (Learning Curves)      — depends on D1 (needs quiz simulation)
│
D4 (Ablation Study)           — depends on T1, T3 (can run independent of D1)
│
D5 (Web Demo)                 — depends on T5, D2, D3 (visualize results)
```

---

## MVP Recommendation (for MEXT Demo — July 2026)

**Time budget:** ~6-8 weeks to implement before interview.

### Phase 1: Foundation (Weeks 1-2) — Table Stakes ONLY
1. **T1:** Cold-start data splitting (random split + cold-start isolation split)
2. **T3:** Metric computation (Precision@10, NDCG@10, HR@10)
3. **T4:** Config + reproducibility infrastructure

**Deliverable:** Can run `python ml/eval/run.py --config eval_configs/baseline.yaml` and get metrics.

### Phase 2: Baselines (Week 3) — Table Stakes
1. **T2:** Popularity + Random baselines
2. **T5:** Comparison table output

**Deliverable:** First results: "GraphSAGE beats Popularity by X% on NDCG@10"

### Phase 3: Research Core (Weeks 4-5) — Differentiators
1. **D1:** Connect quiz pipeline → evaluation (fix PIPE-03 first)
2. **D4:** Ablation study (content vs. structure)
3. **D2:** Cold-start stratification reporting

**Deliverable:** Full evaluation: stratified results, ablation table

### Phase 4: Polish (Weeks 6-8) — Differentiators
1. **D3:** Learning curve evaluation
2. **D5:** Static HTML demo page with charts

**Deliverable:** MEXT-ready demo package with reproducible results

### Defer (Post-MEXT / Future Work)
- Beyond-accuracy metrics (diversity, novelty)
- Multi-dataset validation
- Real-time serving
- Hyperparameter optimization
- User studies

---

## Sources

- **ColdRec toolkit** (github.com/YuanchenBei/ColdRec) — Comprehensive cold-start evaluation framework, 26+ models, unified pipeline and dataset division. HIGH confidence.
- **RecBole** (recbole.io) — Industry-standard recommendation benchmarking library. Evaluation settings documented at recbole.io/docs/user_guide/config/evaluation_settings.html. HIGH confidence.
- **DropoutNet** (github.com/layer6ai-labs/DropoutNet) — NeurIPS 2017 cold-start paper. Evaluation protocol with warm/cold splits. HIGH confidence.
- **"From Variability to Stability"** (openreview.net/pdf/c862940c9a8a8443b46f6b1d3d40fe67e585d1f7) — KDD 2024 benchmarking methodology. NDCG@10 as primary metric, Spearman correlation analysis. MEDIUM confidence (not yet verified in indexed proceedings).
- **MARec** (arxiv.org/pdf/2404.13298) — Cold-start paper with HR@k and NDCG@k, bootstrapped significance testing, +8.4% to +53.8% lifts. MEDIUM confidence.
- **SimRec** (arxiv.org/pdf/2410.22136) — Cold-start stratification by item frequency (0, <10, ≥10 occurrences). MEDIUM confidence.
- **SASRec + content initialization** (arxiv.org/pdf/2507.19473) — Learning curves with NDCG vs delta_max, cold/warm item split. MEDIUM confidence.
- **MEXT Research Plan Guide** (guides.scholarshipunion.com/mext/research-plan.html) — "Specific, testable research question; clear methodology with specific methods and data sources; semester-by-semester timeline." HIGH confidence.
- **MEXT 2026 Guidelines** (studyinjapan.go.jp/en/_mt/2025/04/01-2026_Research_Guidelines_E.pdf) — Official guidelines, interview assesses clarity of purpose. HIGH confidence.
- **PROJECT.md** — Precision@10 and NDCG@10, Popularity + Random baselines, MEXT July 2026 deadline. HIGH confidence (project authority).
