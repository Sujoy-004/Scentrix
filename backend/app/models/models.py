"""SQLAlchemy ORM models for Scentrix (users + fragrance_ratings only)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_id(raw_id: str) -> str:
    """Return the canonical ``frag_``-prefixed form of a fragrance ID.

    The catalog and the GraphSAGE node index both key fragrances as
    ``frag_<brand>_<name>_<year>``. Ratings persisted before the prefix
    convention (unprefixed ``fragrance_neo4j_id``) are canonicalised on
    write/read via this helper.
    """
    if not raw_id or not raw_id.strip():
        return raw_id
    if raw_id.startswith("frag_"):
        return raw_id
    return f"frag_{raw_id}"


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preferences_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=dict
    )
    quiz_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, email_hash={self.email_hash})>"


class FragranceRating(Base):
    """User's rating of a fragrance (1-10 scale)."""

    __tablename__ = "fragrance_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "fragrance_neo4j_id", name="uq_user_fragrance_rating"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    fragrance_neo4j_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    quiz_rating: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<FragranceRating(user_id={self.user_id}, "
            f"fragrance={self.fragrance_neo4j_id}, quiz_rating={self.quiz_rating})>"
        )