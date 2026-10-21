"""Database resilience tests.

A free-tier deployment must survive a database that is unreachable, suspended
or still waking up: the catalog and the recommender are file-backed and do
not need it, so the API must keep serving.
"""

from sqlalchemy import create_engine

from app import database


def _broken_engine():
    """An engine whose database file can never be created."""
    return create_engine("sqlite:////proc/definitely-not-a-directory/scentrix.db")


def test_init_db_reports_failure_instead_of_raising(monkeypatch):
    monkeypatch.setattr(database, "engine", _broken_engine())
    assert database.init_db() is False


def test_ensure_schema_reports_failure_instead_of_raising(monkeypatch):
    monkeypatch.setattr(database, "engine", _broken_engine())
    monkeypatch.setattr(database, "_schema_ready", False)
    monkeypatch.setattr(database, "_schema_retry_after", 0.0)
    assert database.ensure_schema() is False


def test_catalog_still_serves_when_the_database_is_down(monkeypatch, client):
    monkeypatch.setattr(database, "engine", _broken_engine())
    monkeypatch.setattr(database, "_schema_ready", False)
    monkeypatch.setattr(database, "_schema_retry_after", 0.0)

    resp = client.get("/fragrances/catalog?limit=2")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 4559


def test_recommendations_still_serve_when_the_database_is_down(monkeypatch, client):
    monkeypatch.setattr(database, "engine", _broken_engine())
    monkeypatch.setattr(database, "_schema_ready", False)
    monkeypatch.setattr(database, "_schema_retry_after", 0.0)

    catalog = client.get("/fragrances/catalog?limit=1").json()["data"]["items"]
    resp = client.post(
        "/recommendations/guest",
        json={"ratings": [{"fragrance_id": catalog[0]["id"], "rating": 9}], "quiz_submitted": True},
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) > 0


def test_health_reports_the_actual_database_driver(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["database"] == "sqlite"
    assert "database_ready" in data
