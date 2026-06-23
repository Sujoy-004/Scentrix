"""Standalone feed normalizer for external scraper bundle.

Usage (matches requested sequence):
  python import_licensed_feed.py --input data/fragrantica_raw.json

Writes canonical output to data/fragrantica_canonical.json by default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
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
)


CANONICAL_SCHEMA_MAPPING: dict[str, tuple[str, ...]] = {
    "id": ("id", "fragrance_id", "perfume_id", "external_id", "uuid"),
    "name": ("name", "perfume", "perfume_name", "fragrance_name", "title"),
    "brand": ("brand", "house", "maker", "designer", "company"),
    "year": ("year", "release_year", "launch_year", "released", "release_date"),
    "concentration": (
        "concentration",
        "strength",
        "concentration_type",
        "perfume_concentration",
    ),
    "gender_label": ("gender_label", "gender", "target_gender", "sex", "for_gender"),
    "description": (
        "description",
        "summary",
        "about",
        "fragrance_description",
        "notes_description",
    ),
    "top_notes": ("top_notes", "notes_top", "top", "top_note", "head_notes"),
    "middle_notes": (
        "middle_notes",
        "heart_notes",
        "notes_middle",
        "middle",
        "heart",
    ),
    "base_notes": ("base_notes", "notes_base", "base", "base_note", "drydown_notes"),
    "all_notes": ("notes", "note_list", "fragrance_notes"),
    "accords": ("accords", "main_accords", "main_accord", "accord", "fragrance_family"),
    "review_count": ("review_count", "reviews", "num_reviews", "review_total"),
    "rating_count": ("rating_count", "ratings_count", "votes", "num_votes"),
    "view_count": ("view_count", "views", "view_total", "page_views"),
    "popularity_score": (
        "popularity_score",
        "popularity",
        "rating",
        "average_rating",
        "rating_value",
    ),
}


def _split_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]

    text = str(value).strip()
    if not text:
        return []

    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except json.JSONDecodeError:
            pass

    for token in ("|", ";", ",", " / ", "/"):
        if token in text:
            return [part.strip() for part in text.split(token) if part.strip()]

    return [text]


def _first(row: dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        if key not in row:
            continue
        value = row[key]
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return default


def _normalize_key(value: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return key.strip("_")


def _normalize_row_keys(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        normalized[_normalize_key(str(key))] = value
    return normalized


def _as_int_year(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    match = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", text)
    if not match:
        return None

    try:
        year = int(match.group(1))
        if 1800 <= year <= 2100:
            return year
        return None
    except (TypeError, ValueError):
        return None


def _normalize_gender(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"male", "man", "men", "for men", "m"}:
        return "Male"
    if text in {"female", "woman", "women", "for women", "f"}:
        return "Female"
    if text in {"unisex", "for women and men", "both", "u"}:
        return "Unisex"
    return "N/A"


def _normalize_concentration(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "N/A"
    if "extrait" in text:
        return "Extrait de Parfum"
    if "eau de parfum" in text or text == "edp":
        return "Eau de Parfum"
    if "eau de toilette" in text or text == "edt":
        return "Eau de Toilette"
    if "eau de cologne" in text or "cologne" in text or text == "edc":
        return "Eau de Cologne"
    return str(value).strip() or "N/A"


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _stable_id(name: str, brand: str, idx: int) -> str:
    source = f"{name}|{brand}|{idx}".encode("utf-8")
    digest = hashlib.sha1(source).hexdigest()[:16]
    return f"frag_{digest}"


def _partition_notes(all_notes: list[str]) -> tuple[list[str], list[str], list[str]]:
    if not all_notes:
        return [], [], []

    if len(all_notes) < 3:
        return all_notes[:1], all_notes[1:2], all_notes[2:3]

    top_end = max(1, len(all_notes) // 3)
    middle_end = max(top_end + 1, (2 * len(all_notes)) // 3)
    top_notes = all_notes[:top_end]
    middle_notes = all_notes[top_end:middle_end]
    base_notes = all_notes[middle_end:]
    return top_notes, middle_notes, base_notes


def _normalize_record(row: dict[str, Any], idx: int) -> dict[str, Any] | None:
    normalized_row = _normalize_row_keys(row)

    name = str(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["name"], default="")).strip()
    brand = str(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["brand"], default="")).strip()
    if not name or not brand:
        return None

    top_notes = _split_list(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["top_notes"], default=[]))
    middle_notes = _split_list(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["middle_notes"], default=[]))
    base_notes = _split_list(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["base_notes"], default=[]))
    all_notes = _split_list(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["all_notes"], default=[]))

    if not (top_notes or middle_notes or base_notes) and all_notes:
        top_notes, middle_notes, base_notes = _partition_notes(all_notes)

    canonical_id = _first(normalized_row, CANONICAL_SCHEMA_MAPPING["id"], default=None)
    canonical_id = str(canonical_id).strip() if canonical_id is not None else _stable_id(name, brand, idx)
    if not canonical_id:
        canonical_id = _stable_id(name, brand, idx)

    normalized = {
        "id": canonical_id,
        "name": name,
        "brand": brand,
        "year": _as_int_year(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["year"], default=None)),
        "concentration": _normalize_concentration(
            _first(normalized_row, CANONICAL_SCHEMA_MAPPING["concentration"], default="N/A")
        ),
        "gender_label": _normalize_gender(
            _first(normalized_row, CANONICAL_SCHEMA_MAPPING["gender_label"], default="N/A")
        ),
        "description": str(
            _first(normalized_row, CANONICAL_SCHEMA_MAPPING["description"], default="")
        ).strip()[:500],
        "top_notes": top_notes,
        "middle_notes": middle_notes,
        "base_notes": base_notes,
        "accords": _split_list(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["accords"], default=[])),
        "review_count": _as_float(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["review_count"], default=None)),
        "rating_count": _as_float(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["rating_count"], default=None)),
        "view_count": _as_float(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["view_count"], default=None)),
        "popularity_score": _as_float(
            _first(normalized_row, CANONICAL_SCHEMA_MAPPING["popularity_score"], default=None)
        ),
    }

    if not (normalized["top_notes"] or normalized["middle_notes"] or normalized["base_notes"]):
        return None

    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize scraped feed to canonical schema")
    parser.add_argument("--input", required=True, help="Input JSON file path")
    parser.add_argument("--output", default="data/fragrantica_canonical.json", help="Output canonical JSON path")
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise SystemExit(f"Input file not found: {in_path}")

    raw = json.loads(in_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("Input must be a JSON array")

    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        normalized = _normalize_record(item, idx)
        if normalized is not None:
            rows.append(normalized)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"input_rows={len(raw)}")
    print(f"output_rows={len(rows)}")
    print(f"output_file={out_path}")
    print(f"required_fields={','.join(REQUIRED_FIELDS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
