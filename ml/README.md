# Scentrix ML Pipeline

Machine learning pipeline for fragrance embeddings, personalization, and recommendation ranking.

## Architecture

The ML system consists of 5 connected stages:

1. **Knowledge Graph** — Neo4j database with fragrance relationships
2. **Embedding Model** — GraphSAGE GNN (2-layer, 128-dim output)
3. **Personalization** — Bayesian Personalized Ranking (BPR) loss
4. **Text Matching** — Sentence-BERT (`all-MiniLM-L6-v2`)
5. **Ranking** — Weighted combination of similarity scores

## Directory Structure

```
ml/
├── graph/                   # Knowledge graph interaction
│   ├── neo4j_client.py      # Neo4j connection with pooling
│   └── schema_init.cypher   # Graph constraints and indexes
├── scraper/                 # Fragrantica data scraper
│   ├── spiders/             # Scrapy spiders
│   └── pipelines/           # R2 storage pipeline
├── data/                    # Data storage and preprocessing
│   ├── seed_fragrances.json # Bootstrap dataset
│   ├── graph_dataset.py     # PyTorch Geometric data loader
│   └── text_embeddings.pkl  # Cached text embeddings
├── models/                  # Neural network models
│   ├── graph_sage.py        # GraphSAGE implementation
│   └── text_encoder.py      # Sentence-BERT wrapper
├── training/                # Training and evaluation
│   ├── train_graphsage.py   # Training loop
│   ├── evaluate.py          # Hit Rate@10, NDCG@10 metrics
│   └── losses/              # BPR loss implementation
├── pipeline/                # Data and ML orchestration
│   ├── clean.py             # Data cleaning and deduplication
│   ├── ingest.py            # Neo4j graph ingestion
│   ├── populate_pinecone.py # Embed to vector DB
│   └── query_pinecone.py    # ANN similarity search
├── scoring/                 # Final ranking logic
│   └── rank.py              # Weighted ensemble ranking
├── flows/                   # Prefect workflows
│   └── weekly_refresh.py    # Weekly ETL + retraining
├── tests/                   # ML pipeline tests
│   └── test_graph.py        # Graph validation
├── logs/                    # Training run logs and metrics
└── README.md
```

## Quickstart

### Prerequisites
- Python 3.11+
- Neo4j running locally or on AuraDB
- Redis (for caching)
- Pinecone account (for vector search)

### Local Setup

```bash
# Install dependencies
cd ../backend
pip install -e ".[dev]"

# Seed initial data
python ml/pipeline/ingest.py

# Train GraphSAGE model
python ml/training/train_graphsage.py

# Populate Pinecone index
python ml/pipeline/populate_pinecone.py

# Run evaluation
python ml/training/evaluate.py
```

## Validation Profiles and Release Gates

Production validation now uses profile-based thresholds and strict-mode gates.

- `SCENTSCAPE_VALIDATION_PROFILE=local|staging|production`
- `SCENTSCAPE_VALIDATION_STRICT=true|false`

### Graph Validation

```bash
python -m ml.tests.test_graph --profile local
python -m ml.tests.test_graph --profile staging
python -m ml.tests.test_graph --profile production --strict
```

### End-to-End Integration Validation

```bash
python -m ml.tests.test_integration --cleanup --profile local
python -m ml.tests.test_integration --cleanup --profile production --strict
```

Integration artifacts are written to `ml/logs/integration/` by default.

### Production Release Gate

Run deterministic multi-cycle release checks before promotion:

```bash
python -m ml.tests.release_gate --profile production --strict --cycles 3
```

Release gate artifacts are written to `ml/logs/release_gate/` by default.

### Recommended Promotion Policy

1. Zero validation query errors.
2. Zero failed checks in strict mode.
3. Deterministic graph totals across repeat runs.
4. Artifact attached to release sign-off.

## Models

### GraphSAGE (Graph Embeddings)
- Architecture: 2-layer GraphSAGE with mean aggregation
- Input features: Note one-hot, brand embedding, TF-IDF descriptions
- Output: 128-dim fragrance embeddings
- Training: BPR loss + AdamW optimizer
- Evaluation: Hit Rate@10 (primary), NDCG@10 (secondary)
- Retraining: Weekly batch job on delta ratings

See [docs/ml-architecture.md](../docs/ml-architecture.md) for detailed architecture decisions.

### Sentence-BERT (Text Embeddings)
- Model: `all-MiniLM-L6-v2` (384-dim, 22M params)
- Used for: User text queries → fragrance description matching
- Inference: <100ms per query
- Pre-computed: All fragrance descriptions cached weekly

### Bayesian Personalized Ranking (BPR)
- Loss function for personalization
- For each user's (positive) rating: sample 5 negative fragrances
- Minimize: rank loss between positive and negative in embedding space
- Applied: Multiplied with GraphSAGE embeddings during fine-tuning

## Data Pipeline

### Ingestion
```
Fragrantica (web) 
  → Scrapy spider (respects robots.txt, 1 req/sec)
    → Raw JSON (Cloudflare R2)
      → Cleaning (validation, deduplication, normalization)
        → Neo4j ingestion (idempotent upsert)
```

### Weekly Refresh (Prefect)
```
New ratings in PostgreSQL
  → GraphSAGE retraining (delta only)
    → Pinecone index update
      → Text embeddings regeneration
        → Redis cache invalidation
```

### Seed Data
- 100 hand-curated fragrances covering all note categories
- Used for bootstrap before scraper completes
- See [ml/data/seed_fragrances.json](ml/data/seed_fragrances.json)

## Performance

- GraphSAGE inference: ~50ms/fragrance (500ms for top-10)
- Pinecone ANN search: <100ms for 1K nearest neighbors
- Text encoding: <100ms per query
- Full recommendation pipeline: <500ms (cached) / <2s (cold start)

## Evaluation Metrics

### Offline Metrics (Test Set)
- **Hit Rate@10** — Did correct recommendation appear in top-10? (target: ≥0.65)
- **NDCG@10** — Normalized Discounted Cumulative Gain (secondary)

### Online Metrics (User Feedback)
- Recommendation satisfaction survey (4-5 scale, target: ≥4.0)
- Click-through rate on recommendations
- Collection add rate from recommendations

## Configuration

Set via environment or code:
```python
# ml/config.py
GRAPHSAGE_HIDDEN_DIM = 256  # Hidden dimension for GraphSAGE
GRAPHSAGE_OUTPUT_DIM = 128  # Output embedding dimension
GRAPHSAGE_DROPOUT = 0.3
BPR_NEGATIVE_SAMPLES = 5
TEXT_ENCODER_MODEL = "all-MiniLM-L6-v2"
```

## Troubleshooting

**Q: GraphSAGE loss not converging?**
- Check Neo4j graph has ≥100 fragrances, ≥50 rated pairs
- Increase learning rate to 0.01, reduce early stopping patience
- Check batch size (should be 128-256)

**Q: Pinecone query returns 0 results?**
- Verify index name matches `PINECONE_INDEX_NAME`
- Check namespace is "fragrances"
- Run `populate_pinecone.py` to refresh embeddings

**Q: Text search too slow?**
- Cache text encodings with `ml/data/text_embeddings.pkl`
- Pre-compute all fragrance descriptions on startup
- Use batch encoding for multiple queries

## Next Steps (Phase 5)

- Full evaluation on ≥500 fragrances (Hit Rate@10 ≥0.65)
- Load testing: 100 concurrent recommendation requests
- Model interpretability: SHAP values for top recommendations
- Cold-start handling for new users without history
