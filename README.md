# Scentrix

**Research Theme:** Graph-Based Preference Initialisation for Cold-Start Recommendation in Zero-Interaction Domains
**Primary Objective:** Demonstrate feasibility and operational deployability of graph-based preference initialization

## Project Context

Scentrix is a 3rd-year undergraduate research project for MEXT scholarship interviews (July 2026). Research theme: "Graph-Based Preference Initialisation for Cold-Start Recommendation in Zero-Interaction Domains." Started as a product-oriented perfume platform, pivoted to research. See [CHANGELOG.md](./CHANGELOG.md) for phase history and requirement traceability.

**Key constraints:** Local Docker only, no cloud costs. Precision@10 and NDCG@10 evaluation (Matsuo/Kashima lab standards). Popularity + Random baselines only (CF/MF meaningless for cold-start). Results presented as MEXT interview demo, not paper submission.

graph-based cold-start fragrance recommendation.

## what's the move?

hybrid research + engineering. the thesis: **cold-start preference initialization via direct user-vector from quiz ratings**. the original pipeline (confidence → seeds → centroid → GraphSAGE) discarded per-item rating information at every stage. the USER_VECTOR path (rating-weighted embedding sum → KNN) preserves the full signal and achieves +14.9% FH / +41.4% NDCG over centroid — simpler, faster, better.

## the numbers (original pipeline — under evaluation audit)

⚠️ Phase 5.1 evaluation audit found the evaluation methodology had two flaws: (1) NDCG@10 was computed as RR@10 (break on first relevant item), and (2) ground truth used note-Jaccard >0.20, which is circular with the Jaccard graph. Values below are from the original pipeline. Fix A (true NDCG) applied, Fix B (brand+accord GT) proposed — gap narrows under corrected methodology.

| Model | Precision@10 | Reported NDCG@10 (was RR@10) | Recall@10 |
|---|---|---|---|
| GraphSAGE-Jaccard (pure_cold) | 0.0745 | **0.504** | 0.0926 |
| GraphSAGE-Embedding (pure_cold) | 0.0306 | **0.197** | 0.0216 |
| GraphSAGE-Jaccard (quiz_init) | 0.063 | **0.405** | 0.057 |
| Feature-Only | 0.0782 | **0.557** | 0.0932 |
| Content-Only (oracle) | 0.0860 | **0.581** | 0.1225 |
| Popularity | 0.0019 | **0.008** | 0.0010 |
| Random | 0.0045 | **0.021** | 0.0011 |

**bootstrap significance (n=10000, original pipeline):** Jaccard vs Embedding: p≤0.001, d=0.93. Jaccard vs Feature-Only: p=1.000, d=-0.149.

**headline:** GraphSAGE-Jaccard (0.504) vs GraphSAGE-Embedding (0.197) under the original pipeline. Feature-Only (0.557) leads all models but has no mechanism to incorporate user interactions — GraphSAGE-Jaccard provides an extensible foundation. ⚠️ Phase 5.1 evaluation audit: these numbers change under corrected metric and ground truth (see Phase 5.1 CONTEXT.md for before/after comparison).

## key decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GraphSAGE on Neo4j | Graph-based preference init for cold-start — core hypothesis | Complete — Jaccard NDCG@10=0.504 vs Embedding 0.197 |
| Adaptive confidence quiz | Preference init without interaction history | Complete — analyzed; does not beat pure_cold (0.496 vs 0.504) |
| Popularity + Random baselines | Only honest cold-start baselines | Complete — NDCG@10=0.008, 0.021 |
| Precision@10 + NDCG@10 | Standard metrics for target labs | Complete — ranx-based, operational |
| Local Docker only | No cloud costs, sufficient | Confirmed |
| GraphSAGE as Preference Init Layer | Feature-Only beats GS at every coldness level | Architecture Freeze — GS alongside FB, never alone |
| USER_VECTOR over centroid | Preserves per-item signal, simpler, faster | Production — +14.9% FH / +41.4% NDCG, ~10× faster |

## the architecture

See [ARCHITECTURE-FREEZE.md](./ARCHITECTURE-FREEZE.md) for the canonical 5-state dispatch architecture.

## the product

5 Docker containers — Postgres 15, Neo4j 5, Redis 7, FastAPI backend, Next.js frontend. 5,000 quality-filtered items (from 22,740). 24 brands. 48 accords. 16,244 edges at threshold 0.20.

The recommendation flow: zero ratings → State 0 (popularity). Complete quiz → State 1 (GraphSAGE — user-vector from per-item ratings, centroid legacy fallback). Tap Star → State 2 (blended). 5 ratings → State 3 (feature-based). 20 → State 4 (feature-based + diversity).

API responses include `state` (0–4) and `state_label` to inform the frontend of the current dispatch state. Quiz endpoints include `POST /fragrances/quiz/session/{session_id}/guest-finalize` for guest persistence and `GET /recommendations/quiz-summary` for the Last Quiz Summary card on `/profile/history`.

### development commands

```bash
# start everything
docker compose up                                      # → http://localhost:3000

# run backend tests (requires running system)
make test-backend                                      # or: docker compose exec backend pytest
docker compose exec backend pytest tests/test_phase11_quiz.py  # single file

# run frontend checks (from frontend/)
npm run lint                                           # ESLint
npm run format                                         # Prettier
npm run type-check                                     # TypeScript (tsc --noEmit)
npm run build                                          # Next.js production build

# run e2e tests (Playwright, requires running system)
npm run test:e2e                                       # headless
npm run test:e2e:ui                                    # interactive UI mode
```

## the threshold

| Threshold | Edges | Coverage | Group A NDCG | degree-0 items |
|---|---|---|---|---|
| 0.10 | 21,452 | 100% | 0.432 | 0 |
| 0.15 | 20,124 | 100% | 0.455 | 0 |
| **0.20** | **16,244** | **99.2%** | **0.494** | **7** |
| 0.25 | 10,821 | 84.9% | 0.554 | 127 |
| 0.30 | 6,341 | 65.4% | 0.642 | 292 |

## quiz_init (superseded by USER_VECTOR)

⚠️ The centroid-based quiz_init below uses the old pipeline (confidence → seeds → centroid). Replaced in production by USER_VECTOR (direct embedding lookup from per-item ratings, no centroid step). USER_VECTOR validation: +14.9% FH, +41.4% NDCG over centroid.

| metric | value (old pipeline) |
|---|---|
| mean NDCG@10 (5 seeds) | 0.496 |
| pure_cold baseline | 0.504 |
| std dev | 0.023 |
| beats baseline | 2/5 runs |

Old centroid-based quiz_init does NOT reliably beat pure_cold. USER_VECTOR is the production replacement.

## coldness stratification

| Model | Level 0 (0 int.) | Level 1 (1-3) | Level 2 (4+) |
|---|---|---|---|
| GraphSAGE-Embedding | 0.1975 | 0.1608 | 0.2293 |
| GraphSAGE-Jaccard | 0.4955 | 0.4469 | 0.5201 |
| Feature-Only | 0.5573 | 0.5464 | 0.5801 |
| Popularity | 0.0078 | 0.0115 | 0.0113 |

Feature-Only leads all levels (original pipeline). ⚠️ Values change under corrected metric (true NDCG) and non-circular ground truth (brand+accord). GraphSAGE-Jaccard monotonic. Embedding non-monotonic (drops from 0.198 to 0.161 — low-pop connectivity weakness).

## roadmap

| Phase | Status | Focus |
|-------|--------|-------|
| 9 | ❌ Out of Scope | Graph Sync — irrelevant for static MEXT dataset |
| 10 | ⚠️ Reduced Scope | Auth & Ratings — guest persistence merged into Phase 11 |
| 11 | ✅ Complete | Quiz Flow Integration — 5 deliverables across Waves 1–3B |
| 12 | 🔲 Pending | Observability — structured logging, load testing, monitoring |

See [CHANGELOG.md](./CHANGELOG.md) for full phase history, sub-phase details, and requirement→phase traceability.

### Phase 11 — Quiz Flow Integration (Complete)

Phase 11 delivered the end-to-end quiz→recommendation user experience across five deliverables:

| Wave | Deliverable | Summary |
|------|-------------|---------|
| 1 | Guest Quiz Persistence | `POST /fragrances/quiz/session/{session_id}/guest-finalize` — Redis session finalization for guests, DB upsert for authenticated users |
| 2 | StateIndicator + Cold→Warm UX | `StateIndicator.tsx` component, 5-state-aware header on `/recommendations`, `state`/`state_label` in API responses |
| 3A | Last Quiz Summary | `GET /recommendations/quiz-summary` endpoint, `/profile/history` page rewritten from mock timeline to real summary card |
| 3B | Quiz Flow Polish | Extension flow UI (evaluate→prompt→fetch more questions), loading overlay during finalization, post-completion success screen, user-visible error handling |

## run it yourself

```bash
python -m ml.eval.pipeline --mode pure_cold --seed 42  # canonical run
python -m ml.eval.run_bootstrap                           # bootstrap n=10000
python -m ml.eval.pipeline --mode quiz_sensitivity        # quiz sensitivity
python -m ml.eval.pipeline --mode stratification          # stratification grid
```
