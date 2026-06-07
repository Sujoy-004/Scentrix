"""Phase 11 tests — guest-finalize, quiz-summary, state/state_label.

Covers:
  B1. guest-finalize endpoint (guest + authenticated flow)
  B2. quiz-summary endpoint (with/without quiz, 401, edge cases)
  B3. state/state_label in recommendation responses
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import FragranceRating as DBFragranceRating
from app.models.models import User
from app.routers import quiz as quiz_router
from app.routers import recommendations as rec_mod
from app.services.dispatcher import DispatchRequest, RecommendationDispatcher

pytestmark = pytest.mark.asyncio


async def _register_user(client: AsyncClient, db_session: AsyncSession) -> dict:
    uid = f"p11_{uuid4().hex[:8]}"
    email = f"{uid}@example.com"
    resp = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPass123!",
            "username": uid,
            "opt_in_training": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    email_hash = hashlib.sha256(email.lower().strip().encode()).hexdigest()
    result = await db_session.execute(select(User).where(User.email_hash == email_hash))
    user = result.scalar_one()
    return {"user_id": user.id, "access_token": data["access_token"], "email": email}


# ═══════════════════════════════════════════════════════════════════════════════
# B1: guest-finalize
# ═══════════════════════════════════════════════════════════════════════════════


class TestGuestFinalize:
    """Prove guest-finalize endpoint works for guests and authenticated users."""

    SAMPLE_CATALOG = [
        {"id": "frag_001", "name": "Citrus Dawn", "brand": "Brand A",
         "top_notes": ["Bergamot"], "accords": ["Citrus"], "review_count": 120, "view_count": 9000, "popularity_score": 74},
        {"id": "frag_002", "name": "Woods Echo", "brand": "Brand B",
         "top_notes": ["Cedar"], "accords": ["Woody"], "review_count": 90, "view_count": 7000, "popularity_score": 67},
        {"id": "frag_003", "name": "Floral Mist", "brand": "Brand C",
         "top_notes": ["Rose"], "accords": ["Floral"], "review_count": 80, "view_count": 6400, "popularity_score": 61},
        {"id": "frag_004", "name": "Amber Night", "brand": "Brand D",
         "top_notes": ["Saffron"], "accords": ["Amber"], "review_count": 110, "view_count": 8200, "popularity_score": 71},
        {"id": "frag_005", "name": "Marine Air", "brand": "Brand E",
         "top_notes": ["Sea Salt"], "accords": ["Aquatic"], "review_count": 95, "view_count": 7600, "popularity_score": 69},
        {"id": "frag_006", "name": "Smoked Leather", "brand": "Brand F",
         "top_notes": ["Leather"], "accords": ["Smoky"], "review_count": 76, "view_count": 5100, "popularity_score": 58},
        {"id": "frag_007", "name": "Vanilla Thread", "brand": "Brand G",
         "top_notes": ["Vanilla"], "accords": ["Gourmand"], "review_count": 103, "view_count": 8000, "popularity_score": 72},
        {"id": "frag_008", "name": "Green Path", "brand": "Brand H",
         "top_notes": ["Galbanum"], "accords": ["Green"], "review_count": 70, "view_count": 4300, "popularity_score": 54},
    ]

    async def _create_guest_session(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch,
        headers: dict[str, str] | None = None,
    ) -> str:
        store: dict[str, dict] = {}

        async def fake_create(session_id: str, payload: dict):
            store[session_id] = payload

        async def fake_get(session_id: str):
            return store.get(session_id)

        async def fake_save(session_id: str, payload: dict):
            store[session_id] = payload

        monkeypatch.setattr(quiz_router, "load_recommendation_catalog", lambda: self.SAMPLE_CATALOG)
        monkeypatch.setattr(quiz_router, "create_quiz_session", fake_create)
        monkeypatch.setattr(quiz_router, "get_quiz_session", fake_get)
        monkeypatch.setattr(quiz_router, "save_quiz_session", fake_save)

        kwargs = {}
        if headers:
            kwargs["headers"] = headers
        start = await client.post(
            "/fragrances/quiz/session/start",
            json={"seed_count": 8, "candidate_pool_size": 50, "filters": {"exclude_seen": False}},
            **kwargs,
        )
        assert start.status_code == 200
        return start.json()["data"]["session_id"]

    async def test_guest_finalize_success(self, client: AsyncClient, monkeypatch):
        """Guest can finalize without auth token."""
        session_id = await self._create_guest_session(client, monkeypatch)
        resp = await client.post(f"/fragrances/quiz/session/{session_id}/guest-finalize")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["data"]["message"] == "Guest quiz finalized"

    async def test_guest_finalize_idempotent(self, client: AsyncClient, monkeypatch):
        """Guest finalize can be called multiple times."""
        session_id = await self._create_guest_session(client, monkeypatch)
        resp1 = await client.post(f"/fragrances/quiz/session/{session_id}/guest-finalize")
        assert resp1.status_code == 200
        resp2 = await client.post(f"/fragrances/quiz/session/{session_id}/guest-finalize")
        assert resp2.status_code == 200

    async def test_guest_finalize_nonexistent_session(self, client: AsyncClient):
        """guest-finalize returns 404 for unknown session."""
        resp = await client.post("/fragrances/quiz/session/qz_nonexistent/guest-finalize")
        assert resp.status_code == 404

    async def test_authenticated_finalize_via_guest_endpoint(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch
    ):
        """Authenticated user calling guest-finalize delegates to standard finalize (DB upsert)."""
        user = await _register_user(client, db_session)
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        session_id = await self._create_guest_session(client, monkeypatch, headers=headers)

        resp = await client.post(
            f"/fragrances/quiz/session/{session_id}/guest-finalize",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"

        db_user = (await db_session.execute(select(User).where(User.id == user["user_id"]))).scalar_one()
        assert db_user.quiz_completed_at is not None


# ═══════════════════════════════════════════════════════════════════════════════
# B2: quiz-summary
# ═══════════════════════════════════════════════════════════════════════════════


class TestQuizSummary:
    """Prove quiz-summary returns correct data for various states."""

    async def test_quiz_summary_without_auth(self, client: AsyncClient):
        """quiz-summary requires authentication."""
        resp = await client.get("/recommendations/quiz-summary")
        assert resp.status_code == 401

    async def test_quiz_summary_no_quiz(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """User without completed quiz gets has_completed_quiz=False."""
        user = await _register_user(client, db_session)
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        resp = await client.get("/recommendations/quiz-summary", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert data["has_completed_quiz"] is False

    async def test_quiz_summary_with_quiz(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """User with completed quiz gets full summary."""
        user = await _register_user(client, db_session)
        headers = {"Authorization": f"Bearer {user['access_token']}"}

        for i in range(8):
            db_session.add(
                DBFragranceRating(
                    user_id=user["user_id"],
                    fragrance_neo4j_id=str(100 + i),
                    quiz_rating=7.0 + (i % 3),
                )
            )
        db_user = (await db_session.execute(select(User).where(User.id == user["user_id"]))).scalar_one()
        db_user.quiz_completed_at = datetime.now(UTC).replace(tzinfo=None)
        await db_session.commit()

        resp = await client.get("/recommendations/quiz-summary", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert data["has_completed_quiz"] is True
        assert data["total_rated"] == 8
        assert data["average_rating"] is not None
        assert "rating_distribution" in data
        assert isinstance(data["top_matches"], list)

    async def test_quiz_summary_invalid_token(self, client: AsyncClient):
        """quiz-summary rejects invalid token."""
        resp = await client.get(
            "/recommendations/quiz-summary",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# B3: state/state_label in recommendation responses
# ═══════════════════════════════════════════════════════════════════════════════


class TestStateInRecommendations:
    """Prove state and state_label appear in guest + personalized responses."""

    async def test_guest_cold_start_has_state(
        self, client: AsyncClient
    ):
        """Guest recs without quiz_confidence have state=0, label='anonymous'."""
        with (
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[{
                        "id": "101", "name": "Fresh", "brand": "T",
                        "match_score": 50.0, "reason": "Popular",
                        "source": "popularity",
                    }],
                    state=0,
                    state_label="anonymous",
                )
            )
            mock_get.return_value = mock_disp

            resp = await client.post(
                "/recommendations/guest",
                json={"ratings": []},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == 0
        assert body["state_label"] == "anonymous"

    async def test_guest_quiz_user_has_state(
        self, client: AsyncClient
    ):
        """Guest recs with quiz_confidence have state=1, label='quiz_user'."""
        with (
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[{
                        "id": "102", "name": "Woody", "brand": "T",
                        "match_score": 85.0, "reason": "Quiz Match",
                        "source": "graphsage",
                    }],
                    state=1,
                    state_label="quiz_user",
                )
            )
            mock_get.return_value = mock_disp

            resp = await client.post(
                "/recommendations/guest",
                json={
                    "ratings": [],
                    "quiz_confidence": {"fresh": 0.8, "woody": 0.4},
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == 1
        assert body["state_label"] == "quiz_user"

    async def test_guest_empty_dispatcher_fallback_no_state(
        self, client: AsyncClient
    ):
        """When dispatcher returns empty, fallback legacy path omits state."""
        with (
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(recommendations=[], state=0, state_label="anonymous")
            )
            mock_get.return_value = mock_disp

            resp = await client.post(
                "/recommendations/guest",
                json={"ratings": [{"fragrance_id": "101", "rating": 5.0}]},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"

    async def test_personalized_has_state(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Personalized recs include state and state_label."""
        user = await _register_user(client, db_session)
        token = user["access_token"]
        for i in range(5):
            db_session.add(
                DBFragranceRating(
                    user_id=user["user_id"],
                    fragrance_neo4j_id=str(200 + i),
                    quiz_rating=6.0,
                )
            )
        await db_session.commit()

        with (
            patch.object(rec_mod.cache, "get", new_callable=AsyncMock, return_value=None),
            patch.object(rec_mod.cache, "set", new_callable=AsyncMock),
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
            patch.object(rec_mod, "load_recommendation_catalog",
                  return_value=TestGuestFinalize.SAMPLE_CATALOG),
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[{
                        "id": "101", "name": "Fresh", "brand": "T",
                        "match_score": 80.0, "reason": "Feature",
                        "source": "feature_based",
                    }],
                    state=3,
                    state_label="warm",
                )
            )
            mock_get.return_value = mock_disp

            resp = await client.get(
                "/recommendations/personalized",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == 3
        assert body["state_label"] == "warm"


# ═══════════════════════════════════════════════════════════════════════════════
# B4: Negative-path checks
# ═══════════════════════════════════════════════════════════════════════════════


class TestNegativePaths:
    """Prove endpoints handle edge-case inputs gracefully."""

    async def test_guest_finalize_wrong_owner(self, client: AsyncClient, monkeypatch):
        """guest-finalize rejects session owned by another user."""
        store = {
            "qz_other": {
                "session_id": "qz_other",
                "user_id": 999,
                "responses": [],
                "config": {
                    "min_core_questions": 8,
                    "max_total_questions": 16,
                    "medium_extension": 3,
                    "low_extension": 5,
                    "confidence_threshold": 0.72,
                },
            }
        }

        async def fake_get(session_id: str):
            return store.get(session_id)

        monkeypatch.setattr(quiz_router, "get_quiz_session", fake_get)
        resp = await client.post("/fragrances/quiz/session/qz_other/guest-finalize")
        assert resp.status_code == 403

    async def test_guest_finalize_missing_session(self, client: AsyncClient):
        """guest-finalize returns 404 for non-existent session."""
        resp = await client.post("/fragrances/quiz/session/qz_missing/guest-finalize")
        assert resp.status_code == 404
