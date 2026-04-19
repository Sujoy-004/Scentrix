"""T2.3: Authentication API endpoints.

Provides user registration, login, token refresh, and logout functionality.
"""

import hashlib
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.auth.dependencies import get_current_user_id
from app.auth.encryption import vault
from app.database import get_session
from app.limiter import limiter
from app.models.models import RefreshToken, User
from app.schemas.schemas import (
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserProfile,
    UserRegister,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _utc_now_naive() -> datetime:
    # DB columns are TIMESTAMP WITHOUT TIME ZONE.
    return datetime.utcnow()


def _hash_email(email: str) -> str:
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


@limiter.limit("5/minute")
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    user_data: UserRegister,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Register a new user account."""
    email_hash = _hash_email(user_data.email)

    # Check if user already exists
    stmt = select(User).where(User.email_hash == email_hash)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        logger.warning(f"Registration failed: email already exists: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user
    hashed_password = hash_password(user_data.password)
    normalized_email = user_data.email.lower().strip()
    new_user = User(
        email_hash=email_hash,
        encrypted_email=vault.encrypt(normalized_email),
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        is_active=True,
        opt_in_training=user_data.opt_in_training,
    )

    session.add(new_user)
    await session.flush()  # Get the ID before commit
    user_id = new_user.id

    # Create refresh token in database
    refresh_token = create_refresh_token(user_id)
    refresh_token_obj = RefreshToken(
        user_id=user_id,
        token=refresh_token,
        expires_at=_utc_now_naive() + timedelta(days=7),
    )
    session.add(refresh_token_obj)

    await session.commit()
    logger.info(f"User registered: {user_data.email} (ID: {user_id})")

    # Generate tokens
    access_token = create_access_token(user_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 30 * 60,
    }


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: UserLogin,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Login with email and password."""
    email_hash = _hash_email(credentials.email)

    # Find user by email_hash
    stmt = select(User).where(User.email_hash == email_hash)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        logger.warning(f"Login failed: invalid credentials for {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        logger.warning(f"Login failed: inactive user {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Create tokens
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # Store refresh token in database
    refresh_token_obj = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=_utc_now_naive() + timedelta(days=7),
    )
    session.add(refresh_token_obj)
    await session.commit()

    logger.info(f"User logged in: {credentials.email} (ID: {user.id})")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 30 * 60,
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Refresh access token using a valid refresh token."""
    # Verify refresh token exists and is not revoked
    stmt = select(RefreshToken).where(
        RefreshToken.token == request.refresh_token,
        RefreshToken.revoked_at.is_(None),
        RefreshToken.expires_at > _utc_now_naive(),
    )
    result = await session.execute(stmt)
    token_obj = result.scalar_one_or_none()

    if not token_obj:
        logger.warning("Refresh failed: invalid or expired refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Create new access token (same user, same refresh token)
    user_id = token_obj.user_id
    access_token = create_access_token(user_id)

    logger.info(f"Token refreshed for user: {user_id}")

    return {
        "access_token": access_token,
        "refresh_token": request.refresh_token,
        "token_type": "bearer",
        "expires_in": 30 * 60,
    }


@router.post("/logout", response_model=dict)
async def logout(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Logout by revoking all refresh tokens for this user."""
    # Revoke all active refresh tokens for this user
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    )
    result = await session.execute(stmt)
    tokens = result.scalars().all()

    for token in tokens:
        token.revoked_at = _utc_now_naive()

    await session.commit()
    logger.info(f"User logged out: {user_id}")

    return {"status": "logged_out", "message": "All sessions revoked"}


@router.get("/me", response_model=UserProfile)
async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> UserProfile:
    """Get current authenticated user's profile."""
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
