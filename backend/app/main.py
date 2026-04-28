"""FastAPI application entry point for Scentrix backend."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import close_db, engine, init_db
from app.limiter import limiter
from app.schemas.schemas import StandardResponse
from app.routers import auth, fragrances, leads, quiz, recommendations, users
from app.sentry_config import init_sentry

# Initialize Sentry for error tracking (if configured)
init_sentry()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Initializing Scentrix API...")

    # In production, we rely on Alembic migrations.
    # Only run init_db() if we are in debug mode and want auto-creation.
    if settings.debug:
        logger.info("Debug mode detected: Running init_db() for auto-schema creation...")
        await init_db()
    else:
        logger.info("Production mode: Skipping init_db(), relying on Alembic migrations.")

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("DB CONNECTION: SUCCESS")
    except Exception as e:
        logger.exception(f"DB CONNECTION: FAILED {str(e)}")

    # Universal Warm-up (Hydrating Discovery Brain & Knowledge Graph)
    try:
        import asyncio

        from app.routers.recommendations import warmup_neural_engine
        from app.services.catalog import load_recommendation_catalog_async

        logger.info("Universal Boiler: Waking up Neural & Catalog Engines...")
        # NO ML loading blocks startup - lazy loading enabled
        # asyncio.create_task(asyncio.to_thread(warmup_neural_engine))
        # asyncio.create_task(load_recommendation_catalog_async())
        logger.info("Universal Boiler: Background hydration deferred to first request.")

    except Exception as e:
        logger.error(f"Universal Boiler: Startup Warm-up failed: {str(e)}")

    logger.info(f"Database initialized: {settings.database_url}")
    logger.info("Scentrix API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Scentrix API...")
    await close_db()
    logger.info("Database connection closed")


# Initialize FastAPI app
app = FastAPI(
    title="Scentrix API",
    description="AI-Driven Fragrance Discovery & Personalization",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "data": None,
            "error": exc.detail
        }
    )


@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "data": None,
            "error": "Internal server error"
        }
    )

# Include routers
app.include_router(auth.router)
app.include_router(fragrances.router)
app.include_router(users.router)
app.include_router(recommendations.router)
app.include_router(quiz.router)
app.include_router(leads.router)


@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint for Render/monitoring."""
    return {"status": "ok"}


@app.get("/", tags=["system"])
async def root() -> StandardResponse:
    """Root endpoint with API info."""
    return {
        "status": "success",
        "data": {
            "name": "Scentrix API",
            "version": "0.1.0",
            "status": "running",
        },
    }


@app.get("/version", tags=["system"])
async def version() -> StandardResponse:
    """Return API version."""
    return {"status": "success", "data": {"version": "0.0.1"}}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
