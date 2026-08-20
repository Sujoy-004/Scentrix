"""Recommendation dispatcher — the 3-state warmth machine.

State machine (derived fresh per request):
  0  ANONYMOUS   rating_count == 0 AND no quiz submitted
  1  COLD        quiz submitted OR 1-2 ratings
  2  WARM        rating_count >= WARM_THRESHOLD (3)

Single safety net: any state that raises falls back to popularity.
"""

import logging
from typing import Any

from app.services.catalog import _normalize_id, get_catalog, get_catalog_map
from app.services.embeddings import gs_service as default_gs_service
from app.services.feature_based import FeatureBasedService
from app.services.popularity import PopularityService

logger = logging.getLogger(__name__)

ANONYMOUS, COLD, WARM = 0, 1, 2
WARM_THRESHOLD = 3

_STATE_LABELS = {ANONYMOUS: "anonymous", COLD: "cold", WARM: "warm"}


def determine_state(rating_count: int, quiz_submitted: bool) -> int:
    """Precedence: anonymous if 0 ratings and no quiz; WARM if >= 3; else COLD."""
    if rating_count == 0 and not quiz_submitted:
        return ANONYMOUS
    if rating_count >= WARM_THRESHOLD:
        return WARM
    return COLD


def _rating_pairs(ratings: list[Any]) -> list[tuple[str, float]]:
    """Extract and canonicalise (fragrance_id, rating) pairs from a request."""
    pairs: list[tuple[str, float]] = []
    for r in ratings:
        if isinstance(r, dict):
            fid = r.get("fragrance_id", "")
            rating = r.get("rating", 0)
        else:
            fid = getattr(r, "fragrance_id", "")
            rating = getattr(r, "rating", 0)
        if fid:
            pairs.append((_normalize_id(str(fid)), float(rating)))
    return pairs


def _hydrate_knn(
    knn_items: list[dict[str, float]],
    catalog_map: dict[str, dict[str, Any]],
    reason: str = "Discovered for you",
) -> list[dict[str, Any]]:
    """Convert bare {id, score} KNN results into the 7-field response shape."""
    results: list[dict[str, Any]] = []
    for item in knn_items:
        cat = catalog_map.get(str(item["id"]))
        if cat is None:
            continue
        score = float(item.get("score", 0.0))
        results.append(
            {
                "id": str(item["id"]),
                "name": cat.get("name", ""),
                "brand": cat.get("brand", ""),
                "match_score": round(min(100.0, max(0.0, (score + 1.0) / 2.0 * 100.0)), 1),
                "reason": reason,
                "top_accords": cat.get("accords", [])[:3],
                "top_notes": cat.get("top_notes", [])[:3],
            }
        )
    return results


class RecommendationDispatcher:
    """Routes recommendation requests to the 3-state warmth machine.

    Construct with injected services for tests; defaults to the module
    singletons and the cached catalog.
    """

    def __init__(
        self,
        gs_service: Any = None,
        feature_based_service: Any = None,
        popularity_service: Any = None,
        catalog: list[dict[str, Any]] | None = None,
    ):
        self._gs_service = gs_service if gs_service is not None else default_gs_service
        self._feature_based_service = (
            feature_based_service if feature_based_service is not None else FeatureBasedService()
        )
        self._popularity_service = (
            popularity_service if popularity_service is not None else PopularityService()
        )
        self._uses_default_catalog = catalog is None
        self._catalog = catalog if catalog is not None else get_catalog()

    # -- public API --

    def dispatch(self, request: Any) -> dict[str, Any]:
        ratings = getattr(request, "ratings", []) or []
        quiz_submitted = bool(getattr(request, "quiz_submitted", False))
        candidate_count = int(getattr(request, "candidate_count", 12) or 12)

        catalog = self._catalog
        catalog_map = (
            get_catalog_map() if self._uses_default_catalog else {str(i["id"]): i for i in catalog}
        )

        state = determine_state(len(ratings), quiz_submitted)
        state_label = _STATE_LABELS[state]
        source = state_label

        try:
            if state == ANONYMOUS:
                recommendations = self._popularity_service.get_top(
                    catalog, count=candidate_count
                )
                source = "popularity"
            elif state == COLD:
                recommendations = self._cold_recommendations(
                    ratings, catalog_map, candidate_count
                )
                source = "embeddings"
            else:
                recommendations = self._feature_based_service.score(
                    ratings, catalog, top_k=candidate_count
                )
                source = "feature_based"
        except Exception as exc:
            logger.warning(
                "dispatcher: state %s (%s) failed (%s) — popularity fallback",
                state,
                state_label,
                exc,
            )
            recommendations = self._popularity_service.get_top(catalog, count=candidate_count)
            source = "popularity"

        return {
            "recommendations": recommendations[:candidate_count],
            "state": state,
            "state_label": state_label,
            "source": source,
        }

    # -- internal --

    def _cold_recommendations(
        self,
        ratings: list[Any],
        catalog_map: dict[str, dict[str, Any]],
        candidate_count: int,
    ) -> list[dict[str, Any]]:
        pairs = _rating_pairs(ratings)
        user_vector = self._gs_service.compute_user_vector(pairs)
        exclude_ids = [fid for fid, _ in pairs]
        knn = self._gs_service.knn_search(user_vector, top_k=200, exclude_ids=exclude_ids)
        return _hydrate_knn(knn, catalog_map)[:candidate_count]


# Module-level singleton.
dispatcher = RecommendationDispatcher()