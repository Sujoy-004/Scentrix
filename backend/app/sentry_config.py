"""Sentry integration for error tracking and monitoring."""

from __future__ import annotations

from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.types import Event, Hint

from app.config import settings


def init_sentry() -> None:
    """Initialize Sentry error tracking if DSN is configured."""
    if not settings.sentry_dsn:
        return

    dsn = str(settings.sentry_dsn).strip()
    # Ignore common template placeholders used in local/dev .env files.
    if "your_sentry_key" in dsn or "project_id" in dsn:
        return

    integrations: list[Any] = [FastApiIntegration()]

    try:
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    except ImportError:
        pass
    else:
        integrations.append(SqlalchemyIntegration())

    try:
        from sentry_sdk.integrations.redis import RedisIntegration
    except ImportError:
        pass
    else:
        integrations.append(RedisIntegration())

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=0.1,
        integrations=integrations,
        # Performance Monitoring
        enable_tracing=True,
        # Release tracking
        release=None,  # Set to version tag in production
        # Performance
        max_breadcrumbs=50,
        attach_stacktrace=True,
        # GDPR/Privacy
        send_default_pii=False,  # Don't send PII unless explicitly enabled
        before_send=before_send_filter,
    )


def before_send_filter(event: Event, hint: Hint) -> Event | None:
    """Filter sensitive data before sending to Sentry."""
    request = event.get("request")
    if isinstance(request, dict):
        headers = request.get("headers")
        if isinstance(headers, dict):
            sensitive_keys = ["authorization", "x-api-key", "password"]
            for key in sensitive_keys:
                if key in headers:
                    headers[key] = "[REDACTED]"

        url = request.get("url")
        if isinstance(url, str):
            sensitive_params = ["password", "token", "secret", "api_key"]
            for param in sensitive_params:
                url = url.replace(f"{param}=", f"{param}=[REDACTED]&")
            request["url"] = url

    return event
