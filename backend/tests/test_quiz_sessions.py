"""Quiz session store tests.

These cover the reason the store moved out of process memory: a quiz session
must be readable by a *different* API instance, and it must expire.
"""

from datetime import UTC, datetime, timedelta

from app.database import SessionLocal
from app.models.models import QuizSession
from app.services.quiz_sessions import (
    QUIZ_TTL,
    create_session,
    delete_session,
    get_session,
    save_session,
)


def _payload(session_id: str = "qz_test1234") -> dict:
    return {
        "session_id": session_id,
        "user_id": None,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "served_ids": ["frag_a"],
        "responses": [],
    }


def test_session_is_readable_from_a_separate_connection():
    """A second worker must see the session - this is the multi-instance fix."""
    db = SessionLocal()
    try:
        create_session(db, "qz_persist01", _payload("qz_persist01"))
    finally:
        db.close()

    # A brand-new connection stands in for a different API instance.
    other = SessionLocal()
    try:
        found = get_session(other, "qz_persist01")
    finally:
        other.close()

    assert found is not None
    assert found["served_ids"] == ["frag_a"]


def test_save_then_read_from_another_connection():
    db = SessionLocal()
    try:
        create_session(db, "qz_save0001", _payload("qz_save0001"))
        payload = _payload("qz_save0001")
        payload["responses"] = [{"fragrance_id": "frag_a", "rating_1_to_10": 9}]
        save_session(db, "qz_save0001", payload)
    finally:
        db.close()

    other = SessionLocal()
    try:
        found = get_session(other, "qz_save0001")
    finally:
        other.close()

    assert found is not None
    assert len(found["responses"]) == 1


def test_expired_session_is_rejected_and_removed():
    db = SessionLocal()
    try:
        create_session(db, "qz_expired01", _payload("qz_expired01"))
        row = db.get(QuizSession, "qz_expired01")
        assert row is not None
        # Backdate the expiry past the TTL.
        row.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()

    other = SessionLocal()
    try:
        found = get_session(other, "qz_expired01")
        remaining = other.get(QuizSession, "qz_expired01")
    finally:
        other.close()

    assert found is None
    assert remaining is None, "expired session rows should be cleaned up on read"


def test_ttl_is_measured_from_creation_not_from_the_last_write():
    """A long quiz must still expire 30 minutes after it started."""
    old = datetime.now(UTC) - (QUIZ_TTL - timedelta(minutes=1))
    payload = _payload("qz_ttl00001")
    payload["created_at"] = old.isoformat()

    db = SessionLocal()
    try:
        create_session(db, "qz_ttl00001", payload)
        # A write must not extend the lifetime.
        save_session(db, "qz_ttl00001", payload)
        found = get_session(db, "qz_ttl00001")
    finally:
        db.close()

    assert found is not None, "session should still be alive 1 minute before expiry"


def test_delete_session_removes_the_row():
    db = SessionLocal()
    try:
        create_session(db, "qz_delete001", _payload("qz_delete001"))
        delete_session(db, "qz_delete001")
        assert db.get(QuizSession, "qz_delete001") is None
    finally:
        db.close()


def test_api_start_persists_the_session_to_the_database(client):
    """The end-to-end proof: the API writes the session to the DB."""
    start = client.post(
        "/fragrances/quiz/session/start",
        json={"seed_count": 6, "candidate_pool_size": 200},
    )
    assert start.status_code == 200
    session_id = start.json()["data"]["session_id"]

    db = SessionLocal()
    try:
        row = db.get(QuizSession, session_id)
    finally:
        db.close()

    assert row is not None, "quiz session should be persisted, not held in process memory"


def test_starting_a_session_purges_abandoned_expired_rows(client):
    """Expired sessions nobody ever reads again must not pile up."""
    db = SessionLocal()
    try:
        create_session(db, "qz_abandon01", _payload("qz_abandon01"))
        row = db.get(QuizSession, "qz_abandon01")
        assert row is not None
        row.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()

    start = client.post(
        "/fragrances/quiz/session/start",
        json={"seed_count": 6, "candidate_pool_size": 200},
    )
    assert start.status_code == 200

    db = SessionLocal()
    try:
        assert db.get(QuizSession, "qz_abandon01") is None
    finally:
        db.close()
