"""Self-contained offline cold-start evaluation for the Scentrix pipeline.

Imports ONLY stdlib + numpy. No app imports, no database, no ranx, no pandas.
All metrics are hand-implemented numpy math.

Motivation / honesty note: the repository has NO user-interaction history (no
reviews/users with observed behavior) — only a 4,559-item fragrance catalog and a
precomputed embedding artifact. This module therefore evaluates an INTRINSIC
capability proxy: item-retrieval quality of a mean-embedding user vector against
a content-based similarity oracle. It is NOT observed user satisfaction.

Ground-truth oracle (model-independent):
    i ~ j  iff  primary accord of i == primary accord of j
            AND  Jaccard(notes_i, notes_j) > 0.20
    where primary accord = lowercased first entry of ``accords`` and notes =
    lowercased union of {top_notes, middle_notes, base_notes}. Items with no
    accords are skipped; two items that match land in each other's ``relevant``
    set (symmetric, self-excluding).

Protocol (per k in {1,2,3,5}):
    N=300 trials, rng = np.random.default_rng(seed).
    Each trial:
      * pick a primary-accord family uniformly among families with >=5 items,
      * sample k items (no replacement) from that family => the user's k known
        liked items (rating 8),
      * each model ranks up to 10 candidates EXCLUDING the k seed items,
      * a candidate is RELEVANT iff its ``relevant`` oracle set intersects the
        seed set.

Models (on identical trials + oracle):
    s-centrix      : user vector = mean of k seed embeddings; rank by cosine
                     (np.dot(matrix, vec)) descending; seeds excluded.
    popularity     : rank remaining by rating_count descending (stable id tie-break).
    random         : numpy RNG permutation of remaining items.
    content-itemknn: pure-content ablation — mean seed profile over multi-hot
                     notes + weighted primary accord, cosine rank. No learned
                     embedding. Answers "do the learned embeddings beat direct
                     content matching on the content oracle?"

Metrics per model per k (averaged over trials):
    P@5, P@10, Recall@10, NDCG@10 (binary gains; IDCG over top-10 relevant cap).
    Win-rate vs popularity = fraction of trials where s-centrix R@10 > pop R@10.
Bootstrap 95% CIs: 1000 resamples of the per-trial arrays, numpy-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

MIN_FAMILY_SIZE = 5
MAX_CANDIDATES = 10
KS = (1, 2, 3, 5)
SCORE_KS = (5, 10)
FINAL_METRICS = ("P@5", "P@10", "R@10", "NDCG@10")
MODEL_ORDER = ("s-centrix", "popularity", "random", "content-itemknn")
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_ALPHA = 0.05
NOTE_JACCARD_THRESHOLD = 0.20
# Weight placed on the primary-accord term in the pure-content baseline vector.
CONTENT_ACCORD_WEIGHT = 2.0

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CATALOG = REPO_ROOT / "backend" / "app" / "data" / "scentrix_master_cleaned.json"
DEFAULT_ARTIFACTS = REPO_ROOT / "backend" / "ml" / "eval" / "data" / "baseline"
DEFAULT_RUNS_DIR = REPO_ROOT / "backend" / "ml" / "eval" / "runs"


# --------------------------------------------------------------------------- #
# Small pure helpers
# --------------------------------------------------------------------------- #
def _redirect_default_runs_dir(requested: Path, runs_dir: Path = DEFAULT_RUNS_DIR) -> Path:
    """Return ``runs_dir/sessions/<timestamp>`` when ``requested`` is the default runs dir.

    ``requested`` is resolved before comparison so a relative alias of the
    default (e.g. ``--runs-dir backend/ml/eval/runs``) is redirected as well.
    Without this, a plain re-run could silently overwrite the tracked
    published reports in ``runs/``.
    """
    src = Path(requested)
    if src.resolve() == Path(runs_dir).resolve():
        return src.resolve() / "sessions" / datetime.now().strftime("%Y%m%d-%H%M%S")
    return src


def _lower_note_list(value) -> set[str]:
    out: set[str] = set()
    if isinstance(value, (list, tuple)):
        for v in value:
            s = str(v).strip().lower()
            if s:
                out.add(s)
    return out


def primary_accord(item: dict) -> str | None:
    """Lowercased first entry of ``accords``; None if missing/empty."""
    accords = item.get("accords")
    if not isinstance(accords, (list, tuple)) or not accords:
        return None
    first = str(accords[0]).strip().lower()
    return first or None


def note_set(item: dict) -> set[str]:
    """Lowercased union of top/middle/base notes."""
    notes: set[str] = set()
    for key in ("top_notes", "middle_notes", "base_notes"):
        notes |= _lower_note_list(item.get(key))
    return notes


def jaccard(a: set, b: set) -> float:
    """Jaccard over the union of the two note sets (0.0 if union empty)."""
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def sha256_prefix(path: Path, n_prefix: int = 10) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:n_prefix]


def bootstrap_ci(samples, rng: np.random.Generator, n_resamples=BOOTSTRAP_RESAMPLES):
    """Percentile bootstrap (95%) CI over per-trial samples (numpy-only)."""
    arr = np.asarray(samples, dtype=float)
    n = arr.size
    if n == 0:
        return float("nan"), float("nan")
    means = np.empty(n_resamples, dtype=float)
    for r in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        means[r] = arr[idx].mean()
    lo, hi = np.percentile(means, [100 * BOOTSTRAP_ALPHA / 2, 100 * (1 - BOOTSTRAP_ALPHA / 2)])
    return float(lo), float(hi)


def metrics_for_ranking(ranked: list[str], hit_ids: set, r_total: int, ks=SCORE_KS) -> dict:
    """Binary-relevance ranking metrics at each k.

    * P@k    = hits in top-k / min(k, len(ranked))
    * R@k    = hits in top-k / r_total   (collection-level recall)
    * NDCG@k = DCG@k / IDCG@k, IDCG capped at the top-k relevant-cap.
    """
    out: dict[str, float] = {}
    for k in ks:
        top_k = ranked[:k]
        hits = sum(1 for fid in top_k if fid in hit_ids)
        denom = min(k, len(ranked))
        out[f"P@{k}"] = (hits / denom) if denom > 0 else 0.0
        out[f"R@{k}"] = (hits / r_total) if r_total > 0 else 0.0
        dcg = 0.0
        for rank, fid in enumerate(ranked[:k], start=1):
            if fid in hit_ids:
                dcg += 1.0 / math.log2(rank + 1)
        idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(k, r_total) + 1))
        out[f"NDCG@{k}"] = (dcg / idcg) if idcg > 0 else 0.0
    return out


# --------------------------------------------------------------------------- #
# Oracle + data loading
# --------------------------------------------------------------------------- #
def build_relevant(catalog: list[dict]):
    """Build the model-independent oracle.

    Returns (relevant, families, family_members):
      * relevant[fid]      = set of fids similar to fid (symmetric, excludes fid;
                             items with no accords keep empty sets),
      * families           = sorted primary-accord names with >= MIN_FAMILY_SIZE items,
      * family_members     = {accord: [fid in catalog order]}.
    """
    notes: dict[str, set] = {}
    pacc_items: dict[str, list[str]] = defaultdict(list)
    for item in catalog:
        fid = item.get("id")
        if not fid:
            continue
        a = primary_accord(item)
        if a is None:
            continue
        pacc_items[a].append(fid)
        notes[fid] = note_set(item)

    relevant: dict[str, set] = {item.get("id"): set() for item in catalog if item.get("id")}

    for member_ids in pacc_items.values():
        if len(member_ids) < 2:
            continue
        voc = sorted(set().union(*(notes[f] for f in member_ids)))
        if not voc:
            continue
        vidx = {v: i for i, v in enumerate(voc)}
        m = len(member_ids)
        mask = np.zeros((m, len(voc)), dtype=np.uint8)
        for r, fid in enumerate(member_ids):
            for v in notes[fid]:
                mask[r, vidx[v]] = 1
        inter = mask.astype(np.float64) @ mask.astype(np.float64).T
        sizes = mask.astype(np.float64).sum(axis=1)
        union = (sizes[:, None] + sizes[None, :]) - inter
        jac = np.zeros_like(inter)
        nz = union > 0
        jac[nz] = inter[nz] / union[nz]
        jac = np.triu(jac, k=1)
        rows, cols = np.nonzero(jac > NOTE_JACCARD_THRESHOLD)
        for r, c in zip(rows.tolist(), cols.tolist(), strict=True):
            fi, fj = member_ids[r], member_ids[c]
            relevant[fi].add(fj)
            relevant[fj].add(fi)

    families = sorted(f for f in pacc_items if len(pacc_items[f]) >= MIN_FAMILY_SIZE)
    family_members = {f: pacc_items[f] for f in families}
    return relevant, families, family_members


def _load_json(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_content_features(catalog: list[dict]):
    """Pure content profile per item: multi-hot notes + weighted primary accord.

    This is the "dumb content recommender" ablation. No learned embeddings,
    no training — just cosine similarity between a mean-of-seeds content
    profile and each candidate's content profile. If a catalog-derived cosine
    baseline matches or beats the GraphSAGE user vector on the content oracle,
    that is a strong hint the learned embeddings mainly rediscover content
    similarity, and their marginal value must be proven on real behavioral
    data instead (the honest story we report).

    Feature vector: one dimension per note term (across top/middle/base) with
    weight 1.0 if present, plus the primary-accord term with
    ``CONTENT_ACCORD_WEIGHT``. Rows are L2-normalized for cosine.
    """
    vocab: set[str] = set()
    rows: dict[str, dict[str, float]] = {}
    for item in catalog:
        fid = str(item.get("id", ""))
        if not fid:
            continue
        terms: dict[str, float] = {}
        for n in note_set(item):
            terms[n] = 1.0
        pa = primary_accord(item)
        if pa:
            terms[pa] = CONTENT_ACCORD_WEIGHT
        rows[fid] = terms
        vocab.update(terms)

    vlist = sorted(vocab)
    vidx = {v: i for i, v in enumerate(vlist)}
    matrix = np.zeros((len(rows), len(vlist)), dtype=np.float64)
    ids: list[str] = []
    for i, (fid, terms) in enumerate(rows.items()):
        for v, w in terms.items():
            matrix[i, vidx[v]] = w
        ids.append(fid)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix /= np.maximum(norms, 1e-8)
    return ids, {fid: i for i, fid in enumerate(ids)}, matrix


def load_artifacts(artifacts_dir: Path):
    """Load snapshot node ids + embedding matrix."""
    ids_path = artifacts_dir / "node_ids_jaccard.json"
    npy_path = artifacts_dir / "node_embeddings_jaccard.npy"
    if not ids_path.exists() or not npy_path.exists():
        raise FileNotFoundError(
            f"Baseline snapshot incomplete in {artifacts_dir}. Need "
            f"{ids_path.name} and {npy_path.name}."
        )
    ids = _load_json(ids_path)
    matrix = np.load(str(npy_path))
    if matrix.ndim != 2 or matrix.shape[0] != len(ids):
        raise ValueError(
            f"Embedding/counts mismatch: matrix {matrix.shape} vs node ids {len(ids)}"
        )
    fid2idx = {fid: i for i, fid in enumerate(ids)}
    return ids, fid2idx, matrix


def rating_counts(catalog: list[dict]) -> dict[str, float]:
    counts: dict[str, float] = {}
    for item in catalog:
        fid = item.get("id")
        if not fid:
            continue
        try:
            counts[fid] = float(item.get("rating_count", 0))
        except (TypeError, ValueError):
            counts[fid] = 0.0
    return counts


# --------------------------------------------------------------------------- #
# Ranking helpers
# --------------------------------------------------------------------------- #
def rank_by_score(pool: list[str], scores: dict[str, float]) -> list[str]:
    """Descending score, ascending-id tie-break (stable), capped at top N."""
    return sorted(pool, key=lambda fid: (-scores[fid], fid))[:MAX_CANDIDATES]


def rank_scentrix(pool: list[str], matrix: np.ndarray, fid2idx: dict, seed_ids: list[str]):
    """Mean-of-seeds user vector, cosine rank descending. Returns (ranked, scores)."""
    vec = matrix[[fid2idx[s] for s in seed_ids]].mean(axis=0)
    sims = matrix.astype(np.float64) @ vec.astype(np.float64)
    scores = {fid: float(sims[fid2idx[fid]]) for fid in pool}
    return rank_by_score(pool, scores), scores


def rank_popularity(pool: list[str], counts: dict[str, float]) -> list[str]:
    return rank_by_score(pool, counts)


def rank_content(pool: list[str], content_ids: list[str], cid2idx: dict, content_matrix, seed_ids: list[str]):
    """Mean-seed content profile cosine rank (pure content ItemKNN baseline)."""
    vec = content_matrix[[cid2idx[s] for s in seed_ids]].mean(axis=0)
    norm = float(np.linalg.norm(vec))
    if norm <= 0.0:
        return rank_random(pool, np.random.default_rng(0))
    sims = content_matrix @ (vec / norm)
    scores = {fid: float(sims[cid2idx[fid]]) for fid in pool}
    return rank_by_score(pool, scores), scores


def rank_random(pool: list[str], rng: np.random.Generator) -> list[str]:
    perm = rng.permutation(len(pool))
    return [pool[i] for i in perm.tolist()][:MAX_CANDIDATES]


# --------------------------------------------------------------------------- #
# Trial orchestration (pure, in-memory — determinism-testable)
# --------------------------------------------------------------------------- #
def run_eval_impl(
    catalog_ids: list[str],
    relevant: dict[str, set],
    families: list[str],
    family_members: dict[str, list[str]],
    fid2idx: dict,
    matrix: np.ndarray,
    counts: dict[str, float],
    content_ids: list[str],
    cid2idx: dict,
    content_matrix: np.ndarray,
    seed: int,
    trials: int,
    k_values=KS,
):
    """Run the full protocol. Raises AssertionError on any sanity violation (spec f)."""
    rng = np.random.default_rng(seed)
    k_list = tuple(k_values)

    # per-trial metric arrays: metrics[model][k][metric_label] -> list[float]
    metrics_internal = {
        model: {k: {m: [] for m in FINAL_METRICS} for k in k_list} for model in MODEL_ORDER
    }
    win_by_k = {k: [] for k in k_list}
    win_content_by_k = {k: [] for k in k_list}
    family_usage = {k: defaultdict(int) for k in k_list}

    for k in k_list:
        for _trial_idx in range(trials):
            # --- family (>=5 items) chosen uniformly, then k eligible seeds ----
            seed_ids: list[str] = []
            for _attempt in range(100):
                fam = families[int(rng.integers(0, len(families)))]
                members = family_members[fam]
                eligible = [f for f in members if f in fid2idx and relevant.get(f)]
                if len(eligible) >= k:
                    pick = rng.choice(len(eligible), size=k, replace=False)
                    seed_ids = [eligible[int(i)] for i in pick.tolist()]
                    family_usage[k][fam] += 1
                    break
            if not seed_ids:
                raise RuntimeError(
                    f"Could not sample k={k} eligible seeds from any family after 100 attempts"
                )
            seed_set = set(seed_ids)
            assert all(s in fid2idx for s in seed_ids)
            for s in seed_ids:
                assert relevant.get(s), f"trial seed {s} has empty oracle relevant set"

            # --- candidate pool: node-indexed catalog ids, minus seeds ----------
            pool = [fid for fid in catalog_ids if fid in fid2idx and fid not in seed_set]

            # --- oracle relevance of candidates (shared across models) ----------
            hit_ids = {fid for fid in pool if relevant.get(fid) and (relevant[fid] & seed_set)}
            r_total = len(hit_ids)

            # --- model rankings -------------------------------------------------
            sc_ranked, sc_scores = rank_scentrix(pool, matrix, fid2idx, seed_ids)
            pop_ranked = rank_popularity(pool, counts)
            rnd_ranked = rank_random(pool, rng)
            content_ranked, _content_scores = rank_content(
                pool, content_ids, cid2idx, content_matrix, seed_ids
            )
            ranked_by_model = {
                "s-centrix": sc_ranked,
                "popularity": pop_ranked,
                "random": rnd_ranked,
                "content-itemknn": content_ranked,
            }

            available = len(pool)
            expected_len = min(MAX_CANDIDATES, available)
            for model, ranked in ranked_by_model.items():
                assert len(ranked) == expected_len, (
                    f"k={k} model={model}: ranked {len(ranked)} != min({MAX_CANDIDATES}, {available})"
                )
                assert len(set(ranked)) == len(ranked), f"{model}: duplicate ids in ranked list"
                assert not (set(ranked) & seed_set), f"{model}: ranked list contains seed ids"

            for r in range(1, len(sc_ranked)):
                assert sc_scores[sc_ranked[r - 1]] >= sc_scores[sc_ranked[r]], (
                    f"s-centrix scores not sorted descending at rank {r}"
                )

            # --- metrics ----------------------------------------------------------
            res_sc = metrics_for_ranking(sc_ranked, hit_ids, r_total)
            res_pop = metrics_for_ranking(pop_ranked, hit_ids, r_total)
            res_rnd = metrics_for_ranking(rnd_ranked, hit_ids, r_total)
            res_content = metrics_for_ranking(content_ranked, hit_ids, r_total)
            for model, res in (
                ("s-centrix", res_sc),
                ("popularity", res_pop),
                ("random", res_rnd),
                ("content-itemknn", res_content),
            ):
                for m in FINAL_METRICS:
                    metrics_internal[model][k][m].append(res[m])
            win_by_k[k].append(1.0 if res_sc["R@10"] > res_pop["R@10"] else 0.0)
            win_content_by_k[k].append(
                1.0 if res_sc["R@10"] > res_content["R@10"] else 0.0
            )

    # ------------------------------------------------------------------------- #
    # Aggregate + bootstrap CIs
    # ------------------------------------------------------------------------- #
    bc_rng = np.random.default_rng(seed + 1)
    results: dict = {
        "metrics": {},
        "win_rate_vs_popularity_recall10": {},
        "win_rate_vs_content_recall10": {},
        "diagnostics": {},
    }
    for model in MODEL_ORDER:
        per_model = {}
        for k in k_list:
            metric_block = {}
            for m in FINAL_METRICS:
                arr = metrics_internal[model][k][m]
                lo, hi = bootstrap_ci(arr, bc_rng)
                metric_block[m] = {
                    "mean": float(np.mean(arr)),
                    "ci_low": lo,
                    "ci_high": hi,
                }
            per_model[str(k)] = metric_block
        results["metrics"][model] = per_model

    for k in k_list:
        arr = win_by_k[k]
        assert len(arr) == trials, f"win-rate sample count mismatch for k={k}"
        results["win_rate_vs_popularity_recall10"][str(k)] = float(np.mean(arr))
        arr_c = win_content_by_k[k]
        assert len(arr_c) == trials, f"content win-rate sample count mismatch for k={k}"
        results["win_rate_vs_content_recall10"][str(k)] = float(np.mean(arr_c))

    results["diagnostics"]["trials_completed"] = {str(k): trials for k in k_list}
    results["diagnostics"]["family_usage_counts"] = {
        str(k): dict(family_usage[k]) for k in k_list
    }
    return results


# --------------------------------------------------------------------------- #
# End-to-end runner + reporting
# --------------------------------------------------------------------------- #
def run_eval(
    catalog_path: Path,
    artifacts_dir: Path,
    seed: int,
    trials: int,
    k_values=KS,
    runs_dir: Path = DEFAULT_RUNS_DIR,
):
    catalog = _load_json(catalog_path)
    ids, fid2idx, matrix = load_artifacts(artifacts_dir)
    relevant, families, family_members = build_relevant(catalog)
    counts = rating_counts(catalog)
    content_ids, cid2idx, content_matrix = build_content_features(catalog)

    node_index = set(ids)
    catalog_ids = [item["id"] for item in catalog if item["id"] in node_index]

    results = run_eval_impl(
        catalog_ids=catalog_ids,
        relevant=relevant,
        families=families,
        family_members=family_members,
        fid2idx=fid2idx,
        matrix=matrix,
        counts=counts,
        content_ids=content_ids,
        cid2idx=cid2idx,
        content_matrix=content_matrix,
        seed=seed,
        trials=trials,
        k_values=k_values,
    )

    results["snapshot"] = {
        "catalog_n": len(catalog),
        "catalog_path": str(catalog_path),
        "artifacts_dir": str(artifacts_dir),
        "node_ids_in_index": len(ids),
        "matrix": {"shape": list(matrix.shape), "dtype": str(matrix.dtype)},
        "sha256_npy_first10": sha256_prefix(artifacts_dir / "node_embeddings_jaccard.npy"),
    }
    results["protocol"] = {
        "trials_per_k": trials,
        "seed": seed,
        "k_values": list(k_values),
        "max_candidates": MAX_CANDIDATES,
        "min_family_size": MIN_FAMILY_SIZE,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "note_jaccard_threshold": NOTE_JACCARD_THRESHOLD,
    }
    return results


def render_report(results: dict) -> str:
    snap = results["snapshot"]
    proto = results["protocol"]
    lines = [
        "# Scentrix Cold-Start Evaluation (k interactions)",
        f"Data: catalog N={snap['catalog_n']}; snapshot={snap['artifacts_dir']}"
        f" (`{snap['sha256_npy_first10']}`)",
        "Oracle: same primary accord AND note-Jaccard > 0.20",
        f"Simulation: N={proto['trials_per_k']} trials per k, seed={proto['seed']}, "
        "seeds rated 8, seed items excluded from ranking.",
        "LIMITATION: no real interaction history exists — intrinsic capability proxy, not observed behavior.",
        "",
    ]
    for k in proto["k_values"]:
        parts = []
        for model in MODEL_ORDER:
            m = results["metrics"][model][str(k)]
            def fmt(name, m=m):
                return f"{name}={m[name]['mean']:.4f}"
            def fmt_ci(name, m=m):
                return f"{name} {m[name]['ci_low']:.4f}–{m[name]['ci_high']:.4f}"
            parts.append(
                f"{model} [P@5={m['P@5']['mean']:.4f}, P@10={m['P@10']['mean']:.4f}, "
                f"R@10={m['R@10']['mean']:.4f}, NDCG@10={m['NDCG@10']['mean']:.4f}] "
                f"(95% CI: {fmt_ci('P@5')}, {fmt_ci('P@10')}, {fmt_ci('R@10')}, {fmt_ci('NDCG@10')})"
            )
        lines.append(f"k={k}: " + " | ".join(parts))
    wr = results["win_rate_vs_popularity_recall10"]
    lines.append(
        "Win-rate vs popularity (R@10): "
        + " ".join(f"k={k}={wr[str(k)]:.4f}" for k in proto["k_values"])
    )
    wc = results["win_rate_vs_content_recall10"]
    lines.append(
        "Win-rate vs content-itemknn (R@10): "
        + " ".join(f"k={k}={wc[str(k)]:.4f}" for k in proto["k_values"])
    )
    lines.append(
        "Note: content-itemknn is a pure content baseline (multi-hot notes + weighted "
        "primary accord, cosine). It shares features with the oracle, so a win-rate near "
        "0.5 for s-centrix would mean the learned embeddings add little over direct "
        "content matching on this intrinsic proxy."
    )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Scentrix cold-start evaluation (offline, intrinsic proxy)."
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--trials", type=int, default=300)
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=DEFAULT_ARTIFACTS,
        help="Dir with node_embeddings_jaccard.npy + node_ids_jaccard.json",
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help=(
            "Output directory for cold_start_eval.json + cold_start_eval_baseline.md. "
            "When the default runs/ dir is used, results land in a gitignored "
            "runs/sessions/<timestamp>/ subfolder so a plain re-run never rewrites "
            "the tracked published reports in runs/ (pass --runs-dir explicitly, "
            "e.g. .../runs/final, to publish into a named folder)."
        ),
    )
    args = parser.parse_args(argv)

    runs_dir = _redirect_default_runs_dir(args.runs_dir)

    results = run_eval(
        catalog_path=args.catalog,
        artifacts_dir=args.artifacts,
        seed=args.seed,
        trials=args.trials,
        runs_dir=runs_dir,
    )

    runs_dir.mkdir(parents=True, exist_ok=True)
    json_path = runs_dir / "cold_start_eval.json"
    md_path = runs_dir / "cold_start_eval_baseline.md"
    json_path.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    report = render_report(results)
    md_path.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\nResults written to: {runs_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
