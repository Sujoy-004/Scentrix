"""Quality-gate tests for the SAVED GraphSAGE-Jaccard embedding artifacts.

Runs against the real artifacts in backend/app/data (node_embeddings_jaccard.npy,
node_ids_jaccard.json, metadata.json). Gates:
  - shape (4559, 64), float32, all finite;
  - unit-ish L2 norms (within tolerance);
  - zero rounded-duplicate embedding rows (6 dp);
  - within-primary-accord median cosine > cross-primary median, and
    within-primary median < 0.99 (structured, not collapsed; the retrained
    artifact's within median is documented in metadata — the trained-pipeline
    gate in train.py uses 0.98, the test uses the relaxed 0.99 bound);
  - catalog-order invariance self-check (permuted feature rows / edge indices
    must recover near-identical embeddings with the same model weights);
  - node ids are unique, in catalog order, and match the catalog;
  - metadata exposes catalog_sha256, text_model, reproducibility and the
    validation semantics summary.

Run:  <venv>/python.exe -m pytest ml/tests/test_embedding_validation.py -q
(from backend/).
"""

import json
from pathlib import Path

import numpy as np
import torch

import train as train_pipeline

DATA_DIR = Path(__file__).resolve().parents[2] / "app" / "data"
CATALOG_PATH = DATA_DIR / "scentrix_master_cleaned.json"
EMBEDDINGS_PATH = DATA_DIR / "node_embeddings_jaccard.npy"
IDS_PATH = DATA_DIR / "node_ids_jaccard.json"
METADATA_PATH = DATA_DIR / "metadata.json"

EMBEDDING_DIM = train_pipeline.EMBEDDING_DIM
EXPECTED_NODES = train_pipeline.EXPECTED_CATALOG_SIZE
ORDER_INVARIANCE_MAX_DIFF = train_pipeline.SEMANTIC_ORDER_INVARIANCE_MAX_DIFF
WITHIN_COLLAPSE_BOUND_TEST = 0.99


def _load_artifacts():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    embeddings = np.load(EMBEDDINGS_PATH)
    node_ids = json.loads(IDS_PATH.read_text(encoding="utf-8"))
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return catalog, embeddings, node_ids, metadata


def test_artifact_shape_dtype_and_finite():
    _, embeddings, node_ids, _ = _load_artifacts()
    assert embeddings.shape == (EXPECTED_NODES, EMBEDDING_DIM)
    assert embeddings.shape == (len(node_ids), EMBEDDING_DIM)
    assert embeddings.dtype == np.float32
    assert np.isfinite(embeddings).all()


def test_unit_norms_within_tolerance():
    _, embeddings, _, _ = _load_artifacts()
    norms = np.linalg.norm(embeddings, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-3)
    assert float(norms.min()) > 0.999
    assert float(norms.max()) < 1.001


def test_node_ids_unique_and_catalog_order():
    catalog, _, node_ids, _ = _load_artifacts()
    assert len(node_ids) == len(set(node_ids))
    canonical = [str(item["id"]) for item in catalog]
    assert node_ids == canonical


def test_zero_rounded_duplicate_rows():
    _, embeddings, _, _ = _load_artifacts()
    rounded = np.round(embeddings, train_pipeline.SEMANTIC_ROUND_DECIMALS)
    _, counts = np.unique(rounded, axis=0, return_counts=True)
    assert int(np.sum(counts > 1)) == 0


def test_within_vs_cross_primary_separation_and_no_collapse():
    catalog, embeddings, _, metadata = _load_artifacts()
    stats = train_pipeline.semantic_separation_stats(embeddings, catalog)
    within = stats["within_primary_similarity_median"]
    cross = stats["cross_primary_similarity_median"]
    assert within > cross, "within-primary median cosine must beat cross-primary"
    assert within < WITHIN_COLLAPSE_BOUND_TEST, (
        f"within-primary median {within:.4f} >= {WITHIN_COLLAPSE_BOUND_TEST} — embeddings collapsed"
    )
    # cross-reference the numbers recorded in metadata at training time
    recorded = metadata["validation"]
    assert np.isclose(stats["within_primary_pairs_sampled"],
                      recorded["within_primary_pairs_sampled"])
    assert np.isclose(stats["cross_primary_pairs_sampled"],
                      recorded["cross_primary_pairs_sampled"])


def test_order_invariance_self_check():
    catalog, _, _, _ = _load_artifacts()
    # Deterministic synthetic text features: order invariance is an
    # architectural property of the model, not of the real text embeddings, so
    # the test must not depend on the large regenerable training cache
    # (text_embeddings.npy). The catalog nodes and Jaccard graph are real.
    rng = np.random.default_rng(0)
    text_embeddings = rng.standard_normal((len(catalog), 384)).astype(np.float32)
    node_features, node_ids = train_pipeline.build_features(catalog, text_embeddings)
    edge_index, _, _ = train_pipeline.build_jaccard_graph(catalog, node_ids)
    assert node_features.shape[0] == len(node_ids)

    torch.manual_seed(train_pipeline.SEED)
    model = train_pipeline.GraphSAGE(
        input_dim=node_features.shape[1], hidden_dim=EMBEDDING_DIM,
        num_layers=train_pipeline.NUM_LAYERS, dropout=train_pipeline.DROPOUT,
    )
    result = train_pipeline.check_order_invariance(
        model, node_features, edge_index, "cpu",
        subsample_nodes=min(train_pipeline.SEMANTIC_ORDER_INVARIANCE_SUBSAMPLE, EXPECTED_NODES),
    )
    assert result["order_invariance_passed"]
    assert result["order_invariance_max_abs_diff"] < ORDER_INVARIANCE_MAX_DIFF


def test_metadata_keys_present():
    _, _, _, metadata = _load_artifacts()
    assert metadata["catalog_sha256"]
    assert metadata["text_model"] == train_pipeline.TEXT_MODEL_DEFAULT
    assert metadata["reproducibility"]["seed"] == train_pipeline.SEED
    assert metadata["reproducibility"]["numpy_version"]
    assert metadata["reproducibility"]["torch_version"]
    assert metadata["training"]["train_loss_curve_min"] is not None
    assert metadata["training"]["loss"].lower().startswith("anchored infonce")
    val = metadata["validation"]
    assert val["rounded_duplicate_rows"] == 0
    assert val["semantic_separation_ok"] is True
    assert val["within_not_collapsed"] is True
    assert val["isolated_fraction_ok"] is True
    assert val["order_invariance_passed"] is True
    assert val["all_checks_passed"] is True
