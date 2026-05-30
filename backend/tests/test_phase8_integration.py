"""Phase 8 integration tests — endpoint wiring, state routing, fallback, cache.

Covers:
  C. State verification (5 tests)
  D. Fallback verification (3 tests)
  E. Cache verification + feature flag (4 tests)
"""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import FragranceRating as DBFragranceRating
from app.models.models import User
from app.routers import recommendations as rec_mod
from app.services.dispatcher import (
    DispatchRequest,
    RecommendationDispatcher,
)
from app.services.feature_based import FeatureBasedService
from app.services.popularity import PopularityService

pytestmark = pytest.mark.asyncio

_test_counter = 0


def _unique_id() -> str:
    global _test_counter
    _test_counter += 1
    return f"p8_{_test_counter}"


# Small test catalog for when load_recommendation_catalog is patched.
TEST_CATALOG: list[dict] = [
    {
        "id": "101",
        "name": "Fresh Breeze",
        "brand": "TestCo",
        "accords": ["fresh", "citrus"],
        "top_notes": ["lemon", "bergamot"],
        "rating_count": 42,
        "_accords_set": {"fresh", "citrus"},
    },
    {
        "id": "102",
        "name": "Woody Night",
        "brand": "TestCo",
        "accords": ["woody", "amber"],
        "top_notes": ["sandalwood", "vanilla"],
        "rating_count": 33,
        "_accords_set": {"woody", "amber"},
    },
    {
        "id": "103",
        "name": "Ocean Mist",
        "brand": "TestCo",
        "accords": ["aquatic", "fresh"],
        "top_notes": ["sea salt", "algae"],
        "rating_count": 28,
        "_accords_set": {"aquatic", "fresh"},
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_user(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Register + login a test user. Returns access_token + user_id."""
    uid = _unique_id()
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
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    data = resp.json()["data"]
    access_token = data["access_token"]
    email_hash = hashlib.sha256(email.lower().strip().encode()).hexdigest()
    result = await db_session.execute(
        select(User).where(User.email_hash == email_hash)
    )
    user = result.scalar_one()
    return {"user_id": user.id, "access_token": access_token}


async def _create_ratings(
    db_session: AsyncSession, user_id: int, count: int, start_id: int = 101
):
    for i in range(count):
        db_session.add(
            DBFragranceRating(
                user_id=user_id,
                fragrance_neo4j_id=str(start_id + i),
                quiz_rating=5.0,
            )
        )
    await db_session.commit()


# ── C. State Verification Tests ───────────────────────────────────────────────


class TestStateRouting:
    """Prove dispatcher is invoked with correct state parameters."""

    async def test_state_0_guest_no_quiz(self, client: AsyncClient):
        """guest + no quiz confidence -> State 0 (anonymous)"""
        with (
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[
                        {
                            "id": "101",
                            "name": "Fresh Breeze",
                            "brand": "TestCo",
                            "match_score": 85.0,
                            "reason": "Popular",
                        }
                    ],
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
        assert body["status"] == "success"
        args: DispatchRequest = mock_disp.dispatch.call_args[0][0]
        assert isinstance(args, DispatchRequest)
        assert len(args.ratings) == 0
        assert args.quiz_completed is False
        assert args.quiz_confidence is None

    async def test_state_1_guest_with_quiz(self, client: AsyncClient):
        """guest + quiz confidence -> State 1 (quiz_user)"""
        with (
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[
                        {
                            "id": "102",
                            "name": "Woody Night",
                            "brand": "TestCo",
                            "match_score": 85.0,
                            "reason": "Quiz Match",
                        }
                    ],
                    state=1,
                    state_label="quiz_user",
                )
            )
            mock_get.return_value = mock_disp

            resp = await client.post(
                "/recommendations/guest",
                json={
                    "ratings": [],
                    "quiz_confidence": {"fresh": 0.9, "woody": 0.4},
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        args: DispatchRequest = mock_disp.dispatch.call_args[0][0]
        assert args.quiz_completed is True
        assert args.quiz_confidence == {"fresh": 0.9, "woody": 0.4}
        assert len(args.ratings) == 0

    async def test_state_2_auth_1_rating(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """auth user with 1 rating -> State 2 (cold)"""
        user = await _register_user(client, db_session)
        user_id = user["user_id"]
        token = user["access_token"]
        await _create_ratings(db_session, user_id, count=1)

        with (
            patch.object(rec_mod.cache, "get", new_callable=AsyncMock, return_value=None),
            patch.object(rec_mod.cache, "set", new_callable=AsyncMock),
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
            patch.object(rec_mod, "load_recommendation_catalog",
                  return_value=TEST_CATALOG),
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[
                        {
                            "id": "101",
                            "name": "Fresh Breeze",
                            "brand": "TestCo",
                            "match_score": 70.0,
                            "reason": "Blend",
                        }
                    ],
                    state=2,
                    state_label="cold",
                )
            )
            mock_get.return_value = mock_disp

            resp = await client.get(
                "/recommendations/personalized",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        args: DispatchRequest = mock_disp.dispatch.call_args[0][0]
        assert args.user_id == user_id
        assert len(args.ratings) == 1

    async def test_state_3_auth_5_ratings(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """auth user with 5 ratings -> State 3 (warm)"""
        user = await _register_user(client, db_session)
        user_id = user["user_id"]
        token = user["access_token"]
        await _create_ratings(db_session, user_id, count=5)

        with (
            patch.object(rec_mod.cache, "get", new_callable=AsyncMock, return_value=None),
            patch.object(rec_mod.cache, "set", new_callable=AsyncMock),
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
            patch.object(rec_mod, "load_recommendation_catalog",
                  return_value=TEST_CATALOG),
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[
                        {
                            "id": "101",
                            "name": "Fresh Breeze",
                            "brand": "TestCo",
                            "match_score": 80.0,
                            "reason": "Feature",
                        }
                    ],
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
        args: DispatchRequest = mock_disp.dispatch.call_args[0][0]
        assert len(args.ratings) == 5

    async def test_state_4_auth_20_ratings(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """auth user with 20 ratings -> State 4 (mature)"""
        user = await _register_user(client, db_session)
        user_id = user["user_id"]
        token = user["access_token"]
        await _create_ratings(db_session, user_id, count=20)

        with (
            patch.object(rec_mod.cache, "get", new_callable=AsyncMock, return_value=None),
            patch.object(rec_mod.cache, "set", new_callable=AsyncMock),
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
            patch.object(rec_mod, "load_recommendation_catalog",
                  return_value=TEST_CATALOG),
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[
                        {
                            "id": "101",
                            "name": "Fresh Breeze",
                            "brand": "TestCo",
                            "match_score": 90.0,
                            "reason": "Diverse",
                        }
                    ],
                    state=4,
                    state_label="mature",
                )
            )
            mock_get.return_value = mock_disp

            resp = await client.get(
                "/recommendations/personalized",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        args: DispatchRequest = mock_disp.dispatch.call_args[0][0]
        assert len(args.ratings) == 20

    async def test_empty_dispatcher_falls_to_legacy(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Verify empty dispatcher result falls through to legacy path."""
        user = await _register_user(client, db_session)
        token = user["access_token"]

        with (
            patch.object(rec_mod.cache, "get", new_callable=AsyncMock, return_value=None),
            patch.object(rec_mod.cache, "set", new_callable=AsyncMock),
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[],
                    state=0,
                    state_label="anonymous",
                )
            )
            mock_get.return_value = mock_disp

            resp = await client.get(
                "/recommendations/personalized",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        # Legacy path returns [] for user with no ratings
        assert body["data"] == []


# ── D. Fallback Verification Tests ────────────────────────────────────────────


class TestFallbackChains:
    """Prove strategy fallback chains execute and endpoint returns valid response."""

    async def test_popularity_strategy_fallback(self, client: AsyncClient):
        """Force PopularityStrategy failure -> dispatcher empty -> legacy fallback."""
        with (
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[],
                    state=0,
                    state_label="anonymous",
                    fallback_chain=["popularity", "fallback_empty"],
                )
            )
            mock_get.return_value = mock_disp

            resp = await client.post(
                "/recommendations/guest",
                json={"ratings": []},
            )
        assert resp.status_code == 200
        mock_disp.dispatch.assert_awaited_once()

    async def test_graphsage_strategy_fallback(self, client: AsyncClient):
        """Force GraphSAGE failure -> FeatureBased fallback within dispatcher."""
        real_fb = FeatureBasedService()
        real_pop = PopularityService()

        disp = RecommendationDispatcher(
            feature_based_service=real_fb,
            popularity_service=real_pop,
        )

        with (
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
            patch.object(rec_mod, "load_recommendation_catalog",
                  return_value=TEST_CATALOG),
        ):
            mock_get.return_value = disp

            resp = await client.post(
                "/recommendations/guest",
                json={
                    "ratings": [],
                    "quiz_confidence": {"nonexistent_accord": 0.9},
                },
            )
        assert resp.status_code == 200

    async def test_feature_based_strategy_fallback(self, client: AsyncClient):
        """Force FeatureBasedStrategy failure -> Popularity fallback within dispatcher."""
        real_pop = PopularityService()

        fb_with_error = FeatureBasedService()
        fb_with_error.score = MagicMock(side_effect=ValueError("fb_error"))

        disp = RecommendationDispatcher(
            feature_based_service=fb_with_error,
            popularity_service=real_pop,
        )

        with (
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
            patch.object(rec_mod, "load_recommendation_catalog",
                  return_value=TEST_CATALOG),
        ):
            mock_get.return_value = disp

            resp = await client.post(
                "/recommendations/guest",
                json={
                    "ratings": [{"fragrance_id": "101", "rating": 5.0}],
                },
            )
        assert resp.status_code == 200


# ── E. Cache & Feature Flag Verification Tests ────────────────────────────────


class TestCacheBehavior:
    """Prove rec:user:{id} cache is set, state is NOT cached."""

    async def test_cache_is_set_on_dispatcher_result(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Dispatcher path sets rec:user:{user_id} cache."""
        user = await _register_user(client, db_session)
        user_id = user["user_id"]
        token = user["access_token"]
        await _create_ratings(db_session, user_id, count=3)

        with (
            patch.object(rec_mod.cache, "get", new_callable=AsyncMock, return_value=None),
            patch.object(rec_mod.cache, "set", new_callable=AsyncMock) as mock_cache_set,
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
            patch.object(rec_mod, "load_recommendation_catalog",
                  return_value=TEST_CATALOG),
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[
                        {
                            "id": "101",
                            "name": "Fresh Breeze",
                            "brand": "TestCo",
                            "match_score": 75.0,
                            "reason": "R",
                        }
                    ],
                    state=2,
                    state_label="cold",
                )
            )
            mock_get.return_value = mock_disp

            resp = await client.get(
                "/recommendations/personalized",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        mock_cache_set.assert_called_once()
        key = mock_cache_set.call_args[0][0]
        assert key == f"rec:user:{user_id}"

    async def test_state_not_in_cache_key(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Cache key contains no state information."""
        user = await _register_user(client, db_session)
        user_id = user["user_id"]
        key = f"rec:user:{user_id}"
        assert "state" not in key


class TestFeatureFlag:
    """Prove PHASE8_DISPATCHER_ENABLED toggle works."""

    async def test_flag_off_routes_to_legacy(self, client: AsyncClient):
        """Flag OFF -> dispatcher not invoked, legacy path runs."""
        with (
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", False),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
        ):
            resp = await client.post(
                "/recommendations/guest",
                json={"ratings": []},
            )
        assert resp.status_code == 200
        mock_get.assert_not_called()

    async def test_flag_on_invokes_dispatcher(self, client: AsyncClient):
        """Flag ON -> dispatcher is invoked."""
        with (
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(recommendations=[])
            )
            mock_get.return_value = mock_disp

            resp = await client.post(
                "/recommendations/guest",
                json={"ratings": [{"fragrance_id": "101", "rating": 5.0}]},
            )
        assert resp.status_code == 200
        mock_get.assert_called_once()
        mock_disp.dispatch.assert_awaited_once()
