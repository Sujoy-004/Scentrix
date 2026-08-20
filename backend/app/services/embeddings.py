"""GraphSAGE embedding cache service (replaces gs_embeddings.py).

Loads precomputed Jaccard embedding artifacts from ``app/data`` and serves
user-vector + KNN lookups. numpy is optional at serving time: when it is
unavailable ``initialize()`` returns False and callers fall back to
popularity. No torch, no model inference, no forward pass.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"

_np: Any = None


def _get_numpy():
    """Lazily import numpy once; returns the module or None."""
    global _np
    if _np is None:
        try:
            import numpy as np

            _np = np
        except ImportError:
            _np = False
    return _np if _np is not False else None


class GraphSAGEService:
    """In-memory cache of Jaccard GraphSAGE embeddings (user-vector + KNN)."""

    def __init__(self) -> None:
        self.initialized = False
        self._embeddings: Any = None
        self._node_ids: list[str] | None = None
        self._id_to_idx: dict[str, int] | None = None

    # -- Initialisation guard -----------------------------------------------

    def _require_initialized(self) -> None:
        """Raise RuntimeError if the embedding cache is not ready."""
        if not self.initialized or self._embeddings is None or self._node_ids is None:
            raise RuntimeError(
                "GraphSAGE: cache not initialised — call initialize() first"
            )

    # -- Initialisation -----------------------------------------------------

    def initialize(self) -> bool:
        """Load and validate the embedding artifacts.

        Checks: files exist, shape [N, 64], dtype float32, no NaN/Inf,
        len(node_ids) == N, no duplicate IDs. Returns True iff every
        check passes and numpy is importable.
        """
        np = _get_numpy()
        if np is None:
            logger.error("GraphSAGE: numpy unavailable — embeddings disabled")
            self.initialized = False
            return False

        emb_path = _DATA_DIR / "node_embeddings_jaccard.npy"
        ids_path = _DATA_DIR / "node_ids_jaccard.json"
        if not emb_path.is_file() or not ids_path.is_file():
            logger.error(
                "GraphSAGE: artifact files not found in %s (missing: %s, %s)",
                _DATA_DIR,
                emb_path if not emb_path.is_file() else "",
                ids_path if not ids_path.is_file() else "",
            )
            self.initialized = False
            return False

        try:
            embeddings = np.load(emb_path)
            with open(ids_path, encoding="utf-8") as f:
                node_ids: list[str] = json.load(f)
        except Exception as exc:
            logger.error("GraphSAGE: failed to load artifacts — %s", exc)
            self.initialized = False
            return False

        ok = True
        if embeddings.ndim != 2 or embeddings.shape[1] != 64:
            logger.error(
                "GraphSAGE: shape is %s, expected [N, 64]",
                getattr(embeddings, "shape", None),
            )
            ok = False
        if embeddings.dtype != np.float32:
            logger.error("GraphSAGE: dtype is %s, expected float32", embeddings.dtype)
            ok = False
        if np.any(np.isnan(embeddings)):
            logger.error("GraphSAGE: embeddings contain NaN values")
            ok = False
        if np.any(np.isinf(embeddings)):
            logger.error("GraphSAGE: embeddings contain Inf values")
            ok = False

        N = int(embeddings.shape[0])
        if len(node_ids) != N:
            logger.error(
                "GraphSAGE: node_ids count (%d) != embeddings rows (%d)",
                len(node_ids),
                N,
            )
            ok = False
        if len(set(node_ids)) != len(node_ids):
            logger.error("GraphSAGE: node_ids contain duplicate values")
            ok = False

        if not ok:
            self.initialized = False
            return False

        self._embeddings = embeddings
        self._node_ids = node_ids
        self._id_to_idx = {fid: i for i, fid in enumerate(node_ids)}
        self.initialized = True
        logger.info(
            "GraphSAGE: cache initialised — %d items, shape %s", N, embeddings.shape
        )
        return True

    # -- User vector (primary) ----------------------------------------------

    def compute_user_vector(
        self,
        item_ratings: list[tuple[str, float]],
    ) -> Any:
        """Compute an L2-normalised rating-weighted user vector.

        u = sum(rating_weight * item_embedding) / sum(rating_weight), where
        rating_weight = rating / 10.0 (1-10 -> 0.1-1.0). The result is
        L2-unit-normalised.

        Raises ValueError if *item_ratings* is empty or none of the IDs
        resolve in the embedding index.
        """
        self._require_initialized()
        np = _get_numpy()

        if not item_ratings:
            raise ValueError("compute_user_vector: item_ratings must not be empty")

        weighted_sum = None
        total_weight = 0.0

        for fid, rating in item_ratings:
            idx = self._id_to_idx.get(fid)
            if idx is None:
                logger.warning(
                    "GraphSAGE: user-vector ID %s not found in embedding index", fid
                )
                continue
            emb = self._embeddings[idx]
            weight = rating / 10.0  # normalise [1, 10] -> [0.1, 1.0]
            if weighted_sum is None:
                weighted_sum = weight * emb
            else:
                weighted_sum += weight * emb
            total_weight += weight

        if weighted_sum is None or total_weight <= 0:
            raise ValueError(
                "compute_user_vector: none of the provided fragrance IDs exist "
                "in the embedding index"
            )

        u = weighted_sum / total_weight
        norm = np.linalg.norm(u)
        if norm > 0:
            u = u / norm

        return u

    # -- Cosine-similarity KNN ----------------------------------------------

    def knn_search(
        self,
        centroid: Any,
        top_k: int = 200,
        exclude_ids: list[str] | None = None,
    ) -> list[dict[str, float]]:
        """Return the *top_k* nearest neighbours of *centroid*.

        Similarity is cosine (inner product with pre-normalised embeddings).
        Results are sorted descending by score; *exclude_ids* are filtered
        out. Returns ``[{"id": str, "score": float}]``.
        """
        self._require_initialized()
        np = _get_numpy()

        if centroid.ndim != 1 or centroid.shape[0] != 64:
            raise ValueError(
                f"knn_search: expected (64,) centroid, got {centroid.shape}"
            )

        similarities = np.dot(self._embeddings, centroid)  # [N]

        top_indices = np.argsort(similarities)[::-1]

        exclude_set = set(exclude_ids or [])
        results: list[dict[str, float]] = []
        for idx in top_indices:
            fid = self._node_ids[idx]
            if fid in exclude_set:
                continue
            results.append({"id": fid, "score": float(similarities[idx])})
            if len(results) >= top_k:
                break

        return results


# Module-level singleton consumed by the dispatcher.
gs_service = GraphSAGEService()