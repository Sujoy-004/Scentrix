from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

import app.routers.fragrances as fragrances_router


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
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    return headers, int(me.json()["id"])


async def test_profile_recommend_requires_auth(client: AsyncClient):
    response = await client.post("/fragrances/recommend/profile")
    assert response.status_code == 401


async def test_text_recommend_requires_auth(client: AsyncClient):
    response = await client.post(
        "/fragrances/recommend/text",
        json={"query": "woody spicy", "limit": 5},
    )
    assert response.status_code == 401


async def test_job_poll_owner_enforced(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    owner_headers, owner_id = await _register_and_login(client)
    other_headers, _ = await _register_and_login(client)

    async def fake_get_job(_: str):
        return {
            "status": "processing",
            "user_id": owner_id,
            "message": "Still generating recommendations...",
            "results": None,
            "generated_at": None,
            "error": None,
            "celery_task_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    monkeypatch.setattr(fragrances_router, "get_job", fake_get_job)

    own_response = await client.get("/fragrances/recommend/job-owner", headers=owner_headers)
    assert own_response.status_code == 200
    assert own_response.json()["status"] in {"processing", "queued"}

    forbidden = await client.get("/fragrances/recommend/job-owner", headers=other_headers)
    assert forbidden.status_code == 403


async def test_job_poll_completed_payload_contract(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    owner_headers, owner_id = await _register_and_login(client)
    generated_at = datetime.now(timezone.utc).isoformat()

    async def fake_get_job(_: str):
        return {
            "status": "completed",
            "user_id": owner_id,
            "message": "Recommendation generation completed",
            "results": [
                {
                    "id": "frag_001",
                    "name": "Sauvage",
                    "brand": "Dior",
                    "match_score": 93.2,
                    "reason": "User taste vector similarity",
                }
            ],
            "generated_at": generated_at,
            "error": None,
            "celery_task_id": None,
            "created_at": generated_at,
        }

    monkeypatch.setattr(fragrances_router, "get_job", fake_get_job)

    response = await client.get("/fragrances/recommend/job-complete", headers=owner_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert isinstance(payload.get("fragrances"), list)
    assert payload["fragrances"]
    assert payload.get("generated_at")


async def test_job_poll_timed_out_maps_to_504(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    owner_headers, owner_id = await _register_and_login(client)
    created_at = datetime.now(timezone.utc).isoformat()

    async def fake_get_job(_: str):
        return {
            "status": "timed_out",
            "user_id": owner_id,
            "message": "Recommendation job timed out while waiting for worker completion",
            "results": None,
            "generated_at": None,
            "error": "Recommendation job timed out",
            "celery_task_id": None,
            "created_at": created_at,
        }

    monkeypatch.setattr(fragrances_router, "get_job", fake_get_job)

    response = await client.get("/fragrances/recommend/job-timeout", headers=owner_headers)
    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()


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


async def test_recommendation_interactions_feed_weekly_metrics(client: AsyncClient):
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
                {
                    "fragrance_id": "frag_002",
                    "interaction_type": "click_detail",
                    "confidence_tier": "high",
                },
                {
                    "fragrance_id": "frag_001",
                    "interaction_type": "wishlist_add",
                    "confidence_tier": "low",
                },
            ]
        },
    )
    assert ingest.status_code == 202
    assert ingest.json()["accepted"] == 4

    metrics = await client.get("/fragrances/recommend/metrics/weekly", headers=headers)
    assert metrics.status_code == 200
    payload = metrics.json()

    assert payload["impressions"] == 2
    assert payload["detail_clicks"] == 1
    assert payload["wishlist_adds"] == 1
    assert payload["click_through_rate_pct"] == 50.0
    assert payload["low_confidence_share_pct"] == 50.0
    assert payload["stock_coverage_pct"] == 50.0