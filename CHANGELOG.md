# CHANGELOG

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

160 backend tests across 10 files — all pass. 14 dedicated Phase 11 tests (`test_phase11_quiz.py`) cover guest-finalize, quiz-summary, state/state_label, and negative paths. 9 in-repo smoke tests (`test_e2e_smoke.py`) validate the full guest quiz lifecycle. Frontend has Playwright E2E tests (6 spec files) and visual regression snapshots (ignored — generated on first run).

## Phase 12 — Observability (2026-06-07)

### Phase 12A — Structured Logging

**Files:** `backend/app/logging_config.py` (NEW), `backend/app/middleware.py` (NEW), `backend/app/main.py` (modified), `backend/app/routers/recommendations.py` (modified), `backend/app/routers/quiz.py` (modified)

- Correlation ID middleware — reads `X-Correlation-ID` request header or generates a new one; sets response header; stores in async-safe `contextvars.ContextVar`.
- `CorrelationIDLogger` filter appends `[correlation_id=...]` to every log record.
- 10 structured event types: `recommendation_request`, `recommendation_result`, `dispatcher_gate`, `ml_lazy_load`, `quiz_start`, `quiz_answer`, `quiz_evaluate`, `quiz_finalize`, `quiz_error`, `error`.
- All three recommendation endpoints logged. All six quiz endpoints logged.
- Zero new dependencies — uses stdlib `logging` only.

### Phase 12B — Load Testing

**Files:** `backend/tests/load/locustfile.py` (NEW), `backend/tests/load/README.md` (NEW), `backend/requirements.txt` (modified)

- Tool: Locust 2.44.1 (Python-native, single `pip install locust`).
- 4 scenarios: Health check, Guest rec State 0 (popularity), Guest rec State 1 (GraphSAGE), Quiz session start.
- Dynamic fragrance ID discovery from live catalog at startup.
- Validation: import check → dry run (1 user, 10s) → full ramp (20 users, 2/s ramp, 5 min).
- 1,875 requests, 1,561 successful (0 true errors). 314 expected 429s from quiz rate limiter.
- All 8 success criteria PASS.

## [Unreleased] — Phase 8 Dispatcher Activation & Quiz-Finalize Bridge (2026-06-05)

Activated Phase 8 dispatcher (config default True, docker-compose env var) and wired quiz-finalize bridge so the research pipeline executes end-to-end through the UI. Docker build fixed: `Dockerfile:45` now copies `scentrix_master.json`.

**Files:** `config.py:18`, `docker-compose.yml:77`, `Dockerfile:45`, `StandardQuiz.tsx:102-122`, `app-store.ts`, `api.ts:79-90`, `hooks.ts:62-89`, `phase-e-verification.spec.ts`

**Outcome:** Playwright E2E proves 7-step pipeline: quiz → evaluate → accord confidence → recommendations with `source: "graphsage"`, `match_score: 81.65`. State 1 reachable from frontend.

## Waves 3A–4B — Frontend Integration & Bug Fixes (2026-06-01/02)

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

## Phase History

| Phase | Status | Key Output |
|---|---|---|
| 1–4 | ✅ | Data pipeline, eval infra, baselines, GraphSAGE pipeline |
| 5 | ✅ | Research differentiators, quiz_init, sensitivity, stratification |
| 6 | ✅ | MEXT Demo |
| 6.5 | ✅ | Architecture Freeze |
| 7 | ✅ | Preference Init Service (centroid + USER_VECTOR) |
| 8 | ✅ | 5-State Dispatcher + Frontend Integration |
| 11 | ✅ | Quiz Flow Integration — guest persistence, state-aware UI, quiz summary |
| 12A | ✅ | Structured Logging — correlation IDs across rec/quiz endpoints |
| 12B | ✅ | Load Testing — Locust, 20 users, all criteria PASS |
