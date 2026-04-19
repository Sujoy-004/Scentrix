"""Authentication dependencies for FastAPI.

Provides dependency injections for user authentication and authorization.
"""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import get_user_id_from_token, verify_token
from app.database import get_session
from app.services.supabase_auth import (
    SupabaseAuthError,
    decode_supabase_access_token,
    is_supabase_configured,
    sync_local_user_from_supabase,
)

security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> int:
    """Dependency: Extract and verify user ID from Bearer token.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        User ID from token

    Raises:
        HTTPException: 401 Unauthorized if token is invalid or expired
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    if is_supabase_configured():
        supabase_payload = decode_supabase_access_token(token)
        if not supabase_payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            user = await sync_local_user_from_supabase(session, supabase_payload)
            return user.id
        except SupabaseAuthError as exc:
            logger.warning("Supabase token sync failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    # Legacy fallback for local/test environments only.
    token_payload = verify_token(token)
    if not token_payload or token_payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> int | None:
    """Dependency: Optionally extract user ID from Bearer token."""
    if not credentials:
        return None

    try:
        return await get_current_user_id(credentials, session)
    except HTTPException:
        # Ignore invalid/expired tokens for optional auth
        return None
