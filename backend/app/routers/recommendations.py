import logging
import os
from typing import Any

import psutil
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_id, get_optional_user_id
from app.cache import cache
from app.config import settings
from app.database import get_session
from app.logging_config import get_correlation_id
from app.models.models import FragranceRating as DBFragranceRating
from app.models.models import User
from app.schemas.schemas import (
    FragranceRecommendation,
    FragranceRatingInput,
    GuestRatingInput,
    GuestRecommendationRequest,
    QuizSummaryResponse,
    StandardResponse,
)
from app.services.catalog import load_recommendation_catalog
from app.services.dispatcher import DispatchRequest, RecommendationDispatcher
from app.services.feature_based import FeatureBasedService
from app.services.gs_embeddings import gs_service
from app.services.hybrid_search import _catalog_embeddings_cache, recommender
from app.services.popularity import PopularityService

# ── Feature flags ──────────────────────────────────────────────────────────────

PHASE8_DISPATCHER_ENABLED: bool = settings.phase8_dispatcher_enabled
USE_USER_VECTOR: bool = settings.use_user_vector

# ── Phase 8 dispatcher singleton (lazy-initialised services) ──────────────────

_feature_based_service: FeatureBasedService | None = None
_popularity_service: PopularityService = PopularityService()
_dispatcher: RecommendationDispatcher | None = None


def _get_dispatcher() -> RecommendationDispatcher | None:
    """Initialise and return the Phase 8 dispatcher singleton.

    Services are created on first call so imports do not block startup.
    ``gs_service`` is the module-level singleton from ``gs_embeddings``.
    If its artifacts are unavailable the service remains uninitialised;
    each strategy's fallback chain handles ``None`` gracefully.
    """
    global _feature_based_service, _dispatcher
    if _dispatcher is not None:
        return _dispatcher
    if _feature_based_service is None:
        _feature_based_service = FeatureBasedService()
    _dispatcher = RecommendationDispatcher(
        gs_service=gs_service,
        feature_based_service=_feature_based_service,
        popularity_service=_popularity_service,
    )
    return _dispatcher

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)

# State and Warmup logic moved to app.services.hybrid_search


def log_mem(stage):
    m = psutil.Process(os.getpid()).memory_info().rss / (1024**2)
    print(f"[MEM] {stage}: {m:.2f} MB")


def get_encoder():
    """Neural Engine: Access the ML Encoder via the global recommender service."""
    return recommender._get_encoder()


def _get_item_text(item: dict[str, Any]) -> str:
    """Proxy for the recommender service text extractor."""
    return recommender._get_item_text(item)


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class BatchRatingRequest(BaseModel):
    ratings: list[FragranceRatingInput]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _normalize_id(raw_id: str) -> str:
    """Return the canonical prefixed form (``frag_``) of a fragrance ID.

    The catalog SSOT (``ml/data/scentrix_master.json``), the GraphSAGE node
    index (``ml/models/serving/v1/node_ids_jaccard.json``) and the embedding
    index (``ml/data/embedding_index.json``) all key fragrances as
    ``frag_<brand>_<name>_<year>``.  Ratings persisted before the prefix
    convention (unprefixed ``FragranceRating.fragrance_neo4j_id``) are
    canonicalised on read; this helper guarantees every path (write and read)
    uses the same prefixed format.
    """
    if not raw_id or not raw_id.strip():
        return raw_id
    if raw_id.startswith("frag_"):
        return raw_id
    return f"frag_{raw_id}"


def _canonicalize_ratings(
    ratings: list[FragranceRatingInput | GuestRatingInput],
) -> list[FragranceRatingInput | GuestRatingInput]:
    """Return the same ratings with every ``fragrance_id`` canonicalised.

    The dispatcher resolves seeds against the GraphSAGE node index and the
    catalog, both of which key on the ``frag_``-prefixed form.  Applying the
    same canonicalisation the write paths use guarantees guest seeds resolve
    even if a client sends an unprefixed id.
    """
    return [
        r.model_copy(update={"fragrance_id": _normalize_id(r.fragrance_id)})
        for r in ratings
    ]


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
        # Use fragrance_neo4j_id (the actual DB column name).
        # Canonicalise to the prefixed form; legacy rows may still hold the
        # unprefixed variant, so match both and upgrade the row in place.
        neo4j_id = _normalize_id(request.fragrance_id)
        legacy_id = neo4j_id[len("frag_"):] if neo4j_id.startswith("frag_") else neo4j_id

        existing = await db.execute(
            select(DBFragranceRating).where(
                DBFragranceRating.user_id == user_id,
                DBFragranceRating.fragrance_neo4j_id.in_([neo4j_id, legacy_id]),
            )
        )
        row = existing.scalar_one_or_none()

        if row:
            row.quiz_rating = request.rating
            if row.fragrance_neo4j_id != neo4j_id:
                # Migrate the legacy unprefixed row to the canonical form.
                row.fragrance_neo4j_id = neo4j_id
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
            legacy_id = neo4j_id[len("frag_"):] if neo4j_id.startswith("frag_") else neo4j_id
            # Fast update/upsert logic
            existing = await db.execute(
                select(DBFragranceRating).where(
                    DBFragranceRating.user_id == user_id,
                    DBFragranceRating.fragrance_neo4j_id.in_([neo4j_id, legacy_id]),
                )
            )
            row = existing.scalar_one_or_none()

            if row:
                row.quiz_rating = r.rating
                if row.fragrance_neo4j_id != neo4j_id:
                    # Migrate the legacy unprefixed row to the canonical form.
                    row.fragrance_neo4j_id = neo4j_id
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
    cid = get_correlation_id()
    has_quiz = request.quiz_confidence is not None
    rating_count = len(request.ratings)
    logger.info(
        "event=recommendation_request correlation_id=%s type=guest has_quiz=%s rating_count=%s",
        cid, has_quiz, rating_count,
    )
    log_mem("START")
    if _catalog_embeddings_cache is None:
        logger.info("event=ml_lazy_load correlation_id=%s", cid)
        warmup_neural_engine()
        log_mem("AFTER_EMBEDDINGS")

    # ── Phase 8 dispatcher path ──────────────────────────────────────────
    logger.info(
        "event=dispatcher_gate correlation_id=%s phase8_enabled=%s path=%s",
        cid, PHASE8_DISPATCHER_ENABLED, "phase8" if PHASE8_DISPATCHER_ENABLED else "legacy",
    )
    if PHASE8_DISPATCHER_ENABLED:
        dispatcher = _get_dispatcher()
        if dispatcher is not None:
            catalog = load_recommendation_catalog()
            dr = DispatchRequest(
                # When quiz_confidence is present (quiz completed), ratings=[] so
                # rating_count=0 → State 1 → GraphSAGEStrategy receives quiz
                # responses via quiz_ratings for the user-vector path.
                # When there is no quiz, ratings are accumulated user ratings
                # and drive normal State 2/3/4 routing.
                ratings=[] if request.quiz_confidence else _canonicalize_ratings(request.ratings),
                quiz_ratings=_canonicalize_ratings(request.ratings) if request.quiz_confidence else [],
                # Shortcut: quiz_confidence present → quiz completed.
                # Functionally equivalent to the design spec's
                # len(responses) > 0 check on the session payload.
                quiz_completed=request.quiz_confidence is not None,
                quiz_confidence=request.quiz_confidence,
                use_user_vector=USE_USER_VECTOR,
                catalog=catalog,
                candidate_count=50,
                popularity_service=_popularity_service,
            )
            result = await dispatcher.dispatch(dr)
            if result.recommendations:
                logger.info(
                    "event=recommendation_result correlation_id=%s type=guest source=%s state=%s state_label=%s count=%s",
                    cid, result.source, result.state, result.state_label, len(result.recommendations),
                )
                data = [FragranceRecommendation(**r) for r in result.recommendations]
                return {
                    "status": "success",
                    "data": data,
                    "state": result.state,
                    "state_label": result.state_label,
                }
            logger.info(
                "event=dispatcher_empty correlation_id=%s type=guest",
                cid,
            )

    # ── Legacy path ──────────────────────────────────────────────────────
    try:
        seed_ids = [_normalize_id(r.fragrance_id) for r in request.ratings]
        results = recommender.get_recommendations(request.ratings, seed_ids)
        logger.info(
            "event=recommendation_result correlation_id=%s type=guest source=legacy count=%s",
            cid, len(results),
        )
        data = [FragranceRecommendation(**r) for r in results]
        return {"status": "success", "data": data}

    except Exception as e:
        logger.error(
            "event=recommendation_error correlation_id=%s type=guest error=%s",
            cid, e,
        )
        raise HTTPException(
            status_code=500,
            detail="Recommendation engine encountered a fault.",
        ) from e


@router.get("/personalized", response_model=StandardResponse)
async def get_personalized_recommendations(
    user_id: int | None = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_session),
) -> StandardResponse:
    cid = get_correlation_id()
    logger.info(
        "event=recommendation_request correlation_id=%s type=personalized user_id=%s",
        cid, user_id,
    )
    log_mem("START")
    if not user_id:
        logger.info(
            "event=recommendation_result correlation_id=%s type=personalized source=no_user count=0",
            cid,
        )
        return {"status": "success", "data": []}

    cached_recs = await cache.get(f"rec:user:{user_id}")
    if cached_recs:
        data = [FragranceRecommendation(**r) for r in cached_recs]
        # Resolve state for cached response
        user_stmt = select(User).where(User.id == user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        quiz_completed = user is not None and user.quiz_completed_at is not None
        stmt_count = select(DBFragranceRating).where(DBFragranceRating.user_id == user_id)
        count_result = await db.execute(stmt_count)
        rating_count = len(count_result.scalars().all())
        cached_state = RecommendationDispatcher.determine_state(rating_count, quiz_completed)
        state_label = {0: "anonymous", 1: "quiz_user", 2: "cold", 3: "warm", 4: "mature"}.get(cached_state, "unknown")
        logger.info(
            "event=recommendation_result correlation_id=%s type=personalized source=cache state=%s state_label=%s count=%s user_id=%s",
            cid, cached_state, state_label, len(data), user_id,
        )
        return {"status": "success", "data": data, "state": cached_state, "state_label": state_label}

    if not db:
        return {"status": "success", "data": []}

    # ── Phase 8 dispatcher path ──────────────────────────────────────────
    if PHASE8_DISPATCHER_ENABLED:
        dispatcher = _get_dispatcher()
        if dispatcher is not None:
            stmt = select(DBFragranceRating).where(DBFragranceRating.user_id == user_id)
            result = await db.execute(stmt)
            saved_ratings = result.scalars().all()

            if not saved_ratings:
                return {"status": "success", "data": []}

            catalog = load_recommendation_catalog()
            if not catalog:
                return {"status": "success", "data": []}

            user_stmt = select(User).where(User.id == user_id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            quiz_completed = user is not None and user.quiz_completed_at is not None

            ratings = [
                FragranceRatingInput(
                    fragrance_id=_normalize_id(str(r.fragrance_neo4j_id)),
                    rating=r.quiz_rating or 5.0,
                )
                for r in saved_ratings
            ]

            dr = DispatchRequest(
                user_id=user_id,
                ratings=ratings,
                quiz_completed=quiz_completed,
                use_user_vector=USE_USER_VECTOR,
                catalog=catalog,
                candidate_count=50,
                popularity_service=_popularity_service,
            )
            dr_result = await dispatcher.dispatch(dr)

            if dr_result.recommendations:
                await cache.set(
                    f"rec:user:{user_id}",
                    dr_result.recommendations,
                    expire=3600,
                )
                logger.info(
                    "event=recommendation_result correlation_id=%s type=personalized source=%s state=%s state_label=%s count=%s user_id=%s",
                    cid, dr_result.source, dr_result.state, dr_result.state_label, len(dr_result.recommendations), user_id,
                )
                data = [FragranceRecommendation(**r) for r in dr_result.recommendations]
                return {
                    "status": "success",
                    "data": data,
                    "state": dr_result.state,
                    "state_label": dr_result.state_label,
                }

            logger.info(
                "event=dispatcher_empty correlation_id=%s type=personalized user_id=%s",
                cid, user_id,
            )

    # ── Legacy path ──────────────────────────────────────────────────────
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
            fragrance_id=_normalize_id(str(r.fragrance_neo4j_id)),
            rating=r.quiz_rating or 5.0,
        )
        for r in saved_ratings
    ]

    try:
        seed_ids = [_normalize_id(r.fragrance_id) for r in guest_ratings]
        results = recommender.get_recommendations(guest_ratings, seed_ids)
    except Exception as e:
        logger.error(
            "event=recommendation_error correlation_id=%s type=personalized user_id=%s error=%s",
            cid, user_id, e,
        )
        raise HTTPException(
            status_code=500,
            detail="Recommendation engine encountered a fault.",
        ) from e

    if results:
        await cache.set(f"rec:user:{user_id}", results, expire=3600)

    data = [FragranceRecommendation(**r) for r in results]
    return {"status": "success", "data": data}


@router.get("/quiz-summary", response_model=StandardResponse)
async def get_quiz_summary(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> StandardResponse:
    """Return the last quiz summary built entirely from existing persisted data.

    Uses only:
    - User.quiz_completed_at — when the user last completed (finalized) a quiz
    - FragranceRating — all quiz ratings for this user
    - FeatureBasedService — to compute top matches from existing ratings
    - load_recommendation_catalog — catalog lookup for accord/note analysis

    No new tables, no timeline infrastructure, no schema changes.
    """
    user_stmt = select(User).where(User.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(DBFragranceRating).where(DBFragranceRating.user_id == user_id)
    result = await db.execute(stmt)
    saved_ratings = result.scalars().all()

    if not user.quiz_completed_at:
        return {"status": "success", "data": QuizSummaryResponse(has_completed_quiz=False)}

    ratings_list = [
        FragranceRatingInput(
            fragrance_id=_normalize_id(str(r.fragrance_neo4j_id)),
            rating=r.quiz_rating or 5.0,
        )
        for r in saved_ratings
    ]

    catalog = load_recommendation_catalog()

    top_matches: list[FragranceRecommendation] = []
    top_notes: list[str] = []
    top_accords: list[str] = []

    if ratings_list and catalog:
        fb_service = _feature_based_service or FeatureBasedService()
        scored = fb_service.score(ratings_list, catalog, user_seed_ids=[], top_k=3)
        for s in scored:
            top_matches.append(FragranceRecommendation(**s))

        catalog_map = {str(item["id"]): item for item in catalog}
        note_counter: dict[str, int] = {}
        accord_counter: dict[str, int] = {}
        for r in saved_ratings:
            # Canonicalise stored ids so legacy unprefixed rows match the
            # prefixed catalog_map (otherwise top_notes/top_accords stay empty).
            item = catalog_map.get(_normalize_id(str(r.fragrance_neo4j_id)))
            if item:
                for note in item.get("top_notes", []):
                    note_counter[str(note)] = note_counter.get(str(note), 0) + 1
                for accord in item.get("accords", []):
                    accord_counter[str(accord)] = accord_counter.get(str(accord), 0) + 1
        top_notes = [n for n, _ in sorted(note_counter.items(), key=lambda x: -x[1])[:5]]
        top_accords = [a for a, _ in sorted(accord_counter.items(), key=lambda x: -x[1])[:5]]

    total = len(saved_ratings)
    ratings_vals = [r.quiz_rating or 5.0 for r in saved_ratings]
    avg = round(sum(ratings_vals) / len(ratings_vals), 1) if ratings_vals else None
    avg_norm = round(avg / 2, 1) if avg is not None else None

    high = sum(1 for v in ratings_vals if v >= 7)
    medium = sum(1 for v in ratings_vals if 4 <= v <= 6)
    low = sum(1 for v in ratings_vals if v < 4)

    summary = QuizSummaryResponse(
        has_completed_quiz=True,
        completed_at=user.quiz_completed_at.isoformat(),
        total_rated=total,
        average_rating=avg,
        average_normalized=avg_norm,
        rating_distribution={"high": high, "medium": medium, "low": low},
        top_matches=top_matches,
        top_notes=top_notes,
        top_accords=top_accords,
    )

    return {"status": "success", "data": summary}


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
