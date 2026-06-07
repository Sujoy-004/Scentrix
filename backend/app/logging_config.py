"""Correlation ID context and structured logging helper."""

import contextvars
import logging
import uuid

correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


def generate_correlation_id() -> str:
    return uuid.uuid4().hex[:12]


def get_correlation_id() -> str:
    return correlation_id_var.get()


def set_correlation_id(cid: str | None = None) -> str:
    cid = cid or generate_correlation_id()
    correlation_id_var.set(cid)
    return cid


class CorrelationIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.correlation_id = get_correlation_id() or "-"
        except Exception:
            record.correlation_id = "-"
        return True
