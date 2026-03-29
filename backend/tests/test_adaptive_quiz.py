from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

import app.routers.quiz as quiz_router


pytestmark = pytest.mark.asyncio


def _sample_catalog() -> list[dict]:
    return [
        {
            "id": "frag_001",
            "name": "Citrus Dawn",
            "brand": "Brand A",
            "top_notes": ["Bergamot", "Lemon"],
            "accords": ["Citrus", "Fresh"],
            "review_count": 120,
            "view_count": 9000,
            "popularity_score": 74,
        },
        {
            "id": "frag_002",
            "name": "Woods Echo",
            "brand": "Brand B",
            "top_notes": ["Cedar", "Pepper"],
            "accords": ["Woody", "Spicy"],
            "review_count": 90,
            "view_count": 7000,
            "popularity_score": 67,
        },
        {
            "id": "frag_003",
            "name": "Floral Mist",
            "brand": "Brand C",
            "top_notes": ["Rose", "Violet"],
            "accords": ["Floral", "Powdery"],
            "review_count": 80,
            "view_count": 6400,
            "popularity_score": 61,
        },
        {
            "id": "frag_004",
            "name": "Amber Night",
            "brand": "Brand D",
            "top_notes": ["Saffron", "Cardamom"],
            "accords": ["Amber", "Warm"],
            "review_count": 110,
            "view_count": 8200,
            "popularity_score": 71,
        },
        {
            "id": "frag_005",
            "name": "Marine Air",
            "brand": "Brand E",
            "top_notes": ["Sea Salt", "Grapefruit"],
            "accords": ["Aquatic", "Fresh"],
            "review_count": 95,
            "view_count": 7600,
            "popularity_score": 69,
        },
        {
            "id": "frag_006",
            "name": "Smoked Leather",
            "brand": "Brand F",
            "top_notes": ["Leather", "Incense"],
            "accords": ["Smoky", "Leather"],
            "review_count": 76,
            "view_count": 5100,
            "popularity_score": 58,
        },
        {
            "id": "frag_007",
            "name": "Vanilla Thread",
            "brand": "Brand G",
            "top_notes": ["Vanilla", "Tonka"],
            "accords": ["Gourmand", "Sweet"],
            "review_count": 103,
            "view_count": 8000,
            "popularity_score": 72,
        },
        {
            "id": "frag_008",
            "name": "Green Path",
            "brand": "Brand H",
            "top_notes": ["Galbanum", "Mint"],
            "accords": ["Green", "Aromatic"],
            "review_count": 70,
            "view_count": 4300,
            "popularity_score": 54,
        },
        {
            "id": "frag_009",
            "name": "Iris Silk",
            "brand": "Brand I",
            "top_notes": ["Iris", "Aldehydes"],
            "accords": ["Powdery", "Floral"],
            "review_count": 65,
            "view_count": 4100,
            "popularity_score": 49,
        },
        {
            "id": "frag_010",
            "name": "Spice Root",
            "brand": "Brand J",
            "top_notes": ["Nutmeg", "Clove"],
            "accords": ["Spicy", "Woody"],
            "review_count": 88,
            "view_count": 6200,
            "popularity_score": 63,
        },
    ]


async def _register_and_login(client: AsyncClient) -> tuple[dict[str, str], int]:
    email = f"adaptive_{uuid4().hex[:8]}@example.com"
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


async def test_quiz_start_requires_auth(client: AsyncClient):
    response = await client.post("/fragrances/quiz/session/start", json={})
    assert response.status_code == 401


async def test_quiz_start_submit_and_evaluate_flow(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    headers, user_id = await _register_and_login(client)

    store: dict[str, dict] = {}

    async def fake_create_quiz_session(*, session_id: str, payload: dict):
        store[session_id] = payload

    async def fake_get_quiz_session(session_id: str):
        return store.get(session_id)

    async def fake_save_quiz_session(*, session_id: str, payload: dict):
        store[session_id] = payload

    monkeypatch.setattr(quiz_router, "load_recommendation_catalog", lambda: _sample_catalog())
    monkeypatch.setattr(quiz_router, "create_quiz_session", fake_create_quiz_session)
    monkeypatch.setattr(quiz_router, "get_quiz_session", fake_get_quiz_session)
    monkeypatch.setattr(quiz_router, "save_quiz_session", fake_save_quiz_session)

    start = await client.post(
        "/fragrances/quiz/session/start",
        json={"seed_count": 8, "candidate_pool_size": 50, "filters": {"exclude_seen": True}},
        headers=headers,
    )
    assert start.status_code == 200
    payload = start.json()
    session_id = payload["session_id"]
    assert len(payload["seed_questions"]) == 8

    first_question_id = payload["seed_questions"][0]["fragrance_id"]
    submit = await client.post(
        f"/fragrances/quiz/session/{session_id}/responses",
        json={"fragrance_id": first_question_id, "rating_1_to_10": 7.8, "source": "quiz_core"},
        headers=headers,
    )
    assert submit.status_code == 200
    submit_payload = submit.json()
    assert submit_payload["accepted"] is True
    assert submit_payload["normalized_rating_0_to_5"] == 3.9
    assert submit_payload["answers_count"] == 1

    evaluate = await client.post(
        f"/fragrances/quiz/session/{session_id}/evaluate",
        json={"force": False},
        headers=headers,
    )
    assert evaluate.status_code == 200
    evaluate_payload = evaluate.json()
    assert evaluate_payload["total_answered"] == 1
    assert evaluate_payload["stop_reason"] == "core_incomplete"

    # Ensure session ownership is what we expect in backing store
    assert int(store[session_id]["user_id"]) == user_id


async def test_quiz_session_ownership_enforced(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    owner_headers, owner_id = await _register_and_login(client)
    other_headers, _ = await _register_and_login(client)

    fake_session = {
        "session_id": "qz_owner",
        "user_id": owner_id,
        "config": {
            "min_core_questions": 8,
            "max_total_questions": 16,
            "medium_extension": 3,
            "low_extension": 5,
            "confidence_threshold": 0.72,
        },
        "responses": [],
        "served_ids": ["frag_001"],
        "low_gain_streak": 0,
    }

    async def fake_get_quiz_session(_: str):
        return fake_session

    monkeypatch.setattr(quiz_router, "get_quiz_session", fake_get_quiz_session)

    forbidden = await client.post(
        "/fragrances/quiz/session/qz_owner/responses",
        json={"fragrance_id": "frag_001", "rating_1_to_10": 8.2, "source": "quiz_core"},
        headers=other_headers,
    )
    assert forbidden.status_code == 403

    allowed = await client.post(
        "/fragrances/quiz/session/qz_owner/responses",
        json={"fragrance_id": "frag_001", "rating_1_to_10": 8.2, "source": "quiz_core"},
        headers=owner_headers,
    )
    # save_quiz_session is not patched here, so this call can fail on store unavailability.
    # Ownership check happens before store I/O, so 403 must not occur.
    assert allowed.status_code != 403


async def test_quiz_next_questions_excludes_served_and_answered(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    headers, user_id = await _register_and_login(client)

    store = {
        "qz_next": {
            "session_id": "qz_next",
            "user_id": user_id,
            "responses": [
                {"fragrance_id": "frag_001", "rating_0_to_5": 4.0},
                {"fragrance_id": "frag_002", "rating_0_to_5": 3.5},
            ],
            "served_ids": ["frag_001", "frag_002", "frag_003"],
            "config": {
                "min_core_questions": 8,
                "max_total_questions": 16,
                "medium_extension": 3,
                "low_extension": 5,
                "confidence_threshold": 0.72,
            },
        }
    }

    async def fake_get_quiz_session(session_id: str):
        return store.get(session_id)

    async def fake_save_quiz_session(*, session_id: str, payload: dict):
        store[session_id] = payload

    monkeypatch.setattr(quiz_router, "load_recommendation_catalog", lambda: _sample_catalog())
    monkeypatch.setattr(quiz_router, "get_quiz_session", fake_get_quiz_session)
    monkeypatch.setattr(quiz_router, "save_quiz_session", fake_save_quiz_session)

    response = await client.get(
        "/fragrances/quiz/session/qz_next/next-questions",
        params={"count": 3},
        headers=headers,
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["count"] <= 3

    returned_ids = {item["fragrance_id"] for item in payload["questions"]}
    assert "frag_001" not in returned_ids
    assert "frag_002" not in returned_ids
    assert "frag_003" not in returned_ids

    served_after = set(store["qz_next"]["served_ids"])
    assert returned_ids.issubset(served_after)
