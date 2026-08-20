"""User management endpoints (profile + preferences only).

No wishlist/saved, no perceptual ratings, no delete, no interaction events.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_id
from app.database import get_db
from app.models.models import FragranceRating, User
from app.schemas.schemas import StandardResponse, UserPreferencesUpdate, UserProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


def _rating_count(db: Session, user_id: int) -> int:
    result = db.execute(
        select(func.count(FragranceRating.id)).where(FragranceRating.user_id == user_id)
    )
    return int(result.scalar_one() or 0)


def _build_profile(user: User, quiz_count: int) -> UserProfile:
    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        opt_in_training=False,
        preferences=user.preferences_json or {},
        quiz_count=quiz_count,
        wishlist_count=0,
        recommendation_count=quiz_count,
    )


@router.get("/profile", response_model=StandardResponse)
def get_user_profile(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> StandardResponse:
    """Get the current authenticated user's profile."""
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"status": "success", "data": _build_profile(user, _rating_count(db, user_id))}


@router.post("/preferences", response_model=StandardResponse)
def update_user_preferences(
    preferences: UserPreferencesUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> StandardResponse:
    """Merge stored fragrance preferences for the current user."""
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current = dict(user.preferences_json or {})
    current.update(preferences.model_dump(exclude_none=True))
    user.preferences_json = current
    db.commit()
    db.refresh(user)

    return {"status": "success", "data": _build_profile(user, _rating_count(db, user_id))}