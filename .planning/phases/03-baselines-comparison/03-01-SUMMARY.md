# Phase 3: Baselines & Comparison — Plan 01 Summary

**Phase:** 03-baselines-comparison
**Plan:** 01
**Created:** 2026-05-25
**Status:** Complete

## Objective
Create popularity and random baseline recommenders that produce ranked item lists for evaluation.

## Summary
This plan created the baseline recommenders:
- **PopularityBaseline** — ranks fragrance items by accord count (fragrance complexity proxy for popularity). Loads from `scentrix_master_cleaned.json`, lazily, 4559 items.
- **RandomBaseline** — returns uniformly random shuffles of all fragrance IDs. Python `random.shuffle` for uniform distribution.

## Files
- `ml/eval/models/popularity.py` — PopularityBaseline (accord-count popularity)
- `ml/eval/models/random_baseline.py` — RandomBaseline (uniform random shuffle)

## Requirements
- EVAL-04: Popularity baseline — items ranked by accord count (higher = more complex)
- EVAL-05: Random baseline — uniformly random shuffles

## Verification
- Both classes import and load 4559 fragrance IDs
- PopularityBaseline.get_rankings(k=10) returns top-10 by accord count
- RandomBaseline.get_rankings(k=10) returns 10 uniformly shuffled items
- Empty/missing data handles gracefully (empty list + warning)

## Deviation
- Plan assumed interaction data (`item_id` field, frequency-based popularity). Actual dataset is fragrance catalog using `id`. Used **accord count** as popularity proxy — all 4559 items have ≥1 accord (max 5, avg 4.8).
