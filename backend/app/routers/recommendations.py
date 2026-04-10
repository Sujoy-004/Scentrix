import logging
import os
import math
import re
from typing import Any, Dict, List, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_optional_user_id
from app.database import get_session
from app.models.models import FragranceRating as DBFragranceRating, SavedFragrance
from app.services.catalog import load_recommendation_catalog

try:
    from ml.models.text_encoder import TextEncoder
except ImportError:
    TextEncoder = None

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)

# Lazy loading of models and clients to avoid blocking startup if missing
_encoder = None
_catalog_embeddings_cache = None

def get_encoder():
    global _encoder
    if _encoder is None and TextEncoder is not None:
        try:
            _encoder = TextEncoder()
            logger.info("Semantic ML Encoder activated successfully.")
        except Exception as e:
            logger.error(f"Failed to activate ML Encoder: {str(e)}")
            _encoder = None
    return _encoder

class FragranceRecommendation(BaseModel):
    id: str
    name: str
    brand: str
    match_score: float
    reason: str
    mock: bool = False

class FragranceRatingInput(BaseModel):
    fragrance_id: str
    rating: float
    top_notes: Optional[List[str]] = None
    accords: Optional[List[str]] = None
    description: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None

class GuestRecommendationRequest(BaseModel):
    ratings: List[FragranceRatingInput]

def _get_item_text(item: Dict[str, Any]) -> str:
    """Consolidate item metadata into a semantic string for the ML encoder."""
    parts = [
        str(item.get("name", "")),
        str(item.get("brand", "")),
        str(item.get("description", "")),
        " ".join(item.get("top_notes", []) or []),
        " ".join(item.get("accords", []) or [])
    ]
    return " ".join(filter(None, parts))

def _calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Assume L2-normed vectors (Standard for Sentence-BERT) for O(N) performance."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    return sum(a * b for a, b in zip(vec1, vec2))

def warmup_neural_engine():
    """Industrial-Scale Warm-up: Pre-calculate the DNA of the 9k library during startup."""
    global _catalog_embeddings_cache
    
    catalog = load_recommendation_catalog()
    encoder = get_encoder()
    
    if catalog and encoder and _catalog_embeddings_cache is None:
        logger.info(f"Neural Engine: Pre-caching DNA for {len(catalog)} fragrances. This will take a moment...")
        catalog_texts = [_get_item_text(item) for item in catalog]
        # This performs the heavy Lifting (384D Embeddings) before the user even arrives.
        _catalog_embeddings_cache = encoder.generate_embeddings(catalog_texts)
        logger.info(f"Neural Engine: 9k item library is Semantic-Indexed. Discovery ready.")
    return _catalog_embeddings_cache

@router.post("/guest", response_model=List[FragranceRecommendation])
async def get_guest_recommendations(
    request: GuestRecommendationRequest,
    encoder: Optional[TextEncoder] = Depends(get_encoder),
):
    global _catalog_embeddings_cache
    
    catalog = load_recommendation_catalog()
    if not catalog:
        return []

    if not request.ratings or encoder is None:
        # Return trending if no ratings or no ML brain
        return [
            FragranceRecommendation(
                id=str(catalog[i].get("id", "")),
                name=str(catalog[i].get("name", "Unknown")),
                brand=str(catalog[i].get("brand", "Unknown")),
                match_score=0.0,
                reason="Trending Selection",
            ) for i in range(min(10, len(catalog)))
        ]

    # Pre-Cache Catalog Embeddings (Neural Speed-of-Thought)
    warmup_neural_engine()

    # Semantic User Profile Synthesis
    user_texts = []
    user_weights = []
    
    for rating in request.ratings:
        target_raw = rating.fragrance_id.replace("frag_", "").replace("frag_syn_", "")
        item = next((f for f in catalog if str(f.get("id")).replace("frag_", "").replace("frag_syn_", "") == target_raw), None)
        
        if item:
            user_texts.append(_get_item_text(item))
            user_weights.append(float(rating.rating ** 2))
        elif rating.top_notes or rating.accords or rating.description:
            # Fallback for IDs missing from catalog but present in quiz metadata
            synthetic_text = _get_item_text({
                "name": rating.name or "",
                "brand": rating.brand or "",
                "top_notes": rating.top_notes or [],
                "accords": rating.accords or [],
                "description": rating.description or ""
            })
            user_texts.append(synthetic_text)
            user_weights.append(float(rating.rating ** 2))

    if not user_texts:
        return [
            FragranceRecommendation(
                id=str(catalog[i].get("id", "")),
                name=str(catalog[i].get("name", "Unknown")),
                brand=str(catalog[i].get("brand", "Unknown")),
                match_score=0.0,
                reason="Baseline Recommender",
            ) for i in range(min(10, len(catalog)))
        ]

    # Generate User's Aromatic Embedding (weighted average of their likes)
    user_embeddings = encoder.generate_embeddings(user_texts)
    
    # Weighted Average in Pure Python
    total_weight = sum(user_weights)
    dim = len(user_embeddings[0])
    user_profile_vec = [0.0] * dim
    
    for emb, weight in zip(user_embeddings, user_weights):
        for i in range(dim):
            user_profile_vec[i] += emb[i] * (weight / total_weight)

    # Perform Adaptive Hybrid Search (Vector Selection + Graph Reranking)
    from app.services.hybrid_search import recommender
    
    user_seed_ids = [r.fragrance_id for r in request.ratings]
    results = recommender.get_recommendations(user_profile_vec, user_seed_ids)
    
    return [FragranceRecommendation(**r, match_score=r["match_score"], reason=r["reason"]) for r in results]

@router.get("/personalized", response_model=List[FragranceRecommendation])
async def get_personalized_recommendations(
    user_id: str = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_session),
):
    if not user_id:
        return await get_guest_recommendations(GuestRecommendationRequest(ratings=[]))

    stmt = select(DBFragranceRating).where(DBFragranceRating.user_id == user_id)
    result = await db.execute(stmt)
    ratings = result.scalars().all()
    
    if not ratings:
        return await get_guest_recommendations(GuestRecommendationRequest(ratings=[]))
        
    guest_request = GuestRecommendationRequest(
        ratings=[FragranceRatingInput(fragrance_id=r.fragrance_id, rating=r.rating) for r in ratings]
    )
    return await get_guest_recommendations(guest_request)
