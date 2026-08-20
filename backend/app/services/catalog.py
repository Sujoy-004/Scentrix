"""Catalog service — loads the cleaned fragrance SSOT from local JSON.

Single source of truth: ``backend/app/data/scentrix_master_cleaned.json``
(4,559 items). No Neo4j, no async loading, no config dependency.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "scentrix_master_cleaned.json"

_catalog_cache: list[dict[str, Any]] | None = None
_catalog_map_cache: dict[str, dict[str, Any]] | None = None
_load_lock = threading.Lock()


def _normalize_id(raw_id: str) -> str:
    """Return the canonical ``frag_``-prefixed form of a fragrance ID.

    The catalog and the GraphSAGE node index both key fragrances as
    ``frag_<brand>_<name>_<year>``. Ratings persisted before the prefix
    convention are canonicalised via this helper.
    """
    if not raw_id or not raw_id.strip():
        return raw_id
    if raw_id.startswith("frag_"):
        return raw_id
    return f"frag_{raw_id}"


def _hydrate(row: dict[str, Any]) -> dict[str, Any]:
    """Add derived lookups and safe numeric coercion to one catalog row."""
    all_notes = (
        (row.get("top_notes") or [])
        + (row.get("middle_notes") or [])
        + (row.get("base_notes") or [])
    )
    row["_notes_set"] = {str(n).lower() for n in all_notes if n}
    row["_accords_set"] = {str(a).lower() for a in (row.get("accords") or []) if a}

    rating_count = row.get("rating_count")
    row["rating_count"] = int(rating_count) if rating_count is not None else 0
    rating_value = row.get("rating_value")
    row["rating_value"] = float(rating_value) if rating_value is not None else 3.5

    return row


def get_catalog(force_reload: bool = False) -> list[dict[str, Any]]:
    """Return the hydrated catalog, loading from JSON once and caching."""
    global _catalog_cache, _catalog_map_cache
    if _catalog_cache is not None and not force_reload:
        return _catalog_cache

    with _load_lock:
        if _catalog_cache is not None and not force_reload:
            return _catalog_cache

        if not _CATALOG_PATH.is_file():
            logger.error("Catalog SSOT not found: %s", _CATALOG_PATH)
            _catalog_cache = []
            _catalog_map_cache = {}
            return _catalog_cache

        try:
            with open(_CATALOG_PATH, encoding="utf-8") as f:
                rows = json.load(f)
            catalog = [_hydrate(row) for row in rows]
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to load catalog SSOT: %s", exc)
            catalog = []

        _catalog_cache = catalog
        _catalog_map_cache = {str(item["id"]): item for item in catalog}
        logger.info("Loaded %d fragrances from %s", len(catalog), _CATALOG_PATH)
        return _catalog_cache


def get_catalog_map() -> dict[str, dict[str, Any]]:
    """Return {str(id): item} for every catalog item."""
    if _catalog_map_cache is None:
        get_catalog()
    return _catalog_map_cache or {}


def load_recommendation_catalog(force_reload: bool = False) -> list[dict[str, Any]]:
    """Backward-compatible alias for ``get_catalog``."""
    return get_catalog(force_reload=force_reload)