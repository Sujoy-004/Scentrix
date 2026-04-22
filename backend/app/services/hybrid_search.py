import logging
import os
from typing import Any

from neo4j import GraphDatabase
import numpy as np
from pinecone import Pinecone

from app.config import settings
from app.services.catalog import load_recommendation_catalog

logger = logging.getLogger(__name__)

# Module-level cache for text embeddings to prevent re-computation
_catalog_embeddings_cache: np.ndarray | None = None
_is_hydrating: bool = False

class HybridRecommender:
    """Unified 'Aetheric' DNA Recommender (Text + Graph Fusion).

    Targets 300ms SLA by using Vector Search for top-100 candidates
    followed by Graph-based 'Genetic Match' reranking.
    """

    def __init__(self):
        # 1. Vector Client
        self.pc = Pinecone(api_key=settings.pinecone_api_key) if settings.pinecone_api_key else None
        self.text_index = self.pc.Index(settings.pinecone_index_name) if self.pc else None
        self.graph_index = self.pc.Index("Scentrix-graph") if self.pc else None

        # 2. Graph Client
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            try:
                from ml.models.text_encoder import TextEncoder
                self._encoder = TextEncoder()
                logger.info("Neural Engine: ML Encoder activated.")
            except Exception as e:
                logger.error(f"Neural Engine: Failed to activate ML Encoder: {e}")
                self._encoder = None
        return self._encoder

    def _get_item_text(self, item: dict[str, Any]) -> str:
        parts = [
            str(item.get("name", "")),
            str(item.get("brand", "")),
            str(item.get("description", "")),
            " ".join(item.get("top_notes", []) or []),
            " ".join(item.get("accords", []) or []),
        ]
        return " ".join(filter(None, parts))

    def warmup(self):
        """Pre-cache catalog embeddings at startup."""
        global _catalog_embeddings_cache, _is_hydrating

        if _catalog_embeddings_cache is not None or _is_hydrating:
            return

        _is_hydrating = True
        try:
            catalog = load_recommendation_catalog()
            encoder = self._get_encoder()

            if catalog and encoder:
                # RAM Safety: Limit in-memory cache to top 1000 items in production
                # Full catalog search is handled via Pinecone.
                warmup_limit = 1000 if os.getenv("RUNNING_IN_DOCKER") else len(catalog)
                target_items = catalog[:warmup_limit]

                logger.info(f"Neural Engine: pre-caching {len(target_items)} fragrances (Limit: {warmup_limit}) ...")
                texts = [self._get_item_text(item) for item in target_items]
                embeddings = encoder.generate_embeddings(texts)
                _catalog_embeddings_cache = np.array(embeddings)
                logger.info(f"Neural Engine: Partial catalog ({len(target_items)} items) indexed and ready.")
        except Exception as e:
            logger.error(f"Neural Engine: Warmup failed: {e}")
        finally:
            _is_hydrating = False

    def _query_vector_dna(
        self, user_vec: list[float], limit: int = 100, use_graph_dna: bool = True
    ) -> list[dict[str, Any]]:
        """Phase 1: High-recall dual-vector search (Text DNA + Graph DNA)."""
        candidates_map: dict[str, dict[str, Any]] = {}

        # 1. Text DNA Search (Pinecone)
        if self.text_index:
            try:
                res = self.text_index.query(vector=user_vec, top_k=limit, include_metadata=True)
                for m in res.matches:
                    candidates_map[m.id] = {
                        "id": m.id,
                        "text_score": m.score,
                        "graph_score": 0.0,
                        "metadata": m.metadata or {},
                    }
            except Exception as e:
                logger.warning(f"Text index query failed: {e}")

        # 2. Graph DNA Search (Pinecone - GraphSAGE Embeddings)
        if use_graph_dna and self.graph_index:
            try:
                # We use the same user vector (assuming joint embedding space or similar dimension)
                # In a true Scenter-GNN setup, we might need a separate Graph-Encoder pass.
                res = self.graph_index.query(vector=user_vec, top_k=limit, include_metadata=False)
                for m in res.matches:
                    if m.id in candidates_map:
                        candidates_map[m.id]["graph_score"] = m.score
                    else:
                        candidates_map[m.id] = {
                            "id": m.id,
                            "text_score": 0.0,
                            "graph_score": m.score,
                            "metadata": {},  # Metadata will be hydrated via local catalog if missing
                        }
            except Exception as e:
                logger.warning(f"Graph index query failed: {e}")

        # 3. Local Semantic Fallback (if no results from Pinecone)
        if not candidates_map:
            global _catalog_embeddings_cache, _is_hydrating

            if not _is_hydrating and _catalog_embeddings_cache is not None:
                catalog = load_recommendation_catalog()
                user_vec_np = np.array(user_vec)
                similarities = np.dot(_catalog_embeddings_cache, user_vec_np)
                top_indices = np.argsort(similarities)[-limit:][::-1]
                for idx in top_indices:
                    item = catalog[idx]
                    candidates_map[item["id"]] = {
                        "id": item["id"],
                        "text_score": float(similarities[idx]),
                        "graph_score": 0.0,
                        "metadata": item,
                    }

        return list(candidates_map.values())

    def _rerank_genetic_match(
        self, candidate_ids: list[str], user_rated_ids: list[str]
    ) -> dict[str, dict[str, float]]:
        """Phase 2: High-precision graph reranking using genetic distance."""
        if not user_rated_ids or not candidate_ids:
            return {}

        try:
            with self.driver.session() as session:
                # Optimized Genetic Query: Checks shared Notes, Accords, and Family
                query = """
                MATCH (rec:Fragrance) WHERE rec.id IN $cids
                MATCH (seed:Fragrance) WHERE seed.id IN $sids

                OPTIONAL MATCH (rec)-[:HAS_NOTE]->(n:Note)<-[:HAS_NOTE]-(seed)
                OPTIONAL MATCH (rec)-[:BELONGS_TO_ACCORD]->(a:Accord)<-[:BELONGS_TO_ACCORD]-(seed)
                OPTIONAL MATCH (rec)-[:IN_FAMILY]->(f:Family)<-[:IN_FAMILY]-(seed)

                WITH rec.id as id,
                     count(distinct n) as shared_notes,
                     count(distinct a) as shared_accords,
                     count(distinct f) as shared_family

                RETURN id, shared_notes, shared_accords, shared_family
                """
                result = session.run(query, {"cids": candidate_ids, "sids": user_rated_ids})
                return {
                    r["id"]: {
                        "notes": r["shared_notes"],
                        "accords": r["shared_accords"],
                        "family": r["shared_family"],
                    }
                    for r in result
                }
        except Exception as e:
            logger.error(f"Neo4j reranking failed: {e}")
            return {}

    def get_recommendations(
        self, user_profile_vec: list[float], user_seed_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Main entry point for 300ms Adaptive Discovery."""
        # Step 1: Candidate Selection (Dual Vector DNA)
        candidates = self._query_vector_dna(user_profile_vec, limit=60)
        if not candidates:
            return []

        c_ids = [c["id"] for c in candidates]

        # Step 2: Genetic Reranking (Graph)
        genetic_data = self._rerank_genetic_match(c_ids, user_seed_ids)

        # Step 3: Reciprocal Rank Fusion (RRF) & Metadata Hydration
        from app.routers.recommendations import load_recommendation_catalog

        catalog_map = {item["id"]: item for item in load_recommendation_catalog()}

        refined = []
        for c in candidates:
            c_id = c["id"]
            metadata = c["metadata"] or catalog_map.get(c_id, {})

            # Genetic Weights
            g = genetic_data.get(c_id, {"notes": 0, "accords": 0, "family": 0})
            genetic_score = (g["notes"] * 1.0) + (g["accords"] * 2.0) + (g["family"] * 3.0)
            genetic_normalized = min(genetic_score / 15.0, 1.0)

            # RRF / Hybrid Scalar Fusion: 40% Text Vibe + 40% Graph DNA + 20% Genetic Match
            hybrid_score = (
                (c["text_score"] * 0.4) + (c["graph_score"] * 0.4) + (genetic_normalized * 0.2)
            )

            # Generate reasoning string
            if genetic_score > 5:
                reason = "Deep Genetic Match (Shared Family & Accords)"
            elif g["notes"] > 0:
                reason = f"Genetic Spark ({g['notes']} shared notes)"
            elif c["graph_score"] > 0.8:
                reason = "Neural Discovery (GraphSAGE Structural Match)"
            else:
                reason = "Semantic Soulbound (Aetheric Text Vibe)"

            refined.append(
                {
                    "id": c_id,
                    "name": metadata.get("name", "Unknown"),
                    "brand": metadata.get("brand", "Unknown"),
                    "match_score": round(hybrid_score * 100, 1),
                    "reason": reason,
                    "top_accords": metadata.get("accords", [])[:3],
                    "top_notes": metadata.get("top_notes", [])[:3],
                }
            )

        refined.sort(key=lambda x: x["match_score"], reverse=True)
        return refined[:12]

    def close(self):
        self.driver.close()

recommender = HybridRecommender()
