"""Import licensed fragrance partner feeds into canonical Scentrix schema.

Supports JSON, JSONL, and CSV source files and writes cleaned canonical JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from ml.pipeline.clean import FragranceDataCleaner


CSV_LIST_SPLIT_TOKENS = ("|", ";", ",")

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

# Ensure common Kaggle rating columns contribute to interaction coverage fields.
CANONICAL_SCHEMA_MAPPING["review_count"] = (
    *CANONICAL_SCHEMA_MAPPING["review_count"],
    "rating_count",
    "ratings_count",
    "rating_value",
)
CANONICAL_SCHEMA_MAPPING["rating_count"] = (
    *CANONICAL_SCHEMA_MAPPING["rating_count"],
    "rating_value",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import licensed partner feed into canonical JSON.")
    parser.add_argument("input_path", type=Path, help="Path to source dataset (json, jsonl, csv)")
    parser.add_argument("output_path", type=Path, help="Path to output canonical JSON file")
    parser.add_argument("--strict", action="store_true", help="Enable strict cleaner validation")
    return parser.parse_args()


def _split_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

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

    for token in CSV_LIST_SPLIT_TOKENS:
        if token in text:
            return [item.strip() for item in text.split(token) if item.strip()]

    if " / " in text:
        return [item.strip() for item in text.split(" / ") if item.strip()]
    if "/" in text:
        return [item.strip() for item in text.split("/") if item.strip()]

    return [text]


def _first(row: dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        if key not in row:
            continue
        value = row[key]
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
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


def _map_record(raw: dict[str, Any], index: int) -> dict[str, Any]:
    normalized_row = _normalize_row_keys(raw)

    name = str(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["name"], default="")).strip()
    brand = str(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["brand"], default="Unknown")).strip() or "Unknown"

    rid = _first(normalized_row, CANONICAL_SCHEMA_MAPPING["id"], default=None)
    if rid is None or (isinstance(rid, str) and not rid.strip()):
        digest = hashlib.sha1(f"{name}|{brand}|{index}".encode("utf-8")).hexdigest()[:16]
        rid = f"partner_{digest}"

    year_raw = _first(normalized_row, CANONICAL_SCHEMA_MAPPING["year"], default=None)
    year = None
    if year_raw is not None:
        match = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", str(year_raw))
        if match:
            try:
                year = int(match.group(1))
            except (TypeError, ValueError):
                year = None

    top_notes = _split_list(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["top_notes"], default=[]))
    middle_notes = _split_list(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["middle_notes"], default=[]))
    base_notes = _split_list(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["base_notes"], default=[]))
    all_notes = _split_list(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["all_notes"], default=[]))
    if not (top_notes or middle_notes or base_notes) and all_notes:
        top_end = max(1, len(all_notes) // 3)
        middle_end = max(top_end + 1, (2 * len(all_notes)) // 3)
        top_notes = all_notes[:top_end]
        middle_notes = all_notes[top_end:middle_end]
        base_notes = all_notes[middle_end:]

    gender_text = str(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["gender_label"], default="N/A") or "").strip().lower()
    if gender_text in {"male", "man", "men", "for men", "m"}:
        gender_label = "Male"
    elif gender_text in {"female", "woman", "women", "for women", "f"}:
        gender_label = "Female"
    elif gender_text in {"unisex", "for women and men", "both", "u"}:
        gender_label = "Unisex"
    else:
        gender_label = "N/A"

    concentration_raw = str(
        _first(normalized_row, CANONICAL_SCHEMA_MAPPING["concentration"], default="N/A") or ""
    ).strip()
    concentration_lower = concentration_raw.lower()
    if "extrait" in concentration_lower:
        concentration = "Extrait de Parfum"
    elif "eau de parfum" in concentration_lower or concentration_lower == "edp":
        concentration = "Eau de Parfum"
    elif "eau de toilette" in concentration_lower or concentration_lower == "edt":
        concentration = "Eau de Toilette"
    elif "eau de cologne" in concentration_lower or "cologne" in concentration_lower or concentration_lower == "edc":
        concentration = "Eau de Cologne"
    else:
        concentration = concentration_raw or "N/A"

    def _as_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return None

    record = {
        "id": str(rid).strip(),
        "name": name,
        "brand": brand,
        "year": year,
        "concentration": concentration,
        "gender_label": gender_label,
        "description": str(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["description"], default="")).strip()[:500],
        "top_notes": top_notes,
        "middle_notes": middle_notes,
        "base_notes": base_notes,
        "accords": _split_list(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["accords"], default=[])),
        "review_count": _as_float(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["review_count"], default=None)),
        "rating_count": _as_float(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["rating_count"], default=None)),
        "view_count": _as_float(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["view_count"], default=None)),
        "popularity_score": _as_float(_first(normalized_row, CANONICAL_SCHEMA_MAPPING["popularity_score"], default=None)),
    }

    # Map interaction fields from Kaggle CSV
    record["rating_count"] = (
        raw.get("Rating Count") or raw.get("rating count") or raw.get("votes") or record.get("rating_count") or None
    )
    record["rating_value"] = (
        raw.get("Rating Value") or raw.get("rating value") or raw.get("rating") or None
    )

    record["rating_count"] = _as_float(record.get("rating_count"))
    record["rating_value"] = _as_float(record.get("rating_value"))

    return record


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        return []

    if suffix == ".jsonl":
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                raw = line.strip()
                if not raw:
                    continue
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    rows.append(parsed)
        return rows

    if suffix == ".csv":
        df = pd.read_csv(path, sep=None, engine="python", encoding="latin-1", on_bad_lines="skip")
        return [{str(k): v for k, v in row.items()} for row in df.to_dict(orient="records")]

    raise ValueError(f"Unsupported input extension: {suffix}")


def main() -> int:
    args = _parse_args()
    raw_rows = _load_rows(args.input_path)
    mapped_rows = [_map_record(row, i) for i, row in enumerate(raw_rows, start=1)]

    cleaner = FragranceDataCleaner(strict_mode=args.strict)
    cleaned = cleaner.clean_fragrance_list(mapped_rows)

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")

    report = cleaner.report()
    print(f"input_rows={len(raw_rows)}")
    print(f"output_rows={len(cleaned)}")
    print(f"duplicates_removed={report['duplicates_removed']}")
    print(f"invalid_records={report['invalid_records']}")
    print(f"output_file={args.output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
