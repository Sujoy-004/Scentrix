from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_login(client: AsyncClient) -> tuple[dict[str, str], int]:
    email = f"user_{uuid4().hex[:8]}@example.com"
    password = "SecurePass123!"

    register = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "opt_in_training": True,
        },
    )
    assert register.status_code == 201

    login = await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    return headers, int(me.json()["data"]["id"])


async def test_excised_endpoints_return_404(client: AsyncClient):
    headers, _ = await _register_and_login(client)

    # 1. recommend/text is gone
    text_resp = await client.post(
        "/fragrances/recommend/text",
        headers=headers,
        json={"query": "fresh woodsy", "limit": 5},
    )
    assert text_resp.status_code == 404

    # 2. recommend/profile is gone
    profile_resp = await client.post(
        "/fragrances/recommend/profile",
        headers=headers,
        params={"limit": 5},
    )
    assert profile_resp.status_code == 404

    # 3. recommend/job_id is gone
    poll_resp = await client.get(
        "/fragrances/recommend/some-job-id",
        headers=headers,
    )
    assert poll_resp.status_code == 404

    # 4. recommend/metrics/weekly is gone
    metrics_resp = await client.get(
        "/fragrances/recommend/metrics/weekly",
        headers=headers,
    )
    assert metrics_resp.status_code == 404


async def test_recommendation_interaction_ingest_requires_auth(client: AsyncClient):
    response = await client.post(
        "/fragrances/recommend/interactions",
        json={
            "events": [
                {
                    "fragrance_id": "frag_001",
                    "interaction_type": "impression",
                    "match_score": 44.0,
                    "confidence_tier": "medium",
                }
            ]
        },
    )
    assert response.status_code == 401


async def test_recommendation_interactions_still_ingests(client: AsyncClient):
    headers, _ = await _register_and_login(client)

    ingest = await client.post(
        "/fragrances/recommend/interactions",
        headers=headers,
        json={
            "events": [
                {
                    "fragrance_id": "frag_001",
                    "interaction_type": "impression",
                    "match_score": 22.5,
                    "confidence_tier": "low",
                    "availability": "N/A",
                    "context": {"availability_known": False},
                },
                {
                    "fragrance_id": "frag_002",
                    "interaction_type": "impression",
                    "match_score": 81.0,
                    "confidence_tier": "high",
                    "availability": "in-stock",
                    "context": {"availability_known": True},
                },
            ]
        },
    )
    assert ingest.status_code == 202
    assert ingest.json()["data"]["accepted"] == 2
