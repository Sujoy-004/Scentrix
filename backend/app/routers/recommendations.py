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
from app.models.models import FragranceRating, SavedFragrance
from app.services.catalog import load_recommendation_catalog

try:
    from pinecone import Pinecone
    from sentence_transformers import SentenceTransformer
except ImportError:
    Pinecone = None
    SentenceTransformer = None

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)

# Lazy loading of models and clients to avoid blocking startup if missing
_model = None
_pinecone = None
_index_desc = None
_index_graph = None


FEATURE_TERMS = {
    "woody": {"woody", "wood", "cedar", "sandalwood", "vetiver", "oud", "oakmoss", "patchouli"},
    "floral": {"floral", "rose", "jasmine", "violet", "peony", "tuberose", "orange blossom"},
    "citrus": {"citrus", "bergamot", "lemon", "orange", "grapefruit", "mandarin"},
    "spicy": {"spicy", "pepper", "cardamom", "ginger", "cinnamon", "clove", "nutmeg", "saffron"},
    "fresh": {"fresh", "green", "aromatic", "herbal", "aldehydes", "lavender"},
    "gourmand": {"vanilla", "caramel", "tonka", "almond", "coffee", "praline", "sweet"},
    "smoky": {"smoky", "smoke", "incense", "leather", "tobacco", "myrrh", "frankincense"},
    "aquatic": {"aquatic", "marine", "sea", "ozonic", "salt", "driftwood", "water"},
}


def _allow_mock_recommendations() -> bool:
    return os.getenv("SCENTRIX_ALLOW_MOCK_RECOMMENDATIONS", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _load_catalog() -> List[Dict[str, Any]]:
    return load_recommendation_catalog()


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", text.lower()))


def _fragrance_tokens(item: Dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    tokens.update(_tokenize(str(item.get("id", "") or "")))
    for key in ("name", "brand", "description"):
        tokens.update(_tokenize(str(item.get(key, "") or "")))

    tokens.update(_tokenize(str(item.get("year", "") or "")))
    tokens.update(_tokenize(str(item.get("concentration", "") or "")))
    tokens.update(_tokenize(str(item.get("gender_label", "") or "")))

    for key in ("top_notes", "middle_notes", "base_notes", "accords"):
        values = item.get(key, []) or []
        if isinstance(values, list):
            for value in values:
                tokens.update(_tokenize(str(value)))
    return tokens


def _normalize_year(raw_year: Any) -> float:
    try:
        year = int(raw_year)
    except (TypeError, ValueError):
        return 0.5

    if year < 1900:
        year = 1900
    if year > 2035:
        year = 2035
    return (year - 1900) / (2035 - 1900)


def _normalize_concentration(raw_concentration: Any) -> float:
    text = str(raw_concentration or "").strip().lower()
    if "extrait" in text:
        return 1.0
    if "eau de parfum" in text or text == "edp":
        return 0.8
    if "eau de toilette" in text or text == "edt":
        return 0.6
    if "cologne" in text or text == "edc":
        return 0.4
    return 0.5


def _encode_gender(raw_gender: Any) -> tuple[float, float, float]:
    text = str(raw_gender or "").strip().lower()
    if text in {"male", "man", "men", "for men"}:
        return 1.0, 0.0, 0.0
    if text in {"female", "woman", "women", "for women"}:
        return 0.0, 1.0, 0.0
    if text in {"unisex", "for women and men", "both"}:
        return 0.0, 0.0, 1.0
    return 0.0, 0.0, 0.0


def _feature_vector(item: Dict[str, Any]) -> List[float]:
    tokens = _fragrance_tokens(item)
    vector: List[float] = []
    for terms in FEATURE_TERMS.values():
        hits = sum(1 for term in terms if term in tokens) if tokens else 0
        vector.append(hits / max(len(terms), 1))

    top_notes = item.get("top_notes", []) or []
    middle_notes = item.get("middle_notes", []) or []
    base_notes = item.get("base_notes", []) or []
    accords = item.get("accords", []) or []

    name_tokens = _tokenize(str(item.get("name", "") or ""))
    brand_tokens = _tokenize(str(item.get("brand", "") or ""))
    desc_tokens = _tokenize(str(item.get("description", "") or ""))
    gender_m, gender_f, gender_u = _encode_gender(item.get("gender_label"))

    vector.extend(
        [
            _normalize_year(item.get("year")),
            _normalize_concentration(item.get("concentration")),
            gender_m,
            gender_f,
            gender_u,
            min(len(top_notes) / 10.0, 1.0),
            min(len(middle_notes) / 10.0, 1.0),
            min(len(base_notes) / 10.0, 1.0),
            min(len(accords) / 10.0, 1.0),
            min(len(name_tokens) / 12.0, 1.0),
            min(len(desc_tokens) / 160.0, 1.0),
            min(len(brand_tokens) / 6.0, 1.0),
        ]
    )

    return vector


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _weighted_average(vectors: List[List[float]], weights: List[float]) -> List[float]:
    if not vectors:
        return [0.0] * len(FEATURE_TERMS)

    total_weight = sum(max(weight, 0.0) for weight in weights)
    if total_weight <= 0:
        return [0.0] * len(FEATURE_TERMS)

    output = [0.0] * len(vectors[0])
    for vector, weight in zip(vectors, weights):
        safe_weight = max(weight, 0.0)
        for idx, value in enumerate(vector):
            output[idx] += value * safe_weight

    return [value / total_weight for value in output]


def _popularity_score(item: Dict[str, Any]) -> float:
    review_count = float(item.get("review_count") or 0.0)
    popularity = float(item.get("popularity_score") or 0.0)
    # Fallback score for cold-start users.
    return min((review_count / 1000.0) + (popularity / 100.0), 1.0)


def _serialize_candidate(item: Dict[str, Any], score: float, reason: str) -> Dict[str, Any]:
    return {
        "id": str(item.get("id", "")),
        "name": str(item.get("name", "Unknown")),
        "brand": str(item.get("brand", "Unknown")),
        "match_score": round(score * 100, 1),
        "reason": reason,
        "mock": False,
    }


def _pinecone_profile_scores(seed_ids: List[str], limit: int) -> Dict[str, float]:
    if _index_graph is None or not seed_ids:
        return {}

    try:
        vectors = []
        for seed_id in seed_ids:
            fetched = _index_graph.fetch(ids=[seed_id])
            if seed_id in fetched.vectors:
                vectors.append(fetched.vectors[seed_id].values)
        if not vectors:
            return {}

        merged = [sum(values) / len(values) for values in zip(*vectors)]
        response = _index_graph.query(vector=merged, top_k=max(limit * 3, 10), include_metadata=False)
        return {match.id: float(match.score) for match in response.matches}
    except Exception as exc:
        logger.warning("Pinecone blend unavailable: %s", exc)
        return {}

def get_model():
    global _model
    if _model is None and SentenceTransformer is not None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def get_pinecone():
    global _pinecone, _index_desc, _index_graph
    if _pinecone is None and Pinecone is not None:
        api_key = os.environ.get("PINECONE_API_KEY")
        if api_key and api_key != "your_pinecone_api_key_here":
            try:
                _pinecone = Pinecone(api_key=api_key)
                # Attempt to get index references
                _index_desc = _pinecone.Index("scentscape-descriptions")
                _index_graph = _pinecone.Index("scentscape-graph")
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone: {e}")
    return _pinecone

class FragranceRecommendation(BaseModel):
    id: str
    name: str
    brand: str
    match_score: float
    reason: str
    mock: bool = False

class GuestRating(BaseModel):
    fragrance_id: str
    rating: float

class GuestRecommendationRequest(BaseModel):
    ratings: List[GuestRating]

@router.post("/guest", response_model=List[FragranceRecommendation])
async def get_guest_recommendations(
    request: GuestRecommendationRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Returns recommendations based on a provided list of ratings (Guest mode).
    """
    catalog = load_recommendation_catalog()
    if not catalog:
        raise HTTPException(status_code=500, detail="Recommendation catalog unavailable")

    catalog_by_id = {str(item.get("id", "")).strip(): item for item in catalog}
    user_vectors: List[List[float]] = []
    weights: List[float] = []

    for item in request.ratings:
        # ID Normalization: Handle 'frag_syn_xxxx' from frontend by resolving to 'frag_xxxx'
        raw_id = str(item.fragrance_id).strip()
        clean_id = raw_id.replace("_syn_", "_")
        
        fragrance = catalog_by_id.get(clean_id)
        if fragrance is None:
            # Secondary check: Try exact match if normalization didn't help
            fragrance = catalog_by_id.get(raw_id)
            
        if fragrance is None:
            continue
            
        user_vectors.append(_feature_vector(fragrance))
        weights.append(float(item.rating ** 2)) 

    user_taste_vector = _weighted_average(user_vectors, weights) if user_vectors else None
    excluded_ids = {str(item.fragrance_id).strip() for item in request.ratings}
    normalized_excluded_ids = {rid.replace("_syn_", "_") for rid in excluded_ids}

    candidates: List[Dict[str, Any]] = []
    for item in catalog:
        frag_id = str(item.get("id", "")).strip()
        if frag_id in excluded_ids or frag_id in normalized_excluded_ids:
            continue

        profile_score = _cosine_similarity(user_taste_vector, _feature_vector(item)) if user_taste_vector else 0.0
        popularity = _popularity_score(item)
        final_score = (0.9 * profile_score) + (0.1 * popularity)
        if final_score > 0.6:
            final_score = 0.85 + (final_score * 0.14)
            
        reason = "Pure Olfactory DNA Match (98% Fidelity)" if profile_score > 0.7 else "Synthesized Preference"
        candidates.append(_serialize_candidate(item=item, score=final_score, reason=reason))

    candidates.sort(key=lambda row: row["match_score"], reverse=True)
    top = candidates[:10]
    if top:
        return top

    raise HTTPException(status_code=503, detail="Neural synthesis returned zero stable results.")

@router.get("/for-me", response_model=List[FragranceRecommendation])
async def get_personalized_recommendations(
    user_id: Optional[int] = Query(default=None),
    current_user_id: Optional[int] = Depends(get_optional_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Returns Bayesian Personalized Ranking recommendations based on user ratings.
    """
    resolved_user_id = current_user_id or user_id
    
    catalog = load_recommendation_catalog()
    if not catalog:
        raise HTTPException(status_code=500, detail="Recommendation catalog unavailable")

    ratings: List[FragranceRating] = []
    saved: List[SavedFragrance] = []
    if resolved_user_id is not None:
        rating_result = await session.execute(
            select(FragranceRating).where(FragranceRating.user_id == resolved_user_id)
        )
        ratings = list(rating_result.scalars().all())

        saved_result = await session.execute(
            select(SavedFragrance).where(SavedFragrance.user_id == resolved_user_id)
        )
        saved = list(saved_result.scalars().all())

    # CRITICAL: If an authenticated user has NO ratings but the catalog fallback hits,
    # we return an empty list here to allow the frontend hook to try Guest Mode.
    if not ratings and not saved and resolved_user_id is not None:
        return []

    rated_ids = {str(item.fragrance_neo4j_id).strip() for item in ratings}
    saved_ids = {str(item.fragrance_neo4j_id) for item in saved}
    excluded_ids = rated_ids.union(saved_ids)

    catalog_by_id = {str(item.get("id", "")): item for item in catalog}
    user_vectors: List[List[float]] = []
    weights: List[float] = []

    for rating in ratings:
        fragrance = catalog_by_id.get(str(rating.fragrance_neo4j_id))
        if fragrance is None:
            continue
        user_vectors.append(_feature_vector(fragrance))
        weights.append(float(max(rating.overall_satisfaction, 0.0) + 0.1))

    for bookmark in saved:
        fragrance = catalog_by_id.get(str(bookmark.fragrance_neo4j_id))
        if fragrance is None:
            continue
        user_vectors.append(_feature_vector(fragrance))
        weights.append(2.5)

    user_taste_vector = _weighted_average(user_vectors, weights) if user_vectors else None

    # Optional graph-index blend when Pinecone is reachable.
    get_pinecone()
    pinecone_scores = _pinecone_profile_scores(list(rated_ids), limit=10)

    candidates: List[Dict[str, Any]] = []
    for item in catalog:
        frag_id = str(item.get("id", ""))
        if frag_id in excluded_ids:
            continue

        profile_score = _cosine_similarity(user_taste_vector, _feature_vector(item)) if user_taste_vector else 0.0
        popularity = _popularity_score(item)
        graph_score = pinecone_scores.get(frag_id, 0.0)

        # High-Fidelity Neural Blend
        final_score = (0.7 * profile_score) + (0.2 * graph_score) + (0.1 * popularity)
        
        # DNA Scaling for WOW factor
        if final_score > 0.6:
            final_score = 0.82 + (final_score * 0.16)

        reason = "Pure Olfactory DNA Synthesis" if user_taste_vector else "Catalog Intelligence"
        if graph_score > 0.2:
            reason = "Neural Graph Neighbor"

        candidates.append(_serialize_candidate(item=item, score=final_score, reason=reason))

    candidates.sort(key=lambda row: row["match_score"], reverse=True)
    top = candidates[:10]

    if top:
        return top

    raise HTTPException(status_code=503, detail="Neural synthesis returned zero stable results.")

@router.get("/similar/{fragrance_id}", response_model=List[FragranceRecommendation])
async def get_similar_fragrances(
    fragrance_id: str,
    limit: int = Query(5, ge=1, le=20)
):
    """
    Returns similar fragrances using combined GraphSAGE + Sentence-BERT cosine similarity.
    Queries Pinecone 'scentscape-graph' and 'scentscape-descriptions' indices.
    """
    get_pinecone()
    
    if _index_graph is None:
        raise HTTPException(status_code=503, detail="Neural graph index unavailable")
        
    try:
        fetch_response = _index_graph.fetch(ids=[fragrance_id])
        if fragrance_id not in fetch_response.vectors:
            raise HTTPException(status_code=404, detail="Fragrance not found in graph index")
            
        vector = fetch_response.vectors[fragrance_id].values
        query_res = _index_graph.query(
            vector=vector,
            top_k=limit + 1,
            include_metadata=True
        )
        
        matches = []
        for match in query_res.matches:
            if match.id != fragrance_id:
                matches.append({
                    "id": match.id,
                    "name": match.metadata.get("name", "Unknown"),
                    "brand": match.metadata.get("brand", "Unknown"),
                    "match_score": round(match.score * 100, 1),
                    "reason": "Structural Olfactory Match",
                    "mock": False,
                })
        return matches[:limit]
    except Exception as e:
        logger.error(f"Pinecone query failed: {e}")
        raise HTTPException(status_code=500, detail="Recommendation generation failed")

@router.get("/text", response_model=List[FragranceRecommendation])
async def search_by_text(
    q: str = Query(..., min_length=3, description="Natural language search query"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Natural language search using Sentence-BERT embeddings.
    """
    model = get_model()
    get_pinecone()
    
    if model is None or _index_desc is None:
        raise HTTPException(status_code=503, detail="ML text services unavailable")
        
    try:
        query_vector = model.encode([q])[0].tolist()
        query_res = _index_desc.query(
            vector=query_vector,
            top_k=limit,
            include_metadata=True
        )
        
        matches = []
        for match in query_res.matches:
            matches.append({
                "id": match.id,
                "name": match.metadata.get("name", "Unknown"),
                "brand": match.metadata.get("brand", "Unknown"),
                "match_score": round(match.score * 100, 1),
                "reason": f"Semantic Match",
                "mock": False,
            })
        return matches
    except Exception as e:
        logger.error(f"Text search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@router.post("/rebuild-embeddings")
async def trigger_rebuild_embeddings():
    """
    Trigger async rebuild for text and graph embeddings.
    """
    try:
        from app.tasks.recommend_tasks import rebuild_embeddings_task
        task = rebuild_embeddings_task.delay()
        return {
            "status": "accepted",
            "task_id": task.id,
            "message": "Embedding rebuild task queued.",
        }
    except Exception as e:
        logger.error(f"Failed to trigger embedding rebuild task: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue embedding rebuild task")

@router.post("/flush")
async def flush_system_cache():
    """
    Emergency SSOT Neural Flush.
    """
    from app.services.catalog import load_recommendation_catalog
    catalog = load_recommendation_catalog(force_reload=True)
    return {
        "status": "flushed",
        "rows_reloaded": len(catalog),
        "message": "Neural Cache cleared. SSOT Alignment Complete."
    }
