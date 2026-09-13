# Scentrix Cold-Start Evaluation (Offline, Intrinsic Proxy)

## Dataset limitations — READ THIS FIRST

The repository has **no user-interaction history**: there are no ratings by users,
no reviews, no observed behavior. The only assets are:

* a 4,559-item fragrance catalog
  (`backend/app/data/scentrix_master_cleaned.json`: id, name, brand, year,
  concentration, gender_label, description, top/middle/base notes, accords,
  rating_count, rating_value), and
* a precomputed embedding artifact
  (`backend/app/data/node_embeddings_jaccard.npy` — 4559x64, L2-normalized rows —
  plus `backend/app/data/node_ids_jaccard.json`, 4559 ids in catalog order).

Because there is no interaction log, **this evaluation is an intrinsic
item-retrieval capability proxy, NOT observed user satisfaction.** Nothing in the
numbers below is evidence that real users would like the recommendations; it
only measures whether the embedding-based user vector can retrieve items that a
content-based oracle also calls similar. One process may later retrain and
atomically replace the `npy`; the run below always snapshots its inputs first so
results stay reproducible against a fixed artifact.

## Snapshot / reproducibility

Before every run, copy the current `node_embeddings_jaccard.npy` and
`node_ids_jaccard.json` into a run-specific artifacts directory
(e.g. `backend/ml/eval/data/baseline/`). The runner records the SHA-256 (first
10 hex chars) of the copied `npy` in its JSON/MD output. Comparing that hash
across runs tells you whether a retrained snapshot changed.

## The oracle (model-independent ground truth)

Two fragrances `i` and `j` are **similar** iff:

1. `i` and `j` share the same **primary accord** — the lowercased first entry of
   each item's `accords` list (items with no accords are skipped), AND
2. Jaccard over the lowercased union of
   `{top_notes, middle_notes, base_notes}` is `> 0.20`.

`relevant[i]` = `{j : j != i and similar(i, j)}`. The relation is symmetric and
self-excluding. Items with empty `relevant` sets are skipped as trial seeds.

## The simulation

For each `k in {1, 2, 3, 5}` and `N=300` trials (seeded by
`np.random.default_rng(seed)`):

1. pick a primary-accord family uniformly among families with ≥5 items,
2. sample `k` items (without replacement) from that family — these are the
   user's `k` known-liked interactions (each rated 8),
3. each model returns a ranked list of up to **10 candidates, excluding the k
   seed items** (items not in the node index are dropped),
4. a candidate is **relevant to the trial** iff its `relevant` set intersects
   the seed set.

A higher `k` is not "more interaction history being learned" in the observed-
behavior sense; it is the model seeing more of the user's preferred item
content. The across-`k` comparison shows retrieval quality / coverage as the
number of known-liked (seed) items grows.

## Models compared (on identical trials + oracle)

| model | ranking rule |
| --- | --- |
| `s-centrix` | user vector = mean of the k seed-item embeddings (rows of the snapshot matrix via `node_ids_jaccard.json` order); rank remaining items by cosine (`np.dot(matrix, vec)`) descending; seeds excluded. |
| `popularity` | rank remaining items by `rating_count` descending, stable tie-break by id. |
| `random` | numpy RNG permutation of remaining items. |

## Metrics

Per model per `k`, averaged over trials: `P@5`, `P@10`, `Recall@10`, `NDCG@10`
(binary relevance, gains `1/log2(rank+1)`, IDCG = ideal DCG over the top-10
relevant cap). Bootstrap 95% CIs come from 1000 resamples of the per-trial
arrays (numpy-only). **Win-rate vs popularity** = fraction of trials where
`s-centrix` `Recall@10 > popularity` `Recall@10`.

### Interpretation

* **High P@k is expected** — the oracle and the embedding model both use
  catalog content, so with seeds drawn from one accord family, top retrievals
  are frequently accord-relevant. Do not read P@k as "users liked these."
* **Recall@10 is low and collection-level** — the denominator is the total
  number of relevant candidates in the whole pool (often hundreds for a big
  accord family), so a 10-item window can only cover a small fraction. This is
  the honest measurement of *coverage*; watch how it and P@k respond to `k`.
* Compare models only *within* the same `k`; the random baseline quantifies how
  much of the P@k level is trivially attributable to the accord-family sampling.

## How to re-run

From the repo root, with the project venv:

```powershell
& "C:\Users\KIIT0001\Documents\antigravity skills\Scentrix\backend\venv\Scripts\python.exe" backend/ml/eval/run_cold_start_eval.py --seed 42 --trials 300 --artifacts backend/ml/eval/data/baseline
```

Outputs (both written to `backend/ml/eval/runs/`):

* `cold_start_eval.json` — full numbers including CIs,
* `cold_start_eval_baseline.md` — readable report (same text is printed).

### Against a newer artifact directory

If `train.py` (or another process) retrains and replaces the embedding artifact,
snapshot the new files into a new dir and point `--artifacts` at it:

```powershell
New-Item -ItemType Directory -Force -Path backend/ml/eval/data/run2 | Out-Null
Copy-Item backend/app/data/node_embeddings_jaccard.npy backend/ml/eval/data/run2/
Copy-Item backend/app/data/node_ids_jaccard.json backend/ml/eval/data/run2/
& "C:\Users\KIIT0001\Documents\antigravity skills\Scentrix\backend\venv\Scripts\python.exe" backend/ml/eval/run_cold_start_eval.py --trials 300 --artifacts backend/ml/eval/data/run2
```

Diff the recorded SHA-256 and the metric tables to see whether the retrained
snapshot changed retrieval quality. The runner is self-contained
(stdlib + numpy only); no service or database is required.

### Tests

Pure-function unit tests (no app / database imports):

```powershell
& "C:\Users\KIIT0001\Documents\antigravity skills\Scentrix\backend\venv\Scripts\python.exe" -m pytest backend/ml/tests/test_cold_start_eval.py -q
```

Covers oracle symmetry/self-exclusion, exact hand-computed P@k/R@k/NDCG@k,
guaranteed seed exclusion / no-duplicate / length invariants, and runner
determinism (same seed → identical results).