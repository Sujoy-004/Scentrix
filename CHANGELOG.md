# CHANGELOG

**Research Theme:** Graph-Based Preference Initialisation for Cold-Start Recommendation in Zero-Interaction Domains
**Primary Objective:** Demonstrate feasibility and operational deployability of graph-based preference initialization

## Phase 5.1/7.1/8.1 — Evaluation Audit, USER_VECTOR, & Pipeline Validation (2026-06-06)

Two parallel sub-phase efforts transformed the architecture and evaluation methodology:

**Phase 5.1 — Evaluation Audit Remediation:** Discovered that NDCG@10 was computed as RR@10 (break on first relevant item, no accumulation). Ground truth used note-Jaccard >0.20, which is the same signal used to build the Jaccard graph — creating circular evaluation. Fix A (true NDCG@10) applied to `metrics.py` (committed). Fix B (brand+accord ground truth) implemented in `pipeline.py` / `run_bootstrap.py` with `GT_MODE=brand_accord` env var and executed (2026-06-07). All published numbers superseded by reproducible Fix B results; see main table below.

**Phase 7.1 — USER_VECTOR Migration:** The quiz information audit revealed that per-item ratings were sent in the frontend payload but discarded by the backend. Replaced the centroid pipeline for State 1 with a direct user-vector: weighted sum of quiz item embeddings → KNN retrieval. Proved +14.9% FH / +41.4% NDCG over centroid. `DispatchRequest.ratings` dual-purpose bug fixed via `quiz_ratings` / `ratings` split.

**Phase 8.1 — Dispatcher vs Legacy Validation:** 5-state dispatcher validated against legacy (State 0 top-5 identical). Detailed per-state comparison captured in Phase 8.1 CONTEXT.md.

## Phase 11 — Quiz Flow Integration (2026-06-07)

Phase 11 delivered the end-to-end quiz flow across four waves of frontend and backend work, completing the user-facing recommendation pipeline.

### Wave 1 — Guest Quiz Persistence

**Files:** `backend/app/routers/quiz.py`, `backend/app/schemas/schemas.py`, `frontend/src/components/StandardQuiz.tsx`

- Added `POST /fragrances/quiz/session/{session_id}/guest-finalize` endpoint using `get_optional_user_id` (no JWT requirement for guests, delegates to DB upsert for authenticated users).
- Guest quizzes persist in Redis (session store); authenticated quizzes sync to `FragranceRating` table.
- `StandardQuiz.tsx` calls `guestFinalizeQuizSession` after quiz completion.
- No new DB tables, no schema migrations.

### Wave 2 — StateIndicator + Cold→Warm Transition UX

**Files:** `frontend/src/components/StateIndicator.tsx`, `frontend/src/app/recommendations/page.tsx`, `frontend/src/app/recommendations/recommendations.css`, `backend/app/services/dispatcher.py`, `backend/app/routers/recommendations.py`

- `StateIndicator.tsx` component covers all 5 states with descriptions, strategies, next-action CTAs, and progress bars for States 1–3.
- `/recommendations` page header is state-aware (5 distinct badge/title/subtitle sets per state).
- Backend: `state` (int 0–4) and `state_label` added as optional fields on `StandardResponse` — backward-compatible.
- `DispatchResult` carries `state` + `state_label` from the 5-state machine.

### Wave 3A — Last Quiz Summary

**Files:** `backend/app/schemas/schemas.py`, `backend/app/routers/recommendations.py`, `frontend/src/lib/api.ts`, `frontend/src/lib/hooks.ts`, `frontend/src/app/profile/history/page.tsx`, `frontend/src/app/profile/history/history.css`

- `GET /recommendations/quiz-summary` returns `QuizSummaryResponse` (`has_completed_quiz`, `completed_at`, `total_rated`, `average_rating`, `average_normalized`, `rating_distribution`, `top_matches`, `top_notes`, `top_accords`).
- `/profile/history` page rewritten: removed fake 3-entry timeline, rendered single real summary card from `useQuizSummary()` hook.
- All data computed from existing `FragranceRating` + `FeatureBasedService.score()` + `load_recommendation_catalog` — no new services or tables.

### Wave 3B — Quiz Flow Polish

**Files:** `frontend/src/components/StandardQuiz.tsx`, `frontend/src/app/quiz/quiz.css`

- **Extension flow:** After last seed question, calls `evaluateSession({force:false})`. If `extension_required`, shows prompt with confidence band and question count; accepting fetches more questions via `getNextQuizQuestions`, appends to queue, continues rating.
- **Loading overlay:** Dual-ring neural spinner + "Synthesizing Your Neural Profile" during finalization.
- **Success screen:** "Discovery Protocol Complete" with stats (scents rated, confidence level) and "View Your Recommendations" CTA.
- **Error handling:** All 3 previously silent `.catch(console.warn)` sites replaced with visible inline error banners on loading/success screens (non-blocking, fail open).

### Test inventory (updated 2026-06-07)

160 backend tests across 10 files — all pass. 14 dedicated Phase 11 tests (`test_phase11_quiz.py`) cover guest-finalize, quiz-summary, state/state_label, and negative paths. 9 in-repo smoke tests (`test_e2e_smoke.py`) validate the full guest quiz lifecycle. The pre-existing `test_health.py` assertion gap was fixed. Frontend has Playwright E2E tests (6 spec files) and visual regression snapshots (ignored — generated on first run). Smoke test migrated from external temp file into the repository.

## Phase 12 — Observability (2026-06-07)

Phase 12 delivered observability for the MEXT demo across two sub-phases, with SRV-08 deferred and SRV-10 dropped per scope reduction.

### Phase 12A — Structured Logging (SRV-07 — Complete)

**Files:** `backend/app/logging_config.py` (NEW), `backend/app/middleware.py` (NEW), `backend/app/main.py` (modified), `backend/app/routers/recommendations.py` (modified), `backend/app/routers/quiz.py` (modified)

- Correlation ID middleware at `backend/app/middleware.py` — reads `X-Correlation-ID` request header or generates a new one; sets response header; stores in async-safe `contextvars.ContextVar`.
- `CorrelationIDLogger` filter in `backend/app/logging_config.py` — appends `[correlation_id=...]` to every log record.
- 10 structured event types: `recommendation_request`, `recommendation_result`, `dispatcher_gate`, `ml_lazy_load`, `quiz_start`, `quiz_answer`, `quiz_evaluate`, `quiz_finalize`, `quiz_error`, `error`.
- All three recommendation endpoints logged (guest State 0/1, personalized). All six quiz endpoints logged. Error handlers in `main.py` include `correlation_id`.
- Zero new dependencies — uses stdlib `logging` only.

### Phase 12B — Load Testing (SRV-09 — Complete)

**Files:** `backend/tests/load/locustfile.py` (NEW), `backend/tests/load/README.md` (NEW), `backend/requirements.txt` (modified)

- Tool: Locust 2.44.1 (Python-native, single `pip install locust`).
- 4 scenarios: Health check, Guest rec State 0 (popularity), Guest rec State 1 (GraphSAGE), Quiz session start.
- Dynamic fragrance ID discovery from live catalog at startup.
- Validation: import check → dry run (1 user, 10s) → full ramp (20 users, 2/s ramp, 5 min).
- 1,875 requests, 1,561 successful (0 true errors). 314 expected 429s from quiz rate limiter.
- All 8 success criteria PASS.

### SRV-08 — Performance Monitoring (Deferred)

Not implemented. Prometheus `/metrics` endpoint would expose request duration, error count, and correlation ID throughput. Deferred — not needed for MEXT demo scope.

### SRV-10 — Dashboards & Alerting (Dropped)

Dropped per Phase 12 scope reduction. Grafana dashboards, PagerDuty/Slack alerting are enterprise operational concerns irrelevant to a research demo.

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

⚠️ All numerical values below are from the original pipeline (circular jaccard GT, RR-as-NDCG). Superseded by Fix B canonical results in the table below.

- GraphSAGE-Jaccard NDCG@10=0.504 vs Embedding 0.197 (old pipeline — not reproducible under corrected methodology)
- quiz_init does NOT reliably beat pure_cold (mean 0.496 vs 0.504, std 0.023 — old pipeline)
- Pipeline bug fix: `build_similarity_graph` → `build_jaccard_graph` in 3 functions

## Archived Research Claim (Phase 5 evaluation — historical)

⚠️ **Historical record only.** The claim below and all old-pipeline results tables have been superseded by Fix B (brand_accord GT, true NDCG). The "2.7× improvement" was an artifact of circular evaluation (jaccard GT + RR-as-NDCG). Under non-circular evaluation, the Jaccard-vs-Embedding gap is 1.21× (0.115 vs 0.095), and Feature-Only dominates both at 0.399 NDCG. See the canonical results table below for current metrics.

*Archived claim: "Graph construction methodology is the critical determinant of GNN performance in cold-start recommendation. Embedding-derived similarity graphs introduce feature circularity that degrades NDCG by 63% relative to independent baselines. Replacing circular edges with structurally independent Jaccard similarity over fragrance notes recovers 2.7× performance improvement (NDCG 0.183 → 0.494, p≤0.001, d=0.93)."*

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
| 9 | ❌ | Out of Scope — graph sync irrelevant for static MEXT dataset |
| 10 | ⚠️ | Reduced Scope — guest persistence merged into Phase 11 |
| 11 | ✅ | Quiz Flow Integration — 5 deliverables across Waves 1–3B |
| 12A | ✅ | Structured Logging — correlation IDs across rec/quiz endpoints |
| 12B | ✅ | Load Testing — Locust, 4 scenarios, 20 users, all criteria PASS |
| 12C | ⏭️ | Performance Monitoring — deferred for MEXT scope |
| 12D | ❌ | Dashboards & Alerting — dropped per scope reduction |

## Requirement Traceability

20 v1 requirements (PIPE-01–03, EVAL-01–07, RSCH-01–07, DEMO-01–03) — all complete across Phases 1–6. 12 v2 requirements (SRV-01–10) — Phases 7–8 and 11 complete; Phases 9–10 dropped/rescoped; Phase 12A (SRV-07) and 12B (SRV-09) complete; 12C (SRV-08) deferred; 12D (SRV-10) dropped.

| Phase | Requirements | Status |
|-------|-------------|--------|
| 1 | PIPE-01, PIPE-02 | ✅ |
| 2 | EVAL-01, EVAL-02, EVAL-03 | ✅ |
| 3 | EVAL-04, EVAL-05, EVAL-06, EVAL-07 | ✅ |
| 4 | RSCH-01, RSCH-02 | ✅ |
| 5 | PIPE-03, RSCH-03, RSCH-04, RSCH-05, RSCH-06, RSCH-07 | ✅ |
| 6 | DEMO-01, DEMO-02, DEMO-03 | ✅ |
| 7 | SRV-01, SRV-02a | ✅ |
| 8 | SRV-02, SRV-02b | ✅ |
| 9 | SRV-03 | ❌ Out of Scope |
| 10 | SRV-04, SRV-05 | ⚠️ Reduced Scope |
| 11 | SRV-06 | ✅ |
| 12A | SRV-07 | ✅ Complete |
| 12B | SRV-09 | ✅ Complete |
| 12C | SRV-08 | ⏭️ Deferred |
| 12D | SRV-10 | ❌ Dropped |

**Coverage:** 32 requirements mapped, 0 unmapped. Out of scope: production deployment, mobile app, OAuth, notifications, payments, admin dashboard, multi-language, full user study.

## Canonical Results (Fix B applied — brand_accord GT, true NDCG@10)

All values from reproducible pipeline: `SCENTRIX_EVAL_GT_MODE=brand_accord python -m ml.eval.pipeline --mode pure_cold --seed 42`.

| Model | Precision@10 | NDCG@10 | Recall@10 |
|---|---|---|---|
| GraphSAGE-Jaccard | 0.0567 | **0.115** | 0.1396 |
| GraphSAGE-Embedding | 0.0550 | **0.095** | 0.1075 |
| Feature-Only | 0.1825 | **0.399** | 0.4136 |
| Content-Only | 0.0193 | **0.047** | 0.0465 |
| Popularity | 0.0000 | **0.000** | 0.0000 |
| Random | 0.0007 | **0.001** | 0.0012 |

**Bootstrap (n=10000, brand_accord GT):** Jaccard vs Embedding: p=0.008, d=0.11 (Jaccard leads by 1.21×). Jaccard vs Feature-Only: p=1.000, d=−0.96 (Feature-Only leads by 3.47×).
