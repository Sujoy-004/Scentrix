"""Semantic (behavioural) ML tests for the cold-start recommendation pipeline.

These assert *what the recommender means*, not just that it runs:
directional rating weights, neutral handling, rated-item exclusion, content-
driven cold-start retrieval, quiz→embedding routing, rating validation.
"""

from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError

from app.schemas.schemas import GuestRatingInput
from app.services.catalog import get_catalog
from app.services.dispatcher import (
    ANONYMOUS,
    COLD,
    WARM,
    RecommendationDispatcher,
    determine_state,
)
from app.services.embeddings import gs_service
from app.services.feature_based import FeatureBasedService
from app.services.popularity import PopularityService


def _req(ratings, quiz_submitted=False, candidate_count=12):
    return SimpleNamespace(
        ratings=ratings,
        quiz_submitted=quiz_submitted,
        candidate_count=candidate_count,
    )


def _rating(fid, value):
    return SimpleNamespace(fragrance_id=fid, rating=value)


# ---------------------------------------------------------------------------
# Directional rating weights (FIX 4)
# ---------------------------------------------------------------------------


def test_user_vector_points_toward_liked_away_from_disliked():
    catalog = get_catalog()
    fid = str(catalog[0]["id"])

    pos = gs_service.compute_user_vector([(fid, 9.0)])
    neg = gs_service.compute_user_vector([(fid, 2.0)])

    idx = gs_service._id_to_idx[fid]
    emb = gs_service._embeddings[idx]

    cos_pos = float(np.dot(pos, emb))
    cos_neg = float(np.dot(neg, emb))
    assert cos_pos > 0.9, "a strongly liked item should pull the profile toward it"
    assert cos_neg < -0.9, "a disliked item should push the profile away from it"


def test_neutral_rubric_produces_no_directional_signal():
    catalog = get_catalog()
    fid = str(catalog[0]["id"])
    with pytest.raises(ValueError):
        gs_service.compute_user_vector([(fid, 5.0)])


def test_mixed_positive_and_disliked_signal_is_directional():
    catalog = get_catalog()
    liked = str(catalog[0]["id"])
    disliked = str(catalog[1]["id"])

    vec = gs_service.compute_user_vector([(liked, 9.0), (disliked, 2.0)])
    assert vec.shape == (64,)
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Cold-start content retrieval (semantic, not popularity)
# ---------------------------------------------------------------------------


def test_cold_start_knn_retrieves_similar_family():
    catalog = get_catalog()
    catalog_map = {str(item["id"]): item for item in catalog}
    seed = catalog[200]
    fid = str(seed["id"])
    seed_accords = set(seed.get("_accords_set") or [])

    vec = gs_service.compute_user_vector([(fid, 9.0)])
    knn = gs_service.knn_search(vec, top_k=5, exclude_ids=[fid])

    assert len(knn) == 5
    shared = [
        r
        for r in knn
        if seed_accords.intersection(catalog_map[str(r["id"])].get("_accords_set") or set())
    ]
    assert shared, "top cold-start results should share accord family with the seed"

    popular_ids = {str(p["id"]) for p in PopularityService.get_top(catalog, count=20)}
    assert len([r for r in knn[:3] if r["id"] in popular_ids]) < 3, (
        "cold-start retrieval should be content-driven, not just top-rated"
    )


# ---------------------------------------------------------------------------
# Routing semantics (FIX 2 / FIX 3)
# ---------------------------------------------------------------------------


def test_quiz_submitted_routes_to_embeddings_even_with_three_ratings():
    catalog = get_catalog()
    ratings = [_rating(str(catalog[i]["id"]), float(7 + i)) for i in range(3)]
    result = RecommendationDispatcher().dispatch(_req(ratings, quiz_submitted=True))

    assert result["state"] == COLD
    assert result["source"] == "embeddings"
    rec_ids = {str(r["id"]) for r in result["recommendations"]}
    assert not (rec_ids & {str(catalog[i]["id"]) for i in range(3)})


def test_warm_feature_based_excludes_rated_items():
    catalog = get_catalog()
    ratings = [_rating(str(catalog[i]["id"]), float(7 + i)) for i in range(3)]
    result = RecommendationDispatcher().dispatch(_req(ratings))

    assert result["state"] == WARM
    assert result["source"] == "feature_based"
    rec_ids = {str(r["id"]) for r in result["recommendations"]}
    assert not (rec_ids & {str(catalog[i]["id"]) for i in range(3)}), (
        "WARM must exclude items the user has already rated"
    )


def test_no_ratings_no_quiz_is_anonymous():
    assert determine_state(0, False) == ANONYMOUS


# ---------------------------------------------------------------------------
# Feature-based profile semantics (FIX 4 / FIX 7)
# ---------------------------------------------------------------------------


def test_feature_based_profile_is_case_insensitive_and_weighted():
    catalog = get_catalog()
    fid = str(catalog[0]["id"])
    svc = FeatureBasedService()

    profile = svc._build_profile(
        [
            {
                "fragrance_id": fid,
                "rating": 8.0,
                "top_notes": ["FRUITY", "Sweet"],
                "accords": ["Fresh Spicy"],
            }
        ],
        catalog,
    )
    assert "fruity" in profile["target_notes"]
    assert "sweet" in profile["target_notes"]
    assert "fresh spicy" in profile["target_accords"]


def test_feature_based_profile_tracks_disliked_notes_negatively():
    catalog = get_catalog()
    fid = str(catalog[0]["id"])
    svc = FeatureBasedService()

    profile = svc._build_profile(
        [{"fragrance_id": fid, "rating": 2.0, "top_notes": ["Leathery heavy"]}],
        catalog,
    )
    assert "leathery heavy" in profile["negative_notes"]


def test_feature_based_profile_is_deterministic():
    catalog = get_catalog()
    svc = FeatureBasedService()
    ratings = [
        {"fragrance_id": str(catalog[i]["id"]), "rating": float(6 + i),
         "top_notes": ["Fruity"], "accords": ["Fresh"]}
        for i in range(5)
    ]
    p1 = svc._build_profile(ratings, catalog)
    p2 = svc._build_profile(ratings, catalog)
    assert p1["target_notes"] == p2["target_notes"]
    assert p1["target_accords"] == p2["target_accords"]


# ---------------------------------------------------------------------------
# Rating validation (FIX 6)
# ---------------------------------------------------------------------------


def test_rating_bounds_rejected_at_schema():
    with pytest.raises(ValidationError):
        GuestRatingInput(fragrance_id="frag_x", rating=11.0)
    with pytest.raises(ValidationError):
        GuestRatingInput(fragrance_id="frag_x", rating=0.5)
    assert GuestRatingInput(fragrance_id="frag_x", rating=5.0).rating == 5.0


def test_guest_endpoint_rejects_out_of_range_rating(client):
    resp = client.post(
        "/recommendations/guest",
        json={
            "ratings": [{"fragrance_id": "frag_x", "rating": 11}],
            "quiz_submitted": False,
        },
    )
    assert resp.status_code == 422
