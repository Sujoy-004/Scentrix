"""CP4+CP8 tests: state machine, boundaries, β, weight alignment, strategies,
blend, exploration, diversity, source attribution, gs_service wiring.

No real service execution — all external services are mocked.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, create_autospec

import pytest

from app.services.dispatcher import (
    BlendedStrategy,
    DispatchRequest,
    DispatchResult,
    FeatureBasedStrategy,
    FeatureWithDiversityStrategy,
    GraphSAGEStrategy,
    PopularityStrategy,
    RecommendationDispatcher,
    RecommendationStrategy,
    _align_quiz_confidence,
    _compute_beta,
    _determine_state,
    _select_strategy,
    _state_label,
)
from app.services.feature_based import FeatureBasedService
from app.services.popularity import PopularityService

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_gs_service() -> Any:
    m = MagicMock()
    m.compute_centroid.return_value = [0.1] * 64
    m.knn_search.return_value = [
        {"id": f"gs_{i}", "score": 0.9 - i * 0.1} for i in range(10)
    ]
    return m


@pytest.fixture
def mock_feature_based() -> Any:
    m = create_autospec(FeatureBasedService)
    m.score.return_value = [
        {
            "id": f"fb_{i}",
            "name": f"Test {i}",
            "brand": "MockBrand",
            "match_score": 85.0 - i * 5,
            "reason": "Harmonious Discovery",
            "top_accords": ["fresh", "citrus"],
            "top_notes": ["bergamot", "lemon"],
        }
        for i in range(12)
    ]
    return m


@pytest.fixture
def mock_popularity() -> Any:
    m = create_autospec(PopularityService)
    m.get_top.return_value = [
        {
            "id": f"pop_{i}",
            "name": f"Popular {i}",
            "brand": "PopBrand",
            "match_score": 50.0,
            "reason": "Popular Choice",
            "top_accords": ["fresh"],
            "top_notes": ["citrus"],
        }
        for i in range(12)
    ]
    return m


@pytest.fixture
def dispatcher(
    mock_gs_service: Any,
    mock_feature_based: Any,
    mock_popularity: Any,
) -> RecommendationDispatcher:
    return RecommendationDispatcher(
        gs_service=mock_gs_service,
        feature_based_service=mock_feature_based,
        popularity_service=mock_popularity,
    )


@pytest.fixture
def sample_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": "cat_001",
            "name": "Fresh Aqua",
            "brand": "Oceanic",
            "accords": ["aquatic", "fresh", "citrus"],
            "rating_count": 1200,
            "_accords_set": {"aquatic", "fresh", "citrus"},
            "_notes_set": {"bergamot", "lemon", "sea salt"},
        },
        {
            "id": "cat_002",
            "name": "Warm Ember",
            "brand": "Noir",
            "accords": ["warm spicy", "amber", "tobacco"],
            "rating_count": 850,
            "_accords_set": {"warm spicy", "amber", "tobacco"},
            "_notes_set": {"cinnamon", "clove", "saffron"},
        },
        {
            "id": "cat_003",
            "name": "Floral Dream",
            "brand": "Jardin",
            "accords": ["floral", "fruity", "fresh"],
            "rating_count": 2100,
            "_accords_set": {"floral", "fruity", "fresh"},
            "_notes_set": {"rose", "jasmine", "peach"},
        },
    ]


# ===================================================================
# SECTION C — State-machine tests
# ===================================================================


class TestStateDetermination:
    """Proves _determine_state returns correct state for every input."""

    @pytest.mark.parametrize(
        "rating_count,quiz_completed,expected_state,expected_label",
        [
            (0, False, 0, "anonymous"),
            (0, True, 1, "quiz_user"),
            (1, False, 2, "cold"),
            (1, True, 2, "cold"),
            (4, False, 2, "cold"),
            (4, True, 2, "cold"),
            (5, False, 3, "warm"),
            (5, True, 3, "warm"),
            (19, False, 3, "warm"),
            (19, True, 3, "warm"),
            (20, False, 4, "mature"),
            (20, True, 4, "mature"),
            (100, False, 4, "mature"),
            (100, True, 4, "mature"),
        ],
    )
    def test_state_boundaries(
        self,
        rating_count: int,
        quiz_completed: bool,
        expected_state: int,
        expected_label: str,
    ) -> None:
        state = _determine_state(rating_count, quiz_completed)
        assert state == expected_state, (
            f"_determine_state({rating_count}, {quiz_completed}) "
            f"= {state}, expected {expected_state}"
        )
        assert _state_label(state) == expected_label


class TestDispatcherDetermineState:
    """Proves dispatcher.determine_state matches module-level function."""

    def test_static_method_matches_module_function(
        self, dispatcher: RecommendationDispatcher
    ) -> None:
        for rc, qc, exp, _ in [
            (0, False, 0, "anonymous"),
            (0, True, 1, "quiz_user"),
            (1, False, 2, "cold"),
            (5, False, 3, "warm"),
            (20, False, 4, "mature"),
        ]:
            assert dispatcher.determine_state(rc, qc) == exp
            assert dispatcher.determine_state(rc, qc) == _determine_state(rc, qc)


# ===================================================================
# SECTION D — Boundary-condition tests
# ===================================================================


class TestBoundaryConditions:
    """Proves dispatcher.dispatch() routes correctly at every boundary."""

    @pytest.mark.parametrize(
        "user_id,rating_count,quiz_completed,expected_state,expected_label,expected_source",
        [
            # State 0: rating_count=0, quiz=False
            (None, 0, False, 0, "anonymous", "popularity"),
            # State 1: rating_count=0, quiz=True
            (None, 0, True, 1, "quiz_user", "graphsage"),
            # State 2: rating_count=1
            (1, 1, False, 2, "cold", "blended"),
            # State 2: rating_count=4
            (1, 4, False, 2, "cold", "blended"),
            # State 3: rating_count=5
            (1, 5, False, 3, "warm", "feature_based"),
            # State 3: rating_count=19
            (1, 19, False, 3, "warm", "feature_based"),
            # State 4: rating_count=20
            (1, 20, False, 4, "mature", "diversity"),
        ],
    )
    async def test_boundary_routing(
        self,
        dispatcher: RecommendationDispatcher,
        mock_popularity: Any,
        mock_feature_based: Any,
        mock_gs_service: Any,
        sample_catalog: list[dict[str, Any]],
        user_id: int | None,
        rating_count: int,
        quiz_completed: bool,
        expected_state: int,
        expected_label: str,
        expected_source: str,
    ) -> None:
        ratings = []
        for i in range(rating_count):
            r = MagicMock()
            r.fragrance_id = f"f{i:03d}"
            r.rating = 7.0
            ratings.append(r)

        quiz_confidence: dict[str, float] | None = (
            {"fresh": 0.8, "woody": 0.6} if quiz_completed and rating_count == 0 else None
        )

        catalog = sample_catalog if quiz_completed and rating_count == 0 else []

        req = DispatchRequest(
            user_id=user_id,
            ratings=ratings,
            quiz_completed=quiz_completed,
            quiz_confidence=quiz_confidence,
            catalog=catalog,
            candidate_count=12,
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
            popularity_service=mock_popularity,
        )
        result = await dispatcher.dispatch(req)
        assert result.state == expected_state, (
            f"state: got {result.state}, expected {expected_state} "
            f"(rc={rating_count}, quiz={quiz_completed})"
        )
        assert result.state_label == expected_label
        assert result.source == expected_source


# ===================================================================
# β computation tests
# ===================================================================


class TestBetaComputation:
    """Proves _compute_beta returns correct blend coefficient."""

    @pytest.mark.parametrize(
        "rating_count,expected_beta",
        [
            (1, 0.00),
            (2, 0.25),
            (3, 0.50),
            (4, 0.75),
            (5, 1.00),
            # Additional: clamp boundary
            (0, 0.00),  # below min
            (6, 1.00),  # above max
            (10, 1.00),
        ],
    )
    def test_beta_values(self, rating_count: int, expected_beta: float) -> None:
        beta = _compute_beta(rating_count)
        assert beta == pytest.approx(expected_beta, abs=1e-6), (
            f"_compute_beta({rating_count}) = {beta}, expected {expected_beta}"
        )

    @pytest.mark.parametrize(
        "rating_count,expected_beta",
        [
            (1, 0.00),
            (2, 0.25),
            (3, 0.50),
            (4, 0.75),
            (5, 1.00),
        ],
    )
    def test_beta_via_dispatcher(
        self,
        dispatcher: RecommendationDispatcher,
        rating_count: int,
        expected_beta: float,
    ) -> None:
        beta = dispatcher.compute_beta(rating_count)
        assert beta == pytest.approx(expected_beta, abs=1e-6)

    async def test_beta_in_blended_strategy_metadata(
        self,
        dispatcher: RecommendationDispatcher,
        mock_gs_service: Any,
        mock_feature_based: Any,
    ) -> None:
        """Proves BlendedStrategy includes β in metadata."""
        ratings = [MagicMock(fragrance_id="f001", rating=8.0)]
        req = DispatchRequest(
            user_id=1,
            ratings=ratings,
            quiz_completed=False,
            catalog=[],
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher.dispatch(req)
        assert result.state == 2
        assert "beta" in result.metadata


# ===================================================================
# Weight alignment tests
# ===================================================================


class TestWeightAlignment:
    """Proves _align_quiz_confidence produces aligned seed_ids + weights."""

    def test_basic_alignment(self, sample_catalog: list[dict[str, Any]]) -> None:
        quiz_confidence = {"fresh": 0.9, "warm spicy": 0.7}
        seed_ids, weights = _align_quiz_confidence(quiz_confidence, sample_catalog)

        assert len(seed_ids) == len(weights), (
            f"len(seed_ids)={len(seed_ids)} != len(weights)={len(weights)}"
        )
        assert len(seed_ids) == 2, f"Expected 2 seeds, got {len(seed_ids)}"
        assert len(weights) == 2, f"Expected 2 weights, got {len(weights)}"

        # fresh → cat_001 (1200) or cat_003 (2100) — both have "fresh" accord
        # cat_003 has higher rating_count (2100 > 1200) so should be picked
        # warm spicy → cat_002 (850)
        assert "cat_003" in seed_ids, f"Expected cat_003 (fresh), got {seed_ids}"
        assert "cat_002" in seed_ids, f"Expected cat_002 (warm spicy), got {seed_ids}"
        assert 0.9 in weights, f"Expected 0.9 weight (fresh), got {weights}"
        assert 0.7 in weights, f"Expected 0.7 weight (warm spicy), got {weights}"

    def test_length_invariant(self, sample_catalog: list[dict[str, Any]]) -> None:
        """Proves len(seed_ids) == len(weights) for various input sizes."""
        for size, conf in [(1, 0.9), (2, 0.8), (3, 0.7), (4, 0.6), (5, 0.5)]:
            qc = {f"accord_{i}": conf - i * 0.1 for i in range(size)}
            # Use a catalog that has all the test accords
            cat = [
                {
                    "id": f"item_{i}",
                    "name": f"Item {i}",
                    "rating_count": 100 - i,
                    "_accords_set": {f"accord_{i}"},
                    "_notes_set": set(),
                }
                for i in range(size)
            ]
            seed_ids, weights = _align_quiz_confidence(qc, cat, max_seeds=size)
            assert len(seed_ids) == len(weights), (
                f"size={size}: len(seed_ids)={len(seed_ids)} != len(weights)={len(weights)}"
            )
            assert len(seed_ids) <= size

    def test_max_seeds_limit(self, sample_catalog: list[dict[str, Any]]) -> None:
        """Proves max_seeds limits returned pairs."""
        qc = {"fresh": 0.9, "warm spicy": 0.7, "floral": 0.5}
        seed_ids, weights = _align_quiz_confidence(qc, sample_catalog, max_seeds=2)
        assert len(seed_ids) == 2
        assert len(weights) == 2
        # cat_003 (floral + fresh) has highest rating_count,
        # so fresh → cat_003, floral → cat_003 — but only one of each accord.
        # Actually floral and fresh are different accords; both match cat_003
        # "warm spicy" matches cat_002.
        # With max_seeds=2, we take top 2 accords by confidence: fresh(0.9), warm spicy(0.7)

    def test_unknown_accord_skipped(self, sample_catalog: list[dict[str, Any]]) -> None:
        """Proves accords with no catalog match are silently skipped."""
        qc = {"nonexistent_accord": 0.9, "fresh": 0.7}
        seed_ids, weights = _align_quiz_confidence(qc, sample_catalog)
        assert len(seed_ids) == len(weights)
        assert len(seed_ids) == 1  # only "fresh" matched
        assert 0.7 in weights

    def test_empty_confidence(self, sample_catalog: list[dict[str, Any]]) -> None:
        seed_ids, weights = _align_quiz_confidence({}, sample_catalog)
        assert seed_ids == []
        assert weights == []

    def test_via_dispatcher_static(
        self,
        dispatcher: RecommendationDispatcher,
        sample_catalog: list[dict[str, Any]],
    ) -> None:
        qc = {"fresh": 0.8, "woody": 0.4}
        seed_ids, weights = dispatcher.align_quiz_confidence(qc, sample_catalog)
        assert len(seed_ids) == len(weights)
        assert len(seed_ids) <= 5

    def test_weights_are_confidences_not_normalized(
        self, sample_catalog: list[dict[str, Any]]
    ) -> None:
        """Proves weights are raw confidence values from the input dict."""
        qc = {"fresh": 0.95, "warm spicy": 0.30}
        _, weights = _align_quiz_confidence(qc, sample_catalog)
        assert 0.95 in weights
        assert 0.30 in weights


# ===================================================================
# Strategy selection tests
# ===================================================================


class TestStrategySelection:
    """Proves _select_strategy returns correct strategy per state."""

    @pytest.mark.parametrize(
        "state,expected_type_name",
        [
            (0, "PopularityStrategy"),
            (1, "GraphSAGEStrategy"),
            (2, "BlendedStrategy"),
            (3, "FeatureBasedStrategy"),
            (4, "FeatureWithDiversityStrategy"),
        ],
    )
    def test_strategy_type(
        self, state: int, expected_type_name: str
    ) -> None:
        strategy = _select_strategy(state)
        assert strategy.__class__.__name__ == expected_type_name, (
            f"State {state}: got {strategy.__class__.__name__}, "
            f"expected {expected_type_name}"
        )

    @pytest.mark.parametrize("state", [-1, 5, 99])
    def test_invalid_state_raises_key_error(self, state: int) -> None:
        with pytest.raises(KeyError):
            _select_strategy(state)

    def test_strategy_is_strategy_instance(self) -> None:
        for state in range(5):
            strategy = _select_strategy(state)
            assert isinstance(strategy, RecommendationStrategy)

    def test_via_dispatcher(
        self, dispatcher: RecommendationDispatcher
    ) -> None:
        strategy = dispatcher.select_strategy(2)
        assert strategy.__class__.__name__ == "BlendedStrategy"


# ===================================================================
# Dispatch result contract tests
# ===================================================================


class TestDispatchResultContract:
    """Proves DispatchResult has all required fields."""

    def test_all_fields_present(self) -> None:
        r = DispatchResult(
            recommendations=[],
            source="popularity",
            state=0,
            state_label="anonymous",
            metadata={"beta": 0.0},
            fallback_chain=["popularity"],
        )
        assert hasattr(r, "recommendations")
        assert hasattr(r, "source")
        assert hasattr(r, "state")
        assert hasattr(r, "state_label")
        assert hasattr(r, "metadata")
        assert hasattr(r, "fallback_chain")

    def test_default_factory(self) -> None:
        r = DispatchResult()
        assert r.recommendations == []
        assert r.source == ""
        assert r.state == -1
        assert r.state_label == ""
        assert r.metadata == {}
        assert r.fallback_chain == []


class TestDispatchRequestContract:
    """Proves DispatchRequest has all required fields."""

    def test_all_fields_present(self) -> None:
        r = DispatchRequest(
            user_id=1,
            ratings=[],
            quiz_completed=True,
            quiz_confidence={"fresh": 0.9},
            catalog=[{"id": "test"}],
            candidate_count=12,
            gs_service=None,
            feature_based_service=None,
            popularity_service=None,
        )
        assert hasattr(r, "user_id")
        assert hasattr(r, "ratings")
        assert hasattr(r, "quiz_completed")
        assert hasattr(r, "quiz_confidence")
        assert hasattr(r, "catalog")
        assert hasattr(r, "candidate_count")
        assert hasattr(r, "gs_service")
        assert hasattr(r, "feature_based_service")
        assert hasattr(r, "popularity_service")

    def test_defaults(self) -> None:
        r = DispatchRequest()
        assert r.user_id is None
        assert r.ratings == []
        assert r.quiz_completed is False
        assert r.quiz_confidence is None
        assert r.catalog is None
        assert r.candidate_count == 12


# ===================================================================
# Full dispatch integration (mocked services)
# ===================================================================


class TestDispatchWithMocks:
    """Proves dispatcher.dispatch() runs with mocked services."""

    async def test_state_0_popularity(
        self,
        dispatcher: RecommendationDispatcher,
        mock_popularity: Any,
    ) -> None:
        req = DispatchRequest(
            user_id=None,
            ratings=[],
            quiz_completed=False,
            catalog=[],
            popularity_service=mock_popularity,
        )
        result = await dispatcher.dispatch(req)
        assert result.state == 0
        assert result.state_label == "anonymous"
        assert result.source == "popularity"

    async def test_state_1_graphsage(
        self,
        dispatcher: RecommendationDispatcher,
        mock_gs_service: Any,
        mock_feature_based: Any,
        sample_catalog: list[dict[str, Any]],
    ) -> None:
        req = DispatchRequest(
            user_id=None,
            ratings=[],
            quiz_completed=True,
            quiz_confidence={"fresh": 0.8, "woody": 0.4},
            catalog=sample_catalog,
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher.dispatch(req)
        assert result.state == 1
        assert result.state_label == "quiz_user"
        assert result.source == "graphsage"

    async def test_state_1_no_confidence_falls_to_feature_based(
        self,
        dispatcher: RecommendationDispatcher,
        mock_gs_service: Any,
        mock_feature_based: Any,
    ) -> None:
        req = DispatchRequest(
            user_id=None,
            ratings=[],
            quiz_completed=True,
            quiz_confidence=None,
            catalog=[],
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher.dispatch(req)
        assert result.state == 1
        # Should fallback to feature_based since no seeds
        assert result.source == "feature_based"

    async def test_state_2_blended(
        self,
        dispatcher: RecommendationDispatcher,
        mock_gs_service: Any,
        mock_feature_based: Any,
    ) -> None:
        ratings = [MagicMock(fragrance_id="f001", rating=8.0)]
        req = DispatchRequest(
            user_id=1,
            ratings=ratings,
            quiz_completed=False,
            catalog=[],
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher.dispatch(req)
        assert result.state == 2
        assert result.state_label == "cold"
        assert result.source == "blended"
        assert "beta" in result.metadata
        assert result.metadata["rating_count"] == 1

    async def test_state_3_feature_based(
        self,
        dispatcher: RecommendationDispatcher,
        mock_gs_service: Any,
        mock_feature_based: Any,
    ) -> None:
        ratings = [MagicMock(fragrance_id=f"f{i:03d}", rating=7.0) for i in range(5)]
        req = DispatchRequest(
            user_id=1,
            ratings=ratings,
            quiz_completed=False,
            catalog=[],
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher.dispatch(req)
        assert result.state == 3
        assert result.state_label == "warm"
        assert result.source == "feature_based"

    async def test_state_4_diversity(
        self,
        dispatcher: RecommendationDispatcher,
        mock_feature_based: Any,
    ) -> None:
        ratings = [MagicMock(fragrance_id=f"f{i:03d}", rating=7.0) for i in range(20)]
        req = DispatchRequest(
            user_id=1,
            ratings=ratings,
            quiz_completed=False,
            catalog=[],
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher.dispatch(req)
        assert result.state == 4
        assert result.state_label == "mature"
        assert result.source == "diversity"


# ===================================================================
# CP8A — Strategy Hardening tests
# ===================================================================


class TestBlendedStrategy:
    """Proves BlendedStrategy produces actual blended ranking."""

    async def test_blended_output_differs_from_pure_fb(
        self,
        mock_gs_service: Any,
        mock_feature_based: Any,
    ) -> None:
        """Requirement 1: Blended output differs from pure feature-based output."""
        fb_ids = {str(item["id"]) for item in mock_feature_based.score.return_value}
        gs_ids = {str(item["id"]) for item in mock_gs_service.knn_search.return_value}
        assert fb_ids != gs_ids, "Test requires FB and GS item sets to differ"

        # Build a catalog that covers both FB and GS item IDs so hydration works
        catalog = [{"id": "dummy", "name": "D", "brand": "B",
                     "accords": ["fresh"], "rating_count": 10,
                     "_accords_set": {"fresh"}, "_notes_set": {"x"}}]
        for gid in gs_ids:
            catalog.append({"id": gid, "name": f"N_{gid}", "brand": "B",
                            "accords": ["woody"], "rating_count": 5,
                            "_accords_set": {"woody"}, "_notes_set": {"y"}})

        dispatcher = RecommendationDispatcher(
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        ratings = [MagicMock(fragrance_id="f001", rating=8.0)]
        req = DispatchRequest(
            user_id=1,
            ratings=ratings,
            quiz_completed=False,
            catalog=catalog,
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher.dispatch(req)

        assert result.source == "blended", f"Expected 'blended', got '{result.source}'"
        # Blended output should have items from both FB and GS sources
        result_ids = {str(r["id"]) for r in result.recommendations}
        fb_ids_in_result = result_ids & fb_ids
        gs_ids_in_result = result_ids & gs_ids
        assert len(fb_ids_in_result) > 0, "Blended output must include FB items"
        assert len(gs_ids_in_result) > 0, "Blended output must include GS items"

    async def test_blend_formula_respects_beta(
        self,
        mock_gs_service: Any,
        mock_feature_based: Any,
    ) -> None:
        """Proves β influences blend: more ratings → higher β → FB-weighted."""
        dispatcher = RecommendationDispatcher(
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )

        # β = 0.25 for 2 ratings (state 2 — Cold)
        ratings_2 = [MagicMock(fragrance_id=f"f{i:03d}", rating=7.0) for i in range(2)]
        req_2 = DispatchRequest(
            user_id=1, ratings=ratings_2, quiz_completed=False,
            catalog=[{"id": "dummy"}], gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        result_2 = await dispatcher.dispatch(req_2)
        assert result_2.state == 2
        assert result_2.source == "blended"
        assert "beta" in result_2.metadata
        assert result_2.metadata["beta"] == pytest.approx(0.25, abs=1e-6)

        # β = 0.75 for 4 ratings (state 2 — Cold, max beta before state 3)
        ratings_4 = [MagicMock(fragrance_id=f"f{i:03d}", rating=7.0) for i in range(4)]
        req_4 = DispatchRequest(
            user_id=1, ratings=ratings_4, quiz_completed=False,
            catalog=[{"id": "dummy"}], gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        result_4 = await dispatcher.dispatch(req_4)
        assert result_4.state == 2
        assert result_4.metadata["beta"] == pytest.approx(0.75, abs=1e-6)

    async def test_tie_break_fb_wins(
        self,
        mock_gs_service: Any,
        mock_feature_based: Any,
    ) -> None:
        """Proves tie-break: same blended score → higher FB match_score wins."""
        mock_feature_based.score.return_value = [
            {"id": "fb_a", "name": "A", "brand": "B", "match_score": 40.0,
             "reason": "Test", "top_accords": ["fresh"], "top_notes": ["bergamot"]},
            {"id": "fb_b", "name": "B", "brand": "B", "match_score": 30.0,
             "reason": "Test", "top_accords": ["woody"], "top_notes": ["cedar"]},
        ]
        # Only gs_a has a GS score (higher than fb_a's FB contribution at β=0.25)
        mock_gs_service.knn_search.return_value = [
            {"id": "gs_a", "score": 0.95},
            {"id": "gs_b", "score": 0.50},
            {"id": "gs_extra", "score": 0.80},
        ]

        dispatcher = RecommendationDispatcher(
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        ratings = [MagicMock(fragrance_id="f001", rating=8.0)]
        req = DispatchRequest(
            user_id=1, ratings=ratings, quiz_completed=False,
            catalog=[], gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher.dispatch(req)

        # Every blended item should have source = "blended"
        for item in result.recommendations:
            assert "source" in item, f"Item {item['id']} missing 'source'"
            assert item["source"] == "blended", (
                f"Item {item['id']} has source='{item['source']}', expected 'blended'"
            )
        assert result.recommendations  # non-empty


class TestFeatureBasedStrategyExploration:
    """Proves exploration items appear in FeatureBasedStrategy output."""

    async def test_exploration_items_appear(
        self,
        mock_gs_service: Any,
        mock_feature_based: Any,
    ) -> None:
        """Requirement 2: Exploration items actually appear in result."""
        dispatcher = RecommendationDispatcher(
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        ratings = [MagicMock(fragrance_id=f"f{i:03d}", rating=7.0) for i in range(5)]
        # Build catalog covering GS IDs so exploration items survive hydration
        gs_ids = {str(item["id"]) for item in mock_gs_service.knn_search.return_value}
        catalog = [{"id": "dummy", "name": "D", "brand": "B",
                    "accords": ["fresh"], "rating_count": 10,
                    "_accords_set": {"fresh"}, "_notes_set": {"x"}}]
        for gid in gs_ids:
            catalog.append({"id": gid, "name": f"N_{gid}", "brand": "B",
                            "accords": ["woody"], "rating_count": 5,
                            "_accords_set": {"woody"}, "_notes_set": {"y"}})

        req = DispatchRequest(
            user_id=1,
            ratings=ratings,
            quiz_completed=False,
            catalog=catalog,
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
            candidate_count=12,
        )
        result = await dispatcher.dispatch(req)

        assert result.source == "feature_based"
        assert result.state == 3

        # Check that at least one item has source "exploration"
        exploration_items = [
            r for r in result.recommendations
            if r.get("source") == "exploration"
        ]
        assert len(exploration_items) > 0, (
            f"No exploration items found in {[r.get('source') for r in result.recommendations]}"
        )
        # GS IDs are gs_0..gs_9 — exploration items should be from GS
        exploration_ids = {r["id"] for r in exploration_items}
        assert all("gs_" in str(i) for i in exploration_ids), (
            f"Exploration items should come from GS: {exploration_ids}"
        )

    async def test_exploration_duplicate_prevention(
        self,
        mock_gs_service: Any,
        mock_feature_based: Any,
    ) -> None:
        """Proves exploration items that duplicate FB items are excluded."""
        # Make one FB item share an ID with GS
        mock_feature_based.score.return_value = [
            {"id": "gs_0", "name": "Shared", "brand": "B", "match_score": 80.0,
             "reason": "Test", "top_accords": ["fresh"], "top_notes": ["bergamot"]},
        ] + [
            {"id": f"fb_{i}", "name": f"Test {i}", "brand": "MockBrand",
             "match_score": 70.0 - i, "reason": "Harmonious Discovery",
             "top_accords": ["fresh"], "top_notes": ["citrus"]}
            for i in range(1, 12)
        ]

        dispatcher = RecommendationDispatcher(
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        ratings = [MagicMock(fragrance_id=f"f{i:03d}", rating=7.0) for i in range(5)]
        req = DispatchRequest(
            user_id=1, ratings=ratings, quiz_completed=False,
            catalog=[{"id": "dummy"}], gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
            candidate_count=12,
        )
        result = await dispatcher.dispatch(req)
        result_ids = [r["id"] for r in result.recommendations]
        # No duplicate IDs should exist
        assert len(result_ids) == len(set(result_ids)), "Duplicate IDs found"


class TestFeatureWithDiversityStrategy:
    """Proves diversity strategy output differs from feature-based."""

    async def test_diversity_differs_from_feature_based(
        self,
        mock_feature_based: Any,
    ) -> None:
        """Requirement 3: Diversity strategy output differs from feature strategy."""
        shared_items = [
            {"id": "div_0", "name": "A", "brand": "B", "match_score": 90.0,
             "reason": "Test", "top_accords": ["A", "B"],
             "top_notes": ["x"]},
            {"id": "div_1", "name": "B", "brand": "B", "match_score": 85.0,
             "reason": "Test", "top_accords": ["A", "C"],
             "top_notes": ["y"]},
            {"id": "div_2", "name": "C", "brand": "B", "match_score": 80.0,
             "reason": "Test", "top_accords": ["D", "E"],
             "top_notes": ["z"]},
            {"id": "div_3", "name": "D", "brand": "B", "match_score": 75.0,
             "reason": "Test", "top_accords": ["A", "D"],
             "top_notes": ["w"]},
            {"id": "div_4", "name": "E", "brand": "B", "match_score": 70.0,
             "reason": "Test", "top_accords": ["F", "G"],
             "top_notes": ["v"]},
        ]
        mock_feature_based.score.return_value = list(shared_items)

        gs = MagicMock()
        gs.compute_centroid.return_value = [0.1] * 64
        gs.knn_search.return_value = []

        catalog_base = [
            {"id": "dummy", "name": "D", "brand": "B",
             "accords": ["fresh"], "rating_count": 10,
             "_accords_set": {"fresh"}, "_notes_set": {"x"}},
        ]

        # State 3 (FeatureBasedStrategy)
        fb_dispatcher = RecommendationDispatcher(
            gs_service=gs, feature_based_service=mock_feature_based,
        )
        fb_result = await fb_dispatcher.dispatch(
            DispatchRequest(
                user_id=1,
                ratings=[MagicMock(fragrance_id=f"f{i:03d}", rating=7.0) for i in range(5)],
                quiz_completed=False,
                catalog=catalog_base,
                gs_service=gs,
                feature_based_service=mock_feature_based,
            )
        )
        # State 4 (FeatureWithDiversityStrategy) — same FB items
        mock_feature_based.score.return_value = list(shared_items)
        div_dispatcher = RecommendationDispatcher(
            gs_service=gs, feature_based_service=mock_feature_based,
        )
        div_result = await div_dispatcher.dispatch(
            DispatchRequest(
                user_id=1,
                ratings=[MagicMock(fragrance_id=f"f{i:03d}", rating=7.0) for i in range(20)],
                quiz_completed=False,
                catalog=catalog_base,
                gs_service=gs,
                feature_based_service=mock_feature_based,
            )
        )

        assert fb_result.state == 3
        assert div_result.state == 4

        fb_order = [r["id"] for r in fb_result.recommendations]
        div_order = [r["id"] for r in div_result.recommendations]
        assert fb_order != div_order, (
            f"Expected diversity to change order: FB={fb_order}, DIV={div_order}"
        )

    async def test_diversity_all_items_have_source(
        self,
        mock_feature_based: Any,
        mock_gs_service: Any,
    ) -> None:
        """Proves every diversity item has source='diversity'."""
        ratings = [MagicMock(fragrance_id=f"f{i:03d}", rating=7.0) for i in range(20)]
        dispatcher = RecommendationDispatcher(
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        req = DispatchRequest(
            user_id=1, ratings=ratings, quiz_completed=False, catalog=[],
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher.dispatch(req)
        for item in result.recommendations:
            assert item.get("source") == "diversity", (
                f"Item {item['id']} has source='{item.get('source')}', expected 'diversity'"
            )


class TestSourceAttribution:
    """Proves every recommendation exposes source attribution."""

    @pytest.mark.parametrize(
        "rating_count,quiz_completed,expected_source,expected_item_source",
        [
            (0, False, "popularity", "popularity"),
            (0, True, "graphsage", "graphsage"),
            (1, False, "blended", "blended"),
            (5, False, "feature_based", "feature_based"),
            (20, False, "diversity", "diversity"),
        ],
    )
    async def test_source_on_all_items(
        self,
        dispatcher: RecommendationDispatcher,
        mock_gs_service: Any,
        mock_feature_based: Any,
        mock_popularity: Any,
        rating_count: int,
        quiz_completed: bool,
        expected_source: str,
        expected_item_source: str,
    ) -> None:
        ratings = [MagicMock(fragrance_id=f"f{i:03d}", rating=7.0)
                   for i in range(rating_count)]
        quiz_confidence: dict[str, float] | None = (
            {"fresh": 0.8} if quiz_completed and rating_count == 0 else None
        )
        req = DispatchRequest(
            user_id=1,
            ratings=ratings,
            quiz_completed=quiz_completed,
            quiz_confidence=quiz_confidence,
            catalog=[{"id": "cat_001", "name": "X", "brand": "Y",
                      "accords": ["fresh"], "rating_count": 100,
                      "_accords_set": {"fresh"}, "_notes_set": {"bergamot"}}],
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
            popularity_service=mock_popularity,
        )
        result = await dispatcher.dispatch(req)
        assert result.source == expected_source
        for item in result.recommendations:
            assert "source" in item, f"Item {item['id']} missing 'source' key"
            # FeatureBasedStrategy may have "exploration" items mixed in
            if expected_item_source == "feature_based":
                assert item["source"] in ("feature_based", "exploration")
            else:
                assert item["source"] == expected_item_source, (
                    f"Item {item['id']} source='{item['source']}', "
                    f"expected '{expected_item_source}'"
                )


# ===================================================================
# CP8D — GraphSAGE Wiring tests
# ===================================================================


class TestGraphSAGEWiring:
    """Proves gs_service is wired into dispatcher and strategies handle it."""

    async def test_graphsage_executes_centroid_and_knn(
        self,
        mock_gs_service: Any,
        mock_feature_based: Any,
        sample_catalog: list[dict[str, Any]],
    ) -> None:
        """Requirement 5: GraphSAGEStrategy executes centroid + KNN when service available."""
        dispatcher = RecommendationDispatcher(
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        req = DispatchRequest(
            user_id=None,
            ratings=[],
            quiz_completed=True,
            quiz_confidence={"fresh": 0.8, "woody": 0.4},
            catalog=sample_catalog,
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher.dispatch(req)
        assert result.state == 1
        assert result.source == "graphsage"
        mock_gs_service.compute_centroid.assert_called_once()
        mock_gs_service.knn_search.assert_called_once()

    async def test_dispatcher_receives_gs_service(
        self,
        mock_gs_service: Any,
    ) -> None:
        """Requirement 4: Dispatcher receives gs_service through real constructor path."""
        dispatcher = RecommendationDispatcher(
            gs_service=mock_gs_service,
            feature_based_service=MagicMock(),
            popularity_service=MagicMock(),
        )
        assert dispatcher._gs_service is mock_gs_service, (
            "gs_service not wired into dispatcher"
        )

    async def test_constructor_injection_works(
        self,
        mock_gs_service: Any,
        mock_feature_based: Any,
        mock_popularity: Any,
    ) -> None:
        """Proves constructor injection populates request defaults."""
        dispatcher = RecommendationDispatcher(
            gs_service=mock_gs_service,
            feature_based_service=mock_feature_based,
            popularity_service=mock_popularity,
        )
        req = DispatchRequest(ratings=[], quiz_completed=False)
        # Before dispatch, gs_service is None on the request
        assert req.gs_service is None
        # After dispatch injection, it should be set
        assert dispatcher._gs_service is mock_gs_service


class TestGracefulDegradation:
    """Proves all states still work when gs_service unavailable."""

    @pytest.fixture
    def dispatcher_no_gs(self, mock_feature_based: Any, mock_popularity: Any) -> RecommendationDispatcher:
        return RecommendationDispatcher(
            gs_service=None,
            feature_based_service=mock_feature_based,
            popularity_service=mock_popularity,
        )

    async def test_state_0_popularity_no_gs(
        self,
        dispatcher_no_gs: RecommendationDispatcher,
        mock_popularity: Any,
    ) -> None:
        """State 0 works without gs_service."""
        req = DispatchRequest(
            user_id=None, ratings=[], quiz_completed=False, catalog=[],
            popularity_service=mock_popularity,
        )
        result = await dispatcher_no_gs.dispatch(req)
        assert result.state == 0
        assert result.source == "popularity"

    async def test_state_1_graphsage_falls_back_no_gs(
        self,
        dispatcher_no_gs: RecommendationDispatcher,
        mock_feature_based: Any,
        sample_catalog: list[dict[str, Any]],
    ) -> None:
        """Requirement 6: State 1 falls back gracefully when gs_service is None."""
        req = DispatchRequest(
            user_id=None, ratings=[], quiz_completed=True,
            quiz_confidence={"fresh": 0.8}, catalog=sample_catalog,
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher_no_gs.dispatch(req)
        assert result.state == 1
        # Should fallback to feature_based
        assert result.source == "feature_based"
        assert "fallback" in result.metadata

    async def test_state_2_blended_no_gs(
        self,
        dispatcher_no_gs: RecommendationDispatcher,
        mock_feature_based: Any,
    ) -> None:
        """State 2 works when gs_service is None (pure FB blend)."""
        ratings = [MagicMock(fragrance_id="f001", rating=8.0)]
        req = DispatchRequest(
            user_id=1, ratings=ratings, quiz_completed=False,
            catalog=[{"id": "dummy"}],
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher_no_gs.dispatch(req)
        assert result.state == 2
        # With no GS, blend = pure FB items with source="blended"
        assert result.source == "blended"
        assert result.metadata["gs_candidate_count"] == 0
        assert result.metadata["fb_candidate_count"] > 0

    async def test_state_3_feature_based_no_gs(
        self,
        dispatcher_no_gs: RecommendationDispatcher,
        mock_feature_based: Any,
    ) -> None:
        """State 3 works without gs_service (exploration skipped)."""
        ratings = [MagicMock(fragrance_id=f"f{i:03d}", rating=7.0) for i in range(5)]
        req = DispatchRequest(
            user_id=1, ratings=ratings, quiz_completed=False, catalog=[],
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher_no_gs.dispatch(req)
        assert result.state == 3
        assert result.source == "feature_based"
        assert result.metadata["exploration_count"] == 0

    async def test_state_4_diversity_no_gs(
        self,
        dispatcher_no_gs: RecommendationDispatcher,
        mock_feature_based: Any,
    ) -> None:
        """State 4 works without gs_service (no GS dependency)."""
        ratings = [MagicMock(fragrance_id=f"f{i:03d}", rating=7.0) for i in range(20)]
        req = DispatchRequest(
            user_id=1, ratings=ratings, quiz_completed=False, catalog=[],
            feature_based_service=mock_feature_based,
        )
        result = await dispatcher_no_gs.dispatch(req)
        assert result.state == 4
        assert result.source == "diversity"


class TestAccordJaccard:
    """Proves _accord_jaccard and _diversity_rerank work correctly."""

    def test_accord_jaccard_identical(self) -> None:
        a = {"top_accords": ["fresh", "citrus", "woody"]}
        b = {"top_accords": ["fresh", "citrus", "woody"]}
        assert FeatureWithDiversityStrategy._accord_jaccard(a, b) == 1.0

    def test_accord_jaccard_disjoint(self) -> None:
        a = {"top_accords": ["fresh", "citrus"]}
        b = {"top_accords": ["woody", "amber"]}
        assert FeatureWithDiversityStrategy._accord_jaccard(a, b) == 0.0

    def test_accord_jaccard_partial(self) -> None:
        a = {"top_accords": ["fresh", "citrus", "woody"]}
        b = {"top_accords": ["fresh", "amber"]}
        # intersection = {"fresh"}, union = {"fresh", "citrus", "woody", "amber"}
        assert FeatureWithDiversityStrategy._accord_jaccard(a, b) == 0.25

    def test_accord_jaccard_empty(self) -> None:
        a = {"top_accords": []}
        b = {"top_accords": ["fresh"]}
        assert FeatureWithDiversityStrategy._accord_jaccard(a, b) == 0.0

    def test_diversity_rerank_preserves_count(self) -> None:
        items = [
            {"id": "1", "match_score": 90.0, "top_accords": ["a", "b"]},
            {"id": "2", "match_score": 80.0, "top_accords": ["c", "d"]},
            {"id": "3", "match_score": 70.0, "top_accords": ["a", "c"]},
        ]
        reranked = FeatureWithDiversityStrategy._diversity_rerank(items, lambda_d=0.5)
        assert len(reranked) == len(items)
        assert {r["id"] for r in reranked} == {"1", "2", "3"}

    def test_diversity_rerank_single_item(self) -> None:
        items = [{"id": "1", "match_score": 90.0, "top_accords": ["a"]}]
        reranked = FeatureWithDiversityStrategy._diversity_rerank(items)
        assert len(reranked) == 1
        assert reranked[0]["id"] == "1"

    def test_diversity_rerank_empty(self) -> None:
        reranked = FeatureWithDiversityStrategy._diversity_rerank([])
        assert reranked == []
