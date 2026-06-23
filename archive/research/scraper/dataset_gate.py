"""Standalone dataset gate for external scraper bundle.

Usage (matches requested sequence):
  python dataset_gate.py

Reads data/fragrantica_canonical.json by default and enforces production minima.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return (part / total) * 100.0


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Production dataset gate")
    parser.add_argument("--input", default="data/fragrantica_canonical.json")
    parser.add_argument("--min-rows", type=int, default=10000)
    parser.add_argument("--min-unique-brands", type=int, default=500)
    parser.add_argument("--min-gender-populated-pct", type=float, default=80.0)
    parser.add_argument("--max-release-lag-years", type=int, default=1)
    parser.add_argument("--min-interaction-coverage-pct", type=float, default=30.0)
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        raise SystemExit(f"Input file not found: {path}")

    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("Gate input must be a JSON array")

    total = len(rows)
    brands = {
        str(r.get("brand", "")).strip().lower()
        for r in rows
        if isinstance(r, dict) and str(r.get("brand", "")).strip()
    }
    unique_brands = len(brands)

    gender_populated = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = str(row.get("gender_label", "")).strip().lower()
        if value and value not in {"n/a", "na", "unknown", "none", "null"}:
            gender_populated += 1
    gender_pct = _pct(gender_populated, total)

    years = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            y = int(str(row.get("year", "")))
            if 1800 <= y <= datetime.now().year + 1:
                years.append(y)
        except (TypeError, ValueError):
            pass
    max_year = max(years) if years else None
    release_lag = (datetime.now().year - max_year) if max_year is not None else None

    interaction_fields = ("rating_count", "popularity_score", "view_count", "purchase_count", "wishlist_count", "review_count")
    interaction_rows = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        if any(_is_non_empty(row.get(field)) for field in interaction_fields):
            interaction_rows += 1
    interaction_pct = _pct(interaction_rows, total)

    list_fields = ("top_notes", "middle_notes", "base_notes", "accords")
    list_ok = all(
        _pct(sum(1 for r in rows if isinstance(r, dict) and isinstance(r.get(field), list)), total) >= 100.0
        for field in list_fields
    )

    checks = [
        ("Row count", total >= args.min_rows, f"{total}", f">= {args.min_rows}"),
        ("Unique brands", unique_brands >= args.min_unique_brands, f"{unique_brands}", f">= {args.min_unique_brands}"),
        (
            "Gender label populated",
            gender_pct >= args.min_gender_populated_pct,
            f"{gender_pct:.1f}%",
            f">= {args.min_gender_populated_pct:.1f}%",
        ),
        (
            "Year recency",
            release_lag is not None and release_lag <= args.max_release_lag_years,
            "N/A" if release_lag is None else f"lag={release_lag}y",
            f"<= {args.max_release_lag_years}y",
        ),
        (
            "Interaction coverage",
            interaction_pct >= args.min_interaction_coverage_pct,
            f"{interaction_pct:.1f}%",
            f">= {args.min_interaction_coverage_pct:.1f}%",
        ),
        ("List normalization", list_ok, "100.0%", "100.0%"),
    ]

    print("=" * 80)
    print("External Scraper Dataset Gate")
    print("=" * 80)

    passed = 0
    for name, ok, actual, expected in checks:
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"{name:24} actual={actual:16} expected={expected:14} status={status}")

    print("-" * 80)
    print(f"summary={passed}/{len(checks)}")

    if passed == len(checks):
        print("gate_result=PASS")
        return 0

    print("gate_result=FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
