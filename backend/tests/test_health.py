import pytest
from app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "running"


def test_version():
    """Test version endpoint."""
    response = client.get("/version")
    assert response.status_code == 200
    assert "version" in response.json()
