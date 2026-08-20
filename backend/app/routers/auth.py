"""Authentication API endpoints (local JWT only).

Provides user registration, login, and current-user profile.
No Supabase, no refresh tokens.
"""

import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.auth import create_access_token, hash_password, verify_password
from app.auth.dependencies import get_current_user_id
from app.database import get_db
from app.models.models import User
from app.schemas.schemas import StandardResponse, UserLogin, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])

MIN_PASSWORD_LENGTH = 8


def _hash_email(email: str) -> str:
    """Return the sha256 hex digest of a normalized (lowercased) email."""
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


def _user_payload(user: User) -> dict:
    """Serialize a User ORM object for API responses."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "preferences": user.preferences_json,
        "quiz_completed_at": user.quiz_completed_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def _auth_data(user: User, access_token: str) -> dict:
    """Build the standard success payload for login/register."""
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "user": _user_payload(user),
    }


@router.post("/register", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
) -> StandardResponse:
    """Register a new user account."""
    if len(user_data.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
        )

    email_hash = _hash_email(user_data.email)

    existing = db.execute(select(User).where(User.email_hash == email_hash)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    normalized_email = user_data.email.lower().strip()
    new_user = User(
        email=normalized_email,
        email_hash=email_hash,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role="user",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(new_user.id)
    return {"status": "success", "data": _auth_data(new_user, access_token)}


@router.post("/login", response_model=StandardResponse)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
) -> StandardResponse:
    """Login with email and password."""
    email_hash = _hash_email(credentials.email)

    user = db.execute(select(User).where(User.email_hash == email_hash)).scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(user.id)
    return {"status": "success", "data": _auth_data(user, access_token)}


@router.get("/me", response_model=StandardResponse)
def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> StandardResponse:
    """Get current authenticated user's profile."""
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {"status": "success", "data": {"user": _user_payload(user)}}