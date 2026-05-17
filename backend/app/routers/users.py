"""T2.5: User management endpoints.

Provides endpoints for:
- Get user profile
- Submit fragrance ratings
- Manage saved fragrance collections
- GDPR data deletion request
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_id
from app.auth.encryption import vault
from app.database import get_session
from app.models.models import FragranceRating, SavedFragrance, User, UserInteractionEvent
from app.schemas.schemas import (
    FragranceRatingCreate,
    FragranceRatingResponse,
    SavedFragranceCreate,
    SavedFragranceResponse,
    StandardResponse,
    UserPreferencesUpdate,
    UserProfile,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


def _utc_now_naive() -> datetime:
    # DB columns are TIMESTAMP WITHOUT TIME ZONE.
    return datetime.now(UTC).replace(tzinfo=None)


async def _build_user_profile(session: AsyncSession, user: User) -> UserProfile:
    quiz_count_result = await session.execute(
        select(func.count(FragranceRating.id)).where(FragranceRating.user_id == user.id)
    )
    wishlist_count_result = await session.execute(
        select(func.count(SavedFragrance.id)).where(SavedFragrance.user_id == user.id)
    )
    recommendation_count_result = await session.execute(
        select(func.count(UserInteractionEvent.id)).where(UserInteractionEvent.user_id == user.id)
    )

    preferences = user.preferences_json or {}

    # Safely decrypt PII
    try:
        email = vault.decrypt(user.encrypted_email)
    except ValueError:
        logger.error(f"DECRYPTION_FAILURE: Failed to decrypt email for user {user.id}")
        email = None

    try:
        full_name = vault.decrypt(user.encrypted_full_name) if user.encrypted_full_name else None
    except ValueError:
        logger.error(f"DECRYPTION_FAILURE: Failed to decrypt full_name for user {user.id}")
        full_name = None

    return UserProfile(
        id=user.id,
        email=email or "Unknown",
        full_name=full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        opt_in_training=user.opt_in_training,
        preferences=preferences,
        quiz_count=int(quiz_count_result.scalar_one() or 0),
        wishlist_count=int(wishlist_count_result.scalar_one() or 0),
        recommendation_count=int(recommendation_count_result.scalar_one() or 0),
    )


@router.get("/profile", response_model=StandardResponse)
async def get_user_profile(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Get current user's profile.

    Args:
        user_id: Current authenticated user
        session: Database session

    Returns:
        User profile data

    Raises:
        HTTPException: 404 if user not found
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="User database is offline."
        )
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    profile = await _build_user_profile(session, user)
    return {"status": "success", "data": profile}


@router.post("/preferences", response_model=StandardResponse)
async def update_user_preferences(
    preferences: UserPreferencesUpdate,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Update stored fragrance preferences for the current user."""

    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="User database is offline."
        )
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    current_preferences = dict(user.preferences_json or {})
    current_preferences.update(preferences.model_dump(exclude_none=True))
    user.preferences_json = current_preferences

    await session.commit()
    await session.refresh(user)

    profile = await _build_user_profile(session, user)
    return {"status": "success", "data": profile}


@router.post("/ratings", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def submit_fragrance_rating(
    rating: FragranceRatingCreate,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Submit or update a fragrance rating.

    If user already rated this fragrance, the rating is updated.

    Args:
        rating: FragranceRatingCreate with dimensions and overall satisfaction
        user_id: Current authenticated user
        session: Database session

    Returns:
        Created or updated fragrance rating
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Rating database is offline."
        )
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
        data = FragranceRatingResponse.model_validate(existing_rating)
        return {"status": "success", "data": data}
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
        data = FragranceRatingResponse.model_validate(new_rating)
        return {"status": "success", "data": data}


@router.get("/ratings", response_model=StandardResponse)
async def get_user_ratings(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Get all of user's fragrance ratings.

    Args:
        user_id: Current authenticated user
        session: Database session

    Returns:
        List of user's fragrance ratings
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Rating database is offline."
        )
    stmt = select(FragranceRating).where(FragranceRating.user_id == user_id)
    result = await session.execute(stmt)
    ratings = result.scalars().all()

    data = [FragranceRatingResponse.model_validate(r) for r in ratings]
    return {"status": "success", "data": data}


@router.get("/saved", response_model=StandardResponse)
async def get_saved_fragrances(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Get user's saved fragrance collection.

    Args:
        user_id: Current authenticated user
        session: Database session

    Returns:
        List of saved fragrances
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Collection database is offline.",
        )
    stmt = select(SavedFragrance).where(SavedFragrance.user_id == user_id)
    result = await session.execute(stmt)
    saved = result.scalars().all()

    data = [SavedFragranceResponse.model_validate(s) for s in saved]
    return {"status": "success", "data": data}


@router.post("/saved", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def add_saved_fragrance(
    fragrances: SavedFragranceCreate,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Add fragrance to user's collection.

    Args:
        fragrances: SavedFragranceCreate with fragrance ID and optional notes
        user_id: Current authenticated user
        session: Database session

    Returns:
        Created saved fragrance entry
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Collection database is offline.",
        )
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

    data = SavedFragranceResponse.model_validate(saved)
    return {"status": "success", "data": data}


@router.delete("/saved/{saved_id}", response_model=StandardResponse)
async def remove_saved_fragrance(
    saved_id: int,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Remove fragrance from user's collection."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Collection database is offline.",
        )
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

    return {"status": "success", "data": {"message": "Saved fragrance removed"}}


@router.post("/delete", response_model=StandardResponse)
async def request_data_deletion(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Request GDPR data deletion (right to be forgotten).

    Marks user account for deletion. All personal data will be deleted
    within 30 days. User cannot log in after this request.

    Args:
        user_id: Current authenticated user
        session: Database session

    Returns:
        Deletion request confirmation
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="User database is offline."
        )
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
        "status": "success",
        "data": {
            "message": "Your data deletion request has been submitted. All personal data will be deleted within 30 days."
        },
    }


class UpdateNotesRequest(BaseModel):
    notes: str


@router.patch("/saved/{saved_id}/notes", response_model=StandardResponse)
async def update_saved_fragrance_notes(
    saved_id: int,
    request: UpdateNotesRequest,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Update personal notes for a saved fragrance."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Collection database is offline.",
        )
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

    saved.notes = request.notes
    await session.commit()
    await session.refresh(saved)

    data = SavedFragranceResponse.model_validate(saved)
    return {"status": "success", "data": data}
