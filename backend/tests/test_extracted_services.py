"""Behavior-equivalence tests for CP2 (feature_based) and CP3 (popularity).

Proves that FeatureBasedService and PopularityService produce IDENTICAL output
to the logic extracted from HybridRecommender (hybrid_search.py).
"""

from __future__ import annotations

from typing import Any

import pytest

from app.services.feature_based import FeatureBasedService
from app.services.popularity import PopularityService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_FAKE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "f001",
        "name": "Fresh Aqua",
        "brand": "Oceanic",
        "description": "A fresh aquatic scent with citrus and floral notes",
        "accords": ["aquatic", "fresh", "citrus"],
        "top_notes": ["bergamot", "lemon", "sea salt"],
        "rating_count": 1200,
        "rating_value": 4.2,
        "_notes_set": {"bergamot", "lemon", "sea salt", "lavender"},
        "_accords_set": {"aquatic", "fresh", "citrus"},
    },
    {
        "id": "f002",
        "name": "Warm Ember",
        "brand": "Noir",
        "description": "A warm spicy oriental fragrance with amber and tobacco",
        "accords": ["warm spicy", "amber", "tobacco"],
        "top_notes": ["cinnamon", "clove", "saffron"],
        "rating_count": 850,
        "rating_value": 4.5,
        "_notes_set": {"cinnamon", "clove", "saffron", "vanilla"},
        "_accords_set": {"warm spicy", "amber", "tobacco"},
    },
    {
        "id": "f003",
        "name": "Woodland Walk",
        "brand": "Botanic",
        "description": "Woody chypre with leather and earthy undertones",
        "accords": ["woody", "leather", "earthy"],
        "top_notes": ["oakmoss", "patchouli", "vetiver"],
        "rating_count": 320,
        "rating_value": 3.8,
        "_notes_set": {"oakmoss", "patchouli", "vetiver", "cedar"},
        "_accords_set": {"woody", "leather", "earthy"},
    },
    {
        "id": "f004",
        "name": "Floral Dream",
        "brand": "Jardin",
        "description": "A light floral bouquet with fruity accents",
        "accords": ["floral", "fruity", "fresh"],
        "top_notes": ["rose", "jasmine", "peach"],
        "rating_count": 2100,
        "rating_value": 4.0,
        "_notes_set": {"rose", "jasmine", "peach", "lily"},
        "_accords_set": {"floral", "fruity", "fresh"},
    },
    {
        "id": "f005",
        "name": "Midnight Oud",
        "brand": "Orient",
        "description": "Deep oriental leather and oud with animalic warmth",
        "accords": ["oud", "leather", "animalic", "balsamic"],
        "top_notes": ["labdanum", "myrrh", "castoreum"],
        "rating_count": 95,
        "rating_value": 4.7,
        "_notes_set": {"labdanum", "myrrh", "castoreum", "incense"},
        "_accords_set": {"oud", "leather", "animalic", "balsamic"},
    },
    {
        "id": "f006",
        "name": "Forest Pine",
        "brand": "Alpine",
        "description": "Woody aromatic with green and balsamic accords",
        "accords": ["woody", "aromatic", "balsamic", "green"],
        "top_notes": ["pine", "juniper", "cypress"],
        "rating_count": 450,
        "rating_value": 3.9,
        "_notes_set": {"pine", "juniper", "cypress", "moss"},
        "_accords_set": {"woody", "aromatic", "balsamic", "green"},
    },
]


@pytest.fixture
def catalog() -> list[dict[str, Any]]:
    return [dict(item) for item in _FAKE_CATALOG]


# ---------------------------------------------------------------------------
# CP2 — FeatureBasedService identity proof
# ---------------------------------------------------------------------------


class FakeRating:
    """Mimics the FragranceRatingInput / quiz-rating objects hybrid_search expects."""

    def __init__(
        self,
        fragrance_id: str,
        rating: float = 7.0,
        top_notes: list[str] | None = None,
        accords: list[str] | None = None,
    ):
        self.fragrance_id = fragrance_id
        self.rating = rating
        self.top_notes = top_notes or []
        self.accords = accords or []


def _hybrid_search_equivalent(
    ratings: list[Any],
    catalog: list[dict[str, Any]],
    seed_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Replicates the EXACT scoring logic from hybrid_search.py:get_recommendations()

    This is the reference implementation — it mirrors the original monolith code
    and is used to prove FeatureBasedService produces identical output.
    """
    import math

    if seed_ids is None:
        seed_ids = []
    seed_id_set = set(seed_ids)
    catalog_map = {str(item["id"]): item for item in catalog}

    # 1. Build Target Profile
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

        from app.services.hybrid_search import FRESH_ACCORDS, WARM_ACCORDS

        if any(a in FRESH_ACCORDS for a in item_accords):
            target_occasions.add("day")
        if any(a in WARM_ACCORDS for a in item_accords):
            target_occasions.add("night")

    if not target_notes and not target_accords:
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
            )[:12]
        ]

    # 2. Candidate Pooling
    candidate_pool: list[dict[str, Any]] = []
    target_notes_set = set(target_notes)
    target_accords_set = set(target_accords)

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

    # 3. Scoring
    scored: list[dict[str, Any]] = []
    user_embedding = None

    for item in candidate_pool:
        item_id = str(item["id"])
        if item_id in seed_id_set:
            continue

        item_notes = item.get("_notes_set", set())
        intersection_n = len(target_notes_set.intersection(item_notes))
        union_n = len(target_notes_set.union(item_notes))
        note_sim = (intersection_n / union_n) if union_n > 0 else 0

        item_accords = item.get("_accords_set", set())
        intersection_a = len(target_accords_set.intersection(item_accords))
        accord_sim = intersection_a / max(len(target_accords_set), 1)

        cat_match = 0.0
        desc = item.get("description", "").lower()
        for family in target_families:
            if family in desc or family in item_accords:
                cat_match = 1.0
                break

        occ_match = 0.0
        item_occ: set[str] = set()
        from app.services.hybrid_search import FRESH_ACCORDS, WARM_ACCORDS
        if any(a in FRESH_ACCORDS for a in item_accords):
            item_occ.add("day")
        if any(a in WARM_ACCORDS for a in item_accords):
            item_occ.add("night")
        if target_occasions.intersection(item_occ):
            occ_match = 1.0

        semantic_score = 0.0
        # (user_embedding is None in this test — no neural engine)

        rc = item.get("rating_count", 0)
        pop_count_score = min(math.log10(rc + 1) / 4.0, 1.0)
        rv = item.get("rating_value", 3.5)
        pop_val_score = (rv - 1.0) / 4.0
        popularity = (pop_count_score * 0.6) + (pop_val_score * 0.4)

        base_score = (
            (0.35 * note_sim)
            + (0.25 * accord_sim)
            + (0.15 * cat_match)
            + (0.15 * occ_match)
            + (0.10 * popularity)
        )

        scored.append({"id": item_id, "base_score": base_score, "item": item})

    # 4. Diversity Selection
    scored.sort(key=lambda x: x["base_score"], reverse=True)
    top_n = scored[:100]

    final_selections: list[dict[str, Any]] = []
    selected_accords_union: set[str] = set()

    for _ in range(12):
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

    # 5. Format Output
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


class TestFeatureBasedEquivalence:
    """Proves FeatureBasedService.score() == hybrid_search scoring logic."""

    def test_empty_catalog(self, catalog: list[dict[str, Any]]) -> None:
        fb = FeatureBasedService()
        assert fb.score([], []) == []
        # When catalog is None, the service loads the real catalog;
        # we verify at least it doesn't crash and returns something.
        result = fb.score([], None)
        assert isinstance(result, list)
        # When catalog is passed explicitly:
        result2 = fb.score([], catalog, [])
        assert isinstance(result2, list)
        assert len(result2) == 6  # our synthetic catalog has 6 items

    def test_empty_ratings_fallsback_to_popularity(
        self, catalog: list[dict[str, Any]]
    ) -> None:
        fb = FeatureBasedService()
        expected = _hybrid_search_equivalent([], catalog, [])
        actual = fb.score([], catalog, [])
        assert actual == expected

    def test_popularity_fallback_counts(
        self, catalog: list[dict[str, Any]]
    ) -> None:
        fb = FeatureBasedService()
        result = fb.score([], catalog, [])
        assert len(result) == 6  # only 6 items in catalog
        assert all(r["match_score"] == 50.0 for r in result)
        assert all(r["reason"] == "Popular Choice" for r in result)
        # Most popular first: Floral Dream (2100) > Fresh Aqua (1200) > Warm Ember (850)
        assert result[0]["id"] == "f004"  # Floral Dream
        assert result[1]["id"] == "f001"  # Fresh Aqua
        assert result[2]["id"] == "f002"  # Warm Ember

    @pytest.mark.parametrize(
        "ratings_fixture",
        [
            "single_rating",
            "two_ratings",
            "three_ratings",
            "rating_with_notes_and_accords",
        ],
    )
    def test_identical_to_hybrid_search_logic(
        self, ratings_fixture: str, catalog: list[dict[str, Any]], request: Any
    ) -> None:
        ratings: list[FakeRating] = request.getfixturevalue(ratings_fixture)
        seed_ids = [r.fragrance_id for r in ratings]

        fb = FeatureBasedService()
        expected = _hybrid_search_equivalent(ratings, catalog, seed_ids)
        actual = fb.score(ratings, catalog, seed_ids)

        assert len(actual) == len(expected)
        for i, (a, e) in enumerate(zip(actual, expected, strict=False)):
            assert a["id"] == e["id"], f"Item {i} id mismatch: {a['id']} != {e['id']}"
            assert a["name"] == e["name"], f"Item {i} name mismatch"
            assert a["brand"] == e["brand"], f"Item {i} brand mismatch"
            assert (
                a["match_score"] == e["match_score"]
            ), f"Item {i} match_score: {a['match_score']} != {e['match_score']}"
            assert (
                a["reason"] == e["reason"]
            ), f"Item {i} reason: {a['reason']} != {e['reason']}"
            assert (
                a["top_accords"] == e["top_accords"]
            ), f"Item {i} top_accords mismatch"
            assert (
                a["top_notes"] == e["top_notes"]
            ), f"Item {i} top_notes mismatch"
            assert sorted(a.keys()) == sorted(
                e.keys()
            ), f"Item {i} keys differ"

    # -- Rating fixtures --

    @pytest.fixture
    def single_rating(self) -> list[FakeRating]:
        return [FakeRating(fragrance_id="f001", rating=8.0)]

    @pytest.fixture
    def two_ratings(self) -> list[FakeRating]:
        return [
            FakeRating(fragrance_id="f001", rating=8.0),
            FakeRating(fragrance_id="f004", rating=6.0),
        ]

    @pytest.fixture
    def three_ratings(self) -> list[FakeRating]:
        return [
            FakeRating(fragrance_id="f001", rating=9.0),
            FakeRating(fragrance_id="f002", rating=7.0),
            FakeRating(fragrance_id="f004", rating=5.0),
        ]

    @pytest.fixture
    def rating_with_notes_and_accords(self) -> list[FakeRating]:
        return [
            FakeRating(
                fragrance_id="f003",
                rating=8.0,
                top_notes=["oakmoss", "patchouli"],
                accords=["woody", "earthy"],
            ),
        ]


# ---------------------------------------------------------------------------
# CP3 — PopularityService identity proof
# ---------------------------------------------------------------------------


class TestPopularityEquivalence:
    """Proves PopularityService.get_top() == hybrid_search popularity fallback."""

    @staticmethod
    def _hybrid_popularity_fallback(
        catalog: list[dict[str, Any]], count: int = 12
    ) -> list[dict[str, Any]]:
        """Reference: exact copy of hybrid_search.py lines 363-377."""
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

    def test_empty_catalog(self) -> None:
        assert PopularityService.get_top([], 12) == []

    def test_default_count(self, catalog: list[dict[str, Any]]) -> None:
        result = PopularityService.get_top(catalog)
        assert len(result) == 6  # only 6 items in catalog
        assert all(r["match_score"] == 50.0 for r in result)

    def test_custom_count(self, catalog: list[dict[str, Any]]) -> None:
        result = PopularityService.get_top(catalog, count=3)
        assert len(result) == 3

    def test_ordering_by_rating_count(self, catalog: list[dict[str, Any]]) -> None:
        result = PopularityService.get_top(catalog)
        counts = next(zip(
            *[(r["id"], next(
                c["rating_count"]
                for c in catalog
                if c["id"] == r["id"]
            )) for r in result]
        ))
        # Verify rating_count is descending
        ids_with_counts = [
            (catalog[next(i for i, c in enumerate(catalog) if c["id"] == r["id"])]["rating_count"], r["id"])
            for r in result
        ]
        for i in range(len(ids_with_counts) - 1):
            assert (
                ids_with_counts[i][0] >= ids_with_counts[i + 1][0]
            ), f"Order wrong at {i}: {ids_with_counts}"

    def test_identical_to_hybrid_search(
        self, catalog: list[dict[str, Any]]
    ) -> None:
        expected = self._hybrid_popularity_fallback(catalog)
        actual = PopularityService.get_top(catalog)
        assert actual == expected

    def test_identical_with_count_param(
        self, catalog: list[dict[str, Any]]
    ) -> None:
        expected = self._hybrid_popularity_fallback(catalog, count=3)
        actual = PopularityService.get_top(catalog, count=3)
        assert actual == expected

    def test_all_fields_match(self, catalog: list[dict[str, Any]]) -> None:
        result = PopularityService.get_top(catalog)
        for r in result:
            assert set(r.keys()) == {
                "id", "name", "brand", "match_score",
                "reason", "top_accords", "top_notes",
            }, f"Field mismatch in {r['id']}: {set(r.keys())}"
