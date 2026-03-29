"""Authentication dependencies for FastAPI.

Provides dependency injections for user authentication and authorization.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.auth import get_user_id_from_token, verify_token


security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
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
    
    # Verify token
    token_payload = verify_token(token)
    if not token_payload or token_payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user ID
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


async def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[int]:
    """Dependency: Optionally extract user ID from Bearer token.
    
    Returns None if no token provided. Raises 401 if token invalid.
    
    Args:
        credentials: Optional HTTP Bearer token
        
    Returns:
        User ID or None if no token provided
        
    Raises:
        HTTPException: 401 if token is invalid (but provided)
    """
    if not credentials:
        return None
    
    return await get_current_user_id(credentials)
