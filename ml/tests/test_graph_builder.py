"""Behavioral tests for build_similarity_graph() (RSCH-02).

Tests KNN graph construction from precomputed embeddings.
Handles edge cases: fewer nodes than k, single node, no valid IDs, threshold filtering.
Uses temporary file fixtures — no Neo4j or external data required.
"""
import json
import numpy as np
import pytest

from ml.eval.models.graph_builder import build_similarity_graph


# ---------------------------------------------------------------------------
# Fixtures: temporary embedding data files
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_embeddings_10(tmp_path):
    """Create temp embeddings.npy (10 nodes, 8 dims) and embedding_index.json."""
    np.random.seed(42)
    embeddings = np.random.randn(10, 8).astype(np.float32)

    emb_path = tmp_path / "embeddings.npy"
    index_path = tmp_path / "embedding_index.json"

    np.save(str(emb_path), embeddings)

    # Build a deterministic similarity structure: first few nodes cluster
    embedding_index = {}
    for i in range(10):
        embedding_index[f"frag_{i:04d}"] = i

    with open(str(index_path), "w") as f:
        json.dump(embedding_index, f)

    return {
        "emb_path": str(emb_path),
        "index_path": str(index_path),
    }


@pytest.fixture
def temp_embeddings_3(tmp_path):
    """Create temp embeddings with only 3 nodes (to test fewer-nodes-than-k)."""
    np.random.seed(42)
    embeddings = np.random.randn(3, 8).astype(np.float32)

    emb_path = tmp_path / "embeddings_3.npy"
    index_path = tmp_path / "embedding_index_3.json"

    np.save(str(emb_path), embeddings)

    embedding_index = {}
    for i in range(3):
        embedding_index[f"frag_{i:04d}"] = i

    with open(str(index_path), "w") as f:
        json.dump(embedding_index, f)

    return {
        "emb_path": str(emb_path),
        "index_path": str(index_path),
    }


@pytest.fixture
def temp_embeddings_1(tmp_path):
    """Create temp embeddings with only 1 node (edge-case: single node)."""
    np.random.seed(42)
    embeddings = np.random.randn(1, 8).astype(np.float32)

    emb_path = tmp_path / "embeddings_1.npy"
    index_path = tmp_path / "embedding_index_1.json"

    np.save(str(emb_path), embeddings)

    embedding_index = {}
    for i in range(1):
        embedding_index[f"frag_0000"] = i

    with open(str(index_path), "w") as f:
        json.dump(embedding_index, f)

    return {
        "emb_path": str(emb_path),
        "index_path": str(index_path),
    }


@pytest.fixture
def temp_embeddings_low_sim(tmp_path):
    """Embeddings where all similarities are below a high threshold."""
    np.random.seed(123)
    embeddings = np.random.randn(10, 8).astype(np.float32)

    emb_path = tmp_path / "low_sim_emb.npy"
    index_path = tmp_path / "low_sim_index.json"

    np.save(str(emb_path), embeddings)

    embedding_index = {}
    for i in range(10):
        embedding_index[f"frag_{i:04d}"] = i

    with open(str(index_path), "w") as f:
        json.dump(embedding_index, f)

    return {
        "emb_path": str(emb_path),
        "index_path": str(index_path),
    }


# ---------------------------------------------------------------------------
# Normal cases
# ---------------------------------------------------------------------------


class TestBuildSimilarityGraphNormal:
    """build_similarity_graph with valid data."""

    def test_returns_edge_index_and_scores(self, temp_embeddings_10):
        """Must return four-element tuple of correct types."""
        fragrance_ids = [f"frag_{i:04d}" for i in range(10)]
        result = build_similarity_graph(
            fragrance_ids=fragrance_ids,
            embeddings_path=temp_embeddings_10["emb_path"],
            embedding_index_path=temp_embeddings_10["index_path"],
            k=3,
            threshold=0.0,
        )

        edge_index, edge_scores, node_id_to_idx, idx_to_node_id = result

        assert isinstance(edge_index, np.ndarray)
        assert edge_index.dtype == np.int64
        assert edge_index.shape[0] == 2  # always [2, num_edges]

        assert isinstance(edge_scores, np.ndarray)
        assert edge_scores.dtype == np.float32
        assert edge_scores.shape[0] == edge_index.shape[1]

        assert isinstance(node_id_to_idx, dict)
        assert isinstance(idx_to_node_id, dict)
        assert len(node_id_to_idx) == 10

    def test_edges_are_undirected_and_deduplicated(self, temp_embeddings_10):
        """Edges must be stored once per pair (i < neighbor_idx)."""
        fragrance_ids = [f"frag_{i:04d}" for i in range(10)]
        edge_index, _, _, _ = build_similarity_graph(
            fragrance_ids=fragrance_ids,
            embeddings_path=temp_embeddings_10["emb_path"],
            embedding_index_path=temp_embeddings_10["index_path"],
            k=3,
            threshold=0.0,
        )

        # Check no duplicate edges
        edge_set = set()
        for i in range(edge_index.shape[1]):
            u, v = int(edge_index[0, i]), int(edge_index[1, i])
            # Must satisfy i < neighbor_idx constraint
            assert u < v, f"Edge ({u}, {v}) violates undirected dedup constraint"
            edge_set.add((u, v))

        assert len(edge_set) == edge_index.shape[1], "Duplicate edges found"

    def test_node_id_to_idx_mapping_correct(self, temp_embeddings_10):
        """node_id_to_idx must correctly map fragrance IDs to local indices."""
        fragrance_ids = [f"frag_{i:04d}" for i in range(10)]
        _, _, node_id_to_idx, _ = build_similarity_graph(
            fragrance_ids=fragrance_ids,
            embeddings_path=temp_embeddings_10["emb_path"],
            embedding_index_path=temp_embeddings_10["index_path"],
            k=3,
            threshold=0.0,
        )

        for i, fid in enumerate(fragrance_ids):
            assert node_id_to_idx[fid] == i

    def test_idx_to_node_id_is_inverse(self, temp_embeddings_10):
        """idx_to_node_id must be the inverse of node_id_to_idx."""
        fragrance_ids = [f"frag_{i:04d}" for i in range(10)]
        _, _, node_id_to_idx, idx_to_node_id = build_similarity_graph(
            fragrance_ids=fragrance_ids,
            embeddings_path=temp_embeddings_10["emb_path"],
            embedding_index_path=temp_embeddings_10["index_path"],
            k=3,
            threshold=0.0,
        )

        for i in range(10):
            idx = node_id_to_idx[idx_to_node_id[i]]
            assert idx == i


# ---------------------------------------------------------------------------
# Edge case: fewer nodes than k
# ---------------------------------------------------------------------------


class TestFewerNodesThanK:
    """When there are fewer nodes than k, the function must reduce k gracefully."""

    def test_three_nodes_with_k_10_reduces_k(self, temp_embeddings_3):
        """With 3 nodes and k=10, effective k must be min(10, 3-1) = 2."""
        fragrance_ids = [f"frag_{i:04d}" for i in range(3)]
        edge_index, edge_scores, _, _ = build_similarity_graph(
            fragrance_ids=fragrance_ids,
            embeddings_path=temp_embeddings_3["emb_path"],
            embedding_index_path=temp_embeddings_3["index_path"],
            k=10,
            threshold=0.0,
        )

        # With 3 nodes, effective_k = min(10, 2) = 2
        # Complete undirected edges among 3 nodes: at most 3 edges
        assert edge_index.shape[1] <= 3
        # All nodes should have at least one edge (since threshold=0.0)
        assert edge_index.shape[1] > 0

    def test_two_nodes_with_k_10(self, tmp_path):
        """Exactly 2 nodes with k=10: effective_k = 1, should get 1 edge with negative threshold."""
        np.random.seed(42)
        # Use identical features to guarantee high similarity
        embeddings = np.ones((2, 8), dtype=np.float32)

        emb_path = tmp_path / "two_emb.npy"
        index_path = tmp_path / "two_index.json"

        np.save(str(emb_path), embeddings)
        with open(str(index_path), "w") as f:
            json.dump({"frag_0000": 0, "frag_0001": 1}, f)

        edge_index, edge_scores, _, _ = build_similarity_graph(
            fragrance_ids=["frag_0000", "frag_0001"],
            embeddings_path=str(emb_path),
            embedding_index_path=str(index_path),
            k=10,
            threshold=-1.0,  # ensure edge passes even with random similarity
        )

        # With identical features, cosine similarity = 1.0, so edge must exist
        assert edge_index.shape[1] == 1
        assert edge_scores.shape[0] == 1


# ---------------------------------------------------------------------------
# Edge case: single node
# ---------------------------------------------------------------------------


class TestSingleNode:
    """Single node must return empty edge_index."""

    def test_single_node_returns_empty_edge_index(self, temp_embeddings_1):
        """With only 1 node, must return empty (2,0) edge_index."""
        edge_index, edge_scores, node_id_to_idx, idx_to_node_id = build_similarity_graph(
            fragrance_ids=["frag_0000"],
            embeddings_path=temp_embeddings_1["emb_path"],
            embedding_index_path=temp_embeddings_1["index_path"],
            k=3,
            threshold=0.0,
        )

        assert edge_index.shape == (2, 0), f"Expected (2,0), got {edge_index.shape}"
        assert edge_scores.shape == (0,), f"Expected (0,), got {edge_scores.shape}"
        assert len(node_id_to_idx) == 1
        assert len(idx_to_node_id) == 1

    def test_single_node_still_returns_mappings(self, temp_embeddings_1):
        """Even with 1 node, the index mappings must be correct."""
        _, _, node_id_to_idx, idx_to_node_id = build_similarity_graph(
            fragrance_ids=["frag_0000"],
            embeddings_path=temp_embeddings_1["emb_path"],
            embedding_index_path=temp_embeddings_1["index_path"],
            k=3,
            threshold=0.0,
        )

        assert node_id_to_idx == {"frag_0000": 0}
        assert idx_to_node_id == {0: "frag_0000"}


# ---------------------------------------------------------------------------
# Edge case: no valid IDs
# ---------------------------------------------------------------------------


class TestNoValidIds:
    """When no fragrance IDs exist in the embedding index, must return empty."""

    def test_nonexistent_ids_returns_empty(self, temp_embeddings_10):
        """If no fragrance_id matches the index, must return empty (2,0) edge_index."""
        edge_index, edge_scores, node_id_to_idx, idx_to_node_id = build_similarity_graph(
            fragrance_ids=["ghost_1", "ghost_2", "ghost_3"],
            embeddings_path=temp_embeddings_10["emb_path"],
            embedding_index_path=temp_embeddings_10["index_path"],
            k=3,
            threshold=0.0,
        )

        assert edge_index.shape == (2, 0)
        assert edge_scores.shape == (0,)
        assert node_id_to_idx == {}
        assert idx_to_node_id == {}

    def test_partial_valid_ids(self, temp_embeddings_10):
        """Some valid and some invalid IDs must only use valid ones."""
        fragrance_ids = ["frag_0000", "frag_0001", "ghost_1", "frag_0002"]
        edge_index, edge_scores, node_id_to_idx, idx_to_node_id = build_similarity_graph(
            fragrance_ids=fragrance_ids,
            embeddings_path=temp_embeddings_10["emb_path"],
            embedding_index_path=temp_embeddings_10["index_path"],
            k=2,
            threshold=0.0,
        )

        assert len(node_id_to_idx) == 3  # only 3 valid nodes
        assert "ghost_1" not in node_id_to_idx
        assert edge_index.shape[1] > 0


# ---------------------------------------------------------------------------
# Edge case: threshold filtering
# ---------------------------------------------------------------------------


class TestThresholdFiltering:
    """Edges below the similarity threshold must be excluded."""

    def test_high_threshold_filters_all_edges(self, temp_embeddings_low_sim):
        """With threshold=0.99, random embeddings should have no edges passing."""
        fragrance_ids = [f"frag_{i:04d}" for i in range(10)]
        edge_index, edge_scores, _, _ = build_similarity_graph(
            fragrance_ids=fragrance_ids,
            embeddings_path=temp_embeddings_low_sim["emb_path"],
            embedding_index_path=temp_embeddings_low_sim["index_path"],
            k=3,
            threshold=0.99,
        )

        # Random embeddings are unlikely to have similarity > 0.99
        assert edge_index.shape[1] == 0
        assert edge_scores.shape[0] == 0

    def test_negative_threshold_includes_all_edges(self, temp_embeddings_10):
        """With threshold=-1.0, all KNN edges should pass."""
        fragrance_ids = [f"frag_{i:04d}" for i in range(10)]
        edge_index_low, _, _, _ = build_similarity_graph(
            fragrance_ids=fragrance_ids,
            embeddings_path=temp_embeddings_10["emb_path"],
            embedding_index_path=temp_embeddings_10["index_path"],
            k=3,
            threshold=-1.0,
        )

        edge_index_high, _, _, _ = build_similarity_graph(
            fragrance_ids=fragrance_ids,
            embeddings_path=temp_embeddings_10["emb_path"],
            embedding_index_path=temp_embeddings_10["index_path"],
            k=3,
            threshold=0.99,
        )

        # Lower threshold must produce at least as many edges
        assert edge_index_low.shape[1] >= edge_index_high.shape[1]


# ---------------------------------------------------------------------------
# Edge case: empty fragrance_ids
# ---------------------------------------------------------------------------


class TestEmptyFragranceIds:
    """Empty fragrance_ids list must not crash."""

    def test_empty_id_list_returns_empty(self, temp_embeddings_10):
        """Empty fragrance_ids must produce empty (2,0) edge_index."""
        edge_index, edge_scores, node_id_to_idx, idx_to_node_id = build_similarity_graph(
            fragrance_ids=[],
            embeddings_path=temp_embeddings_10["emb_path"],
            embedding_index_path=temp_embeddings_10["index_path"],
            k=3,
            threshold=0.0,
        )

        assert edge_index.shape == (2, 0)
        assert edge_scores.shape == (0,)
        assert node_id_to_idx == {}
        assert idx_to_node_id == {}


# ---------------------------------------------------------------------------
# Determinism check
# ---------------------------------------------------------------------------


class TestDeterminism:
    """build_similarity_graph must be deterministic given same inputs."""

    def test_deterministic_output(self, temp_embeddings_10):
        """Two calls with same inputs must produce identical edge_index."""
        fragrance_ids = [f"frag_{i:04d}" for i in range(10)]

        result1 = build_similarity_graph(
            fragrance_ids=fragrance_ids,
            embeddings_path=temp_embeddings_10["emb_path"],
            embedding_index_path=temp_embeddings_10["index_path"],
            k=3,
            threshold=0.0,
        )

        result2 = build_similarity_graph(
            fragrance_ids=fragrance_ids,
            embeddings_path=temp_embeddings_10["emb_path"],
            embedding_index_path=temp_embeddings_10["index_path"],
            k=3,
            threshold=0.0,
        )

        np.testing.assert_array_equal(result1[0], result2[0])
        np.testing.assert_array_equal(result1[1], result2[1])
