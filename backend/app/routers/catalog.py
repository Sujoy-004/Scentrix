"""Fragrance catalog endpoints (single source: the cleaned JSON SSOT).

Provides:
- GET /fragrances/catalog — paginated, filterable, sortable catalog listing
- GET /fragrances/{id}    — single fragrance detail

No Neo4j, no semantic /search, no interaction ingestion.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas.schemas import StandardResponse
from app.services.catalog import _normalize_id, get_catalog as get_catalog_rows

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fragrances", tags=["fragrances"])


def _as_list(value: Any) -> list[str]:
    """Coerce a notes/accords cell (list or comma-string) to a clean str list."""
    if value is None:
        return []
    if isinstance(value, str):
        raw = [item.strip() for item in value.split(",") if item.strip()]
    else:
        raw = list(value)
    return [str(item).strip() for item in raw if item and str(item).strip()]


def _row_to_item(row: dict[str, Any], match_score: float | None = None) -> dict[str, Any]:
    """Project one hydrated catalog row into the catalog/detail response shape.

    Fields satisfy both the minimal spec (id, name, brand, accords, top_notes,
    description, rating_count, rating_value, gender_label, year, concentration)
    and what the frontend FragranceCard reads (family, top_accords, rating,
    image_url, match_score).
    """
    accords = _as_list(row.get("accords"))
    rating_value = row.get("rating_value")
    return {
        "id": str(row.get("id", "")),
        "name": str(row.get("name", "") or ""),
        "brand": str(row.get("brand", "") or "Unknown"),
        "family": accords[0] if accords else "Unknown",
        "year": row.get("year"),
        "concentration": str(row.get("concentration", "") or "N/A"),
        "gender_label": str(row.get("gender_label", "") or "N/A"),
        "description": str(row.get("description", "") or ""),
        "top_notes": _as_list(row.get("top_notes")),
        "middle_notes": _as_list(row.get("middle_notes")),
        "base_notes": _as_list(row.get("base_notes")),
        "accords": accords,
        "top_accords": accords[:3],
        "rating": float(rating_value) if rating_value is not None else None,
        "rating_count": int(row.get("rating_count") or 0),
        "rating_value": float(rating_value) if rating_value is not None else None,
        "image_url": row.get("image_url"),
        "match_score": match_score,
    }


def _matches_text(value: str, query: str) -> bool:
    return query in value.lower()


def _filter_rows(
    rows: list[dict[str, Any]],
    *,
    q: str | None,
    brand: str | None,
    family: str | None,
    accord: str | None,
) -> list[tuple[dict[str, Any], float]]:
    """Apply filters; returns (row, match_score) pairs so q-ranking survives sort."""
    query_norm = (q or "").strip().lower()
    brand_norm = (brand or "").strip().lower()
    family_norm = (family or accord or "").strip().lower()

    results: list[tuple[dict[str, Any], float]] = []
    for row in rows:
        name = str(row.get("name", "") or "")
        brand_name = str(row.get("brand", "") or "")
        description = str(row.get("description", "") or "")
        top_notes = _as_list(row.get("top_notes"))
        middle_notes = _as_list(row.get("middle_notes"))
        base_notes = _as_list(row.get("base_notes"))
        accords = _as_list(row.get("accords"))

        if brand_norm and not _matches_text(brand_name, brand_norm):
            continue

        if family_norm:
            if not any(family_norm in a.lower() for a in accords):
                continue

        if not query_norm:
            results.append((row, 0.0))
            continue

        haystack = [name.lower(), brand_name.lower(), description.lower()]
        haystack.extend(n.lower() for n in top_notes)
        haystack.extend(n.lower() for n in middle_notes)
        haystack.extend(n.lower() for n in base_notes)
        haystack.extend(a.lower() for a in accords)

        query_terms = query_norm.split()
        if not query_terms:
            continue
        match_count = sum(1 for term in query_terms if any(term in chunk for chunk in haystack))
        if match_count == 0:
            continue
        match_score = round((match_count / len(query_terms)) * 100.0, 1)
        results.append((row, match_score))

    return results


def _apply_sort(items: list[tuple[dict[str, Any], float]], sort: str | None) -> None:
    if sort == "name":
        items.sort(key=lambda item: str(item[0].get("name", "") or "").lower())
    elif sort == "newest":
        items.sort(key=lambda item: item[0].get("year") or 0, reverse=True)
    elif sort == "rating":
        items.sort(key=lambda item: item[0].get("rating_value") or 0.0, reverse=True)
    elif sort == "match":
        items.sort(key=lambda item: item[1], reverse=True)
    else:  # "popular" (default)
        items.sort(key=lambda item: item[0].get("rating_count") or 0, reverse=True)


@router.get("/catalog", response_model=StandardResponse)
def get_catalog(
    q: str | None = Query(None, min_length=1, max_length=100),
    brand: str | None = Query(None),
    family: str | None = Query(None),
    accord: str | None = Query(None),
    sort: str | None = Query(None, pattern="^(popular|name|newest|rating|match)$"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
) -> StandardResponse:
    """Paginated catalog listing with search, filters, sort and pagination."""
    rows = get_catalog_rows()
    if not rows:
        return {"status": "success", "data": {"items": [], "total": 0, "limit": limit, "offset": offset}}

    matched = _filter_rows(rows, q=q, brand=brand, family=family, accord=accord)

    if q:
        # q ranking is the primary order; only re-sort when a non-match sort is requested
        if sort and sort != "match":
            _apply_sort(matched, sort)
        else:
            _apply_sort(matched, "match")
    else:
        _apply_sort(matched, sort or "popular")

    total = len(matched)

    effective_limit = page_size or limit
    if page is not None:
        effective_offset = (page - 1) * effective_limit
    else:
        effective_offset = offset

    page_rows = matched[effective_offset : effective_offset + effective_limit]
    items = [_row_to_item(row, match_score=score) for row, score in page_rows]

    return {
        "status": "success",
        "data": {
            "items": items,
            "total": total,
            "limit": effective_limit,
            "offset": effective_offset,
        },
    }


@router.get("/{fragrance_id}", response_model=StandardResponse)
def get_fragrance_detail(fragrance_id: str) -> StandardResponse:
    """Return a single fragrance by its canonical ``frag_`` id."""
    normalized = _normalize_id(fragrance_id)
    catalog_map = {str(item["id"]): item for item in get_catalog_rows()}
    row = catalog_map.get(normalized) or catalog_map.get(fragrance_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Fragrance not found")
    return {"status": "success", "data": _row_to_item(row)}