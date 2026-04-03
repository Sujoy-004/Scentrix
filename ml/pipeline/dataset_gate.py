"""Dataset readiness gate for ML production rollout.

Validates fragrance datasets against minimum production thresholds.
Exit code 0 when all checks pass, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


GENDER_EMPTY_VALUES = {"", "n/a", "na", "unknown", "none", "null"}
INTERACTION_FIELDS = (
    "rating_count",
    "popularity_score",
    "view_count",
    "purchase_count",
    "wishlist_count",
    "review_count",
)
LIST_FIELDS = ("top_notes", "middle_notes", "base_notes", "accords")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate dataset production readiness.")
    parser.add_argument("dataset", type=Path, help="Path to dataset file (.json or .jsonl)")
    parser.add_argument("--min-rows", type=int, default=5_000)
    parser.add_argument("--min-unique-brands", type=int, default=200)
    parser.add_argument("--min-gender-populated-pct", type=float, default=80.0)
    parser.add_argument("--max-release-lag-years", type=int, default=2)
    parser.add_argument("--min-interaction-coverage-pct", type=float, default=30.0)
    parser.add_argument("--min-list-normalization-pct", type=float, default=100.0)
    return parser.parse_args()


def _load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                raw = line.strip()
                if not raw:
                    continue
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    records.append(parsed)
        return records

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _as_int_year(value: Any) -> int | None:
    if value is None:
        return None
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    if 1800 <= year <= datetime.now().year + 1:
        return year
    return None


def _pct(part: int, total: int) -> float:
    if total == 0:
        return 0.0
    return (part / total) * 100.0


def evaluate(records: list[dict[str, Any]], args: argparse.Namespace) -> int:
    total = len(records)
    current_year = datetime.now().year

    brands = {
        _safe_str(row.get("brand")).lower()
        for row in records
        if _safe_str(row.get("brand"))
    }
    unique_brands = len(brands)

    gender_populated = 0
    for row in records:
        value = _safe_str(row.get("gender_label")).lower()
        if value and value not in GENDER_EMPTY_VALUES:
            gender_populated += 1
    gender_populated_pct = _pct(gender_populated, total)

    years = [y for y in (_as_int_year(row.get("year")) for row in records) if y is not None]
    min_year = min(years) if years else None
    max_year = max(years) if years else None
    release_lag = (current_year - max_year) if max_year is not None else None

    interaction_rows = 0
    for row in records:
        if any(_is_non_empty(row.get(field)) for field in INTERACTION_FIELDS):
            interaction_rows += 1
    interaction_coverage_pct = _pct(interaction_rows, total)

    list_metrics: dict[str, float] = {}
    for field in LIST_FIELDS:
        list_rows = sum(1 for row in records if isinstance(row.get(field), list))
        list_metrics[field] = _pct(list_rows, total)

    checks = [
        (
            "Row count",
            total >= args.min_rows,
            f"{total}",
            f">= {args.min_rows}",
        ),
        (
            "Unique brands",
            unique_brands >= args.min_unique_brands,
            f"{unique_brands}",
            f">= {args.min_unique_brands}",
        ),
        (
            "Gender label populated",
            gender_populated_pct >= args.min_gender_populated_pct,
            f"{gender_populated_pct:.1f}%",
            f">= {args.min_gender_populated_pct:.1f}%",
        ),
        (
            "Year recency",
            release_lag is not None and release_lag <= args.max_release_lag_years,
            "N/A" if release_lag is None else f"lag={release_lag}y (max={max_year})",
            f"lag <= {args.max_release_lag_years}y",
        ),
        (
            "Interaction coverage",
            interaction_coverage_pct >= args.min_interaction_coverage_pct,
            f"{interaction_coverage_pct:.1f}%",
            f">= {args.min_interaction_coverage_pct:.1f}%",
        ),
    ]

    for field in LIST_FIELDS:
        value = list_metrics[field]
        checks.append(
            (
                f"{field} normalized as list",
                value >= args.min_list_normalization_pct,
                f"{value:.1f}%",
                f">= {args.min_list_normalization_pct:.1f}%",
            )
        )

    print("=" * 84)
    print("ScentScape Dataset Production Readiness Report")
    print("=" * 84)
    print(f"Rows: {total}")
    print(f"Year range: {min_year} - {max_year}" if min_year is not None else "Year range: N/A")
    print("-" * 84)
    print(f"{'Check':36} {'Actual':22} {'Required':20} {'Status':6}")
    print("-" * 84)

    passed = 0
    for name, ok, actual, required in checks:
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"{name:36} {actual:22} {required:20} {status:6}")

    print("-" * 84)
    print(f"Summary: {passed}/{len(checks)} checks passed")

    if passed == len(checks):
        print("Gate result: PASS (dataset is production-ready)")
        return 0

    print("Gate result: FAIL (dataset is not production-ready)")
    return 1


def main() -> int:
    args = _parse_args()
    records = _load_records(args.dataset)
    return evaluate(records, args)


if __name__ == "__main__":
    raise SystemExit(main())
