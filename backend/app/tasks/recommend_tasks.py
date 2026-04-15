"""Celery tasks for recommendation generation and ML inference.

T2.6: Async recommendation job processing via Celery.
"""

import asyncio
import logging
import math
import random
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from celery import Task
from sqlalchemy import select

from app.celery_app import celery_app
from app.database import async_session_maker
from app.models.models import FragranceRating
from app.services.catalog import load_recommendation_catalog

logger = logging.getLogger(__name__)


FEATURE_TERMS = {
    "woody": {"woody", "wood", "cedar", "sandalwood", "vetiver", "oud", "oakmoss", "patchouli"},
    "floral": {"floral", "rose", "jasmine", "violet", "peony", "tuberose", "neroli", "orange blossom"},
    "citrus": {"citrus", "bergamot", "lemon", "orange", "grapefruit", "mandarin", "neroli"},
    "spicy": {"spicy", "pepper", "cardamom", "ginger", "cinnamon", "clove", "nutmeg", "saffron"},
    "fresh": {"fresh", "green", "aromatic", "aldehydes", "herbal", "lavender"},
    "gourmand": {"vanilla", "caramel", "tonka", "almond", "coffee", "praline", "sweet"},
    "smoky": {"smoky", "smoke", "incense", "leather", "tobacco", "myrrh", "frankincense"},
    "aquatic": {"aquatic", "marine", "sea", "ozonic", "salt", "driftwood", "water"},
}

EXTRA_FEATURE_DIM = 12
VECTOR_DIM = len(FEATURE_TERMS) + EXTRA_FEATURE_DIM


def _load_catalog() -> list[dict[str, Any]]:
    """Load merged catalog: large canonical primary + seed fallback."""
    return load_recommendation_catalog()


def _split_train_val_test(
    rows: Sequence[Any],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> dict[str, list[Any]]:
    """Deterministically split rows into train/val/test partitions."""
    if not rows:
        return {"train": [], "val": [], "test": []}

    indices = list(range(len(rows)))
    random.Random(seed).shuffle(indices)

    train_count = int(len(rows) * train_ratio)
    val_count = int(len(rows) * val_ratio)

    if len(rows) >= 3:
        train_count = max(train_count, 1)
        val_count = max(val_count, 1)
        test_count = len(rows) - train_count - val_count
        if test_count <= 0:
            test_count = 1
            if train_count >= val_count and train_count > 1:
                train_count -= 1
            elif val_count > 1:
                val_count -= 1
    else:
        # Sparse history fallback: always retain at least one training row.
        train_count = max(train_count, 1)
        val_count = 0

    train_ids = indices[:train_count]
    val_ids = indices[train_count : train_count + val_count]
    test_ids = indices[train_count + val_count :]

    return {
        "train": [rows[idx] for idx in train_ids],
        "val": [rows[idx] for idx in val_ids],
        "test": [rows[idx] for idx in test_ids],
    }


def _tokenize(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", value.lower()))


def _fragrance_tokens(fragrance: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    tokens.update(_tokenize(str(fragrance.get("id", "") or "")))
    for key in ("name", "brand", "description"):
        tokens.update(_tokenize(str(fragrance.get(key, "") or "")))

    tokens.update(_tokenize(str(fragrance.get("year", "") or "")))
    tokens.update(_tokenize(str(fragrance.get("concentration", "") or "")))
    tokens.update(_tokenize(str(fragrance.get("gender_label", "") or "")))

    for key in ("top_notes", "middle_notes", "base_notes", "accords"):
        values = fragrance.get(key, []) or []
        if isinstance(values, list):
            for item in values:
                tokens.update(_tokenize(str(item)))
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


def _fragrance_feature_vector(fragrance: dict[str, Any]) -> list[float]:
    tokens = _fragrance_tokens(fragrance)
    vector: list[float] = []
    for terms in FEATURE_TERMS.values():
        hits = sum(1 for term in terms if term in tokens) if tokens else 0
        vector.append(hits / max(len(terms), 1))

    top_notes = fragrance.get("top_notes", []) or []
    middle_notes = fragrance.get("middle_notes", []) or []
    base_notes = fragrance.get("base_notes", []) or []
    accords = fragrance.get("accords", []) or []

    name_tokens = _tokenize(str(fragrance.get("name", "") or ""))
    brand_tokens = _tokenize(str(fragrance.get("brand", "") or ""))
    desc_tokens = _tokenize(str(fragrance.get("description", "") or ""))
    gender_m, gender_f, gender_u = _encode_gender(fragrance.get("gender_label"))

    vector.extend(
        [
            _normalize_year(fragrance.get("year")),
            _normalize_concentration(fragrance.get("concentration")),
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

    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _weighted_average(vectors: Sequence[Sequence[float]], weights: Sequence[float]) -> list[float]:
    if not vectors:
        return [0.0] * VECTOR_DIM

    total_weight = sum(max(weight, 0.0) for weight in weights)
    if total_weight <= 0:
        return [0.0] * VECTOR_DIM

    out = [0.0] * len(vectors[0])
    for vector, weight in zip(vectors, weights, strict=False):
        safe_weight = max(weight, 0.0)
        for idx, value in enumerate(vector):
            out[idx] += value * safe_weight

    return [value / total_weight for value in out]


async def _fetch_user_ratings_async(user_id: int) -> list[FragranceRating]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(FragranceRating).where(FragranceRating.user_id == user_id)
        )
        return list(result.scalars().all())


def _fetch_user_ratings(user_id: int) -> list[FragranceRating]:
    """Load user ratings in Celery context while tolerating unavailable DB dependencies."""
    try:
        return asyncio.run(_fetch_user_ratings_async(user_id))
    except RuntimeError:
        # Fallback for environments where an event loop is already active.
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_fetch_user_ratings_async(user_id))
        finally:
            loop.close()
    except Exception as exc:
        logger.warning("Unable to fetch ratings for user %s: %s", user_id, exc)
        return []


def _serialize_recommendation(
    fragrance: dict[str, Any],
    score: float,
    reason: str,
) -> dict[str, Any]:
    top_notes = [
        str(note).strip()
        for note in (fragrance.get("top_notes") or [])
        if str(note).strip()
    ]
    accords = [
        str(accord).strip()
        for accord in (fragrance.get("accords") or [])
        if str(accord).strip()
    ]

    review_count_value = fragrance.get("review_count")
    review_count = None
    if isinstance(review_count_value, (int, float)):
        review_count = float(review_count_value)

    return {
        "id": str(fragrance.get("id", "")),
        "name": str(fragrance.get("name", "Unknown")),
        "brand": str(fragrance.get("brand", "Unknown")),
        "top_notes": top_notes,
        "top_accords": accords[:3],
        "similarity_score": round(score, 4),
        "match_score": round(max(0.0, min(100.0, score * 100.0)), 1),
        "review_count": review_count,
        "reason": reason,
    }


def _build_user_taste_vector(
    rating_rows: Sequence[FragranceRating],
    catalog_by_id: dict[str, dict[str, Any]],
) -> list[float]:
    vectors: list[list[float]] = []
    weights: list[float] = []
    for row in rating_rows:
        fragrance = catalog_by_id.get(str(row.fragrance_neo4j_id))
        if fragrance is None:
            continue
        vectors.append(_fragrance_feature_vector(fragrance))
        weights.append(float(max(row.overall_satisfaction, 0.0) + 0.1))

    return _weighted_average(vectors, weights)


def _rank_by_text(
    query: str,
    catalog: Sequence[dict[str, Any]],
    user_taste_vector: Sequence[float] | None,
    limit: int,
) -> list[dict[str, Any]]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    ranked: list[tuple[float, dict[str, Any], str]] = []
    for fragrance in catalog:
        fragrance_tokens = _fragrance_tokens(fragrance)
        overlap = len(query_tokens.intersection(fragrance_tokens))
        lexical_score = overlap / max(len(query_tokens), 1)

        profile_bonus = 0.0
        if user_taste_vector is not None:
            profile_bonus = _cosine_similarity(
                list(user_taste_vector),
                _fragrance_feature_vector(fragrance),
            )

        score = (0.8 * lexical_score) + (0.2 * profile_bonus)
        if score <= 0:
            continue

        reason = "Text semantic overlap"
        if user_taste_vector is not None and profile_bonus > 0.2:
            reason = "Text match plus user taste alignment"

        ranked.append((score, fragrance, reason))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        _serialize_recommendation(fragrance=item[1], score=item[0], reason=item[2])
        for item in ranked[:limit]
    ]


def _rank_by_profile(
    catalog: Sequence[dict[str, Any]],
    user_taste_vector: Sequence[float],
    rated_ids: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    ranked: list[tuple[float, dict[str, Any], str]] = []
    for fragrance in catalog:
        frag_id = str(fragrance.get("id", ""))
        if frag_id in rated_ids:
            continue

        vector_score = _cosine_similarity(user_taste_vector, _fragrance_feature_vector(fragrance))
        popularity = float(fragrance.get("review_count") or fragrance.get("popularity_score") or 0.0)
        popularity_score = min(popularity / 1000.0, 1.0)
        final_score = (0.9 * vector_score) + (0.1 * popularity_score)
        if final_score <= 0:
            continue

        ranked.append((final_score, fragrance, "User taste vector similarity"))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        _serialize_recommendation(fragrance=item[1], score=item[0], reason=item[2])
        for item in ranked[:limit]
    ]


class CallbackTask(Task):
    """Task with callbacks for tracking completion."""

    def on_success(self, retval, task_id, args, kwargs):
        """Success callback."""
        logger.info(f"Task {task_id} completed successfully")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Retry callback."""
        logger.warning(f"Task {task_id} retrying due to: {exc}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Failure callback."""
        logger.error(f"Task {task_id} failed: {exc}")


@celery_app.task(
    base=CallbackTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.tasks.recommend_by_text",
)
def recommend_by_text_task(
    self,
    job_id: str,
    query: str,
    limit: int = 10,
    user_id: int | None = None,
) -> dict:
    """Generate text-based fragrance recommendations using lexical+profile ranking."""
    try:
        logger.info(f"[{job_id}] Starting text-based recommendation for: {query[:50]}")

        catalog = _load_catalog()
        catalog_split = _split_train_val_test(catalog, seed=7)
        logger.info(
            "[%s] Catalog split train=%s val=%s test=%s",
            job_id,
            len(catalog_split["train"]),
            len(catalog_split["val"]),
            len(catalog_split["test"]),
        )

        user_taste_vector: list[float] | None = None
        if user_id:
            logger.info("[%s] Building user taste vector for user=%s", job_id, user_id)
            ratings = _fetch_user_ratings(user_id)
            rating_split = _split_train_val_test(
                sorted(ratings, key=lambda row: row.created_at or datetime.min),
                seed=17,
            )
            catalog_by_id = {str(item.get("id", "")): item for item in catalog}
            user_taste_vector = _build_user_taste_vector(rating_split["train"], catalog_by_id)

        ranked = _rank_by_text(query=query, catalog=catalog, user_taste_vector=user_taste_vector, limit=limit)

        logger.info(f"[{job_id}] Recommendation complete. {len(ranked)} results.")
        return {
            "job_id": job_id,
            "status": "completed",
            "fragrances": ranked,
            "generated_at": datetime.now(UTC).isoformat(),
            "split": {
                "train": len(catalog_split["train"]),
                "val": len(catalog_split["val"]),
                "test": len(catalog_split["test"]),
            },
        }

    except Exception as exc:
        logger.error(f"[{job_id}] Recommendation task failed: {exc}")
        self.retry(exc=exc)


@celery_app.task(
    base=CallbackTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.tasks.recommend_by_profile",
)
def recommend_by_profile_task(
    self,
    job_id: str,
    user_id: int,
    limit: int = 10,
) -> dict:
    """Generate user-profile recommendations with split-aware taste modeling."""
    try:
        logger.info(f"[{job_id}] Starting profile-based recommendation for user {user_id}")

        user_ratings = _fetch_user_ratings(user_id)
        interaction_split = _split_train_val_test(
            sorted(user_ratings, key=lambda row: row.created_at or datetime.min),
            seed=23,
        )

        catalog = _load_catalog()
        catalog_by_id = {str(item.get("id", "")): item for item in catalog}
        user_vector = _build_user_taste_vector(interaction_split["train"], catalog_by_id)
        rated_ids = {str(row.fragrance_neo4j_id) for row in user_ratings}

        recommendations = _rank_by_profile(
            catalog=catalog,
            user_taste_vector=user_vector,
            rated_ids=rated_ids,
            limit=limit,
        )

        logger.info(f"[{job_id}] Recommendation complete. {len(recommendations)} results.")
        return {
            "job_id": job_id,
            "status": "completed",
            "fragrances": recommendations,
            "generated_at": datetime.now(UTC).isoformat(),
            "split": {
                "train": len(interaction_split["train"]),
                "val": len(interaction_split["val"]),
                "test": len(interaction_split["test"]),
            },
        }

    except Exception as exc:
        logger.error(f"[{job_id}] Profile recommendation task failed: {exc}")
        self.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    name="app.tasks.generate_user_embeddings",
)
def generate_user_embeddings_task(
    self,
    user_id: int,
) -> dict:
    """Generate and cache user taste vector embeddings.

    Called periodically for each user who has rated fragrances.
    Caches result in Redis for fast access during recommendations.

    Args:
        user_id: User ID for whom to generate embeddings

    Returns:
        Dictionary with task status and embedding shape
    """
    try:
        logger.info(f"Generating embeddings for user {user_id}...")

        catalog = _load_catalog()
        catalog_by_id = {str(item.get("id", "")): item for item in catalog}
        rating_rows = _fetch_user_ratings(user_id)
        split = _split_train_val_test(rating_rows, seed=31)
        taste_vector = _build_user_taste_vector(split["train"], catalog_by_id)

        return {
            "status": "completed",
            "user_id": user_id,
            "embedding_dim": len(taste_vector),
            "history_count": len(rating_rows),
            "split": {
                "train": len(split["train"]),
                "val": len(split["val"]),
                "test": len(split["test"]),
            },
        }

    except Exception as exc:
        logger.error(f"Embedding generation failed for user {user_id}: {exc}")
        self.retry(exc=exc)


@celery_app.task(
    base=CallbackTask,
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    name="app.tasks.rebuild_embeddings",
)
def rebuild_embeddings_task(self) -> dict:
    """Rebuild text and graph embeddings from the current seed dataset."""
    try:
        fragrances = load_recommendation_catalog(force_reload=True)
        if not fragrances:
            raise FileNotFoundError("Merged recommendation catalog is empty")

        # Lazy imports to avoid forcing ML deps on API startup.
        from ml.models.graph_sage import GraphEmbedder
        from ml.models.text_encoder import TextEncoder

        text_encoder = TextEncoder()
        text_encoder.process_and_upload(fragrances)

        graph_embedder = GraphEmbedder()
        graph_embedder.generate_and_upload(fragrances)

        return {
            "status": "completed",
            "processed": len(fragrances),
        }
    except Exception as exc:
        logger.error(f"Embedding rebuild task failed: {exc}")
        self.retry(exc=exc)
