import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import verify_password
from app.models.models import User

pytestmark = pytest.mark.asyncio


async def test_register_user(client: AsyncClient, db_session: AsyncSession):
    response = await client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "username": "testuser",
            "opt_in_training": True,
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data

    # Verify in DB — User model uses email_hash for GDPR privacy, not plain email
    import hashlib

    email_hash = hashlib.sha256("test@example.com".lower().strip().encode()).hexdigest()
    result = await db_session.execute(select(User).where(User.email_hash == email_hash))
    user = result.scalar_one()
    assert user is not None
    assert verify_password("SecurePassword123!", user.hashed_password)


async def test_register_duplicate_user(client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePassword123!",
        "username": "dupuser",
        "opt_in_training": True,
    }
    # First registration
    response1 = await client.post("/auth/register", json=payload)
    assert response1.status_code == 201

    # Second registration should fail
    response2 = await client.post("/auth/register", json=payload)
    assert response2.status_code == 409
    assert response2.json()["message"] == "Email already registered"


async def test_login_success(client: AsyncClient):
    payload = {
        "email": "login@example.com",
        "password": "SecurePassword123!",
        "username": "loginuser",
        "opt_in_training": True,
    }
    await client.post("/auth/register", json=payload)

    response = await client.post(
        "/auth/login", json={"email": "login@example.com", "password": "SecurePassword123!"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "access_token" in data


async def test_login_invalid_password(client: AsyncClient):
    payload = {
        "email": "invalid@example.com",
        "password": "SecurePassword123!",
        "username": "invuser",
        "opt_in_training": True,
    }
    await client.post("/auth/register", json=payload)

    response = await client.post(
        "/auth/login", json={"email": "invalid@example.com", "password": "WrongPassword!"}
    )
    assert response.status_code == 401


async def test_get_current_user(client: AsyncClient):
    payload = {
        "email": "me@example.com",
        "password": "SecurePassword123!",
        "username": "meuser",
    }
    register_response = await client.post("/auth/register", json=payload)
    token = register_response.json()["data"]["access_token"]

    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "me@example.com"
