# Roadmap: Scentrix Cold-Start Recommendation Evaluation

## Overview

Scentrix is transitioning from a broken E2E fragrance discovery app into a research platform for cold-start recommendation experiments. This roadmap builds the evaluation infrastructure and research pipeline that enables valid, reproducible cold-start experiments for the MEXT interview demo (July 2026). The dependency chain is: fix pipeline crashes → build evaluation infrastructure → baseline recommenders → GraphSAGE pipeline → research differentiators → MEXT demo. Each phase delivers a coherent, verifiable capability that unblocks the next.

## Phases

- [x] **Phase 1: Pipeline & Data Foundation** - Fix broken pipeline components and prepare fragrance graph data for experiments
- [ ] **Phase 2: Evaluation Infrastructure** - Cold-start-aware data splitting, metric computation via ranx, and reproducibility config
- [ ] **Phase 3: Baselines & Comparison** - Popularity + Random baselines, results aggregation, bootstrap significance testing
- [ ] **Phase 4: GraphSAGE Pipeline** - GraphSAGE evaluation wrapper and full orchestration pipeline for cold-start inference
- [ ] **Phase 5: Research Differentiators** - Quiz-initialized GraphSAGE, stratification, ablation study, learning curves, debiasing
- [ ] **Phase 6: MEXT Demo** - Static HTML demo page, live recommendation example, reproducible results package

## Phase Details

### Phase 1: Pipeline & Data Foundation
**Goal**: Fix broken pipeline components so the system can start and fragrance graph data is ready for experiments.
**Depends on**: Nothing (first phase)
**Requirements**: PIPE-01, PIPE-02
**Success Criteria** (what must be TRUE):
  1. Docker stack starts without crashes — Celery worker no longer crashes with missing `celery_app.py` module
  2. `recommend_by_text` and `recommend_by_profile` endpoints return proper responses (not 503) — either implemented correctly or cleanly removed with documented rationale
  3. Fragrance dataset is preprocessed, cleaned, and normalized from `ml/data/scentrix_master.json` into Neo4j-ready format
  4. Neo4j fragrance graph is populated with similarity edges, note relationships, and note-fragrance connections
**Plans**: 4 plans (Wave 1-3)
Plans:
- [x] 01-01-PLAN.md — Remove Celery worker + scikit-learn dependency (Wave 1)
- [x] 01-02-PLAN.md — Remove 4 dead 503 endpoints + frontend scrub (Wave 1)
- [x] 01-03-PLAN.md — Create Neo4j graph service + import rewiring (Wave 2)
- [x] 01-04-PLAN.md — Create fragrance ingestor + data preprocessing (Wave 3)

### Phase 2: Evaluation Infrastructure
**Goal**: Cold-start-aware evaluation harness that produces valid, reproducible metric computations aligned with RecSys standard practices.
**Depends on**: Phase 1
**Requirements**: EVAL-01, EVAL-02, EVAL-03
**Success Criteria** (what must be TRUE):
  1. ColdStartSplitter produces train/test splits with zero cold-start user contamination — temporal split + leave-cold-out strategies both operational
  2. Metric computation returns Precision@10, NDCG@10, and Recall@10 via ranx using all-ranking protocol (not sampled negatives)
  3. Evaluation is config-driven (YAML/JSON): changing seed produces different but valid splits with full reproducibility
  4. Evaluation artifacts persist to `ml/eval/runs/{timestamp}/` with complete metadata (config used, seed, all outputs)
**Plans**: 4 plans (Wave 1-2)
Plans:
- [ ] 02-01-PLAN.md — Config + Dependencies + Test Fixtures (Wave 1)
- [ ] 02-02-PLAN.md — ColdStartSplitter + Strategies (Wave 1)
- [ ] 02-03-PLAN.md — MetricsWrapper + ranx computation (Wave 1)
- [ ] 02-04-PLAN.md — Pipeline Orchestrator + CLI + Persistence (Wave 2)

### Phase 3: Baselines & Comparison
**Goal**: Baseline recommenders produce expected results and comparison infrastructure surfaces model differences with statistical rigor.
**Depends on**: Phase 2
**Requirements**: EVAL-04, EVAL-05, EVAL-06, EVAL-07
**Success Criteria** (what must be TRUE):
  1. Popularity baseline returns items ranked by global popularity (verifiable against raw interaction counts in training data)
  2. Random baseline returns uniformly random shuffles with uniform expected score distribution across repeated runs
  3. ResultsAggregator produces per-user metric histograms and comparison tables across all models (plain-text + Markdown + JSON)
  4. Bootstrap significance testing (paired BCa confidence intervals + sign-flip permutation test) produces valid p-values and interval estimates
**Plans**: 2 plans (Wave 1-2)

Plans:
- [x] 03-01-PLAN.md — Popularity and random baselines (Wave 1)
- [x] 03-02-PLAN.md — Results aggregation and significance testing (Wave 2)

### Phase 4: GraphSAGE Pipeline
**Goal**: GraphSAGE model integrates with evaluation pipeline for cold-start inductive inference on unseen nodes.
**Depends on**: Phase 3
**Requirements**: RSCH-01, RSCH-02
**Success Criteria** (what must be TRUE):
  1. GraphSAGE wrapper produces recommendations for cold-start nodes with zero training interactions via inductive inference (no transductive lookup)
  2. `run_evaluation(config)` runs end-to-end: load data → build graph → cold-start split → train GraphSAGE → infer → aggregate → persist
  3. Pipeline handles edge cases correctly: degree-0 cold nodes use feature-only fallback, missing features gracefully handled, evaluation config controls all parameters
**Plans**: 1 plan (Wave 1)

Plans:
- [x] 04-01-PLAN.md — GraphSAGE wrapper with contrastive learning, KNN graph construction, and full pipeline integration (Wave 1)

### Phase 5: Research Differentiators
**Goal**: Core research claims are validated through quiz-initialized evaluation, stratification, ablation study, learning curves, and popularity debiasing.
**Depends on**: Phase 4
**Requirements**: PIPE-03, RSCH-03, RSCH-04, RSCH-05, RSCH-06, RSCH-07
**Success Criteria** (what must be TRUE):
  1. Adaptive confidence-scored quiz connects to GraphSAGE inference → recommendation output E2E (no more 503 errors) — user can take quiz and see recommendations
  2. Quiz-initialized GraphSAGE evaluation runs in three operational modes: pure cold-start, quiz-initiated cold-start, warm-start reference
  3. Cold-start stratification 3×3 grid (3 coldness levels × 3 models) shows differentiated performance — reveals where each model excels/fails
  4. Learning curve plot shows NDCG@10 improving with quiz length k ∈ {1,3,5,7,10} — quantifies value of each additional quiz question
  5. Ablation study isolates contribution of content-only, structure-only, and full GraphSAGE variants on cold-start accuracy
  6. Popularity debiasing report tracks catalog coverage, popularity-stratified NDCG, and long-tail distribution alongside accuracy metrics
**Plans**: 2 plans (Wave 1-2)

Plans:
- [ ] 05-01-PLAN.md — Quiz-Init Evaluation Foundation: config, quiz simulator, three-mode evaluation branching (Wave 1)
- [ ] 05-02-PLAN.md — Research Experiments: stratification grid, learning curves, ablation study, popularity debiasing (Wave 2)

### Phase 6: MEXT Demo
**Goal**: Demo package ready for MEXT interview presentation with reproducible results and visualized research narratives.
**Depends on**: Phase 5
**Requirements**: DEMO-01, DEMO-02, DEMO-03
**Success Criteria** (what must be TRUE):
  1. Static HTML demo page loads without Docker in any browser and shows: comparison table, stratification bar chart, learning curve plot
  2. "Live" recommendation example walks through quiz → recommendation flow with actual (non-cherry-picked) outputs from the evaluation pipeline
  3. Reproducible results package in timestamped directory includes: config file, seed, all model outputs, plots, and README with reproduction instructions
**Plans**: 2 plans (Wave 1)
**UI hint**: yes
Plans:
- [ ] 06-01-PLAN.md — Static HTML demo page generator with 7-section narrative, comparison tables, embedded plots, and live recommendation example (Wave 1)
- [ ] 06-02-PLAN.md — Reproducible results package: ZIP archive with config, seed, splits, plots, model, README, and demo HTML (Wave 1)

## Progress

**Execution Order:** Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Pipeline & Data Foundation | 4/4 | Complete | 2026-05-22 |
| 2. Evaluation Infrastructure | 4/4 | Complete | 2026-05-23 |
| 3. Baselines & Comparison | 2/2 | Complete | 2026-05-25 |
| 4. GraphSAGE Pipeline | 1/1 | Complete | 2026-05-25 |
| 5. Research Differentiators | 0/2 | Planned | 2026-05-25 |
| 6. MEXT Demo | 0/2 | Planned | — |
