"""GraphSAGE Preference Initialization Service (Phase 7, M1).

Loads precomputed Jaccard embedding artifacts at startup, validates them,
and holds embeddings in memory for downstream centroid + KNN operations.
No torch, no checkpoint, no model inference, no forward pass.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GSEmbeddingHealth:
    """Mutable health snapshot updated after initialization attempt."""

    initialized: bool = False
    shape: tuple[int, int] | None = None
    num_nodes: int = 0
    normalized: bool = False
    has_nan: bool = False
    has_inf: bool = False
    duplicate_ids: bool = False
    metadata: dict[str, Any] | None = None
    errors: list[str] | None = None


class GraphSAGEService:
    """In-memory cache of Jaccard GraphSAGE embeddings.

    Responsibilities (M1):
    - Load node_embeddings_jaccard.npy
    - Load node_ids_jaccard.json
    - Load metadata.json
    - Validate all artifacts at startup (10 checks)
    - Expose health state for /health endpoint

    Responsibilities (M2):
    - Weighted centroid computation from seed embeddings
    - Cosine-similarity KNN retrieval
    - Centroid disagreement instrumentation

    No checkpoint loading, no model inference, no torch runtime dependency.
    """

    def __init__(self) -> None:
        self._embeddings: np.ndarray | None = None
        self._node_ids: list[str] | None = None
        self._id_to_idx: dict[str, int] | None = None
        self._metadata: dict[str, Any] | None = None
        self._health: GSEmbeddingHealth = GSEmbeddingHealth()

    # -- Public accessors ---------------------------------------------------

    @property
    def embeddings(self) -> np.ndarray | None:
        return self._embeddings

    @property
    def node_ids(self) -> list[str] | None:
        return self._node_ids

    @property
    def metadata(self) -> dict[str, Any] | None:
        return self._metadata

    @property
    def health(self) -> GSEmbeddingHealth:
        return self._health

    # -- Initialisation guard -----------------------------------------------

    def _require_initialized(self) -> None:
        """Raise RuntimeError if the embedding cache is not ready."""
        if not self._health.initialized:
            raise RuntimeError(
                "GraphSAGE: cache not initialised — call initialize() first"
            )
        if self._embeddings is None:
            raise RuntimeError(
                "GraphSAGE: cache not initialised — embeddings are None"
            )
        if self._node_ids is None:
            raise RuntimeError(
                "GraphSAGE: cache not initialised — node IDs are None"
            )

    # -- Initialisation -----------------------------------------------------

    def initialize(self) -> bool:
        """Load and validate all embedding artifacts at startup.

        Performs 10 validation checks:
          1. node_embeddings_jaccard.npy exists
          2. node_ids_jaccard.json exists
          3. metadata.json exists
          4. shape == [N, 64]
          5. len(node_ids) == N
          6. no duplicate IDs
          7. no NaN in embeddings
          8. no Inf in embeddings
          9. all rows L2-unit-normalised (≈1.0)
         10. metadata loads successfully

        Returns True iff every check passes.
        """
        errors: list[str] = []
        base_dir = os.getcwd()

        emb_path = os.path.join(base_dir, settings.gs_embeddings_path)
        ids_path = os.path.join(base_dir, settings.gs_node_ids_path)
        meta_path = os.path.join(base_dir, settings.gs_metadata_path)

        # --- Checks 1-3: file existence -----------------------------------
        if not os.path.isfile(emb_path):
            errors.append(f"GS embeddings file not found: {emb_path}")
        if not os.path.isfile(ids_path):
            errors.append(f"GS node-IDs file not found: {ids_path}")
        if not os.path.isfile(meta_path):
            errors.append(f"GS metadata file not found: {meta_path}")

        if errors:
            self._health.errors = errors
            logger.error("GraphSAGE: artifact file checks failed — %s", "; ".join(errors))
            return False

        try:
            embeddings = np.load(emb_path)
        except Exception as exc:
            errors.append(f"Failed to load embeddings: {exc}")
            self._health.errors = errors
            logger.error("GraphSAGE: %s", errors[-1])
            return False

        # --- Check 4: shape -----------------------------------------------
        if embeddings.ndim != 2 or embeddings.shape[1] != 64:
            errors.append(
                f"Embeddings shape is {embeddings.shape}, expected [N, 64]"
            )

        # --- Check 7: NaN -------------------------------------------------
        if np.any(np.isnan(embeddings)):
            errors.append("Embeddings contain NaN values")
            self._health.has_nan = True

        # --- Check 8: Inf -------------------------------------------------
        if np.any(np.isinf(embeddings)):
            errors.append("Embeddings contain Inf values")
            self._health.has_inf = True

        # --- Check 9: L2 normalisation ------------------------------------
        norms = np.linalg.norm(embeddings, axis=1)
        if bool(np.allclose(norms, 1.0, atol=1e-3)):
            self._health.normalized = True
        else:
            actual_range = (float(norms.min()), float(norms.max()))
            errors.append(
                f"Embeddings not L2-unit-normalised (norm range {actual_range})"
            )

        if errors:
            self._health.errors = errors
            logger.error("GraphSAGE: embedding validation failed — %s", "; ".join(errors))
            return False

        # --- Load node IDs ------------------------------------------------
        try:
            with open(ids_path, encoding="utf-8") as f:
                node_ids: list[str] = json.load(f)
        except Exception as exc:
            errors.append(f"Failed to load node IDs: {exc}")
            self._health.errors = errors
            logger.error("GraphSAGE: %s", errors[-1])
            return False

        N = int(embeddings.shape[0])

        # --- Check 5: length match ----------------------------------------
        if len(node_ids) != N:
            errors.append(
                f"node_ids count ({len(node_ids)}) != embeddings rows ({N})"
            )

        # --- Check 6: duplicate IDs ---------------------------------------
        if len(set(node_ids)) != len(node_ids):
            errors.append("node_ids contain duplicate values")
            self._health.duplicate_ids = True

        if errors:
            self._health.errors = errors
            logger.error("GraphSAGE: node-ID validation failed — %s", "; ".join(errors))
            return False

        # --- Check 10: metadata -------------------------------------------
        try:
            with open(meta_path, encoding="utf-8") as f:
                metadata: dict[str, Any] = json.load(f)
        except Exception as exc:
            errors.append(f"Failed to load metadata: {exc}")
            self._health.errors = errors
            logger.error("GraphSAGE: %s", errors[-1])
            return False

        # -- Success --------------------------------------------------------
        self._embeddings = embeddings
        self._node_ids = node_ids
        self._id_to_idx = {fid: i for i, fid in enumerate(node_ids)}
        self._metadata = metadata
        self._health.initialized = True
        self._health.shape = tuple(embeddings.shape)
        self._health.num_nodes = N
        self._health.metadata = metadata

        norm_status = "L2-unit" if self._health.normalized else "NOT normalized"
        logger.info(
            "GraphSAGE: cache initialised — %d items, shape %s, %s",
            N,
            embeddings.shape,
            norm_status,
        )
        return True

    # -- Seed resolution ----------------------------------------------------

    def _resolve_seed_ids(
        self, seed_ids: list[str]
    ) -> tuple[list[int], set[str]]:
        """Resolve fragrance IDs to embedding row indices.

        Uses the cached *self._id_to_idx* mapping built during
        *initialize()*.

        Returns (indices, valid_ids_set). Logs a warning for any ID
        that does not appear in the embedding index.

        An empty *indices* list signals that *seed_ids* contains no
        known fragrances — callers should raise or fall back.
        """
        indices: list[int] = []
        valid_ids: set[str] = set()
        for sid in seed_ids:
            idx = self._id_to_idx.get(sid) if self._id_to_idx else None
            if idx is not None:
                indices.append(idx)
                valid_ids.add(sid)
            else:
                logger.warning(
                    "GraphSAGE: seed ID %s not found in embedding index", sid,
                )
        return indices, valid_ids

    # -- User vector (primary) ----------------------------------------------

    def compute_user_vector(
        self,
        item_ratings: list[tuple[str, float]],
    ) -> np.ndarray:
        """Compute an L2‑normalised rating‑weighted user vector.

        u = mean(rating_weight × item_embedding) for all rated items.
        Each embedding is weighted by its rating normalised to [0.1, 1.0].

        Parameters
        ----------
        item_ratings : list[tuple[str, float]]
            (fragrance_id, rating 1‑10) pairs from the user's quiz responses.

        Returns
        -------
        np.ndarray, shape (64,), dtype float64
            L2‑unit‑normalised user preference vector.

        Raises
        ------
        RuntimeError
            If the embedding cache has not been initialised.
        ValueError
            If *item_ratings* is empty or no IDs resolve.
        """
        self._require_initialized()

        if not item_ratings:
            raise ValueError("compute_user_vector: item_ratings must not be empty")

        weighted_sum: np.ndarray | None = None
        total_weight = 0.0

        for fid, rating in item_ratings:
            idx = self._id_to_idx.get(fid) if self._id_to_idx else None
            if idx is None:
                logger.warning(
                    "GraphSAGE: user-vector ID %s not found in embedding index", fid,
                )
                continue
            emb = self._embeddings[idx]
            weight = rating / 10.0  # normalise [1, 10] → [0.1, 1.0]
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

    # -- Weighted centroid (M2) ---------------------------------------------

    def compute_centroid(
        self,
        seed_ids: list[str],
        weights: list[float] | None = None,
    ) -> np.ndarray:
        """Compute an L2‑normalised weighted centroid from *seed_ids*.

        Parameters
        ----------
        seed_ids : list[str]
            Fragrance IDs whose embeddings form the centroid.  IDs not
            present in the embedding index are silently skipped.
        weights : list[float] | None
            Per‑seed weight (e.g. quiz rating).  When *None* every
            resolved seed receives equal weight.

        Returns
        -------
        np.ndarray, shape (64,), dtype float64
            L2‑unit‑normalised centroid vector.

        Raises
        ------
        RuntimeError
            If the embedding cache has not been initialised.
        ValueError
            If *seed_ids* is empty, none of the IDs resolve, *weights*
            length mismatches *seed_ids*, or the effective weight sum
            is zero.
        """
        self._require_initialized()

        if not seed_ids:
            raise ValueError("compute_centroid: seed_ids must not be empty")

        indices, _valid_ids = self._resolve_seed_ids(seed_ids)
        if not indices:
            raise ValueError(
                "compute_centroid: none of the provided seed IDs exist "
                "in the embedding index"
            )

        seed_embs = self._embeddings[indices]  # [M, 64]

        if weights is not None:
            if len(weights) != len(seed_ids):
                raise ValueError(
                    f"compute_centroid: weights length ({len(weights)}) "
                    f"does not match seed_ids length ({len(seed_ids)})"
                )
            valid_weights = np.array(
                [w for sid, w in zip(seed_ids, weights, strict=True)
                 if sid in _valid_ids],
                dtype=np.float64,
            )
        else:
            valid_weights = np.ones(len(indices), dtype=np.float64)

        w_sum = np.sum(valid_weights)
        if w_sum <= 0:
            raise ValueError(
                "compute_centroid: weight sum is zero — "
                "cannot compute centroid"
            )

        centroid = np.dot(valid_weights, seed_embs) / w_sum  # [64]

        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm

        return centroid

    # -- Cosine-similarity KNN (M2) ----------------------------------------

    def knn_search(
        self,
        centroid: np.ndarray,
        top_k: int = 200,
        exclude_ids: list[str] | None = None,
    ) -> list[dict[str, float]]:
        """Return the *top_k* nearest neighbours of *centroid*.

        Similarity is measured via cosine similarity (inner product with
        pre‑normalised embeddings).  Results are sorted descending by
        score.  IDs listed in *exclude_ids* are filtered out.

        Parameters
        ----------
        centroid : np.ndarray, shape (64,)
            Query vector (should already be L2‑normalised).
        top_k : int
            Maximum number of results to return.
        exclude_ids : list[str] | None
            Fragrance IDs to omit from results (typically the seed IDs
            that generated the centroid).

        Returns
        -------
        list[dict[str, float]]
            Each entry: ``{"id": <fragrance ID>, "score": <cosine sim>}``.
            Empty list if the cache is not initialised or *centroid*
            is malformed.

        Raises
        ------
        RuntimeError
            If the embedding cache has not been initialised.
        ValueError
            If *centroid* is not a 1‑D array of length 64.

        Execution time
        --------------
        O(N * 64) for the dot product + O(N log N) for argsort.
        With N ≈ 4 559 this completes in <10 ms.
        """
        self._require_initialized()

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

    # -- Disagreement instrumentation (M2) ----------------------------------

    def log_disagreement(
        self,
        seed_ids: list[str],
        weights: list[float] | None = None,  # noqa: ARG002
    ) -> dict[str, float | int]:
        """Compute and log pairwise cosine distance among *seed_ids*.

        The disagreement score is a proxy for how spread out the user's
        preferences are.  Higher mean pairwise distance → more diverse
        taste (harder to centroid accurately).

        Results are logged at INFO and returned as a dict for optional
        programmatic use by the Phase 8 dispatcher.

        Returns
        -------
        dict[str, float | int]
            ``{"mean": float, "min": float, "max": float, "std": float,
            "count": int}``.  When fewer than 2 seeds are provided every
            metric is 0.0 and count reflects the number of resolved seeds.

        Raises
        ------
        RuntimeError
            If the embedding cache has not been initialised.

        Execution time
        --------------
        O(M² * 64) where M = len(seed_ids).  With M ≤ 20 this is
        effectively instant.
        """
        self._require_initialized()

        indices, _valid_ids = self._resolve_seed_ids(seed_ids)

        count = len(indices)
        if count < 2:
            logger.info(
                "GraphSAGE: disagreement — too few seeds (%d), skipping",
                count,
            )
            return {"mean": 0.0, "min": 0.0, "max": 0.0, "std": 0.0,
                    "count": count}

        seed_embs = self._embeddings[indices]  # [M, 64]
        sim_matrix = np.dot(seed_embs, seed_embs.T)  # [M, M]
        np.clip(sim_matrix, -1.0, 1.0, out=sim_matrix)
        dist_matrix = 1.0 - sim_matrix

        # Upper triangle excluding diagonal
        iu = np.triu_indices(count, k=1)
        pairwise_dists = dist_matrix[iu]

        if pairwise_dists.size == 0:
            return {"mean": 0.0, "min": 0.0, "max": 0.0, "std": 0.0,
                    "count": count}

        stats: dict[str, float | int] = {
            "mean": float(np.mean(pairwise_dists)),
            "min": float(np.min(pairwise_dists)),
            "max": float(np.max(pairwise_dists)),
            "std": float(np.std(pairwise_dists)),
            "count": count,
        }

        logger.info(
            "GraphSAGE: disagreement — mean=%.4f min=%.4f max=%.4f "
            "std=%.4f (seeds=%d)",
            stats["mean"], stats["min"], stats["max"], stats["std"],
            count,
        )
        return stats


# Module-level singleton consumed by lifespan and downstream consumers.
gs_service = GraphSAGEService()
