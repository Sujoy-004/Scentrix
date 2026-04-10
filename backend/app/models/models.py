"""SQLAlchemy ORM models for ScentScape.

Defines user auth/session entities, ratings/saves, and interaction ingestion models.
"""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base, mapped_column, Mapped

Base = declarative_base()


def utc_now() -> datetime:
    # DB columns are TIMESTAMP WITHOUT TIME ZONE, so store UTC as naive.
    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    """User account model.

    Stores authentication, GDPR preferences, and account metadata.
    """

    __tablename__ = "users"
    __allow_unmapped__ = True

    id: int = mapped_column(Integer, primary_key=True, index=True)
    encrypted_email: str = mapped_column(Text, unique=True, nullable=False)
    email_hash: str = mapped_column(String(64), unique=True, index=True, nullable=False)
    hashed_password: str = mapped_column(String(255), nullable=False)
    role: str = mapped_column(String(20), default="user", nullable=False)
    is_active: bool = mapped_column(Boolean, default=True, index=True)
    created_at: datetime = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: datetime = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # GDPR fields
    gdpr_deletion_requested_at: Optional[datetime] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
    )
    opt_in_training: bool = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="User consents to use of their data for model training",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class FragranceRating(Base):
    """User's rating of a fragrance across 5 dimensions.

    Stores perceptual ratings (sweetness, woodiness, etc.) and overall satisfaction.
    """

    __tablename__ = "fragrance_ratings"
    __allow_unmapped__ = True

    id: int = mapped_column(Integer, primary_key=True, index=True)
    user_id: int = mapped_column(Integer, nullable=False, index=True)
    fragrance_neo4j_id: str = mapped_column(String(100), nullable=False, index=True)

    # Five perceptual dimensions (0-5 scale)
    rating_sweetness: float = mapped_column(Float, nullable=False)
    rating_woodiness: float = mapped_column(Float, nullable=False)
    rating_longevity: float = mapped_column(Float, nullable=False)
    rating_projection: float = mapped_column(Float, nullable=False)
    rating_freshness: float = mapped_column(Float, nullable=False)

    # Overall satisfaction (0-5 scale)
    overall_satisfaction: float = mapped_column(Float, nullable=False)

    # Metadata
    created_at: datetime = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: datetime = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<FragranceRating(user_id={self.user_id}, "
            f"fragrance={self.fragrance_neo4j_id}, "
            f"satisfaction={self.overall_satisfaction})>"
        )


class SavedFragrance(Base):
    """User's saved fragrance collection.

    Stores bookmarked or favorited fragrances.
    """

    __tablename__ = "saved_fragrances"
    __allow_unmapped__ = True

    id: int = mapped_column(Integer, primary_key=True, index=True)
    user_id: int = mapped_column(Integer, nullable=False, index=True)
    fragrance_neo4j_id: str = mapped_column(String(100), nullable=False, index=True)
    notes: Optional[str] = mapped_column(Text, nullable=True)
    created_at: datetime = mapped_column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<SavedFragrance(user_id={self.user_id}, fragrance={self.fragrance_neo4j_id})>"


class RefreshToken(Base):
    """Refresh token storage for JWT rotation.

    Stores user refresh tokens for secure session management.
    """

    __tablename__ = "refresh_tokens"
    __allow_unmapped__ = True

    id: int = mapped_column(Integer, primary_key=True, index=True)
    user_id: int = mapped_column(Integer, nullable=False, index=True)
    token: str = mapped_column(String(500), unique=True, nullable=False)
    expires_at: datetime = mapped_column(DateTime, nullable=False)
    revoked_at: Optional[datetime] = mapped_column(DateTime, nullable=True, default=None)
    created_at: datetime = mapped_column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<RefreshToken(user_id={self.user_id})>"


class UserInteractionEvent(Base):
    """Raw user-fragrance interaction events for recommendation training ingestion."""

    __tablename__ = "user_interaction_events"
    __allow_unmapped__ = True

    id: int = mapped_column(Integer, primary_key=True, index=True)
    user_id: int = mapped_column(Integer, nullable=False, index=True)
    fragrance_neo4j_id: str = mapped_column(String(100), nullable=False, index=True)
    interaction_type: str = mapped_column(
        String(50),
        nullable=False,
        comment="Event type, e.g. view, click, save, rate, purchase",
    )
    interaction_value: Optional[float] = mapped_column(
        Float,
        nullable=True,
        comment="Optional numeric value (e.g., dwell_seconds, rating)",
    )
    source: Optional[str] = mapped_column(
        String(50),
        nullable=True,
        comment="Origin channel (web, mobile, api, import)",
    )
    context_json: Optional[str] = mapped_column(
        Text,
        nullable=True,
        comment="Optional serialized metadata for offline feature generation",
    )
    created_at: datetime = mapped_column(DateTime, default=utc_now, nullable=False, index=True)

    def __repr__(self) -> str:
        return (
            "<UserInteractionEvent("
            f"user_id={self.user_id}, "
            f"fragrance={self.fragrance_neo4j_id}, "
            f"type={self.interaction_type})>"
        )
