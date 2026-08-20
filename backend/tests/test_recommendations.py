"""Guest recommendation endpoint tests (3-state warmth routing)."""

from app.services.catalog import get_catalog


def test_guest_empty_ratings_state_zero(client):
    resp = client.post(
        "/recommendations/guest",
        json={"ratings": [], "quiz_submitted": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == 0
    assert body["state_label"] == "anonymous"
    assert body["source"] == "popularity"
    assert body["data"]


def test_guest_three_ratings_state_warm(client):
    catalog = get_catalog()
    ratings = [
        {"fragrance_id": str(catalog[i]["id"]), "rating": float(6 + i)}
        for i in range(3)
    ]
    resp = client.post(
        "/recommendations/guest",
        json={"ratings": ratings, "quiz_submitted": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == 2
    assert body["state_label"] == "warm"
    assert body["source"] == "feature_based"
    assert body["data"]