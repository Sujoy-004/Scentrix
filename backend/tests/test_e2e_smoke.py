"""E2E guest quiz smoke validation — adapted from e2e_smoke.py.

Covers the full guest quiz lifecycle:
  1. Start quiz session
  2. Submit seed answers
  3. Evaluate (force=true)
  4. Guest finalize
  5. Re-evaluate after finalize (refresh simulation)
  6. Guest recommendations with quiz_confidence (state=1)
  7. Cold start recommendations (no quiz_confidence, state=0)
  8. Authenticated finalize still gated by JWT
  9. Fresh guest → state=0 expected

No external dependencies — uses the test AsyncClient + monkeypatch for quiz store.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.routers import quiz as quiz_router
from app.routers import recommendations as rec_mod
from app.services.dispatcher import RecommendationDispatcher

pytestmark = pytest.mark.asyncio

SAMPLE_CATALOG = [
    {"id": "frag_001", "name": "Citrus Dawn", "brand": "Brand A",
     "top_notes": ["Bergamot", "Lemon"], "accords": ["Citrus", "Fresh"],
     "review_count": 120, "view_count": 9000, "popularity_score": 74},
    {"id": "frag_002", "name": "Woods Echo", "brand": "Brand B",
     "top_notes": ["Cedar", "Pepper"], "accords": ["Woody", "Spicy"],
     "review_count": 90, "view_count": 7000, "popularity_score": 67},
    {"id": "frag_003", "name": "Floral Mist", "brand": "Brand C",
     "top_notes": ["Rose", "Violet"], "accords": ["Floral", "Powdery"],
     "review_count": 80, "view_count": 6400, "popularity_score": 61},
    {"id": "frag_004", "name": "Amber Night", "brand": "Brand D",
     "top_notes": ["Saffron", "Cardamom"], "accords": ["Amber", "Warm"],
     "review_count": 110, "view_count": 8200, "popularity_score": 71},
    {"id": "frag_005", "name": "Marine Air", "brand": "Brand E",
     "top_notes": ["Sea Salt", "Grapefruit"], "accords": ["Aquatic", "Fresh"],
     "review_count": 95, "view_count": 7600, "popularity_score": 69},
    {"id": "frag_006", "name": "Smoked Leather", "brand": "Brand F",
     "top_notes": ["Leather", "Incense"], "accords": ["Smoky", "Leather"],
     "review_count": 76, "view_count": 5100, "popularity_score": 58},
    {"id": "frag_007", "name": "Vanilla Thread", "brand": "Brand G",
     "top_notes": ["Vanilla", "Tonka"], "accords": ["Gourmand", "Sweet"],
     "review_count": 103, "view_count": 8000, "popularity_score": 72},
    {"id": "frag_008", "name": "Green Path", "brand": "Brand H",
     "top_notes": ["Galbanum", "Mint"], "accords": ["Green", "Aromatic"],
     "review_count": 70, "view_count": 4300, "popularity_score": 54},
]


@pytest.fixture
def quiz_store(monkeypatch: pytest.MonkeyPatch) -> dict[str, dict]:
    store: dict[str, dict] = {}

    async def fake_create(session_id: str, payload: dict):
        store[session_id] = payload

    async def fake_get(session_id: str):
        return store.get(session_id)

    async def fake_save(session_id: str, payload: dict):
        store[session_id] = payload

    monkeypatch.setattr(quiz_router, "load_recommendation_catalog", lambda: SAMPLE_CATALOG)
    monkeypatch.setattr(quiz_router, "create_quiz_session", fake_create)
    monkeypatch.setattr(quiz_router, "get_quiz_session", fake_get)
    monkeypatch.setattr(quiz_router, "save_quiz_session", fake_save)
    return store


async def _start_quiz(client: AsyncClient, quiz_store: dict) -> str:
    resp = await client.post(
        "/fragrances/quiz/session/start",
        json={"seed_count": 8, "candidate_pool_size": 250, "filters": {"exclude_seen": True}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    data = body["data"]
    assert data["session_id"]
    assert len(data["seed_questions"]) >= 8
    return data["session_id"], data["seed_questions"]


class TestGuestQuizSmoke:
    """Full guest quiz lifecycle — 9 smoke checks."""

    async def test_1_start_quiz(self, client: AsyncClient, quiz_store: dict):
        """Check 1-4: Start quiz session."""
        sid, questions = await _start_quiz(client, quiz_store)
        assert sid.startswith("qz_")

    async def test_2_submit_answers(self, client: AsyncClient, quiz_store: dict):
        """Check 5: Submit 8 answers."""
        sid, questions = await _start_quiz(client, quiz_store)
        for i, q in enumerate(questions):
            resp = await client.post(
                f"/fragrances/quiz/session/{sid}/answer",
                json={"fragrance_id": q["fragrance_id"], "rating_1_to_10": 5.0 + (i % 5), "source": "standard_quiz"},
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["accepted"] is True

    async def test_3_evaluate(self, client: AsyncClient, quiz_store: dict):
        """Check 6: Evaluate with force=true."""
        sid, questions = await _start_quiz(client, quiz_store)
        for i, q in enumerate(questions):
            await client.post(
                f"/fragrances/quiz/session/{sid}/answer",
                json={"fragrance_id": q["fragrance_id"], "rating_1_to_10": 5.0 + (i % 5), "source": "standard_quiz"},
            )
        resp = await client.post(
            f"/fragrances/quiz/session/{sid}/evaluate",
            json={"force": True},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["confidence_score"] is not None
        assert data["stop_reason"] is not None

    async def test_4_guest_finalize(self, client: AsyncClient, quiz_store: dict):
        """Check 7: Guest finalize (no auth)."""
        sid, questions = await _start_quiz(client, quiz_store)
        for i, q in enumerate(questions):
            await client.post(
                f"/fragrances/quiz/session/{sid}/answer",
                json={"fragrance_id": q["fragrance_id"], "rating_1_to_10": 5.0 + (i % 5), "source": "standard_quiz"},
            )
        await client.post(
            f"/fragrances/quiz/session/{sid}/evaluate",
            json={"force": True},
        )
        resp = await client.post(f"/fragrances/quiz/session/{sid}/guest-finalize")
        assert resp.status_code == 200
        assert resp.json()["data"]["message"] == "Guest quiz finalized"

    async def test_5_session_after_finalize(self, client: AsyncClient, quiz_store: dict):
        """Check 8: Session re-evaluable after finalize."""
        sid, questions = await _start_quiz(client, quiz_store)
        for i, q in enumerate(questions):
            await client.post(
                f"/fragrances/quiz/session/{sid}/answer",
                json={"fragrance_id": q["fragrance_id"], "rating_1_to_10": 5.0 + (i % 5), "source": "standard_quiz"},
            )
        await client.post(f"/fragrances/quiz/session/{sid}/evaluate", json={"force": True})
        await client.post(f"/fragrances/quiz/session/{sid}/guest-finalize")
        resp = await client.post(f"/fragrances/quiz/session/{sid}/evaluate", json={"force": True})
        assert resp.status_code == 200

    async def test_6_guest_recs_with_quiz_confidence(
        self, client: AsyncClient, quiz_store: dict
    ):
        """Check 9-13: Guest recs with quiz_confidence have state."""
        sid, questions = await _start_quiz(client, quiz_store)
        for i, q in enumerate(questions):
            await client.post(
                f"/fragrances/quiz/session/{sid}/answer",
                json={"fragrance_id": q["fragrance_id"], "rating_1_to_10": 5.0 + (i % 5), "source": "standard_quiz"},
            )
        await client.post(f"/fragrances/quiz/session/{sid}/evaluate", json={"force": True})
        await client.post(f"/fragrances/quiz/session/{sid}/guest-finalize")

        ratings_payload = [{"fragrance_id": q["fragrance_id"], "rating": 5.0} for q in questions]
        with (
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[{
                        "id": "frag_001", "name": "Citrus Dawn", "brand": "Brand A",
                        "match_score": 85.0, "reason": "Quiz Match", "source": "graphsage",
                    }],
                    state=1, state_label="quiz_user",
                )
            )
            mock_get.return_value = mock_disp
            resp = await client.post(
                "/recommendations/guest",
                json={"ratings": ratings_payload, "quiz_confidence": {"citrus": 0.8, "floral": 0.3, "woody": 0.7}},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["state"] == 1
        assert body["state_label"] == "quiz_user"
        assert isinstance(body["data"], list)
        assert len(body["data"]) > 0

    async def test_7_cold_start_recommendations(
        self, client: AsyncClient, quiz_store: dict
    ):
        """Check 14-16: Cold start recs without quiz_confidence."""
        sid, questions = await _start_quiz(client, quiz_store)
        ratings = [{"fragrance_id": q["fragrance_id"], "rating": 5.0} for q in questions[:3]]
        with (
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[{
                        "id": "frag_001", "name": "Citrus Dawn", "brand": "Brand A",
                        "match_score": 70.0, "reason": "Popular", "source": "popularity",
                    }],
                    state=2, state_label="cold",
                )
            )
            mock_get.return_value = mock_disp
            resp = await client.post(
                "/recommendations/guest",
                json={"ratings": ratings},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "state" in body
        assert "state_label" in body

    async def test_8_authenticated_finalize_gated(
        self, client: AsyncClient, quiz_store: dict
    ):
        """Check 17: /finalize returns 401 without auth."""
        resp = await client.post("/fragrances/quiz/session/qx_any/finalize")
        assert resp.status_code == 401

    async def test_9_fresh_guest_state_0(
        self, client: AsyncClient, quiz_store: dict
    ):
        """Check 18-20: Fresh guest → state=0 expected."""
        with (
            patch.object(rec_mod, "PHASE8_DISPATCHER_ENABLED", True),
            patch.object(rec_mod, "_get_dispatcher") as mock_get,
        ):
            mock_disp = MagicMock(spec=RecommendationDispatcher)
            mock_disp.dispatch = AsyncMock(
                return_value=MagicMock(
                    recommendations=[{
                        "id": "frag_001", "name": "Citrus Dawn", "brand": "Brand A",
                        "match_score": 50.0, "reason": "Popular", "source": "popularity",
                    }],
                    state=0, state_label="anonymous",
                )
            )
            mock_get.return_value = mock_disp
            resp = await client.post(
                "/recommendations/guest",
                json={"ratings": [], "quiz_confidence": None},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == 0
        assert body["state_label"] == "anonymous"
