"""FastAPI application entry point for Scentrix (minimal, fully-ownable).

Mounts only the surviving routers (catalog, quiz, recommendations, users)
plus system endpoints. No Sentry, no rate limiting, no correlation-ID
middleware, no async catalog loading, no gs warmup task. No JWT configuration
is required: authentication was removed from the product flow (no login).
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, ensure_schema
from app.routers import catalog, quiz, recommendations, users
from app.services.embeddings import gs_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the database schema and initialise the GraphSAGE embedding cache."""
    logger.info("Initializing Scentrix API...")

    if ensure_schema():
        logger.info("Database initialized: %s", settings.database_url)
    else:
        # The catalog and the recommender are file-backed and still work.
        logger.warning(
            "Database unavailable at startup - catalog and recommendations "
            "still work, but quiz sessions need the database."
        )

    if gs_service.initialize():
        logger.info("GraphSAGE: embedding cache ready.")
    else:
        logger.warning(
            "GraphSAGE: embedding cache unavailable - popularity fallback active."
        )

    logger.info("Scentrix API started successfully")
    yield


app = FastAPI(
    title="Scentrix API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog.router)
app.include_router(quiz.router)
app.include_router(recommendations.router)
app.include_router(users.router)


@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    data = {
        "status": "ok",
        "database": engine.dialect.name,
        "database_ready": ensure_schema(),
    }
    data["gs_embeddings"] = {"initialized": gs_service.initialized}
    return {"status": "success", "data": data}


@app.get("/", tags=["system"])
async def root():
    """Root endpoint with API info."""
    return {
        "status": "success",
        "data": {
            "name": "Scentrix API",
            "version": "0.1.0",
            "status": "running",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)