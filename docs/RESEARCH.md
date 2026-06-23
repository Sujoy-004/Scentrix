# Scentrix — Research Thesis

## Abstract

Graph-Based Preference Initialisation for Cold-Start Recommendation in Zero-Interaction Domains. A full evaluation of GraphSAGE on a Jaccard-similarity graph for cold-start fragrance recommendation, with a corrected evaluation methodology that surfaced surprising findings about model complexity vs evaluation rigor.

## Thesis

Cold-start preference initialization via direct user-vector from quiz ratings. The original pipeline (confidence → seeds → centroid → GraphSAGE) discarded per-item rating information at every stage. The USER_VECTOR path (rating-weighted embedding sum → KNN) preserves the full signal and achieves +14.9% FH / +41.4% NDCG over centroid — simpler, faster, better.

## Canonical Results (Fix B applied — brand_accord GT, true NDCG@10)

⚠️ Phase 5.1 evaluation audit identified two flaws: (1) NDCG@10 was computed as RR@10, and (2) ground truth used note-Jaccard >0.20 (circular with the Jaccard graph). Fix A (true NDCG) and Fix B (brand+accord GT) have been applied. Values below are from the canonical reproducible pipeline:

```bash
SCENTRIX_EVAL_GT_MODE=brand_accord python -m ml.eval.pipeline --mode pure_cold --seed 42
```

| Model | Precision@10 | NDCG@10 | Recall@10 |
|---|---|---|---|
| GraphSAGE-Jaccard (pure_cold) | 0.0567 | **0.115** | 0.1396 |
| GraphSAGE-Embedding (pure_cold) | 0.0550 | **0.095** | 0.1075 |
| Feature-Only | 0.1825 | **0.399** | 0.4136 |
| Content-Only | 0.0193 | **0.047** | 0.0465 |
| Popularity | 0.0000 | **0.000** | 0.0000 |
| Random | 0.0007 | **0.001** | 0.0012 |

## Bootstrap Significance (n=10000, brand_accord GT)

Jaccard vs Embedding: p=0.008, d=0.11 (Jaccard leads by 1.21×). Jaccard vs Feature-Only: p=1.000, d=−0.96 (Feature-Only leads by 3.47×).

## Headline

Under non-circular brand+accord ground truth, Feature-Only (0.399 NDCG@10) dominates GraphSAGE-Jaccard (0.115) by 3.47×. GraphSAGE-Jaccard marginally outperforms GraphSAGE-Embedding (0.095) by 1.21× — structural independence helps modestly, but direct feature matching is substantially more predictive of brand+accord relevance on this dataset.

## Key Architecture Decisions

| Decision | Rationale | Outcome |
|---|---|---|
| GraphSAGE on Neo4j | Graph-based preference init for cold-start — core hypothesis | Complete — Jaccard NDCG@10=0.115 vs Embedding 0.095 |
| Adaptive confidence quiz | Preference init without interaction history | Complete — analyzed; does not beat pure_cold (0.496 vs 0.504) |
| Popularity + Random baselines | Only honest cold-start baselines | Complete — NDCG@10=0.008, 0.021 |
| Precision@10 + NDCG@10 | Standard metrics for target labs | Complete — ranx-based, operational |
| Local Docker only | No cloud costs, sufficient | Confirmed |
| GraphSAGE as Preference Init Layer | Feature-Only beats GS at every coldness level by up to 3.5× | Architecture Freeze — GS alongside FB, never alone |
| USER_VECTOR over centroid | Preserves per-item signal, simpler, faster | Production — +14.9% FH / +41.4% NDCG, ~10× faster |

## Threshold Analysis

⚠️ Values from the original pipeline used circular jaccard GT. Under Fix B (brand_accord GT), absolute values are lower but the pattern — higher thresholds produce higher NDCG at the cost of coverage — is consistent. Threshold 0.20 remains the canonical choice, balancing coverage (99.2%) with reasonable NDCG.

| Threshold | Edges | Deg-0 | NDCG@10 | Precision@10 | Recall@10 |
|---|---|---|---|---|---|
| 0.10 | 21,452 | 12 | 0.082 | 0.043 | 0.102 |
| 0.15 | 20,124 | 27 | 0.084 | 0.045 | 0.102 |
| **0.20** | **16,244** | **84** | **0.113** | **0.054** | **0.135** |
| 0.25 | 10,821 | 204 | 0.168 | 0.082 | 0.189 |
| 0.30 | 6,341 | 369 | 0.233 | 0.108 | 0.253 |

## Coldness Stratification

| Model | Level 0 (0 int.) | Level 1 (1-3) | Level 2 (4+) |
|---|---|---|---|
| GraphSAGE-Embedding | 0.095 | 0.071 | 0.131 |
| GraphSAGE-Jaccard | 0.115 | 0.081 | 0.152 |
| Feature-Only | 0.399 | 0.401 | 0.419 |
| Popularity | 0.000 | 0.001 | 0.001 |

Feature-Only leads all levels by a wide margin under brand_accord GT. Feature-Only and Popularity are near-constant across levels (feature-based signal does not degrade with coldness). GraphSAGE-Jaccard is monotonic across levels. GraphSAGE-Embedding non-monotonic (drops from 0.095 to 0.071 at Level 1 — low-pop connectivity weakness). Both GraphSAGE variants benefit from more interaction signal at Level 2, unlike Feature-Only which plateaus.

## Archived Research

### quiz_init (superseded by USER_VECTOR)

The centroid-based quiz_init was evaluated under the original pipeline (circular jaccard GT, RR-as-NDCG). It does NOT reliably beat pure_cold (mean NDCG 0.496 vs 0.504, std 0.023, beats baseline 2/5 runs). Deemed not reproducible under corrected methodology. Superseded in production by USER_VECTOR (direct embedding lookup from per-item ratings).

### Original pipeline claims

⚠️ **Historical record only.** The claim below and all old-pipeline results tables have been superseded by Fix B (brand_accord GT, true NDCG). The "2.7× improvement" was an artifact of circular evaluation (jaccard GT + RR-as-NDCG). Under non-circular evaluation, the Jaccard-vs-Embedding gap is 1.21× (0.115 vs 0.095), and Feature-Only dominates both at 0.399 NDCG.

*Archived claim: "Graph construction methodology is the critical determinant of GNN performance in cold-start recommendation. Embedding-derived similarity graphs introduce feature circularity that degrades NDCG by 63% relative to independent baselines. Replacing circular edges with structurally independent Jaccard similarity over fragrance notes recovers 2.7× performance improvement (NDCG 0.183 → 0.494, p≤0.001, d=0.93)."*

## Future Work

### Q1: Centroid disagreement analysis (HIGH)
How does centroid disagreement correlate with recommendation quality degradation? Currently logged per request but not analyzed.

### Q2: Quiz reranker efficacy (MEDIUM)
Does the quiz reranker (α=0.3) add value beyond pure GraphSAGE centroid for State 1? Not re-evaluated under Fix B.

### Q3: Diversity injection parameters (LOW)
Optimal number and position of diversity-injected items for States 3–4. Needs real user data.

### Q4: Embedding staleness detection (LOW)
How does recommendation quality degrade as embeddings age relative to catalog changes?

## Reproducibility

```bash
# Canonical run (Fix B, brand_accord GT)
python -m ml.eval.pipeline --mode pure_cold --seed 42

# Bootstrap significance (n=10000)
python -m ml.eval.run_bootstrap

# Quiz sensitivity analysis
python -m ml.eval.pipeline --mode quiz_sensitivity

# Coldness stratification
python -m ml.eval.pipeline --mode stratification
```

---

See [README.md](../README.md) for the project overview, architecture, and quick start.
