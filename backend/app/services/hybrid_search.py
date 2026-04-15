import logging
import os
from typing import Any

import numpy as np
from neo4j import GraphDatabase
from pinecone import Pinecone

from app.config import settings

logger = logging.getLogger(__name__)


class HybridRecommender:
    """Unified 'Aetheric' DNA Recommender (Text + Graph Fusion).

    Targets 300ms SLA by using Vector Search for top-100 candidates
    followed by Graph-based 'Genetic Match' reranking.
    """

    def __init__(self):
        # 1. Vector Client
        pc_api_key = os.environ.get("PINECONE_API_KEY")
        self.pc = Pinecone(api_key=pc_api_key) if pc_api_key else None
        self.vector_index = self.pc.Index("scentscape-fragrances") if self.pc else None

        # 2. Graph Client
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )

    def _query_vector_dna(self, user_vec: list[float], limit: int = 100) -> list[dict[str, Any]]:
        """Phase 1: High-recall vector search (Pinecone with Local Fallback)."""
        # 1. External Production Service (Pinecone)
        if self.vector_index:
            try:
                res: Any = self.vector_index.query(
                    vector=user_vec, top_k=limit, include_metadata=True
                )
                return [
                    {"id": m.id, "score": m.score, "metadata": m.metadata or {}}
                    for m in res.matches
                ]
            except Exception as e:
                logger.warning(f"Pinecone query failed, attempting local fallback: {e}")

        # 2. Local Semantic Brain Fallback (High-Fidelity)
        from app.routers.recommendations import (  # noqa: E402
            _catalog_embeddings_cache,
            _is_hydrating,
            load_recommendation_catalog,
        )

        # If the engine is busy hydrating, we skip the slow local scan and return empty
        if _is_hydrating:
            logger.info("Neural Engine is hydrating; skipping local fallback.")
            return []

        catalog = load_recommendation_catalog()

        if _catalog_embeddings_cache is not None and catalog:
            # Vectorized Cosine Similarity in NumPy for O(N) performance
            candidates = []
            user_vec_np = np.array(user_vec)

            # Simple dot product since SentenceTransformers outputs unit vectors
            similarities = np.dot(_catalog_embeddings_cache, user_vec_np)

            # Get top K indices
            top_indices = np.argsort(similarities)[-limit:][::-1]

            for idx in top_indices:
                item = catalog[idx]
                candidates.append(
                    {"id": item.get("id"), "score": float(similarities[idx]), "metadata": item}
                )
            return candidates

        return []

    def _rerank_genetic_match(
        self, candidate_ids: list[str], user_rated_ids: list[str]
    ) -> dict[str, Any]:
        """Phase 2: High-precision graph reranking using genetic distance."""
        if not user_rated_ids:
            return {}

        try:
            with self.driver.session() as session:
                # We calculate 'Genetic Distance' based on shared notes/accords between candidates and user seeds.
                query = """
                MATCH (rec:Fragrance) WHERE rec.id IN $cids
                MATCH (seed:Fragrance) WHERE seed.id IN $sids
                MATCH (rec)-[:HAS_TOP_NOTE|HAS_MIDDLE_NOTE|HAS_BASE_NOTE]->(n:Note)<-[:HAS_TOP_NOTE|HAS_MIDDLE_NOTE|HAS_BASE_NOTE]-(seed)
                WITH rec, count(n) as shared_notes
                RETURN rec.id as id, shared_notes
                """
                result = session.run(query, {"cids": candidate_ids, "sids": user_rated_ids})
                return {r["id"]: r["shared_notes"] for r in result}
        except Exception as e:
            logger.error(f"Neo4j reranking failed: {e}")
            return {}

    def get_recommendations(
        self, user_profile_vec: list[float], user_seed_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Main entry point for 300ms Adaptive Discovery."""
        # Step 1: Candidate Selection (Vector ANN)
        try:
            candidates = self._query_vector_dna(user_profile_vec, limit=50)
            if not candidates:
                return []
            c_ids = [c["id"] for c in candidates]
        except Exception as e:
            logger.error(f"Vector search critical failure: {e}")
            return []

        # Step 2: Genetic Reranking (Graph)
        shared_note_counts = self._rerank_genetic_match(c_ids, user_seed_ids)

        # Step 3: Reciprocal Rank Fusion (RRF) / Hybrid Scalar Fusion
        refined = []
        for c in candidates:
            c_id = c["id"]
            shared_notes = shared_note_counts.get(c_id, 0)

            # Weighted Hybrid Score: 70% Vibe (Vector) + 30% Genetics (Graph)
            # Normalize shared notes (Assume 10 max shared notes for scaling)
            graph_boost = min(shared_notes / 5.0, 1.0)
            hybrid_score = (c["score"] * 0.7) + (graph_boost * 0.3)

            refined.append(
                {
                    "id": c_id,
                    "name": c["metadata"].get("name", "Unknown"),
                    "brand": c["metadata"].get("brand", "Unknown"),
                    "image_url": c["metadata"].get("image_url", ""),
                    "match_score": round(hybrid_score * 100, 1),
                    "reason": f"Shared Genetic Resonance ({shared_notes} notes)"
                    if shared_notes > 0
                    else "Semantic Soulbound Match",
                }
            )

        refined.sort(key=lambda x: x["match_score"], reverse=True)
        return refined[:12]

    def close(self):
        self.driver.close()


recommender = HybridRecommender()
