# CHANGELOG

**Research Theme:** Graph-Based Preference Initialisation for Cold-Start Recommendation in Zero-Interaction Domains
**Primary Objective:** Demonstrate feasibility and operational deployability of graph-based preference initialization

## Phase 5.1/7.1/8.1 — Evaluation Audit, USER_VECTOR, & Pipeline Validation (2026-06-06)

Two parallel sub-phase efforts transformed the architecture and evaluation methodology:

**Phase 5.1 — Evaluation Audit Remediation:** Discovered that NDCG@10 was computed as RR@10 (break on first relevant item, no accumulation). Ground truth used note-Jaccard >0.20, which is the same signal used to build the Jaccard graph — creating circular evaluation. Fix A (true NDCG@10) applied to `metrics.py` (committed). Fix B (brand+accord ground truth) proposed in `pipeline.py` / `run_bootstrap.py` with `GT_MODE=brand_accord` env var (committed, not default).

**Phase 7.1 — USER_VECTOR Migration:** The quiz information audit revealed that per-item ratings were sent in the frontend payload but discarded by the backend. Replaced the centroid pipeline for State 1 with a direct user-vector: weighted sum of quiz item embeddings → KNN retrieval. Proved +14.9% FH / +41.4% NDCG over centroid. `DispatchRequest.ratings` dual-purpose bug fixed via `quiz_ratings` / `ratings` split.

**Phase 8.1 — Dispatcher vs Legacy Validation:** 5-state dispatcher validated against legacy (State 0 top-5 identical). Detailed per-state comparison captured in Phase 8.1 CONTEXT.md.

## [Unreleased] — Phase 8 Dispatcher Activation & Quiz-Finalize Bridge (2026-06-05)

Activated Phase 8 dispatcher (config default True, docker-compose env var) and wired quiz-finalize bridge so the research pipeline (State 1 → GraphSAGE centroid → KNN → recommendations) executes end-to-end through the UI. Docker build fixed: `Dockerfile:45` now copies `scentrix_master.json` (not deleted `fra_elite_24k.json`).

**Files:** `config.py:18`, `docker-compose.yml:77`, `Dockerfile:45`, `StandardQuiz.tsx:102-122`, `app-store.ts`, `api.ts:79-90`, `hooks.ts:62-89`, `phase-e-verification.spec.ts`

**Outcome:** Playwright E2E proves 7-step pipeline: quiz → evaluate → accord confidence (13 accords) → recommendations with `source: "graphsage"`, `match_score: 81.65`. State 1 reachable from frontend per ARCHITECTURE-FREEZE.md.

**Low-severity:** `/finalize` requires JWT (guest persistence not bridged); uniform test accord weights; accord→catalog-item heuristic is design tradeoff; Neo4j schema warnings pre-existing.

## Waves 3A–4B — Frontend Integration & Bug Fixes (2026-06-01/02)

**Scope:** Unblocked anonymous cold-start (State 0), wired Star button rating, recommendation reason exposure, guest persistence fix, recommendation depth fix, fragrances page Suspense fix.

**Key changes:**
- `hooks.ts` — guest recs enabled for ALL states (empty ratings → State 0)
- `FragranceCard.tsx` — Star button replaces ShoppingBag; reason text displayed
- `reason-engine.ts` — computes reason from quiz responses (direct match → shared notes → shared accords → API fallback)
- `app-store.ts` — Zustand `merge` callback clears `quizResponses` on guest rehydration
- `feature_based.py` — `top_k=50` (was 12) for full candidate depth
- `dispatcher.py` — State 3 fallback popularity→graphsage; State 4 GraphSAGE exploration injection (2 items at positions 2,5); `_hydrate_from_catalog` match_score fix
- `fragrances/page.tsx` — Suspense boundary; no-filter shows full catalog
- `docker-compose.yml` — PostgreSQL host port 5432→5433

## GraphSAGE Preference Init Service (2026-05-30)

`gs_embeddings.py` — loads precomputed Jaccard embeddings [4559×64] at startup, weighted centroid computation, cosine-similarity KNN retrieval, disagreement instrumentation. No torch runtime dependency. Artifacts at `ml/models/serving/v1/`.

## Architecture Freeze (2026-05-30)

5-state dispatch architecture: dispatcher is single entry point, state machine routes by user state, extracted services over monolith, GraphSAGE is preference init (not inference runtime), legacy hybrid_search retained as fallback. See `ARCHITECTURE-FREEZE.md`.

## MEXT Demo (2026-05-28)

`mext_demo.html` (167.8KB, zero JS, 7 sections, 6-model comparison). Packaged ZIP with both `.pt` checkpoints. All 10 UAT tests passed. Reproduction: `python -m ml.eval.pipeline --mode pure_cold --seed 42`.

## Phase 5 — Research Differentiators (2026-05-28)

- GraphSAGE-Jaccard NDCG@10=0.504 vs Embedding 0.197 (63% relative degradation, p≤0.001, d=0.93)
- quiz_init does NOT reliably beat pure_cold (mean 0.496 vs 0.504, std 0.023)
- Stratification: Feature-Only leads all levels; GraphSAGE-Jaccard monotonic; Embedding non-monotonic
- Pipeline bug fix: `build_similarity_graph` → `build_jaccard_graph` in 3 functions

## Locked Research Claim (Phase 5 evaluation)

⚠️ **Evaluation status:** The claim below and all results tables in this changelog use the original pipeline methodology. Phase 5.1 evaluation audit found two flaws: (1) NDCG@10 was computed as RR@10, and (2) ground truth (note-Jaccard) was circular with the Jaccard graph. Under corrected pipeline (Fix A+B), the gap collapses from 2.7× to ~1.24×. The values below are the locked Phase 5 results pending formal re-evaluation under the corrected methodology. See Phase 5.1 CONTEXT.md for full audit findings and corrected numbers.

"Graph construction methodology is the critical determinant of GNN performance in cold-start recommendation. Embedding-derived similarity graphs introduce feature circularity that degrades NDCG by 63% relative to independent baselines. Replacing circular edges with structurally independent Jaccard similarity over fragrance notes recovers 2.7× performance improvement (NDCG 0.183 → 0.494, p≤0.001, d=0.93)."

## Phase History

| Phase | Status | Key Output |
|---|---|---|---|
| 1–4 | ✅ | Data pipeline, eval infra, baselines, GraphSAGE pipeline |
| 5 | ✅ | quiz_init, sensitivity, stratification, paper locked |
| 5.1 | ✅ | Evaluation Audit Remediation (RR→NDCG, circular GT) |
| 5.2 | ✅ | GT Method Selection (brand+accord ground truth) |
| 6 | ✅ | MEXT Demo |
| 6.5 | ✅ | Architecture Freeze |
| 7 | ✅ | Preference Init Service (centroid) |
| 7.1 | ✅ | USER_VECTOR Migration (centroid → direct user-vector) |
| 8 | ✅ | 5-State Dispatcher |
| 8.1 | ✅ | Dispatcher vs Legacy Validation |
| 8a | ✅ | Direct Rating MVP + Frontend Integration |
| 9–12 | 🔲 | Planned (Graph Sync, Auth, Frontend, Observability) |

## Requirement Traceability

20 v1 requirements (PIPE-01–03, EVAL-01–07, RSCH-01–07, DEMO-01–03) — all complete across Phases 1–6. 12 v2 requirements (SRV-01–10) — Phases 7–8 complete, 9–12 planned.

| Phase | Requirements |
|-------|-------------|
| 1 | PIPE-01, PIPE-02 |
| 2 | EVAL-01, EVAL-02, EVAL-03 |
| 3 | EVAL-04, EVAL-05, EVAL-06, EVAL-07 |
| 4 | RSCH-01, RSCH-02 |
| 5 | PIPE-03, RSCH-03, RSCH-04, RSCH-05, RSCH-06, RSCH-07 |
| 6 | DEMO-01, DEMO-02, DEMO-03 |
| 7 | SRV-01, SRV-02a |
| 8 | SRV-02, SRV-02b |
| 9 | SRV-03 |
| 10 | SRV-04, SRV-05 |
| 11 | SRV-06 |
| 12 | SRV-07, SRV-08, SRV-09, SRV-10 |

**Coverage:** 32 requirements mapped, 0 unmapped. Out of scope: production deployment, mobile app, OAuth, notifications, payments, admin dashboard, multi-language, full user study.

## Results (original pipeline — evaluation under audit, see note above)

| Model | Reported (RR@10 labeled NDCG@10) |
|---|---|
| GraphSAGE-Jaccard (pure_cold) | **0.504** |
| GraphSAGE-Embedding (pure_cold) | **0.197** |
| GraphSAGE-Jaccard (quiz_init) | **0.405** |
| Feature-Only | **0.557** |
| Content-Only (oracle) | **0.581** |
| Popularity | **0.008** |
| Random | **0.021** |

**Bootstrap (n=10000):** Jaccard vs Embedding: p≤0.001, d=0.93. Jaccard vs Feature-Only: p=1.000, d=-0.149.
