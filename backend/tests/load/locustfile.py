"""Load testing for Scentrix backend — Phase 12B.

Scenarios:
  - Health check (baseline)
  - Guest recommendation State 0 (popularity, no quiz)
  - Guest recommendation State 1 (GraphSAGE user-vector, with quiz)
  - Quiz session start

Usage:
  locust --headless -u 20 -r 2 --run-time 300s --host http://localhost:8000 --html load_report.html
"""

from __future__ import annotations

import logging
import random

from locust import HttpUser, between, task

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

QUIZ_CONFIDENCE: dict[str, float] = {
    "citrus": 0.9,
    "woody": 0.7,
    "floral": 0.3,
    "fresh": 0.8,
    "sweet": 0.2,
}

QUIZ_START_PAYLOAD: dict = {
    "seed_count": 8,
    "candidate_pool_size": 200,
    "filters": {"exclude_seen": False},
}

# ── Discover fragrance IDs from live catalog ──────────────────────────────────

FRAGRANCE_IDS: list[str] = []


def _discover_fragrance_ids() -> list[str]:
    """Fetch real fragrance IDs from the backend via a State-0 request."""
    import requests as sync_requests
    host = "http://localhost:8000"
    try:
        resp = sync_requests.post(
            f"{host}/recommendations/guest",
            json={"ratings": [], "quiz_confidence": None},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            ids = [item["id"] for item in data.get("data", [])]
            logger.info("Discovered %d fragrance IDs from catalog", len(ids))
            return ids
    except Exception as exc:
        logger.warning("Could not discover fragrance IDs: %s", exc)
    return []


def _init() -> None:
    global FRAGRANCE_IDS
    if not FRAGRANCE_IDS:
        FRAGRANCE_IDS = _discover_fragrance_ids()
        if not FRAGRANCE_IDS:
            FRAGRANCE_IDS = [f"frag_{i:03d}" for i in range(1, 11)]
            logger.warning("Using fallback fragrance IDs: %s", FRAGRANCE_IDS)


_init()

# ── Users ──────────────────────────────────────────────────────────────────────


class HealthCheckUser(HttpUser):
    """Scenario 1: GET /health — baseline server overhead."""

    wait_time = between(1, 3)
    weight = 1

    @task
    def health_check(self) -> None:
        self.client.get("/health")


class GuestRecUser(HttpUser):
    """Scenarios 2 & 3: Guest recommendation — State 0 (popularity) and State 1 (GraphSAGE)."""

    wait_time = between(2, 4)
    weight = 3

    @task(3)
    def state0_popularity(self) -> None:
        """Empty ratings, no quiz → State 0 → PopularityStrategy (pure sort)."""
        self.client.post(
            "/recommendations/guest",
            json={"ratings": [], "quiz_confidence": None},
            name="/recommendations/guest [State 0]",
        )

    @task(2)
    def state1_graphsage(self) -> None:
        """Ratings + quiz_confidence → State 1 → GraphSAGEStrategy (embedding KNN)."""
        count = min(5, len(FRAGRANCE_IDS))
        if count < 5:
            logger.warning("Not enough fragrance IDs for State 1 payload")
            return
        ratings = [
            {
                "fragrance_id": fid,
                "rating": round(random.uniform(6.0, 10.0), 1),
            }
            for fid in random.sample(FRAGRANCE_IDS, count)
        ]
        self.client.post(
            "/recommendations/guest",
            json={"ratings": ratings, "quiz_confidence": QUIZ_CONFIDENCE},
            name="/recommendations/guest [State 1]",
        )


class QuizStartUser(HttpUser):
    """Scenario 4: POST /fragrances/quiz/session/start — quiz session creation."""

    wait_time = between(3, 6)
    weight = 2

    @task
    def start_session(self) -> None:
        self.client.post(
            "/fragrances/quiz/session/start",
            json=QUIZ_START_PAYLOAD,
            name="/quiz/session/start",
        )
