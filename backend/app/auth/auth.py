"""Legacy authentication utilities and JWT handling (retired product surface).

Login was intentionally removed from the product; this module survives only to
support legacy authed endpoints that the anonymous demo never calls. It must
NOT require any configuration at startup, so the legacy signing secret is read
lazily from the environment instead of pydantic settings. When no secret is
configured, presented tokens are treated as invalid (401) and the app still
starts fine without an env file.
"""

import os
from datetime import UTC, datetime, timedelta

from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15


def _legacy_secret_key() -> str | None:
    """Return the legacy JWT secret if one was configured, else None."""
    return os.getenv("JWT_SECRET_KEY")


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # subject (user_id)
    exp: datetime
    iat: datetime
    type: str  # "access"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.

    Args:
        user_id: User ID to encode in token
        expires_delta: Custom expiration time. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES

    Returns:
        Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    secret = _legacy_secret_key()
    if secret is None:
        raise RuntimeError("JWT_SECRET_KEY is not set; legacy auth is retired")

    now = datetime.now(UTC)
    expire = now + expires_delta

    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }

    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> TokenPayload | None:
    """Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenPayload if valid, None if invalid

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        secret = _legacy_secret_key()
        if secret is None:
            return None
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except JWTError:
        return None