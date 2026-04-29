# ruff: noqa
import logging
import os
import json
import psutil
from typing import Any

# SAFE MODE: Conditional numpy import
# SAFE MODE: Conditional imports for optional neural/graph drivers
try:
    import numpy as np
except (ImportError, Exception):
    np = None

try:
    from pinecone import Pinecone
except (ImportError, Exception):
    Pinecone = None

try:
    from neo4j import GraphDatabase
except (ImportError, Exception):
    GraphDatabase = None

from app.config import settings
from app.services.catalog import load_recommendation_catalog

logger = logging.getLogger(__name__)

# Module-level cache for text embeddings to prevent re-computation
_catalog_embeddings_cache = None
_is_hydrating: bool = False

def log_mem(stage):
    import psutil
    try:
        m = psutil.Process(os.getpid()).memory_info().rss / (1024 ** 2)
        logger.info(f"[MEM] {stage}: {m:.2f} MB")
    except Exception:
        pass


class HybridRecommender:
    """Unified Recommender with clean fallbacks for disconnected environments."""

    def __init__(self):
        # 1. Vector Client (Pinecone)
        self.pc = None
        self.text_index = None
        self.graph_index = None

        if Pinecone and settings.pinecone_api_key:
            try:
                self.pc = Pinecone(api_key=settings.pinecone_api_key)
                self.text_index = self.pc.Index(settings.pinecone_index_name)
                logger.info(f"Neural Engine: Connected to Text Index '{settings.pinecone_index_name}'")
            except Exception as e:
                logger.warning(f"Neural Engine: Vector indices unreachable: {e}")
                self.pc = None

        # 2. Graph Client (Neo4j)
        self.driver = None
        if GraphDatabase:
            try:
                self.driver = GraphDatabase.driver(
                    settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
                )
            except Exception as e:
                logger.warning(f"Neural Engine: Graph driver failed: {e}")
                self.driver = None
        self._encoder = None
        self._encoder_load_attempted = False

        # 3. Semantic Similarity (Precomputed)
        self.embeddings = None
        self.embedding_index = None
        self.semantic_enabled = False
        
        base_dir = os.getcwd()
        embeddings_path = os.path.join(base_dir, "ml", "data", "embeddings.npy")
        index_path = os.path.join(base_dir, "ml", "data", "embedding_index.json")
        
        if np is not None and os.path.exists(embeddings_path) and os.path.exists(index_path):
            try:
                self.embeddings = np.load(embeddings_path)
                # Pre-normalize for faster dot-product similarity
                norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                self.embeddings = self.embeddings / norms
                
                with open(index_path, 'r', encoding='utf-8') as f:
                    self.embedding_index = json.load(f)
                self.semantic_enabled = True
                logger.info(f"Neural Engine: Semantic embeddings loaded and normalized ({len(self.embedding_index)} items)")
            except Exception as e:
                logger.warning(f"Neural Engine: Semantic embeddings load failed: {e}")

    def _get_encoder(self):
        if self._encoder_load_attempted:
            return self._encoder

        self._encoder_load_attempted = True
        if self._encoder is None:
            try:
                from ml.models.text_encoder import TextEncoder  # noqa: F821

                self._encoder = TextEncoder()  # noqa: F821
                logger.info("Neural Engine: ML Encoder activated.")
            except Exception as e:
                logger.error(f"Neural Engine: Failed to activate ML Encoder: {e}")
                self._encoder = None
        return self._encoder

    def _cosine_similarity(self, a, b) -> float:
        """Optimized dot product for pre-normalized vectors."""
        if a is None or b is None or np is None:
            return 0.0
        # 'b' is already normalized in self.embeddings
        # 'a' (user_embedding) must be normalized before calling this
        return float(np.dot(a, b))

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
        """Pre-cache catalog embeddings at startup (Disabled in Safe Mode)."""
        logger.info("Neural Engine: Warmup skipped (Safe Mode/Disabled).")
        return

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

        # 3. Local Rule-Based Fallback (Jaccard-like Similarity)
        if not candidates_map:
            catalog = load_recommendation_catalog()
            # Simple scoring based on notes/accords overlap if we can't use ML
            for item in catalog[:200]: # Limit scan for speed
                candidates_map[item["id"]] = {
                    "id": item["id"],
                    "text_score": 0.5, # Baseline score
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
        self, ratings: list[Any], user_seed_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Main entry point for Optimized Rule-Based Discovery."""
        import time
        start_total = time.perf_counter()
        
        catalog = load_recommendation_catalog()
        if not catalog:
            return []

        # 1. Build Target Profile
        target_notes = set()
        target_accords = set()
        target_families = set()
        target_occasions = set()
        
        # Check if we got a vector (legacy search pass) or ratings
        is_vector = len(ratings) > 0 and isinstance(ratings[0], (int, float))
        
        # Fresh/Day Proxy Accords
        FRESH_ACCORDS = {"fresh", "citrus", "floral", "green", "aquatic", "aromatic", "fresh spicy"}
        # Warm/Night Proxy Accords
        WARM_ACCORDS = {"warm spicy", "amber", "tobacco", "leather", "oud", "sweet", "vanilla", "animalic", "balsamic"}

        catalog_map = {str(item["id"]): item for item in catalog}
        
        if is_vector:
            # For vector-based (semantic search fallback in safe mode), we just use a default high-count profile
            # In a real setup, we'd do vector similarity, but here we just return popularity if ML is off.
            pass
        else:
            seeds_count = 0
            for r in ratings:
                fid = str(getattr(r, "fragrance_id", r.get("fragrance_id", "") if isinstance(r, dict) else ""))
                score = getattr(r, "rating", r.get("rating", 5.0) if isinstance(r, dict) else 5.0)
                if score < 6.0: continue # Skip low ratings for profile building

                provided_notes = getattr(r, "top_notes", r.get("top_notes", []) if isinstance(r, dict) else [])
                provided_accords = getattr(r, "accords", r.get("accords", []) if isinstance(r, dict) else [])
                if provided_notes:
                    target_notes.update(provided_notes)
                if provided_accords:
                    target_accords.update(provided_accords)
                
                item = catalog_map.get(fid)
                if not item: continue
                
                seeds_count += 1
                target_notes.update(item.get("_notes_set", set()))
                item_accords = item.get("_accords_set", set())
                target_accords.update(item_accords)
                
                # Extract family from description or accords
                desc = item.get("description", "").lower()
                for family in ["woody", "citrus", "oriental", "floral", "fruity", "aromatic", "leather", "chypre"]:
                    if family in desc or family in item_accords:
                        target_families.add(family)
                
                # Extract occasion proxy
                if any(a in FRESH_ACCORDS for a in item_accords): target_occasions.add("day")
                if any(a in WARM_ACCORDS for a in item_accords): target_occasions.add("night")

        # 1.5 Semantic User Profile (Averaging item embeddings)
        user_embedding = None
        if self.semantic_enabled and not is_vector:
            profile_vecs = []
            for r in ratings:
                fid = str(getattr(r, "fragrance_id", r.get("fragrance_id", "") if isinstance(r, dict) else ""))
                score = getattr(r, "rating", r.get("rating", 5.0) if isinstance(r, dict) else 5.0)
                if score < 6.0: continue
                
                idx = self.embedding_index.get(fid)
                if idx is not None:
                    profile_vecs.append(self.embeddings[idx])
            
            if profile_vecs:
                user_embedding = np.mean(profile_vecs, axis=0)
                # Normalize user embedding once
                u_norm = np.linalg.norm(user_embedding)
                if u_norm > 0:
                    user_embedding = user_embedding / u_norm

        profile = {
            "target_notes": list(target_notes)[:10],
            "target_accords": list(target_accords)[:10],
        }
        if target_notes or target_accords:
            print("PROFILE EXISTS → SHOULD NOT FALLBACK")

        if not target_notes and not target_accords:
            print("DEBUG PROFILE:", profile)
            print("DEBUG CANDIDATES:", 0)
            # Cold start: Return top popularity items
            return [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "brand": item["brand"],
                    "match_score": 50.0,
                    "reason": "Popular Choice",
                    "top_accords": item.get("accords", [])[:3],
                    "top_notes": item.get("top_notes", [])[:3],
                } for item in sorted(catalog, key=lambda x: x.get("rating_count", 0), reverse=True)[:12]
            ]

        # 2. Candidate Pooling & Scoring
        scored_candidates = []
        seed_id_set = set(user_seed_ids)
        
        start_scoring = time.perf_counter()
        
        import math

        # Pre-filter catalog to reduce scoring overhead (Target: <1000 items)
        candidate_pool = []
        for item in catalog:
            item_id = str(item["id"])
            if item_id in seed_id_set: continue
            
            # Phase 1 Filter: Accord Overlap (Weighted)
            item_accords = item.get("_accords_set", set())
            overlap_a = len(target_accords.intersection(item_accords))
            if overlap_a >= 2: # Require at least 2 matching accords for fast path
                candidate_pool.append(item)
                continue
                
            # Phase 2 Filter: Note Overlap (High precision)
            item_notes = item.get("_notes_set", set())
            overlap_n = len(target_notes.intersection(item_notes))
            if overlap_n >= 5: # Require significant note overlap
                candidate_pool.append(item)
                continue
            
            # Phase 3 Filter: Family match (Strict)
            desc = item.get("description", "").lower()
            if any(family in desc for family in target_families):
                candidate_pool.append(item)
        
        # Hard cap on candidate pool for latency stability
        if len(candidate_pool) > 1000:
            candidate_pool.sort(key=lambda x: x.get("rating_count", 0), reverse=True)
            candidate_pool = candidate_pool[:1000]
        
        # Ensure we have at least some candidates, otherwise take top popularity
        if len(candidate_pool) < 20:
            candidate_pool = sorted(catalog, key=lambda x: x.get("rating_count", 0), reverse=True)[:100]

        print("DEBUG CANDIDATES:", len(candidate_pool))

        for item in candidate_pool:
            item_id = str(item["id"])
            if item_id in seed_id_set: continue
            
            # a) NOTE_SIMILARITY (0.35) - Jaccard
            item_notes = item.get("_notes_set", set())
            intersection_n = len(target_notes.intersection(item_notes))
            union_n = len(target_notes.union(item_notes))
            note_sim = (intersection_n / union_n) if union_n > 0 else 0
            
            # b) ACCORD_SIMILARITY (0.25) - Overlap
            item_accords = item.get("_accords_set", set())
            intersection_a = len(target_accords.intersection(item_accords))
            accord_sim = (intersection_a / max(len(target_accords), 1))
            
            # c) CATEGORY_MATCH (0.15)
            cat_match = 0.0
            desc = item.get("description", "").lower()
            for family in target_families:
                if family in desc or family in item_accords:
                    cat_match = 1.0
                    break
            
            # d) OCCASION_MATCH (0.10)
            occ_match = 0.0
            item_occ = set()
            if any(a in FRESH_ACCORDS for a in item_accords): item_occ.add("day")
            if any(a in WARM_ACCORDS for a in item_accords): item_occ.add("night")
            if target_occasions.intersection(item_occ):
                occ_match = 1.0
                
            # e) SEMANTIC_SCORE (0.15)
            semantic_score = 0.0
            if user_embedding is not None:
                item_idx = self.embedding_index.get(item_id)
                if item_idx is not None:
                    semantic_score = self._cosine_similarity(user_embedding, self.embeddings[item_idx])

            # f) POPULARITY_SCORE (0.10)
            # Normalizing log10(count) [0 to 4] and rating [1 to 5]
            rc = item.get("rating_count", 0)
            pop_count_score = min(math.log10(rc + 1) / 4.0, 1.0)
            rv = item.get("rating_value", 3.5)
            pop_val_score = (rv - 1.0) / 4.0
            popularity = (pop_count_score * 0.6) + (pop_val_score * 0.4)
            
            # Compute Final Base Score
            # Weight update: 0.35->0.30, 0.25->0.20, +0.15 Semantic
            if self.semantic_enabled and user_embedding is not None:
                base_score = (
                    (0.30 * note_sim) +
                    (0.20 * accord_sim) +
                    (0.15 * semantic_score) +
                    (0.15 * cat_match) +
                    (0.10 * occ_match) +
                    (0.10 * popularity)
                )
            else:
                # Fallback to pure rule-based weights if semantic is off
                base_score = (
                    (0.35 * note_sim) +
                    (0.25 * accord_sim) +
                    (0.15 * cat_match) +
                    (0.15 * occ_match) + # Give slightly more weight to occasion/popularity in fallback
                    (0.10 * popularity)
                )
            
            scored_candidates.append({
                "id": item_id,
                "base_score": base_score,
                "item": item
            })

        # 3. Selection with DIVERSITY_PENALTY (0.05)
        scored_candidates.sort(key=lambda x: x["base_score"], reverse=True)
        top_n = scored_candidates[:100] # Candidate pool for diversity pass
        
        final_selections = []
        selected_accords_union = set()
        
        for _ in range(12):
            if not top_n: break
            
            best_idx = -1
            best_final_score = -1.0
            
            for i, cand in enumerate(top_n):
                # f) DIVERSITY_PENALTY
                # Penalize if it shares accords with already selected set
                overlap = len(cand["item"].get("_accords_set", set()).intersection(selected_accords_union))
                penalty = min(overlap * 0.1, 1.0) # Penalty builds up
                
                final_score = cand["base_score"] - (0.05 * penalty)
                
                if final_score > best_final_score:
                    best_final_score = final_score
                    best_idx = i
            
            winner = top_n.pop(best_idx)
            final_selections.append(winner)
            selected_accords_union.update(winner["item"].get("_accords_set", set()))

        # 4. Format Output
        results = []
        for s in final_selections:
            item = s["item"]
            score = s["base_score"] # We display the match relevance, penalty is for selection
            
            # Adaptive reasoning
            reason = "Atmospheric Resonance"
            if s["base_score"] > 0.6: reason = "Olfactory Soulmate"
            elif s["base_score"] > 0.4: reason = "Harmonious Discovery"

            results.append({
                "id": item["id"],
                "name": item["name"],
                "brand": item["brand"],
                "match_score": round(score * 100, 1),
                "reason": reason,
                "top_accords": item.get("accords", [])[:3],
                "top_notes": item.get("top_notes", [])[:3],
            })
            
        end_total = time.perf_counter()
        total_ms = (end_total - start_total) * 1000
        scoring_ms = (end_total - start_scoring) * 1000
        logger.info(f"Discovery Engine: Optimized pass completed in {total_ms:.1f}ms (scoring: {scoring_ms:.1f}ms) | Pool: {len(candidate_pool)}")
        
        return results

    def close(self):
        self.driver.close()


recommender = HybridRecommender()
