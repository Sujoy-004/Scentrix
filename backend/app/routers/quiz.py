"""Adaptive quiz session endpoints.

Scaffolds a confidence-aware onboarding quiz flow that starts with 8
questions and extends only when confidence is low.
"""

from __future__ import annotations

import logging
import random
from collections import defaultdict
from datetime import UTC, datetime
from statistics import pstdev
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_id, get_optional_user_id
from app.database import get_session
from app.limiter import limiter
from app.models.models import FragranceRating
from app.schemas.schemas import (
    QuizConfidenceComponents,
    QuizQuestion,
    QuizSessionEvaluateRequest,
    QuizSessionEvaluateResponse,
    QuizSessionNextQuestionsResponse,
    QuizSessionRules,
    QuizSessionStartRequest,
    QuizSessionStartResponse,
    QuizSessionSubmitResponseRequest,
    QuizSessionSubmitResponseResponse,
)
from app.services.catalog import load_recommendation_catalog
from app.services.quiz_store import (
    create_quiz_session,
    get_quiz_session,
    quiz_expiry_utc,
    save_quiz_session,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fragrances/quiz/session", tags=["quiz"])

CONFIDENCE_THRESHOLD = 0.72
MEDIUM_BAND_THRESHOLD = 0.58
DEFAULT_START_COUNT = 10
DEFAULT_MEDIUM_EXTENSION = 3
DEFAULT_LOW_EXTENSION = 5
DEFAULT_MAX_TOTAL = 16


def _question_from_row(row: dict) -> QuizQuestion:
    raw_notes = row.get("top_notes") or []
    raw_accords = row.get("accords") or []

    # Industrial Sanitizer: Handle strings or lists gracefully
    if isinstance(raw_notes, str):
        raw_notes = [n.strip() for n in raw_notes.split(",")]
    if isinstance(raw_accords, str):
        raw_accords = [a.strip() for a in raw_accords.split(",")]

    return QuizQuestion(
        fragrance_id=str(row.get("id", "")),
        name=str(row.get("name", "Unknown")),
        brand=str(row.get("brand", "Unknown")),
        top_notes=[str(v) for v in raw_notes if v and str(v).strip()][:4],
        accords=[str(v) for v in raw_accords if v and str(v).strip()][:4],
    )


def _confidence_band(score: float) -> str:
    if score >= CONFIDENCE_THRESHOLD:
        return "high"
    if score >= MEDIUM_BAND_THRESHOLD:
        return "medium"
    return "low"


def _normalize_rating_0_to_5(rating_1_to_10: float) -> float:
    return round(max(0.0, min(5.0, rating_1_to_10 / 2.0)), 2)


def _safe_float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _select_seed_questions(rows: list[dict], count: int) -> list[dict]:
    if not rows:
        return []

    # Olfactive Kingdoms: The 18 pillars of modern perfumery for full spectrum coverage
    KINGDOMS = {
        "citrus": ["citrus", "lemon", "bergamot", "orange", "lime", "grapefruit", "yuzu"],
        "floral": ["floral", "rose", "jasmine", "white floral", "tuberose", "iris", "violet"],
        "oriental": ["oriental", "amber", "vanilla", "spicy", "cinnamon", "balsamic", "resin"],
        "woody": ["woody", "sandalwood", "cedar", "patchouli", "vetiver", "oud", "guaiac"],
        "aromatic": ["aromatic", "lavender", "herbal", "mint", "sage", "rosemary", "fougere"],
        "chypre": ["chypre", "oakmoss", "earthy", "mossy", "patchouli"],
        "leather": ["leather", "smoky", "tobacco", "animalic", "castoreum"],
        "gourmand": ["gourmand", "sweet", "chocolate", "caramel", "honey", "pudding", "vanilla"],
        "marine": ["marine", "aquatic", "sea water", "ozonic", "salt", "calone"],
        "green": ["green", "grass", "leafy", "galbanum", "tea", "bamboo"],
        "fruity": ["fruity", "berry", "apple", "peach", "pear", "plum", "cherry"],
        "animalic": ["animalic", "musk", "civet", "castoreum", "ambergris", "dirty"],
        "powdery": ["powdery", "iris", "orris", "talc", "rice", "heliotrope"],
        "musky": ["musk", "white musk", "clean musk", "laundry"],
        "spicy_warm": ["warm spicy", "cinnamon", "clove", "cardamom", "nutmeg"],
        "spicy_fresh": ["fresh spicy", "pink pepper", "ginger", "coriander", "juniper"],
    }

    random.shuffle(rows)
    selected: list[dict] = []
    filled_kingdoms: set[str] = set()
    used_ids: set[str] = set()

    # Priority 1: Randomized Kingdom Coverage (1 item per kingdom, picked randomly from the 18)
    # Shuffling the kingdoms list ensures that different sessions cover different families.
    kingdom_list = list(KINGDOMS.items())
    random.shuffle(kingdom_list)

    for kingdom_name, keywords in kingdom_list:
        if len(selected) >= count:
            break

        for row in rows:
            row_id = str(row.get("id", ""))
            if row_id in used_ids:
                continue

            accords = [str(a).lower() for a in (row.get("accords") or [])]
            notes = [
                str(n).lower()
                for n in (row.get("top_notes") or [])
                + (row.get("middle_notes") or [])
                + (row.get("base_notes") or [])
            ]
            traits = accords + notes

            # Check if this fragrance fits the kingdom and doesn't overlap too much with already filled ones
            if any(k in traits for k in keywords):
                # Exclusive Selection: Does this row belong to ANY kingdom we already filled?
                already_covered = False
                for prev_k in filled_kingdoms:
                    if any(k in traits for k in KINGDOMS[prev_k]):
                        already_covered = True
                        break

                if not already_covered or len(selected) < 4:
                    selected.append(row)
                    used_ids.add(row_id)
                    filled_kingdoms.add(kingdom_name)
                    break

    # Priority 2: Fill remaining slots with Greedy Diversity (Brand/Accord variation)
    if len(selected) < count:
        seen_brands: set[str] = {str(r.get("brand", "")).lower() for r in selected}
        for row in rows:
            if len(selected) >= count:
                break
            row_id = str(row.get("id", ""))
            if row_id in used_ids:
                continue

            brand = str(row.get("brand", "")).lower()
            if brand not in seen_brands:
                selected.append(row)
                used_ids.add(row_id)
                seen_brands.add(brand)

    # Priority 3: Hard Fallback (Random Fill)
    if len(selected) < count:
        for row in rows:
            if len(selected) >= count:
                break
            row_id = str(row.get("id", ""))
            if row_id not in used_ids:
                selected.append(row)
                used_ids.add(row_id)

    return selected[:count]


def _build_confidence_components(
    session_payload: dict, catalog_by_id: dict[str, dict]
) -> QuizConfidenceComponents:
    responses = session_payload.get("responses") or []
    total_answered = len(responses)

    if total_answered == 0:
        return QuizConfidenceComponents(stability=0.0, margin=0.0, consistency=0.0, coverage=0.0)

    ratings = [_safe_float(item.get("rating_1_to_10")) for item in responses]

    stability = min(total_answered / 12.0, 1.0)
    margin = min(0.45 + (total_answered * 0.04), 1.0)

    if len(ratings) < 2:
        consistency = 0.55
    else:
        consistency = max(0.0, 1.0 - min(pstdev(ratings) / 4.0, 1.0))

    unique_accords: set[str] = set()
    for item in responses:
        fragrance_id = str(item.get("fragrance_id", ""))
        row = catalog_by_id.get(fragrance_id)
        if not row:
            continue
        for accord in row.get("accords") or []:
            value = str(accord).strip().lower()
            if value:
                unique_accords.add(value)

    coverage = min(len(unique_accords) / 10.0, 1.0)

    return QuizConfidenceComponents(
        stability=round(stability, 4),
        margin=round(margin, 4),
        consistency=round(consistency, 4),
        coverage=round(coverage, 4),
    )


def _compute_confidence_score(components: QuizConfidenceComponents) -> float:
    score = (
        (0.35 * components.stability)
        + (0.25 * components.margin)
        + (0.20 * components.consistency)
        + (0.20 * components.coverage)
    )
    return round(max(0.0, min(1.0, score)), 4)


def _to_rules_payload(session_payload: dict) -> QuizSessionRules:
    config = session_payload.get("config") or {}
    return QuizSessionRules(
        min_core_questions=int(config.get("min_core_questions", 8)),
        max_total_questions=int(config.get("max_total_questions", DEFAULT_MAX_TOTAL)),
        medium_extension=int(config.get("medium_extension", DEFAULT_MEDIUM_EXTENSION)),
        low_extension=int(config.get("low_extension", DEFAULT_LOW_EXTENSION)),
        confidence_threshold=float(config.get("confidence_threshold", CONFIDENCE_THRESHOLD)),
    )


async def _load_seen_ids(user_id: int, session: AsyncSession) -> set[str]:
    result = await session.execute(
        select(FragranceRating.fragrance_neo4j_id).where(FragranceRating.user_id == user_id)
    )
    return {str(row[0]) for row in result.all() if row and row[0]}


def _require_owned_session(session_payload: dict | None, session_id: str, user_id: int) -> dict:
    if session_payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz session not found")

    owner_id = int(session_payload.get("user_id") or 0)
    if owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this quiz session",
        )

    if str(session_payload.get("session_id", "")) != session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz session not found")

    return session_payload


@router.post("/start", response_model=QuizSessionStartResponse)
@limiter.limit("30/minute")
async def start_quiz_session(
    quiz_data: QuizSessionStartRequest,
    request: Request,
    user_id: int | None = Depends(get_optional_user_id),
    session: AsyncSession = Depends(get_session),
) -> QuizSessionStartResponse:
    effective_user_id = user_id if user_id is not None else 0
    catalog = load_recommendation_catalog()
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation catalog unavailable",
        )

    candidate_rows = [row for row in catalog if str(row.get("id", "")).strip()]

    if quiz_data.filters.exclude_seen and user_id:
        seen_ids = await _load_seen_ids(user_id, session)
        filtered = [row for row in candidate_rows if str(row.get("id", "")) not in seen_ids]
        if filtered:
            candidate_rows = filtered

    rng = random.Random(f"quiz:{effective_user_id}:{uuid4().hex}")
    if len(candidate_rows) > quiz_data.candidate_pool_size:
        candidate_rows = rng.sample(candidate_rows, quiz_data.candidate_pool_size)

    seed_rows = _select_seed_questions(candidate_rows, quiz_data.seed_count)
    if not seed_rows:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to initialize quiz session",
        )

    session_id = f"qz_{uuid4().hex[:8]}"
    now_iso = datetime.now(UTC).isoformat()
    rules = QuizSessionRules(
        min_core_questions=quiz_data.seed_count,
        max_total_questions=DEFAULT_MAX_TOTAL,
        medium_extension=DEFAULT_MEDIUM_EXTENSION,
        low_extension=DEFAULT_LOW_EXTENSION,
        confidence_threshold=CONFIDENCE_THRESHOLD,
    )

    seed_questions = [_question_from_row(row) for row in seed_rows]
    seed_ids = [question.fragrance_id for question in seed_questions]

    payload = {
        "session_id": session_id,
        "user_id": user_id,
        "created_at": now_iso,
        "updated_at": now_iso,
        "config": rules.model_dump(),
        "seed_question_ids": seed_ids,
        "served_ids": seed_ids,
        "responses": [],
        "confidence_score": None,
        "confidence_band": None,
        "low_gain_streak": 0,
        "stop_reason": None,
    }

    try:
        await create_quiz_session(session_id=session_id, payload=payload)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Quiz session store unavailable: {exc}",
        ) from exc

    return QuizSessionStartResponse(
        session_id=session_id,
        seed_questions=seed_questions,
        rules=rules,
        expires_at=quiz_expiry_utc(),
    )


@router.post("/{session_id}/answer", response_model=QuizSessionSubmitResponseResponse)
@limiter.limit("20/minute")
async def submit_quiz_answer(
    session_id: str,
    quiz_data: QuizSessionSubmitResponseRequest,
    request: Request,
    user_id: int | None = Depends(get_optional_user_id),
    db_session: AsyncSession = Depends(get_session),
) -> QuizSessionSubmitResponseResponse:
    effective_user_id = user_id if user_id is not None else 0
    session_payload = _require_owned_session(
        await get_quiz_session(session_id), session_id, effective_user_id
    )

    served_ids = [str(v) for v in (session_payload.get("served_ids") or [])]
    if quiz_data.fragrance_id not in served_ids:
        served_ids.append(quiz_data.fragrance_id)

    responses = [
        item for item in (session_payload.get("responses") or []) if isinstance(item, dict)
    ]

    normalized = _normalize_rating_0_to_5(quiz_data.rating_1_to_10)
    response_payload = {
        "fragrance_id": quiz_data.fragrance_id,
        "rating_1_to_10": round(quiz_data.rating_1_to_10, 2),
        "rating_0_to_5": normalized,
        "source": quiz_data.source,
        "created_at": datetime.now(UTC).isoformat(),
    }

    replaced = False
    for index, item in enumerate(responses):
        if str(item.get("fragrance_id", "")) == quiz_data.fragrance_id:
            responses[index] = response_payload
            replaced = True
            break

    if not replaced:
        responses.append(response_payload)

    session_payload["served_ids"] = served_ids
    session_payload["responses"] = responses
    session_payload["updated_at"] = datetime.now(UTC).isoformat()

    try:
        await save_quiz_session(session_id=session_id, payload=session_payload)

        # BRIDGE: Sync to permanent database for authenticated users
        if user_id:
            neo4j_id = quiz_data.fragrance_id.replace("frag_syn_", "").replace("frag_", "")
            existing = await db_session.execute(
                select(FragranceRating).where(
                    FragranceRating.user_id == user_id,
                    FragranceRating.fragrance_neo4j_id == neo4j_id,
                )
            )
            row = existing.scalar_one_or_none()
            if row:
                row.quiz_rating = quiz_data.rating_1_to_10
            else:
                db_session.add(
                    FragranceRating(
                        user_id=user_id,
                        fragrance_neo4j_id=neo4j_id,
                        quiz_rating=quiz_data.rating_1_to_10,
                    )
                )
            await db_session.commit()

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Quiz session store unavailable: {exc}",
        ) from exc

    return QuizSessionSubmitResponseResponse(
        accepted=True,
        normalized_rating_0_to_5=normalized,
        answers_count=len(responses),
    )


@router.post("/{session_id}/finalize")
async def finalize_quiz_session(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, int | str]:
    """Bridge transient quiz session data to permanent profile table."""
    session_payload = _require_owned_session(
        await get_quiz_session(session_id), session_id, user_id
    )
    responses = session_payload.get("responses") or []

    if not responses:
        return {"status": "no_data"}

    from sqlalchemy.dialects.postgresql import insert

    from app.models.models import FragranceRating

    for res in responses:
        fid = str(res.get("fragrance_id", "")).replace("frag_syn_", "").replace("frag_", "")
        rating = float(res.get("rating_1_to_10") or 0)

        stmt = (
            insert(FragranceRating)
            .values(user_id=user_id, fragrance_neo4j_id=fid, quiz_rating=rating)
            .on_conflict_do_update(
                index_elements=["user_id", "fragrance_neo4j_id"], set_={"quiz_rating": rating}
            )
        )
        await db.execute(stmt)

    await db.commit()
    logger.info(
        f"Quiz Session {session_id} finalized for user {user_id}. {len(responses)} ratings synced."
    )
    return {"status": "synced", "count": len(responses)}


@router.post("/{session_id}/evaluate", response_model=QuizSessionEvaluateResponse)
async def evaluate_quiz_session(
    session_id: str,
    request: QuizSessionEvaluateRequest,
    user_id: int | None = Depends(get_optional_user_id),
) -> QuizSessionEvaluateResponse:
    effective_user_id = user_id if user_id is not None else 0
    session_payload = _require_owned_session(
        await get_quiz_session(session_id), session_id, effective_user_id
    )

    catalog = load_recommendation_catalog()
    catalog_by_id = {
        str(row.get("id", "")): row for row in catalog if str(row.get("id", "")).strip()
    }

    responses = [
        item for item in (session_payload.get("responses") or []) if isinstance(item, dict)
    ]
    total_answered = len(responses)

    rules = _to_rules_payload(session_payload)
    components = _build_confidence_components(session_payload, catalog_by_id)
    confidence_score = _compute_confidence_score(components)
    confidence_band = _confidence_band(confidence_score)

    previous_score_raw = session_payload.get("confidence_score")
    previous_score = float(previous_score_raw) if previous_score_raw is not None else None

    low_gain_streak = int(session_payload.get("low_gain_streak") or 0)
    if previous_score is not None:
        if (confidence_score - previous_score) < 0.02:
            low_gain_streak += 1
        else:
            low_gain_streak = 0

    extension_required = False
    additional_questions_target = 0
    stop_reason: str | None = None

    if total_answered < rules.min_core_questions and not request.force:
        stop_reason = "core_incomplete"
    elif confidence_score >= rules.confidence_threshold:
        stop_reason = "confidence_threshold_met"
    elif total_answered >= rules.max_total_questions:
        stop_reason = "hard_cap_reached"
    elif low_gain_streak >= 2 and total_answered > rules.min_core_questions:
        stop_reason = "low_marginal_gain"
    else:
        if confidence_band == "medium":
            additional_questions_target = rules.medium_extension
        elif confidence_band == "low":
            additional_questions_target = rules.low_extension

        remaining_budget = max(rules.max_total_questions - total_answered, 0)
        additional_questions_target = min(additional_questions_target, remaining_budget)
        extension_required = additional_questions_target > 0

        if not extension_required:
            stop_reason = "no_remaining_budget"

    session_payload["confidence_score"] = confidence_score
    session_payload["confidence_band"] = confidence_band
    session_payload["confidence_components"] = components.model_dump()
    session_payload["low_gain_streak"] = low_gain_streak
    session_payload["stop_reason"] = stop_reason
    session_payload["updated_at"] = datetime.now(UTC).isoformat()

    try:
        await save_quiz_session(session_id=session_id, payload=session_payload)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Quiz session store unavailable: {exc}",
        ) from exc

    return QuizSessionEvaluateResponse(
        confidence_score=confidence_score,
        confidence_band=confidence_band,
        extension_required=extension_required,
        additional_questions_target=additional_questions_target,
        total_answered=total_answered,
        stop_reason=stop_reason,
        components=components,
    )


@router.get("/{session_id}/next-questions", response_model=QuizSessionNextQuestionsResponse)
async def get_next_quiz_questions(
    session_id: str,
    count: int = Query(3, ge=1, le=5),
    user_id: int | None = Depends(get_optional_user_id),
) -> QuizSessionNextQuestionsResponse:
    effective_user_id = user_id if user_id is not None else 0
    session_payload = _require_owned_session(
        await get_quiz_session(session_id), session_id, effective_user_id
    )

    catalog = load_recommendation_catalog()
    if not catalog:
        return QuizSessionNextQuestionsResponse(questions=[], count=0)

    responses = [
        item for item in (session_payload.get("responses") or []) if isinstance(item, dict)
    ]
    served_ids = {str(v) for v in (session_payload.get("served_ids") or [])}
    response_ids = {
        str(item.get("fragrance_id", "")) for item in responses if item.get("fragrance_id")
    }
    blocked_ids = served_ids.union(response_ids)

    catalog_by_id = {
        str(row.get("id", "")): row for row in catalog if str(row.get("id", "")).strip()
    }

    seen_brands = {
        str(catalog_by_id[rid].get("brand", "")).strip().lower()
        for rid in response_ids
        if rid in catalog_by_id
    }

    answered_accords: set[str] = set()
    accord_weights: dict[str, float] = defaultdict(float)
    for item in responses:
        rid = str(item.get("fragrance_id", ""))
        row = catalog_by_id.get(rid)
        if not row:
            continue
        weight = max(0.0, _safe_float(item.get("rating_0_to_5")) / 5.0)
        for accord in row.get("accords") or []:
            value = str(accord).strip().lower()
            if not value:
                continue
            answered_accords.add(value)
            accord_weights[value] += weight

    max_accord_weight = max(accord_weights.values()) if accord_weights else 0.0

    scored: list[tuple[float, dict]] = []
    for row in catalog:
        row_id = str(row.get("id", "")).strip()
        if not row_id or row_id in blocked_ids:
            continue

        brand = str(row.get("brand", "")).strip().lower()
        accords = [str(v).strip().lower() for v in (row.get("accords") or []) if str(v).strip()]

        if accords and max_accord_weight > 0:
            preference = sum(
                (accord_weights.get(a, 0.0) / max_accord_weight) for a in accords
            ) / len(accords)
        else:
            preference = 0.5

        uncertainty = 1.0 - abs(preference - 0.5) * 2.0

        brand_diversity = 0.0 if (brand and brand in seen_brands) else 1.0
        if accords:
            unseen_accords = [a for a in accords if a not in answered_accords]
            accord_diversity = len(unseen_accords) / len(accords)
        else:
            accord_diversity = 0.5

        diversity = (0.6 * brand_diversity) + (0.4 * accord_diversity)

        review_count = _safe_float(row.get("review_count"))
        view_count = _safe_float(row.get("view_count"))
        popularity_score = _safe_float(row.get("popularity_score"))
        engagement = min(
            (review_count / 1000.0) + (view_count / 50000.0) + (popularity_score / 100.0), 1.0
        )

        # Neural Scent Graph priority: Uncertainty (60%), Diversity (30%), Engagement (10%)
        total_score = (0.6 * uncertainty) + (0.3 * diversity) + (0.1 * engagement)
        scored.append((total_score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    chosen_rows = [row for _, row in scored[:count]]
    questions = [_question_from_row(row) for row in chosen_rows]

    if questions:
        merged_served = list(served_ids.union({question.fragrance_id for question in questions}))
        session_payload["served_ids"] = merged_served
        session_payload["updated_at"] = datetime.now(UTC).isoformat()
        try:
            await save_quiz_session(session_id=session_id, payload=session_payload)
        except Exception as exc:
            # Silently log errors for guests (Quiz Session store is non-critical for guest flow)
            logger.error(f"Quiz Pulse Error: {exc}")

    return QuizSessionNextQuestionsResponse(questions=questions, count=len(questions))
