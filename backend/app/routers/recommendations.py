import logging
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
    StandardResponse,
    RecommendationResult,
    RecommendationJob,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)

# State and Warmup logic moved to app.services.hybrid_search


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


class GuestRecommendationRequest(BaseModel):
    ratings: list[FragranceRatingInput]


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


def _score_catalog(
    user_ratings: list[FragranceRatingInput],
    catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Generate recommendations from user quiz ratings.

    Strategy (in priority order):
    1. ML semantic embedding (if encoder available + catalog cached)
    2. Note/accord overlap heuristic (always available)
    3. Trending fallback (when no ratings match catalogue)
    """
    if _is_hydrating or _catalog_embeddings_cache is None:
        logger.error("ML_NOT_READY")
        raise HTTPException(
            status_code=503,
            detail="ML system is initializing. Please try again shortly."
        )

    encoder = get_encoder()
    catalog_by_norm_id = {_normalize_id(str(item.get("id", ""))): item for item in catalog}

    # -- Resolve user rated items against catalog --------------------------
    rated_items: list[dict[str, Any]] = []
    weights: list[float] = []
    liked_notes: set = set()
    liked_accords: set = set()

    for r in user_ratings:
        norm = _normalize_id(r.fragrance_id)
        item = catalog_by_norm_id.get(norm)
        if item:
            rated_items.append(item)
            weights.append(r.rating)
            liked_notes.update(item.get("top_notes", []) or [])
            liked_accords.update(item.get("accords", []) or [])
        else:
            # Use metadata supplied by the frontend
            liked_notes.update(r.top_notes or [])
            liked_accords.update(r.accords or [])

    seed_ids = {_normalize_id(r.fragrance_id) for r in user_ratings}

    logger.info(
        f"Score Catalog: Received {len(user_ratings)} ratings. Matched {len(rated_items)} items against catalog."
    )
    logger.info(
        f"Successfully resolved {len(rated_items)} items against catalog for scoring out of {len(user_ratings)} provided."
    )

    # -- ML path -----------------------------------------------------------
    if not _is_hydrating and _catalog_embeddings_cache is not None and rated_items:
        try:
            import numpy as np

            encoder = recommender._get_encoder()
            if encoder:
                user_texts = [recommender._get_item_text(item) for item in rated_items]
                user_embeddings = encoder.generate_embeddings(user_texts)

                # Center weights so <5.5 pushes vector AWAY from the target, >5.5 pulls TOWARD the target.
                shifted_weights = [w - 5.5 for w in weights]
                total_w = sum(abs(w) for w in shifted_weights) or 1.0

                dim = len(user_embeddings[0])
                user_vec = np.zeros(dim)
                for emb, w in zip(user_embeddings, shifted_weights, strict=False):
                    user_vec += np.array(emb) * (w / total_w)

                # Normalize user vector to ensure unit length
                user_v_norm = np.linalg.norm(user_vec)
                if user_v_norm > 0:
                    user_vec = user_vec / user_v_norm

                catalog_embs = np.array(_catalog_embeddings_cache)
                # Ensure catalog is normalized (it should be, but let's be safe)
                norms = np.linalg.norm(catalog_embs, axis=1, keepdims=True)
                catalog_embs = catalog_embs / np.where(norms > 0, norms, 1.0)

                scores = catalog_embs.dot(user_vec).tolist()

                logger.info(
                    f"Neural ML Computed {len(scores)} scores. Max score: {max(scores):.4f}"
                )

            results = []
            nid_set = seed_ids  # already a set of normalized IDs to exclude
            for item, score in zip(catalog, scores, strict=False):
                nid = _normalize_id(str(item.get("id", "")))
                if nid in nid_set:
                    continue

                # Neural contrast: Only boost positive correlations.
                # Negative correlations (repulsion) are handled by the shifted vector.
                safe_score = max(score, 0.0)

                # --- Specificity Boosting & Generalist Penalty ---
                # A "specialist" typically has 5-8 well-defined notes.
                # A "generalist" (like London) has 20+.
                all_notes = (
                    (item.get("top_notes", []) or [])
                    + (item.get("middle_notes", []) or [])
                    + (item.get("base_notes", []) or [])
                )
                num_notes = len(all_notes)

                # Dynamic complexity penalty: starts at 12 notes, drops scores by up to 30%
                complexity_penalty = 1.0
                if num_notes > 10:
                    complexity_penalty = max(0.7, 1.0 - (num_notes - 10) * 0.03)

                # Exponential Contrast: score^3 creates much sharper separation than score^1
                calibrated_score = (safe_score**3.0) * complexity_penalty

                results.append(
                    {
                        "id": str(item.get("id", "")),
                        "name": str(item.get("name", "Unknown")),
                        "brand": str(item.get("brand", "Unknown")),
                        "match_score": round(min(max(calibrated_score, 0.0), 1.0) * 100, 1),
                        "reason": "Neural soulbound match",
                    }
                )

            results.sort(key=lambda x: x["match_score"], reverse=True)
            top = results[:12]
            if top and top[0]["match_score"] > 0:
                return top
        except Exception as e:
            logger.error(f"ML scoring path failed: {e}")
            pass

    # -- ML path failed or incomplete --
    return []


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
    if _is_hydrating or _catalog_embeddings_cache is None:
        logger.error("ML_NOT_READY")
        raise HTTPException(
            status_code=503,
            detail="ML system is initializing. Please try again shortly.",
        )

    if not request.ratings:
        return {"status": "success", "data": []}

    catalog = load_recommendation_catalog()
    if not catalog:
        raise HTTPException(status_code=503, detail="Catalog unavailable")

    encoder = get_encoder()
    if not encoder:
        logger.error("ML_NOT_READY: Encoder missing")
        raise HTTPException(
            status_code=503,
            detail="ML system is initializing. Please try again shortly.",
        )

    try:
        # Generate profile vector from guest ratings
        rated_items = []
        weights = []
        catalog_by_id = {_normalize_id(str(i.get("id", ""))): i for i in catalog}

        for r in request.ratings:
            item = catalog_by_id.get(_normalize_id(r.fragrance_id))
            if item:
                rated_items.append(_get_item_text(item))
                weights.append(r.rating)

        if not rated_items:
            # If no items matched catalog, we can't do ML inference
            return {"status": "success", "data": []}

        user_embeddings = encoder.generate_embeddings(rated_items)
        total_w = sum(weights) or 1.0
        dim = len(user_embeddings[0])
        user_vec = [0.0] * dim
        for emb, w in zip(user_embeddings, weights, strict=False):
            for i in range(dim):
                user_vec[i] += emb[i] * (w / total_w)

        seed_ids = [_normalize_id(r.fragrance_id) for r in request.ratings]
        results = recommender.get_recommendations(user_vec, seed_ids)
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
    if not user_id:
        return {"status": "success", "data": []}

    cached_recs = await cache.get(f"rec:user:{user_id}")
    if cached_recs:
        data = [FragranceRecommendation(**r) for r in cached_recs]
        return {"status": "success", "data": data}

    stmt = select(DBFragranceRating).where(DBFragranceRating.user_id == user_id)
    result = await db.execute(stmt)
    saved_ratings = result.scalars().all()

    if not saved_ratings:
        return {"status": "success", "data": []}

    if _is_hydrating or _catalog_embeddings_cache is None:
        logger.error("ML_NOT_READY")
        raise HTTPException(
            status_code=503,
            detail="ML system is initializing. Please try again shortly.",
        )

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

    encoder = get_encoder()
    if not encoder:
        logger.error("ML_NOT_READY: Encoder missing")
        raise HTTPException(
            status_code=503,
            detail="ML system is initializing. Please try again shortly.",
        )

    try:
        rated_items = []
        weights = []
        catalog_by_id = {_normalize_id(str(i.get("id", ""))): i for i in catalog}

        for r in guest_ratings:
            item = catalog_by_id.get(_normalize_id(r.fragrance_id))
            if item:
                rated_items.append(_get_item_text(item))
                weights.append(r.rating)

        if not rated_items:
            return {"status": "success", "data": []}

        user_embeddings = encoder.generate_embeddings(rated_items)
        total_w = sum(weights) or 1.0
        dim = len(user_embeddings[0])
        user_vec = [0.0] * dim
        for emb, w in zip(user_embeddings, weights, strict=False):
            for i in range(dim):
                user_vec[i] += emb[i] * (w / total_w)

        seed_ids = [_normalize_id(r.fragrance_id) for r in guest_ratings]
        results = recommender.get_recommendations(user_vec, seed_ids)
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
