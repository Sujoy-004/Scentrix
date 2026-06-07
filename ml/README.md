# Scentrix ML Pipeline

Cold-start fragrance recommendation via GraphSAGE on a Jaccard-similarity graph.

## What It Does

The ML system evaluates GraphSAGE's ability to reconstruct a cold-start fragrance's relevant neighbours from its feature profile, without any interaction history. The current evaluation pipeline uses a note-Jaccard ground truth definition. ⚠️ Phase 5.1 audit found this evaluation has two methodological flaws: (1) NDCG@10 was computed as RR@10, and (2) ground truth uses the same signal (note-Jaccard) as the Jaccard graph — creating a circular evaluation. Fixes are applied (Fix A: true NDCG) and proposed (Fix B: brand+accord ground truth) in the `ml/eval/` pipeline but not yet committed. All values below are from the original pipeline. See Phase 5.1 CONTEXT.md for full audit details and corrected numbers.

## Model: GraphSAGE

Two architectures exist in the codebase:

**Eval wrapper** (primary — used in pipeline):
- 2-layer mean-aggregation GraphSAGE with configurable hidden dim (default 64)
- Contrastive loss (InfoNCE) with cosine similarity
- Edge dropout for regularization, tau temperature scaling
- Input: concatenated one-hot accord vector + 432-dim embedding → variable-dim features

**Standalone model** (`models/graph_sage.py`):
- 2-layer SAGEConv, hidden=128, output=384
- Reconstruction loss (MSE on feature reconstruction)
- 10-dimensional handcrafted node features (year, note counts, accord count, description length, gender, concentration)
- Early stopping with patience=20

## Graph Construction

Two strategies, compared head-to-head in the evaluation:

**Embedding graph** (`build_similarity_graph`):
- KNN (k=10, metric=cosine) on `embeddings.npy` (432-dim Sentence-Transformer embeddings)
- Threshold=0.5 similarity cutoff
- Problem: feature circularity — node features contain the same embeddings used to build edges

**Jaccard graph** (`build_jaccard_graph`):
- Edge if primary_accord matches AND Jaccard(notes) > threshold
- Default threshold=0.20 (99.2% cold item coverage)
- Zero embedding signal in edge construction
- Independent structural signal from fragrance note composition

The ablation shows Jaccard graph outperforms the circular embedding graph under the original pipeline. ⚠️ Phase 5.1 audit found the gap shrinks under corrected metric (true NDCG) and non-circular ground truth (brand+accord) — the "2.7×" figure is specific to the original flawed methodology.

## Evaluation Pipeline

```bash
# Full evaluation: split → GraphSAGE (embedding + Jaccard) → baselines → sweep
python -m ml.eval.pipeline

# Bootstrap significance tests (n=10000)
python -m ml.eval.run_bootstrap

# Degree-split analysis for threshold sweep
python ml/scripts/sweep_degree_split.py
```

The pipeline:
1. Stratified cold-start split (80/20 warm/cold) via `ColdStartSplitter`
2. Builds both embedding-based and Jaccard-based graphs
3. Trains GraphSAGE on warm-subgraph edges only
4. Predicts cold-start rankings via cosine similarity of learned embeddings
5. Computes Precision@10, NDCG@10, Recall@10 via `ranx`
6. Runs Jaccard threshold sweep (0.10–0.30) with degree-split reporting
7. Compares against Popularity, Random, Feature-Only, and Content-Only baselines

## Key Results (original pipeline — under evaluation audit)

⚠️ All values below use the original pipeline methodology (RR@10 labeled as NDCG@10, note-Jaccard circular ground truth). Phase 5.1 audit found these numbers change under corrected methodology. See Phase 5.1 CONTEXT.md for before/after comparison.

**Original pipeline (pre-Fix-B) — NOT reproducible:**

| Model | NDCG@10 (was RR@10) | Notes |
|---|---|---|
| GraphSAGE-Jaccard | 0.494–0.523 | Original primary result — circular GT inflated |
| GraphSAGE-Embedding | 0.183–0.191 | Circular graph — baseline |
| Feature-Only | 0.557 | Near-oracle under old GT |
| Popularity | 0.008 | Naive baseline |
| Random | 0.031 | Naive baseline |

**Corrected (Fix A + Fix B, brand_accord GT, true NDCG) — canonical:**

| Model | NDCG@10 | Notes |
|---|---|---|
| Feature-Only | **0.399** | Dominates — 3.47× over GS-Jaccard |
| GraphSAGE-Jaccard | **0.115** | 1.21× over GS-Embedding (p=0.008, d=0.11) |
| GraphSAGE-Embedding | **0.095** | Non-monotonic across coldness levels |
| Content-Only | 0.047 | Description embedding cosine |
| Popularity | 0.000 | Cold-start floor |
| Random | 0.001 | Performance floor |

Original finding (embedding-derived graph introduces feature circularity) is superseded by the corrected finding: after removing evaluation leakage, Feature-Only dominates by 3.47×, and the primary contribution is methodological — evaluation methodology matters more than model complexity.

## Directory Structure

```
ml/
├── eval/                   # Evaluation pipeline, metrics, significance testing
│   ├── pipeline.py         # Orchestrator: split → train → evaluate → report
│   ├── run_bootstrap.py    # Bootstrap significance tests (n=10000)
│   ├── models/             # GraphSAGE wrapper, graph builder, baselines
│   └── config.py           # EvalConfig (pydantic-settings)
├── models/                 # Neural network model definitions
│   ├── graph_sage.py       # Standalone GraphSAGE + Pinecone upload
│   └── text_encoder.py     # Sentence-Transformer encoder
├── pipeline/               # Data pipeline
│   ├── clean.py            # Dataset cleaning and deduplication
│   ├── ingest.py           # Neo4j graph ingestion
│   └── filter_elite.py     # Quality gate filtering
├── data/                   # Datasets and cached embeddings
├── scripts/                # Utility scripts
├── tests/                  # ML pipeline tests
└── training/               # Training entry point (scaffold)
```
