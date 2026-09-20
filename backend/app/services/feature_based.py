"""Feature-based scoring service extracted from HybridRecommender.

Provides FeatureBasedService.score() that replicates the exact rule-based
scoring logic from hybrid_search.py:get_recommendations() for feature
matching. The semantic/embedding path is intentionally dropped — scoring
is pure Jaccard/overlap on notes and accords.
"""

import logging
import math
from typing import Any

from app.services.catalog import get_catalog

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

    @staticmethod
    def _deviation_weight(rating: Any) -> float:
        """Centered, signed rating weight in [-1, 1] (5.0 -> 0, 10.0 -> +1)."""
        try:
            clamped = max(1.0, min(10.0, float(rating)))
        except (TypeError, ValueError):
            return 0.0
        return max(-1.0, min(1.0, (clamped - 5.0) / 5.0))

    # ------------------------------------------------------------------
    # Profile building
    # ------------------------------------------------------------------

    def _build_profile(
        self, ratings: list[Any], catalog: list[dict[str, Any]]
    ) -> dict[str, Any]:
        catalog_map = {str(item["id"]): item for item in catalog}
        note_scores: dict[str, float] = {}
        accord_scores: dict[str, float] = {}
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
            item_rating = getattr(
                r, "rating",
                r.get("rating", 0) if isinstance(r, dict) else 0,
            )
            weight = self._deviation_weight(item_rating)
            provided_notes = getattr(
                r, "top_notes",
                r.get("top_notes", []) if isinstance(r, dict) else [],
            )
            provided_accords = getattr(
                r, "accords",
                r.get("accords", []) if isinstance(r, dict) else [],
            )
            for note in provided_notes:
                key = str(note).strip().lower()
                if key:
                    note_scores[key] = note_scores.get(key, 0.0) + weight
            for accord in provided_accords:
                key = str(accord).strip().lower()
                if key:
                    accord_scores[key] = accord_scores.get(key, 0.0) + weight

            item = catalog_map.get(fid)
            if not item:
                continue

            for note in item.get("_notes_set", set()):
                note_scores[note] = note_scores.get(note, 0.0) + weight
            item_accords = item.get("_accords_set", set())
            for accord in item_accords:
                accord_scores[accord] = accord_scores.get(accord, 0.0) + weight

            if weight > 0:
                desc = item.get("description", "").lower()
                for family in FAMILIES:
                    if family in desc or family in item_accords:
                        target_families.add(family)
                if any(a in FRESH_ACCORDS for a in item_accords):
                    target_occasions.add("day")
                if any(a in WARM_ACCORDS for a in item_accords):
                    target_occasions.add("night")

        # Deterministic ordering (no set-iteration order dependence).
        target_notes = sorted(
            (k for k, s in note_scores.items() if s > 0),
            key=lambda k: note_scores[k],
            reverse=True,
        )[:10]
        target_accords = sorted(
            (k for k, s in accord_scores.items() if s > 0),
            key=lambda k: accord_scores[k],
            reverse=True,
        )[:10]
        negative_notes = sorted(k for k, s in note_scores.items() if s < 0)
        negative_accords = sorted(k for k, s in accord_scores.items() if s < 0)

        return {
            "target_notes": target_notes,
            "target_accords": target_accords,
            "target_families": target_families,
            "target_occasions": target_occasions,
            "negative_notes": negative_notes,
            "negative_accords": negative_accords,
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
        negative_notes = set(profile.get("negative_notes") or [])
        negative_accords = set(profile.get("negative_accords") or [])

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

            # g) Negative-signal penalty — shy away from disliked notes/accords
            neg_penalty = (
                0.03 * len(item_notes.intersection(negative_notes))
                + 0.03 * len(item_accords.intersection(negative_accords))
            )
            base_score -= min(neg_penalty, 0.15)

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
                    "explanation": self._explain_item(item, target_accords, target_notes,
                                                      negative_accords, negative_notes),
                    "top_accords": item.get("accords", [])[:3],
                    "top_notes": item.get("top_notes", [])[:3],
                }
            )

        return results

    @staticmethod
    def _titles(names: list[str]) -> str:
        return ", ".join(str(n).replace("_", " ").title() for n in names[:3])

    @classmethod
    def _explain_item(cls, item, target_accords, target_notes, negative_accords, negative_notes):
        """Human-readable 'why' from the profile overlap actually scored."""
        item_accords: set[str] = item.get("_accords_set", set())
        item_notes: set[str] = item.get("_notes_set", set())
        considered_accords = target_accords if isinstance(target_accords, set) else set(target_accords)
        considered_notes = target_notes if isinstance(target_notes, set) else set(target_notes)
        hit_accords = sorted(considered_accords & item_accords)
        hit_notes = sorted(considered_notes & item_notes)
        parts: list[str] = []
        if hit_accords:
            parts.append(f"matches your top accords ({cls._titles(hit_accords)})")
        if hit_notes:
            parts.append(f"overlaps the notes you like ({cls._titles(hit_notes)})")
        neg_hits = sorted(set(negative_accords or []) & item_accords)
        neg_hits += [n for n in sorted(set(negative_notes or []) & item_notes) if n not in neg_hits]
        if neg_hits:
            parts.append(f"paces itself around {cls._titles(neg_hits)}, which you rated low")
        return (parts[0].capitalize() + ("; " + parts[1] if len(parts) > 1 else "")
                + ("." if parts else "A strong rule-based overlap with your scent profile."))

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
                "explanation": "The most-loved scents in the catalog right now.",
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
