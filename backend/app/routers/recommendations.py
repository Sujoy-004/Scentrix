"""Recommendation endpoints routed through the 3-state warmth dispatcher.

No Redis cache, no psutil, no sommelier, no async. All handlers are sync;
FastAPI runs them in a threadpool.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_id
from app.database import get_db
from app.models.models import FragranceRating, User
from app.schemas.schemas import (
    FragranceRatingInput,
    FragranceRecommendation,
    GuestRatingInput,
    StandardResponse,
)
from app.services.catalog import _normalize_id
from app.services.dispatcher import RecommendationDispatcher
from app.services.embeddings import gs_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommendations", tags=["recommendations"])

CANDIDATE_COUNT = 20

_dispatcher = RecommendationDispatcher()


def _ensure_embeddings() -> None:
    """Lazily warm the embedding cache; failures fall back to popularity."""
    if not gs_service.initialized:
        try:
            gs_service.initialize()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Embedding cache init failed (%s) — popularity fallback active", exc)


class BatchRatingRequest(BaseModel):
    """Batch of ratings to upsert (guest → user conversion)."""

    ratings: list[FragranceRatingInput]


class GuestRecommendationBody(BaseModel):
    """Guest recommendation request (3-state dispatcher input).

    Accepts the spec shape ``{ratings, quiz_submitted}`` and the legacy
    frontend shape ``{ratings, quiz_confidence}`` interchangeably.
    """

    ratings: list[GuestRatingInput] = Field(default_factory=list)
    quiz_submitted: bool | None = None
    quiz_confidence: dict[str, float] | None = None


def _upsert_rating(db: Session, user_id: int, fragrance_id: str, rating: float) -> None:
    """Insert or update one FragranceRating row (SQLite-safe upsert)."""
    fid = _normalize_id(str(fragrance_id))
    row = db.execute(
        select(FragranceRating).where(
            FragranceRating.user_id == user_id,
            FragranceRating.fragrance_neo4j_id == fid,
        )
    ).scalar_one_or_none()
    if row:
        row.quiz_rating = rating
    else:
        db.add(FragranceRating(user_id=user_id, fragrance_neo4j_id=fid, quiz_rating=rating))


def _recommendations_payload(result: dict) -> dict:
    """Wrap a dispatcher result into the shared response envelope."""
    return {
        "status": "success",
        "data": [FragranceRecommendation(**r) for r in result["recommendations"]],
        "state": result["state"],
        "state_label": result["state_label"],
        "source": result["source"],
    }


@router.post("/rate", response_model=StandardResponse)
def submit_fragrance_rating(
    request: FragranceRatingInput,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> StandardResponse:
    """Persist a single rating (auth required)."""
    try:
        _upsert_rating(db, user_id, request.fragrance_id, request.rating)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Rating persist error for user %s: %s", user_id, exc)
        raise HTTPException(status_code=500, detail="Failed to save rating") from exc
    return {"status": "success", "data": {"status": "saved"}}


@router.post("/batch-rate", response_model=StandardResponse)
def submit_batch_ratings(
    request: BatchRatingRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> StandardResponse:
    """Persist many ratings at once (auth required)."""
    try:
        for r in request.ratings:
            _upsert_rating(db, user_id, r.fragrance_id, r.rating)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Batch rating persist error for user %s: %s", user_id, exc)
        raise HTTPException(status_code=500, detail="Failed to sync batch ratings") from exc
    return {"status": "success", "data": {"status": "saved", "count": len(request.ratings)}}


@router.post("/guest")
def get_guest_recommendations(request: GuestRecommendationBody) -> dict:
    """Route a guest's ratings through the 3-state dispatcher (no auth)."""
    _ensure_embeddings()
    if request.quiz_submitted is not None:
        quiz_submitted = bool(request.quiz_submitted)
    else:
        quiz_submitted = request.quiz_confidence is not None

    dispatch_request = SimpleNamespace(
        ratings=request.ratings,
        quiz_submitted=quiz_submitted,
        candidate_count=CANDIDATE_COUNT,
    )
    result = _dispatcher.dispatch(dispatch_request)
    return _recommendations_payload(result)


@router.get("/personalized")
def get_personalized_recommendations(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    """Recommendations for an authed user from their stored ratings."""
    _ensure_embeddings()
    saved = db.execute(
        select(FragranceRating).where(FragranceRating.user_id == user_id)
    ).scalars().all()
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()

    ratings = [
        FragranceRatingInput(
            fragrance_id=_normalize_id(str(r.fragrance_neo4j_id)),
            rating=r.quiz_rating or 5.0,
        )
        for r in saved
        if r.quiz_rating is not None
    ]
    quiz_submitted = bool(user is not None and user.quiz_completed_at is not None)

    dispatch_request = SimpleNamespace(
        ratings=ratings,
        quiz_submitted=quiz_submitted,
        candidate_count=CANDIDATE_COUNT,
    )
    result = _dispatcher.dispatch(dispatch_request)
    return _recommendations_payload(result)