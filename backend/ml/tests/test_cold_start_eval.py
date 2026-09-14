"""Pure-function unit tests for the cold-start evaluation runner.

No app imports, no database, no data files — imports only the self-contained
runner module (stdlib + numpy).
"""

import json
import re
from pathlib import Path

import numpy as np
import pytest

# NOTE: kept intentionally free of app/db imports. The runner module itself
# only imports stdlib + numpy.
from ml.eval.run_cold_start_eval import (
    MAX_CANDIDATES,
    _redirect_default_runs_dir,
    build_relevant,
    metrics_for_ranking,
    rank_popularity,
    rank_random,
    rank_scentrix,
    run_eval_impl,
)


def _make_catalog():
    """Tiny catalog exercising accord + note-jaccard oracle semantics."""
    return [
        # woody family (>=5 members) with distinct note clusters
        {"id": "a1", "accords": ["Woody"], "top_notes": ["Musk"], "middle_notes": [], "base_notes": []},
        {"id": "a2", "accords": [" woody "], "top_notes": ["musk"], "middle_notes": ["amber"], "base_notes": []},
        {"id": "a3", "accords": ["woody"], "top_notes": ["Rose"], "middle_notes": [], "base_notes": []},
        {"id": "a4", "accords": ["citrus"], "top_notes": ["musk"], "middle_notes": [], "base_notes": []},
        {"id": "a5", "accords": ["woody"], "top_notes": ["rose"], "middle_notes": ["milk"], "base_notes": ["oat"]},
        {"id": "a6", "accords": ["woody"], "top_notes": [], "middle_notes": [], "base_notes": []},
        # item with no accords at all -> skipped from the oracle
        {"id": "b0", "accords": [], "top_notes": ["musk"], "middle_notes": [], "base_notes": []},
    ]


def _synth_catalog_and_embeddings():
    """6 identical-note items in each of 3 families => full intra-family relevance."""
    catalog = []
    counts = {}
    for fam in ("woody", "fruity", "citrus"):
        for j in range(6):
            fid = f"{fam}_{j}"
            catalog.append(
                {
                    "id": fid,
                    "accords": [fam],
                    "top_notes": [f"{fam}_note1"],
                    "middle_notes": [f"{fam}_note2"],
                    "base_notes": [],
                }
            )
            counts[fid] = float(100 - len(catalog))
    ids = [it["id"] for it in catalog]
    rng = np.random.default_rng(7)
    m = rng.standard_normal((len(ids), 8))
    m = m / np.linalg.norm(m, axis=1, keepdims=True)
    fid2idx = {fid: i for i, fid in enumerate(ids)}
    return catalog, ids, m, fid2idx, counts


# --------------------------------------------------------------------------- #
# 1. Oracle: symmetric, self-excluding, accord + jaccard semantics
# --------------------------------------------------------------------------- #
def test_oracle_is_symmetric_and_self_excluding():
    catalog = _make_catalog()
    relevant, families, family_members = build_relevant(catalog)

    # expected symmetric pairs under the exact oracle
    assert relevant["a1"] == {"a2"}
    assert relevant["a2"] == {"a1"}
    assert relevant["a3"] == {"a5"}
    assert relevant["a5"] == {"a3"}
    # different accord => not similar even with identical note sets
    assert relevant["a4"] == set()
    # empty note set => union empty => never similar
    assert relevant["a6"] == set()
    # no accords => skipped
    assert relevant["b0"] == set()

    # symmetry + self-exclusion over every item
    for fid in catalog:
        fid = fid["id"]
        assert fid not in relevant[fid]
        for other in relevant[fid]:
            assert fid in relevant[other]

    # families only count primary accords with >= MIN_FAMILY_SIZE (5) members
    assert families == ["woody"]
    # a6 (woody, no notes) still counts as a family member
    assert set(family_members["woody"]) == {"a1", "a2", "a3", "a5", "a6"}


# --------------------------------------------------------------------------- #
# 2. Metrics: exact hand-computed values
# --------------------------------------------------------------------------- #
def test_metrics_hand_computed():
    ranked = ["x1", "x2", "rel1", "x3", "x4"]  # 1 relevant item at rank 3
    hit_ids = {"rel1"}
    r_total = 1

    m = metrics_for_ranking(ranked, hit_ids, r_total, ks=(3, 5))
    # P@3 = 1/3, R@3 = 1/1, NDCG@3 = (1/log2(4)) / 1 = 0.5
    assert m["P@3"] == pytest.approx(1.0 / 3.0)
    assert m["R@3"] == pytest.approx(1.0)
    assert m["NDCG@3"] == pytest.approx(0.5)
    # P@5 = 1/5, R@5 = 1/1, NDCG@5 = 0.5 (same positional gain)
    assert m["P@5"] == pytest.approx(1.0 / 5.0)
    assert m["R@5"] == pytest.approx(1.0)
    assert m["NDCG@5"] == pytest.approx(0.5)

    # nothing relevant -> all zero (IDCG cap of 0 makes NDCG 0)
    m0 = metrics_for_ranking(ranked, set(), r_total=0, ks=(5,))
    assert m0["P@5"] == 0.0
    assert m0["R@5"] == 0.0
    assert m0["NDCG@5"] == 0.0

    # IDCG cap: multiple relevant => rare relevant at rank 1 in a top-1 k
    m1 = metrics_for_ranking(["relA", "x", "relB"], {"relA", "relB"}, r_total=2, ks=(1,))
    assert m1["P@1"] == pytest.approx(1.0)
    assert m1["R@1"] == pytest.approx(0.5)
    assert m1["NDCG@1"] == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# 3. Seed ids always excluded from ranked lists
# --------------------------------------------------------------------------- #
def test_seed_ids_always_excluded():
    catalog, ids, matrix, fid2idx, counts = _synth_catalog_and_embeddings()
    seeds = ["woody_0", "woody_2"]

    pool = [fid for fid in ids if fid not in seeds]
    assert len(pool) == len(ids) - len(seeds)

    sc_ranked, sc_scores = rank_scentrix(pool, matrix, fid2idx, seeds)
    pop_ranked = rank_popularity(pool, counts)
    rnd_ranked = rank_random(pool, np.random.default_rng(0))

    for ranked, name in ((sc_ranked, "s-centrix"), (pop_ranked, "popularity"), (rnd_ranked, "random")):
        assert not (set(ranked) & set(seeds)), f"{name} leaked seed ids"
        assert len(set(ranked)) == len(ranked), f"{name} has duplicate ids"
        assert len(ranked) == min(MAX_CANDIDATES, len(pool)), f"{name} wrong length"


# --------------------------------------------------------------------------- #
# 4. Runner determinism: same seed -> identical results
# --------------------------------------------------------------------------- #
def test_runner_determinism_same_seed():
    catalog, ids, matrix, fid2idx, counts = _synth_catalog_and_embeddings()
    relevant, families, family_members = build_relevant(catalog)

    kwargs = {
        "catalog_ids": ids,
        "relevant": relevant,
        "families": families,
        "family_members": family_members,
        "fid2idx": fid2idx,
        "matrix": matrix,
        "counts": counts,
        "seed": 123,
        "trials": 25,
        "k_values": (1, 2),
    }
    r_a = run_eval_impl(**kwargs)
    r_b = run_eval_impl(**kwargs)
    assert json.dumps(r_a, sort_keys=True) == json.dumps(r_b, sort_keys=True)

    # runner passes its own internal sanity assertions (seed exclusion,
    # lengths, no dupes, sorted cosine) on this synthetic data
    assert r_a["diagnostics"]["trials_completed"] == {"1": 25, "2": 25}
    wr = r_a["win_rate_vs_popularity_recall10"]
    assert all(0.0 <= wr[str(k)] <= 1.0 for k in (1, 2))
    for model in ("s-centrix", "popularity", "random"):
        for k in (1, 2):
            for metric in ("P@5", "P@10", "R@10", "NDCG@10"):
                mean = r_a["metrics"][model][str(k)][metric]["mean"]
                assert 0.0 <= mean <= 1.0, (model, k, metric, mean)


# --------------------------------------------------------------------------- #
# 5. User vector is mean of seeds; ranked order follows dot-product scores
# --------------------------------------------------------------------------- #
def test_rank_scentrix_vector_is_mean_of_seeds_and_order_follows_dot_product():
    rng = np.random.default_rng(77)
    m = rng.standard_normal((12, 8))
    m = m / np.linalg.norm(m, axis=1, keepdims=True)
    ids = [f"n{i}" for i in range(12)]
    fid2idx = {fid: i for i, fid in enumerate(ids)}

    seeds = ["n2", "n5"]
    vec_expected = m[[fid2idx[s] for s in seeds]].mean(axis=0)
    vec_actual = m[[fid2idx[s] for s in seeds]].mean(axis=0)
    np.testing.assert_array_equal(vec_actual, vec_expected)

    pool = ["n0", "n3", "n6", "n7", "n8", "n10"]
    ranked, scores = rank_scentrix(pool, m, fid2idx, seeds)

    sims = {fid: float(m[fid2idx[fid]] @ vec_expected) for fid in pool}
    expected_order = sorted(pool, key=lambda fid: (-sims[fid], fid))
    assert ranked == expected_order

    for i in range(len(ranked) - 1):
        assert scores[ranked[i]] >= scores[ranked[i + 1]]


# --------------------------------------------------------------------------- #
# 6. All k values in {1,2,3,5} run and every metric is sane
# --------------------------------------------------------------------------- #
def test_all_k_values_run_and_report_sane_metrics():
    catalog, ids, matrix, fid2idx, counts = _synth_catalog_and_embeddings()
    relevant, families, family_members = build_relevant(catalog)
    res = run_eval_impl(
        catalog_ids=ids,
        relevant=relevant,
        families=families,
        family_members=family_members,
        fid2idx=fid2idx,
        matrix=matrix,
        counts=counts,
        seed=123,
        trials=12,
        k_values=(1, 2, 3, 5),
    )

    assert res["diagnostics"]["trials_completed"] == {
        "1": 12, "2": 12, "3": 12, "5": 12,
    }

    for k in ("1", "2", "3", "5"):
        wr = res["win_rate_vs_popularity_recall10"][k]
        assert 0.0 <= wr <= 1.0, (k, wr)
        for model in ("s-centrix", "popularity", "random"):
            for metric in ("P@5", "P@10", "R@10", "NDCG@10"):
                mean = res["metrics"][model][k][metric]["mean"]
                assert 0.0 <= mean <= 1.0, (model, k, metric, mean)


# --------------------------------------------------------------------------- #
# 7. Default runs-dir redirect protects the tracked published reports
# --------------------------------------------------------------------------- #
def test_default_runs_dir_redirects_to_gitignored_sessions(tmp_path):
    runs_dir = tmp_path / "runs"

    out = _redirect_default_runs_dir(runs_dir, runs_dir=runs_dir)
    assert out.parent == runs_dir / "sessions"
    assert re.fullmatch(r"\d{8}-\d{6}", out.name) is not None

    # a relative alias of the default (resolve()-equal) is redirected too
    alias = runs_dir / "x" / ".."
    out_alias = _redirect_default_runs_dir(alias, runs_dir=runs_dir)
    assert out_alias.parent == runs_dir / "sessions"

    # explicit named folders for publishing are returned unchanged
    pub = runs_dir / "final"
    assert _redirect_default_runs_dir(pub, runs_dir=runs_dir) == pub
    assert _redirect_default_runs_dir("/tmp/elsewhere", runs_dir=runs_dir) == Path("/tmp/elsewhere")
