# Scentrix

**Research Theme:** Graph-Based Preference Initialisation for Cold-Start Recommendation in Zero-Interaction Domains
**Primary Objective:** Demonstrate feasibility and operational deployability of graph-based preference initialization

## Project Context

Scentrix is a 3rd-year undergraduate research project for MEXT scholarship interviews (July 2026). Research theme: "Graph-Based Preference Initialisation for Cold-Start Recommendation in Zero-Interaction Domains." Started as a product-oriented perfume platform, pivoted to research. See [CHANGELOG.md](./CHANGELOG.md) for phase history and requirement traceability.

**Key constraints:** Local Docker only, no cloud costs. Precision@10 and NDCG@10 evaluation (Matsuo/Kashima lab standards). Popularity + Random baselines only (CF/MF meaningless for cold-start). Results presented as MEXT interview demo, not paper submission.

graph-based cold-start fragrance recommendation.

## what's the move?

hybrid research + engineering. the thesis: **cold-start preference initialization via direct user-vector from quiz ratings**. the original pipeline (confidence → seeds → centroid → GraphSAGE) discarded per-item rating information at every stage. the USER_VECTOR path (rating-weighted embedding sum → KNN) preserves the full signal and achieves +14.9% FH / +41.4% NDCG over centroid — simpler, faster, better.

## the numbers (canonical — Fix B applied)

⚠️ Phase 5.1 evaluation audit identified two flaws: (1) NDCG@10 was computed as RR@10, and (2) ground truth used note-Jaccard >0.20 (circular with the Jaccard graph). Fix A (true NDCG) and Fix B (brand+accord GT) have been applied. Values below are from the canonical reproducible pipeline: `SCENTRIX_EVAL_GT_MODE=brand_accord python -m ml.eval.pipeline --mode pure_cold --seed 42`.

| Model | Precision@10 | NDCG@10 | Recall@10 |
|---|---|---|---|
| GraphSAGE-Jaccard (pure_cold) | 0.0567 | **0.115** | 0.1396 |
| GraphSAGE-Embedding (pure_cold) | 0.0550 | **0.095** | 0.1075 |
| Feature-Only | 0.1825 | **0.399** | 0.4136 |
| Content-Only | 0.0193 | **0.047** | 0.0465 |
| Popularity | 0.0000 | **0.000** | 0.0000 |
| Random | 0.0007 | **0.001** | 0.0012 |

**bootstrap significance (n=10000, brand_accord GT):** Jaccard vs Embedding: p=0.008, d=0.11 (Jaccard leads by 1.21×). Jaccard vs Feature-Only: p=1.000, d=−0.96 (Feature-Only leads by 3.47×).

**headline:** Under non-circular brand+accord ground truth, Feature-Only (0.399 NDCG@10) dominates GraphSAGE-Jaccard (0.115) by 3.47×. GraphSAGE-Jaccard marginally outperforms GraphSAGE-Embedding (0.095) by 1.21× — structural independence helps modestly, but direct feature matching is substantially more predictive of brand+accord relevance on this dataset.

## key decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GraphSAGE on Neo4j | Graph-based preference init for cold-start — core hypothesis | Complete — Jaccard NDCG@10=0.115 vs Embedding 0.095 |
| Adaptive confidence quiz | Preference init without interaction history | Complete — analyzed; does not beat pure_cold (0.496 vs 0.504) |
| Popularity + Random baselines | Only honest cold-start baselines | Complete — NDCG@10=0.008, 0.021 |
| Precision@10 + NDCG@10 | Standard metrics for target labs | Complete — ranx-based, operational |
| Local Docker only | No cloud costs, sufficient | Confirmed |
| GraphSAGE as Preference Init Layer | Feature-Only beats GS at every coldness level by up to 3.5× | Architecture Freeze — GS alongside FB, never alone |
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

⚠️ "Group A NDCG" values from the original pipeline used circular jaccard GT. Under Fix B (brand_accord GT), absolute values are lower but the pattern — higher thresholds produce higher NDCG at the cost of coverage — is consistent. Threshold 0.20 remains the canonical choice, balancing coverage (99.2%) with reasonable NDCG.

| Threshold | Edges | Deg-0 | NDCG@10 | Precision@10 | Recall@10 |
|---|---|---|---|---|---|
| 0.10 | 21,452 | 12 | 0.082 | 0.043 | 0.102 |
| 0.15 | 20,124 | 27 | 0.084 | 0.045 | 0.102 |
| **0.20** | **16,244** | **84** | **0.113** | **0.054** | **0.135** |
| 0.25 | 10,821 | 204 | 0.168 | 0.082 | 0.189 |
| 0.30 | 6,341 | 369 | 0.233 | 0.108 | 0.253 |

## quiz_init (archived — superseded by USER_VECTOR)

The centroid-based quiz_init was evaluated under the original pipeline (circular jaccard GT, RR-as-NDCG). It does NOT reliably beat pure_cold (mean NDCG 0.496 vs 0.504, std 0.023, beats baseline 2/5 runs). Deemed not reproducible under corrected methodology. Superseded in production by USER_VECTOR (direct embedding lookup from per-item ratings). See `07_01-CONTEXT.md` for USER_VECTOR validation in its own evaluation context.

## coldness stratification

| Model | Level 0 (0 int.) | Level 1 (1-3) | Level 2 (4+) |
|---|---|---|---|
| GraphSAGE-Embedding | 0.095 | 0.071 | 0.131 |
| GraphSAGE-Jaccard | 0.115 | 0.081 | 0.152 |
| Feature-Only | 0.399 | 0.401 | 0.419 |
| Popularity | 0.000 | 0.001 | 0.001 |

Feature-Only leads all levels by a wide margin under brand_accord GT. Feature-Only and Popularity are near-constant across levels (feature-based signal does not degrade with coldness). GraphSAGE-Jaccard is monotonic across levels. GraphSAGE-Embedding non-monotonic (drops from 0.095 to 0.071 at Level 1 — low-pop connectivity weakness). Both GraphSAGE variants benefit from more interaction signal at Level 2, unlike Feature-Only which plateaus.

## roadmap

| Phase | Status | Focus |
|-------|--------|-------|
| 9 | ❌ Out of Scope | Graph Sync — irrelevant for static MEXT dataset |
| 10 | ⚠️ Reduced Scope | Auth & Ratings — guest persistence merged into Phase 11 |
| 11 | ✅ Complete | Quiz Flow Integration — 5 deliverables across Waves 1–3B |
| 12A | ✅ Complete | Structured Logging — correlation IDs, structured events across rec/quiz endpoints |
| 12B | ✅ Complete | Load Testing — Locust, 4 scenarios, 20 users/5-min ramp, all criteria PASS |
| 12C | ⏭️ Deferred | Performance Monitoring — `/metrics` endpoint with Prometheus |
| 12D | ❌ Dropped | Dashboards & Alerting — out of scope for MEXT demo |

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
