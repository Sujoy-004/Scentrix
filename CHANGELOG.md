
# CHANGELOG

## [Unreleased] — Phase 4 Rework + Eval Hardening

### What happened (post-Phase 4 audit, this session)

**Root cause identified and fixed — graph_builder.py**
- Original GraphSAGE used KNN edges built from embeddings.npy (cosine distance)
- Node features also contained embeddings.npy → feature circularity
- GraphSAGE aggregated neighbors already maximally similar in the same space
- Result: trained model worse than raw feature cosine similarity
- Fix: replaced KNN edges with Jaccard similarity over fragrance notes
  (primary_accord_i == primary_accord_j AND Jaccard(notes) > 0.20)
- Zero embedding signal in edge construction

**Results after fix**
| Model | NDCG@10 |
|---|---|
| GraphSAGE-Embedding (original, circular) | 0.183 |
| GraphSAGE-Jaccard (fixed) | 0.501–0.523 |
| Feature-Only (raw 432-dim cosine, near-oracle) | 0.557 |
| Content-Only (Jaccard notes, oracle/invalid) | 0.581 |
| Popularity | 0.008 |
| Random | 0.031 |

**Bootstrap significance tests (n=10000)**
- Jaccard vs Embedding: p=0.001, d=0.93 ✅
- Jaccard vs Popularity: p=0.001, d=1.87 ✅
- Jaccard vs Random: p=0.001, d=1.72 ✅
- Jaccard vs Feature-Only: p=1.000, d=-0.149 ❌ (Jaccard does NOT beat Feature-Only)

**Threshold sweep — first attempt (INVALID, discarded)**
- Sweep used raw Jaccard edge scores as recommendations
- Ground truth also defined by Jaccard > threshold
- When threshold ≤ 0.20, recommendations = ground truth → NDCG=0.992 (circular)
- Discarded entirely

**Threshold sweep — second attempt (valid)**
- Each threshold: build graph → train GraphSAGE → embedding cosine sim → evaluate
- Results:
| Threshold | Edges | Deg0 | NDCG@10 |
|---|---|---|---|
| 0.10 | 21452 | 12 | 0.439 |
| 0.15 | 20124 | 27 | 0.452 |
| 0.20 | 16244 | 84 | 0.491 |
| 0.25 | 10821 | 204 | 0.503 |
| 0.30 | 6341 | 369 | 0.528 |
- Monotonic rise is UNCONFIRMED as genuine — may be fallback inflation
- Next step: split degree-0 vs degree>0 cold items and report NDCG separately

---

## Open Questions (must resolve before Phase 5)

### Resolved: Threshold Sweep Finding (confirmed real)

Degree-split analysis confirms sweep rise is genuine, not fallback inflation.
Group A (degree>0) NDCG rises monotonically as threshold increases:
  0.10 → 0.432, 0.15 → 0.455, 0.20 → 0.494, 0.25 → 0.554, 0.30 → 0.642

Finding: Stricter Jaccard thresholds produce higher-quality edges and better 
GraphSAGE representations, at the cost of coverage (843→551 connected items).

Design decision: threshold=0.20 selected as primary operating point.
Justification: 99.2% cold item coverage (836/843) with NDCG=0.494.
Tradeoff explicitly acknowledged — not arbitrary.

This is a second research finding beyond the Embedding vs Jaccard ablation:
"Edge quality vs coverage tradeoff in graph-based cold-start recommendation."

2. **Threshold 0.20 justification** — currently matches ground truth definition (circularity risk in framing)
   Need to either justify independently or acknowledge as a design choice

3. **Feature-Only ceiling** — Jaccard does not significantly beat Feature-Only
   Interview question: "Why use a graph at all?" needs a prepared answer

4. **p-value floor** — all significant tests floor at p=0.001 (minimum for n=10000 is 0.0001)
   Consider reporting as p≤0.001 not p=0.001

---

## Locked Research Claim (current best language)

"Graph construction methodology is the critical determinant of GNN performance 
in cold-start recommendation. Embedding-derived similarity graphs introduce 
feature circularity that degrades NDCG by 63% relative to independent baselines. 
Replacing circular edges with structurally independent Jaccard similarity over 
fragrance notes recovers 2.7× performance improvement (NDCG 0.183 → 0.501, 
p≤0.001, d=0.93)."

Note: This claim does not assert GraphSAGE beats Feature-Only. It asserts 
graph construction methodology determines model quality. That is what the 
ablation supports.

---

## Next Steps (in order, before touching Phase 5)

1. ~~Run degree-split on sweep → confirm or discard threshold finding~~ ✅ Done
2. Update ROADMAP.md Phase 4 status to reflect rework
3. Prepare spoken answer to "why use a graph if Feature-Only matches?"
4. Then proceed to Phase 5

---

## Phase History

| Phase | Status | Key Output |
|---|---|---|
| 1 — Pipeline & Data Foundation | ✅ Complete | Clean dataset, Neo4j graph |
| 2 — Evaluation Infrastructure | ✅ Complete | Cold-start splitter, ranx metrics |
| 3 — Baselines & Comparison | ✅ Complete | Popularity, Random, bootstrap |
| 4 — GraphSAGE Pipeline | ✅ Complete (with rework) | Jaccard graph, ablation confirmed |
| 5 — Research Differentiators | 🔲 Not started | — |
| 6 — MEXT Demo | 🔲 Not started | — |

---

### Decision: Dataset size kept at ~5k (quality-filtered elite subset)

Original catalog: ~22,740 items
Current eval dataset: ~5,000 items (fra_elite_24k.json filtered via filter_elite.py)
Reason for filter: quality gates applied during ml/pipeline/filter_elite.py
Deployment constraint (Railway 512MB RAM) was original trigger but is no longer relevant.
Decision: keep filtered dataset for all MEXT eval results for consistency.
Rationale: all current eval numbers (NDCG, bootstrap, sweep) computed on this set.
Reverting would invalidate all results and require full rerun — not feasible before June 28.
Framing: "quality-filtered elite subset" in research write-up. Full 22k is future work.

---

### Decision: Scentrix framed as hybrid research + engineering project

Primary goal shifted from MEXT-only to dual-purpose:
1. Research paper framing — cold-start GNN recommendation with ablation study,
   significance tests, and quantified findings
2. Full-stack engineering showcase — FastAPI + Next.js + Neo4j + PostgreSQL + 
   Redis + Docker + GraphSAGE, production-grade, deployed

This framing works for: MEXT interview, placement drives, portfolio, future publication.
MEXT selection not yet confirmed — proceeding regardless as research output
has independent value.

---

### Handoff Snapshot — Final Numbers (for new chat continuity)

**Full results table:**
| Model | Precision@10 | NDCG@10 | Recall@10 |
|---|---|---|---|
| GraphSAGE-Jaccard | 0.0745 | 0.494–0.523 | 0.0926 |
| GraphSAGE-Embedding | 0.0306 | 0.183–0.191 | 0.0216 |
| Feature-Only | 0.0782 | 0.557 | 0.0932 |
| Content-Only (oracle/invalid) | 0.0860 | 0.581 | 0.1225 |
| Popularity | 0.0019 | 0.008 | 0.0010 |
| Random | 0.0045 | 0.031 | 0.0011 |

Evaluated on 843 cold items (from 920 cold split, 77 excluded — zero relevant ground truth).
Ground truth: primary accord match + Jaccard(notes) > 0.20. No embeddings.npy in GT.

**Bootstrap significance tests (n=10000):**
- Jaccard vs Embedding: p≤0.001, d=0.93 ✅
- Jaccard vs Popularity: p≤0.001, d=1.87 ✅
- Jaccard vs Random: p≤0.001, d=1.72 ✅
- Jaccard vs Feature-Only: p=1.000, d=-0.149 ❌

**Degree-split table (threshold sweep):**
| Threshold | Edges | A_n | A_NDCG | B_n | B_NDCG | Aggregate_NDCG |
|---|---|---|---|---|---|---|
| 0.10 | 21452 | 843 | 0.432 | 0 | 0.000 | 0.432 |
| 0.15 | 20124 | 843 | 0.455 | 0 | 0.000 | 0.455 |
| 0.20 | 16244 | 836 | 0.494 | 7 | 0.255 | 0.492 |
| 0.25 | 10821 | 716 | 0.554 | 127 | 0.241 | 0.507 |
| 0.30 | 6341 | 551 | 0.642 | 292 | 0.317 | 0.529 |

Finding: sweep rise is genuine (not fallback inflation). Stricter thresholds
produce better representations at cost of coverage. Threshold=0.20 chosen:
99.2% coverage (836/843) with NDCG=0.494.

**Locked research claim:**
"Graph construction methodology is the critical determinant of GNN performance
in cold-start recommendation. Embedding-derived similarity graphs introduce
feature circularity that degrades NDCG by 63% relative to independent baselines.
Replacing circular edges with structurally independent Jaccard similarity over
fragrance notes recovers 2.7× performance improvement (NDCG 0.183 → 0.494,
p≤0.001, d=0.93)."

Note: Claim does not assert GraphSAGE beats Feature-Only. It asserts graph
construction methodology determines model quality. That is what the ablation supports.

**Open questions still pending:**
1. Threshold 0.20 matches ground truth definition — acknowledge as design choice in write-up
2. Prepare spoken answer: "why use a graph if Feature-Only matches performance?"
3. Phase 5 not started — quiz-init evaluation, stratification, learning curves
