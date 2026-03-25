"""FastAPI application entry point for ScentScape backend."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, close_db
from app.routers import auth, fragrances, users
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
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Initializing ScentScape API...")
    await init_db()
    logger.info(f"Database initialized: {settings.database_url}")
    logger.info("ScentScape API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ScentScape API...")
    await close_db()
    logger.info("Database connection closed")


# Initialize FastAPI app
app = FastAPI(
    title="ScentScape API",
    description="AI-Driven Fragrance Discovery & Personalization",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(fragrances.router)
app.include_router(users.router)


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
