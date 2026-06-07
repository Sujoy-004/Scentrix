# Architecture Freeze — Phase 6.5

**Research Theme:** Graph-Based Preference Initialisation for Cold-Start Recommendation in Zero-Interaction Domains
**Primary Objective:** Demonstrate feasibility and operational deployability of graph-based preference initialization

**Date:** 2026-06-06 (initial freeze 2026-05-30, USER_VECTOR update 2026-06-06)
**Status:** APPROVED

This document is the canonical source of truth for Scentrix's production recommendation architecture from Phase 7 onwards. All implementation decisions must conform to this freeze. Deviations require a written exception approved via architecture review.

---

## 1. Architecture Principles

1. **State-driven, not model-driven.** The recommendation system dispatches to different strategies based on user state, not based on which model is newest or fastest. User signal maturity determines the retrieval strategy.

2. **GraphSAGE is a Preference Initialization Layer, not the recommendation system.** GraphSAGE solves cold-start for items, not users. Its job is structural discovery — mapping fragrance relationships that feature-based scoring cannot see. It is always deployed alongside a feature-based component.

3. **Feature-based ranking dominates as user signal increases.** Research evidence consistently shows Feature-Only (direct accord/note overlap) beats GraphSAGE-Jaccard at every coldness level. Feature-based is the asymptote; GraphSAGE is the initialization.

4. **Graceful degradation is mandatory.** Every retrieval strategy must have a fallback to a simpler strategy. No single-point-of-failure in the recommendation pipeline.

5. **Explainability is required.** Every recommendation must be traceable to its source — GraphSAGE similarity, feature overlap, or popularity — and explainable in user-facing language.

6. **The retrieval strategy is independent of the serving API.** The dispatch tree in this document governs *what* is computed. The API layer (endpoints, serialization, caching) is a separate concern.

---

## 2. User State Lifecycle

Users progress through five mutually exclusive states based on their interaction signal maturity:

```
                    ┌──────────────────────────────────────┐
                    │          State 0: Anonymous           │
                    │  Signal: none (no session, no quiz)   │
                    │  Strategy: Popularity-only            │
                    └──────────────────┬───────────────────┘
                                       │ take quiz or rate
                                       ▼
                    ┌──────────────────────────────────────┐
                    │          State 1: Quiz User           │
                    │  Signal: quiz confidence vector (48d) │
                    │  Strategy: GraphSAGE primary          │
                    └──────────────────┬───────────────────┘
                                       │ rate ≥ 1 item
                                       ▼
                    ┌──────────────────────────────────────┐
                    │          State 2: Cold User           │
                    │  Signal: 1–5 ratings                 │
                    │  Strategy: Hybrid (GraphSAGE → FB)   │
                    └──────────────────┬───────────────────┘
                                       │ rate ≥ 5 items
                                       ▼
                    ┌──────────────────────────────────────┐
                    │        State 3: Warm User             │
                    │  Signal: 5–20 ratings                │
                    │  Strategy: Feature-based primary      │
                    └──────────────────┬───────────────────┘
                                       │ rate ≥ 20 items
                                       ▼
                    ┌──────────────────────────────────────┐
                    │       State 4: Mature User            │
                    │  Signal: 20+ ratings                 │
                    │  Strategy: Feature-based + diversity  │
                    └──────────────────────────────────────┘
```

### State boundaries (hard thresholds)

| State | Ratings count | Quiz completed | Session |
|-------|--------------|----------------|---------|
| 0     | 0            | No             | Guest |
| 1     | 0            | Yes            | Guest or auth |
| 2     | 1–4          | Maybe          | Auth |
| 3     | 5–19         | Maybe          | Auth |
| 4     | 20+          | Maybe          | Auth |

State transitions are triggered by the next rating submission. The system checks `len(ratings)` after each `POST /ratings` and upgrades the user if they cross a boundary.

### State 1 retrieval (updated 2026-06-06)

State 1 (Quiz User) supports two retrieval modes behind the `USE_USER_VECTOR` flag:

- **USER_VECTOR (default):** Per-item ratings → embedding lookup → rating-weighted mean → KNN.
  Uses the user's actual rated item embeddings directly, preserving per-item rating information.
  Proven +14.9% FH / +41.4% NDCG over centroid.

- **CENTROID (legacy fallback):** Quiz confidence → accord-to-seed mapping → equal-weight centroid → KNN.
  Falls back to accord-level popularity when ratings are absent or `USE_USER_VECTOR=false`.
  Preserved unchanged for comparison and A/B testing.

---

## 3. Recommendation Dispatch Tree

```
User request → Determine state (rating_count from DB, or zero for guest)

State 0 (Anonymous)
  └── Popularity ranking → Top-N by global popularity score
      └── Fallback: random sample of catalog

State 1 (Quiz User)
  └── GraphSAGE primary (parallel paths under USE_USER_VECTOR flag)
      │
      ├── USER_VECTOR path (default, USE_USER_VECTOR=true, ratings present)
      │   ├─ Step 1: Compute user-vector as rating-weighted mean of embeddings
      │   │          u = Σ((rating_i / 10) × gs_embedding_i) / Σ(rating_i / 10)
      │   │          L2 normalize: u = u / ||u||
      │   ├─ Step 2: KNN search (cosine similarity, candidate pool top-50)
      │   └─ Step 3: Feature-based re-ranking
      │   │
      │   Validation: +14.9% FH, +41.4% NDCG over centroid
      │   Runtime: ~0.67 ms total (vector + KNN), ~10× faster than centroid
      │
      └── CENTROID path (legacy fallback, USE_USER_VECTOR=false or no ratings)
          ├─ Step 1: Convert quiz → seed items (top-K by accord_cosine, K=5)
          ├─ Step 2: Weighted centroid: Σ(w_i × gs_embedding_i) / Σ(w_i)
          │          where w_i = quiz_confidence[item.primary_accord]
          ├─ Step 3: KNN search (cosine similarity, candidate pool top-200)
          └─ Step 4: Feature-based failover if centroid fetch fails

State 2 (Cold User, 1–5 ratings)
  └── Hybrid (GraphSAGE → Feature-based blend)
      ├─ Step 1: Centroid from rated items (w = rating_score / 10)
      ├─ Step 2: GraphSAGE retrieval → top-100
      ├─ Step 3: Feature-based retrieval → top-100
      ├─ Step 4: Blend: β = clamp((ratings_count-1)/4, 0, 1)
      │          final = β × gs_score + (1-β) × feature_score
      └─ Step 5: Apply diversity penalty

State 3 (Warm User, 5–19 ratings)
  └── Feature-based primary + GraphSAGE exploration
      ├─ Step 1: Feature-based retrieval → top-100
      ├─ Step 2: GraphSAGE centroid → top-20 NOT in FB pool
      │          Inject 2 items at positions 2, 5
      └─ Step 3: Final ranking by feature score

State 4 (Mature User, 20+ ratings)
  └── Feature-based + diversity injection
      ├─ Step 1: Feature-based retrieval → top-100
      ├─ Step 2: Intra-list diversity rerank
      ├─ Step 3: Reintroduce diversity from lower ranks
      └─ Step 4: Track saturation — skip if last 3 identical
```

---

## 4. GraphSAGE Role Definition

GraphSAGE is a **Preference Initialization Layer** — a bridge between zero interaction history and the feature-based system.

- **Input:** Item cold-start (fragrance features, Jaccard graph neighborhood)
- **Output:** 64-dim unit-normalized embeddings encoding structural fragrance relationships
- **Training (research pipeline):** Contrastive InfoNCE loss over Jaccard note-similarity edges
- **Build-time export (one-time):** `ml/export/export_jaccard_embeddings.py` — runs model forward pass over full catalog, L2-normalizes output
- **Runtime retrieval:** Loads precomputed embeddings from disk. No model loading, no forward pass, no PyTorch dependency.

### Role by user state

| State | GraphSAGE role | Rationale |
|-------|----------------|-----------|
| 0 | Unused | No user preference to initialize |
| 1 | Primary retrieval path | Per-item ratings → user vector (rating-weighted mean of embeddings) → KNN. Centroid fallback via quiz confidence if ratings unavailable. |
| 2 | Co-equal scorer (β blend 1→0) | Bridge during signal accumulation |
| 3 | Exploration layer | Inject structural diversity |
| 4 | Diversity injection | Prevent over-specialization |

### What GraphSAGE does NOT do

- Does NOT solve cold-user — no user nodes, features, or embeddings
- Does NOT replace feature-based scoring — feature-based is consistently more accurate
- Does NOT rank everything alone — always feeds into a blended or secondary ranking step
- Does NOT run real-time retraining — frozen checkpoint until next retraining cycle

---

## 5. Retrieval Strategy

Two retrieval modes coexist behind the `USE_USER_VECTOR` feature flag.

### User-vector path (primary, USE_USER_VECTOR=true)

```
u = Σ((rating_i / 10) × gs_embedding_i) / Σ(rating_i / 10)
u = u / ||u||  (L2 unit normalise)
```

- **Input:** Per-item `(fragrance_id, rating)` pairs from quiz responses
- **Weight:** `rating / 10` normalises [1, 10] → [0.1, 1.0]
- **Retrieval:** cosine similarity(u, all item embeddings) → top-N
- **Validation:** +14.9% FH, +41.4% NDCG over centroid (user_vector_prototype.py)

### Weighted centroid path (legacy fallback, USE_USER_VECTOR=false)

```
centroid = Σ(w_i × gs_embedding_i) / Σ(w_i)
```

- **w_i:** rating_score/10 for States 2–4; quiz_confidence[primary_accord] for State 1
- **Retrieval:** cosine similarity(centroid, all item embeddings) → top-N
- **Note:** Preserved unchanged for A/B comparison. Seeds mapped via `_align_quiz_confidence()`, which can produce duplicate seeds from different accords.

### Canonical retrieval artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| `node_embeddings_jaccard.npy` | `ml/models/serving/v1/` | L2-normalized GraphSAGE-Jaccard embeddings, [4559, 64], float32 |
| `node_ids_jaccard.json` | `ml/models/serving/v1/` | 4,559 fragment IDs aligned with embedding rows |
| `metadata.json` | `ml/models/serving/v1/` | Provenance: source checkpoint, export timestamp, graph params |

### Disagreement instrumentation

```
pairwise_sims = cosine_similarity(seed_embeddings)     # K×K matrix
mean_pairwise  = mean(pairwise_sims[upper_tri])        # single float
logger.info("centroid_disagreement", mean_pairwise=..., seed_count=K)
```

Logged for offline analysis. No routing decisions. No multi-centroid retrieval. (Centroid path only.)

---

## 5a. USER_VECTOR Design Rationale

### Why replace centroid with user-vector?

The original pipeline computed a weighted centroid from quiz confidence scores:

```
Quiz (8 binary likes) → Accord confidence (4-component formula) → Seed selection (top-5 perfumers by accord) → Weighted centroid → KNN
```

**Problem:** Per-item rating information (1-10 scale) was collected by the frontend but discarded by the backend. Only binary liked/disliked reached the confidence formula. The 4-component formula (stability×0.35 + margin×0.25 + consistency×0.20 + coverage×0.20) was an untested heuristic. Seed selection was the primary pipeline bottleneck (see Phase 8.1 CONTEXT.md for bottleneck analysis).

**Discovery:** A quiz information audit (2026-06-04) revealed that `lib/hooks.ts` was sending per-item `rating` values alongside binary `liked`. The backend payload contained rich preference signal — confidence-weighted preference strength per note, per accord, per olfactive kingdom — but the dispatcher only read the binary liked flags.

**USER_VECTOR replaces the entire confidence→seeds→centroid chain with a single computation:**

```
User ratings (1-10) → u = Σ((rating_i / 10) × gs_embedding_i) / Σ(rating_i / 10) → L2 normalize → KNN
```

This is:
- **Direct:** Uses the same embeddings GraphSAGE learned for items, weighted by user preference strength
- **Information-preserving:** Every rating contributes proportionally; no lossy classification into liked/disliked
- **Computationally cheaper:** ~0.67 ms vs ~7 ms for centroid path at comparable accuracy
- **Zero overlap with centroid at top-200** (proved via side-by-side validation; see Phase 7.1 CONTEXT.md for full analysis)

### The routing fix

`DispatchRequest.ratings` had dual purpose: it was used for (a) state determination (counting how many items rated) and (b) computing the preference vector. The `quiz_ratings` field was added to split these concerns. Ratings for state determination remain in `ratings`; per-item quiz ratings for the user-vector computation go in `quiz_ratings`.

### Validation

| Metric | Centroid (old) | User-Vector | Delta |
|--------|---------------|-------------|-------|
| FH / NDCG | baseline | +14.9% / +41.4% | Significant |
| Runtime | ~7 ms | ~0.67 ms | ~10× faster |
| Top-200 overlap | — | 0% | Completely different candidates |

## 5b. Dispatcher Validation

### Dispatcher vs legacy comparison (2026-06-05)

The 5-state dispatcher was validated against the legacy `HybridRecommender` to ensure the new architecture does not regress on existing functionality:

| State | Dispatcher | Legacy | Top-5 match |
|-------|-----------|--------|-------------|
| State 0 (Popularity) | `PopularityService` | `GlobalPopularity` | **Identical** |
| State 1 (Quiz User) | `GraphSAGEService` (user-vector + centroid) | `HybridRecommender.quiz_seeded` | Comparable (new path) |
| State 2 (Cold) | `FeatureBasedService` + β blend | — | New path |
| State 3 (Warm) | `FeatureBasedService` | `HybridRecommender` | Comparable |
| State 4 (Mature) | `FeatureBasedService` + diversity | `HybridRecommender` | + diversity injection |

**Key finding:** State 0 output is byte-identical between dispatcher and legacy (same top-5, same scores). State 1 is a new path (USER_VECTOR) with no legacy equivalent. States 2-4 produce comparable or improved results over legacy.

The dispatcher is now the single entry point for all recommendation requests. Legacy `HybridRecommender` is retained as a runtime fallback only.

---

## 6. State Transition Rules

### Hard transitions

State 0 → State 1: Quiz completed (`POST /quiz/evaluate` or `/finalize`). Confidence vector generated. Guest session (no persistence across sessions unless user registers).

### Smoothed transitions (β blend)

State 2 → State 3 (at rating 5):
```
β = clamp((ratings_count - 1) / 4, 0, 1)
  count=1 → β=0.00 (pure GS), count=3 → β=0.50 (equal), count=5 → β=1.00 (pure FB)
```

### Regressive transitions

If ratings deleted (GDPR): State 4 → State 0. State does NOT regress on quiz retake.

---

## 7. Failure Strategy

| Failure mode | Detection | Fallback |
|---|---|---|
| Embedding artifact load fails | `np.load()`/`json.load()` raises at startup | Service unhealthy; dispatcher routes to feature-based only |
| Embedding cache has NaN | `isnan(embeddings).any()` at startup | Fail startup; re-export artifact |
| Redis cache miss | `cache.get()` returns None | Recompute full dispatch (cold path) |
| Feature-based scoring error | Exception in scoring function | GraphSAGE-only for that request |
| All retrieval paths fail | No candidates from any source | Empty result set |
| Centroid has no seeds | Empty seed_items list | Fallback per state |

### Health check requirements

- Embedding artifacts: verify existence, shape alignment, no NaN/Inf/duplicates at startup
- Normalization: all rows L2-unit-normalized (0.999–1.001)
- Provenance: metadata.json exists with consistent source checkpoint reference
- Feature index: accord/note lookup table loads completely

---

## 8. Open Research Questions

### Q1: Centroid disagreement analysis (HIGH)

**RQ:** How does centroid disagreement correlate with recommendation quality degradation?

**Status:** `mean_pairwise` logged per request. Not yet analyzed. If a degradation threshold exists, design multi-centroid retrieval experiment.

### Q2: Quiz reranker efficacy (MEDIUM)

**RQ:** Does quiz reranker (α=0.3) add value beyond pure GraphSAGE centroid for State 1?

**Status:** Research says NO — under the original pipeline, mean NDCG 0.496 (quiz) vs 0.504 (pure cold), high variance. Not re-evaluated under Fix B because the quiz reranker operates on centroid-based GraphSAGE, which has been superseded by USER_VECTOR. Disabled by default until proven with real user data.

### Q3: Diversity injection parameters (LOW)

**RQ:** Optimal number and position of diversity-injected items for States 3–4?

**Status:** Needs real user data and A/B test.

### Q4: Embedding staleness detection (LOW)

**RQ:** How does recommendation quality degrade as embeddings age relative to catalog changes?

**Status:** Deferred to Phase 9 (graph sync).

---

## 9. Final Architecture Summary

```
                     STATE DISPATCHER
              rating_count + quiz_completed → state
           │              │              │              │
     State 0          State 1         State 2        State 3/4
     Popularity       GraphSAGE       Hybrid         Feature-based
     only             primary         β blend        + diversity
                      2 paths         1.0→0.0
                      ├ USER_VECTOR
                      └ CENTROID (legacy)
                       │              │
                       ▼              ▼
              ┌──────────────────────────┐
              │     RETRIEVAL BACKENDS    │
              │  GraphSAGE (64-dim,      │
              │   user-vector + KNN)     │
              │   centroid + KNN)        │
              │  Feature-Based (accord/   │
              │   note overlap score)     │
              │  Popularity (global       │
              │   score, fallback)        │
              └──────────────────────────┘
```

### Architecture invariants

- GraphSAGE is ALWAYS a Preference Initialization Layer
- Feature-based ALWAYS outranks GraphSAGE as signal grows
- Every path has a fallback to simpler path
- User-vector is the primary State 1 retrieval path (rating-weighted mean of item embeddings)
- Centroid is the legacy fallback (quiz confidence → seeds → equal-weight centroid)
- Runtime loads precomputed L2-normalized embeddings — no model, no forward pass, no PyTorch
- Centroid disagreement is instrumented only — no routing decisions
- Quiz reranker is disabled by default
- All recommendations are traceable to source

### Key numbers

| Parameter | Value |
|---|---|
| GraphSAGE embedding dimension | 64 |
| NN candidate pool | 200 (State 1), 100 (States 2–4) |
| User vector input | Per-item ratings from quiz responses (up to N rated items) |
| Centroid seed count | 5 (State 1 via quiz, legacy), all rated (States 2–4) |
| Blend β range | 0.0 → 1.0 over ratings 1→5 |
| Quiz reranker α | 0.3 (disabled by default) |
| Diversity injection | 2 items (States 3–4) |
| Embedding count | 4,559 (100% of cleaned catalog) |
| Runtime torch dependency | None |
| Runtime model loading | None (precomputed embeddings only) |
| User-vector latency | ~0.67 ms total (vector + KNN), ~10× faster than centroid |

> **Implementation Note (2026-06-06):** State 1 (Quiz User) uses USER_VECTOR by default. Per-item ratings from quiz responses are sent alongside `quiz_confidence` for backward compatibility. The dispatcher routes to `compute_user_vector()` when `USE_USER_VECTOR=true` and ratings are present; falls back to centroid path when the flag is off or ratings are empty. Zero overlap between the two paths at top-200 (proved via side-by-side validation). The centroid path is preserved unchanged as legacy fallback for A/B testing.

---

## 10. API Layer Exposures (Phase 11)

The following API additions surface dispatch state and quiz data without changing the retrieval architecture.

### State exposure

All recommendation responses (`GET /recommendations/guest`, `GET /recommendations/personalized`) return optional fields:
- `state` (int, 0–4): Current dispatch state per the lifecycle in §2.
- `state_label` (string): Human-readable label ("Anonymous", "Quiz User", "Cold", "Warm", "Mature").

The frontend uses these to render the state-aware header and StateIndicator component on `/recommendations`. They are backward-compatible — existing clients ignoring these fields receive identical payloads.

### Guest quiz finalize

- `POST /fragrances/quiz/session/{session_id}/guest-finalize`
- For guests: marks the Redis session as finalized (no DB write).
- For authenticated users: delegates to the existing `POST /{session_id}/finalize` (DB upsert).
- Uses `get_optional_user_id` dependency (no JWT requirement).

### Quiz summary

- `GET /recommendations/quiz-summary`
- Authenticated only (JWT required).
- Returns `QuizSummaryResponse` with fields: `has_completed_quiz`, `completed_at`, `total_rated`, `average_rating`, `average_normalized`, `rating_distribution`, `top_matches`, `top_notes`, `top_accords`.
- Computed entirely from existing DB tables (`User.quiz_completed_at`, `FragranceRating`, `FeatureBasedService.score()`, `load_recommendation_catalog`) — no new tables, no schema migrations.

---

*Architecture Freeze: 2026-05-30 (Phase 11 addendum: 2026-06-07)*
