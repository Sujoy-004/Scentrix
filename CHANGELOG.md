# CHANGELOG

## [Unreleased] — Phase 8 Complete, Repository Hardening

### Repository State Consolidation (2026-06-01)

**Scope:** Repository state audit, git hygiene sweep, CHANGELOG update.

**Deliverables:**
- `CURRENT_PRODUCT_POSITION.md` created — product position snapshot for handoff continuity
- `REPOSITORY_STATE_2026-06-01.md` created — repository state snapshot for handoff continuity
- CHANGELOG.md updated with all 2026-06-01 work entries
- Drift audit completed across 6 canonical docs — 1 HIGH drift found (CHANGELOG itself), rest clean
- Git hygiene sweep completed — 12 commit, 1 delete, 3 ignore classifications
- `repo_tree.txt` deleted (regeneratable artifact)
- `.gitignore` updated to exclude `response.md`, `fresh-state-0.png`, `state0.png`

### Recommendation Reason Exposure (2026-06-01)

**Context:** Recommendation Intelligence Exposure Audit accepted. Smallest-possible UI change to surface existing backend intelligence.

**Files modified:**
- `frontend/src/components/FragranceCard.tsx` — reason text added as "Why Recommended" section in card body (below notes, above rating). Uses existing `frag.reason` field from API plus local `computeReason()` engine as fallback.
- `frontend/src/lib/reason-engine.ts` — created. Computes reason text from quizResponses array: direct match, shared notes, shared accords, then falls back to API `frag.reason`.
- `frontend/src/app/recommendations/page.tsx` — `reason?: string` added to `FragranceRecommendation` interface.

**Values displayed (already in API, never rendered):**
- State 0: "Popular Choice" on every card
- State 2–4: "Olfactory Soulmate", "Discovered for you", "Harmonious Discovery", "Atmospheric Resonance"

**Zero-backend-work constraint honored:** No new endpoints, fields, algorithms, GraphSAGE changes, or dispatcher changes.

### Documentation Alignment (2026-06-01)

**Files modified:**
- `ARCHITECTURE-FREEZE.md` — State 1 Implementation Note added: "State 1 remains architecturally valid but quiz→recommendations pipeline not wired; Direct Rating MVP routes State 0→State 2 via Star button"
- `README.md` — "the product" section extracted from "the architecture" section; "run the web app" subsection added; `docker compose up` command documented
- `backend/README.md` — Service Architecture table added (dispatcher, gs_embeddings, feature_based, popularity, hybrid_search, quiz_store); verb updated to reflect Direct Rating MVP

### Direct Rating MVP — Frontend & Dispatcher Follow-up (2026-06-01)

**Scope:** Unblocked anonymous cold-start (State 0), wired Star button rating, improved State 3/4 dispatch fallbacks.

**Frontend — State 0 unblocked:**
- `frontend/src/lib/hooks.ts` — guest recommendation query enabled for ALL states (removed `quizResponses.length > 0` gate; empty array triggers State 0 popularity path on backend)
- `frontend/src/app/recommendations/page.tsx` — quiz gate removed (anonymous users with zero ratings see recommendations immediately); conditional header: "Popular Picks"/"Popular Fragrances" at State 0 vs "Protocol Results Complete"/"Your Aromatic Constellation" at State 2+; guest banner text conditional on rating count; discovery state meter added (Cold Exploration → Taste Initialising → Taste Active → Taste Mature); match_score display gated by `ratingCount > 0` (hidden during State 0)

**Frontend — Star rating wired:**
- `frontend/src/components/FragranceCard.tsx` — ShoppingBag button replaced with Star button; `handleRate` writes to both local `addQuizResponse` (session state) and `useSubmitRating` (backend); `isRated` state tracked and reflected in Star fill color; `useSubmitRating` hook imported

**Backend — State 3 fallback chain:**
- `backend/app/services/dispatcher.py` — FeatureBasedStrategy fallback changed from `popularity` to `graphsage` (when feature-based scoring fails, attempt GraphSAGE centroid retrieval before giving up); fallback_chain updated accordingly

**Backend — State 4 GraphSAGE exploration:**
- `backend/app/services/dispatcher.py` — FeatureWithDiversityStrategy: GraphSAGE centroid KNN retrieval injected (top-20 excluding FB + seed IDs, insert top-2 at positions 2 and 5) as exploration items with `source="exploration"`

**Backend — match_score hydration fix:**
- `backend/app/services/dispatcher.py` — `_hydrate_from_catalog`: `match_score` now reads `item.get("match_score", ...)` first, falls back to `item.get("score", ...)` only if match_score absent (fixes items where score was double-multiplied or missing)

**Backend — Tests:**
- `backend/tests/test_dispatcher.py` — `test_state_3_fallback_to_graphsage` added (proves State 3 falls back to GS when FB raises); `test_diversity_gs_exploration_appears` added (proves exploration items with `source="exploration"` appear in State 4 output); `TestSourceAttribution.test_source_attribution_per_state` updated to accept `"exploration"` alongside `"diversity"`

**Infrastructure:**
- `docker-compose.yml` — PostgreSQL host port changed from `5432` to `5433` (avoids conflict with local Postgres instances)

### Repository Hardening (2026-05-31)

**Scope:** Waves 1-4 per REPOSITORY_HARDENING_PLAN.md — delete, archive, test structure, doc pruning.

**Deliverables:**
- CHANGELOG.md updated with all entries
- ARCHITECTURE-FREEZE.md promoted from `.planning/` to repository root
- README.md pruned: phase status table removed, architecture diagram replaced with link to ARCHITECTURE-FREEZE.md
- `.planning/PROJECT.md` pruned: redundant description replaced with pointer to README/CHANGELOG
- `report.md` findings merged into CHANGELOG, report.md archived
- `.planning/REPOSITORY_HARDENING_EXECUTION_1.md` created

### Cleanup Wave 3 — Test Structure (2026-05-31)

**Actions:**
- `backend/tests/test_phase8_integration.py` — VERIFIED non-redundant (tests HTTP endpoint wiring layer, distinct from test_dispatcher.py), KEPT
- `backend/tests/benchmark_sla.py` — MOVED to `backend/scripts/benchmark_sla.py` (not a pytest test, SLA benchmark script)
- `ml/tests/test_graph.py` vs `backend/tests/test_graph.py` — VERIFIED no duplication (backend/test_graph.py does NOT exist), KEPT both

### Cleanup Wave 2 — Archive Completed-Phase Docs (2026-05-31)

**Archived to `.planning/_archive/`:**
- `.planning/phases/08-dispatcher-integration/` (7 Phase 8 design docs)
- `.planning/PHASE7_8_CLEANUP_WAVE1.md`, `WAVE2.md`, `WAVE3.md`
- `.planning/PHASE7_8_CLEANUP_INVENTORY.md`
- `docs/architecture.md` — pre-freeze, superseded by ARCHITECTURE-FREEZE.md
- `.planning/codebase/ARCHITECTURE.md` — superseded by freeze

### Cleanup Wave 1 — Delete Obsolete Files (2026-05-31)

**Deleted:**
- `query.txt` — session handoff, content subsumed by CHANGELOG
- `.planning/SPEC.md` — trivial redirect stub
- `.planning/_archive/SPEC.md` — obsolete pre-pivot Railway doc

### 5-State Recommendation Dispatcher (2026-05-31)

**Phase 8 status:** ✅ COMPLETE.

**Deliverables:**
- `backend/app/services/dispatcher.py` — 5-state dispatch tree: anonymous/popularity, quiz/GraphSAGE, cold/hybrid β-blend, warm/feature-based, mature/diversity injection
- `backend/app/services/feature_based.py` — extracted from hybrid_search: accord/note scoring service
- `backend/app/services/popularity.py` — extracted from hybrid_search: popularity ranking service
- `backend/app/services/gs_embeddings.py` — extracted from ML-serving: GraphSAGE centroid+KNN retrieval
- `backend/app/services/hybrid_search.py` — retained as legacy fallback behind `PHASE8_DISPATCHER_ENABLED` flag
- `backend/tests/test_dispatcher.py` — 90+ tests covering all 5 states, fallback chains, error propagation, diversity injection
- Integration wiring in `backend/app/routers/recommendations.py`

**Architecture:** Per ARCHITECTURE-FREEZE.md. Dispatcher is the single entry point. Extracted services are peers. Legacy hybrid_search retained behind feature flag.

**Known remaining items (not blocking):**
1. `backend/app/config.py:18` — `phase8_dispatcher_enabled` defaults to `False`; flip to `True` to route all traffic through dispatcher
2. `backend/app/services/catalog.py` — Neo4j Cypher query needs `f.rating_count as rating_count` for PopularityStrategy sorting
3. Legacy code extraction from `backend/app/services/hybrid_search.py` — dead branches remain behind flag; planned for code purge (post-hardening)

### GraphSAGE Preference Init Service (2026-05-30)

**Phase 7 status:** ✅ COMPLETE.

**Deliverables:**
- `backend/app/services/gs_embeddings.py` — GraphSAGE Preference Initialization Service: loads precomputed Jaccard embeddings at startup, weighted centroid computation, cosine-similarity KNN retrieval, disagreement instrumentation
- Canonic artifacts at `ml/models/serving/v1/`: `node_embeddings_jaccard.npy` [4559×64], `node_ids_jaccard.json`, `metadata.json`
- Export pipeline: `ml/export/export_jaccard_embeddings.py`
- Wired into `/health` endpoint and FastAPI lifespan — fails startup on invalid artifacts

**Key property:** No checkpoint loading, no model inference, no torch runtime dependency.

### Architecture Freeze (2026-05-30)

**Phase 6.5 status:** ✅ COMPLETE.

**Deliverables:**
- `.planning/ARCHITECTURE-FREEZE.md` (403 lines, now promoted to `ARCHITECTURE-FREEZE.md` at root)
- 5-state dispatch architecture with 9 principles:
  1. Dispatcher is single entry point
  2. State machine routes by user state
  3. Extracted services over monolith
  4. Feature flag with phased rollover
  5. Disagreement instrumentation logged, not served
  6. GraphSAGE is preference init, not inference runtime
  7. Hybrid search retained as legacy fallback
  8. Cache strategy: per-user TTL, no state in key
  9. All extracted services are stateless

### MEXT Demo (2026-05-28)

**Phase 6 status:** ✅ COMPLETE.

**Deliverables:**
- `mext_demo.html` generated at `ml/eval/runs/20260528_165737/mext_demo.html`, 167.8KB, zero JS, 7 narrative sections, 6-model comparison table with locked CHANGELOG values.
- `mext_demo_package_20260528_232926.zip` created with 12 files: both model checkpoints (`graphsage_model.pt`, `graphsage_jaccard.pt`), config.yaml, seed.txt, splits (2 CSV), plots (1 PNG), models (5 files total), mext_demo.html, README.txt.
- README.txt reproduction command: `python -m ml.eval.pipeline --mode pure_cold --seed 42` (canonical seed), includes feature circularity caveat and synthetic ground-truth methodology caveat.

**UAT results:** All 10 tests passed.

| # | Test | Result |
|---|---|---|
| 1 | Demo page opens without server | ✅ PASS |
| 2 | 7 narrative sections | ✅ PASS |
| 3 | 6-model comparison table, locked metrics | ✅ PASS |
| 4 | Honest limitations with feature-circularity framing | ✅ PASS |
| 5 | Bar chart embedded (Content-Only excluded) | ✅ PASS |
| 6 | Live recommendation example | ✅ PASS |
| 7 | Zero JavaScript | ✅ PASS |
| 8 | No Scentrix branding in body | ✅ PASS |
| 9 | ZIP contains both .pt files | ✅ PASS |
| 10 | README.txt corrected reproduction steps | ✅ PASS |

### State Synchronization (2026-05-28)

**Source of truth:** CHANGELOG.md only. .planning/ files are secondary and must never be marked complete ahead of CHANGELOG confirmation.

**Phase 5 status:** ✅ COMPLETE.

**Phase 6 status:** ✅ UNBLOCKED.

**Completed this session (Phase 5 final task):**
- `--mode stratification` added as valid CLI mode in argparse and EvalConfig regex
- `run_stratification_grid()` rewritten from stub to real per-stratum evaluation:
  - Level 0 (cold items), Level 1 (low-popularity warm), Level 2 (high-popularity warm)
  - Real predict_cold_start inference per level for GraphSAGE-Embedding and GraphSAGE-Jaccard
  - Feature-Only and Popularity baselines recomputed per level
  - Results saved to runs dir + stratification_grid.md
  - Reporter (StratificationReporter) updated with correct model names (4-column output) and dynamic bar-chart layout
  - `_run_pure_cold` stores Jaccard wrapper on `self._gs_jaccard_wrapper` for reuse
- Leakage caveat documented: Levels 1-2 evaluate warm items with model trained on full warm set (optimistic scores)
- Stratification results section (V-D) added to docs/research_paper.md with table and caveat

**Phase 5 locked claims (unchanged):**
- GraphSAGE-Jaccard NDCG@10=0.504 vs GraphSAGE-Embedding NDCG@10=0.197. 63% relative degradation. p≤0.001, d=0.93.
- quiz_init does NOT reliably beat pure_cold (mean 0.496 vs 0.504, high variance)
- Stratification: Feature-Only leads at all levels; GraphSAGE-Jaccard follows the expected monotonic trend; GraphSAGE-Embedding is non-monotonic (connectivity weakness for low-popularity items)

**Locked research claim (unchanged):**
GraphSAGE-Jaccard NDCG@10=0.504 vs GraphSAGE-Embedding NDCG@10=0.197. 63% relative degradation. p≤0.001, d=0.93. Feature-Only (0.557) beats GraphSAGE-Jaccard — graph claim is scoped to structural independence, not absolute performance.

**Working protocol (reinstated):**
- CHANGELOG.md is the ONLY source of truth
- .planning/ files are supplementary — never mark complete before CHANGELOG confirms execution
- No UAT result is valid unless the command was actually run and output was pasted and verified
- Phase N cannot begin until Phase N-1 is fully locked in CHANGELOG.md

---

### Session Summary (post-Phase 4 audit + Phase 5 start)

**Paper audit complete — 6 fixes applied to docs/research_paper.md**
1. Abstract: "capable of incorporating" → "designed to support" (unproven capability claim)
2. Abstract + Intro: "63% NDCG degradation" → "63% relative NDCG degradation compared to corrected Jaccard baseline"
3. Intro Contribution 3: threshold 0.20 = GT floor disclosure added
4. Intro: NDCG range 0.494–0.523 stochasticity explanation added
5. Section V-B: defensive "not a failure" phrasing → positive reframe
6. Section VI: "capable of" → "designed to support / In future extensions"
InfoNCE loss confirmed accurate — verified in ml/eval/models/graphsage_wrapper.py.

**Pipeline bug fixes — ml/eval/pipeline.py**
Three functions were using build_similarity_graph (circular KNN) instead of build_jaccard_graph:
- _run_quiz_init (line 675) → fixed to build_jaccard_graph ✅
- run_quiz_sensitivity (was run_learning_curve, line 927) → fixed to build_jaccard_graph ✅
- run_ablation_study (line 1018) → fixed to build_jaccard_graph ✅
Only _run_warm_reference (line 797) correctly retains build_similarity_graph.
EvalConfig now has catalog_path and jaccard_threshold fields with correct defaults.

**Phase 5 — quiz_init baseline run complete**
| Model | NDCG@10 | Notes |
|---|---|---|
| GraphSAGE-Jaccard (pure_cold) | 0.504 | Within paper range 0.494–0.523 ✅ |
| GraphSAGE-Embedding (pure_cold) | 0.197 | Slightly above 0.183–0.191, stochasticity ✅ |
| Feature-Only | 0.557 | Matches paper exactly ✅ |
| Content-Only | 0.581 | Matches paper exactly ✅ |
| Popularity | 0.008 | Matches ✅ |
| Random | 0.021 | Minor deviation from 0.031, acceptable ✅ |
| GraphSAGE-Jaccard (quiz_init) | 0.405 | First run, injection-only, no alpha blending |

quiz_init run details:
- 4559 nodes, 16244 edges (threshold=0.20)
- 920 cold nodes, quiz_length=5, quiz_noise=0.1
- 209 degree-0 cold nodes (feature-only fallback)
- 711 cold nodes with graph edges (inductive inference)
- Bias mechanism: additive injection node_features[idx, :48] += confidence
- No alpha blending implemented yet

### quiz_init — Reranker Fix (current session)

**Root cause diagnosed:** additive `+=` injection into one-hot item features caused two failures:
1. Feature space corruption — one-hot constraint violated, warm/cold node distributions diverged
2. Semantic mismatch — quiz signal (user preference) injected into item feature vectors (wrong side)

**Fix applied:**
- `quiz_simulator.py`: added `_last_confidence` cache in `simulate()` + `get_accord_confidence()` method
- `pipeline.py` `_run_quiz_init`: removed `+=` injection block entirely, replaced with post-prediction reranker — warm candidates re-scored by quiz confidence of their `primary_accord`, item features untouched, graph structure preserved
- `research_paper.md` line ~233: future work sentence updated to reflect reranker implementation

**Expected outcome:** quiz_init NDCG@10 should meet or exceed pure_cold NDCG@10 = 0.504.
If below 0.504 after fix, diagnose reranker — check accord_lookup coverage and predictions dict structure before concluding.

---

### quiz_init — Alpha Sweep + Variance Analysis (current session)

**Reranker architecture finalised:**
- quiz_rerank_pool=50: predict_cold_start retrieves top-50 candidates
- Alpha blend: blended = (1-α) * rank_score + α * quiz_score
  where rank_score = 1 - (rank / total), normalised over pool
- Top-10 truncation after reranking for metric computation
- quiz_alpha=0.3 set as default in EvalConfig

**Alpha sweep results (seed=42, quiz_rerank_pool=50):**
| alpha | NDCG@10 | delta vs pure_cold (0.504) |
|-------|---------|---------------------------|
| 0.0   | 0.49932 | -0.00468 (sanity check ✅) |
| 0.1   | 0.49859 | -0.00541 |
| 0.3   | 0.52081 | +0.01681 ✅ |
| 0.5   | 0.49759 | -0.00641 |
| 1.0   | 0.46965 | -0.03435 |

**Variance analysis (alpha=0.3, quiz_rerank_pool=50, 5 seeds):**
| seed | quiz seed | NDCG@10 |
|------|-----------|---------|
| 42   | 43        | 0.50920 |
| 43   | 44        | 0.46108 |
| 44   | 45        | 0.50318 |
| 45   | 46        | 0.51907 |
| 46   | 47        | 0.48625 |
- mean: 0.49576
- std:  0.02276
- min:  0.46108 (seed=43)
- max:  0.51907 (seed=45)
- beats pure_cold: 2/5 runs

**Interpretation:**
quiz_init does NOT reliably beat pure_cold. Mean NDCG (0.496) is below
pure_cold (0.504). High std (0.023) means result is seed-dependent.
The improvement at alpha=0.3 seed=42 (0.521) was a favourable quiz draw,
not a stable signal. Honest claim: quiz preference reranking is directionally
correct but requires better quiz signal (longer quiz, real user data, or
accord-matched simulation) to beat pure_cold consistently.

**Current EvalConfig state:**
- quiz_alpha: float = 0.3
- quiz_rerank_pool: int = 50
- seed: int = 42 (default restored)

### quiz_init — Quiz Length Variance Sweep

**Setup:** alpha=0.3, quiz_rerank_pool=50, 5 seeds per length.

| quiz_length | seed_42 | seed_43 | seed_44 | seed_45 | seed_46 | mean | std |
|-------------|---------|---------|---------|---------|---------|------|-----|
| 5 | 0.50920 | 0.46108 | 0.50318 | 0.51907 | 0.48625 | 0.49576 | 0.02276 |
| 10 | 0.52234 | 0.49760 | 0.48042 | 0.49598 | 0.50752 | 0.50077 | 0.01548 |
| 20 | 0.47267 | 0.50251 | 0.52336 | 0.52670 | 0.51239 | 0.50753 | 0.02169 |

**Interpretation:**
- quiz_length=20 clears pure_cold mean (0.504) by 0.003 — marginal
- std=0.022 at length=20 means individual runs still fall below baseline
- quiz_length=10 is the variance minimum (std=0.015) but undershoots mean
- No quiz_length produces a reliable, consistent improvement over pure_cold

### quiz_init — Quiz Sensitivity Analysis

**Reranker fix applied to `run_quiz_sensitivity`** — same post-prediction reranker pattern as `_run_quiz_init`.

**Run:** `python -m ml.eval.pipeline --mode quiz_sensitivity` (seed=42, alpha=0.3, quiz_rerank_pool=50)

**Raw scores (NDCG@10 vs quiz length k):**

| k (quiz_length) | quiz_init NDCG@10 | pure_cold NDCG@10 |
|-----------------|-------------------|-------------------|
| 1               | 0.50907           | 0.51072           |
| 3               | 0.50652           | 0.51072           |
| 5               | 0.50534           | 0.51072           |
| 7               | 0.50489           | 0.51072           |
| 10              | 0.50609           | 0.51072           |

**Interpretation:**
- quiz_init does NOT beat pure_cold at any quiz_length (1–10)
- Gap is small and consistent: pure_cold leads by 0.002–0.006
- Reranker fix confirmed working — no corruption artifacts
- k-axis is quiz_length, NOT warm interaction count (this is a quiz sensitivity curve, not a true learning curve)
- Simulated quiz signal insufficient to beat pure_cold; real user interaction data expected to widen the gap
- A true learning curve (NDCG vs warm interaction count) is NOT yet implemented

Plot saved to `ml/eval/runs/20260528_075227/plots/quiz_sensitivity.png`.

**Naming fix:** `run_learning_curve` → `run_quiz_sensitivity`, `LearningCurvePlotter` → `QuizSensitivityPlotter`, `--mode learning_curve` → `--mode quiz_sensitivity`.

**Open questions before Phase 5 complete:** (all resolved)

1. ~~Can a longer quiz (quiz_length > 5) reduce variance and push mean above 0.504?~~ — answered (no)
2. ~~Quiz sensitivity curves not yet run~~ — done with reranker fix
3. ~~Stratified analysis not yet run~~ — done (coldness-level stratification, not per-accord — see below)
4. ~~MEXT spoken answer for "why graph over Feature-Only" not yet memorised~~ — drafted in paper

---

## Stratification Clarification (2026-05-28)

"per-accord NDCG breakdown" was a misnomer — the planned and completed analysis was always coldness-level stratification. Key differences:

- **Coldness-level stratification** (built): segments by interaction-data availability (0 / 1-3 / 4+ interactions). Shows how model performance scales with warmth.
- **Per-accord stratification** (never planned): segments by accord category (Fruity, Woody, Fresh, etc.). Would show which olfactory families are easier/harder — but was never specified in any design doc or requirements.

Per-accord is **explicitly descoped** from Phase 5. Phase 5 is now fully complete and locked.

---

## Locked Research Claim (unchanged)

"Graph construction methodology is the critical determinant of GNN performance
in cold-start recommendation. Embedding-derived similarity graphs introduce
feature circularity that degrades NDCG by 63% relative to independent baselines.
Replacing circular edges with structurally independent Jaccard similarity over
fragrance notes recovers 2.7× performance improvement (NDCG 0.183 → 0.494,
p≤0.001, d=0.93)."

---

## Phase History

| Phase | Status | Key Output |
|---|---|---|---|
| 1 — Pipeline & Data Foundation | ✅ Complete | Clean dataset, Neo4j graph |
| 2 — Evaluation Infrastructure | ✅ Complete | Cold-start splitter, ranx metrics |
| 3 — Baselines & Comparison | ✅ Complete | Popularity, Random, bootstrap |
| 4 — GraphSAGE Pipeline | ✅ Complete (with rework) | Jaccard graph, ablation confirmed |
| 5 — Research Differentiators | ✅ Complete | quiz_init, quiz_sensitivity, stratification grid, paper locked |
| 6 — MEXT Demo | ✅ Complete | mext_demo.html (167.8KB, 7 sections, zero JS), packaged ZIP with both .pt files, all 10 UAT tests passed |
| 7 — Preference Initialization Service | ✅ Complete | GraphSAGE Preference Initialization Service: loads precomputed Jaccard embeddings (`node_embeddings_jaccard.npy`), weighted centroid computation, cosine-similarity KNN retrieval, disagreement instrumentation, artifact startup validation. No checkpoint loading, no model inference, no torch runtime dependency. Per ARCHITECTURE-FREEZE.md. |
| 8 — 5-State Recommendation Dispatcher | ✅ Complete | 5-state dispatch tree: anonymous/popularity, quiz/GraphSAGE, cold/hybrid β-blend, warm/feature-based, mature/diversity injection. Feature-based, popularity, and gs_embeddings extracted as peer services. Legacy hybrid_search retained behind flag. 90+ tests. Per ARCHITECTURE-FREEZE.md. |
| 8a — Direct Rating MVP + Frontend Integration | ✅ Complete | State 0 unblocked (anonymous cold-start), Star button rating on FragranceCard, State 3 fallback (popularity→graphsage), State 4 GraphSAGE exploration injection, recommendation reason badge, doc alignment, repository state consolidation. See CHANGELOG [Unreleased] (2026-06-01). |
| 9 — Data & Graph Sync | 🔲 Planned | Incremental Jaccard rebuild, Celery nightly graph refresh, stale embedding detection |
| 10 — Auth, User State & Rating Loop | 🔲 Planned | JWT auth, rating → warm upgrade trigger, Redis per-user cache with TTL |
| 11 — Frontend Integration | 🔲 Planned | Next.js wired to real endpoints, quiz flow UI, cold→warm transition UX, accord explanations |
| 12 — Observability & Hardening | 🔲 Planned | Structured logging, quality metrics, load testing, Docker Compose production config |

---

## Handoff Snapshot — for new chat continuity

**Full results table:**
| Model | Precision@10 | NDCG@10 | Recall@10 |
|---|---|---|---|
| GraphSAGE-Jaccard (pure_cold) | 0.0745 | 0.504 | 0.0926 |
| GraphSAGE-Embedding (pure_cold) | 0.0306 | 0.197 | 0.0216 |
| GraphSAGE-Jaccard (quiz_init) | 0.063 | 0.405 | 0.057 |
| Feature-Only | 0.0782 | 0.557 | 0.0932 |
| Content-Only (oracle) | 0.0860 | 0.581 | 0.1225 |
| Popularity | 0.0019 | 0.008 | 0.0010 |
| Random | 0.0045 | 0.021 | 0.0011 |

**Bootstrap significance (pure_cold, n=10000):**
- Jaccard vs Embedding: p≤0.001, d=0.93 ✅
- Jaccard vs Popularity: p≤0.001, d=1.87 ✅
- Jaccard vs Random: p≤0.001, d=1.72 ✅
- Jaccard vs Feature-Only: p=1.000, d=-0.149 ❌

**Pipeline bug fixes applied this session:**
- _run_quiz_init, run_quiz_sensitivity (was run_learning_curve), run_ablation_study: build_similarity_graph → build_jaccard_graph
- EvalConfig: catalog_path + jaccard_threshold fields added

**Working protocol:**
- Claude inspects and directs via targeted shell commands
- Agent executes, pastes output back
- Every decision committed to CHANGELOG.md
- No claims without results
- CHANGELOG.md is source of truth — always read first

**HANDOFF NOTE (2026-06-01):**
- Phase 6 ✅ COMPLETE. All 10 UAT tests passed. mext_demo.html + ZIP generated.
- Phase 6.5 ✅ COMPLETE. Architecture Freeze approved. See `ARCHITECTURE-FREEZE.md`.
- Phase 7 ✅ COMPLETE. GraphSAGE Preference Initialization Service implemented — artifact loading, startup validation, weighted centroid, cosine-similarity KNN, disagreement instrumentation per ARCHITECTURE-FREEZE.md. No checkpoint loading, no model inference, no torch dependency.
- Phase 8 ✅ COMPLETE. 5-state dispatcher per ARCHITECTURE-FREEZE.md. 90+ tests.
- Phase 8a ✅ COMPLETE. Direct Rating MVP frontend (State 0 unblocked, Star button rating), State 3 fallback redesign (popularity→graphsage), State 4 GraphSAGE exploration injection, recommendation reason badge, doc alignment (ARCHITECTURE-FREEZE.md note, README/backend/README updates), repository state consolidation. See [Unreleased] (2026-06-01).
- Phase 9–12 🔲 Planned. Governed by ARCHITECTURE-FREEZE.md.
- Next decision: Improve recommendation explanation (A) or fix onboarding/navigation flow (B). No recommendation yet.
- `response.md` contains latest session audit — not tracked, regeneratable.
- CHANGELOG.md is source of truth — read first.
