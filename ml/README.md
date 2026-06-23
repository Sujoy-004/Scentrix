# Scentrix ML Pipeline

Cold-start fragrance recommendation via GraphSAGE on a Jaccard-similarity graph.

## What It Does

The ML system produces precomputed GraphSAGE embeddings [4559×64] used by the backend recommendation dispatcher at serving time. Backend loads the embeddings as `.npy` files — zero PyTorch runtime dependency.

## Directory Structure

```
ml/
├── eval/                   # Evaluation pipeline, metrics, significance testing
│   ├── pipeline.py         # Orchestrator: split → train → evaluate → report
│   ├── run_bootstrap.py    # Bootstrap significance tests (n=10000)
│   ├── models/             # GraphSAGE wrapper, graph builder, baselines
│   │   ├── graphsage_wrapper.py
│   │   ├── graph_builder.py
│   │   └── baseline_models.py
│   ├── metrics.py          # NDCG, precision, recall
│   ├── config.py           # EvalConfig (pydantic-settings)
│   ├── split.py            # Train/test splitting strategies
│   ├── significance.py     # Statistical significance testing
│   ├── aggregator.py       # Result aggregation
│   ├── reporting.py        # Report generation
│   ├── user_vector_prototype.py  # USER_VECTOR preference init
│   ├── quiz_simulator.py   # Simulated quiz responses
│   └── ...                 # Diagnostic modules (seed sensitivity, bottleneck, oracle gap, etc.)
├── models/                 # Neural network model definitions
│   ├── graph_sage.py       # Standalone GraphSAGE model
│   └── text_encoder.py     # Sentence-Transformer encoder
├── pipeline/               # Data pipeline
│   ├── clean.py            # Dataset cleaning and deduplication
│   ├── ingest.py           # Neo4j graph ingestion
│   └── filter_elite.py     # Quality gate filtering
├── export/                 # Embedding export for serving
│   └── export_jaccard_embeddings.py  # Build-time export → ml/models/serving/v1/
├── data/                   # Datasets and cached embeddings
├── scripts/                # Utility scripts
└── tests/                  # ML pipeline tests
```

## How to Run

```bash
# Full evaluation: split → GraphSAGE → baselines → sweep
python -m ml.eval.pipeline

# Bootstrap significance tests (n=10000)
python -m ml.eval.run_bootstrap

# Export embeddings for serving (checkpoint at archive/research/evaluation-runs/)
python -m ml.export.export_jaccard_embeddings
```

## Production Serving

The backend loads precomputed embeddings from `ml/models/serving/v1/`:
- `node_embeddings_jaccard.npy` — L2-normalized [4559×64] embeddings
- `node_ids_jaccard.json` — aligned fragrance IDs
- `metadata.json` — provenance and validation results

These artifacts are produced by `ml/export/export_jaccard_embeddings.py` using the canonical GraphSAGE checkpoint from the evaluation pipeline. The serving artifacts are checked into the repository and do not require PyTorch or model training to load.

## Research

For research methodology, evaluation results, and reproducibility commands, see [docs/RESEARCH.md](../docs/RESEARCH.md).
