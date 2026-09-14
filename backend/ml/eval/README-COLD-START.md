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
content-based oracle also calls similar.

## Background: the embedding artifact and the collapse story

**GraphSAGE purpose.** The 64-d embedding vectors encode "who smells like me"
via message passing over a Jaccard-similarity graph: two fragrances sharing the
same primary accord are linked when their note-Jaccard exceeds 0.20 (top-k 10
neighbors per node). A 2-layer GraphSAGE (`train.py`) with an anchored InfoNCE
contrastive loss trains these vectors so that same-cluster fragrances cluster in
embedding space, enabling content-based retrieval without any user-history
matrix factorisation.

**Original embedding collapse.** The first training run (pre-fix) produced
near-collapsed vectors: the accord one-hot feature dominated the concatenated
text signal, so items sharing a primary accord collapsed into near-duplicate
vectors (within-primary-accord median cosine ≈ 0.992; 34 rounded-duplicate
rows at 6 decimal places — effectively 2 unique vectors with 34 copies
colliding). This defeated retrieval: same-accord neighbours became
indistinguishable.

**How it was detected.** `train.py` runs semantic validation gates after every
training run: (a) count rows identical to 6 decimal places, (b) measure
median within-primary-accord cosine vs median cross-primary cosine, (c) check
isolated-node fraction, (d) verify catalog-order invariance. Gate (b)
`within_primary_similarity_median < 0.98` flagged collapse. The tests
`backend/ml/tests/test_embedding_validation.py` encode the same invariants as
pure assertions. The committed `backend/app/data/metadata.json` records the
full validation report.

**How it was fixed (`train.py`, fixes A–F).** Key changes: (A) the accord
one-hot is scaled to 0.2 and the 384-d text block is L2-normalized *before*
concatenation so the accord spike no longer swamps the text signal; (B) graph
edges emit both directions (undirected) so message passing is
catalog-order-invariant; (C) the loss becomes a properly anchored InfoNCE
(positives per-edge neighbours, negatives sampled from the global pool) plus a
small off-diagonal-Gram uniformity term that discourages embedding collapse
(tau 0.5, uniform_reg_lambda 1.0, edge_dropout 0.1); (D) semantic quality
gates run at export; (E) a content-hash text cache. The shipped serving
artifact (`backend/app/data/node_embeddings_jaccard.npy`, SHA prefix
`f9117664b8`) passes every gate — 0 rounded duplicates, within-primary median
cosine 0.3846 vs cross-accord −0.0204.

**Artifact snapshots.** The committed baseline snapshot in
`backend/ml/eval/data/baseline/` (SHA prefix `699cf6fa30`) is the **pre-fix**
output — the collapsed-era artifact retained for comparison. The **fixed**
serving artifact lives at `backend/app/data/` (SHA prefix `f9117664b8`). The
committed results in `runs/` and `runs/retrained/` report these two snapshots
respectively. A fresh run against `backend/app/data` reproduces the retrained
numbers bit-for-bit.

## How the app uses this (quiz → cold-start path)

At serving time there is no model inference. Embeddings are precomputed and
shipped as a NumPy array. The 3-state dispatcher
(`backend/app/services/dispatcher.py`) determines which recommendation
strategy fires:

1. **Cold (embedding path)** — the default for anonymous users. A short
   quiz (`/fragrances/quiz/session/start` → answer → `guest-finalize`)
   collects k rated items; the frontend posts them to `/recommendations/guest`,
   which calls `compute_user_vector` (`backend/app/services/embeddings.py`).
2. **Warm (feature-based)** — if the user has ≥3 rated items with ratings
   spread across the preference range, a Jaccard-over-features strategy takes
   over.
3. **Popularity** — fallback when no directional signal exists.

**Signed rating representation.** Each rating is centred on the neutral point
5 and divided by 5:

| Rating | Weight `(rating − 5) / 5` | Effect |
| --- | --- | --- |
| 10 | +1.0 | strongly liked — pulls profile toward this item |
| 8 | +0.6 | liked |
| 5 | 0.0 | neutral — no directional signal |
| 3 | −0.4 | disliked — pushes profile away |
| 1 | −1.0 | strongly disliked — pushes profile away |

The weighted sum of rated items' embeddings is L2-normalised to produce the
user vector. A purely neutral set (all 5s) yields a zero vector; the
dispatcher detects this and falls back to popularity.

The offline evaluation below uses an *unweighted* mean of seed embeddings.
This is equivalent to the app's weighted path because every simulated seed
is rated 8 (weight 0.6, which cancels after normalisation when all weights
are equal). The eval intentionally fixes rating at 8 to isolate the effect
of *content* (which seeds are liked) from *rating magnitude*.

## Snapshot / reproducibility

Before every run, copy the current embedding artifact into a run-specific
artifacts directory (e.g. `backend/ml/eval/data/baseline/`). The runner
records the SHA-256 (first 10 hex chars) of the npy in its JSON/MD output.
Comparing that hash across runs tells you whether a retrained snapshot
changed retrieval quality.

The tracked published results live in:

* `runs/cold_start_eval_baseline.{json,md}` — **pre-fix** baseline snapshot
  `699cf6fa30` (collapsed-era embeddings)
* `runs/retrained/cold_start_eval_baseline.md` — **fixed** serving-artifact
  snapshot `f9117664b8`

A default re-run writes to `runs/sessions/<timestamp>/` (gitignored); pass
`--runs-dir backend/ml/eval/runs/final` to publish into a named folder.

## The oracle (model-independent ground truth)

Two fragrances `i` and `j` are **similar** iff:

1. `i` and `j` share the same **primary accord** — the lowercased first entry of
   each item's `accords` list (items with no accords are skipped), AND
2. Jaccard over the lowercased union of
   `{top_notes, middle_notes, base_notes}` is `> 0.20`.

`relevant[i]` = `{j : j != i and similar(i, j)}`. The relation is symmetric and
self-excluding. Items with empty `relevant` sets are skipped as trial seeds.

This oracle mirrors the training-time graph-edge predicate in
`train.py` (`build_jaccard_graph`): same primary accord AND note-Jaccard > 0.20,
top-k 10 neighbors. The evaluation therefore tests whether the embedding
captures the same content-similarity signal the graph was built to encode.

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

**Rating weighting note.** The app builds the user vector as
`Σ ((rating−5)/5) · embedding` (L2-normalised). The eval's unweighted mean
is equivalent because all simulated seeds are rated 8 (equal positive
weights). The eval isolates the content-retrieval question independently of
rating-magnitude variation.

## Metrics

Per model per `k`, averaged over trials: `P@5`, `P@10`, `Recall@10`, `NDCG@10`
(binary relevance, gains `1/log2(rank+1)`, IDCG = ideal DCG over the top-10
relevant cap). Bootstrap 95% CIs come from 1000 resamples of the per-trial
arrays (numpy-only). **Win-rate vs popularity** = fraction of trials where
`s-centrix` `Recall@10 > popularity` `Recall@10`.

## Interpretation

* **High P@k is expected** — the oracle and the embedding model both use
  catalog content, so with seeds drawn from one accord family, top retrievals
  are frequently accord-relevant. Do not read P@k as "users liked these."
* **Recall@10 is low** — the denominator is the trial's seed-dependent
  relevant set (the union of similar-item neighbourhoods across the k seeds),
  measuring at a mean ~11 (k=1) up to ~41 (k=5), so a 10-item window
  covers only a fraction. Watch how it and P@k respond to `k`; the detailed
  mechanism is in the next paragraph.
* **Why Recall@10 drops as k increases.** The trial's relevant set is a
  *union* over seeds: an item is relevant if it is similar to *any* of the k
  seeds (`hit_ids`), so `r_total` grows as each extra seed contributes its own
  similar-item neighbourhood. Measured mean `r_total` rises from ~11 (k=1) to
  ~41 (k=5) — a ~3.5× increase. Meanwhile the numerator is hard-capped by the
  10-slot ranking window (`hits ≤ 10`), so the achievable-recall ceiling per
  trial falls (mean `min(1, 10/r_total)` ≈ 0.87 → 0.57). The model keeps
  improving *within* the window (P@10 rises from 0.17 → 0.36, NDCG@10 from
  0.40 → 0.51), but collection-level coverage of the ever-larger relevant set
  must fall. This is a classic precision/recall tradeoff, not a model failure.
  The non-monotone k=2 vs k=3 R@10 difference (0.388 vs 0.404) is sampling
  noise — the 95% bootstrap CIs overlap broadly — and does not indicate
  structural instability.
* Compare models only *within* the same `k`; the random baseline quantifies how
  much of the P@k level is trivially attributable to the accord-family sampling.

## Actual result

Fixed-artifact run (`app/data`, SHA prefix `f9117664b8`; 300 trials, seed 42):

| k (seed items) | P@5 | P@10 | Recall@10 | NDCG@10 | win-rate vs popularity (R@10) |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.3467 | 0.2383 | 0.6404 | 0.6597 | 0.9233 |
| 2 | 0.3553 | 0.2817 | 0.4058 | 0.4799 | 0.8167 |
| 3 | 0.4140 | 0.3377 | 0.3876 | 0.5193 | 0.9100 |
| 5 | 0.4860 | 0.3980 | 0.3217 | 0.5320 | 0.8133 |

95% bootstrap CIs for every metric are in the tracked `runs/retrained/cold_start_eval.json`.

Pre-fix baseline comparison (snapshot `699cf6fa30`): k=1 NDCG@10 0.4021
vs retrained 0.6597; k=1 P@5 0.2340 vs 0.3467 — the collapse fix
substantially improves retrieval quality.

## What this proves and what it does not

**What it proves.**
The s-centrix user vector — a mean of k seed embeddings — can retrieve
same-accord, note-similar items above the popularity and random baselines
on identical synthetic trials. With the collapse fix applied, within-accord
NDCG@10 reaches 0.66 at k=1 and 0.53 at k=5, beating popularity (0.1%)
and random (0.1%) by wide margins. The win-rate is 81–92% across all k.

**What it does NOT prove.**
This is an intrinsic content-based proxy, not a user study. Nothing here is
evidence that real users would prefer these recommendations. There is no
observed user-behaviour data, no A/B test, no click-through measurement.
The oracle (same primary accord + note-Jaccard > 0.20) is a convenient
content-similarity rule, not a user-preference ground truth.

## How to re-run

All paths are relative to the **repository root**. Any Python 3.11+ with
`numpy` installed works; no other dependencies are required by the runner
(`backend/ml/eval/run_cold_start_eval.py` is stdlib + numpy only).

```bash
# Default run (outputs to gitignored runs/sessions/<timestamp>/):
python backend/ml/eval/run_cold_start_eval.py --seed 42 --trials 300

# Reproduce the pre-fix baseline numbers (snapshot in ml/eval/data/baseline):
python backend/ml/eval/run_cold_start_eval.py --seed 42 --trials 300 \
    --artifacts backend/ml/eval/data/baseline \
    --runs-dir backend/ml/eval/runs/baseline-snapshot

# Reproduce the final fixed-artifact numbers (serving artifact in app/data):
python backend/ml/eval/run_cold_start_eval.py --seed 42 --trials 300 \
    --artifacts backend/app/data \
    --runs-dir backend/ml/eval/runs/final
```

Compare the recorded SHA-256 prefixes in the JSON/MD output to confirm which
snapshot was used: `699cf6fa30` = pre-fix baseline; `f9117664b8` = fixed
serving artifact. Both are tracked in git.

### Tests

Pure-function unit tests (no app / database imports):

```bash
python -m pytest backend/ml/tests/test_cold_start_eval.py -q
```

Covers oracle symmetry/self-exclusion, exact hand-computed P@k/R@k/NDCG@k,
guaranteed seed exclusion / no-duplicate / length invariants, runner
determinism (same seed → identical results), user-vector mean-of-seeds
correctness + dot-product ordering, and sane metrics across all four k values
({1,2,3,5}).
