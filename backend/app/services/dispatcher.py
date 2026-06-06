"""Recommendation dispatcher — state machine, strategy selection, blend math.

State machine (derived per request — no caching):
  0  Anonymous   rating_count == 0 AND quiz_completed == False
  1  Quiz User   rating_count == 0 AND quiz_completed == True
  2  Cold        1 <= rating_count <= 4
  3  Warm        5 <= rating_count <= 19
  4  Mature      rating_count >= 20
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ── Dispatcher Contracts ─────────────────────────────────────────────────────


@dataclass
class DispatchRequest:
    """Input contract for RecommendationDispatcher.dispatch().

    Everything needed to determine user state and route to a strategy.
    rating_count is derived from len(ratings).
    """

    user_id: int | None = None
    ratings: list[Any] = field(default_factory=list)
    quiz_ratings: list[Any] = field(default_factory=list)
    quiz_completed: bool = False
    quiz_confidence: dict[str, float] | None = None
    use_user_vector: bool = False
    catalog: list[dict[str, Any]] | None = None
    candidate_count: int = 12
    gs_service: Any = None
    feature_based_service: Any = None
    popularity_service: Any = None


@dataclass
class DispatchResult:
    """Output contract from RecommendationDispatcher.dispatch()."""

    recommendations: list[dict[str, Any]] = field(default_factory=list)
    source: str = ""
    state: int = -1
    state_label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    fallback_chain: list[str] = field(default_factory=list)


# ── Strategy Interface ───────────────────────────────────────────────────────


class RecommendationStrategy(ABC):
    """Abstract base for all recommendation strategies."""

    @abstractmethod
    async def execute(self, request: DispatchRequest) -> DispatchResult:
        ...


# ── Concrete Strategies (stubs for CP4 — no service execution) ──────────────


class PopularityStrategy(RecommendationStrategy):
    """State 0: Top-N by rating_count."""

    async def execute(self, request: DispatchRequest) -> DispatchResult:
        source = "popularity"
        fallback_chain: list[str] = [source]
        try:
            svc = request.popularity_service
            if svc is not None and request.catalog:
                items = svc.get_top(request.catalog, count=request.candidate_count)
            else:
                items = []
            for item in items:
                item["source"] = source
            return DispatchResult(
                recommendations=items,
                source=source,
                state=0,
                state_label="anonymous",
                metadata={"candidate_count": len(items)},
                fallback_chain=fallback_chain,
            )
        except Exception:
            return DispatchResult(
                recommendations=[],
                source="popularity",
                state=0,
                state_label="anonymous",
                metadata={"error": "strategy_failed"},
                fallback_chain=fallback_chain + ["fallback_empty"],
            )


class GraphSAGEStrategy(RecommendationStrategy):
    """State 1: GraphSAGE centroid/KNN from quiz confidence or user vector."""

    async def execute(self, request: DispatchRequest) -> DispatchResult:
        source = "graphsage"
        fallback_chain: list[str] = [source]
        try:
            gs = request.gs_service
            if gs is None:
                raise ValueError("gs_service_unavailable")

            # ── User-vector path (primary) ─────────────────────────────────
            uv_ratings = request.quiz_ratings if request.quiz_ratings else request.ratings
            if request.use_user_vector and uv_ratings:
                item_ratings = [(r.fragrance_id, r.rating) for r in uv_ratings]
                user_vector = gs.compute_user_vector(item_ratings)
                exclude_ids = [r.fragrance_id for r in uv_ratings]
                candidates = gs.knn_search(
                    user_vector, top_k=200, exclude_ids=exclude_ids,
                )
                for item in candidates:
                    item["source"] = source

                return DispatchResult(
                    recommendations=candidates,
                    source=source,
                    state=1,
                    state_label="quiz_user",
                    metadata={
                        "rated_count": len(item_ratings),
                        "candidate_count": len(candidates),
                        "mode": "user_vector",
                    },
                    fallback_chain=fallback_chain,
                )

            # ── Centroid path (legacy) ─────────────────────────────────────
            catalog = request.catalog if request.catalog is not None else []
            if request.quiz_confidence is not None and catalog:
                seed_ids, weights = _align_quiz_confidence(
                    request.quiz_confidence, catalog
                )
            else:
                seed_ids, weights = [], []

            if not seed_ids:
                raise ValueError("no_seeds")

            centroid = gs.compute_centroid(seed_ids, weights)
            candidates = gs.knn_search(centroid, top_k=200, exclude_ids=seed_ids)
            for item in candidates:
                item["source"] = source

            return DispatchResult(
                recommendations=candidates,
                source=source,
                state=1,
                state_label="quiz_user",
                metadata={
                    "seed_count": len(seed_ids),
                    "candidate_count": len(candidates),
                    "mode": "centroid",
                    "alpha": 0.0,
                },
                fallback_chain=fallback_chain,
            )
        except Exception:
            # Fall through to feature_based
            try:
                fb = request.feature_based_service
                if fb is not None and request.catalog:
                    fallback_items = fb.score(
                        request.ratings if request.ratings else [],
                        request.catalog,
                        user_seed_ids=[],
                    )
                else:
                    fallback_items = []
                for item in fallback_items:
                    item["source"] = "feature_based"
                return DispatchResult(
                    recommendations=fallback_items,
                    source="feature_based",
                    state=1,
                    state_label="quiz_user",
                    metadata={"fallback": "graphsage_failed"},
                    fallback_chain=fallback_chain + ["feature_based"],
                )
            except Exception:
                return DispatchResult(
                    recommendations=[],
                    source="feature_based",
                    state=1,
                    state_label="quiz_user",
                    metadata={"error": "all_strategies_failed"},
                    fallback_chain=fallback_chain + ["feature_based", "fallback_empty"],
                )


class BlendedStrategy(RecommendationStrategy):
    """State 2: β-blend of GraphSAGE and feature-based scores.

    Blend formula
    -------------
    blended_score(i) = β · fb_norm(i) + (1 − β) · gs_norm(i)

    where
      fb_norm = match_score / 100       (feature-based score in [0,1])
      gs_norm = (score + 1) / 2         (cosine similarity in [-1,1] → [0,1])
      β      = clamp((rating_count − 1) / 4, 0, 1)

    Candidate merge
    ---------------
    Every unique fragrance across both candidate sets gets a blended score.
    An item that appears in only one set receives the weighted score from
    the available source (the missing source contributes zero).

    Tie-break
    ---------
    When blended scores are equal the item with the higher feature-based
    match_score wins (feature-based signal is more user-specific).
    """

    async def execute(self, request: DispatchRequest) -> DispatchResult:
        source = "blended"
        fallback_chain: list[str] = [source]
        try:
            rating_count = len(request.ratings)
            beta = _compute_beta(rating_count)
            gs = request.gs_service
            fb_svc = request.feature_based_service

            gs_candidates: list[dict] = []
            fb_candidates: list[dict] = []
            seed_ids: list[str] = []

            if gs is not None and request.ratings:
                seed_ids = [r.fragrance_id for r in request.ratings]
                weights = [getattr(r, "rating", 5.0) / 10 for r in request.ratings]
                centroid = gs.compute_centroid(seed_ids, weights)
                gs_candidates = gs.knn_search(centroid, top_k=100)

            if fb_svc is not None and request.catalog:
                fb_candidates = fb_svc.score(
                    request.ratings, request.catalog,
                    user_seed_ids=seed_ids,
                    top_k=request.candidate_count,
                )

            # Build lookup maps
            gs_by_id: dict[str, float] = {}
            for item in gs_candidates:
                gs_by_id[str(item["id"])] = item["score"]

            fb_by_id: dict[str, dict] = {}
            for item in fb_candidates:
                fb_by_id[str(item["id"])] = item

            all_ids = set(gs_by_id.keys()) | set(fb_by_id.keys())

            blended: list[dict[str, Any]] = []
            for fid in all_ids:
                gs_score = gs_by_id.get(fid)
                fb_item = fb_by_id.get(fid)

                # Normalise both sources to [0,1]
                gs_norm = (gs_score + 1.0) / 2.0 if gs_score is not None else 0.0
                fb_norm = fb_item["match_score"] / 100.0 if fb_item is not None else 0.0

                blended_score = beta * fb_norm + (1.0 - beta) * gs_norm

                if fb_item is not None:
                    item = dict(fb_item)
                else:
                    item = {"id": fid}

                item["match_score"] = round(blended_score * 100, 1)
                item["source"] = source
                blended.append(item)

            # Sort by blended_score desc; tie-break by FB match_score desc
            blended.sort(
                key=lambda x: (
                    x["match_score"],
                    fb_by_id.get(str(x["id"]), {}).get("match_score", 0),
                ),
                reverse=True,
            )

            return DispatchResult(
                recommendations=blended,
                source=source,
                state=2,
                state_label="cold",
                metadata={
                    "beta": beta,
                    "rating_count": rating_count,
                    "gs_candidate_count": len(gs_candidates),
                    "fb_candidate_count": len(fb_candidates),
                    "blended_count": len(blended),
                },
                fallback_chain=fallback_chain,
            )
        except Exception:
            try:
                fb_svc = request.feature_based_service
                if fb_svc is not None and request.catalog:
                    items = fb_svc.score(
                        request.ratings, request.catalog, user_seed_ids=[]
                    )
                else:
                    items = []
                for item in items:
                    item["source"] = "feature_based"
                return DispatchResult(
                    recommendations=items,
                    source="feature_based",
                    state=2,
                    state_label="cold",
                    metadata={"fallback": "blend_failed"},
                    fallback_chain=fallback_chain + ["feature_based"],
                )
            except Exception:
                return DispatchResult(
                    recommendations=[],
                    source="feature_based",
                    state=2,
                    state_label="cold",
                    metadata={"error": "all_strategies_failed"},
                    fallback_chain=fallback_chain + ["feature_based", "fallback_empty"],
                )


class FeatureBasedStrategy(RecommendationStrategy):
    """State 3: Feature-based scoring with GraphSAGE exploration.

    Exploration injection
    ---------------------
    Up to 25 % of the final output is replaced by GraphSAGE exploration
    items (items the user hasn't rated that are near their centroid).

    Insertion positions (0-indexed)
        [2, 5, 8, 11, …] — every 3rd slot starting at index 2.

    Exclusion rules
        Any exploration item whose ID already appears in the feature-based
        result set is skipped (duplicate prevention).

    Duplicate prevention
        Items are compared by string ID.  Exploration items are filtered
        against both the FB result set AND the user's seed (rated) IDs.
    """

    async def execute(self, request: DispatchRequest) -> DispatchResult:
        source = "feature_based"
        fallback_chain: list[str] = [source]
        try:
            fb_svc = request.feature_based_service
            gs = request.gs_service
            if fb_svc is not None and request.catalog:
                items = fb_svc.score(
                    request.ratings, request.catalog,
                    user_seed_ids=[],
                    top_k=request.candidate_count,
                )
            else:
                items = []

            exploration_count = 0
            if gs is not None and items:
                seed_ids = [r.fragrance_id for r in request.ratings]
                fb_ids = {str(r["id"]) for r in items} if items else set()
                centroid = gs.compute_centroid(seed_ids)
                gs_items = gs.knn_search(
                    centroid, top_k=20, exclude_ids=fb_ids | set(seed_ids)
                )
                exploration_count = len(gs_items)

                if gs_items:
                    # Up to 25 % of candidate_count as exploration
                    explore_slots = max(1, request.candidate_count // 4)
                    explore_take = min(explore_slots, exploration_count)

                    # Make room by trimming FB items
                    items = items[: request.candidate_count - explore_take]

                    # Tag FB items
                    for item in items:
                        item["source"] = source

                    # Build exploration items (will be hydrated by dispatcher)
                    exploration = []
                    for gs_item in gs_items[:explore_take]:
                        exploration.append({
                            "id": gs_item["id"],
                            "score": gs_item["score"],
                            "source": "exploration",
                        })

                    # Insert at every 3rd slot starting at index 2
                    final_items = list(items)
                    for i, exp in enumerate(exploration):
                        pos = min(2 + i * 3, len(final_items))
                        final_items.insert(pos, exp)

                    items = final_items
            else:
                for item in items:
                    item["source"] = source

            return DispatchResult(
                recommendations=items,
                source=source,
                state=3,
                state_label="warm",
                metadata={
                    "rating_count": len(request.ratings),
                    "exploration_count": exploration_count,
                },
                fallback_chain=fallback_chain,
            )
        except Exception:
            try:
                gs = request.gs_service
                if gs is not None and request.ratings and request.catalog:
                    seed_ids = [r.fragrance_id for r in request.ratings]
                    centroid = gs.compute_centroid(seed_ids)
                    candidates = gs.knn_search(centroid, top_k=request.candidate_count)
                else:
                    candidates = []
                for item in candidates:
                    item["source"] = "graphsage"
                return DispatchResult(
                    recommendations=candidates,
                    source="graphsage",
                    state=3,
                    state_label="warm",
                    metadata={"fallback": "feature_based_failed"},
                    fallback_chain=fallback_chain + ["graphsage"],
                )
            except Exception:
                return DispatchResult(
                    recommendations=[],
                    source="graphsage",
                    state=3,
                    state_label="warm",
                    metadata={"error": "all_strategies_failed"},
                    fallback_chain=fallback_chain + ["graphsage", "fallback_empty"],
                )


class FeatureWithDiversityStrategy(RecommendationStrategy):
    """State 4: Feature-based scoring with diversity rerank.

    Diversity metric
    ----------------
    Accord-overlap Jaccard similarity between two fragrance items:
        J(A, B) = |accords_A ∩ accords_B| / |accords_A ∪ accords_B|
    Two items sharing no accords → J = 0.  One or both with no accords → J = 0.

    Candidate replacement logic (MMR)
    ----------------------------------
    1. Pick the highest-scoring item as the anchor.
    2. For each remaining slot, compute:
        MMR_score(i) = λ · score_norm(i) − (1 − λ) · max J(i, selected)
       where score_norm = match_score / 100.
    3. The item with the highest MMR_score is selected next.
    4. Repeat until the output list is full.

    Compared to FeatureBasedStrategy (λ = 0.7 → mild diversity) the
    diversity strategy uses λ = 0.5 for stronger diversity emphasis,
    which is appropriate for Mature users (20+ ratings) whose taste
    is well established.
    """

    @staticmethod
    def _accord_jaccard(a: dict, b: dict) -> float:
        accords_a = set(a.get("top_accords", []))
        accords_b = set(b.get("top_accords", []))
        union = len(accords_a | accords_b)
        return len(accords_a & accords_b) / union if union else 0.0

    @staticmethod
    def _diversity_rerank(
        items: list[dict[str, Any]], lambda_d: float = 0.5
    ) -> list[dict[str, Any]]:
        if len(items) < 2:
            return list(items)

        reranked: list[dict[str, Any]] = [dict(items[0])]
        remaining: list[dict[str, Any]] = [dict(i) for i in items[1:]]

        while remaining and len(reranked) < len(items):
            best_idx = -1
            best_score = -1.0

            for i, cand in enumerate(remaining):
                max_overlap = max(
                    (
                        FeatureWithDiversityStrategy._accord_jaccard(cand, sel)
                        for sel in reranked
                    ),
                    default=0.0,
                )
                cand_score = cand.get("match_score", 0) / 100.0
                mmr = lambda_d * cand_score - (1.0 - lambda_d) * max_overlap
                if mmr > best_score:
                    best_score = mmr
                    best_idx = i

            reranked.append(remaining.pop(best_idx))

        return reranked

    async def execute(self, request: DispatchRequest) -> DispatchResult:
        source = "diversity"
        fallback_chain: list[str] = [source]
        try:
            fb_svc = request.feature_based_service
            if fb_svc is not None and request.catalog:
                items = fb_svc.score(
                    request.ratings, request.catalog,
                    user_seed_ids=[],
                    top_k=request.candidate_count,
                )
            else:
                items = []

            if items and len(items) >= 2:
                items = self._diversity_rerank(items, lambda_d=0.5)

            for item in items:
                item["source"] = source

            gs = request.gs_service
            if gs is not None and request.ratings:
                seed_ids = [r.fragrance_id for r in request.ratings]
                fb_ids = {str(r["id"]) for r in items}
                centroid = gs.compute_centroid(seed_ids)
                gs_items = gs.knn_search(
                    centroid, top_k=20, exclude_ids=fb_ids | set(seed_ids)
                )
                for i, gs_item in enumerate(gs_items[:2]):
                    pos = min(2 + i * 3, len(items))
                    items.insert(pos, {
                        "id": gs_item["id"],
                        "score": gs_item["score"],
                        "source": "exploration",
                    })

            return DispatchResult(
                recommendations=items,
                source=source,
                state=4,
                state_label="mature",
                metadata={
                    "rating_count": len(request.ratings),
                    "saturation_check": len(request.ratings) >= 20,
                },
                fallback_chain=fallback_chain,
            )
        except Exception:
            try:
                fb_svc = request.feature_based_service
                if fb_svc is not None and request.catalog:
                    items = fb_svc.score(
                        request.ratings, request.catalog, user_seed_ids=[]
                    )
                else:
                    items = []
                for item in items:
                    item["source"] = "feature_based"
                return DispatchResult(
                    recommendations=items,
                    source="feature_based",
                    state=4,
                    state_label="mature",
                    metadata={"fallback": "diversity_failed"},
                    fallback_chain=fallback_chain + ["feature_based"],
                )
            except Exception:
                return DispatchResult(
                    recommendations=[],
                    source="feature_based",
                    state=4,
                    state_label="mature",
                    metadata={"error": "all_strategies_failed"},
                    fallback_chain=fallback_chain + ["feature_based", "fallback_empty"],
                )


# ── State helpers ────────────────────────────────────────────────────────────

# Strategy instances (singletons — stateless, safe to share)
_POPULARITY_STRATEGY = PopularityStrategy()
_GRAPHSAGE_STRATEGY = GraphSAGEStrategy()
_BLENDED_STRATEGY = BlendedStrategy()
_FEATURE_BASED_STRATEGY = FeatureBasedStrategy()
_DIVERSITY_STRATEGY = FeatureWithDiversityStrategy()

_STRATEGY_FOR_STATE: dict[int, RecommendationStrategy] = {
    0: _POPULARITY_STRATEGY,
    1: _GRAPHSAGE_STRATEGY,
    2: _BLENDED_STRATEGY,
    3: _FEATURE_BASED_STRATEGY,
    4: _DIVERSITY_STRATEGY,
}


def _determine_state(
    rating_count: int,
    quiz_completed: bool,
) -> int:
    """Derive user state from rating_count and quiz_completed.

    Returns:
        0  Anonymous      rating_count == 0 AND quiz_completed == False
        1  Quiz User      rating_count == 0 AND quiz_completed == True
        2  Cold           1 <= rating_count <= 4
        3  Warm           5 <= rating_count <= 19
        4  Mature         rating_count >= 20
    """
    if rating_count == 0 and not quiz_completed:
        return 0
    if rating_count == 0 and quiz_completed:
        return 1
    if 1 <= rating_count <= 4:
        return 2
    if rating_count >= 20:
        return 4
    # 5 <= rating_count <= 19
    return 3


def _state_label(state: int) -> str:
    _LABELS = {0: "anonymous", 1: "quiz_user", 2: "cold", 3: "warm", 4: "mature"}
    return _LABELS.get(state, "unknown")


def _compute_beta(rating_count: int) -> float:
    """Blend coefficient for State 2 (Cold).

    β = clamp((rating_count - 1) / 4, 0, 1)

    1 → 0.00 (pure GraphSAGE)
    2 → 0.25
    3 → 0.50
    4 → 0.75
    5 → 1.00 (pure feature-based)
    """
    return max(0.0, min(1.0, (rating_count - 1) / 4.0))


def _align_quiz_confidence(
    quiz_confidence: dict[str, float],
    catalog: list[dict[str, Any]],
    max_seeds: int = 5,
) -> tuple[list[str], list[float]]:
    """Convert accord→confidence dict to aligned seed_ids + weights.

    For each accord in *quiz_confidence*, finds the best-matching catalog item
    (highest rating_count) whose ``_accords_set`` contains the accord.

    Returns:
        (seed_ids, weights) where each list is length == min(len(quiz_confidence), max_seeds)
        and both lists are 1:1 aligned.
    """
    # Sort accords by confidence descending, take max_seeds
    sorted_accords = sorted(
        quiz_confidence.items(), key=lambda x: x[1], reverse=True
    )[:max_seeds]

    seed_ids: list[str] = []
    weights: list[float] = []

    for accord, confidence in sorted_accords:
        # Find the best catalog item for this accord
        best_item: dict | None = None
        best_rating_count = -1
        for item in catalog:
            accords_set = item.get("_accords_set", set())
            if accord in accords_set:
                rc = item.get("rating_count", 0)
                if rc > best_rating_count:
                    best_rating_count = rc
                    best_item = item

        if best_item is not None:
            seed_ids.append(str(best_item["id"]))
            weights.append(confidence)

    return seed_ids, weights


def _hydrate_from_catalog(
    items: list[dict[str, Any]],
    catalog: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Convert KNN-style results to full recommendation dicts.

    KNN results from GraphSAGEService return ``{"id": ..., "score": ...}``
    without the full item fields (name, brand, accords, etc).  This function
    hydrates them from *catalog* so they match the FragranceRecommendation
    schema.  Items that already have a ``name`` key are passed through unchanged.
    Items that cannot be hydrated are silently dropped.
    """
    if not catalog:
        return items
    catalog_map = {str(item["id"]): item for item in catalog}
    hydrated: list[dict[str, Any]] = []
    for item in items:
        item_id = str(item.get("id", ""))
        if "name" in item or "brand" in item:
            hydrated.append(item)
            continue
        cat_item = catalog_map.get(item_id)
        if cat_item is None:
            continue
        hydrated.append({
            "id": item_id,
            "name": cat_item.get("name", ""),
            "brand": cat_item.get("brand", ""),
            "match_score": item.get("match_score", item.get("score", 50.0) * 100),
            "reason": item.get("reason", "Discovered for you"),
            "source": item.get("source", "discovered"),
            "top_accords": cat_item.get("accords", [])[:3],
            "top_notes": cat_item.get("top_notes", [])[:3],
        })
    return hydrated


def _select_strategy(state: int) -> RecommendationStrategy:
    """Return the strategy instance for the given state."""
    return _STRATEGY_FOR_STATE[state]


# ── Dispatcher ───────────────────────────────────────────────────────────────


class RecommendationDispatcher:
    """Stateful dispatcher that routes recommendation requests to strategies.

    State is derived fresh on EVERY dispatch() call — no caching, no hooks.
    """

    def __init__(
        self,
        gs_service: Any = None,
        feature_based_service: Any = None,
        popularity_service: Any = None,
    ):
        self._gs_service = gs_service
        self._feature_based_service = feature_based_service
        self._popularity_service = popularity_service

    # -- internal API (exposed for testing) --

    @staticmethod
    def determine_state(rating_count: int, quiz_completed: bool) -> int:
        return _determine_state(rating_count, quiz_completed)

    @staticmethod
    def compute_beta(rating_count: int) -> float:
        return _compute_beta(rating_count)

    @staticmethod
    def align_quiz_confidence(
        quiz_confidence: dict[str, float],
        catalog: list[dict[str, Any]],
        max_seeds: int = 5,
    ) -> tuple[list[str], list[float]]:
        return _align_quiz_confidence(quiz_confidence, catalog, max_seeds)

    # -- public API --

    async def dispatch(self, request: DispatchRequest) -> DispatchResult:
        if request.catalog is None:
            request.catalog = []

        # Inject default services from constructor if not overridden
        if request.gs_service is None:
            request.gs_service = self._gs_service
        if request.feature_based_service is None:
            request.feature_based_service = self._feature_based_service
        if request.popularity_service is None:
            request.popularity_service = self._popularity_service

        rating_count = len(request.ratings)
        state = self.determine_state(rating_count, request.quiz_completed)
        strategy = _select_strategy(state)

        result = await strategy.execute(request)
        result.recommendations = _hydrate_from_catalog(
            result.recommendations, request.catalog
        )
        result.state = state
        result.state_label = _state_label(state)
        return result
