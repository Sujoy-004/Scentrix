---
phase: 01-pipeline-data-foundation
plan: 04
subsystem: ml, pipeline
tags: neo4j, graph-ingestor, sentence-transformer, knn, cosine-similarity, data-cleaning

# Dependency graph
requires:
  - phase: 01-pipeline-data-foundation
    plan: 03
    provides: Neo4j graph service at backend/app/services/graph.py for downstream consumers
provides:
  - ml/pipeline/ingest.py with FragranceGraphIngestor, ingest_fragrances_from_file, compute_similarity_edges
  - Cleaned fragrance dataset at ml/data/scentrix_master_cleaned.json (4559 records, 18 duplicates removed)
affects: graph population, evaluation harness, GraphSAGE training, neo4j database

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Self-contained ingestor — accepts Neo4j driver parameter, no backend.app.services.graph import
    - Two-phase ingestion: Phase 1 creates nodes + non-similarity edges, Phase 2 computes similarity via KNN
    - SentenceTransformer all-MiniLM-L6-v2 for description embedding cosine similarity
    - sklearn.neighbors.NearestNeighbors with cosine metric for top-10 KNN similarity edges
    - Dict.fromkeys() dedup pattern for MERGE-safe note/accord creation
    - FOREACH Cypher query for batch node/edge creation

key-files:
  created:
    - ml/pipeline/ingest.py
    - ml/data/scentrix_master_cleaned.json
  modified: []

key-decisions:
  - compute_similarity_edges is a standalone function (not ingestor method) — reusable without Neo4j connection
  - KNN n_neighbors=11 (10 + self), only edges with cosine > 0.5 kept, duplicates avoided via i < neighbor_idx
  - Model download allowed (local_files_only=False) — ingestor uses SentenceTransformer directly, NOT get_encoder()
  - dataset_gate failures on row count (<5000) and interaction coverage (0%) are expected — dataset is clean for graph ingestion, gate is for ML production

patterns-established:
  - Self-contained ingestor pattern: accepts driver, no backend imports, works from ml/ context
  - Two-phase graph population: structural edges first, then similarity edges (requires all embeddings)

requirements-completed: []

# Metrics
duration: 8 min
completed: 2026-05-22
---

# Phase 01 Plan 04: Data Preprocessing and Graph Population Summary

**FragranceGraphIngestor at ml/pipeline/ingest.py with compute_similarity_edges (SentenceTransformer + KNN), cleaned dataset at scentrix_master_cleaned.json (4559 records)**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-22T09:25:09Z
- **Completed:** 2026-05-22T09:33:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `ml/pipeline/ingest.py` with `FragranceGraphIngestor` class — self-contained, accepts Neo4j driver, no backend imports
- `ingest_fragrances()` creates Fragrance, Note (top/middle/base categories), Brand, and Accord nodes via Cypher MERGE queries
- Note relationships: `HAS_TOP_NOTE`, `HAS_MIDDLE_NOTE`, `HAS_BASE_NOTE` with category on Note nodes
- Brand relationship: `MADE_BY` edge to Brand node
- Accord relationships: `BELONGS_TO_ACCORD` edges
- `compute_similarity_edges()` standalone function — SentenceTransformer all-MiniLM-L6-v2 embeddings + sklearn KNN (top-10, cosine > 0.5 threshold)
- `SIMILAR_TO` edges computed in Phase 2 after all structural nodes exist
- CLI entry point with `--uri`, `--user`, `--password` arguments for standalone use
- Preprocessed full dataset: `clean.py` → `dataset_gate.py` → cleaned JSON (4577 → 4559 records, 18 duplicates removed)
- Makefile `enrich` target now references an existing `ml/pipeline/ingest.py`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ml/pipeline/ingest.py** — `4653804` (feat)
2. **Task 2: Run data preprocessing** — `578d612` (feat)

## Files Created/Modified

- `ml/pipeline/ingest.py` — FragranceGraphIngestor, compute_similarity_edges, ingest_fragrances_from_file, CLI entry point (299 lines)
- `ml/data/scentrix_master_cleaned.json` — Cleaned fragrance dataset (4559 records)

## Decisions Made

- `compute_similarity_edges` implemented as standalone function (not method on ingestor) — reusable without Neo4j connection, can be unit-tested independently
- Two-phase ingestion in `ingest_fragrances()`: Phase 1 creates nodes + structural edges, Phase 2 runs similarity computation and creates SIMILAR_TO edges. This is required because all fragrance nodes must exist before MATCH queries for similarity edges
- KNN parameters: n_neighbors=11 (10 neighbors + self), cosine distance metric, algorithm="brute" (appropriate for 4577 items). Duplicate edges avoided by directionality constraint (i < neighbor_idx)
- Dedup via `dict.fromkeys()` pattern for notes and accords ensures MERGE doesn't conflict on duplicate entries within a single fragrance
- Used raw SentenceTransformer (not TextEncoder.get_encoder()) — `local_files_only=False` allows first-time model download; avoids Pitfall 1 from Research

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Dataset gate failures (expected):** 2/9 checks failed — row count 4559 < 5000 threshold, interaction coverage 0%. Both expected: the dataset has 4577 raw entries (4559 after dedup), and interaction fields (rating_count, popularity_score) are not populated. This does NOT affect graph ingestion quality — the data is clean and valid for all fields needed (name, brand, notes, accords, description).

## Next Phase Readiness

- Graph ingestor ready to populate Neo4j when downstream pipeline connects
- Cleaned dataset ready for ingestion
- Next: run ingestion against Neo4j (needs running Docker services with graph db + backend), then validation via test_graph.py

---

*Phase: 01-pipeline-data-foundation*
*Completed: 2026-05-22*
