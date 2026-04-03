"""Catalog loading utilities that combine large canonical and small seed datasets."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

def _candidate_roots() -> list[Path]:
    roots: list[Path] = []

    env_root = os.getenv("SCENTSCAPE_REPO_ROOT")
    if env_root:
        roots.append(Path(env_root).resolve())

    roots.append(Path(__file__).resolve().parents[3])
    roots.append(Path.cwd())

    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(root)
    return deduped


def _catalog_path_candidates() -> tuple[list[Path], list[Path]]:
    primary: list[Path] = []
    fallback: list[Path] = []

    # Check environment variable first (SSOT Lock)
    env_data_path = os.getenv("SCENTSCAPE_DATA_PATH")
    
    for root in _candidate_roots():
        if env_data_path:
            # If absolute, use it; if relative, join it with root
            p = Path(env_data_path)
            primary.append(p if p.is_absolute() else root / p)
        
        # Always prioritize Elite file locally
        primary.append(root / "ml" / "data" / "fra_elite_5k.json")
        
        # Fallback for continuity
        fallback.append(root / "ml" / "data" / "seed_fragrances.json")

    return primary, fallback

_catalog_cache: list[dict[str, Any]] | None = None


def _load_json_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
    except Exception as exc:  # pragma: no cover - defensive path
        logger.warning("Failed to load catalog file %s: %s", path, exc)
    return []


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    if 1800 <= year <= 2100:
        return year
    return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            text = _safe_text(item)
            if text:
                out.append(text)
        return out

    text = _safe_text(value)
    if not text:
        return []

    for delimiter in ("|", ";", ",", " / ", "/"):
        if delimiter in text:
            return [_safe_text(part) for part in text.split(delimiter) if _safe_text(part)]

    return [text]


def _stable_id(name: str, brand: str, year: int | None, concentration: str) -> str:
    raw = f"{name}|{brand}|{year or ''}|{concentration}".lower().encode("utf-8")
    digest = hashlib.sha1(raw).hexdigest()[:16]
    return f"frag_{digest}"


def _normalize_record(raw: dict[str, Any]) -> dict[str, Any] | None:
    name = _safe_text(raw.get("name"))
    brand = _safe_text(raw.get("brand"), "Unknown")
    if not name:
        return None

    year = _safe_int(raw.get("year"))
    concentration = _safe_text(raw.get("concentration"), "N/A")

    frag_id = _safe_text(raw.get("id"))
    if not frag_id:
        frag_id = _stable_id(name=name, brand=brand, year=year, concentration=concentration)

    return {
        "id": frag_id,
        "name": name,
        "brand": brand,
        "year": year,
        "concentration": concentration,
        "gender_label": _safe_text(raw.get("gender_label"), "N/A"),
        "description": _safe_text(raw.get("description"), ""),
        "top_notes": _safe_list(raw.get("top_notes")),
        "middle_notes": _safe_list(raw.get("middle_notes")),
        "base_notes": _safe_list(raw.get("base_notes")),
        "accords": _safe_list(raw.get("accords")),
        "review_count": _safe_float(raw.get("review_count")),
        "rating_count": _safe_float(raw.get("rating_count")),
        "view_count": _safe_float(raw.get("view_count")),
        "popularity_score": _safe_float(raw.get("popularity_score")),
        "rating": _safe_float(raw.get("rating")),
    }


def _merge_record(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)

    for text_key in ("name", "brand", "concentration", "gender_label", "description"):
        if not _safe_text(merged.get(text_key)) and _safe_text(incoming.get(text_key)):
            merged[text_key] = incoming[text_key]

    if merged.get("year") is None and incoming.get("year") is not None:
        merged["year"] = incoming["year"]

    for list_key in ("top_notes", "middle_notes", "base_notes", "accords"):
        existing = _safe_list(merged.get(list_key))
        incoming_values = _safe_list(incoming.get(list_key))
        if not existing and incoming_values:
            merged[list_key] = incoming_values

    for numeric_key in ("review_count", "rating_count", "view_count", "popularity_score", "rating"):
        if merged.get(numeric_key) is None and incoming.get(numeric_key) is not None:
            merged[numeric_key] = incoming[numeric_key]

    return merged


def _dedupe_merge(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}

    for row in rows:
        frag_id = _safe_text(row.get("id"))
        if not frag_id:
            continue

        if frag_id in by_id:
            by_id[frag_id] = _merge_record(by_id[frag_id], row)
        else:
            by_id[frag_id] = row

    return list(by_id.values())


def load_recommendation_catalog(force_reload: bool = False) -> list[dict[str, Any]]:
    """Load merged recommendation catalog.

    Priority:
    - Primary 24k canonical dataset(s)
    - Fallback seed set for continuity
    """
    global _catalog_cache

    if _catalog_cache is not None and not force_reload:
        return _catalog_cache

    normalized_rows: list[dict[str, Any]] = []

    primary_paths, fallback_paths = _catalog_path_candidates()

    for path in primary_paths:
        for raw in _load_json_rows(path):
            normalized = _normalize_record(raw)
            if normalized is not None:
                normalized_rows.append(normalized)

    for fallback_path in fallback_paths:
        for raw in _load_json_rows(fallback_path):
            normalized = _normalize_record(raw)
            if normalized is not None:
                normalized_rows.append(normalized)

    merged = _dedupe_merge(normalized_rows)

    if not merged:
        logger.warning("Merged recommendation catalog is empty")

    _catalog_cache = merged
    logger.info("Loaded recommendation catalog rows=%s", len(_catalog_cache))
    return _catalog_cache


def get_catalog_stats() -> dict[str, Any]:
    catalog = load_recommendation_catalog()
    return {
        "rows": len(catalog),
        "features": [
            "id",
            "name",
            "brand",
            "year",
            "concentration",
            "gender_label",
            "description",
            "top_notes",
            "middle_notes",
            "base_notes",
            "accords",
        ],
    }
