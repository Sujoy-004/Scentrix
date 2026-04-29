import logging
import os
import psutil
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_id, get_optional_user_id
from app.cache import cache
from app.database import get_session
from app.models.models import FragranceRating as DBFragranceRating
from app.services.catalog import load_recommendation_catalog
from app.services.hybrid_search import _catalog_embeddings_cache, _is_hydrating, recommender
from app.schemas.schemas import (
    FragranceRecommendation,
    GuestRecommendationRequest,
    StandardResponse,
    RecommendationResult,
    RecommendationJob,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)

# State and Warmup logic moved to app.services.hybrid_search

def log_mem(stage):
    m = psutil.Process(os.getpid()).memory_info().rss / (1024 ** 2)
    print(f"[MEM] {stage}: {m:.2f} MB")


def get_encoder():
    """Neural Engine: Access the ML Encoder via the global recommender service."""
    return recommender._get_encoder()


def _get_item_text(item: dict[str, Any]) -> str:
    """Proxy for the recommender service text extractor."""
    return recommender._get_item_text(item)


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class FragranceRecommendation(BaseModel):
    id: str
    name: str
    brand: str
    match_score: float
    reason: str
    mock: bool = False


class FragranceRatingInput(BaseModel):
    """A single fragrance rating from the quiz."""

    fragrance_id: str  # ID as sent by the frontend (may have frag_ prefix)
    rating: float  # 1-10 quiz rating
    top_notes: list[str] | None = None
    accords: list[str] | None = None
    description: str | None = None
    name: str | None = None
    brand: str | None = None


class BatchRatingRequest(BaseModel):
    ratings: list[FragranceRatingInput]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _normalize_id(raw_id: str) -> str:
    """Strip common prefix variants so IDs match the catalog."""
    return raw_id.replace("frag_syn_", "").replace("frag_", "")


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    return sum(a * b for a, b in zip(v1, v2, strict=False))


def warmup_neural_engine():
    """Proxy for the recommender service warmup."""
    return recommender.warmup()


# ── Score engine ──────────────────────────────────────────────────────────────


# Scoring moved to HybridRecommender


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/rate", status_code=200)
async def submit_fragrance_rating(
    request: FragranceRatingInput,
    user_id: int | None = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """
    Persist a quiz rating for authenticated users.
    For guests this is a silent 200 no-op — ratings live in localStorage.
    """
    if not user_id:
        return {"status": "success", "data": {"status": "guest_local"}}

    if not db:
        logger.warning(f"Rating persist skipped for user {user_id}: DB_OFFLINE")
        return {"status": "success", "data": {"status": "guest_local_fallback"}}

    try:
        # Use fragrance_neo4j_id (the actual DB column name)
        neo4j_id = _normalize_id(request.fragrance_id)

        existing = await db.execute(
            select(DBFragranceRating).where(
                DBFragranceRating.user_id == user_id,
                DBFragranceRating.fragrance_neo4j_id == neo4j_id,
            )
        )
        row = existing.scalar_one_or_none()

        if row:
            row.quiz_rating = request.rating
        else:
            db.add(
                DBFragranceRating(
                    user_id=user_id,
                    fragrance_neo4j_id=neo4j_id,
                    quiz_rating=request.rating,
                )
            )

        await db.commit()

        # Invalidate recommendation cache
        await cache.delete(f"rec:user:{user_id}")

        return {"status": "success", "data": {"status": "saved"}}

    except Exception as e:
        logger.error(f"Rating persist error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save rating") from e


@router.post("/batch-rate", status_code=200)
async def submit_batch_ratings(
    request: BatchRatingRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """
    Persist multiple quiz ratings at once. Used during Guest -> User conversion.
    """
    try:
        count = 0
        for r in request.ratings:
            neo4j_id = _normalize_id(r.fragrance_id)
            # Fast update/upsert logic
            existing = await db.execute(
                select(DBFragranceRating).where(
                    DBFragranceRating.user_id == user_id,
                    DBFragranceRating.fragrance_neo4j_id == neo4j_id,
                )
            )
            row = existing.scalar_one_or_none()

            if row:
                row.quiz_rating = r.rating
            else:
                db.add(
                    DBFragranceRating(
                        user_id=user_id,
                        fragrance_neo4j_id=neo4j_id,
                        quiz_rating=r.rating,
                    )
                )
            count += 1

        await db.commit()

        # Invalidate recommendation cache
        await cache.delete(f"rec:user:{user_id}")

        return {"status": "success", "data": {"status": "saved", "count": count}}
    except Exception as e:
        logger.error(f"Batch rating persist error for user {user_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to sync batch ratings") from e


@router.post("/guest", response_model=StandardResponse)
async def get_guest_recommendations(
    request: GuestRecommendationRequest,
) -> StandardResponse:
    print("REQUEST RECEIVED")
    log_mem("START")
    if _catalog_embeddings_cache is None:
        logger.info("ML_LAZY_LOAD: Triggering first-time warmup for guest...")
        warmup_neural_engine()
        log_mem("AFTER_EMBEDDINGS")


    try:
        seed_ids = [_normalize_id(r.fragrance_id) for r in request.ratings]
        results = recommender.get_recommendations(request.ratings, seed_ids)
        data = [FragranceRecommendation(**r) for r in results]
        return {"status": "success", "data": data}

    except Exception as e:
        logger.error(f"Guest hybrid discovery failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Recommendation engine encountered a fault.",
        ) from e


@router.get("/personalized", response_model=StandardResponse)
async def get_personalized_recommendations(
    user_id: int | None = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_session),
) -> StandardResponse:
    log_mem("START")
    if not user_id:
        return {"status": "success", "data": []}

    cached_recs = await cache.get(f"rec:user:{user_id}")
    if cached_recs:
        data = [FragranceRecommendation(**r) for r in cached_recs]
        return {"status": "success", "data": data}

    if not db:
        logger.warning(f"Personalized discovery fallback to guest mode for user {user_id}")
        return {"status": "success", "data": []}

    stmt = select(DBFragranceRating).where(DBFragranceRating.user_id == user_id)
    result = await db.execute(stmt)
    saved_ratings = result.scalars().all()

    if not saved_ratings:
        return {"status": "success", "data": []}

    catalog = load_recommendation_catalog()
    if not catalog:
        return {"status": "success", "data": []}

    guest_ratings = [
        FragranceRatingInput(
            fragrance_id=r.fragrance_neo4j_id,
            rating=r.quiz_rating or 5.0,
        )
        for r in saved_ratings
    ]

    try:
        seed_ids = [_normalize_id(r.fragrance_id) for r in guest_ratings]
        results = recommender.get_recommendations(guest_ratings, seed_ids)
    except Exception as e:
        logger.error(f"Hybrid discovery hit a critical fault: {e}")
        raise HTTPException(
            status_code=500,
            detail="Recommendation engine encountered a fault.",
        ) from e

    if results:
        await cache.set(f"rec:user:{user_id}", results, expire=3600)

    data = [FragranceRecommendation(**r) for r in results]
    return {"status": "success", "data": data}


class SommelierInsightRequest(BaseModel):
    fragrances: list[FragranceRecommendation]


class SommelierInsightResponse(BaseModel):
    insight: str
    vibe_category: str
    sommelier_name: str = "Aethera"


@router.post("/sommelier/insight", response_model=StandardResponse)
async def get_sommelier_insight(
    request: SommelierInsightRequest,
) -> StandardResponse:
    """
    Generate an atmospheric, AI-powered insight for a collection of recommendations.
    """
    from app.services.sommelier import sommelier_service

    try:
        insight, category = await sommelier_service.generate_insight(request.fragrances)
        data = SommelierInsightResponse(insight=insight, vibe_category=category)
        return {"status": "success", "data": data}
    except Exception as e:
        logger.error(f"Sommelier Service failed: {e}")
        data = SommelierInsightResponse(
            insight="Your collection resonates with a unique, elusive frequency. There is a deep, structural harmony between your choices that suggests a preference for complex, narrative-driven olfactive profiles.",
            vibe_category="Aetheric Discovery",
        )
        return {"status": "success", "data": data}
