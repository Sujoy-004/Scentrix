"""Sentry integration for error tracking and monitoring."""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

try:
    from sentry_sdk.integrations.sqlalchemy import SqlAlchemyIntegration
except ImportError:
    SqlAlchemyIntegration = None

try:
    from sentry_sdk.integrations.celery import CeleryIntegration
except ImportError:
    CeleryIntegration = None

try:
    from sentry_sdk.integrations.redis import RedisIntegration
except ImportError:
    RedisIntegration = None

from app.config import settings


def init_sentry() -> None:
    """Initialize Sentry error tracking if DSN is configured."""
    if not settings.sentry_dsn:
        return

    integrations = [FastApiIntegration()]
    
    if SqlAlchemyIntegration:
        integrations.append(SqlAlchemyIntegration())
    if CeleryIntegration:
        integrations.append(CeleryIntegration())
    if RedisIntegration:
        integrations.append(RedisIntegration())

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
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


def before_send_filter(event, hint):
    """Filter sensitive data before sending to Sentry."""
    # Remove authorization headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive_keys = ["authorization", "x-api-key", "password"]
        for key in sensitive_keys:
            if key in headers:
                headers[key] = "[REDACTED]"
    
    # Remove sensitive query parameters
    if "request" in event and "url" in event["request"]:
        url = event["request"]["url"]
        sensitive_params = ["password", "token", "secret", "api_key"]
        for param in sensitive_params:
            url = url.replace(f"{param}=", f"{param}=[REDACTED]&")
        event["request"]["url"] = url
    
    return event
