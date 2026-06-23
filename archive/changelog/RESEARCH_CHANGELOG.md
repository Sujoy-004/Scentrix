# Research CHANGELOG — Archived Audit Trail

**Archived from:** CHANGELOG.md (pre-Phase 13 restructuring)
**Archive date:** 2026-06-23
**Purpose:** Preserve full research audit trail for reproducibility and reference. This document is NOT part of the primary repository narrative.

## Phase 5.1/7.1/8.1 — Evaluation Audit, USER_VECTOR, & Pipeline Validation (2026-06-06)

Two parallel sub-phase efforts transformed the architecture and evaluation methodology:

**Phase 5.1 — Evaluation Audit Remediation:** Discovered that NDCG@10 was computed as RR@10 (break on first relevant item, no accumulation). Ground truth used note-Jaccard >0.20, which is the same signal used to build the Jaccard graph — creating circular evaluation. Fix A (true NDCG@10) applied to `metrics.py` (committed). Fix B (brand+accord ground truth) implemented in `pipeline.py` / `run_bootstrap.py` with `GT_MODE=brand_accord` env var and executed (2026-06-07). All published numbers superseded by reproducible Fix B results; see main table below.

**Phase 7.1 — USER_VECTOR Migration:** The quiz information audit revealed that per-item ratings were sent in the frontend payload but discarded by the backend. Replaced the centroid pipeline for State 1 with a direct user-vector: weighted sum of quiz item embeddings → KNN retrieval. Proved +14.9% FH / +41.4% NDCG over centroid. `DispatchRequest.ratings` dual-purpose bug fixed via `quiz_ratings` / `ratings` split.

**Phase 8.1 — Dispatcher vs Legacy Validation:** 5-state dispatcher validated against legacy (State 0 top-5 identical). Detailed per-state comparison captured in Phase 8.1 CONTEXT.md.

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

## Requirement Traceability

20 v1 requirements (PIPE-01–03, EVAL-01–07, RSCH-01–07, DEMO-01–03) — all complete across Phases 1–6. 12 v2 requirements (SRV-01–10) — Phases 7–8 and 11 complete; Phases 9–10 dropped/rescoped; Phase 12A (SRV-07) and 12B (SRV-09) complete; 12C (SRV-08) deferred; 12D (SRV-10) dropped.

| Phase | Requirements | Status |
|---|---|---|
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
