"""T2.5: User management endpoints.

Provides endpoints for:
- Get user profile
- Submit fragrance ratings
- Manage saved fragrance collections
- GDPR data deletion request
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_id
from app.auth.encryption import vault
from app.database import get_session
from app.models.models import FragranceRating, SavedFragrance, User
from app.schemas.schemas import (
    FragranceRatingCreate,
    FragranceRatingResponse,
    SavedFragranceCreate,
    SavedFragranceResponse,
    UserProfile,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


def _utc_now_naive() -> datetime:
    # DB columns are TIMESTAMP WITHOUT TIME ZONE.
    return datetime.utcnow()


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> UserProfile:
    """Get current user's profile.

    Args:
        user_id: Current authenticated user
        session: Database session

    Returns:
        User profile data

    Raises:
        HTTPException: 404 if user not found
    """
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Decrypt email for profile response
    email = vault.decrypt(user.encrypted_email)

    return UserProfile(
        id=user.id,
        email=email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        opt_in_training=user.opt_in_training,
    )


@router.post(
    "/ratings", response_model=FragranceRatingResponse, status_code=status.HTTP_201_CREATED
)
async def submit_fragrance_rating(
    rating: FragranceRatingCreate,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> FragranceRatingResponse:
    """Submit or update a fragrance rating.

    If user already rated this fragrance, the rating is updated.

    Args:
        rating: FragranceRatingCreate with dimensions and overall satisfaction
        user_id: Current authenticated user
        session: Database session

    Returns:
        Created or updated fragrance rating
    """
    # Check if rating already exists
    stmt = select(FragranceRating).where(
        FragranceRating.user_id == user_id,
        FragranceRating.fragrance_neo4j_id == rating.fragrance_neo4j_id,
    )
    result = await session.execute(stmt)
    existing_rating = result.scalar_one_or_none()

    if existing_rating:
        # Update existing rating
        existing_rating.rating_sweetness = rating.rating_sweetness
        existing_rating.rating_woodiness = rating.rating_woodiness
        existing_rating.rating_longevity = rating.rating_longevity
        existing_rating.rating_projection = rating.rating_projection
        existing_rating.rating_freshness = rating.rating_freshness
        existing_rating.overall_satisfaction = rating.overall_satisfaction
        existing_rating.updated_at = _utc_now_naive()

        await session.commit()
        logger.info(f"Updated rating for user {user_id} on {rating.fragrance_neo4j_id}")
        return FragranceRatingResponse.model_validate(existing_rating)
    else:
        # Create new rating
        new_rating = FragranceRating(
            user_id=user_id,
            fragrance_neo4j_id=rating.fragrance_neo4j_id,
            rating_sweetness=rating.rating_sweetness,
            rating_woodiness=rating.rating_woodiness,
            rating_longevity=rating.rating_longevity,
            rating_projection=rating.rating_projection,
            rating_freshness=rating.rating_freshness,
            overall_satisfaction=rating.overall_satisfaction,
        )
        session.add(new_rating)
        await session.commit()
        logger.info(f"Created rating for user {user_id} on {rating.fragrance_neo4j_id}")
        return FragranceRatingResponse.model_validate(new_rating)


@router.get("/ratings", response_model=list[FragranceRatingResponse])
async def get_user_ratings(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[FragranceRatingResponse]:
    """Get all of user's fragrance ratings.

    Args:
        user_id: Current authenticated user
        session: Database session

    Returns:
        List of user's fragrance ratings
    """
    stmt = select(FragranceRating).where(FragranceRating.user_id == user_id)
    result = await session.execute(stmt)
    ratings = result.scalars().all()

    return [FragranceRatingResponse.model_validate(r) for r in ratings]


@router.get("/saved", response_model=list[SavedFragranceResponse])
async def get_saved_fragrances(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[SavedFragranceResponse]:
    """Get user's saved fragrance collection.

    Args:
        user_id: Current authenticated user
        session: Database session

    Returns:
        List of saved fragrances
    """
    stmt = select(SavedFragrance).where(SavedFragrance.user_id == user_id)
    result = await session.execute(stmt)
    saved = result.scalars().all()

    return [SavedFragranceResponse.model_validate(s) for s in saved]


@router.post("/saved", response_model=SavedFragranceResponse, status_code=status.HTTP_201_CREATED)
async def add_saved_fragrance(
    fragrances: SavedFragranceCreate,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> SavedFragranceResponse:
    """Add fragrance to user's collection.

    Args:
        fragrances: SavedFragranceCreate with fragrance ID and optional notes
        user_id: Current authenticated user
        session: Database session

    Returns:
        Created saved fragrance entry
    """
    # Check if already saved
    stmt = select(SavedFragrance).where(
        SavedFragrance.user_id == user_id,
        SavedFragrance.fragrance_neo4j_id == fragrances.fragrance_neo4j_id,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fragrance already in collection",
        )

    # Create new saved entry
    saved = SavedFragrance(
        user_id=user_id,
        fragrance_neo4j_id=fragrances.fragrance_neo4j_id,
        notes=fragrances.notes,
    )
    session.add(saved)
    await session.commit()
    logger.info(f"Added fragrance to collection for user {user_id}")

    return SavedFragranceResponse.model_validate(saved)


@router.delete("/saved/{saved_id}", response_model=dict)
async def remove_saved_fragrance(
    saved_id: int,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Remove fragrance from user's collection.

    Args:
        saved_id: Saved fragrance record ID
        user_id: Current authenticated user
        session: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if saved fragrance not found or not owned by user
    """
    stmt = select(SavedFragrance).where(
        SavedFragrance.id == saved_id,
        SavedFragrance.user_id == user_id,
    )
    result = await session.execute(stmt)
    saved = result.scalar_one_or_none()

    if not saved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved fragrance not found",
        )

    await session.delete(saved)
    await session.commit()
    logger.info(f"Removed fragrance from collection for user {user_id}")

    return {"status": "deleted"}


@router.post("/delete", response_model=dict)
async def request_data_deletion(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Request GDPR data deletion (right to be forgotten).

    Marks user account for deletion. All personal data will be deleted
    within 30 days. User cannot log in after this request.

    Args:
        user_id: Current authenticated user
        session: Database session

    Returns:
        Deletion request confirmation
    """
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Mark for deletion
    user.is_active = False
    user.gdpr_deletion_requested_at = _utc_now_naive()
    await session.commit()

    logger.info(f"Data deletion requested for user {user_id}")

    return {
        "status": "deletion_requested",
        "message": "Your data deletion request has been submitted. All personal data will be deleted within 30 days.",
    }
