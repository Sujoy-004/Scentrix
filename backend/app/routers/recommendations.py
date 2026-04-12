import logging
import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_optional_user_id, get_current_user_id
from app.database import get_session
from app.models.models import FragranceRating as DBFragranceRating, SavedFragrance
from app.services.catalog import load_recommendation_catalog

try:
    from ml.models.text_encoder import TextEncoder
except ImportError:
    TextEncoder = None

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)


# ── Module-level caches ───────────────────────────────────────────────────────
_encoder = None
_catalog_embeddings_cache = None


def get_encoder():
    global _encoder
    if _encoder is None and TextEncoder is not None:
        try:
            _encoder = TextEncoder()
            logger.info("Semantic ML Encoder activated.")
        except Exception as e:
            logger.error(f"Failed to activate ML Encoder: {e}")
            _encoder = None
    return _encoder


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
    fragrance_id: str          # ID as sent by the frontend (may have frag_ prefix)
    rating: float              # 1-10 quiz rating
    top_notes: Optional[List[str]] = None
    accords: Optional[List[str]] = None
    description: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None


class GuestRecommendationRequest(BaseModel):
    ratings: List[FragranceRatingInput]


class BatchRatingRequest(BaseModel):
    ratings: List[FragranceRatingInput]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_id(raw_id: str) -> str:
    """Strip common prefix variants so IDs match the catalog."""
    return raw_id.replace("frag_syn_", "").replace("frag_", "")


def _get_item_text(item: Dict[str, Any]) -> str:
    parts = [
        str(item.get("name", "")),
        str(item.get("brand", "")),
        str(item.get("description", "")),
        " ".join(item.get("top_notes", []) or []),
        " ".join(item.get("accords", []) or []),
    ]
    return " ".join(filter(None, parts))


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    return sum(a * b for a, b in zip(v1, v2))


def warmup_neural_engine():
    """Pre-cache catalog embeddings at startup."""
    global _catalog_embeddings_cache
    catalog = load_recommendation_catalog()
    encoder = get_encoder()
    if catalog and encoder and _catalog_embeddings_cache is None:
        logger.info(f"Neural Engine: pre-caching {len(catalog)} fragrances …")
        texts = [_get_item_text(item) for item in catalog]
        _catalog_embeddings_cache = encoder.generate_embeddings(texts)
        logger.info("Neural Engine: catalog indexed and ready.")
    return _catalog_embeddings_cache


# ── Score engine ──────────────────────────────────────────────────────────────

def _score_catalog(
    user_ratings: List[FragranceRatingInput],
    catalog: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Generate recommendations from user quiz ratings.

    Strategy (in priority order):
    1. ML semantic embedding (if encoder available + catalog cached)
    2. Note/accord overlap heuristic (always available)
    3. Trending fallback (when no ratings match catalogue)
    """
    encoder = get_encoder()
    catalog_by_norm_id = {_normalize_id(str(item.get("id", ""))): item for item in catalog}

    # -- Resolve user rated items against catalog --------------------------
    rated_items: List[Dict[str, Any]] = []
    weights: List[float] = []
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

    # -- ML path -----------------------------------------------------------
    if encoder and _catalog_embeddings_cache is not None and rated_items:
        try:
            import numpy as np
            user_texts = [_get_item_text(item) for item in rated_items]
            user_embeddings = encoder.generate_embeddings(user_texts)

            total_w = sum(weights) or 1.0
            dim = len(user_embeddings[0])
            user_vec = [0.0] * dim
            for emb, w in zip(user_embeddings, weights):
                for i in range(dim):
                    user_vec[i] += emb[i] * (w / total_w)

            catalog_embs = np.array(_catalog_embeddings_cache)
            uv = np.array(user_vec)
            scores = catalog_embs.dot(uv).tolist()

            results = []
            for item, score in zip(catalog, scores):
                nid = _normalize_id(str(item.get("id", "")))
                if nid in seed_ids:
                    continue
                results.append({
                    "id": str(item.get("id", "")),
                    "name": str(item.get("name", "Unknown")),
                    "brand": str(item.get("brand", "Unknown")),
                    "match_score": round(min(max(score, 0.0), 1.0) * 100, 1),
                    "reason": "Neural soulbound match",
                })

            results.sort(key=lambda x: x["match_score"], reverse=True)
            top = results[:12]
            if top and top[0]["match_score"] > 0:
                return top
        except Exception as e:
            logger.warning(f"ML scoring failed, falling back to heuristic: {e}")

    # -- Heuristic note-overlap path ----------------------------------------
    if liked_notes or liked_accords:
        results = []
        for item in catalog:
            nid = _normalize_id(str(item.get("id", "")))
            if nid in seed_ids:
                continue
            item_notes = set(item.get("top_notes", []) or [])
            item_accords = set(item.get("accords", []) or [])
            note_overlap = len(item_notes & liked_notes)
            accord_overlap = len(item_accords & liked_accords)
            total_overlap = note_overlap * 2 + accord_overlap
            max_possible = max(len(liked_notes) * 2 + len(liked_accords), 1)
            score = min(total_overlap / max_possible, 1.0)
            results.append({
                "id": str(item.get("id", "")),
                "name": str(item.get("name", "Unknown")),
                "brand": str(item.get("brand", "Unknown")),
                "match_score": round(score * 100, 1),
                "reason": f"{note_overlap} shared notes, {accord_overlap} shared accords",
            })

        results.sort(key=lambda x: x["match_score"], reverse=True)
        top = [r for r in results[:12] if r["match_score"] > 0]
        if top:
            return top

    # -- Trending fallback --------------------------------------------------
    return [
        {
            "id": str(catalog[i].get("id", "")),
            "name": str(catalog[i].get("name", "Unknown")),
            "brand": str(catalog[i].get("brand", "Unknown")),
            "match_score": round((len(catalog) - i) / len(catalog) * 60, 1),
            "reason": "Trending pick",
        }
        for i in range(min(12, len(catalog)))
    ]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/rate", status_code=200)
async def submit_fragrance_rating(
    request: FragranceRatingInput,
    user_id: Optional[int] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_session),
):
    """
    Persist a quiz rating for authenticated users.
    For guests this is a silent 200 no-op — ratings live in localStorage.
    """
    if not user_id:
        return {"status": "guest_local"}

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
            db.add(DBFragranceRating(
                user_id=user_id,
                fragrance_neo4j_id=neo4j_id,
                quiz_rating=request.rating,
            ))

        await db.commit()
        return {"status": "saved"}

    except Exception as e:
        logger.error(f"Rating persist error for user {user_id}: {e}")
        return {"status": "error", "detail": str(e)}


@router.post("/batch-rate", status_code=200)
async def submit_batch_ratings(
    request: BatchRatingRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
):
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
                db.add(DBFragranceRating(
                    user_id=user_id,
                    fragrance_neo4j_id=neo4j_id,
                    quiz_rating=r.rating,
                ))
            count += 1
            
        await db.commit()
        return {"status": "saved", "count": count}
    except Exception as e:
        logger.error(f"Batch rating persist error for user {user_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to sync batch ratings")


@router.post("/guest", response_model=List[FragranceRecommendation])
async def get_guest_recommendations(
    request: GuestRecommendationRequest,
):
    """Score against the full catalog purely from guest quiz ratings."""
    catalog = load_recommendation_catalog()
    if not catalog:
        raise HTTPException(status_code=503, detail="Catalog unavailable")

    if not request.ratings:
        return []

    warmup_neural_engine()
    results = _score_catalog(request.ratings, catalog)
    return [FragranceRecommendation(**r) for r in results]


@router.get("/personalized", response_model=List[FragranceRecommendation])
async def get_personalized_recommendations(
    user_id: Optional[int] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_session),
):
    """
    Return personalized recommendations for an authenticated user based on
    their saved quiz ratings. Falls back to empty list if no ratings exist.
    """
    if not user_id:
        return []

    stmt = select(DBFragranceRating).where(DBFragranceRating.user_id == user_id)
    result = await db.execute(stmt)
    saved_ratings = result.scalars().all()

    if not saved_ratings:
        return []

    catalog = load_recommendation_catalog()
    if not catalog:
        raise HTTPException(status_code=503, detail="Catalog unavailable")

    warmup_neural_engine()

    # Convert DB rows back to the same format as guest ratings
    guest_ratings = [
        FragranceRatingInput(
            fragrance_id=r.fragrance_neo4j_id,
            rating=r.quiz_rating or 5.0,
        )
        for r in saved_ratings
    ]

    results = _score_catalog(guest_ratings, catalog)
    return [FragranceRecommendation(**r) for r in results]
