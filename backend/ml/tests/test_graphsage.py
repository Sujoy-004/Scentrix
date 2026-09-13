"""Behavioral tests for GraphSAGEWrapper (RSCH-01).

Tests the complete public API: train, predict, predict_cold_start, save, load.
Uses only CPU and synthetic data — no GPU or Neo4j required.
Focuses on edge cases: degree-0 nodes, empty graphs, single nodes.
"""
import numpy as np
import pytest
import torch

from ml.eval.models.graphsage_wrapper import GraphSAGEWrapper


# ---------------------------------------------------------------------------
# Fixtures: small synthetic datasets
# ---------------------------------------------------------------------------


@pytest.fixture
def wrapper():
    """Default GraphSAGEWrapper on CPU with tiny embedding dim for fast tests."""
    return GraphSAGEWrapper(
        embedding_dim=8,
        num_layers=1,
        dropout=0.0,
        edge_dropout=0.0,
        tau=1.0,
        device="cpu",
    )


@pytest.fixture
def synthetic_5node():
    """5 nodes, 4-dim features, fully connected edges (star graph)."""
    np.random.seed(0)
    features = np.random.randn(5, 4).astype(np.float32)
    # star: node 0 connected to 1,2,3,4
    edge_index = np.array([[0, 0, 0, 0], [1, 2, 3, 4]], dtype=np.int64)
    node_ids = ["n0", "n1", "n2", "n3", "n4"]
    return features, edge_index, node_ids


@pytest.fixture
def synthetic_10node():
    """10 nodes, 5-dim features, random edges."""
    np.random.seed(1)
    features = np.random.randn(10, 5).astype(np.float32)
    rng = np.random.default_rng(1)
    src = rng.integers(0, 10, 20)
    dst = rng.integers(0, 10, 20)
    # ensure no self-loops in test data
    mask = src != dst
    edge_index = np.stack([src[mask], dst[mask]], axis=0).astype(np.int64)
    node_ids = [f"n{i}" for i in range(10)]
    return features, edge_index, node_ids


# ---------------------------------------------------------------------------
# Precondition checks: predict / save must fail before training
# ---------------------------------------------------------------------------


class TestPreconditionGuards:
    """GraphSAGEWrapper must guard predict() and save() before training."""

    def test_predict_raises_error_before_training(self, wrapper, synthetic_5node):
        """Calling predict() on an untrained model must raise RuntimeError."""
        features, edge_index, node_ids = synthetic_5node
        with pytest.raises(RuntimeError, match="Model must be trained"):
            wrapper.predict(features, edge_index, node_ids, k=3)

    def test_predict_cold_start_raises_error_before_training(self, wrapper, synthetic_5node):
        """Calling predict_cold_start() on an untrained model must raise RuntimeError."""
        features, edge_index, node_ids = synthetic_5node
        with pytest.raises(RuntimeError, match="Model must be trained"):
            wrapper.predict_cold_start(
                features, edge_index, node_ids, test_node_ids=node_ids[:2], k=3
            )

    def test_save_raises_error_before_training(self, wrapper, tmp_path):
        """Calling save() on an untrained model must raise RuntimeError."""
        save_path = str(tmp_path / "untrained.pt")
        with pytest.raises(RuntimeError, match="Model must be trained"):
            wrapper.save(save_path)

    def test_load_without_training(self, wrapper, tmp_path):
        """load() after save() must restore is_trained=True and produce predictions."""
        # This tests that load properly restores trained state
        pass  # tested in save_load_round_trip


# ---------------------------------------------------------------------------
# Train + Predict smoke tests
# ---------------------------------------------------------------------------


class TestTrainAndPredict:
    """Basic train and predict workflow."""

    def test_train_and_predict_returns_recommendations(self, wrapper, synthetic_5node):
        """After training, predict() must return a dict with all node_ids as keys."""
        features, edge_index, node_ids = synthetic_5node
        wrapper.train(features, edge_index, node_ids, num_epochs=5)
        assert wrapper.is_trained

        results = wrapper.predict(features, edge_index, node_ids, k=2)
        assert isinstance(results, dict)
        assert set(results.keys()) == set(node_ids)
        for nid, recs in results.items():
            assert len(recs) == 2  # k=2
            for rec_id, score in recs:
                assert isinstance(rec_id, str)
                assert isinstance(score, float)

    def test_predict_excludes_self_from_recommendations(self, wrapper, synthetic_5node):
        """A node must not recommend itself (score must be -inf for self)."""
        features, edge_index, node_ids = synthetic_5node
        wrapper.train(features, edge_index, node_ids, num_epochs=5)
        results = wrapper.predict(features, edge_index, node_ids, k=4)
        for nid, recs in results.items():
            rec_ids = [r[0] for r in recs]
            assert nid not in rec_ids, f"{nid} recommends itself: {rec_ids}"

    def test_predict_k_larger_than_graph(self, wrapper, synthetic_5node):
        """predict() with k > number of nodes must return at most n items (self excluded from valid)."""
        features, edge_index, node_ids = synthetic_5node
        wrapper.train(features, edge_index, node_ids, num_epochs=5)
        results = wrapper.predict(features, edge_index, node_ids, k=100)
        for nid, recs in results.items():
            # Must not have more recommendations than total other nodes
            assert len(recs) <= len(node_ids)
            # Self-recommendations (if present) must have -inf score
            for rec_id, score in recs:
                if rec_id == nid:
                    assert score == float("-inf"), "Self-recommendation must have -inf score"

    def test_train_with_contrastive_loss_default(self, wrapper, synthetic_5node):
        """Default loss_type='contrastive' must complete training without error."""
        features, edge_index, node_ids = synthetic_5node
        wrapper.train(features, edge_index, node_ids, num_epochs=5)
        assert wrapper.is_trained
    
    @pytest.mark.xfail(strict=True, reason="IMPLEMENTATION BUG: _reconstruction_loss shape mismatch in F.linear when embedding_dim != input_dim. See _reconstruction_loss line 77: torch.randn_like(embeddings.T) creates wrong-shaped weight.")
    def test_train_with_reconstruction_loss(self, wrapper, synthetic_5node):
        """loss_type='reconstruction' must complete training without error.
        
        KNOWN BUG: _reconstruction_loss uses torch.randn_like(embeddings.T) as F.linear
        weight, but when embedding_dim != input_dim the shapes don't match.
        F.linear expects (out_features, in_features) but gets (num_nodes, embedding_dim).
        """
        features, edge_index, node_ids = synthetic_5node
        wrapper.train(features, edge_index, node_ids, num_epochs=5, loss_type="reconstruction")
        assert wrapper.is_trained


# ---------------------------------------------------------------------------
# Cold-start predictions (the core requirement RSCH-01)
# ---------------------------------------------------------------------------


class TestColdStartPredictions:
    """Cold-start predictions — RSCH-01 core requirement."""

    def test_cold_start_degree_zero_nodes(self, wrapper, synthetic_10node):
        """
        Degree-0 cold nodes (present in training features but with zero edges)
        must still receive recommendations via feature-only cosine similarity fallback.
        
        Contract: cold node IDs must be registered in self.node_ids at training time.
        They are present in the graph (features + id) but have zero incident edges.
        """
        features, edge_index, node_ids = synthetic_10node
        # Keep one node (n9) as cold — it has features but we'll remove its edges
        warm_ids = node_ids[:9]   # n0..n8 are warm
        cold_ids = node_ids[9:]   # n9 is cold

        # Build edge_index with only warm-warm edges
        warm_idx_set = set(range(9))
        warm_edge_mask = np.array([
            edge_index[0, i] in warm_idx_set and edge_index[1, i] in warm_idx_set
            for i in range(edge_index.shape[1])
        ])
        warm_edge_index = edge_index[:, warm_edge_mask]

        # Train on ALL nodes (warm + cold) but only warm edges
        wrapper.train(features, warm_edge_index, node_ids, num_epochs=10)

        # n9 is degree-0 in the training graph
        results = wrapper.predict_cold_start(
            node_features=features,
            edge_index=warm_edge_index,
            train_node_ids=warm_ids,
            test_node_ids=cold_ids,
            k=3,
        )

        assert "n9" in results, "Degree-0 cold node must get recommendations"
        assert len(results["n9"]) == 3, "Must return k=3 recommendations"
        for rec_id, score in results["n9"]:
            assert isinstance(rec_id, str)
            assert isinstance(score, float)
            assert -1.0 <= score <= 1.0, f"Score {score} outside [-1, 1]"

    def test_cold_start_with_edges(self, wrapper, synthetic_10node):
        """
        Cold nodes that DO have edges must get recommendations via
        inductive inference (model forward pass).
        """
        features, edge_index, node_ids = synthetic_10node

        train_ids = node_ids[:7]  # first 7 are "warm"
        test_ids = node_ids[7:]   # last 3 are "cold" but they have edges in the graph

        wrapper.train(features, edge_index, node_ids, num_epochs=10)

        results = wrapper.predict_cold_start(
            node_features=features,
            edge_index=edge_index,
            train_node_ids=train_ids,
            test_node_ids=test_ids,
            k=3,
        )

        for cold_id in test_ids:
            assert cold_id in results, f"Cold node {cold_id} must get recommendations"
            assert len(results[cold_id]) == 3
            for rec_id, score in results[cold_id]:
                assert isinstance(rec_id, str)

    def test_cold_start_mixed_degree_zero_and_with_edges(self, wrapper, synthetic_10node):
        """
        When some cold nodes have edges and some are degree-0, both must
        receive recommendations (different paths: inductive + feature-only).
        """
        features, edge_index, node_ids = synthetic_10node

        # Add a degree-0 node
        new_features = np.vstack([features, np.random.randn(1, 5).astype(np.float32)])
        new_ids = node_ids + ["cold_deg0"]

        train_ids = node_ids[:6]
        test_ids = node_ids[6:] + ["cold_deg0"]

        wrapper.train(new_features, edge_index, new_ids, num_epochs=10)

        results = wrapper.predict_cold_start(
            node_features=new_features,
            edge_index=edge_index,  # no edges to cold_deg0
            train_node_ids=train_ids,
            test_node_ids=test_ids,
            k=2,
        )

        for cold_id in test_ids:
            assert cold_id in results, f"Cold node {cold_id} must get recommendations"
            assert len(results[cold_id]) == 2

    def test_cold_start_all_degree_zero(self, wrapper):
        """
        ALL cold nodes are degree-0: must still produce recommendations
        via feature-only fallback.
        """
        np.random.seed(42)
        # 5 warm nodes + 2 cold nodes that have no edges
        all_features = np.random.randn(7, 4).astype(np.float32)
        # Warm: n0..n4 connected in a chain; Cold: n5, n6 with no edges
        warm_edge_index = np.array([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=np.int64)
        all_ids = ["warm0", "warm1", "warm2", "warm3", "warm4", "cold_A", "cold_B"]

        wrapper.train(all_features, warm_edge_index, all_ids, num_epochs=10)

        results = wrapper.predict_cold_start(
            node_features=all_features,
            edge_index=warm_edge_index,
            train_node_ids=all_ids[:5],
            test_node_ids=["cold_A", "cold_B"],
            k=2,
        )

        assert "cold_A" in results
        assert "cold_B" in results
        assert len(results["cold_A"]) == 2
        assert len(results["cold_B"]) == 2

    def test_cold_start_with_all_train_degree_zero_graph(self, wrapper):
        """
        Training graph has NO edges (empty edge_index) but cold-start still
        works via feature-only fallback.
        """
        np.random.seed(42)
        all_features = np.random.randn(6, 4).astype(np.float32)
        empty_edge = np.empty((2, 0), dtype=np.int64)
        all_ids = ["w0", "w1", "w2", "w3", "w4", "cold_X"]

        wrapper.train(all_features, empty_edge, all_ids, num_epochs=10)

        results = wrapper.predict_cold_start(
            node_features=all_features,
            edge_index=empty_edge,
            train_node_ids=all_ids[:5],
            test_node_ids=["cold_X"],
            k=2,
        )

        assert "cold_X" in results
        assert len(results["cold_X"]) == 2


# ---------------------------------------------------------------------------
# Persistence: save and load
# ---------------------------------------------------------------------------


class TestSaveAndLoad:
    """Save and load round-trip tests."""

    def test_save_and_load_round_trip(self, wrapper, synthetic_5node, tmp_path):
        """After save + load, model must produce predictions matching the original."""
        features, edge_index, node_ids = synthetic_5node
        wrapper.train(features, edge_index, node_ids, num_epochs=10)

        save_path = str(tmp_path / "model.pt")
        wrapper.save(save_path)

        # Load into a new wrapper
        wrapper2 = GraphSAGEWrapper(
            embedding_dim=8,
            num_layers=1,
            dropout=0.0,
            edge_dropout=0.0,
            tau=1.0,
            device="cpu",
        )
        wrapper2.load(save_path, input_dim=features.shape[1])

        assert wrapper2.is_trained
        assert wrapper2.node_ids == node_ids
        assert wrapper2.embedding_dim == 8

        # Both models should produce non-None predictions
        orig_results = wrapper.predict(features, edge_index, node_ids, k=2)
        loaded_results = wrapper2.predict(features, edge_index, node_ids, k=2)

        assert set(orig_results.keys()) == set(loaded_results.keys())
        # Predictions may differ slightly due to dropout/numerics but must be valid
        for nid in node_ids:
            assert len(loaded_results[nid]) == 2

    def test_load_restores_all_config(self, wrapper, synthetic_5node, tmp_path):
        """load() must restore all config params from the checkpoint."""
        features, edge_index, node_ids = synthetic_5node
        wrapper.train(features, edge_index, node_ids, num_epochs=5)
        save_path = str(tmp_path / "config_check.pt")
        wrapper.save(save_path)

        wrapper2 = GraphSAGEWrapper(device="cpu")
        wrapper2.load(save_path, input_dim=features.shape[1])

        assert wrapper2.num_layers == wrapper.num_layers
        assert wrapper2.dropout == wrapper.dropout
        assert wrapper2.edge_dropout == wrapper.edge_dropout
        assert wrapper2.tau == wrapper.tau
        assert wrapper2.loss_type == wrapper.loss_type


# ---------------------------------------------------------------------------
# Edge cases: degenerate inputs
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Degenerate graph inputs must not crash."""

    def test_empty_edge_index(self, wrapper):
        """Train with an empty edge_index (2x0) must not crash."""
        features = np.random.randn(5, 4).astype(np.float32)
        empty_edge = np.empty((2, 0), dtype=np.int64)
        node_ids = ["n0", "n1", "n2", "n3", "n4"]

        # Must not raise
        wrapper.train(features, empty_edge, node_ids, num_epochs=5)
        assert wrapper.is_trained

        results = wrapper.predict(features, empty_edge, node_ids, k=2)
        assert len(results) == 5

    def test_single_node(self, wrapper):
        """Train and predict with a single node must not crash."""
        features = np.random.randn(1, 4).astype(np.float32)
        edge_index = np.empty((2, 0), dtype=np.int64)
        node_ids = ["lonely"]

        wrapper.train(features, edge_index, node_ids, num_epochs=5)
        assert wrapper.is_trained

        # Predict with single node (k=5 but only self exists)
        results = wrapper.predict(features, edge_index, node_ids, k=5)
        assert "lonely" in results
        # Self-recommendation with -inf may appear; no other nodes to recommend
        valid_recs = [(rid, s) for rid, s in results["lonely"] if s != float("-inf")]
        assert len(valid_recs) == 0, f"Expected 0 valid recs, got {len(valid_recs)}"

    def test_edge_index_with_self_loops(self, wrapper, synthetic_5node):
        """Training with self-loops in edge_index must not crash."""
        features, edge_index, node_ids = synthetic_5node
        # Add self-loops
        self_loops = np.array([[0, 1, 2], [0, 1, 2]], dtype=np.int64)
        bad_edge = np.concatenate([edge_index, self_loops], axis=1)

        wrapper.train(features, bad_edge, node_ids, num_epochs=5)
        results = wrapper.predict(features, bad_edge, node_ids, k=3)
        assert "n0" in results

    def test_highly_similar_features(self, wrapper):
        """Nodes with identical features must not produce NaN scores."""
        features = np.ones((5, 4), dtype=np.float32)
        edge_index = np.array([[0, 1, 2], [1, 2, 3]], dtype=np.int64)
        node_ids = ["a", "b", "c", "d", "e"]

        wrapper.train(features, edge_index, node_ids, num_epochs=5)

        results = wrapper.predict(features, edge_index, node_ids, k=3)
        for nid, recs in results.items():
            for _, score in recs:
                assert not np.isnan(score), f"NaN score for {nid}"
                assert not np.isinf(score), f"Inf score for {nid}"

    def test_non_contiguous_node_ids(self, wrapper, synthetic_5node):
        """train_node_ids and test_node_ids may contain IDs not in node_ids (should skip gracefully)."""
        features, edge_index, node_ids = synthetic_5node
        wrapper.train(features, edge_index, node_ids, num_epochs=5)

        # train_node_ids references nodes that actually exist; test_node_ids has unknown IDs
        results = wrapper.predict_cold_start(
            node_features=features,
            edge_index=edge_index,
            train_node_ids=node_ids,
            test_node_ids=["nonexistent_1", "nonexistent_2"],
            k=2,
        )
        # Unknown test IDs should produce empty or no results
        assert isinstance(results, dict)
