"""Database configuration and session management.

Provides a sync SQLAlchemy engine and session factory for FastAPI.

The engine is tuned for a serverless/free-tier deployment: connections are
pre-pinged before use (a pooled Postgres can drop an idle connection at any
time, and a serverless instance can be frozen between requests) and recycled
before the provider's idle timeout.
"""

import logging
import time

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

_is_sqlite = settings.database_url.startswith("sqlite")

connect_args: dict = {}
if _is_sqlite:
    connect_args["check_same_thread"] = False
elif settings.database_url.startswith("postgresql"):
    # Fail fast instead of hanging when the database is unreachable.
    connect_args["connect_timeout"] = 10

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    # Replace a connection that the server closed while it was idle.
    pool_pre_ping=True,
    # Recycle before a managed Postgres drops an idle connection.
    pool_recycle=300,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()

# Set once the schema is known to exist. Retried lazily if the database was
# unreachable at startup.
_schema_ready = False
_schema_retry_after = 0.0
_SCHEMA_RETRY_COOLDOWN = 10.0


def get_db():
    """FastAPI dependency: yield a database session."""
    ensure_schema()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> bool:
    """Create all tables. Returns False if the database is unreachable.

    The API does not fail to boot when the database is down: the catalog and
    the recommendation engine are file-backed and keep working, and the quiz
    endpoints report the problem themselves.
    """
    try:
        Base.metadata.create_all(engine)
    except SQLAlchemyError as exc:
        logger.error("Database schema init failed: %s", exc)
        return False
    return True


def ensure_schema() -> bool:
    """Make sure the tables exist, retrying at most every few seconds.

    A managed Postgres that scales to zero can refuse the first connection
    while it resumes. Rather than crash the app, the schema is re-checked on
    the next request that needs it.
    """
    global _schema_ready, _schema_retry_after

    if _schema_ready:
        return True

    now = time.monotonic()
    if now < _schema_retry_after:
        return False

    _schema_ready = init_db()
    if not _schema_ready:
        _schema_retry_after = now + _SCHEMA_RETRY_COOLDOWN
    return _schema_ready
