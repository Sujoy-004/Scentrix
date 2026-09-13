"""Health endpoint tests — the public health check powering demo/ops uptime."""


def test_health_returns_success_and_ready_state(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["status"] == "ok"
    assert body["data"]["database"] == "sqlite"
    assert body["data"]["gs_embeddings"]["initialized"] is True


def test_health_is_unauthenticated(client):
    """/health must never require credentials (anonymous demo contract)."""
    resp = client.get("/health", headers={"Authorization": ""})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"