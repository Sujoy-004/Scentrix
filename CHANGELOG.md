# CHANGELOG

## [Unreleased] — Phase 5 In Progress

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
- run_learning_curve (line 927) → fixed to build_jaccard_graph ✅
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

---

## Open Questions (must resolve before Phase 5 complete)

1. **quiz_init NDCG=0.405 < pure_cold NDCG=0.504** — quiz bias is HURTING performance
   Root cause unknown. Two candidates:
   a. Additive += on one-hot features corrupts the feature space (one-hot no longer sums to 1)
   b. quiz_length=5 injects too much noise across 5 accords simultaneously
   Next step: diagnose before adding alpha blending

2. **Alpha blending not implemented** — current bias is raw += with no scaling
   Need: node_features[idx, :48] = (1-α) * original + α * confidence
   Sweep α ∈ {0.0, 0.25, 0.5, 0.75, 1.0} to find optimal blend

3. **Learning curves not yet run** — run_learning_curve uses build_jaccard_graph (fixed) but not executed

4. **Stratified analysis not yet run** — per-accord NDCG breakdown pending

5. **Spoken answer "why graph over Feature-Only"** — drafted in paper, not memorized

---

## Next Steps (in order)

1. Diagnose quiz_init regression (0.405 < 0.504) — check feature corruption
2. Implement alpha blending in _run_quiz_init
3. Sweep alpha, report optimal blend NDCG
4. Run learning curves (python -m ml.eval.pipeline --mode learning_curve)
5. Run stratified analysis per accord family
6. Memorize spoken answer for MEXT interview (June 28)

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
|---|---|---|
| 1 — Pipeline & Data Foundation | ✅ Complete | Clean dataset, Neo4j graph |
| 2 — Evaluation Infrastructure | ✅ Complete | Cold-start splitter, ranx metrics |
| 3 — Baselines & Comparison | ✅ Complete | Popularity, Random, bootstrap |
| 4 — GraphSAGE Pipeline | ✅ Complete (with rework) | Jaccard graph, ablation confirmed |
| 5 — Research Differentiators | 🔄 In Progress | quiz_init baseline done, regression to diagnose |
| 6 — MEXT Demo | 🔲 Not started | — |

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
- _run_quiz_init, run_learning_curve, run_ablation_study: build_similarity_graph → build_jaccard_graph
- EvalConfig: catalog_path + jaccard_threshold fields added

**Working protocol:**
- Claude inspects and directs via targeted shell commands
- Agent executes, pastes output back
- Every decision committed to CHANGELOG.md
- No claims without results
- CHANGELOG.md is source of truth — always read first

**To resume:** upload CHANGELOG.md + query.txt (repo tree). First task is diagnosing quiz_init regression.
