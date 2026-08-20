"""Dispatcher state-machine tests: determine_state + dispatch routing."""

from types import SimpleNamespace

from app.services.catalog import get_catalog
from app.services.dispatcher import (
    ANONYMOUS,
    COLD,
    WARM,
    RecommendationDispatcher,
    determine_state,
)


def _req(ratings, quiz_submitted=False, candidate_count=12):
    return SimpleNamespace(
        ratings=ratings,
        quiz_submitted=quiz_submitted,
        candidate_count=candidate_count,
    )


def _rating(fid, value):
    return SimpleNamespace(fragrance_id=fid, rating=value)


def test_determine_state_no_ratings_no_quiz_is_anonymous():
    assert determine_state(0, False) == ANONYMOUS


def test_determine_state_quiz_flag_or_few_ratings_is_cold():
    assert determine_state(0, True) == COLD
    assert determine_state(1, False) == COLD
    assert determine_state(2, False) == COLD


def test_determine_state_three_plus_ratings_is_warm_and_beats_quiz_flag():
    assert determine_state(3, False) == WARM
    assert determine_state(10, True) == WARM


def test_dispatch_anonymous_returns_popularity():
    result = RecommendationDispatcher().dispatch(_req([]))
    assert result["state"] == ANONYMOUS
    assert result["source"] == "popularity"
    assert result["recommendations"]
    assert result["recommendations"][0]["reason"] == "Popular Choice"


def test_dispatch_cold_returns_embeddings():
    catalog = get_catalog()
    ratings = [_rating(catalog[0]["id"], 8), _rating(catalog[1]["id"], 5)]
    result = RecommendationDispatcher().dispatch(_req(ratings))
    assert result["state"] == COLD
    assert result["source"] == "embeddings"
    assert result["recommendations"]
    assert all("id" in item and "match_score" in item for item in result["recommendations"])


def test_dispatch_warm_returns_feature_based():
    catalog = get_catalog()
    ratings = [
        _rating(catalog[0]["id"], 8),
        _rating(catalog[1]["id"], 5),
        _rating(catalog[2]["id"], 7),
    ]
    result = RecommendationDispatcher().dispatch(_req(ratings))
    assert result["state"] == WARM
    assert result["source"] == "feature_based"
    assert result["recommendations"]


def test_dispatch_cold_junk_ids_falls_back_to_popularity():
    ratings = [_rating("no-such-fragrance-1", 8), _rating("no-such-fragrance-2", 5)]
    result = RecommendationDispatcher().dispatch(_req(ratings))
    assert result["state"] == COLD
    assert result["source"] == "popularity"
    assert result["recommendations"][0]["reason"] == "Popular Choice"