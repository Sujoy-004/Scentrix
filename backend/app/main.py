"""FastAPI application entry point for Scentrix backend."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import close_db, init_db
from app.limiter import limiter
from app.routers import auth, fragrances, quiz, recommendations, users
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
    await init_db()

    # Universal Warm-up (Hydrating Discovery Brain & Knowledge Graph)
    try:
        import asyncio

        from app.routers.recommendations import warmup_neural_engine
        from app.services.catalog import load_recommendation_catalog_async

        logger.info("Universal Boiler: Waking up Neural & Catalog Engines...")
        asyncio.create_task(asyncio.to_thread(warmup_neural_engine))
        asyncio.create_task(load_recommendation_catalog_async())
        logger.info("Universal Boiler: Background hydration dispatched.")

    except Exception as e:
        logger.error(f"Universal Boiler: Startup Warm-up failed: {str(e)}")

    logger.info(f"Database initialized: {settings.database_url}")
    logger.info("Scentrix API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down ScentScape API...")
    await close_db()
    logger.info("Database connection closed")


# Initialize FastAPI app
app = FastAPI(
    title="Scentrix API",
    description="AI-Driven Fragrance Discovery & Personalization",
    version="0.1.0",
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

# Include routers
app.include_router(auth.router)
app.include_router(fragrances.router)
app.include_router(users.router)
app.include_router(recommendations.router)
app.include_router(quiz.router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "ok"}


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    """Root endpoint with API info."""
    return {
        "name": "ScentScape API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/version", tags=["system"])
async def version() -> dict[str, str]:
    """Return API version."""
    return {"version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
