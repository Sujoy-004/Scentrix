# CHANGELOG

## [Unreleased] — Phase 5 In Progress

### State Synchronization (2026-05-28)

**Source of truth:** CHANGELOG.md only. .planning/ files are secondary and must never be marked complete ahead of CHANGELOG confirmation.

**Phase 5 status:** In progress. One task remaining:
- Stratified analysis (per-accord NDCG breakdown) — NOT YET RUN
  Command: `python -m ml.eval.pipeline --mode stratification`

**Phase 6 status:** NOT STARTED. 06-UAT.md reset to pending. Phase 6 cannot begin until Phase 5 stratified analysis is complete and research_paper.md final framing is locked.

**Verified completed this session (Phase 5):**
- quiz_init reranker fix (+= → post-prediction reranker)
- quiz_length sweep [5, 10, 20] across 5 seeds — mean NDCG@10 peaks at 0.508 (length=20), marginal improvement, high variance
- `run_learning_curve` renamed to `run_quiz_sensitivity` across 6 files
- Quiz sensitivity results: quiz_init does not beat pure_cold at any quiz_length (1–10). Gap: 0.002–0.006, pure_cold leads consistently.
- CHANGELOG updated, reporting.py corrected, tests updated

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

**Open questions before Phase 5 complete:**
1. ~~Can a longer quiz (quiz_length > 5) reduce variance and push mean above 0.504?~~ — answered
2. ~~Quiz sensitivity curves not yet run~~ — done with reranker fix
3. Stratified analysis not yet run — per-accord NDCG breakdown pending
4. MEXT spoken answer for "why graph over Feature-Only" not yet memorised

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

3. **Stratified analysis not yet run** — per-accord NDCG breakdown pending

4. **Spoken answer "why graph over Feature-Only"** — drafted in paper, not memorized

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
- _run_quiz_init, run_quiz_sensitivity (was run_learning_curve), run_ablation_study: build_similarity_graph → build_jaccard_graph
- EvalConfig: catalog_path + jaccard_threshold fields added

**Working protocol:**
- Claude inspects and directs via targeted shell commands
- Agent executes, pastes output back
- Every decision committed to CHANGELOG.md
- No claims without results
- CHANGELOG.md is source of truth — always read first

**HANDOFF NOTE (2026-05-28):**
- Phase 5 one task remaining: stratified analysis
  Command: `python -m ml.eval.pipeline --mode stratification`
- Phase 6 blocked until Phase 5 locked
- .planning/ fully synced to CHANGELOG state
- Next session: run stratification, paste results, update paper framing, lock Phase 5, then rebuild Phase 6 clean
