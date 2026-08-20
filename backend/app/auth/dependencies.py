"""Authentication dependencies for FastAPI.

Provides dependency injections for local JWT-based user authentication.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.auth import verify_token

security = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
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

    token_payload = verify_token(credentials.credentials)
    if not token_payload or token_payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return int(token_payload.sub)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> int | None:
    """Dependency: Optionally extract user ID from Bearer token.

    Returns None when no token is provided or the token is invalid/expired.
    """
    if not credentials:
        return None

    try:
        return get_current_user_id(credentials)
    except HTTPException:
        # Ignore invalid/expired tokens for optional auth
        return None