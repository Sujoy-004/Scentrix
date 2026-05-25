# Phase 04-01 Summary: GraphSAGE Pipeline

**Completed:** 2026-05-25

## Deliverables

### Files Modified
- `ml/eval/models/graphsage_wrapper.py` — Refactored 287→244 lines
- `ml/eval/pipeline.py` — Enhanced with full GraphSAGE pipeline integration
- `ml/eval/config.py` — Added 11 GraphSAGE config fields

### Files Created
- `ml/eval/models/graph_builder.py` — KNN similarity graph construction (69 lines)

## What Was Built

### GraphSAGEWrapper (contrastive learning)
- **InfoNCE loss**: Positive pairs from KNN edges, negative pairs from random sampling, configurable tau temperature
- **Reconstruction fallback**: MSE loss available via `loss_type='reconstruction'`
- **Warm-train/full-inference**: Train on warm subgraph only, run inductive message passing on full graph
- **Degree-0 fallback**: Nodes with no neighbors use direct cosine similarity on raw 432-dim feature vectors
- **Persistence**: `save()`/`load()` with full checkpoint metadata (tau, loss_type)

### KNN Graph Builder
- `build_similarity_graph()` using sklearn `NearestNeighbors` on precomputed 384-dim embeddings
- Returns COO edge_index + edge_scores + node mappings
- Handles edge cases: fewer nodes than k, single node, no valid IDs in index

### Pipeline Integration
- `EvaluationOrchestrator.run()` now executes: load → build graph → build features → split → warm-train → cold-infer → metrics → aggregate → persist
- `_build_features()` assembles 432-dim feature vectors (accord one-hot + description embedding)
- `_build_ground_truth()` uses full-graph similarity neighbors as cold-start ground truth
- Three edge case paths: too-few-nodes skip, no-edges feature-only, warm-no-edges feature-only, and full contrastive path
- Model checkpoints, node embeddings, and graph data persist to `runs/{timestamp}/models/`

### Config
- 11 new `EvalConfig` fields: `graphsage_enabled`, `graphsage_embedding_dim`, `graphsage_num_layers`, `graphsage_epochs`, `graphsage_learning_rate`, `graphsage_dropout`, `graphsage_edge_dropout`, `graphsage_tau`, `graphsage_loss_type`, `graphsage_knn_k`, `graphsage_similarity_threshold`

## Verification
- All 4 modules import successfully
- GraphSAGE model instantiates with 432-dim input
- Config defaults verified (graphsage_enabled=True, tau=0.5, all defaults correct)
- InfoNCE contrastive loss: present
- Degree-0 fallback: present
- NearestNeighbors KNN: present

## Decisions Honored
| Decision | Status |
|----------|--------|
| D-01: KNN from embeddings | `graph_builder.py` with sklearn NearestNeighbors |
| D-02: 432-dim features (48+384) | `_build_features()` concatenates accord one-hot + description embedding |
| D-03: InfoNCE contrastive loss | `_info_nce_loss()` with configurable tau |
| D-04: Warm-train + full inference | `predict_cold_start()` with degree-0 fallback |
| D-05: Semi-integrated pipeline | Graph construction separate; train→metrics→persist integrated |
