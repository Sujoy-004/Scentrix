"""Popularity-based recommendation service extracted from HybridRecommender.

Provides PopularityService.get_top() that replicates the exact cold-start
popularity fallback logic from hybrid_search.py:get_recommendations().
"""

import logging
from typing import Any

from app.services.catalog import load_recommendation_catalog

logger = logging.getLogger(__name__)


class PopularityService:
    """Pure popularity-based ranking using rating_count.

    Produces identical output to ``HybridRecommender``'s cold-start
    popularity fallback (hybrid_search.py lines 363-377 and 569-580).
    """

    @staticmethod
    def get_top(
        catalog: list[dict[str, Any]] | None = None,
        count: int = 12,
    ) -> list[dict[str, Any]]:
        """Return the top *count* items sorted by ``rating_count`` descending.

        Output format (identical to hybrid_search.py popularity fallback):
          id, name, brand, match_score=50.0, reason="Popular Choice",
          top_accords[:3], top_notes[:3]
        """
        if catalog is None:
            catalog = load_recommendation_catalog()
        if not catalog:
            return []

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
