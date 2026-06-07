"""Correlation ID middleware for request tracing."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.logging_config import generate_correlation_id, set_correlation_id


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cid = request.headers.get("X-Correlation-ID") or generate_correlation_id()
        set_correlation_id(cid)
        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response
