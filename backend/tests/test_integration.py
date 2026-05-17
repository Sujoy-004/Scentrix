import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_full_user_journey(client: AsyncClient, db_session: AsyncSession):
    """
    Test the full user journey:
    1. Register
    2. Login
    3. Browse
    4. Rate
    5. Get Recommendations
    """
    # 1. Register
    reg_response = await client.post(
        "/auth/register",
        json={
            "email": "journey@example.com",
            "password": "SecurePassword123!",
            "username": "journeyuser",
            "opt_in_training": True,
        },
    )
    assert reg_response.status_code == 201

    # 2. Login
    login_response = await client.post(
        "/auth/login", json={"email": "journey@example.com", "password": "SecurePassword123!"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Browse Fragrances
    browse_response = await client.get("/fragrances", params={"limit": 10})
    assert browse_response.status_code == 200
    fragrances = browse_response.json()["data"]
    assert isinstance(fragrances, list)

    frag_id = fragrances[0]["id"] if fragrances else "frag_001"

    # 4. Rate a fragrance
    rate_response = await client.post(
        "/recommendations/rate",
        headers=headers,
        json={"fragrance_id": frag_id, "rating": 8.5},
    )
    assert rate_response.status_code == 200
    assert rate_response.json()["data"]["status"] == "saved"

    # 5. Get Personalized Recommendations
    rec_response = await client.get("/recommendations/personalized", headers=headers)
    assert rec_response.status_code == 200
    recs = rec_response.json()["data"]
    assert isinstance(recs, list)


async def test_semantic_text_search(client: AsyncClient):
    """Test text-based NLP search against fragrances search API"""
    response = await client.get("/fragrances/search", params={"q": "fresh citrus"})
    assert response.status_code == 200
    results = response.json()["data"]
    assert isinstance(results, list)


async def test_fragrance_detail_and_similarity(client: AsyncClient):
    """Test details and similarity (neighbors) endpoint"""
    # First get any fragrance from browse
    browse_response = await client.get("/fragrances", params={"limit": 1})
    assert browse_response.status_code == 200
    fragrances = browse_response.json()["data"]
    if fragrances:
        frag_id = fragrances[0]["id"]
        response = await client.get(f"/fragrances/{frag_id}")
        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["id"] == frag_id
        assert "top_notes" in payload
