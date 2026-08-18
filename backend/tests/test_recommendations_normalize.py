"""Tests for canonical fragrance-ID normalisation (prefixed ``frag_`` form).

Guards the end-to-end fix: ``FragranceRating.fragrance_neo4j_id`` must be
stored and read in the same format as catalog ids / GraphSAGE node ids
(``frag_<brand>_<name>_<year>``), and legacy unprefixed rows must keep
working for existing users (read-path canonicalisation + write-path upgrade).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import FragranceRating as DBFragranceRating
from app.models.models import User
from app.routers import recommendations as rec_mod
from app.routers.recommendations import _normalize_id

# ── Catalog with canonical (prefixed) ids ─────────────────────────────────────


def _catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": "frag_test-brand_fresh-breeze_2024",
            "name": "Fresh Breeze",
            "brand": "TestBrand",
            "accords": ["fresh", "citrus"],
            "top_notes": ["lemon", "bergamot"],
            "rating_count": 42,
            "_accords_set": {"fresh", "citrus"},
            "_notes_set": {"lemon", "bergamot"},
        },
        {
            "id": "frag_test-brand_woody-night_2024",
            "name": "Woody Night",
            "brand": "TestBrand",
            "accords": ["woody", "amber"],
            "top_notes": ["sandalwood", "vanilla"],
            "rating_count": 33,
            "_accords_set": {"woody", "amber"},
            "_notes_set": {"sandalwood", "vanilla"},
        },
        {
            "id": "frag_test-brand_ocean-mist_2024",
            "name": "Ocean Mist",
            "brand": "TestBrand",
            "accords": ["aquatic", "fresh"],
            "top_notes": ["sea salt", "algae"],
            "rating_count": 28,
            "_accords_set": {"aquatic", "fresh"},
            "_notes_set": {"sea salt", "algae"},
        },
    ]


async def _register_user(client: AsyncClient, db_session: AsyncSession) -> dict:
    import uuid

    email = f"norm_{uuid.uuid4().hex[:8]}@example.com"
    resp = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPass123!",
            "username": f"norm_{uuid.uuid4().hex[:6]}",
            "opt_in_training": True,
        },
    )
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    data = resp.json()["data"]
    email_hash = hashlib.sha256(email.lower().strip().encode()).hexdigest()
    result = await db_session.execute(select(User).where(User.email_hash == email_hash))
    user = result.scalar_one()
    return {"user_id": user.id, "access_token": data["access_token"]}


# ── _normalize_id unit tests ──────────────────────────────────────────────────


class TestNormalizeId:
    def test_prepends_prefix_to_legacy_unprefixed_id(self) -> None:
        assert (
            _normalize_id("hermes_tutti-twilly-d-hermes_2023")
            == "frag_hermes_tutti-twilly-d-hermes_2023"
        )

    def test_preserves_existing_prefix(self) -> None:
        assert (
            _normalize_id("frag_hermes_tutti-twilly-d-hermes_2023")
            == "frag_hermes_tutti-twilly-d-hermes_2023"
        )

    def test_preserves_syn_prefixed_id(self) -> None:
        # frag_syn_ ids start with frag_ so they are already canonical.
        assert _normalize_id("frag_syn_placeholder") == "frag_syn_placeholder"

    def test_empty_string_passes_through(self) -> None:
        # Empty/whitespace ids must not be turned into junk "frag_" seeds.
        assert _normalize_id("") == ""
        assert _normalize_id("   ") == "   "


# ── Write-path tests (/rate) ──────────────────────────────────────────────────


class TestRateWritePath:
    pytestmark = pytest.mark.asyncio

    async def test_rate_stores_prefixed_id(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _register_user(client, db_session)
        headers = {"Authorization": f"Bearer {user['access_token']}"}

        resp = await client.post(
            "/recommendations/rate",
            headers=headers,
            json={"fragrance_id": "frag_test-brand_fresh-breeze_2024", "rating": 8.0},
        )
        assert resp.status_code == 200

        result = await db_session.execute(
            select(DBFragranceRating).where(DBFragranceRating.user_id == user["user_id"])
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].fragrance_neo4j_id == "frag_test-brand_fresh-breeze_2024"
        assert rows[0].quiz_rating == 8.0

    async def test_rate_canonicalizes_unprefixed_input(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _register_user(client, db_session)
        headers = {"Authorization": f"Bearer {user['access_token']}"}

        resp = await client.post(
            "/recommendations/rate",
            headers=headers,
            json={"fragrance_id": "test-brand_fresh-breeze_2024", "rating": 7.0},
        )
        assert resp.status_code == 200

        result = await db_session.execute(
            select(DBFragranceRating).where(DBFragranceRating.user_id == user["user_id"])
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].fragrance_neo4j_id == "frag_test-brand_fresh-breeze_2024"

    async def test_rate_upgrades_legacy_row_in_place(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Re-rating a legacy unprefixed row must upgrade it, not duplicate it."""
        user = await _register_user(client, db_session)
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        db_session.add(
            DBFragranceRating(
                user_id=user["user_id"],
                fragrance_neo4j_id="test-brand_fresh-breeze_2024",
                quiz_rating=6.0,
            )
        )
        await db_session.commit()

        resp = await client.post(
            "/recommendations/rate",
            headers=headers,
            json={"fragrance_id": "frag_test-brand_fresh-breeze_2024", "rating": 9.0},
        )
        assert resp.status_code == 200

        result = await db_session.execute(
            select(DBFragranceRating).where(DBFragranceRating.user_id == user["user_id"])
        )
        rows = result.scalars().all()
        assert len(rows) == 1, "Legacy re-rate must not create a duplicate row"
        assert rows[0].fragrance_neo4j_id == "frag_test-brand_fresh-breeze_2024"
        assert rows[0].quiz_rating == 9.0


# ── Read-path tests (personalized + quiz-summary) ─────────────────────────────


class TestPersonalizedReadPath:
    pytestmark = pytest.mark.asyncio

    async def test_personalized_canonicalizes_legacy_rows(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Legacy unprefixed stored rows are canonicalised before dispatch."""
        user = await _register_user(client, db_session)
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        db_session.add(
            DBFragranceRating(
                user_id=user["user_id"],
                fragrance_neo4j_id="test-brand_fresh-breeze_2024",
                quiz_rating=8.0,
            )
        )
        await db_session.commit()

        with (
            patch.object(rec_mod.cache, "get", new_callable=AsyncMock, return_value=None),
            patch.object(rec_mod.cache, "set", new_callable=AsyncMock),
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
            patch.object(rec_mod, "load_recommendation_catalog", return_value=_catalog()),
        ):
            mock_disp = MagicMock(spec=rec_mod.RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[
                        {
                            "id": "frag_test-brand_woody-night_2024",
                            "name": "Woody Night",
                            "brand": "TestBrand",
                            "match_score": 75.0,
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
                headers=headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["state"] == 2
        assert body["state_label"] == "cold"
        args = mock_disp.dispatch.call_args[0][0]
        assert len(args.ratings) == 1
        assert args.ratings[0].fragrance_id == "frag_test-brand_fresh-breeze_2024"


class TestQuizSummary:
    pytestmark = pytest.mark.asyncio

    async def test_quiz_summary_populates_notes_from_legacy_rows(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Legacy unprefixed rows still contribute top_notes/top_accords."""
        user = await _register_user(client, db_session)
        headers = {"Authorization": f"Bearer {user['access_token']}"}

        result = await db_session.execute(select(User).where(User.id == user["user_id"]))
        u = result.scalar_one()
        u.quiz_completed_at = datetime.now(UTC).replace(tzinfo=None)
        db_session.add(
            DBFragranceRating(
                user_id=user["user_id"],
                fragrance_neo4j_id="test-brand_fresh-breeze_2024",
                quiz_rating=8.0,
            )
        )
        await db_session.commit()

        with (
            patch.object(rec_mod, "load_recommendation_catalog", return_value=_catalog()),
            patch.object(rec_mod, "_feature_based_service", None),
        ):
            resp = await client.get(
                "/recommendations/quiz-summary",
                headers=headers,
            )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["has_completed_quiz"] is True
        assert data["total_rated"] == 1
        assert data["top_notes"], "top_notes must be populated from the rated fragrance"
        assert data["top_accords"], "top_accords must be populated from the rated fragrance"
        assert "lemon" in data["top_notes"] or "bergamot" in data["top_notes"]
