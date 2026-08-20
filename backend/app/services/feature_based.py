"""Feature-based scoring service extracted from HybridRecommender.

Provides FeatureBasedService.score() that replicates the exact rule-based
scoring logic from hybrid_search.py:get_recommendations() for feature
matching. The semantic/embedding path is intentionally dropped — scoring
is pure Jaccard/overlap on notes and accords.
"""

import logging
import math
from typing import Any

from app.services.catalog import get_catalog, get_catalog_map

logger = logging.getLogger(__name__)

# Fresh/Day Proxy Accords (inlined from the deleted hybrid_search.py)
FRESH_ACCORDS = {"fresh", "citrus", "floral", "green", "aquatic", "aromatic", "fresh spicy"}
# Warm/Night Proxy Accords (inlined from the deleted hybrid_search.py)
WARM_ACCORDS = {
    "warm spicy",
    "amber",
    "tobacco",
    "leather",
    "oud",
    "sweet",
    "vanilla",
    "animalic",
    "balsamic",
}


class FeatureBasedService:
    """Rule-based feature scoring identical to HybridRecommender's feature pass."""

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _jaccard(a: set, b: set) -> float:
        union = len(a.union(b))
        return len(a.intersection(b)) / union if union > 0 else 0.0

    # ------------------------------------------------------------------
    # Profile building
    # ------------------------------------------------------------------

    def _build_profile(
        self, ratings: list[Any], catalog: list[dict[str, Any]]
    ) -> dict[str, Any]:
        catalog_map = {str(item["id"]): item for item in catalog}
        target_notes: set[str] = set()
        target_accords: set[str] = set()
        target_families: set[str] = set()
        target_occasions: set[str] = set()
        FAMILIES = [
            "woody", "citrus", "oriental", "floral",
            "fruity", "aromatic", "leather", "chypre",
        ]

        for r in ratings:
            fid = str(
                getattr(
                    r, "fragrance_id",
                    r.get("fragrance_id", "") if isinstance(r, dict) else "",
                )
            )
            provided_notes = getattr(
                r, "top_notes",
                r.get("top_notes", []) if isinstance(r, dict) else [],
            )
            provided_accords = getattr(
                r, "accords",
                r.get("accords", []) if isinstance(r, dict) else [],
            )
            if provided_notes:
                target_notes.update(provided_notes)
            if provided_accords:
                target_accords.update(provided_accords)

            item = catalog_map.get(fid)
            if not item:
                continue

            target_notes.update(item.get("_notes_set", set()))
            item_accords = item.get("_accords_set", set())
            target_accords.update(item_accords)

            desc = item.get("description", "").lower()
            for family in FAMILIES:
                if family in desc or family in item_accords:
                    target_families.add(family)

            if any(a in FRESH_ACCORDS for a in item_accords):
                target_occasions.add("day")
            if any(a in WARM_ACCORDS for a in item_accords):
                target_occasions.add("night")

        return {
            "target_notes": list(target_notes)[:10],
            "target_accords": list(target_accords)[:10],
            "target_families": target_families,
            "target_occasions": target_occasions,
        }

    # ------------------------------------------------------------------
    # Candidate pooling (mirrors hybrid_search.py lines 388-422)
    # ------------------------------------------------------------------

    def _get_candidates(
        self,
        catalog: list[dict[str, Any]],
        profile: dict[str, Any],
        seed_id_set: set[str],
    ) -> list[dict[str, Any]]:
        target_notes = profile["target_notes"]
        target_accords = profile["target_accords"]
        target_families = profile["target_families"]
        target_notes_set = set(target_notes)
        target_accords_set = set(target_accords)

        candidate_pool: list[dict[str, Any]] = []
        for item in catalog:
            item_id = str(item["id"])
            if item_id in seed_id_set:
                continue

            item_accords = item.get("_accords_set", set())
            overlap_a = len(target_accords_set.intersection(item_accords))
            if overlap_a >= 2:
                candidate_pool.append(item)
                continue

            item_notes = item.get("_notes_set", set())
            overlap_n = len(target_notes_set.intersection(item_notes))
            if overlap_n >= 5:
                candidate_pool.append(item)
                continue

            desc = item.get("description", "").lower()
            if any(family in desc for family in target_families):
                candidate_pool.append(item)

        if len(candidate_pool) > 1000:
            candidate_pool.sort(key=lambda x: x.get("rating_count", 0), reverse=True)
            candidate_pool = candidate_pool[:1000]

        if len(candidate_pool) < 20:
            candidate_pool = sorted(
                catalog,
                key=lambda x: x.get("rating_count", 0),
                reverse=True,
            )[:100]

        return candidate_pool

    # ------------------------------------------------------------------
    # Scoring (mirrors hybrid_search.py lines 426-500 + 504-559)
    # ------------------------------------------------------------------

    def _score_and_select(
        self,
        candidate_pool: list[dict[str, Any]],
        profile: dict[str, Any],
        seed_id_set: set[str],
        top_k: int = 50,
    ) -> list[dict[str, Any]]:
        target_notes = set(profile["target_notes"])
        target_accords = set(profile["target_accords"])
        target_families = profile["target_families"]
        target_occasions = profile["target_occasions"]

        scored: list[dict[str, Any]] = []
        for item in candidate_pool:
            item_id = str(item["id"])
            if item_id in seed_id_set:
                continue

            # a) NOTE_SIMILARITY — Jaccard
            item_notes = item.get("_notes_set", set())
            note_sim = self._jaccard(target_notes, item_notes)

            # b) ACCORD_SIMILARITY — overlap / max
            item_accords = item.get("_accords_set", set())
            intersection_a = len(target_accords.intersection(item_accords))
            accord_sim = intersection_a / max(len(target_accords), 1)

            # c) CATEGORY_MATCH
            cat_match = 0.0
            desc = item.get("description", "").lower()
            for family in target_families:
                if family in desc or family in item_accords:
                    cat_match = 1.0
                    break

            # d) OCCASION_MATCH
            occ_match = 0.0
            item_occ: set[str] = set()
            if any(a in FRESH_ACCORDS for a in item_accords):
                item_occ.add("day")
            if any(a in WARM_ACCORDS for a in item_accords):
                item_occ.add("night")
            if target_occasions.intersection(item_occ):
                occ_match = 1.0

            # e) POPULARITY_SCORE
            rc = item.get("rating_count", 0)
            pop_count_score = min(math.log10(rc + 1) / 4.0, 1.0)
            rv = item.get("rating_value", 3.5)
            pop_val_score = (rv - 1.0) / 4.0
            popularity = (pop_count_score * 0.6) + (pop_val_score * 0.4)

            # f) Final base score (pure rule-based)
            base_score = (
                (0.35 * note_sim)
                + (0.25 * accord_sim)
                + (0.15 * cat_match)
                + (0.15 * occ_match)
                + (0.10 * popularity)
            )

            scored.append({"id": item_id, "base_score": base_score, "item": item})

        # Diversity selection (mirrors hybrid_search.py lines 504-534)
        scored.sort(key=lambda x: x["base_score"], reverse=True)
        top_n = scored[:100]

        final_selections: list[dict[str, Any]] = []
        selected_accords_union: set[str] = set()

        for _ in range(top_k):
            if not top_n:
                break

            best_idx = -1
            best_final = -1.0

            for i, cand in enumerate(top_n):
                overlap = len(
                    cand["item"].get("_accords_set", set()).intersection(selected_accords_union)
                )
                penalty = min(overlap * 0.1, 1.0)
                final_score = cand["base_score"] - (0.05 * penalty)
                if final_score > best_final:
                    best_final = final_score
                    best_idx = i

            winner = top_n.pop(best_idx)
            final_selections.append(winner)
            selected_accords_union.update(winner["item"].get("_accords_set", set()))

        # Format output (mirrors hybrid_search.py lines 536-559)
        results: list[dict[str, Any]] = []
        for s in final_selections:
            item = s["item"]
            score = s["base_score"]

            reason = "Atmospheric Resonance"
            if score > 0.6:
                reason = "Olfactory Soulmate"
            elif score > 0.4:
                reason = "Harmonious Discovery"

            results.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "brand": item["brand"],
                    "match_score": round(score * 100, 1),
                    "reason": reason,
                    "top_accords": item.get("accords", [])[:3],
                    "top_notes": item.get("top_notes", [])[:3],
                }
            )

        return results

    # ------------------------------------------------------------------
    # Cold-start popularity fallback (identical to hybrid_search lines 363-377)
    # ------------------------------------------------------------------

    @staticmethod
    def _popularity_fallback(catalog: list[dict[str, Any]], count: int = 50) -> list[dict[str, Any]]:
        return [
            {
                "id": item["id"],
                "name": item["name"],
                "brand": item["brand"],
                "match_score": 50.0,
                "reason": "Popular Choice",
                "top_accords": item.get("accords", [])[:3],
                "top_notes": item.get("top_notes", [])[:3],
            }
            for item in sorted(
                catalog, key=lambda x: x.get("rating_count", 0), reverse=True
            )[:count]
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        ratings: list[Any],
        catalog: list[dict[str, Any]] | None = None,
        user_seed_ids: list[str] | None = None,
        top_k: int = 50,
    ) -> list[dict[str, Any]]:
        """Full feature-based scoring pipeline.

        Produces identical output to ``HybridRecommender.get_recommendations()``
        for the same inputs with the semantic path disabled.
        """
        if catalog is None:
            catalog = get_catalog()
        if not catalog:
            return []

        if user_seed_ids is None:
            user_seed_ids = []
        seed_id_set = set(user_seed_ids)

        profile = self._build_profile(ratings, catalog)

        if not set(profile["target_notes"]) and not set(profile["target_accords"]):
            return self._popularity_fallback(catalog, count=top_k)

        candidate_pool = self._get_candidates(catalog, profile, seed_id_set)
        return self._score_and_select(candidate_pool, profile, seed_id_set, top_k=top_k)