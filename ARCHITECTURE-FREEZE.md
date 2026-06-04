# Architecture Freeze — Phase 6.5

**Research Theme:** Graph-Based Preference Initialisation for Cold-Start Recommendation in Zero-Interaction Domains
**Primary Objective:** Demonstrate feasibility and operational deployability of graph-based preference initialization

**Date:** 2026-05-30
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
| 0     | 0            | No             | No auth required |
| 1     | 0            | Yes            | Guest or auth |
| 2     | 1–4          | Maybe          | Auth |
| 3     | 5–19         | Maybe          | Auth |
| 4     | 20+          | Maybe          | Auth |

State transitions are triggered by the next rating submission. The system checks `len(ratings)` after each `POST /ratings` and upgrades the user if they cross a boundary.

---

## 3. Recommendation Dispatch Tree

```
User request
    │
    ▼
┌──────────────────┐
│ Determine state  │ ← rating_count from DB (or zero for guest)
└──────┬───────────┘
       │
       ├── State 0 (Anonymous)
       │    └── Popularity ranking
       │         → Top-N by global popularity score
       │         → Fallback: random sample of catalog
       │
       ├── State 1 (Quiz User)
       │    └── GraphSAGE primary + optional quiz reranker
       │         ├─ Step 1: Convert quiz → seed items
       │         │   Find best-matching fragrances from quiz accord confidence
       │         │   (top-K by accord_cosine similarity, K=5)
       │         ├─ Step 2: Compute GraphSAGE centroid
       │         │   weighted centroid = Σ(w_i × gs_embedding_i) / Σ(w_i)
       │         │   where w_i = quiz_confidence[item.primary_accord]
       │         ├─ Step 3: Nearest-neighbor search
       │         │   cosine similarity(centroid, all item embeddings)
       │         │   → candidate pool (top-200)
       │         ├─ Step 4: [Optional] Quiz reranker
       │         │   blended = (1-α) × gs_score + α × quiz_accord_score
       │         │   α = 0.3 (configurable, disabled by default per research)
       │         └─ Step 5: Feature-based failover
       │             If GraphSAGE centroid fetch fails or returns < threshold:
       │             degrade to feature-based scoring using quiz accord confidence
       │
       ├── State 2 (Cold User, 1–5 ratings)
       │    └── Hybrid (GraphSAGE → Feature-based blend)
       │         ├─ Step 1: Compute GraphSAGE centroid from seed items
       │         │   seed items = user's rated items (rating ≥ threshold)
       │         │   centroid = weighted mean of gs_embeddings, w = rating_score / 10
       │         ├─ Step 2: GraphSAGE retrieval → candidate pool (top-100)
       │         ├─ Step 3: Feature-based retrieval → candidate pool (top-100)
       │         ├─ Step 4: Blend scores
       │         │   β = clamp((ratings_count - 1) / 4, 0, 1)  # linear 1→0
       │         │   final_score = β × gs_score + (1-β) × feature_score
       │         └─ Step 5: Apply diversity penalty
       │
        ├── State 3 (Warm User, 5–19 ratings)
        │    └── Feature-based primary + GraphSAGE exploration
        │         ├─ Step 1: Feature-based retrieval (primary)
        │         │   accord/note overlap scoring from rated items
        │         │   → candidate pool (top-100)
        │         ├─ Step 2: GraphSAGE diversity injection
        │         │   GraphSAGE centroid → top-20 items NOT in feature-based pool
        │         │   Inject top-2 items at positions 2, 5 (every 3rd slot from index 2)
        │         └─ Step 3: Final ranking by feature score
        │             Exploration items promoted: min 2 per top-10
       │
       └── State 4 (Mature User, 20+ ratings)
            └── Feature-based + diversity injection
                 ├─ Step 1: Feature-based retrieval (top-100)
                 ├─ Step 2: Intra-list diversity rerank
                 │   Penalize items whose top 3 accords match >2 existing items
                 ├─ Step 3: Reintroduce diversity from lower-ranked candidates
                 └─ Step 4: Track saturation — skip if last 3 recs were identical
```

---

## 4. GraphSAGE Role Definition

### What GraphSAGE does

GraphSAGE is a **Preference Initialization Layer** — a bridge between zero interaction history and the feature-based system.

- **Input:** Item cold-start (fragrance features, Jaccard graph neighborhood)
- **Output:** 64-dim unit-normalized embeddings encoding structural fragrance relationships
- **Training (research pipeline):** Contrastive InfoNCE loss over Jaccard note-similarity edges
- **Build-time export (one-time):** The trained model runs inductive inference over the full catalog (features + Jaccard graph) to produce frozen L2-normalized 64-dim embeddings. This is a one-time step (`ml/export/export_jaccard_embeddings.py`), not a runtime operation.
- **Runtime retrieval:** The serving layer loads precomputed embeddings from disk. No model loading, no forward pass, no PyTorch dependency at runtime.

### Role by user state

| State | GraphSAGE role | Rationale |
|-------|----------------|-----------|
| 0     | Unused | No user preference to initialize |
| 1     | Primary scorer + ranker | Only signal available. Quiz confidence weights the centroid. |
| 2     | Co-equal scorer (β blend 1→0) | Bridge during signal accumulation. Feature-based takes over as ratings grow. |
| 3     | Exploration layer | Inject structural diversity. Feature-based is more accurate per research. |
| 4     | Diversity injection | Prevent over-specialization. GraphSAGE surfaces "surprising but structurally related" items. |

### What GraphSAGE does NOT do

- GraphSAGE does NOT solve cold-user — it has no user nodes, user features, or user embeddings
- GraphSAGE does NOT replace feature-based scoring — research shows feature-based is consistently more accurate
- GraphSAGE does NOT rank everything alone — it always feeds into a blended or secondary ranking step
- GraphSAGE does NOT run real-time retraining — it is a frozen checkpoint until the next retraining cycle

---

## 5. Retrieval Strategy Decision

### Phase 7 baseline: Single weighted centroid

```
centroid = Σ(w_i × gs_embedding_i) / Σ(w_i)
```

- **w_i:** rating_score / 10 for States 2–4; quiz_confidence[primary_accord] for State 1
- **Retrieval:** cosine similarity(centroid, all item embeddings) → top-N
- **Justification:** For users with consistent preferences (single accord cluster), centroid falls near the real item cluster in embedding space. This is the common case.
- **Mathematical equivalence:** Mean cosine similarity to centroid = mean of per-seed cosine similarities across all candidate items. Centroid nearest-neighbor retrieval ≈ query-by-committee average.

### Canonical retrieval artifacts

The centroid + KNN operation loads precomputed L2-normalized embeddings, not a checkpoint:

| Artifact | Path | Description |
|----------|------|-------------|
| `node_embeddings_jaccard.npy` | `ml/models/serving/v1/node_embeddings_jaccard.npy` | L2-normalized GraphSAGE-Jaccard embeddings, shape `[4559, 64]`, dtype float32 |
| `node_ids_jaccard.json` | `ml/models/serving/v1/node_ids_jaccard.json` | 4,559 fragment IDs, 1:1 aligned with embedding matrix rows |
| `metadata.json` | `ml/models/serving/v1/metadata.json` | Provenance: source checkpoint, export timestamp, graph params, validation results |

These artifacts are produced by the Jaccard Embedding Export Pipeline (`ml/export/export_jaccard_embeddings.py`), a one-time build step that runs `graphsage_jaccard.pt` forward pass over the full catalog and L2-normalizes the output. The serving layer loads them directly — no checkpoint, no torch, no forward pass at runtime.

### Centroid disagreement instrumentation (implemented alongside baseline)

```
pairwise_sims = cosine_similarity(seed_embeddings)          # K×K matrix
mean_pairwise  = mean(pairwise_sims[upper_tri])             # single float
# Log statistic for Phase 7.1 evaluation planning
logger.info("centroid_disagreement", mean_pairwise=mean_pairwise, seed_count=K)
```

The system computes and stores pairwise similarity statistics for every recommendation request. These statistics are logged for offline analysis. No routing decisions are made based on disagreement. No multi-centroid retrieval is implemented. The data feeds Phase 7.1 experimental evaluation planning only.

---

## 6. State Transition Rules

### Hard transitions (immediate, no smoothing)

```
State 0 → State 1: Quiz completed (POST /quiz/finalize)
                    The quiz response generates a confidence vector.
                    User is immediately promoted to State 1.
                    This is a guest session — no persistence across sessions
                    unless user registers.
```

### Smoothed transitions (β blend across boundary)

State 2 → State 3 (at rating 5):

```
β = clamp((ratings_count - 1) / 4, 0, 1)
  ratings_count=1 → β=0.00 (pure GraphSAGE)
  ratings_count=3 → β=0.50 (equal blend)
  ratings_count=5 → β=1.00 (pure feature-based)
```

This ensures no "jerk" in recommendations when a user crosses a boundary.

### Regressive transitions

If a user's ratings are deleted (GDPR, account deletion), the state regresses:
- 20+ → 0 ratings: State 4 → State 0 (popularity-only, effectively a new user)
- State does NOT regress on quiz retake (quiz is initialization, ratings are the committed signal)

---

## 7. Failure Strategy

| Failure mode | Detection | Fallback |
|-------------|-----------|----------|
| Embedding artifact load fails | `np.load()` or `json.load()` raises at startup | Service reports unhealthy; Phase 8 dispatcher routes to feature-based only |
| Embedding cache has NaN | `isnan(embeddings).any()` at startup | Fail startup; artifact must be re-exported |
| Redis cache miss | `cache.get()` returns None | Recompute full dispatch (cold path) |
| Pinecone unavailable | Connection timeout | Use in-memory numpy embeddings (loaded at startup) |
| Feature-based scoring error | Exception in scoring function | GraphSAGE-only for that request |
| All retrieval paths fail | No candidates from any source | Empty result set returned. No state ends with popularity fallback — that is a startup-level concern, not dispatch-level. |
| Centroid has no seeds | Empty seed_items list | Fallback chain per state. State 1 falls back to feature-based. State 2 falls back to feature-based. |

### Health check requirements

- Embedding artifacts: verify `node_embeddings_jaccard.npy` and `node_ids_jaccard.json` exist, `len(node_ids) == embeddings.shape[0]`, no NaN, no Inf, no duplicate IDs at startup
- Normalization: verify all embedding rows are L2-unit-normalized (min/max norm within 0.999–1.001)
- Provenance: verify `metadata.json` exists and source checkpoint reference is consistent
- Feature index: verify accord/note lookup table loads completely

---

## 8. Open Research Questions (Phase 7.1+)

### Question 1: Centroid disagreement analysis

**RQ:** How does centroid disagreement (low pairwise similarity among seed embeddings) correlate with recommendation quality degradation?

**Instrumentation data:** Per-request `mean_pairwise` similarity statistic collected from production (Phase 7).

**Experiment:** Analyze logged disagreement statistics against implicit feedback (rating of recommended items). Determine whether a pairwise-similarity threshold exists below which single-centroid retrieval produces measurably worse recommendations. If evidence shows a meaningful degradation threshold, design a multi-centroid retrieval experiment for a future phase.

**Priority:** HIGH — directly affects retrieval quality for diverse-interest users. Phase 7 instruments the data; Phase 7.1+ analyzes it.

### Question 2: Quiz reranker efficacy

**RQ:** Does the quiz reranker (α=0.3) add value beyond pure GraphSAGE centroid retrieval for State 1 users?

**Status:** Research evidence says NO — mean NDCG 0.496 (quiz) vs 0.504 (pure cold), high variance.

**Experiment:** Re-evaluate with real user data when available. Disabled by default until proven.

**Priority:** MEDIUM — currently a feature flag with evidence against enabling.

### Question 3: Diversity injection parameters

**RQ:** What is the optimal number and position of diversity-injected items for State 3 and State 4?

**Experiment:** A/B test 1–4 injected items at varying positions. Measure NDCG@10, intra-list dissimilarity, and user engagement proxy.

**Priority:** LOW — needed only when real user data is available.

### Question 4: Embedding staleness detection

**RQ:** How does recommendation quality degrade as GraphSAGE embeddings age relative to catalog changes?

**Experiment:** Inject synthetic new items, measure NDCG drop vs retrained model. Establish drift threshold.

**Priority:** LOW — deferred to Phase 9 (graph sync).

---

## 9. Explicitly Rejected Alternatives

| Alternative | Why rejected |
|-------------|--------------|
| **GraphSAGE as sole ranker** | Research evidence: Feature-Only beats GraphSAGE at every coldness level. Using GraphSAGE alone would produce worse recommendations for all users. |
| **Neural collaborative filtering** | Requires user-item interaction matrix. Scentrix is a zero-interaction domain. NCGF is architecture for warm-start, not cold-start. |
| **Matrix factorization** | Same reason as NCF. Requires interaction data that does not exist and will not exist in meaningful volume. |
| **Random node split for evaluation** | Already corrected in Phases 4–5. Random split gives unrealistically optimistic metrics by leaking graph structure. |
| **Cold-user graph construction** | Adding user nodes to the Jaccard graph would require user-item edges that don't exist at cold-start. Would create sparse, disconnected user nodes with no benefit. |
| **Online learning / real-time retraining** | GraphSAGE retraining takes hours on the full catalog. Real-time retraining is computationally infeasible and architecturally unnecessary — embeddings are stable between retraining cycles. |
| **Reinforcement learning bandit** | Requires real-time user feedback loop at production scale. Premature for a research demo. Deferred indefinitely. |
| **LLM-based recommendation** | High latency, high cost, non-deterministic. Would reduce the research contribution (graph-based preference initialization) to a prompt engineering exercise. |
| **Pure popularity baseline** | Rejected as the *only* strategy. Popularity-only is the fallback (State 0) but is never the primary for users with any signal. |
| **Multi-centroid retrieval (Phase 7)** | Deferred. Phase 7 implements centroid disagreement instrumentation only — no routing decisions, no multi-centroid retrieval. Multi-centroid is a potential future experiment pending disagreement data analysis. |

---

## 10. Final Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SCENTRIX RECOMMENDATION ARCHITECTURE                   │
│                           (Frozen: 2026-05-30)                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         STATE DISPATCHER                               │
│  rating_count + quiz_completed → state                                │
└────────────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ State 0  │  │ State 1  │  │ State 2  │  │State 3/4 │
    │ Popular  │  │GraphSAGE │  │ Hybrid   │  │ Feature  │
    │ -ity only│  │primary   │  │ β blend  │  │ -based + │
    │          │  │± quiz    │  │ 1.0→0.0  │  │ diversity│
    └──────────┘  └──────────┘  └──────────┘  └──────────┘
         │              │              │              │
         └──────────────┼──────────────┼──────────────┘
                        ▼              ▼
              ┌──────────────────────────────────┐
              │     RETRIEVAL BACKENDS           │
              │  ┌────────────┐ ┌──────────────┐ │
              │  │ GraphSAGE  │ │ Feature-Based│ │
              │  │ 64-dim     │ │ accord/note  │ │
              │  │ embeddings │ │ overlap score│ │
              │  │ Centroid + │ │              │ │
              │  │ KNN search │ │              │ │
              │  └────────────┘ └──────────────┘ │
              │  ┌──────────────────────────────┐ │
              │  │ Popularity (global score)    │ │
              │  │ (fallback for all states)    │ │
              │  └──────────────────────────────┘ │
              └──────────────────────────────────┘

ARCHITECTURE INVARIANTS:
• GraphSAGE is ALWAYS a Preference Initialization Layer
• Feature-based ALWAYS outranks GraphSAGE as signal grows
• Every path has a fallback to simpler path
• Centroid retrieval is weighted single-centroid baseline
• Runtime loads precomputed L2-normalized embeddings — no model, no forward pass, no PyTorch
• Centroid disagreement is instrumented only — no routing decisions
• Quiz reranker is disabled by default
• All recommendations are traceable to source
```

### Key numbers

| Parameter | Value | Source |
|-----------|-------|--------|
| GraphSAGE embedding dimension | 64 | graphsage_wrapper.py (contrastive loss output) |
| Nearest-neighbor candidate pool | 200 (State 1), 100 (States 2–4) | Architecture decision |
| Centroid seed count | 5 (State 1 via quiz), all rated (States 2–4) | Architecture decision |
| Blend β range | 0.0 → 1.0 over ratings 1→5 | Architecture decision |
| β smoothing window | Linear over ratings_count = 1..5 | Architecture decision |
| Quiz reranker α | 0.3 (disabled by default) | Research evidence (mean NDCG 0.496 vs 0.504) |
| Diversity injection count | 2 items (States 3–4) | Architecture decision (experimental) |
| Centroid disagreement instrumentation | Logged per request for offline analysis | Architecture decision (no routing impact) |
| Embedding artifact path | `ml/models/serving/v1/node_embeddings_jaccard.npy` | Export pipeline artifact |
| ID mapping artifact path | `ml/models/serving/v1/node_ids_jaccard.json` | Export pipeline artifact |
| Provenance artifact | `ml/models/serving/v1/metadata.json` | Export pipeline artifact |
| Embedding count | 4,559 (100% of cleaned catalog) | Export pipeline validation |
| Embedding normalization | L2 unit-normalized | Applied post-export, matches evaluation retrieval |
| Runtime torch dependency | None | Architecture decision |
| Runtime model loading | None (precomputed embeddings only) | Architecture decision |
| Popularity fallback | Always available as last resort | Architecture invariant |

> **Implementation Note (2026-06-02):** State 1 (Quiz User) remains architecturally valid. The dispatch tree, centroid computation, quiz reranker, and fallback paths for State 1 are implemented and testable via API calls. However, the frontend quiz (`StandardQuiz.tsx`) routes to `/recommendations` with raw ratings (not `quiz_confidence`), bypassing `POST /quiz/finalize`. Users arrive at recommendations with rating_count=8 (from quiz responses), entering State 2 (1-4 ratings) or State 3 (5-19) depending on quiz length — never State 1. The Star button on FragranceCards routes State 0 → State 2 directly via a single rating. State 1 will become reachable when the quiz frontend calls `POST /quiz/finalize` and sends `quiz_confidence` to the backend (Phase 11).

---

*Architecture Freeze: 2026-05-30*
*Phase 7 implementation complete — all artefacts, startup validation, centroid, KNN, and disagreement instrumentation verified.*
*Next review: before Phase 8 implementation*
*Authority: Phase 6.5 Architecture Validation*
