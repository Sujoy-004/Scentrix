"""Catalog service + route tests."""

from app.services.catalog import _normalize_id, get_catalog


def test_get_catalog_returns_4559_hydrated_items():
    catalog = get_catalog()
    assert len(catalog) == 4559
    for item in catalog[:10]:
        assert isinstance(item["_notes_set"], set) and item["_notes_set"]
        assert isinstance(item["_accords_set"], set)
        assert isinstance(item["rating_count"], int)
        assert isinstance(item["rating_value"], float)


def test_normalize_id_canonicalizes():
    assert _normalize_id("frag_chanel_no-5_1921") == "frag_chanel_no-5_1921"
    assert _normalize_id("chanel_no-5_1921") == "frag_chanel_no-5_1921"
    assert _normalize_id("") == ""
    assert _normalize_id(None) is None


def test_catalog_route_list_and_detail(client):
    listing = client.get("/fragrances/catalog", params={"limit": 5})
    assert listing.status_code == 200
    data = listing.json()["data"]
    assert data["total"] == 4559
    assert data["limit"] == 5
    assert len(data["items"]) == 5
    for item in data["items"]:
        assert item["id"]
        assert item["name"]

    fid = data["items"][0]["id"]
    detail = client.get(f"/fragrances/{fid}")
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == fid