"""Catalog service + route tests."""

from app.routers.catalog import _filter_rows, _primary_families
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


def test_primary_families_compound_labels():
    assert _primary_families("Amber-Oriental") == ["amber", "oriental"]
    assert _primary_families("White-Floral") == ["floral"]
    assert _primary_families("Marine-Aquatic") == ["aquatic"]
    assert _primary_families("Earthy-Mossy") == ["earthy"]
    assert _primary_families("warm spicy") == ["spicy"]
    assert _primary_families("fresh spicy") == ["spicy"]
    assert _primary_families("soft spicy") == ["spicy"]
    assert _primary_families("rose") == ["floral"]
    assert _primary_families("oud") == ["woody"]
    assert _primary_families("vanilla") == ["gourmand"]
    assert _primary_families("coconut") == ["fruity"]
    assert _primary_families("lavender") == ["aromatic"]
    assert _primary_families("aldehydic") == ["powdery"]
    assert _primary_families("tobacco") == ["smoky"]
    assert _primary_families("musk") == ["musky"]
    assert _primary_families("mineral") == ["aquatic"]
    assert _primary_families("balsamic") == ["oriental"]
    assert _primary_families("cinnamon") == ["spicy"]
    assert _primary_families("") == []
    assert _primary_families("Fruity") == ["fruity"]


def test_family_filter_matches_primary_accord_only():
    catalog = get_catalog()
    woody = _filter_rows(catalog, q=None, brand=None, family="woody", accord=None)
    assert len(woody) == 548
    for row, _ in woody:
        accords = row.get("accords") or []
        assert accords, "every woody hit must have accords"
        assert "woody" in _primary_families(accords[0])

    assert not any(
        "tutti-twilly" in (row.get("name") or "").lower() for row, _ in woody
    )


def test_family_amber_and_oriental_both_nonzero():
    catalog = get_catalog()
    amber = _filter_rows(catalog, q=None, brand=None, family="amber", accord=None)
    oriental = _filter_rows(catalog, q=None, brand=None, family="oriental", accord=None)
    assert len(amber) == 239
    assert len(oriental) == 240
    assert amber and oriental  # Amber-Oriental counts toward both


def test_accord_filter_keeps_loose_any_accord_behavior():
    catalog = get_catalog()
    woody_acc = _filter_rows(catalog, q=None, brand=None, family=None, accord="woody")
    woody_fam = _filter_rows(catalog, q=None, brand=None, family="woody", accord=None)
    assert len(woody_acc) > len(woody_fam)
    for row, _ in woody_acc:
        assert any("woody" in a.lower() for a in (row.get("accords") or []))