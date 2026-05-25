# Phase 5: Research Differentiators — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-05-25
**Phase:** 05-research-differentiators
**Areas discussed:** Three evaluation modes, Stratification 3×3 grid, Quiz→GraphSAGE connection, Learning curves, Ablation study, Popularity debiasing

## Questions Asked

### Quiz initialization mechanism
- **Options:** Feature augmentation (enrich node features) / Separate evaluation variant / Both
- **Selected:** Separate evaluation variant — new pipeline path
- **Note:** Quiz confidence scores inject preference bias, not augment features

### Mode gating
- **Options:** Single evaluation_mode config flag / Dedicated functions per mode
- **Selected:** Single evaluation_mode config flag

### Quiz init mechanism
- **Options:** Edge weights (modulate similarity) / Initial node features (preference bias)
- **Selected:** Initial node features — quiz scores become extra embedding bias

### Coldness levels
- **Options:** Interaction count buckets / Percentile buckets
- **Selected:** Interaction count buckets — Level 0 (0 ints), Level 1 (1-3), Level 2 (4+)
- **User reasoning:** Percentile is semantically meaningless for cold-start research claim. Interaction counts map to defensible simulation protocol.

### Models in 3×3 grid
- **Options:** Popularity, Random, GraphSAGE / GraphSAGE variants (pure, quiz, warm)
- **Selected:** Popularity, Random, GraphSAGE — shows lift over baselines

### Quiz data source
- **Options:** Simulated quiz layer in ml/eval/ / Real quiz backend integration
- **Selected:** Simulated quiz layer — no Docker needed

### Quiz bias injection
- **Options:** Per-accord confidence vector (48-dim) / Learned preference embedding (MLP)
- **Selected:** 48-dim confidence vector added to accord one-hot. No new training components.

### Learning curve orchestration
- **Options:** Wrapper script calling run_evaluation() / Built-in run_learning_curve() method
- **Selected:** Built-in method — reuses same split across all k values
- **User reasoning:** Split must be shared across k values; wrapper script creates split variance that confounds results

### Plot series
- **Options:** Two lines (quiz-init + warm ref) / Three lines (quiz-init + pure cold + warm ref)
- **Selected:** Three lines

### Content-only variant
- **Options:** Direct feature cosine similarity / GraphSAGE with empty edge_index
- **Selected:** Direct feature cosine similarity — no GraphSAGE involved

### Random features for structure-only
- **Options:** IID Gaussian / Permuted real features (row-shuffle per column)
- **Selected:** Permuted real features — preserves per-dim distribution while destroying correlations

### Ablation output format
- **Options:** Comparison table + bar chart / Table only
- **Selected:** Comparison table + bar chart

### Popularity metric
- **Options:** Warm-set interaction counts / Global catalog attribute commonality
- **Selected:** Warm-set interaction counts

### Debiasing report format
- **Options:** Single report page with table + plots / Three separate metrics in standard output
- **Selected:** Single report page with table + plots

## Noted
- All discussion stayed within phase scope — no deferred ideas generated from discussion
