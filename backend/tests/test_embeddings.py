"""Embedding service tests against the real npy artifacts."""

import numpy as np

from app.services.catalog import get_catalog
from app.services.embeddings import gs_service


def test_initialize_true():
    assert gs_service.initialize() is True
    assert gs_service.initialized is True


def test_compute_user_vector_and_knn():
    catalog = get_catalog()
    ids = [str(catalog[0]["id"]), str(catalog[1]["id"])]

    vec = gs_service.compute_user_vector([(ids[0], 8.0), (ids[1], 5.0)])
    assert vec.shape == (64,)
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-6

    knn = gs_service.knn_search(vec, top_k=5)
    assert isinstance(knn, list) and len(knn) == 5
    assert all(set(item) == {"id", "score"} for item in knn)
    assert all(knn[i]["score"] >= knn[i + 1]["score"] for i in range(len(knn) - 1))