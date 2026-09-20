"""Pure-function unit tests for the real-data evaluation runner.

No app imports, no database, no real data file — imports only the
self-contained runner module (stdlib + numpy + cold-start helpers).
"""

import numpy as np

from ml.eval.run_real_data_eval import (
    build_content_features,
    run_real_eval_impl,
)


def _synth_data():
    """Small ratings grid: 3 cliques of users each loving one brand's perfumes.

    6 users x 6 items; item i belongs to a distinct perfume id. Users 0-1 love
    brand 'A' (items a0..a1, rating 8/9), users 2-3 love brand 'B' items,
    users 4-5 love brand 'C' items; all rate one 'decoy' item at 5 (irrelevant).
    """
    ratings = {}
    content = {}
    popularity = {}
    item_ids = []
    for bi, brand in enumerate(("A", "B", "C")):
        for j in range(2):
            pid = f"{brand}_{j}"
            item_ids.append(pid)
            content[pid] = {"brand": brand, "group": f"g{bi}", "nature": "warm",
                            "origin": "X", "decade": 2010}
    decoy = "decoy1"
    item_ids.append(decoy)
    content[decoy] = {"brand": "Z", "group": "gz", "nature": "cold",
                      "origin": "X", "decade": 2000}
    for i in range(6):
        brand = "ABC"[i // 2]
        uid = f"u{i}"
        prefs = {}
        for j in range(2):
            pid = f"{brand}_{j}"
            prefs[pid] = 8 + j
            popularity[pid] = popularity.get(pid, 0) + 2
        prefs[decoy] = 5
        popularity[decoy] = popularity.get(decoy, 0) + 1
        ratings[uid] = prefs
    return ratings, content, popularity, item_ids


def _run(k_values, seed=7, trials=100, **kw):
    ratings, content, popularity, item_ids = _synth_data()
    content_ids, cid2idx, content_matrix = build_content_features(content)
    base = {
        "ratings": ratings,
        "all_perfumes": item_ids,
        "popularity": popularity,
        "score_sums": {pid: sum(u.get(pid, 0) for u in ratings.values()) for pid in item_ids},
        "content_ids": content_ids,
        "cid2idx": cid2idx,
        "content_matrix": content_matrix,
        "seed": seed,
        "trials": trials,
        "k_values": k_values,
    }
    base.update(kw)
    return run_real_eval_impl(**base)


def test_determinism_same_seed():
    a = _run((1,), seed=42)
    b = _run((1,), seed=42)
    assert a == b


def test_different_seed_differs():
    a = _run((1,), seed=42)
    b = _run((1,), seed=43)
    assert a != b


def test_trials_capped_at_eligible():
    # only 6 users, each with 2 positives -> k=1 needs >=2 positives => 6 eligible
    res = _run((1,), trials=100)
    assert res["diagnostics"]["n_trials"]["1"] == 6
    assert res["diagnostics"]["n_eligible_users"]["1"] == 6


def test_positive_threshold_consistent():
    res = _run((1,), trials=100)
    for model in ("popularity", "top-rated", "random", "content-itemknn"):
        block = res["metrics"][model]["1"]
        for metric in ("P@5", "P@10", "R@10", "NDCG@10"):
            val = block[metric]
            assert 0.0 <= val["mean"] <= 1.0
            assert val["ci_low"] <= val["mean"] <= val["ci_high"] + 1e-12
    assert 0.0 <= res["win_rate_content_vs_popularity_recall10"]["1"] <= 1.0


def test_empty_k_reports_zero_trials():
    # users have exactly 2 positives -> k=2 has nobody eligible, must not crash
    res = _run((1, 2), trials=100)
    assert res["diagnostics"]["n_trials"]["2"] == 0
    assert np.isnan(res["metrics"]["popularity"]["2"]["R@10"]["mean"])


def test_content_features_boost_brand_and_group():
    ratings, content, popularity, item_ids = _synth_data()
    content_ids, cid2idx, matrix = build_content_features(content)
    # a0/a1 share brand A + group g0 -> same profile; a0 vs decoy differ.
    idx_a0 = cid2idx["A_0"]
    idx_a1 = cid2idx["A_1"]
    idx_decoy = cid2idx["decoy1"]
    assert matrix[idx_a0] @ matrix[idx_a1] > matrix[idx_a0] @ matrix[idx_decoy]
    assert matrix[idx_a0] @ matrix[idx_a1] > 0.99  # near-identical profiles
