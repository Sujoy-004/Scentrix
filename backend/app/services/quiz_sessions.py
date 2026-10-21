"""Quiz session store.

The adaptive quiz spans several HTTP requests, so the session state has to
survive between them. It used to live in a process-local dict, which meant a
session was invisible to any other API instance - the flow broke as soon as
the backend ran on more than one worker (serverless, or any scaled
deployment). It is now stored in the database, which works identically on one
process or many.

The whole session is kept as a JSON payload so the stored shape can evolve
without a migration. Expiry is enforced on read: a row past ``expires_at`` is
deleted and reported as missing.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import QuizSession

logger = logging.getLogger(__name__)

QUIZ_TTL = timedelta(minutes=30)


def _utcnow() -> datetime:
    """Naive UTC now - matches the naive DateTime columns used by the models."""
    return datetime.now(UTC).replace(tzinfo=None)


def _expires_at(payload: dict[str, Any]) -> datetime:
    """Derive the session expiry from the payload's creation time.

    The TTL is measured from creation and is deliberately *not* refreshed on
    every write, so a long quiz still expires 30 minutes after it started.
    """
    created = payload.get("created_at")
    if isinstance(created, str):
        try:
            parsed = datetime.fromisoformat(created)
        except (ValueError, TypeError):
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(UTC).replace(tzinfo=None)
            return parsed + QUIZ_TTL
    return _utcnow() + QUIZ_TTL


def create_session(db: Session, session_id: str, payload: dict[str, Any]) -> None:
    """Persist a new session."""
    db.add(
        QuizSession(
            id=session_id,
            user_id=payload.get("user_id"),
            payload=dict(payload),
            expires_at=_expires_at(payload),
        )
    )
    db.commit()
    _purge_expired(db)


def _purge_expired(db: Session) -> None:
    """Delete sessions that expired without ever being read again.

    Abandoned sessions are never read, so the read-time cleanup never sees
    them. Sweeping on create keeps the table bounded without a background job.
    """
    db.query(QuizSession).filter(QuizSession.expires_at < _utcnow()).delete(
        synchronize_session=False
    )
    db.commit()


def get_session(db: Session, session_id: str) -> dict[str, Any] | None:
    """Return the session payload, or None if missing or expired.

    An expired row is deleted as a side effect so the table self-cleans
    without a separate sweep job.
    """
    row = db.get(QuizSession, session_id)
    if row is None:
        return None

    if row.expires_at < _utcnow():
        db.delete(row)
        db.commit()
        return None

    return dict(row.payload)


def save_session(db: Session, session_id: str, payload: dict[str, Any]) -> None:
    """Write the session payload back, creating the row if it is gone."""
    row = db.get(QuizSession, session_id)
    if row is None:
        create_session(db, session_id, payload)
        return

    row.payload = dict(payload)
    row.user_id = payload.get("user_id")
    row.updated_at = _utcnow()
    db.commit()


def delete_session(db: Session, session_id: str) -> None:
    """Remove a session (used after finalize)."""
    row = db.get(QuizSession, session_id)
    if row is not None:
        db.delete(row)
        db.commit()
