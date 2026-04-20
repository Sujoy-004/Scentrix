"""T2.4: Fragrance search and recommendation endpoints.

Provides endpoints for:
- Get fragrance details by ID
- Search fragrances by name, brand, accords
- Text-based recommendation queries (async)
- User-profile-based recommendations (async)
"""

import json
import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_id, get_optional_user_id
from app.celery_app import celery_app
from app.config import settings
from app.database import get_session
from app.models.models import UserInteractionEvent
from app.routers.recommendations import get_encoder
from app.schemas.schemas import (
    FragranceAccord,
    FragranceCatalogItem,
    FragranceCatalogPage,
    FragranceDetail,
    FragranceNote,
    FragranceSearchResult,
    RecommendationInteractionBatchRequest,
    RecommendationInteractionBatchResponse,
    RecommendationJob,
    RecommendationResult,
    RecommendationWeeklyMetrics,
    TextRecommendationRequest,
)
from app.services.catalog import load_recommendation_catalog
from app.services.hybrid_search import recommender
from app.services.job_store import create_job, get_job, is_job_timed_out, update_job
from app.tasks.recommend_tasks import recommend_by_profile_task, recommend_by_text_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fragrances", tags=["fragrances"])


def _matches_text(value: str, query: str) -> bool:
    return query in value.lower()


def _catalog_filtered_rows_from_list(
    rows: list[dict[str, Any]],
    *,
    query: str | None = None,
    brand: str | None = None,
    family: str | None = None,
    concentration: str | None = None,
) -> list[dict[str, Any]]:
    query_norm = (query or "").strip().lower()
    brand_norm = (brand or "").strip().lower()
    family_norm = (family or "").strip().lower()
    concentration_norm = (concentration or "").strip().lower()

    filtered: list[dict[str, Any]] = []
    for row in rows:
        # existing filter logic ... (copying from original)
        name = str(row.get("name", "") or "")
        brand_name = str(row.get("brand", "") or "")
        description = str(row.get("description", "") or "")
        top_notes = row.get("top_notes") or []
        accords = row.get("accords") or []
        middle_notes = row.get("middle_notes") or []
        base_notes = row.get("base_notes") or []

        if isinstance(top_notes, str):
            top_notes = [n.strip() for n in top_notes.split(",")]
        if isinstance(accords, str):
            accords = [a.strip() for a in accords.split(",")]
        if isinstance(middle_notes, str):
            middle_notes = [n.strip() for n in middle_notes.split(",")]
        if isinstance(base_notes, str):
            base_notes = [n.strip() for n in base_notes.split(",")]

        top_notes = [str(n).strip() for n in top_notes if n and str(n).strip()]
        accords = [str(a).strip() for a in accords if a and str(a).strip()]
        middle_notes = [str(n).strip() for n in middle_notes if n and str(n).strip()]
        base_notes = [str(n).strip() for n in base_notes if n and str(n).strip()]
        concentration_value = str(row.get("concentration", "") or "")

        if brand_norm and not _matches_text(brand_name, brand_norm):
            continue

        if family_norm:
            # Synchronized with UI: Only show if it's one of the top 2 visible accords.
            family_hit = any(family_norm in accord.lower() for accord in accords[:2])
            if not family_hit:
                continue

        if concentration_norm and concentration_norm != "all":
            if concentration_norm not in concentration_value.lower():
                continue

        if query_norm:
            haystack = [name.lower(), brand_name.lower(), description.lower()]
            haystack.extend([note.lower() for note in top_notes])
            haystack.extend([note.lower() for note in middle_notes])
            haystack.extend([note.lower() for note in base_notes])
            haystack.extend([accord.lower() for accord in accords])

            query_terms = query_norm.split()
            if not query_terms:
                continue

            # Calculate intersection depth
            match_count = sum(1 for term in query_terms if any(term in chunk for chunk in haystack))

            # Exclusion: If nothing matches, skip
            if match_count == 0:
                continue

            # Fuzzy Logic: If multi-term, we allow partial matches but weight them lower
            # A 100% term match always wins.
            match_score = (match_count / len(query_terms)) * 100.0

            # Update row data for sorting later
            row_match_score = match_score
        else:
            row_match_score = 0.0

        filtered.append(
            {
                "id": str(row.get("id", "")),
                "name": name,
                "brand": brand_name or "Unknown",
                "year": row.get("year"),
                "concentration": concentration_value or "N/A",
                "gender_label": str(row.get("gender_label", "N/A") or "N/A"),
                "top_notes": top_notes,
                "middle_notes": middle_notes,
                "base_notes": base_notes,
                "accords": accords,
                "rating": row.get("rating", 0.0),
                "match_score": row_match_score,
            }
        )

    # Sort: Prioritize match_score (weighted fuzzy), then brand/name
    filtered.sort(key=lambda item: (-item["match_score"], item["brand"].lower(), item["name"].lower(), item["id"]))
    return filtered


def _catalog_filtered_rows(**kwargs: Any) -> list[dict[str, Any]]:
    rows = load_recommendation_catalog()
    return _catalog_filtered_rows_from_list(rows, **kwargs)


def _catalog_row_to_detail(row: dict[str, Any], fragrance_id: str) -> FragranceDetail:
    top_notes = [
        FragranceNote(id=f"{fragrance_id}:top:{idx}", name=note, category="top")
        for idx, note in enumerate(row.get("top_notes", []))
    ]
    middle_notes = [
        FragranceNote(id=f"{fragrance_id}:middle:{idx}", name=note, category="middle")
        for idx, note in enumerate(row.get("middle_notes", []))
    ]
    base_notes = [
        FragranceNote(id=f"{fragrance_id}:base:{idx}", name=note, category="base")
        for idx, note in enumerate(row.get("base_notes", []))
    ]
    accords = [
        FragranceAccord(id=f"{fragrance_id}:accord:{idx}", name=accord)
        for idx, accord in enumerate(row.get("accords", []))
    ]

    return FragranceDetail(
        id=row.get("id", fragrance_id),
        name=row.get("name", "Unknown"),
        brand=row.get("brand", "Unknown"),
        year=row.get("year"),
        concentration=row.get("concentration", "N/A"),
        gender_label=row.get("gender_label", "N/A"),
        description=row.get("description", ""),
        top_notes=top_notes,
        middle_notes=middle_notes,
        base_notes=base_notes,
        accords=accords,
        similarity_score=None,
    )


def _safe_pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 1)


def _parse_context_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}




def get_graph_client():
    """Lazy initialize neo4j client"""
    try:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
        from ml.graph.neo4j_client import get_neo4j, init_neo4j

        try:
            return get_neo4j()
        except RuntimeError:
            return init_neo4j(
                settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
            )
    except Exception as exc:
        logger.error(f"Neo4j client init failed: {exc}")
        return None


@router.get("/catalog", response_model=FragranceCatalogPage)
async def get_catalog(
    q: str | None = Query(None, min_length=1, max_length=100),
    brand: str | None = Query(None),
    family: str | None = Query(None),
    concentration: str | None = Query(None),
    limit: int = Query(24, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str | None = Query(None),
) -> FragranceCatalogPage:
    from app.services.catalog import load_recommendation_catalog_async

    all_rows = await load_recommendation_catalog_async()

    # Process filtering in memory (already loaded as a list)
    rows = _catalog_filtered_rows_from_list(
        all_rows,
        query=q,
        brand=brand,
        family=family,
        concentration=concentration,
    )

    # Apply Sorting logic (Metadata is now pre-hydrated in catalog.py)
    if family:
        # Prioritize results where the selected family is the PRIMARY accord
        # Uses substring matching to catch "Warm Spicy", "Fresh Spicy", etc.
        def family_relevance(x):
            accords = [a.lower() for a in x.get("accords", [])]
            for i, accord in enumerate(accords):
                if family.lower() in accord:
                    return i
            return 999

        rows.sort(key=family_relevance)
    elif sort == "rating":
        rows.sort(key=lambda x: x.get("rating", 0.0), reverse=True)
    elif sort == "match":
        rows.sort(key=lambda x: x.get("match_score", 0.0), reverse=True)
    elif sort == "name":
        rows.sort(key=lambda x: str(x.get("name", "")).lower())

    total = len(rows)
    page_rows = rows[offset : offset + limit]

    items: list[FragranceCatalogItem] = []
    for row in page_rows:
        accords_value = row.get("accords") or []
        items.append(
            FragranceCatalogItem(
                id=row["id"],
                name=row["name"],
                brand=row["brand"],
                family=accords_value[0] if accords_value else "Unknown",
                year=row.get("year"),
                concentration=row.get("concentration", "N/A"),
                gender_label=row.get("gender_label", "N/A"),
                description="",  # Performance optimization
                top_notes=row.get("top_notes", []),
                middle_notes=row.get("middle_notes", []),
                base_notes=row.get("base_notes", []),
                accords=row.get("accords", []),
                rating=row["rating"],
                match_score=row["match_score"],
            )
        )

    return FragranceCatalogPage(items=items, total=total, limit=limit, offset=offset)


@router.get("", response_model=list[FragranceSearchResult])
async def list_fragrances(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    brand: str | None = Query(None),
    user_id: int | None = Depends(get_optional_user_id),
) -> list[FragranceSearchResult]:
    """List fragrances with lightweight pagination and optional brand filter."""
    client = get_graph_client()
    if not client:
        fallback_rows = _catalog_filtered_rows(brand=brand)
        page_rows = fallback_rows[offset : offset + limit]
        return [
            FragranceSearchResult(
                id=row["id"],
                name=row["name"],
                brand=row["brand"],
                year=row.get("year"),
                top_accords=row.get("accords", [])[:3],
                similarity_score=None,
            )
            for row in page_rows
        ]

    where_clause = ""
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if brand:
        where_clause = "WHERE toLower(f.brand) CONTAINS toLower($brand)"
        params["brand"] = brand

    query = f"""
    MATCH (f:Fragrance)
    {where_clause}
    OPTIONAL MATCH (f)-[:BELONGS_TO_ACCORD]->(a:Accord)
    RETURN f, collect(distinct a.name) as accords
    SKIP $offset
    LIMIT $limit
    """

    try:
        results = client.execute_query(query, params)
        if results:
            return [
                FragranceSearchResult(
                    id=r["f"].get("id"),
                    name=r["f"].get("name"),
                    brand=r["f"].get("brand", "Unknown"),
                    year=r["f"].get("year"),
                    top_accords=list(r["accords"])[:3],
                    similarity_score=None,
                )
                for r in results
            ]

        fallback_rows = _catalog_filtered_rows(brand=brand)
        page_rows = fallback_rows[offset : offset + limit]
        return [
            FragranceSearchResult(
                id=row["id"],
                name=row["name"],
                brand=row["brand"],
                year=row.get("year"),
                top_accords=row.get("accords", [])[:3],
                similarity_score=None,
            )
            for row in page_rows
        ]
    except Exception as e:
        logger.error(f"List fragrances query failed: {e}")
        fallback_rows = _catalog_filtered_rows(brand=brand)
        page_rows = fallback_rows[offset : offset + limit]
        return [
            FragranceSearchResult(
                id=row["id"],
                name=row["name"],
                brand=row["brand"],
                year=row.get("year"),
                top_accords=row.get("accords", [])[:3],
                similarity_score=None,
            )
            for row in page_rows
        ]


@router.get("/search", response_model=list[FragranceSearchResult])
async def search_fragrances(
    q: str | None = Query(None, min_length=1, max_length=100),
    brand: str | None = Query(None),
    accord: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    user_id: int | None = Depends(get_optional_user_id),
) -> list[FragranceSearchResult]:
    """Search fragrances by name, brand, or accord."""
    client = get_graph_client()
    if not client:
        fallback_rows = _catalog_filtered_rows(query=q, brand=brand, family=accord)
        return [
            FragranceSearchResult(
                id=row["id"],
                name=row["name"],
                brand=row["brand"],
                year=row.get("year"),
                top_accords=row.get("accords", [])[:3],
                similarity_score=None,
            )
            for row in fallback_rows[:limit]
        ]

    # Simplified graph search
    conditions = []
    params: dict[str, Any] = {"limit": limit}

    if q:
        # User-centric Search Sanitization: handle space/hyphen interchangeability
        sanitized_q = q.replace(" ", "-").lower()
        conditions.append(
            "(toLower(f.name) CONTAINS $q_orig OR toLower(f.name) CONTAINS $q_sanitized)"
        )
        params["q_orig"] = q.lower()
        params["q_sanitized"] = sanitized_q
    if brand:
        conditions.append("toLower(f.brand) CONTAINS toLower($brand)")
        params["brand"] = brand

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
    MATCH (f:Fragrance)
    {where_clause}
    OPTIONAL MATCH (f)-[:BELONGS_TO_ACCORD]->(a:Accord)
    RETURN f, collect(distinct a.name) as accords
    LIMIT $limit
    """

    keyword_results = []
    try:
        results = client.execute_query(query, params)
        if results:
            for r in results:
                keyword_results.append(
                    FragranceSearchResult(
                        id=r["f"].get("id"),
                        name=r["f"].get("name"),
                        brand=r["f"].get("brand", "Unknown"),
                        year=r["f"].get("year"),
                        top_accords=list(r["accords"])[:3],
                        match_score=98.0,
                        reason="Keyword Match",
                    )
                )
    except Exception as e:
        logger.error(f"Keyword search failed: {e}")

    # Phase 2: Semantic Discovery (Neural Pass)
    semantic_results = []
    if q and len(q.split()) > 0:
        try:
            # Generate vector for the query via the SentenceTransformer
            encoder = get_encoder()
            if encoder:
                query_vec = encoder.generate_embeddings([q])[0]
                # Use HybridRecommender for the niche 'mood' match
                raw_semantic = recommender.get_recommendations(query_vec, [])

                for r in raw_semantic:
                    # Deduplication: Don't repeat keyword matches
                    if any(k.id == r["id"] for k in keyword_results):
                        continue
                    semantic_results.append(FragranceSearchResult(**r))
        except Exception as e:
            logger.debug(f"Semantic search failed or bypassed: {e}")

    # Fusion and Ranking: Prioritize Keywords, then Neural Vibes
    combined = keyword_results + semantic_results

    if combined:
        return combined[:limit]

    # Extreme Fallback for Cold Cache
    fallback_rows = _catalog_filtered_rows(query=q, brand=brand, family=accord)
    return [
        FragranceSearchResult(
            id=row["id"],
            name=row["name"],
            brand=row["brand"],
            year=row.get("year"),
            top_accords=row.get("accords", [])[:3],
            match_score=50.0,
            reason="Cold Index Map",
        )
        for row in fallback_rows[:limit]
    ]


@router.post("/recommend/text", response_model=RecommendationJob)
async def recommend_by_text(
    request: TextRecommendationRequest,
    user_id: int = Depends(get_current_user_id),
) -> RecommendationJob:
    """Generate recommendation from text description (async job).

    Uses Sentence-BERT to encode the text query and returns top-10 similar fragrances
    based on description embeddings and user taste vector (if authenticated).

    Args:
        request: Text query and limit (default 10)
        user_id: Optional authenticated user for personalized scoring
        session: Database session

    Returns:
        RecommendationJob with job_id and processing status
    """
    job_id = str(uuid4())

    try:
        await create_job(job_id=job_id, user_id=user_id, status="processing", query=request.query)
    except RuntimeError as exc:
        logger.error("Redis unavailable while creating recommendation job %s: %s", job_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation store unavailable",
        ) from exc

    logger.info(f"Created recommendation job {job_id} for query: {request.query[:50]}")

    try:
        async_task = recommend_by_text_task.delay(
            job_id=job_id,
            query=request.query,
            limit=request.limit,
            user_id=user_id,
        )
        await update_job(
            job_id, celery_task_id=async_task.id, message="Recommendation generation started"
        )
    except Exception as exc:
        logger.error(f"Failed to enqueue text recommendation task for {job_id}: {exc}")
        await update_job(
            job_id,
            status="failed",
            error=str(exc),
            message="Recommendation queue unavailable",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation queue unavailable",
        ) from exc

    return RecommendationJob(
        job_id=job_id,
        status="processing",
        message="Recommendation generation started",
    )


@router.post(
    "/recommend/interactions",
    response_model=RecommendationInteractionBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_recommendation_interactions(
    request: RecommendationInteractionBatchRequest,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> RecommendationInteractionBatchResponse:
    """Ingest recommendation interaction events for learning and analytics loops."""
    accepted = 0

    for event in request.events:
        context = dict(event.context)
        if event.match_score is not None:
            context.setdefault("match_score", event.match_score)
        if event.confidence_tier is not None:
            context.setdefault("confidence_tier", event.confidence_tier)
        if event.availability:
            context.setdefault("availability", event.availability)

        interaction_value = event.interaction_value
        if (
            interaction_value is None
            and event.interaction_type == "impression"
            and event.match_score is not None
        ):
            interaction_value = event.match_score

        session.add(
            UserInteractionEvent(
                user_id=user_id,
                fragrance_neo4j_id=event.fragrance_id,
                interaction_type=event.interaction_type,
                interaction_value=interaction_value,
                source=event.source,
                context_json=json.dumps(context, ensure_ascii=False),
            )
        )
        accepted += 1

    await session.commit()
    return RecommendationInteractionBatchResponse(accepted=accepted, rejected=0)


@router.get("/{fragrance_id}", response_model=FragranceDetail)
async def get_fragrance_detail(
    fragrance_id: str,
    user_id: int | None = Depends(get_optional_user_id),
) -> FragranceDetail:
    """Get fragrance detail including notes, accords, and similarity to user profile."""
    client = get_graph_client()
    if not client:
        fallback_match = next(
            (row for row in _catalog_filtered_rows() if row["id"] == fragrance_id), None
        )
        if fallback_match is not None:
            return _catalog_row_to_detail(fallback_match, fragrance_id)
        raise HTTPException(status_code=404, detail="Fragrance not found")

    query = """
    MATCH (f:Fragrance {id: $frag_id})
    OPTIONAL MATCH (f)-[r:HAS_NOTE]->(n:Note)
    OPTIONAL MATCH (f)-[a:BELONGS_TO_ACCORD]->(ac:Accord)
    WITH f, r, n, ac
    OPTIONAL MATCH (f)-[s:SIMILAR_TO]-(other:Fragrance)
    RETURN f,
           collect(distinct {note: n.name, type: type(r), category: n.category}) as notes,
           collect(distinct ac.name) as accords,
           collect(distinct {id: other.id, name: other.name, brand: other.brand, score: s.score})[0..5] as neighbors
    """
    try:
        results = client.execute_query(query, {"frag_id": fragrance_id})
        if not results:
            fallback_match = next(
                (row for row in _catalog_filtered_rows() if row["id"] == fragrance_id), None
            )
            if fallback_match is not None:
                return _catalog_row_to_detail(fallback_match, fragrance_id)
            raise HTTPException(status_code=404, detail="Fragrance not found")

        record = results[0]
        f_node = record["f"]

        # Parse notes
        top, mid, base = [], [], []
        for n in record["notes"]:
            if n.get("note"):
                note_cat = n.get("category", "").lower()
                n_obj = FragranceNote(id=n["note"], name=n["note"], category=note_cat)
                if "top" in note_cat:
                    top.append(n_obj)
                elif "mid" in note_cat:
                    mid.append(n_obj)
                else:
                    base.append(n_obj)

        # Parse accords
        accords = [FragranceAccord(id=a, name=a) for a in record["accords"] if a]

        # Parse neighbors
        neighbors = []
        for n in record.get("neighbors", []):
            if n.get("id"):
                neighbors.append(
                    FragranceSearchResult(
                        id=n["id"],
                        name=n["name"] or "Unknown",
                        brand=n["brand"] or "Unknown",
                        match_score=float(n["score"] * 100) if n.get("score") else 0.0,
                    )
                )

        return FragranceDetail(
            id=f_node.get("id", fragrance_id),
            name=f_node.get("name", "Unknown"),
            brand=f_node.get("brand", "Unknown"),
            year=f_node.get("year", None),
            concentration=f_node.get("concentration", "EDP"),
            gender_label=f_node.get("gender_label", "N/A"),
            description=f_node.get("description", ""),
            top_notes=top,
            middle_notes=mid,
            base_notes=base,
            accords=accords,
            neighbors=neighbors,
            similarity_score=None,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Graph query failed: {exc}")
        fallback_match = next(
            (row for row in _catalog_filtered_rows() if row["id"] == fragrance_id), None
        )
        if fallback_match is not None:
            return _catalog_row_to_detail(fallback_match, fragrance_id)
        raise HTTPException(status_code=500, detail="Database error") from exc


@router.get("/recommend/metrics/weekly", response_model=RecommendationWeeklyMetrics)
async def get_recommendation_weekly_metrics(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> RecommendationWeeklyMetrics:
    """Return a 7-day recommendation quality dashboard for the current user."""
    cutoff_naive = (datetime.now(UTC) - timedelta(days=7)).replace(tzinfo=None)

    from sqlalchemy import select

    result = await session.execute(
        select(UserInteractionEvent).where(
            UserInteractionEvent.user_id == user_id,
            UserInteractionEvent.created_at >= cutoff_naive,
        )
    )
    rows = list(result.scalars().all())

    def _count(event_type: str) -> int:
        return sum(1 for row in rows if row.interaction_type == event_type)

    impressions = [row for row in rows if row.interaction_type == "impression"]
    impression_count = len(impressions)
    detail_clicks = _count("click_detail")
    similar_clicks = _count("click_similar")
    wishlist_adds = _count("wishlist_add")
    purchases = _count("purchase")

    match_scores: list[float] = []
    low_conf_impressions = 0
    stock_known_impressions = 0
    high_impressions = 0
    low_impressions = 0

    for row in impressions:
        context = _parse_context_json(row.context_json)

        if isinstance(row.interaction_value, (int, float)):
            score = float(row.interaction_value)
            if 0.0 <= score <= 100.0:
                match_scores.append(score)

        tier = str(context.get("confidence_tier", "")).lower()
        if tier == "low":
            low_conf_impressions += 1
            low_impressions += 1
        elif tier == "high":
            high_impressions += 1

        availability_known = context.get("availability_known")
        if isinstance(availability_known, bool):
            if availability_known:
                stock_known_impressions += 1
        else:
            availability = str(context.get("availability", "")).strip().lower()
            if availability and availability not in {"n/a", "na", "unknown", "none"}:
                stock_known_impressions += 1

    high_clicks = 0
    low_clicks = 0
    for row in rows:
        if row.interaction_type not in {"click_detail", "click_similar"}:
            continue
        tier = str(_parse_context_json(row.context_json).get("confidence_tier", "")).lower()
        if tier == "high":
            high_clicks += 1
        elif tier == "low":
            low_clicks += 1

    avg_match_score = round(sum(match_scores) / len(match_scores), 1) if match_scores else None
    clicks_total = detail_clicks + similar_clicks
    high_ctr = _safe_pct(high_clicks, high_impressions)
    low_ctr = _safe_pct(low_clicks, low_impressions)

    return RecommendationWeeklyMetrics(
        window_days=7,
        impressions=impression_count,
        detail_clicks=detail_clicks,
        similar_clicks=similar_clicks,
        wishlist_adds=wishlist_adds,
        purchases=purchases,
        avg_match_score=avg_match_score,
        low_confidence_share_pct=_safe_pct(low_conf_impressions, impression_count),
        click_through_rate_pct=_safe_pct(clicks_total, impression_count),
        wishlist_rate_pct=_safe_pct(wishlist_adds, impression_count),
        conversion_rate_pct=_safe_pct(purchases, impression_count),
        stock_coverage_pct=_safe_pct(stock_known_impressions, impression_count),
        high_vs_low_ctr_delta_pct=round(high_ctr - low_ctr, 1),
    )


@router.get("/recommend/{job_id}", response_model=RecommendationResult | RecommendationJob)
async def get_recommendation_result(
    job_id: str,
    user_id: int | None = Depends(get_optional_user_id),
) -> RecommendationResult | RecommendationJob:
    """Poll async recommendation job result.

    Args:
        job_id: Job ID from recommend endpoint

    Returns:
        RecommendationResult if complete, RecommendationJob if processing

    Raises:
        HTTPException: 404 if job not found
    """
    try:
        job = await get_job(job_id)
    except RuntimeError as exc:
        logger.error("Redis unavailable while loading recommendation job %s: %s", job_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation store unavailable",
        ) from exc

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    effective_user_id = user_id if user_id is not None else 0
    if job.get("user_id") != effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this job",
        )

    if job["status"] in {"processing", "queued"} and job.get("celery_task_id"):
        result = AsyncResult(job["celery_task_id"], app=celery_app)
        if result.successful():
            payload = result.result if isinstance(result.result, dict) else {}
            generated_at = payload.get("generated_at")
            if not isinstance(generated_at, str):
                generated_at = datetime.now(UTC).isoformat()

            await update_job(
                job_id,
                status="completed",
                results=payload.get("fragrances", []),
                generated_at=generated_at,
                message="Recommendation generation completed",
                error=None,
            )
            job = await get_job(job_id) or job
        elif result.failed():
            await update_job(
                job_id,
                status="failed",
                error=str(result.result),
                message="Recommendation generation failed",
            )
            job = await get_job(job_id) or job
        else:
            if is_job_timed_out(job.get("created_at")):
                await update_job(
                    job_id,
                    status="timed_out",
                    error="Recommendation job timed out",
                    message="Recommendation job timed out while waiting for worker completion",
                )
                job = await get_job(job_id) or job
            else:
                await update_job(
                    job_id, status="processing", message=f"Worker state: {result.state}"
                )
                job = await get_job(job_id) or job

    if job["status"] in {"processing", "queued"}:
        return RecommendationJob(
            job_id=job_id,
            status=job["status"],
            message=job.get("message") or "Still generating recommendations...",
        )
    elif job["status"] == "completed":
        generated_at = job.get("generated_at")
        if isinstance(generated_at, str) and generated_at:
            try:
                parsed_generated_at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            except ValueError:
                parsed_generated_at = datetime.now(UTC)
        else:
            parsed_generated_at = datetime.now(UTC)

        return RecommendationResult(
            job_id=job_id,
            status="completed",
            fragrances=job["results"] or [],
            generated_at=parsed_generated_at,
            message=job.get("message") or "",
        )
    elif job["status"] in {"failed", "timed_out", "expired"}:
        error_status = (
            status.HTTP_504_GATEWAY_TIMEOUT
            if job["status"] == "timed_out"
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(
            status_code=error_status,
            detail=job.get("error", "Recommendation generation failed"),
        )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unknown job state",
    )


@router.post("/recommend/profile", response_model=RecommendationJob)
async def recommend_by_profile(
    limit: int = Query(10, ge=1, le=50),
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> RecommendationJob:
    """Generate recommendations based on user's fragrance ratings (async job).

    Requires authentication. Uses user's taste vector built from their ratings
    to personalize recommendations via Bayesian Personalized Ranking (BPR).

    Args:
        limit: Max recommendations to return
        user_id: Current authenticated user
        session: Database session

    Returns:
        RecommendationJob with job_id and processing status

    Raises:
        HTTPException: 401 if user not authenticated
    """
    job_id = str(uuid4())

    try:
        await create_job(job_id=job_id, user_id=user_id, status="processing", query=None)
    except RuntimeError as exc:
        logger.error(
            "Redis unavailable while creating profile recommendation job %s: %s", job_id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation store unavailable",
        ) from exc

    logger.info(f"Created profile recommendation job {job_id} for user {user_id}")

    try:
        async_task = recommend_by_profile_task.delay(
            job_id=job_id,
            user_id=user_id,
            limit=limit,
        )
        await update_job(
            job_id, celery_task_id=async_task.id, message="Generating personalized recommendations"
        )
    except Exception as exc:
        logger.error(f"Failed to enqueue profile recommendation task for {job_id}: {exc}")
        await update_job(
            job_id,
            status="failed",
            error=str(exc),
            message="Recommendation queue unavailable",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation queue unavailable",
        ) from exc

    return RecommendationJob(
        job_id=job_id,
        status="processing",
        message="Generating personalized recommendations...",
    )
