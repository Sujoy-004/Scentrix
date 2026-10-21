"""Catalog query cache tests.

The catalog is 4,559 rows and every request used to re-filter and re-sort all
of them. On a free-tier instance with a fraction of a vCPU that scan is the
largest single cost in the API, so the result is memoised.
"""

from app.routers.catalog import _apply_sort, _filter_rows, _query_catalog
from app.services.catalog import get_catalog, get_catalog_version


def _uncached(q, brand, family, accord, sort):
    """The original, un-cached implementation - the reference behaviour."""
    rows = get_catalog()
    matched = _filter_rows(rows, q=q, brand=brand, family=family, accord=accord)
    if q:
        if sort and sort != "match":
            _apply_sort(matched, sort)
        else:
            _apply_sort(matched, "match")
    else:
        _apply_sort(matched, sort or "popular")
    return matched


def test_cached_result_matches_the_uncached_implementation():
    for q, brand, family, accord, sort in [
        (None, None, None, None, None),
        (None, None, "floral", None, None),
        (None, None, "woody", None, "name"),
        ("oud", None, None, None, None),
        ("oud", None, None, None, "rating"),
        (None, "Chanel", None, None, None),
        (None, None, None, "amber", None),
    ]:
        cached = list(
            _query_catalog(q, brand, family, accord, sort, get_catalog_version())
        )
        expected = _uncached(q, brand, family, accord, sort)
        assert cached == expected, f"cache disagrees for {(q, brand, family, accord, sort)}"


def test_repeated_queries_are_served_from_the_cache():
    version = get_catalog_version()
    _query_catalog.cache_clear()
    _query_catalog(None, None, "floral", None, None, version)
    before = _query_catalog.cache_info()
    _query_catalog(None, None, "floral", None, None, version)
    after = _query_catalog.cache_info()
    assert after.hits == before.hits + 1


def test_a_catalog_reload_invalidates_the_cache():
    _query_catalog.cache_clear()
    version = get_catalog_version()
    _query_catalog(None, None, "citrus", None, None, version)
    hits_before = _query_catalog.cache_info().hits

    # A reload bumps the version, so the next call is a miss, not a stale hit.
    _query_catalog(None, None, "citrus", None, None, version + 1)
    assert _query_catalog.cache_info().hits == hits_before


def test_the_api_still_returns_the_full_catalog(client):
    resp = client.get("/fragrances/catalog?limit=5")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 4559
    assert len(data["items"]) == 5


def test_family_filter_still_works_through_the_api(client):
    resp = client.get("/fragrances/catalog?family=floral&limit=200")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] > 0
    assert len(data["items"]) <= 200
    for item in data["items"]:
        assert item["accords"], "a floral item should carry accords"
