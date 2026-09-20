"""Real-behaviour cold-start evaluation on the public Atrafshan perfume dataset.

Imports ONLY stdlib + numpy (+ shared helpers from ``run_cold_start_eval``).
No app imports, no database, no pandas.

Purpose: the intrinsic eval in ``run_cold_start_eval`` has no observed user
behaviour, so its oracle is a content-similarity proxy (which naturally
favours content matching). This module validates the SAME models against
REAL per-user ratings, so a favourite never meets a favourite only because
their notes intersect.

Dataset: Kalashi/Saed "Sentiment-driven community detection" (Atrafshan, a
Persian perfume retailer; MIT). Fields per review: user_id, perfume_id,
perfume_brand/name, scent_specifications (fragrance group + nature),
production_specifications (country, year), and per-user attribute votes
(scent = Arabic-key "manihe"). 36,434 reviews, 2,454 users with a scent
vote, 1,090 perfumes. A perfume row is a vote on a scale 1-10.

Oracle (model-independent, real behaviour):
    candidate is RELEVANT for a user iff the user's held-out scent vote on
    it is >= POSITIVE_THRESHOLD (7) -- the same cut-off the dataset authors
    use for "positive" sentiment in their paper.

Protocol (per k in --k-values):
    For every eligible user (>= k positive votes, plus >= 1 held-out
    positive), sample k of their positive perfumes WITHOUT replacement as
    the cold-start seeds. Each model ranks up to MAX_CANDIDATES pool items
    EXCLUDING the seeds. A candidate is relevant iff it is a held-out
    positive for that user. Trials = min(--trials, eligible users), users
    consumed in RNG-shuffled order (no replacement), so k with a small
    eligible pool reports fewer trials honestly (see diagnostics).

Models (identical trials + oracle):
    popularity    : rank by number of scent votes per perfume.
    top-rated     : rank by mean scent vote per perfume (count tie-break).
    random        : RNG permutation.
    content-itemknn: pure-content ItemKNN on the content available in
                     Atrafshan (brand, fragrance group, nature, origin,
                     decade) -- multi-hot with group/brand boosted, L2
                     cosine. This is the same class of model as
                     run_cold_start_eval's content-itemknn but WITHOUT the
                     rich notes vocabulary, so it can no longer "cheat" by
                     sharing features with the oracle. It answers: does
                     content matching transfer to real behaviour?

    s-centrix is NOT run here: its embedding artifact is keyed to the
    4,559-item Scentrix catalog, which shares no IDs with Atrafshan. Running
    it would require retraining on this dataset and that is out of scope for
    the real-data protocol (documented, not silently skipped).

Win-rate vs popularity (R@10): fraction of trials where content-itemknn
Recall@10 > popularity Recall@10 (ties count for neither).

Determinism: rng = np.random.default_rng(seed); every subset, permutation
and CI index comes from that stream.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

try:
    from ml.eval.run_cold_start_eval import (  # shared numpy helpers, no side effects
        _redirect_default_runs_dir,
        bootstrap_ci,
        metrics_for_ranking,
        rank_by_score,
        rank_random,
        sha256_prefix,
    )
except ImportError:  # run directly from ml/eval/ (python run_real_data_eval.py)
    from run_cold_start_eval import (
        _redirect_default_runs_dir,
        bootstrap_ci,
        metrics_for_ranking,
        rank_by_score,
        rank_random,
        sha256_prefix,
    )

# Persian scent-vote attribute key (independence from console encoding).
SCENT_KEY = "\u0631\u0627\u06cc\u062d\u0647"
POSITIVE_THRESHOLD = 7
MAX_CANDIDATES = 10
KS = (1, 2, 3, 5)
SCORE_KS = (5, 10)
FINAL_METRICS = ("P@5", "P@10", "R@10", "NDCG@10")
MODEL_ORDER = ("popularity", "top-rated", "random", "content-itemknn")
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_ALPHA = 0.05
CONSUMER_RSEED = 42
CONTENT_GROUP_WEIGHT = 2.0
CONTENT_BRAND_WEIGHT = 2.0

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA = REPO_ROOT / "backend" / "ml" / "eval" / "data" / "real" / "atrafshan_data.json"
DEFAULT_RUNS_DIR = REPO_ROOT / "backend" / "ml" / "eval" / "runs"


# --------------------------------------------------------------------------- #
# Data ingestion
# --------------------------------------------------------------------------- #
def load_ratings(data_path: Path):
    """Load Atrafshan reviews -> (ratings, item_content, popularity).

    Ratings: dict[user_id, dict[perfume_id, max scent vote]] (dedupe by max).
    Item content: dict[perfume_id, {brand, group, nature, origin, decade}]
    from the first row mentioning the perfume.
    Popularity: dict[perfume_id, number of scent votes (not reviews)].
    """
    with open(data_path, encoding="utf-8") as fh:
        rows = json.load(fh)

    ratings: dict[str, dict[str, int]] = {}
    content: dict[str, dict] = {}
    popularity: dict[str, int] = {}
    for row in rows:
        pid = str(row.get("perfume_id"))
        votes = (row.get("user_vote_on_perfume") or {}).get("votes") or {}
        if SCENT_KEY not in votes:
            continue
        try:
            score = int(votes[SCENT_KEY])
        except (TypeError, ValueError):
            continue
        popularity[pid] = popularity.get(pid, 0) + 1
        if pid not in content:
            ss = row.get("scent_specifications") or {}
            ps = row.get("production_specifications") or {}
            year = ps.get("release_year") or ""
            try:
                decade = int(year) // 10 * 10
            except (TypeError, ValueError):
                decade = None
            content[pid] = {
                "brand": str(row.get("perfume_brand") or "").strip(),
                "group": str(ss.get("fragrance_group") or ss.get("nature") or "").strip(),
                "nature": str(ss.get("nature") or "").strip(),
                "origin": str(ps.get("origin_country") or "").strip(),
                "decade": decade,
            }
        uid = str(row.get("user_id"))
        per_user = ratings.setdefault(uid, {})
        per_user[pid] = max(per_user.get(pid, 0), score)

    return ratings, content, popularity


# --------------------------------------------------------------------------- #
# Content features (the non-cheating content baseline)
# --------------------------------------------------------------------------- #
def build_content_features(content: dict[dict]):
    """Multi-hot content profile per perfume: brand + group boosted, then
    nature / origin / decade at weight 1.0. L2-normalized for cosine."""
    vocab: set[str] = set()
    rows: dict[str, dict[str, float]] = {}
    for pid, c in content.items():
        terms: dict[str, float] = {}
        for key, w in (
            ("brand", CONTENT_BRAND_WEIGHT),
            ("group", CONTENT_GROUP_WEIGHT),
            ("nature", 1.0),
            ("origin", 1.0),
        ):
            val = c.get(key)
            if val:
                terms[f"{key}:{val}"] = w
        if c.get("decade") is not None:
            terms[f"decade:{c['decade']}"] = 1.0
        if terms:
            rows[pid] = terms
            vocab |= set(terms)
    vlist = sorted(vocab)
    vidx = {v: i for i, v in enumerate(vlist)}
    matrix = np.zeros((len(rows), len(vlist)), dtype=np.float64)
    ids: list[str] = []
    for i, (pid, terms) in enumerate(rows.items()):
        for v, w in terms.items():
            matrix[i, vidx[v]] = w
        ids.append(pid)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix /= np.maximum(norms, 1e-8)
    return ids, {pid: i for i, pid in enumerate(ids)}, matrix


# --------------------------------------------------------------------------- #
# Rankers
# --------------------------------------------------------------------------- #
def rank_top_rated(pool: list[str], counts: dict[str, int], score_sums: dict[str, int]) -> list[str]:
    """Rank by mean scent vote (count as tie-break, then stable id)."""
    scores = {
        fid: (score_sums[fid] / counts[fid] * 1000.0 + counts[fid]) for fid in pool
    }
    return rank_by_score(pool, scores)


def rank_content(pool: list[str], content_ids: list[str], cid2idx: dict, content_matrix, seed_ids: list[str]):
    """Mean-seed content profile cosine rank (real-data content ItemKNN)."""
    vec = content_matrix[[cid2idx[s] for s in seed_ids]].mean(axis=0)
    norm = float(np.linalg.norm(vec))
    if norm <= 0.0:
        return rank_random(pool, np.random.default_rng(0))
    sims = content_matrix @ (vec / norm)
    scores = {fid: float(sims[cid2idx[fid]]) for fid in pool}
    return rank_by_score(pool, scores)


# --------------------------------------------------------------------------- #
# Trial orchestration
# --------------------------------------------------------------------------- #
def run_real_eval_impl(
    ratings: dict[str, dict[str, int]],
    all_perfumes: list[str],
    popularity: dict[str, int],
    score_sums: dict[str, int],
    content_ids: list[str],
    cid2idx: dict,
    content_matrix: np.ndarray,
    seed: int,
    trials: int,
    k_values=KS,
):
    rng = np.random.default_rng(seed)
    k_list = tuple(k_values)

    metrics_internal = {
        model: {k: {m: [] for m in FINAL_METRICS} for k in k_list} for model in MODEL_ORDER
    }
    win_content_vs_pop = {k: [] for k in k_list}
    n_eligible = dict.fromkeys(k_list, 0)

    for k in k_list:
        pos_users = []
        for uid, prefs in ratings.items():
            pos = {pid for pid, s in prefs.items() if s >= POSITIVE_THRESHOLD}
            if len(pos) >= k + 1:
                pos_users.append((uid, sorted(pos)))
        n_eligible[k] = len(pos_users)
        rng.shuffle(pos_users)
        n_trials = min(trials, len(pos_users))

        for _uid, pos in pos_users[:n_trials]:
            seed_ids = [pos[i] for i in rng.choice(len(pos), size=k, replace=False).tolist()]
            assert len(set(seed_ids)) == k
            seed_set = set(seed_ids)

            hit_ids = set(pos) - seed_set
            r_total = len(hit_ids)

            pool = [fid for fid in all_perfumes if fid not in seed_set]

            pop_ranked = rank_by_score(pool, popularity)
            top_ranked = rank_top_rated(pool, popularity, score_sums)
            rnd_ranked = rank_random(pool, rng)
            cont_ranked = rank_content(pool, content_ids, cid2idx, content_matrix, seed_ids)
            ranked_by_model = {
                "popularity": pop_ranked,
                "top-rated": top_ranked,
                "random": rnd_ranked,
                "content-itemknn": cont_ranked,
            }

            available = len(pool)
            expected_len = min(MAX_CANDIDATES, available)
            for model, ranked in ranked_by_model.items():
                assert len(ranked) == expected_len, (
                    f"k={k} model={model}: ranked {len(ranked)} != min({MAX_CANDIDATES}, {available})"
                )
                assert len(set(ranked)) == len(ranked), f"{model}: duplicate ids in ranked list"
                assert not (set(ranked) & seed_set), f"{model}: ranked list contains seed ids"
            for model, ranked in list(ranked_by_model.items())[:2]:
                scores = [popularity[f] if model == "popularity" else score_sums[f] / popularity[f] for f in ranked]
                assert scores == sorted(scores, reverse=True), f"{model}: scores not descending"

            res_pop = metrics_for_ranking(pop_ranked, hit_ids, r_total)
            res_top = metrics_for_ranking(top_ranked, hit_ids, r_total)
            res_rnd = metrics_for_ranking(rnd_ranked, hit_ids, r_total)
            res_cont = metrics_for_ranking(cont_ranked, hit_ids, r_total)
            for model, res in (
                ("popularity", res_pop),
                ("top-rated", res_top),
                ("random", res_rnd),
                ("content-itemknn", res_cont),
            ):
                for m in FINAL_METRICS:
                    metrics_internal[model][k][m].append(res[m])
            win_content_vs_pop[k].append(1.0 if res_cont["R@10"] > res_pop["R@10"] else 0.0)

    # Aggregate + bootstrap CIs
    bc_rng = np.random.default_rng(seed + 1)
    results: dict = {
        "metrics": {},
        "win_rate_content_vs_popularity_recall10": {},
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
        arr = win_content_vs_pop[k]
        results["win_rate_content_vs_popularity_recall10"][str(k)] = float(np.mean(arr))
    results["diagnostics"]["n_trials"] = {str(k): len(win_content_vs_pop[k]) for k in k_list}
    results["diagnostics"]["n_eligible_users"] = {str(k): n_eligible[k] for k in k_list}
    return results


def run_real_eval(
    data_path: Path,
    seed: int,
    trials: int,
    k_values=KS,
    runs_dir: Path = DEFAULT_RUNS_DIR,
):
    ratings, content, popularity = load_ratings(data_path)
    all_perfumes = sorted(popularity)
    score_sums = {
        pid: sum(prefs.get(pid, 0) for uid, prefs in ratings.items()) for pid in all_perfumes
    }
    content_ids, cid2idx, content_matrix = build_content_features(content)

    results = run_real_eval_impl(
        ratings=ratings,
        all_perfumes=all_perfumes,
        popularity=popularity,
        score_sums=score_sums,
        content_ids=content_ids,
        cid2idx=cid2idx,
        content_matrix=content_matrix,
        seed=seed,
        trials=trials,
        k_values=k_values,
    )

    results["dataset"] = {
        "name": "Atrafshan / Kalashi-Saed SentimentDrivenCommunityDetection (public GitHub)",
        "source": "https://github.com/Kalashi-Saed-Collaborations/SentimentDrivenCommunityDetection",
        "license": "MIT",
        "citation": "Kalashi, Saed, Teimourpour, Appl Netw Sci 11, 13 (2026), doi:10.1007/s41109-025-00757-0",
        "path": str(data_path),
        "sha256_npy": sha256_prefix(data_path),
        "reviews": "36,434",
        "users_with_scent_vote": len(ratings),
        "perfumes_with_scent_vote": len(popularity),
        "positive_threshold": POSITIVE_THRESHOLD,
    }
    results["protocol"] = {
        "trials_per_k": trials,
        "seed": seed,
        "k_values": list(k_values),
        "max_candidates": MAX_CANDIDATES,
        "positive_threshold": POSITIVE_THRESHOLD,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "relevance": "held-out scent vote >= 7 on real user data",
        "scentrix_absent": "s-centrix embeddings are catalog-keyed and not run on this data",
    }
    return results


def render_report(results: dict) -> str:
    ds = results["dataset"]
    proto = results["protocol"]
    lines = [
        "# Scentrix Real-Data Cold-Start Evaluation",
        f"Dataset: {ds['name']} (users with scent votes={ds['users_with_scent_vote']}, "
        f"perfumes={ds['perfumes_with_scent_vote']})",
        f"Source: {ds['source']}; license {ds['license']}.",
        "Oracle: REAL held-out user scent votes >= 7 (dataset authors' positivity cut-off).",
        "NOTE: content-itemknn here uses only brand/group/nature/origin/decade (no notes), so it",
        "cannot share features with the oracle the way the intrinsic content baseline did.",
        "",
    ]
    for k in proto["k_values"]:
        parts = []
        for model in MODEL_ORDER:
            m = results["metrics"][model][str(k)]
            parts.append(
                f"{model} [P@5={m['P@5']['mean']:.4f}, P@10={m['P@10']['mean']:.4f}, "
                f"R@10={m['R@10']['mean']:.4f}, NDCG@10={m['NDCG@10']['mean']:.4f}]"
            )
        n_tr = results["diagnostics"]["n_trials"][str(k)]
        lines.append(f"k={k} (trials={n_tr}): " + " | ".join(parts))
    wr = results["win_rate_content_vs_popularity_recall10"]
    lines.append(
        "Win-rate content-itemknn vs popularity (R@10): "
        + " ".join(f"k={k}={wr[str(k)]:.4f}" for k in proto["k_values"])
    )
    lines.append(
        "Caveats: single-market (Persian retailer) implicit vote behaviour; sparse (2,454 users "
        "with votes); trials without replacement = min(requested, eligible users)."
    )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Scentrix real-behaviour cold-start evaluation (Atrafshan dataset)."
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--trials", type=int, default=300)
    parser.add_argument("--k-values", type=int, nargs="+", default=list(KS))
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help=(
            "Output directory for real_data_eval.json + real_data_eval.md. "
            "When the default runs/ dir is used, results land in a gitignored "
            "runs/sessions/<timestamp>/ subfolder (pass explicitly to publish)."
        ),
    )
    args = parser.parse_args(argv)

    runs_dir = _redirect_default_runs_dir(args.runs_dir)
    results = run_real_eval(
        data_path=args.data,
        seed=args.seed,
        trials=args.trials,
        k_values=tuple(args.k_values),
        runs_dir=runs_dir,
    )

    runs_dir.mkdir(parents=True, exist_ok=True)
    json_path = runs_dir / "real_data_eval.json"
    md_path = runs_dir / "real_data_eval.md"
    json_path.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    report = render_report(results)
    md_path.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\nResults written to: {runs_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
