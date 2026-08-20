"""Shared pytest fixtures for the Scentrix backend test suite.

Bootstraps ``sys.path`` so ``app.*`` imports resolve when pytest is run
from ``backend/`` (or anywhere), initialises the SQLite schema once, and
cleans up test-only DB rows between tests.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import FragranceRating, User  # noqa: E402
from app.services.embeddings import gs_service  # noqa: E402

TEST_EMAIL_PATTERN = "test-%@example.com"


@pytest.fixture(scope="session", autouse=True)
def _app_bootstrap():
    """Create DB tables and warm the embedding cache once per session."""
    init_db()
    gs_service.initialize()
    yield


@pytest.fixture()
def client():
    """TestClient wrapping the real app (runs lifespan: init_db + embeddings)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Remove test users and their ratings after every test."""
    yield
    db = SessionLocal()
    try:
        rows = db.query(User).filter(User.email.like(TEST_EMAIL_PATTERN)).all()
        user_ids = [u.id for u in rows]
        if user_ids:
            db.query(FragranceRating).filter(
                FragranceRating.user_id.in_(user_ids)
            ).delete(synchronize_session=False)
            for u in rows:
                db.delete(u)
            db.commit()
    finally:
        db.close()