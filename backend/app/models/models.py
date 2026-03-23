"""SQLAlchemy ORM models for ScentScape.

Defines User, FragranceRating, SavedFragrance, and session models.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base, mapped_column

Base = declarative_base()


class User(Base):
    """User account model.

    Stores authentication, GDPR preferences, and account metadata.
    """

    __tablename__ = "users"

    id: int = mapped_column(Integer, primary_key=True, index=True)
    email: str = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: str = mapped_column(String(255), nullable=False)
    is_active: bool = mapped_column(Boolean, default=True, index=True)
    created_at: datetime = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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
    created_at: datetime = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    id: int = mapped_column(Integer, primary_key=True, index=True)
    user_id: int = mapped_column(Integer, nullable=False, index=True)
    fragrance_neo4j_id: str = mapped_column(String(100), nullable=False, index=True)
    notes: Optional[str] = mapped_column(Text, nullable=True)
    created_at: datetime = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<SavedFragrance(user_id={self.user_id}, fragrance={self.fragrance_neo4j_id})>"


class RefreshToken(Base):
    """Refresh token storage for JWT rotation.

    Stores user refresh tokens for secure session management.
    """

    __tablename__ = "refresh_tokens"

    id: int = mapped_column(Integer, primary_key=True, index=True)
    user_id: int = mapped_column(Integer, nullable=False, index=True)
    token: str = mapped_column(String(500), unique=True, nullable=False)
    expires_at: datetime = mapped_column(DateTime, nullable=False)
    revoked_at: Optional[datetime] = mapped_column(DateTime, nullable=True, default=None)
    created_at: datetime = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<RefreshToken(user_id={self.user_id})>"
