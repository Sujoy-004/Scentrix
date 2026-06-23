# Scentrix Learning Roadmap

Zero → Hero in 15 Stages

```
                        ┌─────────────────────────────────────────────────┐
                        │            YOU KNOW NOTHING ABOUT SCENTRIX      │
                        └────────────────────┬────────────────────────────┘
                                             │
                                           0 │ Orientation
                                             │
                                             v
                        ┌─────────────────────────────────────────────────┐
                  ┌─────┤            COLD-START PROBLEM                   ├─────┐
                  │     │         (why this project exists)               │     │
                  │     └────────────────────┬────────────────────────────┘     │
                  │                          │                                  │
                  v                          v                                  v
     ┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────────┐
     │  1. Problem          │   │  2. Research         │   │  3. Dataset & Domain     │
     │     Understanding    │──▶│     Question         │──▶│     (fragrance, notes,    │
     │                      │   │                      │   │      accords, brands)     │
     └──────────────────────┘   └──────────────────────┘   └───────────┬──────────────┘
                                                                       │
                                                                       v
                                             ┌─────────────────────────────────────────┐
                                             │    4. Original Solution (GraphSAGE)      │
                                             │    Your first encounter with the model   │
                                             └───────────────────┬─────────────────────┘
                                                                 │
                                                                 v
                                             ┌─────────────────────────────────────────┐
                                             │    5. Evaluation Pipeline               │
                                             │    How we measured success (wrongly)    │
                                             └───────────────────┬─────────────────────┘
                                                                 │
                                                    ┌────────────┴────────────┐
                                                    │                         │
                                                    v                         v
                               ┌──────────────────────────┐   ┌────────────────────────────┐
                               │   6. Fix A                │   │   7. Fix B                  │
                               │   RR → NDCG               │   │   Circular GT → brand_accord│
                               │   (metric bug)            │   │   (ground truth fix)        │
                               └──────────────────────────┘   └─────────────┬──────────────┘
                                                                           │
                                                                           v
                                             ┌─────────────────────────────────────────┐
                                             │   8. Ground Truth Selection (GT-A-D)    │
                                             │   Why brand_accord is the canonical GT  │
                                             └───────────────────┬─────────────────────┘
                                                                 │
                                                                 v
                                             ┌─────────────────────────────────────────┐
                                             │   9. Canonical Results (HERO)           │
                                             │   Feature-Only=0.399, GS-Jaccard=0.115   │
                                             │   The corrected numbers                 │
                                             └───────────────────┬─────────────────────┘
                                                                 │
                                                                 v
                                             ┌─────────────────────────────────────────┐
                                             │  10. USER_VECTOR Discovery             │
                                             │   +41.4% NDCG from data audit          │
                                             └───────────────────┬─────────────────────┘
                                                                 │
                                                                 v
                                             ┌─────────────────────────────────────────┐
                                             │  11. Production Architecture            │
                                             │   5-state dispatcher, Docker, load test │
                                             └───────────────────┬─────────────────────┘
                                                                 │
                                                                 v
                                             ┌─────────────────────────────────────────┐
                                             │  12. Research Contributions             │
                                             │  5 contributions + limitations        │
                                             └───────────────────┬─────────────────────┘
                                                                 │
                                                                 v
                                             ┌─────────────────────────────────────────┐
                                             │  13. Defense Preparation                │
                                             │   Top 25 questions, mock defense        │
                                             └───────────────────┬─────────────────────┘
                                                                 │
                                                                 v
                                             ┌─────────────────────────────────────────┐
                                             │  14. Interview Readiness                │
                                             │  Explain fluently for 60+ minutes       │
                                             └─────────────────────────────────────────┘
```

---

# Quick-Start Paths

| Path | Duration | Stages | Goal |
|---|---|---|---|
| **BEGINNER** | 2 hours | 0, 1, 2, 9, 14 | Can explain the project in 5 minutes |
| **STANDARD** | 1 day | 0–9, 12, 14 | Can discuss all major findings and defend against common criticisms |
| **DEEP** | 3 days | 0–14 (all) | Can present, defend, and answer detailed methodology questions for 60+ minutes |

---

# Stage 0 — Orientation

**Why this stage exists:** You need the lay of the land before diving into details. This stage gives you the one-line pitch, the project structure, and the key vocabulary.

**What to study:** The project README provides the executive summary. The study guide adds depth. The presentation gives you the visual story.

**Files to read:**
- READ FIRST: `README.md`
- READ NEXT: `docs/STUDY_GUIDE.md` — Sections 1-4 (Project Overview, Problem Statement, Research Question, Why Cold Start Matters)
- READ LAST: `docs/mext_presentation.html` — all 8 slides (5 minutes to click through)

**Concepts to master:**
- Cold-start recommendation: what it is, why it is hard
- The fragrance domain: why it was chosen
- The one-line pitch: "Evaluation methodology matters more than model complexity"
- The repository structure: docs/, ml/, backend/, scripts/

**Expected outcome:** You can state what this project is about in one sentence and navigate the repository.

**Common mistakes:**
- Jumping into GraphSAGE details before understanding the cold-start problem
- Memorizing numbers (0.399, 0.115) without understanding what they mean
- Confusing the old pipeline results with the Fix-B-corrected results

**Self-check:**
1. What is the one-line pitch of this project?
2. Why does collaborative filtering fail at cold start?
3. What was wrong with the original evaluation?
4. What is the difference between Fix A and Fix B?

---

# Stage 1 — Problem Understanding

**Why this stage exists:** You cannot defend a solution until you deeply understand the problem. This stage ensures you can explain cold-start recommendation to any audience.

**What to study:** Start with the domain motivation — why fragrance? Then understand why every standard approach fails.

**Files to read:**
- READ FIRST: `README.md` — Section "Key Decisions" table, architecture overview
- READ NEXT: `docs/STUDY_GUIDE.md` — Sections 1, 2, 4 (What Is Scentrix, Problem Statement, Why Cold Start Matters)
- READ LAST: `RESPONSE.md` — "Defense Narrative Extraction" section

**Concepts to master:**
- The cold-start regime: zero ratings, zero purchases, zero clicks
- Why CF/MF produce 0.000 NDCG (no user-item matrix to factor)
- Why Popularity as a baseline scores 0.000 NDCG (global popularity does not predict individual preference)
- The three coldness levels (defined by quiz item popularity)
- Why fragrance is a "pure" cold-start domain (each purchase is independent)

**Expected outcome:** You can explain the cold-start problem to three audiences: a researcher (deep technical), a recruiter (business impact), and a non-technical interviewer (intuitive analogy).

**Common mistakes:**
- Claiming CF/MF "perform poorly" at cold start — they produce nothing (NDCG=0.000)
- Confusing cold-start with warm-start evaluation regimes
- Not being able to explain why Popularity=0.000 is realistic and not suspicious

**Self-check:**
1. In your own words, what makes cold-start recommendation hard?
2. Why does Popularity score 0.000 NDCG? Is that realistic?
3. Name three domains where cold-start matters, and one where it doesn't.
4. What makes fragrance a "pure" cold-start domain versus news or movies?


```
COLD-START REGIME:
                                                                     
    User arrives ──▶ No history ──▶ CF can't factor ──▶ 0.000 NDCG
                        │                                          
                        v                                          
               Must recommend                                      
               BEFORE learning                                     
                        │                                          
                        v                                          
    This is the problem Scentrix addresses                         
```

---

# Stage 2 — Research Question

**Why this stage exists:** The project has a specific research question that frames everything. Understanding the question helps you evaluate whether the methodology answers it.

**What to study:** The research question is the anchor. Every design decision (model choice, evaluation setup, GT selection) must be evaluated against whether it helps answer the question.

**Files to read:**
- READ FIRST: `docs/STUDY_GUIDE.md` — Section 3 (Research Question)
- READ NEXT: `docs/STUDY_GUIDE.md` — Section 26 (Research Contributions)
- READ LAST: `ARCHITECTURE-FREEZE.md` — Section "Open Research Questions"

**Concepts to master:**
- Primary question: "Does graph-based preference initialization add value over direct feature matching for cold-start fragrance recommendation?"
- Three sub-questions: evaluation integrity, graph vs features, data utilization
- The difference between the original claim (graph construction > model architecture) and the corrected claim (evaluation methodology > model complexity)
- What question is NOT being asked (e.g., "Can GraphSAGE beat collaborative filtering?" — irrelevant at cold start)

**Expected outcome:** You can state the research question precisely and explain why it matters.

**Common mistakes:**
- Answering a different question than the one being asked
- Framing the project as "we built a GraphSAGE recommender" when the contribution is methodological
- Confusing the engineering goal (build a working system) with the research question (does graph initialization add value over features?)

**Self-check:**
1. What is the primary research question?
2. What are the three sub-questions?
3. How did the research question change after Fix B?
4. What question is this project NOT trying to answer?

---

# Stage 3 — Dataset & Domain

**Why this stage exists:** The dataset determines what questions you can answer. Fragrance has unusually rich structured features — understanding this helps you discuss generalization.

**What to study:** The data pipeline, feature engineering, and why the fragrance domain was chosen over alternatives.

**Files to read:**
- READ FIRST: `docs/STUDY_GUIDE.md` — Section 5 (Dataset), Section 6 (Feature Engineering)
- READ NEXT: `docs/STUDY_GUIDE.md` — Section 7 (Graph Construction)
- READ LAST: `ml/eval/config.py` (if accessible) for feature dimension details

**Concepts to master:**
- 4,559 quality-filtered items from 22,740 raw scraped items
- 24 brands, 48 accords, ~800 unique notes
- Feature vector: 48-dim accord one-hot + 384-dim Sentence-Transformer embedding = 432 dimensions
- Why this is a "feature-rich" domain (accords, notes, brands are structured)
- The filtering pipeline: complete note profiles, valid brand, non-empty accord lists
- What would happen in a feature-sparse domain (images, audio) — this is a limitation

**Expected outcome:** You can describe the dataset, explain why fragrance was chosen, and discuss generalization boundaries.

**Common mistakes:**
- Not knowing the dataset size (4,559) when asked
- Claiming the dataset is "large" (it is medium — 4,559 items)
- Forgetting to mention quality filtering (22,740 → 4,559)
- Over-claiming generalization without mentioning the feature-rich limitation

**Self-check:**
1. How many items in the final dataset? Where did they come from?
2. What is the feature vector composed of?
3. Why might these results NOT generalize to image recommendation?
4. What is the difference between an accord and a note?

```
FEATURE VECTOR (432 dims):
┌──────────────────────────────────────────────────────────────┐
│  48 × accord one-hot    │   384 × Sentence-Transformer       │
│  (sparse — 3-5 active)  │   (dense — semantic embedding)    │
└──────────────────────────────────────────────────────────────┘
         │                              │
         v                              v
   "Which scents?"              "What does the description
   (floral, woody, citrus)       say about this fragrance?"
```

---

# Stage 4 — Original Solution (GraphSAGE)

**Why this stage exists:** You need to understand what was built before you can understand what was wrong with the evaluation.

**What to study:** The GraphSAGE architecture, the Jaccard graph, and the original pipeline that was deployed.

**Files to read:**
- READ FIRST: `docs/STUDY_GUIDE.md` — Section 8 (GraphSAGE), Section 7 (Graph Construction)
- READ NEXT: `README.md` — architecture table, key decisions
- READ LAST: `ARCHITECTURE-FREEZE.md` — system architecture description

**Concepts to master:**
- 2-layer GraphSAGE with mean aggregation, 64-dim embeddings
- Unsupervised link prediction with InfoNCE loss
- Jaccard graph: 16,244 edges at threshold 0.20, 99.2% coverage
- Threshold sweep: coverage vs quality tradeoff
- Inductive inference for cold items
- Hyperparameters selected under the old (circular) evaluation pipeline

**Expected outcome:** You can explain what GraphSAGE is, how the graph was built, and how the model was trained — all without reference to the evaluation flaws.

**Common mistakes:**
- Skipping GraphSAGE architecture details ("it's a GNN")
- Not knowing the embedding dimension (64) or layers (2)
- Confusing the Jaccard graph with the evaluation ground truth
- Claiming the model was "production-ready" under the original evaluation

**Self-check:**
1. How many layers does the GraphSAGE model have?
2. What loss function was used?
3. How many edges in the Jaccard graph? What threshold?
4. Why was threshold 0.20 chosen over 0.10 or 0.30?

```
GraphSAGE TRAINING:
                        ┌──────────┐
    Warm items ────────▶│ Jaccard  │──▶ 16,244 edges
                        │ Graph    │
                        └────┬─────┘
                             │
                             v
                        ┌──────────┐
                        │GraphSAGE │──▶ 64-dim embeddings
                        │ 2-layer  │    for ALL items
                        │ MeAN agg │    (inductive)
                        └──────────┘
                             │
                             v
    Cold items ────────────▶│ Inference ──▶ Cold embeddings
```

---

# Stage 5 — Evaluation Pipeline

**Why this stage exists:** The evaluation pipeline is where the two bugs lived. Understanding how it was supposed to work is necessary for understanding what went wrong.

**What to study:** The 6-model comparison, the leave-cold-out split, the metrics, and the original (flawed) ground truth.

**Files to read:**
- READ FIRST: `docs/STUDY_GUIDE.md` — Section 9 (Evaluation Pipeline)
- READ NEXT: `docs/STUDY_GUIDE.md` — Section 17 (Canonical Results) — just the table, not the analysis yet
- READ LAST: `CHANGELOG.md` — Phase 5 section (original locked results)

**Concepts to master:**
- Leave-cold-out split: 80% warm / 20% cold, stratified by primary accord
- 6 models: GS-Jaccard, GS-Embedding, Feature-Only, Content-Only, Popularity, Random
- Metrics: Precision@10, NDCG@10 (via ranx)
- The reproducibility command: `SCENTRIX_EVAL_GT_MODE=brand_accord python -m ml.eval.pipeline --mode pure_cold --seed 42`
- Why CF/MF were excluded (they require warm-start interactions)

**Expected outcome:** You can describe the evaluation design and explain why each model was included.

**Common mistakes:**
- Forgetting that Content-Only is an oracle baseline (uses the same Jaccard criterion as the original GT)
- Not knowing why Popularity and Random are the only honest cold-start baselines
- Confusing leave-cold-out with leave-one-out or random split
- Not being able to reproduce the results from memory

**Self-check:**
1. What is leave-cold-out evaluation?
2. Name all 6 models and explain why each one exists.
3. Why were CF and MF excluded?
4. What is the reproducibility command?

```
EVALUATION DESIGN:
                                    ┌─────────────────────┐
    Full catalog ──────────────────▶│ 80/20 stratified    │
    (4,559 items)                   │ leave-cold-out      │
                                    └──────────┬──────────┘
                                               │
                         ┌─────────────────────┼─────────────────────┐
                         │                     │                     │
                         v                     v                     v
              ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
              │ WARM (80%)       │   │ COLD (20%)       │   │ Metrics          │
              │ Used to train GS │   │ Held out entirely│   │ P@10, NDCG@10    │
              │ and build baselines│  │ for evaluation   │   │ via ranx         │
              └──────────────────┘   └──────────────────┘   └──────────────────┘
```

---

# Stage 6 — Fix A

**Why this stage exists:** This is one of the two evaluation bugs. Understanding it demonstrates methodological rigor and prevents the same mistake in future work.

**What to study:** The difference between RR@10 and NDCG@10, how the bug was implemented, and why it went undetected.

**Files to read:**
- READ FIRST: `docs/STUDY_GUIDE.md` — Section 10 (Fix A)
- READ NEXT: `docs/mext_presentation.html` — Slide 4 (Evaluation Leakage Discovery)
- READ LAST: `RESPONSE.md` — "Defense Narrative Extraction" Fix A section

**Concepts to master:**
- RR@10: 1/rank_of_first_relevant_item, capped at 10. Stops accumulating at position 1.
- NDCG@10: Accumulates graded relevance across all 10 positions with logarithmic discounting.
- Why RR@10 overestimates models that place one relevant item high
- Why the bug went undetected (relative rankings preserved, no unit test against reference implementation)
- How it was fixed (metrics.py corrected, validated against ranx)

**Expected outcome:** You can explain the difference between RR and NDCG and why the bug mattered. You can answer "how did you not notice?" without being defensive.

**Common mistakes:**
- Hand-waving the mathematical difference ("NDCG is better")
- Not knowing exactly why it went undetected (relative rankings preserved)
- Being defensive when asked "shouldn't you have caught this earlier?"
- Claiming the bug was "small" or "minor" — it inflated every reported number

**Self-check:**
1. What is the mathematical difference between RR@10 and NDCG@10?
2. Why did the bug go undetected through multiple rounds of analysis?
3. Which models were overestimated more by the bug?
4. What structural change prevents this bug recurring?

```
FIX A: RR vs NDCG

RR@10:
  If first relevant item is at rank 3: score = 1/3 = 0.333
  Items at ranks 4-10: ignored

NDCG@10:
  Rank 1: gain = rel_1 / log2(2) = rel_1
  Rank 2: gain = rel_2 / log2(3) ≈ rel_2 / 1.58
  Rank 3: gain = rel_3 / log2(4) = rel_3 / 2
  ...
  All positions matter, but higher ranks get more weight

The bug: code labeled `ndcg` but computed 1/(rank+1).
```

---

# Stage 7 — Fix B

**Why this stage exists:** This is the more significant finding and the primary methodological contribution. Understanding circular ground truth is essential for defending the project.

**What to study:** The circularity mechanism, the brand_accord replacement, and why the original GT was problematic.

**Files to read:**
- READ FIRST: `docs/STUDY_GUIDE.md` — Section 11 (Fix B)
- READ NEXT: `docs/STUDY_GUIDE.md` — Section 12-16 (Ground Truth Selection and GT-A/B/C/D)
- READ LAST: `docs/mext_presentation.html` — Slide 4 (the Fix B panel)

**Concepts to master:**
- The circularity: Jaccard similarity built the graph AND defined the ground truth (same function, same threshold)
- Why this inflates graph method scores (the model optimizes for what it is evaluated against)
- The brand_accord replacement: same brand AND shared accord
- Why brand is independent (factual attribute, not note-chemistry)
- Why accord agreement is functional (perfumer-labeled), not structural
- Effect on results: 2.7× improvement collapsed to 1.21×

**Expected outcome:** You can explain circular ground truth to a non-technical audience, describe the fix, and explain why it changes the results.

**Common mistakes:**
- Describing the circular GT as a "mistake" rather than a structural vulnerability
- Not being able to articulate why brand is independent of note chemistry
- Getting defensive ("everyone uses Jaccard GT")
- Forgetting to mention that the fix was validated across 4 GT definitions

**Self-check:**
1. What exactly was circular about the original ground truth?
2. Why does circular ground truth inflate graph method scores?
3. Why is brand_accord non-circular?
4. What was the effect on the claimed 2.7× improvement?

```
FIX B: CIRCULAR GROUND TRUTH

BEFORE:
  Graph construction:  Jaccard(notes_i, notes_j) > 0.20
  Ground truth:        Jaccard(notes_i, notes_j) > 0.20  ← SAME!
  
  Result: Model is rewarded for doing what the graph already encodes.
  The evaluation signal = the training signal.

AFTER:
  Graph construction:  Jaccard(notes_i, notes_j) > 0.20
  Ground truth:        brand_i == brand_j AND share_accord(i, j)  ← DIFFERENT!
  
  Result: Brand is independent of note chemistry.
  Accord is functional (perfumer-labeled), not structural.
  The evaluation signal ≠ the training signal.
```

---

# Stage 8 — Ground Truth Selection (GT-A/B/C/D)

**Why this stage exists:** The choice of brand_accord as the canonical GT was not arbitrary. Understanding the sensitivity analysis across four definitions demonstrates methodological thoroughness.

**What to study:** The four GT definitions, their coverage, and why brand_accord was selected.

**Files to read:**
- READ FIRST: `docs/STUDY_GUIDE.md` — Sections 13-16 (GT-A through GT-D)
- READ NEXT: `docs/STUDY_GUIDE.md` — Section 12 (Ground Truth Selection)
- READ LAST: `RESPONSE.md` — the GT sensitivity discussion in the defense Q&A

**Concepts to master:**
- GT-A (note-Jaccard >0.20): 84% coverage, circular — rejected
- GT-B (brand + accord): 31.7% coverage, non-circular — selected as canonical
- GT-C (accord-only): 67% coverage, non-circular — ranking holds (Feature-Only leads by 2.1×)
- GT-D (brand-only): ~45% coverage, non-circular but weak signal
- Why GT-B was chosen: strictest non-circular definition; ranking consistent across all non-circular variants

**Expected outcome:** You can explain why brand_accord was chosen, what the alternatives were, and why the ranking is robust across GT choices.

**Common mistakes:**
- Being unable to name all four GT definitions
- Defending brand_accord without mentioning the sensitivity analysis
- Claiming brand_accord is the "best" GT rather than the "strictest non-circular" GT
- Not knowing the coverage percentages

**Self-check:**
1. Name all four GT definitions and their coverage.
2. Why was GT-B (brand_accord) chosen over GT-C (accord-only)?
3. Does the model ranking change across GT definitions?
4. What would you say to someone who claims you cherry-picked brand_accord?

```
GROUND TRUTH SENSITIVITY:

GT-A (Jaccard) ── 84% coverage ── CIRCULAR ── Rejected
GT-B (brand+accord) ── 32% ── STRICTEST non-circular ── SELECTED
GT-C (accord-only) ── 67% ── Non-circular ── Ranking holds
GT-D (brand-only) ── 45% ── Non-circular ── Weak signal

Key result: Feature-Only leads under EVERY non-circular GT.
Ranking is robust, not dependent on any single GT choice.
```

---

# Stage 9 — Canonical Results

**Why this stage exists:** This is the hero slide. These numbers are what every audience member will remember. You must know them cold.

**What to study:** The corrected results table, the bootstrap analysis, the coldness stratification, and the narrative framing.

**Files to read:**
- READ FIRST: `docs/STUDY_GUIDE.md` — Section 17 (Canonical Results), Section 18 (Bootstrap), Section 19 (Coldness Stratification)
- READ NEXT: `docs/mext_presentation.html` — Slide 5 (Hero slide)
- READ LAST: `ml/README.md` — corrected metrics table

**Concepts to master:**
- The 6-model table from memory: Feature-Only=0.399, GS-Jaccard=0.115, GS-Embedding=0.095, Content-Only=0.047, Popularity=0.000, Random=0.001
- Bootstrap: Jaccard vs Embedding p=0.008, d=0.11 (significant, small effect)
- Bootstrap: Jaccard vs Feature-Only p=1.000, d=−0.96 (overwhelming Feature-Only lead)
- Coldness stratification: Feature-Only flat, GS-Jaccard monotonic, GS-Embedding non-monotonic
- The narrative framing: "3.47× gap — evaluation methodology > model complexity"

**Expected outcome:** You can recite the 6-model table from memory, explain the bootstrap results, and discuss the coldness stratification patterns.

**Common mistakes:**
- Forgetting the exact numbers (0.399, 0.115, 0.095)
- Stumbling on the bootstrap interpretation (p=1.000 does not mean "no difference")
- Not knowing which pattern is monotonic versus non-monotonic in stratification
- Presenting the result as "GraphSAGE failed" rather than "Feature-Only dominates; graph adds marginal structural value"

**Self-check:**
1. Recite all 6 NDCG@10 values from memory.
2. What does p=0.008 mean for the Jaccard vs Embedding comparison?
3. Why is p=1.000 for Jaccard vs Feature-Only NOT a null result?
4. Which model is non-monotonic in coldness stratification, and why does that matter?

```
CANONICAL RESULTS (Fix B, brand_accord GT):

NDCG@10
0.400 ┤
      │
0.300 ┤
      │
0.200 ┤
      │                            ████  GS-Embedding (0.095)
0.100 ┤  ████████████████████  Feature-Only (0.399)
      │  ████  GS-Jaccard (0.115)
0.000 ┤  ██  Content-Only (0.047)
      │  ██  Popularity (0.000), Random (0.001)
      └───────────────────────────────────────────
      
Feature-Only dominates by 3.47× over GraphSAGE-Jaccard.
Graph adds 1.21× over feature-circular embeddings (p=0.008).
```

---

# Stage 10 — USER_VECTOR Discovery

**Why this stage exists:** This is the secondary contribution and a compelling story about data utilization. It shows that the evaluation audit mindset produced unexpected improvements.

**What to study:** The discovery story, the mechanism, the results, and the implications.

**Files to read:**
- READ FIRST: `docs/STUDY_GUIDE.md` — Section 20 (USER_VECTOR)
- READ NEXT: `docs/mext_presentation.html` — Slide 6
- READ LAST: `README.md` — decision table row for USER_VECTOR

**Concepts to master:**
- Discovery: frontend sent 1-10 ratings for 9 months, backend used only binary liked/disliked
- The old centroid path: quiz confidence → 5 accord seeds → weighted centroid → KNN
- USER_VECTOR: Σ((rating/10) × embedding) / Σ(rating/10) → L2 normalize → KNN
- Results: +41.4% NDCG, +44.0% Recall, 10× faster, zero top-200 overlap
- Why zero overlap: centroid uses ≤5 basis points, USER_VECTOR uses 8-16 items

**Expected outcome:** You can tell the USER_VECTOR discovery story, explain the mechanism, and discuss why the improvement is real despite using the same embeddings.

**Common mistakes:**
- Framing USER_VECTOR as a "model innovation" — it is a data utilization fix
- Not knowing the exact improvement percentages (41.4%, 44.0%)
- Being unable to explain zero overlap geometrically
- Forgetting to mention that both paths use the same embeddings

**Self-check:**
1. How was USER_VECTOR discovered?
2. What was wrong with the original centroid path?
3. What are the improvement numbers (NDCG, Recall, speed)?
4. Why is there zero overlap between the two paths?

```
USER_VECTOR vs CENTROID:

CENTROID PATH:
  Quiz ratings ──▶ 5 accord seeds ──▶ weighted centroid ──▶ KNN
                     ↑ discards        ↑ collapses to       ↑ limited
                     continuous        ≤5 basis points      expressiveness
                     1-10 ratings      in 64-dim space

USER_VECTOR:
  Quiz ratings ──▶ rating-weighted mean ──▶ L2 normalize ──▶ KNN
                     ↑ uses ALL           ↑ preserves       ↑ full 64-dim
                     ratings 1-10         rating signal     expressiveness

Result: +41.4% NDCG, 10× faster, zero top-200 overlap.
```

---

# Stage 11 — Production Architecture

**Why this stage exists:** The research findings were deployed as a real system. This demonstrates engineering competence and production thinking.

**What to study:** The 5-state dispatcher, the Docker stack, the quiz flow, and the load testing results.

**Files to read:**
- READ FIRST: `docs/STUDY_GUIDE.md` — Sections 21-24 (Architecture through Production Stack)
- READ NEXT: `ARCHITECTURE-FREEZE.md` — full architecture description
- READ LAST: `backend/tests/load/README.md` — load test setup

**Concepts to master:**
- 5 states: Anonymous (Popularity), Quiz (USER_VECTOR), Cold (Hybrid β-blend), Warm (Feature), Mature (Feature + Diversity)
- Graceful degradation: every state has a fallback chain
- Stack: PostgreSQL 15, Neo4j 5, Redis 7, FastAPI, Next.js 16
- Load testing: 20 users, 5-min ramp, all 8 criteria PASS
- Quiz flow: 8-16 items, 1-10 slider, adaptive selection by accord diversity

**Expected outcome:** You can describe the production architecture and explain how research findings translate to a deployed system.

**Common mistakes:**
- Spending too much time on architecture in a research-focused interview
- Not knowing the 5 states or their strategies
- Forgetting that the ML pipeline is offline (independent of the live stack)
- Not being able to explain graceful degradation

**Self-check:**
1. What are the 5 states and what strategy does each use?
2. What happens if a strategy produces zero candidates?
3. What is the role of each Docker container?
4. How was the system load-tested and what were the results?

```
5-STATE DISPATCHER:

                    ┌────────────────┐
                    │  USER ARRIVES  │
                    └────────┬───────┘
                             │
                             v
              ┌────────────────────────┐
              │ State 0: No session    │──▶ Popularity ──▶ Random (fallback)
              └───────────┬────────────┘
                          │ Quiz taken
                          v
              ┌────────────────────────┐
              │ State 1: Quiz done     │──▶ USER_VECTOR ──▶ Feature ──▶ Pop
              └───────────┬────────────┘
                          │ 1-2 purchases
                          v
              ┌────────────────────────┐
              │ State 2: Cold          │──▶ Hybrid β-blend ──▶ Feature ──▶ Pop
              └───────────┬────────────┘
                          │ 3+ purchases
                          v
              ┌────────────────────────┐
              │ State 3: Warm          │──▶ Feature-Only ──▶ Popularity
              └───────────┬────────────┘
                          │ 10+ purchases, 3+ brands
                          v
              ┌────────────────────────┐
              │ State 4: Mature        │──▶ Feature + Diversity
              └────────────────────────┘
```

---

# Stage 12 — Research Contributions

**Why this stage exists:** You need to be able to articulate what this project contributes to the field. This is the most important section for the MEXT interview.

**What to study:** The five contributions, their ordering, and the limitations.

**Files to read:**
- READ FIRST: `docs/STUDY_GUIDE.md` — Section 26 (Research Contributions), Section 27 (Limitations), Section 28 (Future Work)
- READ NEXT: `docs/mext_presentation.html` — Slide 7
- READ LAST: `RESPONSE.md` — the 5-minute presentation structure slide 7

**Concepts to master:**
1. Evaluation leakage discovery (primary, methodological)
2. Fix A — metric correction (RR→NDCG)
3. Fix B — non-circular GT (brand+accord)
4. USER_VECTOR discovery (data utilization)
5. 5-state architecture (supporting evidence)
- The 6 limitations and how to discuss them without being defensive

**Expected outcome:** You can enumerate the five contributions, explain why the primary one is methodological, and discuss limitations honestly.

**Common mistakes:**
- Ordering contributions wrong (architecture should NOT be primary)
- Presenting USER_VECTOR as a model innovation
- Being defensive about limitations
- Not distinguishing the primary contribution (methodological) from supporting ones (architectural)

**Self-check:**
1. What are the five contributions in order?
2. Why is the primary contribution methodological rather than architectural?
3. Name all six limitations.
4. How would you respond to "this is just a null result"?

---

# Stage 13 — Defense Preparation

**Why this stage exists:** You will be challenged. This stage prepares you for the hard questions.

**What to study:** The top questions by category, the gold-standard answers, and the recovery strategies.

**Files to read:**
- READ FIRST: `RESPONSE.md` — "Defense Q&A Preparation" (65 questions)
- READ NEXT: `RESPONSE.md` — "Mock Defense Simulation" (15-question simulation)
- READ LAST: `docs/STUDY_GUIDE.md` — Sections 30 (Common Criticisms), 31 (Interview Answers)

**Concepts to master:**
- The five most dangerous questions: "Why fund a failed project?" "Your GT is also constructed" "68.3% of items irrelevant" "How do you know there are no more bugs?" "One dataset is not a discovery"
- The five recovery strategies: "I don't know", "Circular argument", "Unfamiliar literature", "Accused of p-hacking", "Null result accusation"
- The audience-specific questions: MEXT panel (methodology), researchers (statistics), recruiters (architecture)

**Expected outcome:** You can handle the 20 most likely questions without stumbling, and you know the recovery strategy if you get stuck.

**Common mistakes:**
- Memorizing answers without understanding the principles
- Being defensive when challenged
- Not knowing which questions are most likely from which audience
- Claiming the evaluation is now "correct" (claim transparency, not infallibility)

**Self-check:**
1. What are the five most dangerous questions and their ideal answers?
2. What is the recovery strategy for the "infinite regress" critique?
3. How would a MEXT panel question differ from a recruiter question?
4. What is the one-sentence answer to "Why should we fund this?"

---

# Stage 14 — Interview Readiness

**Why this stage exists:** All the knowledge is useless if you cannot deliver it fluently. This stage focuses on oral delivery and adaptability.

**What to study:** The four time-limited versions, the audience adaptations, and the final practice protocol.

**Files to read:**
- READ FIRST: `docs/STUDY_GUIDE.md` — Sections 34-37 (1-min through 60-min summaries)
- READ NEXT: `docs/STUDY_GUIDE.md` — Sections 32 (MEXT), 33 (Recruiter)
- READ LAST: Run through `docs/mext_presentation.html` aloud with a timer

**Concepts to master:**
- The 1-minute version: one breath, one pitch
- The 5-minute version: 8 slides, narrative arc, hero slide
- The 15-minute version: deep dive with all major results
- The 60-minute version: full journey with methodology and defense
- Audience adaptation: what to emphasize or de-emphasize for each audience type

**Expected outcome:** You can explain Scentrix fluently for 60+ minutes, adapting to any audience and handling interruptions gracefully.

**Common mistakes:**
- Using the same version for all audiences
- Going over time (practice with a timer)
- Reading from notes rather than speaking naturally
- Not knowing which sections to skip if time runs short

**Self-check:**
1. Deliver the 1-minute version without looking at any document.
2. Deliver the 5-minute version with only the presentation as a visual aid.
3. For a MEXT panel, which three findings do you emphasize?
4. For a recruiter, which three findings do you emphasize?

---

# How to Explain Scentrix Fluently for 60 Minutes

## 1-Minute Version

"We built a GraphSAGE recommendation system for cold-start fragrance discovery. Before freezing, we audited our evaluation pipeline and found two hidden flaws: our NDCG was actually RR@10, and our ground truth was circular with our graph construction. After correcting both, a simple feature-based method outperformed our graph neural network by 3.47×. The primary contribution is not a better model — it is the demonstration that evaluation methodology matters more than model complexity, and a replicable methodology for detecting evaluation leakage in graph-based cold-start research."

**Delivery notes:** One breath. No jargon. End on the methodological contribution.

## 5-Minute Version

(Matches the 8-slide presentation at `docs/mext_presentation.html`)

| Time | Section | Key line |
|---|---|---|
| 0:00-0:30 | Cold-start problem | CF and MF produce 0.000 NDCG at cold start |
| 0:30-1:00 | Proposed approach | GraphSAGE on Jaccard graph, USER_VECTOR path |
| 1:00-1:20 | Evaluation design | 6 models, leave-cold-out, ranx metrics |
| 1:20-2:20 | Evaluation leakage | NDCG was RR@10; GT was circular; 2.7× was artifact |
| 2:20-3:20 | Canonical results (hero) | Feature-Only=0.399 leads 3.47× |
| 3:20-3:55 | USER_VECTOR | +41.4% NDCG, data audit discovery |
| 3:55-4:20 | Research contributions | 5 contributions, primary is methodological |
| 4:20-5:00 | Final takeaway | Evaluation methodology > model complexity |

**Delivery notes:** Spend 60% of time on slides 4-6 (the audit and its consequences). Slide 5 (hero) must land. End on the quotable statement.

## 15-Minute Version

| Segment | Time | What to cover |
|---|---|---|
| 1. Problem and setup | 2 min | Cold-start problem, fragrance domain, dataset stats, why CF/MF fail |
| 2. Approach | 2 min | GraphSAGE architecture, Jaccard graph construction, threshold sweep |
| 3. The audit | 4 min | Fix A (RR→NDCG), Fix B (circular GT), the 2.7× artifact, GT sensitivity |
| 4. Corrected results | 3 min | 6-model table, bootstrap, coldness stratification, the hero numbers |
| 5. USER_VECTOR | 2 min | Discovery story, mechanism, results, zero overlap |
| 6. Architecture and wrap | 2 min | 5-state dispatcher, limitations, future work, the closing statement |

**Delivery notes:** The audit segment (4 min) is the longest. This is the story's peak. The corrected results (3 min) must include the full table plus bootstrap interpretation.

## 60-Minute Version

| Part | Time | What to cover |
|---|---|---|
| 1. Domain and motivation | 5 min | Cold-start problem, why fragrance, industry relevance, academic gap |
| 2. Data and features | 5 min | Scraping pipeline, filtering, 432-dim feature vector, why it matters |
| 3. Graph construction | 5 min | Jaccard threshold sweep, degree analysis, coverage vs quality tradeoff |
| 4. GraphSAGE architecture | 5 min | 2-layer, 64-dim, InfoNCE loss, inductive inference, hyperparameters |
| 5. Original evaluation | 5 min | Leave-cold-out, 6 models, original results (circular) |
| 6. Fix A — metric bug | 5 min | RR vs NDCG, bug mechanism, why undetected, fix validation |
| 7. Fix B — circular GT | 10 min | The circularity mechanism, brand_accord replacement, 4 GT definitions |
| 8. Corrected results | 10 min | Full table, bootstrap interpretation, coldness stratification patterns |
| 9. USER_VECTOR | 5 min | Discovery, mechanism, results, implications |
| 10. Production architecture | 5 min | 5-state dispatcher, Docker stack, load test, graceful degradation |
| 11. Contributions and limitations | 5 min | 5 contributions, 6 limitations, honest self-assessment |
| 12. Defense and Q&A | 5 min | Hardest questions, recovery strategies, the one-sentence takeaway |

**Delivery notes:** Keep checking the clock — the 10-minute segments (Fix B, corrected results) are the heart of the talk. If you run short on time, trim Parts 1-4 (the setup) rather than Parts 6-9 (the audit and results).

---

# READ FIRST / READ NEXT / READ LAST Quick Reference

| Stage | READ FIRST | READ NEXT | READ LAST |
|---|---|---|---|
| 0 Orientation | `README.md` | `docs/STUDY_GUIDE.md` §1-4 | `docs/mext_presentation.html` |
| 1 Problem | `README.md` (decisions table) | `docs/STUDY_GUIDE.md` §1-4 | `RESPONSE.md` (defense narrative) |
| 2 Research Question | `docs/STUDY_GUIDE.md` §3 | `docs/STUDY_GUIDE.md` §26 | `ARCHITECTURE-FREEZE.md` (open questions) |
| 3 Dataset | `docs/STUDY_GUIDE.md` §5-6 | `docs/STUDY_GUIDE.md` §7 | `ml/eval/config.py` |
| 4 GraphSAGE | `docs/STUDY_GUIDE.md` §8, §7 | `README.md` (architecture) | `ARCHITECTURE-FREEZE.md` |
| 5 Evaluation | `docs/STUDY_GUIDE.md` §9 | `docs/STUDY_GUIDE.md` §17 (table) | `CHANGELOG.md` Phase 5 |
| 6 Fix A | `docs/STUDY_GUIDE.md` §10 | `docs/mext_presentation.html` slide 4 | `RESPONSE.md` defense narrative |
| 7 Fix B | `docs/STUDY_GUIDE.md` §11 | `docs/STUDY_GUIDE.md` §12-16 | `docs/mext_presentation.html` slide 4 |
| 8 GT Selection | `docs/STUDY_GUIDE.md` §13-16 | `docs/STUDY_GUIDE.md` §12 | `RESPONSE.md` GT sensitivity |
| 9 Canonical Results | `docs/STUDY_GUIDE.md` §17-19 | `docs/mext_presentation.html` slide 5 | `ml/README.md` corrected table |
| 10 USER_VECTOR | `docs/STUDY_GUIDE.md` §20 | `docs/mext_presentation.html` slide 6 | `README.md` decision table |
| 11 Architecture | `docs/STUDY_GUIDE.md` §21-24 | `ARCHITECTURE-FREEZE.md` | `backend/tests/load/README.md` |
| 12 Contributions | `docs/STUDY_GUIDE.md` §26-28 | `docs/mext_presentation.html` slide 7 | `RESPONSE.md` (5-min structure) |
| 13 Defense | `RESPONSE.md` Q&A (65 questions) | `RESPONSE.md` mock defense (15) | `docs/STUDY_GUIDE.md` §30-31 |
| 14 Readiness | `docs/STUDY_GUIDE.md` §34-37 | `docs/STUDY_GUIDE.md` §32-33 | Practice with `mext_presentation.html` |

# Estimated Time To Master

| Path | Duration | Stages | Outcome |
|---|---|---|---|
| BEGINNER | 2 hours | 0, 1, 2, 9, 14 | Can deliver 5-minute presentation |
| STANDARD | 1 day (8 hours) | 0-9, 12, 14 | Can discuss all results, handle common criticisms |
| DEEP | 3 days (24 hours) | 0-14 (all) | Can present, defend, and answer detailed questions for 60+ minutes |

**Breakdown (DEEP path):**
- Day 1: Stages 0-5 (orientation through evaluation pipeline) — ~8 hours
- Day 2: Stages 6-10 (Fix A through USER_VECTOR) — ~8 hours
- Day 3: Stages 11-14 (architecture through readiness) + practice — ~8 hours

**Self-assessment:** After completing each stage, run through the self-check questions. If you cannot answer all of them, repeat the stage before proceeding.
