"""Auth endpoint tests: register, login, me."""

from uuid import uuid4

PASSWORD = "StrongPass123"


def _unique_email():
    return f"test-{uuid4().hex[:10]}@example.com"


def test_register_creates_user_and_duplicate_conflicts(client):
    email = _unique_email()
    payload = {"email": email, "password": PASSWORD, "full_name": "Test User"}

    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201
    data = first.json()["data"]
    assert data["access_token"]
    assert data["user"]["email"] == email

    dup = client.post("/auth/register", json=payload)
    assert dup.status_code == 409


def test_login_valid_and_invalid_credentials(client):
    email = _unique_email()
    client.post("/auth/register", json={"email": email, "password": PASSWORD})

    bad = client.post("/auth/login", json={"email": email, "password": "WrongPass123"})
    assert bad.status_code == 401

    good = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert good.status_code == 200
    assert good.json()["data"]["access_token"]


def test_me_requires_token_and_returns_profile(client):
    email = _unique_email()
    token = client.post(
        "/auth/register", json={"email": email, "password": PASSWORD}
    ).json()["data"]["access_token"]

    authed = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert authed.status_code == 200
    assert authed.json()["data"]["user"]["email"] == email

    anon = client.get("/auth/me")
    assert anon.status_code == 401