"""Supabase auth integration helpers."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import vault
from app.config import settings
from app.models.models import User

logger = logging.getLogger(__name__)


class SupabaseAuthError(RuntimeError):
    """Raised when the Supabase auth API rejects a request."""


def is_supabase_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_anon_key and settings.supabase_jwt_secret)


def is_supabase_registration_enabled() -> bool:
    return bool(is_supabase_configured() and settings.supabase_service_role_key)


def _base_url() -> str:
    if not settings.supabase_url:
        raise SupabaseAuthError("Supabase is not configured")
    return settings.supabase_url.rstrip("/")


def _build_headers(*, api_key: str, bearer_token: str | None = None) -> dict[str, str]:
    token = bearer_token or api_key
    return {
        "apikey": api_key,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def _request_json(
    method: str,
    path: str,
    *,
    json_payload: dict[str, Any] | None = None,
    headers: dict[str, str],
) -> dict[str, Any]:
    url = f"{_base_url()}/auth/v1/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.request(method, url, json=json_payload, headers=headers)

    if response.status_code >= 400:
        detail: Any = response.text
        try:
            body = response.json()
            detail = (
                body.get("msg")
                or body.get("error_description")
                or body.get("message")
                or body
            )
        except ValueError:
            pass

        raise SupabaseAuthError(str(detail))

    if not response.content:
        return {}

    data = response.json()
    return data if isinstance(data, dict) else {"data": data}


def decode_supabase_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a Supabase JWT access token."""

    if not settings.supabase_jwt_secret:
        return None

    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError:
        return None


def extract_supabase_user_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize the user shape returned by Supabase endpoints."""

    user_payload = payload.get("user")
    if isinstance(user_payload, dict):
        return user_payload

    if isinstance(payload.get("data"), dict):
        return payload["data"]

    return payload


def _hash_email(email: str) -> str:
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


def _extract_email(payload: dict[str, Any]) -> str | None:
    email = payload.get("email")
    if isinstance(email, str) and email.strip():
        return email.lower().strip()

    metadata = payload.get("user_metadata")
    if isinstance(metadata, dict):
        meta_email = metadata.get("email")
        if isinstance(meta_email, str) and meta_email.strip():
            return meta_email.lower().strip()

    return None


def _extract_full_name(payload: dict[str, Any]) -> str | None:
    metadata = payload.get("user_metadata")
    if isinstance(metadata, dict):
        for key in ("full_name", "name"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    for key in ("full_name", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _extract_opt_in_training(payload: dict[str, Any]) -> bool | None:
    metadata = payload.get("user_metadata")
    if not isinstance(metadata, dict):
        return None

    value = metadata.get("opt_in_training")
    if value is None:
        return None

    return bool(value)


async def sync_local_user_from_supabase(
    session: AsyncSession,
    payload: dict[str, Any],
    *,
    default_password_hash: str | None = None,
) -> User:
    """Create or update the local user record from a Supabase auth payload."""

    email = _extract_email(payload)
    if not email:
        raise SupabaseAuthError("Supabase user payload is missing an email address")

    supabase_user_id = str(payload.get("id") or payload.get("sub") or "").strip() or None
    full_name = _extract_full_name(payload)
    opt_in_training = _extract_opt_in_training(payload)
    email_hash = _hash_email(email)

    user: User | None = None
    if supabase_user_id:
        stmt = select(User).where(User.supabase_user_id == supabase_user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

    if user is None:
        stmt = select(User).where(User.email_hash == email_hash)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

    if user is None:
        user = User(
            supabase_user_id=supabase_user_id,
            auth_provider="supabase" if supabase_user_id else "local",
            full_name=full_name,
            encrypted_email=vault.encrypt(email),
            email_hash=email_hash,
            hashed_password=default_password_hash,
            is_active=True,
            opt_in_training=opt_in_training if opt_in_training is not None else False,
        )
        session.add(user)
        await session.flush()
        await session.commit()
        return user

    changed = False
    if supabase_user_id and user.supabase_user_id != supabase_user_id:
        user.supabase_user_id = supabase_user_id
        changed = True

    if user.auth_provider != "supabase":
        user.auth_provider = "supabase"
        changed = True

    if full_name and user.full_name != full_name:
        user.full_name = full_name
        changed = True

    if user.email_hash != email_hash:
        user.email_hash = email_hash
        user.encrypted_email = vault.encrypt(email)
        changed = True

    if opt_in_training is not None and user.opt_in_training != opt_in_training:
        user.opt_in_training = opt_in_training
        changed = True

    if default_password_hash is not None and user.hashed_password is None:
        user.hashed_password = default_password_hash
        changed = True

    if changed:
        await session.commit()

    return user


async def create_supabase_user(
    email: str,
    password: str,
    *,
    full_name: str | None = None,
    opt_in_training: bool = False,
) -> dict[str, Any]:
    if not is_supabase_registration_enabled():
        raise SupabaseAuthError("Supabase registration is not configured")

    response = await _request_json(
        "POST",
        "admin/users",
        json_payload={
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": full_name,
                "opt_in_training": opt_in_training,
            },
        },
        headers=_build_headers(api_key=settings.supabase_service_role_key or ""),
    )
    return response


async def sign_in_supabase_user(email: str, password: str) -> dict[str, Any]:
    if not is_supabase_configured():
        raise SupabaseAuthError("Supabase auth is not configured")

    return await _request_json(
        "POST",
        "token?grant_type=password",
        json_payload={"email": email, "password": password},
        headers=_build_headers(api_key=settings.supabase_anon_key or ""),
    )


async def refresh_supabase_session(refresh_token: str) -> dict[str, Any]:
    if not is_supabase_configured():
        raise SupabaseAuthError("Supabase auth is not configured")

    return await _request_json(
        "POST",
        "token?grant_type=refresh_token",
        json_payload={"refresh_token": refresh_token},
        headers=_build_headers(api_key=settings.supabase_anon_key or ""),
    )


async def sign_out_supabase_user(access_token: str) -> None:
    if not is_supabase_configured():
        return

    await _request_json(
        "POST",
        "logout",
        json_payload={},
        headers=_build_headers(api_key=settings.supabase_anon_key or "", bearer_token=access_token),
    )