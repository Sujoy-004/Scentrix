"""T2.3: Authentication API endpoints.

Provides user registration, login, token refresh, and logout functionality.
"""

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

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
    StandardResponse,
    UserLogin,
    UserProfile,
    UserRegister,
)
from app.services.supabase_auth import (
    SupabaseAuthError,
    create_supabase_user,
    extract_supabase_user_payload,
    is_supabase_configured,
    is_supabase_registration_enabled,
    refresh_supabase_session,
    sign_in_supabase_user,
    sync_local_user_from_supabase,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _utc_now_naive() -> datetime:
    # DB columns are TIMESTAMP WITHOUT TIME ZONE.
    return datetime.now(UTC).replace(tzinfo=None)


def _hash_email(email: str) -> str:
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


def _token_response(
    access_token: str,
    refresh_token: str,
    *,
    user_id: int | None = None,
    expires_in: int = 30 * 60,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }
    if user_id is not None:
        response["user_id"] = str(user_id)
    return response


@limiter.limit("5/minute")
@router.post("/register", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    user_data: UserRegister,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Register a new user account."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication database is offline.",
        )
    email_hash = _hash_email(user_data.email)

    # Check if user already exists
    stmt = select(User).where(User.email_hash == email_hash)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        logger.warning(f"Registration failed: email already exists: {email_hash}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    if is_supabase_registration_enabled():
        try:
            created_user = await create_supabase_user(
                user_data.email,
                user_data.password,
                full_name=user_data.full_name,
                opt_in_training=user_data.opt_in_training,
            )
            session_data = await sign_in_supabase_user(user_data.email, user_data.password)

            supabase_user = extract_supabase_user_payload(session_data)
            if not supabase_user:
                supabase_user = extract_supabase_user_payload(created_user)

            user = await sync_local_user_from_supabase(session, supabase_user)

            logger.info(
                "User registered via Supabase: %s (local ID: %s)",
                email_hash,
                user.id,
            )

            return {
                "status": "success",
                "data": _token_response(
                    session_data["access_token"],
                    session_data["refresh_token"],
                    user_id=user.id,
                    expires_in=int(session_data.get("expires_in", 30 * 60)),
                ),
            }
        except SupabaseAuthError as exc:
            logger.exception("Supabase registration failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Registration service unavailable",
            ) from exc

    # Create new user
    hashed_password = hash_password(user_data.password)
    normalized_email = user_data.email.lower().strip()
    new_user = User(
        auth_provider="local",
        email_hash=email_hash,
        encrypted_email=vault.encrypt(normalized_email),
        encrypted_full_name=vault.encrypt(user_data.full_name) if user_data.full_name else None,
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
    logger.info(f"User registered: {email_hash} (ID: {user_id})")

    # Generate tokens
    access_token = create_access_token(user_id)

    return {
        "status": "success",
        "data": _token_response(access_token, refresh_token, user_id=user_id),
    }


@router.post("/login", response_model=StandardResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: UserLogin,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Login with email and password."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication database is offline.",
        )
    email_hash = _hash_email(credentials.email)

    if is_supabase_configured():
        try:
            session_data = await sign_in_supabase_user(credentials.email, credentials.password)
            supabase_user = extract_supabase_user_payload(session_data)
            sb_user = await sync_local_user_from_supabase(session, supabase_user)

            logger.info("User logged in via Supabase: %s (local ID: %s)", email_hash, sb_user.id)

            return {
                "status": "success",
                "data": _token_response(
                    session_data["access_token"],
                    session_data["refresh_token"],
                    user_id=sb_user.id,
                    expires_in=int(session_data.get("expires_in", 30 * 60)),
                ),
            }
        except SupabaseAuthError as exc:
            logger.warning("Supabase login failed for %s: %s", email_hash, exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            ) from exc

    # Find user by email_hash
    stmt = select(User).where(User.email_hash == email_hash)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if (
        not user
        or not user.hashed_password
        or not verify_password(credentials.password, user.hashed_password)
    ):
        logger.warning(f"Login failed: invalid credentials for {email_hash}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        logger.warning(f"Login failed: inactive user {email_hash}")
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

    logger.info(f"User logged in: {email_hash} (ID: {user.id})")

    return {
        "status": "success",
        "data": _token_response(access_token, refresh_token, user_id=user.id),
    }


@router.post("/refresh", response_model=StandardResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Refresh access token using a valid refresh token."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication database is offline.",
        )

    if is_supabase_configured():
        try:
            session_data = await refresh_supabase_session(request.refresh_token)
            supabase_user = extract_supabase_user_payload(session_data)
            user = await sync_local_user_from_supabase(session, supabase_user)

            logger.info(
                "Supabase session refreshed for user: %s (local ID: %s)",
                supabase_user.get("id"),
                user.id,
            )

            return {
                "status": "success",
                "data": _token_response(
                    session_data["access_token"],
                    session_data.get("refresh_token", request.refresh_token),
                    user_id=user.id,
                    expires_in=int(session_data.get("expires_in", 30 * 60)),
                ),
            }
        except SupabaseAuthError as exc:
            logger.warning("Supabase refresh failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            ) from exc

    # Legacy local refresh path for non-Supabase environments.
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

    user_id = token_obj.user_id
    access_token = create_access_token(user_id)

    logger.info(f"Token refreshed for user: {user_id}")

    return {
        "status": "success",
        "data": _token_response(access_token, request.refresh_token, user_id=user_id),
    }


@router.post("/logout", response_model=StandardResponse)
async def logout(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Logout by revoking all refresh tokens for this user."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication database is offline.",
        )
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

    return {
        "status": "success",
        "data": {"message": "All sessions revoked"},
    }


@router.get("/me", response_model=StandardResponse)
async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Get current authenticated user's profile."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication database is offline.",
        )
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Safely decrypt PII for profile response
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

    profile = UserProfile(
        id=user.id,
        email=email or "Unknown",
        full_name=full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        opt_in_training=user.opt_in_training,
    )
    return {"status": "success", "data": profile}
