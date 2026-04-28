"""Database configuration and session management.

Provides async SQLAlchemy engine and session management for FastAPI.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.models import Base

DB_AVAILABLE = False
engine = None
async_session_maker = None

try:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        pool_size=20,
        max_overflow=10,
    )
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    DB_AVAILABLE = True
except Exception:
    import logging
    logging.getLogger(__name__).error("DATABASE_OFFLINE: Failed to create engine. Falling back to Stateless Mode.")

from fastapi import HTTPException, status

async def get_session() -> AsyncGenerator[AsyncSession | None, None]:
    """Dependency: Get an async database session.
    Yields None if database is unavailable, allowing routers to implement fallbacks.
    """
    if not DB_AVAILABLE or async_session_maker is None:
        yield None
        return

    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
async def init_db():
    """Initialize database schema (create tables)."""
    if not DB_AVAILABLE or engine is None:
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connection pool."""
    if engine:
        await engine.dispose()
