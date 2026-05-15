# Domain Pitfalls: Cold-Start Recommendation Systems

**Domain:** Graph-based cold-start recommendation (fragrance discovery via quiz → GraphSAGE → Neo4j)
**Researched:** 2026-05-15
**Overall confidence:** HIGH (verified across multiple peer-reviewed papers, arXiv surveys, and production post-mortems)

---

## Critical Pitfalls

Mistakes that cause invalid experiments, wasted effort, or fundamentally broken recommendations.

### Pitfall 1: Treating "Cold-Start" as a Single Binary State

**What goes wrong:** Researchers define a single interaction threshold (e.g., <5 interactions = "cold") and treat all cold users/items as identical. This obscures the fact that cold-start spans a continuum: zero-interaction (strict cold), 1-5 interactions (cold), 5-20 interactions (lukewarm), etc. Different strategies are optimal at different points along this continuum.

**Why it happens:** Convenience — it's simpler to report a single "cold-start NDCG" number. The threshold is often set via "common sense" heuristics (5-core filtering, arbitrary cutoffs) without empirical justification.

**Consequences:**
- A model that performs well at 15 interactions may be terrible at 0 interactions, but this is invisible in aggregate cold metrics
- Comparison across papers is impossible when cold definitions differ
- You may optimize for the wrong regime — e.g., tuning for users with 5 interactions when your quiz actually produces users with 0

**Prevention:**
- Report metrics at **multiple coldness levels**: 0, 1-3, 4-10, 11-20 interactions (or for Scentrix: by quiz confidence score bucket)
- Use successive evaluation: incrementally add holdout interactions and measure performance at each step
- Define your cold-start threshold empirically using the method from Gusak et al. (2025, arXiv 2508.07856) — find the inflection point where performance plateaus

**Detection:** Your evaluation code defines a single `is_cold` boolean. If you don't bucket cold users by degree/interaction count, you're at risk.

**Phase mapping:** EVAL phases (EVAL-01, EVAL-02, EVAL-03) — this is where the bucketing strategy must be implemented. Without it, all reported numbers are suspect.

**Sources:**
- Gusak et al. "Identifying Cold-Start Thresholds in Recommender Systems" (arXiv 2508.07856) — HIGH confidence
- EngineersOfAI "The Cold Start Problem" — MEDIUM confidence (blog post, but well-sourced)

---

### Pitfall 2: Aggregate NDCG@k That Masks Cold-Start Degradation

**What goes wrong:** Reporting a single NDCG@10 (or Precision@10) across all users hides cold-start problems because experienced users dominate the average. A model can have terrible cold-start performance and still show acceptable aggregate NDCG if warm users are numerous enough.

**Why it happens:** Standard evaluation scripts compute one metric over the entire test set. It's the default behavior, and it requires extra code to stratify.

**Consequences:**
- A cold-start model that's barely better than random can appear competitive if the test set is mostly warm users
- Degradation goes undetected until it's severe enough to drag down the aggregate — by then, experiment cycles have been wasted
- You may conclude your GraphSAGE model "works" when it only works for warm nodes

**Prevention:**
- **Always** evaluate and report NDCG@k / Precision@k stratified by user interaction count (or quiz confidence score in Scentrix's case)
- For Scentrix specifically: bucket test users by quiz confidence score ranges (e.g., 0-2, 3-5, 6-8, 9-10)
- Track cold-start metrics as a separate dashboard, not a footnote in aggregate results
- Set explicit improvement targets for each coldness bucket (e.g., "NDCG@10 ≥ 0.15 for strict cold users")

**Detection:** Your eval harness outputs a single float per metric. If you don't see "NDCG@10 (cold=0), NDCG@10 (cold=1-3), ..." in your output, you're falling into this trap.

**Phase mapping:** EVAL-01 evaluation harness design. Must bake in stratification from day one.

**Sources:**
- EngineersOfAI "The Cold Start Problem" — MEDIUM confidence (practitioner experience)
- Kumo.ai "Handling Cold-Start Nodes in Production" — MEDIUM confidence
- Multiple recsys papers (confirmed pattern: reporting aggregate-only metrics is a known weakness)

---

### Pitfall 3: Data Leakage Through Temporal & Structural Contamination

**What goes wrong:** The evaluation leaks information from the future or from test nodes into training. In graph-based recommenders, this happens in several insidious ways:

1. **Random train/test split on time-dependent data:** Fragrance popularity shifts seasonally. A random split leaks future popularity signals into training.
2. **Leave-one-out last-interaction split:** The standard "train on history, test on last interaction" creates temporal overlap — different users' "last" events happen at different times, so training can see events that occur after some test events.
3. **Including test edges in the graph during message passing:** When computing GNN representations for test nodes, if the graph contains edges from the test period, the GNN "cheats" by seeing the very edges it should predict.
4. **Negative sampling that makes the task artificially easy:** Randomly sampled negative items are almost always irrelevant to the user, so even a poor model can distinguish them. This inflates NDCG by 10-20% compared to ranking against all items.

**Why it happens:** Standard evaluation scripts from papers often use these flawed methods (leave-one-out, random split, 100 sampled negatives). Reproducing "what the paper did" propagates the flaw.

**Consequences:**
- Reported metrics may be 5-15% higher than real-world performance (Kumo.ai, temporal splits guide)
- A method that looks state-of-the-art under sampled evaluation may be worse than Popularity when ranking all items (proven in arXiv 2209.04185: GraphSAGE appeared to beat IDCF on I-NDCG but was actually worse on full NDCG@20)
- Invalid conclusions waste months of research effort

**Prevention:**
- **Use temporal splits:** Train on data before cutoff date, test on data after. For Scentrix, this means ordering quiz sessions by timestamp and splitting accordingly.
- **Rank ALL items (or use a principled candidate set):** Avoid sampled negative evaluation. If you must sample (e.g., computational constraints), use a hard negative sampling strategy (KG-aware, popularity-aware, or heuristic-based) — never uniform random.
- **Exclude test edges from the message-passing graph:** When computing test node embeddings, only use edges from the training period.
- **Validate on time period strictly between train and test:** Don't use test performance for hyperparameter tuning.

**Detection:** Your eval script uses `random.sample` for negative items, `train_test_split(random_state=...)` without time ordering, or leave-one-out for sequential data.

**Phase mapping:** EVAL-01 (evaluation harness design) and DATA-01/DATA-02 (data preprocessing must preserve timestamps). Fixing leakage retroactively requires re-running all experiments — get it right in the harness.

**Sources:**
- Kumo.ai "Temporal Splits: Splitting Train/Test by Time" — HIGH confidence (recommended practice)
- arXiv 2209.04185 "On the Pitfalls of NDCG Evaluation" — HIGH confidence (proves I-NDCG flaw)
- arXiv 2307.14951 "Common Pitfalls in Recommendation System Evaluation" — HIGH confidence
- arXiv 2306.10453 "Evaluating GNNs for Link Prediction: Current Pitfalls" — HIGH confidence (easy negatives problem)
- Kapoor & Narayanan (2023) on information leakage in ML — HIGH confidence

---

### Pitfall 4: GNN Cold-Start → Node Embedding Collapse

**What goes wrong:** Graph Neural Networks (including GraphSAGE) require neighborhood information to compute node embeddings. A cold-start user/item has NO edges in the graph (zero interactions). The GNN therefore has nothing to aggregate, and the resulting embedding is degenerate — essentially just a function of the node's own features (which may not even exist).

**Why it happens:** It's a fundamental architectural constraint: GNNs are message-passing by design. Researchers port GraphSAGE from node classification (where it was designed) to recommendation without adapting it for the zero-neighbor case.

**Consequences:**
- Cold-start item embeddings collapse to near-zero vectors or random noise
- The model degrades to an MLP on node features for cold nodes (often a bad MLP because features weren't designed for this)
- NDCG@k for strict-cold users is essentially random, but this is hidden by aggregate metrics (see Pitfall #2)
- The GNN performs dramatically worse than even Popularity for true cold-start cases

**Prevention:**
- **Verify GraphSAGE is in inductive mode:** Scentrix code (`ml/models/graph_sage.py`) must use `SAGEConv` (which learns a function of features + neighborhood), not transductive embedding lookup. Test that inference works for nodes unseen during training.
- **Implement feature-only fallback:** For nodes with degree 0, bypass GNN aggregation entirely and use a learned MLP on node/quiz features as the embedding.
- **Train with edge dropout:** Randomly remove ~30% of edges during training so the model learns to produce useful embeddings even when neighborhood information is incomplete. This builds cold-start robustness.
- **Consider Cold Brew's teacher-student approach:** Distill knowledge from a GNN teacher into a student that can handle isolated nodes (Amazon Research, Cold Brew framework at openreview.net/pdf?id=1ugNpm7W6E).
- **Use NodeDup augmentation:** Duplicate low-degree nodes in training to give them more representation in the loss function (arXiv 2402.09711 shows 38% improvement on isolated nodes).

**Detection:** Run inference on a dummy user with no edges. If the embedding is near-constant, all-zero, or identical for different cold users, the GNN has collapsed.

**Phase mapping:** EVAL-03 (train/fine-tune GraphSAGE). Must include a unit test that isolates cold-start node behavior. If the GNN collapses, the entire research hypothesis is undermined.

**Sources:**
- Kumo.ai "Handling Cold-Start Nodes in Production" — HIGH confidence
- Amazon Research "Cold Brew" (openreview.net/pdf?id=1ugNpm7W6E) — HIGH confidence
- arXiv 2402.09711 "Node Duplication Improves Cold-start Link Prediction" — HIGH confidence
- arXiv 2012.07064 "Pre-training GNNs for Cold-Start Recommendation" — HIGH confidence (identifies cold neighbor contamination)
- arXiv 2209.12215 "GPatch" — HIGH confidence (describes GNN architectural limitations for cold-start)

---

### Pitfall 5: Popularity Bias Feedback Loop

**What goes wrong:** For cold-start users with no signal, the natural fallback is popular items. These get shown, get clicks, get more popular. Meanwhile, genuinely good niche fragrances never get discovered because cold users — the only ones who might discover them — are served popular items. This creates a self-reinforcing "rich-get-richer" cycle.

For Scentrix's fragrance domain this is **especially dangerous** because:
- The research hypothesis is that graph-based preference initialization beats popularity
- But if the evaluation doesn't control for popularity, the baseline may outperform GraphSAGE not because popularity is better, but because the eval setup favors popular items
- Niche fragrances ARE the long tail — if your system only recommends popular scents, it fails its core value proposition

**Why it happens:** It's the path of least resistance. Popularity is a strong signal, readily available, and "works" in the short-term metrics sense. Researchers may not notice because aggregate NDCG can be driven largely by popular-item recommendations (users do click popular items sometimes).

**Consequences:**
- Your GraphSAGE model may actually learn to be a popularity proxy rather than learning preferences
- Cold-start evaluation overestimates real performance because popular items in the test set also happen to be the same popular items the model predicts
- The research paper claim "our model beats popularity baseline" may be false — the model IS a popularity baseline
- Demo fails because users get recommendations they've already seen elsewhere

**Prevention:**
- **Track popularity exposure as a metric:** What % of recommended items are in the top 10% most popular? In the bottom 50%? Set targets.
- **Report long-tail coverage:** What fraction of all catalog items ever appear in recommendations?
- **Debias evaluation:** Use popularity-stratified NDCG (compute metrics separately for popular, mid, and long-tail items)
- **Exclude popular items from test set:** When measuring cold-start performance, remove items in the top X% popularity from the ground truth
- **Inherited bias check:** If your cold-start model is trained to mimic a warm CF model (e.g., via distillation), test whether the cold model inherits the warm model's popularity bias (arXiv 2510.11402 proves this happens and is actually WORSE for cold models)

**Detection:** Compare the popularity distribution of recommended items vs. ground truth items. If your model recommends items with significantly higher average popularity than the ground truth, popularity bias is present.

**Phase mapping:** EVAL-03 (training/evaluation). Must include coverage and diversity metrics alongside accuracy metrics. Also relevant to the research paper claim — if you can't show your model recommends non-popular items, the claim of "graph-based preference initialization" is hollow.

**Sources:**
- arXiv 2510.11402 "On Inherited Popularity Bias in Cold-Start Item Recommendation" — HIGH confidence (proves cold models inherit AND amplify popularity bias)
- System Overflow "Cold Start Failure Modes" — MEDIUM confidence
- arXiv 2308.01118 "A Survey on Popularity Bias in Recommender Systems" — HIGH confidence
- Journal of Intelligent Information Systems (2026) "Dynamic feedback loops in recommender systems" — HIGH confidence

---

## Moderate Pitfalls

### Pitfall 6: Cold-Start Neighbor Contamination During Graph Convolution

**What goes wrong:** When computing the embedding for a target user, GraphSAGE aggregates information from their neighbors. If those neighbors are THEMSELVES cold-start users (with sparse, unreliable embeddings), their inaccurate representations propagate up to the target. The GNN doesn't distinguish between "this neighbor's embedding is reliable" and "this neighbor's embedding is noise."

**Why it happens:** Standard GraphSAGE uses mean/max/LSTM aggregation over all sampled neighbors equally. It has no mechanism to weight neighbors by their own degree/reliability.

**Consequences:**
- Error compounds: a cold user connected to cold neighbors gets an even worse embedding than a cold user connected to warm neighbors
- The model's performance is non-uniform in ways that correlate with graph density, not user preferences
- Hard to debug because errors propagate through multiple GNN layers

**Prevention:**
- **Implement adaptive neighbor sampling:** Instead of uniform random sampling (GraphSAGE default), sample neighbors with probability proportional to their degree. This over-selects reliable (warm) neighbors.
- **Use attention mechanisms (GATConv):** Replace mean aggregation with attention-weighted aggregation. The attention weights can learn to down-weight unreliable cold neighbors.
- **Meta aggregator:** Incorporate a meta-learning component that explicitly handles cold-start neighbors (arXiv 2012.07064 shows 0.3-6.5% NDCG improvement).
- **Verify Scentrix's GraphSAGE code:** Check `ml/models/graph_sage.py` for its neighbor sampling strategy. If it uses uniform random sampling, this pitfall applies.

**Phase mapping:** EVAL-03 (model training), ARCH phase (architecture review of existing GraphSAGE code). May require model architecture changes.

**Sources:**
- arXiv 2012.07064 "Pre-training GNNs for Cold-Start Recommendation" — HIGH confidence
- arXiv 2209.12215 "GPatch" — HIGH confidence

---

### Pitfall 7: Sparse Signal Overreaction

**What goes wrong:** With very few interactions (e.g., 2-3 quiz responses), a 100% positive response rate for a fragrance doesn't mean it's a perfect match — it means there's insufficient data. Models that treat these signals as equally reliable as signals from users with 50 interactions will overreact to noise.

**Why it happens:** Maximum likelihood estimation treats each data point equally. Without regularization, the model has no mechanism to express lower confidence for sparse observations.

**Consequences:**
- A fragrance that happened to get 3 positive quiz responses (out of 3 seen) gets ranked highest, despite being seen by almost no one
- When shown to the next 10 users, it fails badly, but the damage to user trust is done
- For Scentrix: the adaptive quiz with confidence scoring is designed to address this, but if the confidence score isn't actually used in the recommendation pipeline, the model will overreact to sparse quiz signals

**Prevention:**
- **Use the quiz confidence score as a Bayesian prior:** Smooth predictions using `smoothed_score = (positive_responses + alpha) / (total_responses + alpha + beta)` where alpha/beta encode prior belief about the item
- **Don't treat quiz responses as equal to purchase/rating interactions:** Quiz responses are weaker signals. Down-weight them in the loss function or use a separate head with higher regularization
- **Require minimum interactions before trusting:** Don't surface items with < N quiz responses in top-k unless their confidence-based score exceeds a threshold
- **Verify the confidence score is actually wired through:** Check `backend/app/routers/quiz.py` and the GraphSAGE inference pipeline to ensure confidence scores reach the model

**Detection:** An item with very few interactions but a perfect score appears anomalously high in recommendations. Investigate: is this a real match or noise?

**Phase mapping:** PIPE-03 (connect quiz → GraphSAGE → recommendation). The confidence score bridge is critical here.

**Sources:**
- System Overflow "Cold Start Failure Modes" — MEDIUM confidence
- Bayesian recommendation literature — HIGH confidence (well-established principle)

---

### Pitfall 8: Hybrid Model Degradation — Cold-Start Training Hurts Warm Performance

**What goes wrong:** Cold-start recommenders often train a single model on a mix of cold and warm users. The model must learn weights that work for both vacant embeddings (cold) and trained embeddings (warm). This dual-input design forces compromises that degrade warm-user recommendation quality.

**Why it happens:** The training objective averages over all training examples. Cold-user loss (large, because cold predictions are bad) dominates and pulls the model away from the warm-user optimum.

**Consequences:**
- Your product becomes worse for existing users to accommodate new users
- The research paper claim of "improving cold-start without harming warm" must be VERIFIED, not assumed
- If the model degrades warm performance, the entire approach may be impractical for real deployment
- Scentrix doesn't have "warm users" yet, but this matters for the research claim credibility

**Prevention:**
- **Evaluate warm performance separately:** Always report metrics on warm users/items as a distinct category
- **Use separate model components for cold and warm:** Architectures like GPatch/GNP use a "patching network" dedicated to cold-start that doesn't touch the warm model's weights
- **Check for warm degradation:** Train your GraphSAGE in two configurations — (1) with cold users, (2) without cold users — and compare warm-user performance
- **If warm performance drops >5%, the hybrid approach is failing:** Document this honestly rather than hiding it

**Phase mapping:** EVAL-03 (training). Must include this comparison.

**Sources:**
- arXiv 2209.12215 "GPatch" — HIGH confidence (identifies and solves this)
- arXiv 2410.14241 "Graph Neural Patching for Cold-Start Recommendations" — HIGH confidence

---

### Pitfall 9: Over-Indexing on Quiz Quality at the Expense of User Abandonment

**What goes wrong:** The adaptive confidence-scored quiz is Scentrix's differentiator. But if the quiz asks too many questions to achieve high confidence, users abandon before completion. The users who complete the quiz may be systematically different from those who abandon (survivorship bias), so the training signal only represents a self-selected subset.

**Why it happens:** Engineers optimize quiz confidence thresholds without tracking completion rates. The quiz appears to work great — for the 40% of users who finish it.

**Consequences:**
- The recommendation model is trained and evaluated only on "completers," who may be more patient, more interested in fragrances, or more tech-savvy
- Real-world performance for the "typical user" (who abandons after 3 questions) is unknown
- MEXT demo may show impressive results for cherry-picked users while failing for the broader audience

**Prevention:**
- **Track quiz completion rate as a first-class metric:** It's as important as NDCG for the product story
- **Measure cold-start performance at every exit point:** For users who answer 1, 2, 3, 5, 10 questions, how good are the recommendations?
- **A/B test quiz length:** Shorter quiz with lower confidence but higher completion may produce better overall outcomes
- **Have a fallback for incomplete quizzes:** If user abandons after 3 questions, use hybrid search (already implemented in `backend/app/services/hybrid_search.py`) with the partial signal

**Phase mapping:** PIPE-03 and the upcoming quiz optimization work. Kumo.ai's insight: "Aggressive onboarding collects great signal but loses users. Track completion rates."

**Sources:**
- System Overflow "Cold Start Failure Modes" — MEDIUM confidence
- BBC R&D "Bootstrapped Personalised Popularity for Cold Start" — MEDIUM confidence (notes the completion trade-off)
- General product onboarding wisdom — HIGH confidence (well-established UX principle)

---

### Pitfall 10: Not Measuring Beyond-Accuracy Metrics

**What goes wrong:** Evaluation focuses exclusively on accuracy metrics (NDCG, Precision, Recall) and ignores diversity, novelty, serendipity, and coverage. A model that achieves high NDCG by recommending only popular items may look great on paper but fail the product's core mission of "discovering niche scents."

**Why it happens:** Accuracy metrics are standard, easy to compute, and what papers report. Diversity and serendipity metrics require additional effort and may not be expected by reviewers.

**Consequences:**
- Scentrix recommends only well-known fragrances — indistinguishable from a popularity list
- The "graph-based preference initialization" claim is undermined because the model's success is driven by popularity, not graph structure
- MEXT interviewers may ask: "Your NDCG is good, but are you actually recommending niche fragrances?"

**Prevention:**
- **Report catalog coverage@k:** What fraction of the fragrance catalog ever appears in top-k recommendations?
- **Report novelty (expected popularity complement):** How "long-tail" are the recommendations?
- **Report diversity (intra-list dissimilarity):** Are recommendations all similar or spanning different scent families?
- **Visualize recommendation distribution:** Histogram of recommended fragrance popularity vs. ground truth popularity
- **Set explicit targets:** "Coverage@10 ≥ 0.15" or "At least 30% of recommendations are non-blockbuster scents"

**Phase mapping:** EVAL-01 (evaluation harness). Add these metrics alongside NDCG/Precision. EVAL-02 (baselines) should also report them for comparison.

**Sources:**
- IEEE Trust-CF evaluation paper — HIGH confidence (uses novelty, diversity, coverage alongside NDCG)
- BBC R&D B2P framework — MEDIUM confidence (accuracy-diversity tradeoff is central)
- Carnovalini et al. (MDPI 2025) "Popularity Bias in Recommender Systems" — HIGH confidence

---

## Minor Pitfalls

### Pitfall 11: Unvalidated Dataset Construction

**What goes wrong:** Fragrance preprocessing ignores important structures — e.g., mapping notes to graph edges loses "accord" relationships (top/middle/base), or scent families are treated as flat categories when they're hierarchical.

**Why it happens:** The dataset (`ml/data/scentrix_master.json`) looks reasonable, so edge construction proceeds without verifying that the resulting graph captures meaningful fragrance relationships.

**Prevention:**
- **Validate edge semantics:** Create synthetic test cases. If two fragrances share top notes but not base notes, the graph should represent them as more similar than two that share no notes.
- **Domain expert review:** Have someone with fragrance knowledge check a sample of graph neighborhoods.
- **Sanity check:** Verify that "similar fragrance" pairs known to the domain (e.g., Dior Sauvage / Bleu de Chanel) are close in the graph embedding space.

**Phase mapping:** DATA-01, DATA-02 — the preprocessing and edge construction phases.

---

### Pitfall 12: Under-powered Statistical Comparison

**What goes wrong:** Running GraphSAGE vs. Popularity vs. Random once with one seed and declaring "GraphSAGE wins." With small datasets (Scentrix has one master JSON file, not millions of interactions), results are highly sensitive to train/test splits and random initialization.

**Prevention:**
- **Report mean ± std over 5+ runs with different seeds**
- **Use statistical significance tests** (paired t-test or Wilcoxon signed-rank) when comparing methods
- **Run multiple train/test splits** (if temporal, use rolling window splits)

**Phase mapping:** EVAL-03 (final analysis). Plan for multiple runs upfront.

---

### Pitfall 13: Overclaiming from the MEXT Demo

**What goes wrong:** The demo shows impressive recommendations for a few hand-picked fragrance profiles. It works well in the controlled demo environment. The MEXT interviewers assume this generalizes. No one checks whether the demo scenario is representative.

**Why it happens:** Demo pressure. The interview is the goal, so the demo gets polished while the evaluation is a footnote.

**Prevention:**
- **The demo and evaluation must tell the same story:** Don't show a polished demo that outperforms your evaluation results
- **Be transparent about limitations in the interview:** "Our model achieves NDCG@10 of X on cold-start users, which is Y% above popularity baseline. We're investigating failure cases in [specific area]."
- **Don't cherry-pick demo users:** Select demo users randomly or systematically, not by finding "the ones where it works"

**Phase mapping:** MEXT-01 (demo preparation). Build the demo FROM the evaluation framework, not separately.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **DATA-01/DATA-02** (Preprocessing & Graph Construction) | Pitfall #11: Unvalidated dataset edges | Add graph sanity checks and domain-expert review step. Validate edge semantics before training. |
| **PIPE-03** (Quiz → GraphSAGE Connection) | Pitfall #7: Sparse signal overreaction | Ensure confidence scores are propagated to the model. Use Bayesian smoothing for quiz signals. |
| **PIPE-03** (Quiz UX) | Pitfall #9: User abandonment on long quiz | Track completion rate as a metric. Have fallback for incomplete quizzes. |
| **EVAL-01** (Evaluation Harness) | Pitfall #2: Aggregate-only metrics | Stratify by coldness level. Add beyond-accuracy metrics (coverage, diversity). |
| **EVAL-01** (Evaluation Protocol) | Pitfall #3: Data leakage through temporal contamination or sampled negatives | Use temporal splits, rank all items, exclude test edges from message passing. |
| **EVAL-01** (Cold-Start Definition) | Pitfall #1: Binary cold/warm threshold | Implement multi-bucket evaluation: 0, 1-3, 4-10, 11-20 quiz responses. |
| **EVAL-03** (GraphSAGE Training) | Pitfall #4: GNN embedding collapse for cold nodes | Verify inductive mode, implement feature-only fallback, train with edge dropout. |
| **EVAL-03** (GraphSAGE Aggregation) | Pitfall #6: Cold neighbor contamination | Use GATConv or adaptive neighbor sampling instead of uniform random. |
| **EVAL-03** (Warm Performance) | Pitfall #8: Hybrid model degrades warm quality | Always report warm-user metrics separately. Compare with/without cold training. |
| **EVAL-02/EVAL-03** (Baseline Comparisons) | Pitfall #5: Popularity bias feedback loop | Track coverage and popularity distribution of recommendations. Debias evaluation. |
| **EVAL-03** (Final Analysis) | Pitfall #12: Under-powered statistical claims | Multiple seeds, significance tests, confidence intervals. |
| **MEXT-01** (Demo) | Pitfall #13: Overclaiming from demo | Align demo with eval results. Don't cherry-pick. Be transparent. |

---

## Summary for Roadmap Priority

| Rank | Pitfall | Risk Level | Must Fix Before |
|------|---------|-----------|----------------|
| 1 | Pitfall #3: Data leakage (temporal splits, negative sampling) | Invalid results | EVAL-01 implementation |
| 2 | Pitfall #4: GNN embedding collapse (zero neighbors) | Model broken | EVAL-03 training |
| 3 | Pitfall #2: Aggregate-only metrics | Misses cold-start degradation | EVAL-01 implementation |
| 4 | Pitfall #1: Binary cold-start threshold | Poor experimental resolution | EVAL-01 implementation |
| 5 | Pitfall #5: Popularity bias | Research claim invalid | EVAL-03 analysis |
| 6 | Pitfall #7: Sparse signal overreaction | Bad recommendations | PIPE-03 integration |
| 7 | Pitfall #9: User abandonment | Product failure | PIPE-03 tuning |
| 8 | Pitfall #6: Cold neighbor contamination | Suboptimal GNN | EVAL-03 training |
| 9 | Pitfall #10: No beyond-accuracy metrics | Incomplete research story | EVAL-01 |
| 10 | Pitfall #8: Hybrid degradation | Warm performance drops | EVAL-03 verification |
| 11 | Pitfall #11: Unvalidated graph edges | Wrong graph structure | DATA-02 validation |
| 12 | Pitfall #12: Under-powered stats | Unreliable conclusions | EVAL-03 analysis |
| 13 | Pitfall #13: Demo overclaiming | Interview credibility | MEXT-01 preparation |

**Key insight:** Pitfalls #1-#4 together mean a naive evaluation pipeline will produce numbers that look good but are meaningless. The **most important** single action is getting the EVAL-01 evaluation harness right before running any experiments. Every experiment run on a flawed harness wastes compute and, worse, generates misleading confidence.

## Sources

- arXiv 2508.07856 — Gusak et al. "Identifying Cold-Start Thresholds" (2025) [HIGH]
- arXiv 2209.04185 — "On the Pitfalls of NDCG Evaluation" (2022) [HIGH]
- arXiv 2307.14951 — "Common Pitfalls in Recommendation System Evaluation" (2023) [HIGH]
- arXiv 2306.10453 — "Evaluating GNNs for Link Prediction: Current Pitfalls" (2023) [HIGH]
- arXiv 2402.09711 — "Node Duplication Improves Cold-start Link Prediction" (2024) [HIGH]
- arXiv 2012.07064 — "Pre-training GNNs for Cold-Start Recommendation" (2020) [HIGH]
- arXiv 2209.12215 — "GPatch" (2022) [HIGH]
- arXiv 2410.14241 — "Graph Neural Patching" (2024) [HIGH]
- arXiv 2510.11402 — "On Inherited Popularity Bias in Cold-Start Item Recommendation" (2025) [HIGH]
- arXiv 2308.01118 — "A Survey on Popularity Bias in Recommender Systems" (2023) [HIGH]
- arXiv 2402.15680 — "Overcoming Pitfalls in Graph Contrastive Learning Evaluation" (2024) [HIGH]
- Amazon Research — "Cold Brew" (openreview.net/pdf?id=1ugNpm7W6E) [HIGH]
- Kumo.ai — "Handling Cold-Start Nodes in Production" [MEDIUM]
- Kumo.ai — "Temporal Splits" [HIGH]
- EngineersOfAI — "The Cold Start Problem" [MEDIUM]
- System Overflow — "Cold Start Failure Modes" [MEDIUM]
- BBC R&D — "Bootstrapped Personalised Popularity" (2023) [MEDIUM]
- Kapoor & Narayanan (2023) — ML evaluation pitfalls pre-registration framework [HIGH]
