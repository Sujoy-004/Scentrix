"""SQLAlchemy ORM models for Scentrix.

Defines user auth/session entities, ratings/saves, and interaction ingestion models.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    """User account model.

    Stores authentication, GDPR preferences, and account metadata.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supabase_user_id: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(20), default="local", nullable=False)
    encrypted_full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # GDPR fields
    gdpr_deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
    )
    opt_in_training: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="User consents to use of their data for model training",
    )
    preferences_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, provider={self.auth_provider}, email_hash={self.email_hash})>"


class FragranceRating(Base):
    """User's rating of a fragrance.

    Stores a simple quiz_rating (1-10 from the neural discovery quiz) and
    optionally the 5 perceptual dimensions for advanced analytics.
    """

    __tablename__ = "fragrance_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "fragrance_neo4j_id", name="uq_user_fragrance_rating"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fragrance_neo4j_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Simple quiz rating (1-10 scale) — set by the Discovery Protocol
    quiz_rating: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Five perceptual dimensions (0-5 scale) — legacy/advanced analytics
    rating_sweetness: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating_woodiness: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating_longevity: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating_projection: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating_freshness: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_satisfaction: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Metadata
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
            f"fragrance={self.fragrance_neo4j_id}, "
            f"quiz_rating={self.quiz_rating})>"
        )


class SavedFragrance(Base):
    """User's saved fragrance collection.

    Stores bookmarked or favorited fragrances.
    """

    __tablename__ = "saved_fragrances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fragrance_neo4j_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<SavedFragrance(user_id={self.user_id}, fragrance={self.fragrance_neo4j_id})>"


class RefreshToken(Base):
    """Refresh token storage for JWT rotation.

    Stores user refresh tokens for secure session management.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<RefreshToken(user_id={self.user_id})>"


class UserInteractionEvent(Base):
    """Raw user-fragrance interaction events for recommendation training ingestion."""

    __tablename__ = "user_interaction_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fragrance_neo4j_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    interaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Event type, e.g. view, click, save, rate, purchase",
    )
    interaction_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Optional numeric value (e.g., dwell_seconds, rating)",
    )
    source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Origin channel (web, mobile, api, import)",
    )
    context_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional serialized metadata for offline feature generation",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            "<UserInteractionEvent("
            f"user_id={self.user_id}, "
            f"fragrance={self.fragrance_neo4j_id}, "
            f"type={self.interaction_type})>"
        )
