# Phase 5: Research Differentiators — Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Core research claims validated through evaluation experiments built on the GraphSAGE pipeline (Phase 4). Delivers quiz-initialized evaluation, stratification reporting, learning curves, ablation study, and popularity debiasing — the experiment suite that produces defensible results for the MEXT interview research pitch. Does NOT include the MEXT demo page (Phase 6) or the E2E quiz backend integration (the backend already exists; Phase 5 uses a simulated quiz layer within ml/eval/).

**Scope emphasis:** Evaluation framework + reporting. The quiz-to-pipeline connection (RSCH-03) is the integration bridge; the bulk is running experiments and producing plots/tables.
</domain>

<decisions>
## Implementation Decisions

### Three Evaluation Modes
- **D-01:** Three modes gated by a single `evaluation_mode` config flag in EvalConfig (values: `pure_cold`, `quiz_init`, `warm_ref`). EvaluationOrchestrator.run() branches on this flag.
- **D-02:** Quiz-init is a separate evaluation variant (not feature augmentation). It injects a 48-dim per-accord confidence vector as preference bias into cold-node initial features — added to the accord one-hot before GraphSAGE message passing.
- **D-03:** The preference bias approach means quiz-init uses the same 432-dim feature dimension as pure cold-start. No additional network components or training parameters.
- **D-04:** Pure cold-start: standard run_evaluation() as built in Phase 4. Quiz-init: inject simulated preference bias before inference. Warm-start reference: evaluate on warm items (interaction history available) as upper bound.

### Stratification 3×3 Grid
- **D-05:** Coldness levels defined by interaction count buckets: Level 0 (0 interactions), Level 1 (1-3 interactions), Level 2 (4+ interactions). Aligned with `stratified_leave_cold_out` split strategy. Not percentile-based.
- **D-06:** Grid columns are Popularity, Random, GraphSAGE — shows GraphSAGE's lift over naive baselines at each coldness level.
- **D-07:** Grid reports NDCG@10 per cell as the primary metric. Results comparison uses the existing ResultsAggregator + comparison table infrastructure from Phase 3.

### Quiz → GraphSAGE Connection
- **D-08:** Quiz data source is a simulated layer within ml/eval/ — `QuizSimulator` generates per-accord confidence vectors programmatically. No Docker or backend runtime needed. Runs as part of `run_evaluation()`.
- **D-09:** Quiz simulation samples accords from the dataset, assigns confidence scores with configurable noise. The confidence vector is 48-dim (one per unique primary accord), where each entry reflects simulated user preference for that accord category.
- **D-10:** The quiz simulation is parameterized by `quiz_length` (number of accords to sample, k ∈ {1,3,5,7,10}) and `quiz_noise` (confidence score noise level).

### Learning Curves
- **D-11:** `EvaluationOrchestrator.run_learning_curve()` is a built-in method (not a wrapper script). It loops internally over k ∈ {1,3,5,7,10}, reusing the SAME cold-start split across all k values. This isolates quiz length effects from split variance.
- **D-12:** The plot shows three lines: quiz-init GraphSAGE (rising with k), pure cold-start baseline (flat), warm-start reference (flat upper bound). Illustrates how quiz-init approaches warm-start performance as quiz length increases.

### Ablation Study Variants
- **D-13:** Content-only variant: direct cosine similarity on 432-dim feature vectors. No GraphSAGE model involved. Pure content-based baseline within the ablation.
- **D-14:** Structure-only variant: GraphSAGE trained on row-permuted features (each column shuffled independently across rows). Destroys feature-meaning correlations while preserving per-dimension distribution and graph structure.
- **D-15:** Full GraphSAGE: the standard pipeline from Phase 4 (features + graph + contrastive learning).
- **D-16:** Ablation output format: comparison table (NDCG@10 per variant) + side-by-side bar chart.

### Popularity Debiasing
- **D-17:** Popularity computed from warm-set interaction counts — fragrances with more warm-user interactions are more popular. Decile splits from this distribution.
- **D-18:** Report format: single HTML report page. Includes popularity-stratified NDCG table (decile × model), catalog coverage bar chart per model, and long-tail distribution curve. Generated as a deliverable alongside the standard eval output.

### OpenCode's Discretion
- Exact matplotlib/seaborn plot styling (defaults are acceptable)
- Table formatting details
- Quiz simulator noise level default
- Debiasing report exact layout within the report page
- File naming for plots and report artifacts

</decisions>

<specifics>
## Specific Ideas

- "Interaction count buckets give you a principled simulation protocol — Level 0 = completely held out, Level 1-3 = minimal signal, Level 2 4+ = warm reference. That directly mirrors real deployment scenarios."
- "If the split varies across k values, your learning curve is measuring split variance plus quiz length effect simultaneously. The NDCG@10 vs k plot becomes uninterpretable."
- "Structure-only with permuted features: destroys feature-meaning correlations but keeps the same per-dimension distribution. More rigorous — isolates structure from content statistically."

</specifics>

<canonical_refs>
## Canonical References

### Requirements
- `docs/requirements/RSCH-03.md` — Quiz-initialized GraphSAGE evaluation: three modes, quiz confidence → preference initialization (PHANTOM — does not exist on disk)
- `docs/requirements/RSCH-04.md` — Cold-start stratification: 3×3 grid, interaction-bucket levels (PHANTOM — does not exist on disk)
- `docs/requirements/RSCH-05.md` — Learning curves: NDCG@10 vs quiz length (PHANTOM — does not exist on disk)
- `docs/requirements/RSCH-06.md` — Ablation study: content-only, structure-only, full GraphSAGE (PHANTOM — does not exist on disk)
- `docs/requirements/RSCH-07.md` — Popularity debiasing: coverage, stratified NDCG, long-tail distribution (PHANTOM — does not exist on disk)
- `.planning/REQUIREMENTS.md` §RSCH — Master requirements file with all RSCH requirement definitions

### Upstream Dependencies (Phase 4)
- `ml/eval/models/graphsage_wrapper.py` — GraphSAGE wrapper with contrastive learning, degree-0 fallback
- `ml/eval/models/graph_builder.py` — KNN similarity graph construction
- `ml/eval/pipeline.py` — EvaluationOrchestrator with run_evaluation(), _build_features(), _build_ground_truth()
- `ml/eval/config.py` — EvalConfig with 11 GraphSAGE fields

### Existing Evaluation Infrastructure (Phases 2-3)
- `ml/eval/split.py` — ColdStartSplitter, LeaveColdOutStrategy, SplitResult
- `ml/eval/metrics.py` — MetricsWrapper with ranx-based precision/NDCG/recall
- `ml/eval/aggregator.py` — ResultsAggregator for cross-model comparison tables
- `ml/eval/significance.py` — BootstrapSignificance for statistical testing

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **EvaluationOrchestrator** (`ml/eval/pipeline.py`): The `run()` method is the integration point — adding `evaluation_mode` branching, quiz simulator call, and the three evaluation mode paths.
- **ResultsAggregator** (`ml/eval/aggregator.py`): Already handles multiple model comparison tables. The 3×3 grid can use this for cross-model reporting.
- **EvalConfig** (`ml/eval/config.py`): Adding `evaluation_mode`, `quiz_length`, `quiz_noise` fields extends the existing Pydantic config pattern.
- **ColdStartSplitter** (`ml/eval/split.py`): The `stratified_leave_cold_out` strategy already handles interaction-count-based splitting.

### Established Patterns
- **Config-driven evaluation**: All experimental parameters go through EvalConfig. New fields follow the same Field() + default pattern.
- **Artifact persistence**: Run outputs go to `ml/eval/runs/{timestamp}/`. Plots and report pages follow this pattern.
- **Comparison infrastructure**: ResultsAggregator produces comparison tables in plain-text + Markdown + JSON — the 3×3 grid and debiasing report extend this.

### Integration Points
- `ml/eval/pipeline.py` lines 82-209: The GraphSAGE section in `run()` — `evaluation_mode` branching goes here
- `ml/eval/config.py`: New fields go alongside existing `graphsage_*` fields
- `ml/eval/runs/`: All experiment artifacts persist here

</code_context>

<deferred>
## Deferred Ideas

- Real quiz backend integration (actual Docker stack) — not needed for reproducible experiments; simulated layer is sufficient and faster
- Hyperparameter optimization over GraphSAGE params (ENHN-04) — separate research phase
- Beyond-accuracy metrics — diversity, novelty, ILD (ENHN-01) — v2 scope
- Multi-dataset validation (ENHN-02) — v2 scope
- User studies with real participants (ENHN-05) — out of scope for MEXT

</deferred>

---

*Phase: 05-research-differentiators*
*Context gathered: 2026-05-25*
