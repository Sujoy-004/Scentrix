# Scentrix ML Pipeline

Cold-start fragrance recommendation via GraphSAGE on a Jaccard-similarity graph.

## What It Does

The ML system evaluates GraphSAGE's ability to reconstruct a cold-start fragrance's relevant neighbours from its feature profile, without any interaction history. The central finding: graph construction methodology (embedding-based vs Jaccard-based edges) determines model quality more than the GNN itself.

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

The ablation proves independent edge construction is critical: Jaccard graph recovers 2.7× NDCG improvement over the circular embedding graph.

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

## Key Results

| Model | NDCG@10 | Notes |
|---|---|---|
| GraphSAGE-Jaccard | 0.494–0.523 | Primary result |
| GraphSAGE-Embedding | 0.183–0.191 | Circular graph — baseline |
| Feature-Only | 0.557 | Near-oracle, not fair comparison |
| Popularity | 0.008 | Naive baseline |
| Random | 0.031 | Naive baseline |

Key finding: embedding-derived graph construction introduces feature circularity that degrades NDCG by 63%. Jaccard-based independent edges recover 2.7× improvement (p≤0.001, d=0.93, n=10000 bootstrap).

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
