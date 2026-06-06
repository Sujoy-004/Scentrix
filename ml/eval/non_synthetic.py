"""Non-synthetic evaluations: Design F (self-consistency), C (multi-signal), B (accord retrieval).

Usage:
    python -m ml.eval.non_synthetic
"""

import json
import logging
import random
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
logger = logging.getLogger("non_synthetic")


# ── Data loading ──────────────────────────────────────────────────────────────

def load_catalog(path: str = "ml/data/scentrix_master.json") -> dict:
    with open(path, encoding="utf-8") as f:
        catalog = json.load(f)
    item_map = {}
    for item in catalog:
        fid = item["id"]
        accords = [a.lower() for a in (item.get("accords") or [])]
        item_map[fid] = {
            "brand": str(item.get("brand", "")).lower(),
            "primary_accord": accords[0] if accords else "Unknown",
            "rating_count": item.get("rating_count", 0),
            "rating_value": item.get("rating_value", 0.0),
        }
    return item_map


def load_gs_embeddings(
    emb_path: str = "ml/models/serving/v1/node_embeddings_jaccard.npy",
    ids_path: str = "ml/models/serving/v1/node_ids_jaccard.json",
):
    embeddings = np.load(emb_path)
    with open(ids_path, encoding="utf-8") as f:
        node_ids = json.load(f)
    id_to_idx = {fid: i for i, fid in enumerate(node_ids)}
    return embeddings, node_ids, id_to_idx


def build_432_features(item_map: dict, seed: int = 42) -> tuple[np.ndarray, list[str], dict]:
    emb_path = "ml/data/embeddings.npy"
    idx_path = "ml/data/embedding_index.json"
    embeddings_384 = np.load(emb_path)
    with open(idx_path, encoding="utf-8") as f:
        emb_index = json.load(f)

    all_accords = sorted({v["primary_accord"] for v in item_map.values()})
    accord_to_idx = {a: i for i, a in enumerate(all_accords)}

    features = []
    feature_ids = []
    for fid, meta in item_map.items():
        if fid not in emb_index:
            continue
        accord = meta["primary_accord"]
        accord_vec = np.zeros(len(all_accords), dtype=np.float32)
        if accord in accord_to_idx:
            accord_vec[accord_to_idx[accord]] = 1.0
        emb_vec = embeddings_384[emb_index[fid]].astype(np.float32)
        feature_vec = np.concatenate([accord_vec, emb_vec])
        features.append(feature_vec)
        feature_ids.append(fid)

    features = np.array(features, dtype=np.float32)
    norms = np.linalg.norm(features, axis=1, keepdims=True)
    features = features / (norms + 1e-8)
    id_to_idx = {fid: i for i, fid in enumerate(feature_ids)}
    return features, feature_ids, id_to_idx


# ── Centroid + KNN ─────────────────────────────────────────────────────────────

def compute_centroid(
    embeddings: np.ndarray,
    id_to_idx: dict,
    seed_ids: list[str],
    weights: list[float] | None = None,
):
    indices = [id_to_idx[sid] for sid in seed_ids if sid in id_to_idx]
    if not indices:
        return None

    seed_embs = embeddings[indices]
    if weights is not None:
        valid_w = np.array(
            [w for sid, w in zip(seed_ids, weights) if sid in id_to_idx],
            dtype=np.float64,
        )
    else:
        valid_w = np.ones(len(indices), dtype=np.float64)

    w_sum = np.sum(valid_w)
    if w_sum <= 0:
        return None

    centroid = np.dot(valid_w, seed_embs) / w_sum
    norm = np.linalg.norm(centroid)
    if norm > 0:
        centroid = centroid / norm
    return centroid


def knn_search(
    embeddings: np.ndarray,
    node_ids: list[str],
    centroid: np.ndarray,
    top_k: int = 10,
    exclude_ids: set | None = None,
):
    similarities = np.dot(embeddings, centroid)
    top_indices = np.argsort(similarities)[::-1]

    exclude = exclude_ids or set()
    results = []
    for idx in top_indices:
        fid = node_ids[idx]
        if fid in exclude:
            continue
        results.append((fid, float(similarities[idx])))
        if len(results) >= top_k:
            break
    return results


# ── Metrics ────────────────────────────────────────────────────────────────────

def compute_ndcg_scores(
    predictions: dict[str, list[tuple[str, float]]],
    ground_truth: dict[str, set[str]],
    k: int = 10,
) -> list[float]:
    scores = []
    for qid, ranked in predictions.items():
        relevant = ground_truth.get(qid, set())
        if not relevant:
            continue

        dcg = 0.0
        n_found = 0
        for rank, (item_id, _) in enumerate(ranked[:k], start=1):
            if item_id in relevant:
                dcg += 1.0 / np.log2(rank + 1)
                n_found += 1

        n_rel = min(len(relevant), k)
        idcg = sum(1.0 / np.log2(i + 1) for i in range(1, n_rel + 1))
        ndcg = dcg / idcg if idcg > 0 else 0.0
        scores.append(ndcg)
    return scores


def bootstrap_paired_test(
    a: list[float], b: list[float], n_resamples: int = 10000, seed: int = 42
) -> float:
    rng = np.random.default_rng(seed)
    diffs = np.array(a) - np.array(b)
    observed = np.mean(diffs)
    if abs(observed) < 1e-15:
        return 1.0
    count = 0
    for _ in range(n_resamples):
        mean_perm = np.mean(diffs * rng.choice([-1, 1], size=len(diffs)))
        if mean_perm >= observed:
            count += 1
    return (count + 1) / (n_resamples + 1)


def cohens_d(a: list[float], b: list[float]) -> float:
    arr_a = np.array(a, dtype=float)
    arr_b = np.array(b, dtype=float)
    diff = float(np.mean(arr_a) - np.mean(arr_b))
    pooled = np.sqrt((np.var(arr_a, ddof=1) + np.var(arr_b, ddof=1)) / 2)
    return diff / pooled if pooled > 0 else 0.0


def mean_std(values: list[float]) -> tuple[float, float]:
    return float(np.mean(values)), float(np.std(values, ddof=1))


# ── Ground truth builders ──────────────────────────────────────────────────────

def build_brand_or_accord(item_map: dict) -> dict[str, set[str]]:
    logger.info("  Building brand_or_accord ground truth...")
    brands: dict[str, list[str]] = {}
    accords: dict[str, list[str]] = {}
    for fid, meta in item_map.items():
        brands.setdefault(meta["brand"], []).append(fid)
        accords.setdefault(meta["primary_accord"], []).append(fid)

    gt = {}
    for fid, meta in item_map.items():
        relevant = set()
        relevant.update(brands.get(meta["brand"], []))
        relevant.update(accords.get(meta["primary_accord"], []))
        relevant.discard(fid)
        if relevant:
            gt[fid] = relevant
    return gt


def build_brand_and_accord(item_map: dict) -> dict[str, set[str]]:
    logger.info("  Building brand_and_accord ground truth...")
    groups: dict[tuple[str, str], list[str]] = {}
    for fid, meta in item_map.items():
        key = (meta["brand"], meta["primary_accord"])
        groups.setdefault(key, []).append(fid)

    gt = {}
    for fid, meta in item_map.items():
        key = (meta["brand"], meta["primary_accord"])
        relevant = set(groups.get(key, []))
        relevant.discard(fid)
        if relevant:
            gt[fid] = relevant
    return gt


def build_accord_groups(item_map: dict) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for fid, meta in item_map.items():
        groups.setdefault(meta["primary_accord"], []).append(fid)
    return groups


# ── Evaluation designs ─────────────────────────────────────────────────────────

def evaluate_design_f(
    label: str,
    embeddings: np.ndarray,
    node_ids: list[str],
    id_to_idx: dict,
    ground_truth: dict[str, set[str]],
) -> dict:
    """Design F: centroid = each item's own embedding, KNN, NDCG@10."""
    logger.info("  Running Design-F (%s) ...", label)
    eval_ids = [fid for fid in node_ids if fid in ground_truth]
    predictions = {}
    for fid in eval_ids:
        centroid = compute_centroid(embeddings, id_to_idx, [fid])
        if centroid is None:
            continue
        predictions[fid] = knn_search(embeddings, node_ids, centroid, exclude_ids={fid})
    scores = compute_ndcg_scores(predictions, ground_truth)
    logger.info("    %s: N=%d, mean NDCG@10=%.6f", label, len(scores), np.mean(scores) if scores else 0)
    return {"scores": scores, "n": len(scores)}


def evaluate_design_c(
    label: str,
    embeddings: np.ndarray,
    node_ids: list[str],
    id_to_idx: dict,
    item_map: dict,
    ground_truth: dict[str, set[str]],
    n_seeds: int = 3,
) -> dict:
    """Design C: top-K popular same-brand-or-accord seeds → centroid → KNN."""
    logger.info("  Running Design-C (%s) ...", label)
    eval_ids = [fid for fid in node_ids if fid in ground_truth]
    predictions = {}
    for fid in eval_ids:
        meta = item_map[fid]
        brand = meta["brand"]
        accord = meta["primary_accord"]
        candidates = [oid for oid in node_ids if oid != fid and oid in item_map
                      and (item_map[oid]["brand"] == brand or item_map[oid]["primary_accord"] == accord)]
        candidates.sort(key=lambda oid: item_map[oid]["rating_count"], reverse=True)
        seeds = candidates[:n_seeds]
        if not seeds:
            continue
        weights = [float(item_map[sid]["rating_count"]) for sid in seeds]
        centroid = compute_centroid(embeddings, id_to_idx, seeds, weights)
        if centroid is None:
            continue
        predictions[fid] = knn_search(embeddings, node_ids, centroid, exclude_ids=set(seeds))
    scores = compute_ndcg_scores(predictions, ground_truth)
    logger.info("    %s: N=%d, mean NDCG@10=%.6f", label, len(scores), np.mean(scores) if scores else 0)
    return {"scores": scores, "n": len(scores)}


def evaluate_design_b(
    label: str,
    embeddings: np.ndarray,
    node_ids: list[str],
    id_to_idx: dict,
    item_map: dict,
    accord_groups: dict[str, list[str]],
    min_group_size: int = 4,
    n_seeds: int = 3,
) -> dict:
    """Design B: per-accord, top-K popular seeds → centroid → KNN → retrieve rest of accord."""
    logger.info("  Running Design-B (%s) ...", label)
    node_set = set(node_ids)
    all_scores = []
    for accord, members in accord_groups.items():
        members_in = [fid for fid in members if fid in node_set]
        if len(members_in) < min_group_size:
            continue
        members_in.sort(key=lambda fid: item_map[fid]["rating_count"], reverse=True)
        seeds = members_in[:n_seeds]
        ground = set(members_in[n_seeds:])
        if not seeds or not ground:
            continue
        weights = [float(item_map[sid]["rating_count"]) for sid in seeds]
        centroid = compute_centroid(embeddings, id_to_idx, seeds, weights)
        if centroid is None:
            continue
        results = knn_search(embeddings, node_ids, centroid, top_k=10, exclude_ids=set(seeds))
        # compute NDCG@10 for this accord
        dcg = 0.0
        for rank, (item_id, _) in enumerate(results[:10], start=1):
            if item_id in ground:
                dcg += 1.0 / np.log2(rank + 1)
        n_rel = min(len(ground), 10)
        idcg = sum(1.0 / np.log2(i + 1) for i in range(1, n_rel + 1))
        ndcg = dcg / idcg if idcg > 0 else 0.0
        all_scores.append(ndcg)
    logger.info("    %s: accords=%d, mean NDCG@10=%.6f", label, len(all_scores), np.mean(all_scores) if all_scores else 0)
    return {"scores": all_scores, "n": len(all_scores)}


# ── Baselines ──────────────────────────────────────────────────────────────────

def popularity_ranked(item_map: dict, node_ids: list[str]) -> list[str]:
    ids_with_rc = [fid for fid in node_ids if fid in item_map]
    ids_with_rc.sort(key=lambda fid: item_map[fid]["rating_count"], reverse=True)
    return ids_with_rc


def evaluate_popularity(
    ground_truth: dict[str, set[str]],
    pop_ranking: list[str],
    k: int = 10,
) -> list[float]:
    scores = []
    for qid, relevant in ground_truth.items():
        if not relevant:
            continue
        top_k = pop_ranking[:k]
        dcg = 0.0
        for rank, item_id in enumerate(top_k, start=1):
            if item_id in relevant:
                dcg += 1.0 / np.log2(rank + 1)
        n_rel = min(len(relevant), k)
        idcg = sum(1.0 / np.log2(i + 1) for i in range(1, n_rel + 1))
        ndcg = dcg / idcg if idcg > 0 else 0.0
        scores.append(ndcg)
    return scores


def evaluate_random(
    ground_truth: dict[str, set[str]],
    all_ids: list[str],
    k: int = 10,
    seed: int = 42,
    n_samples: int = 5,
) -> list[float]:
    rng = random.Random(seed)
    all_scores = []
    for _ in range(n_samples):
        shuffled = all_ids.copy()
        rng.shuffle(shuffled)
        top_k = shuffled[:k]
        for qid, relevant in ground_truth.items():
            if not relevant:
                continue
            dcg = 0.0
            for rank, item_id in enumerate(top_k, start=1):
                if item_id in relevant:
                    dcg += 1.0 / np.log2(rank + 1)
            n_rel = min(len(relevant), k)
            idcg = sum(1.0 / np.log2(i + 1) for i in range(1, n_rel + 1))
            ndcg = dcg / idcg if idcg > 0 else 0.0
            all_scores.append(ndcg)
    return all_scores


# ── Reporting ──────────────────────────────────────────────────────────────────

def print_design_header(title: str):
    logger.info("")
    logger.info("=" * 80)
    safe = title.replace("\u2192", "->").replace("\u2014", "--")
    logger.info("  %s", safe)
    logger.info("=" * 80)


def print_design_results(results: dict[str, dict], method_order: list[str]):
    methods = [m for m in method_order if m in results]
    if not methods:
        logger.info("  No results.")
        return

    logger.info(f"  {'Method':<30s} {'N':>6s} {'Mean':>10s} {'Std':>10s}")
    logger.info("  " + "-" * 60)
    for m in methods:
        r = results[m]
        if r["scores"]:
            mn, sd = mean_std(r["scores"])
            logger.info(f"  {m:<30s} {r['n']:>6d} {mn:>10.6f} {sd:>10.6f}")
        else:
            logger.info(f"  {m:<30s} {r['n']:>6d} {'N/A':>10s} {'N/A':>10s}")


def print_pairwise(results: dict[str, dict], method_a: str, method_b: str):
    if method_a not in results or method_b not in results:
        return
    scores_a = results[method_a]["scores"]
    scores_b = results[method_b]["scores"]

    # Pair: align by min length (paired by position in a given design)
    n = min(len(scores_a), len(scores_b))
    if n < 2:
        return
    paired_a = scores_a[:n]
    paired_b = scores_b[:n]

    p = bootstrap_paired_test(paired_a, paired_b)
    d = cohens_d(paired_a, paired_b)
    diff = np.mean(paired_a) - np.mean(paired_b)
    logger.info(
        f"  {method_a:<30s} vs {method_b:<30s}: "
        f"diff={diff:+.6f}  p={p:.4f}  d={d:+.4f}"
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 80)
    logger.info("  NON-SYNTHETIC TIER 2 EVALUATION")
    logger.info("  Data: scentrix_master.json (4,577 items with ratings)")
    logger.info("=" * 80)

    # 1. Load data
    logger.info("\n[1] Loading data...")
    item_map = load_catalog()
    logger.info("  Catalog items: %d", len(item_map))

    gs_emb, gs_ids, gs_id_to_idx = load_gs_embeddings()
    logger.info("  GraphSAGE-Jaccard: %d items, %s", len(gs_ids), gs_emb.shape)

    fo_features, fo_ids, fo_id_to_idx = build_432_features(item_map)
    logger.info("  Feature-Only: %d items, %s", len(fo_ids), fo_features.shape)

    # 2. Build ground truth
    logger.info("\n[2] Building ground truth...")
    gt_brand_or = build_brand_or_accord(item_map)
    gt_brand_and = build_brand_and_accord(item_map)
    accord_groups = build_accord_groups(item_map)
    logger.info("  brand_or_accord: %d queries", len(gt_brand_or))
    logger.info("  brand_and_accord: %d queries", len(gt_brand_and))
    logger.info("  accord_groups: %d groups", len(accord_groups))

    # 3. Popularity ranking
    logger.info("\n[3] Computing popularity ranking...")
    all_gs_ids = [fid for fid in gs_ids if fid in item_map]
    all_fo_ids = [fid for fid in fo_ids if fid in item_map]
    pop_ranking_gs = popularity_ranked(item_map, all_gs_ids)
    pop_ranking_fo = popularity_ranked(item_map, all_fo_ids)
    logger.info("  Popularity ranking: %d items (GS), %d items (FO)", len(pop_ranking_gs), len(pop_ranking_fo))

    results = {}

    # ═══════════════════════════════════════════════════════════════════════════
    # DESIGN F: Centroid Self-Consistency
    # ═══════════════════════════════════════════════════════════════════════════
    print_design_header("DESIGN F: Centroid Self-Consistency (single-item centroid, brand_or_accord GT)")

    # GS
    gt_f_gs = {fid: gt_brand_or[fid] for fid in gs_ids if fid in gt_brand_or}
    r = evaluate_design_f("GraphSAGE-Jaccard", gs_emb, gs_ids, gs_id_to_idx, gt_f_gs)
    results["GraphSAGE-Jaccard_F"] = r

    # FO
    gt_f_fo = {fid: gt_brand_or[fid] for fid in fo_ids if fid in gt_brand_or}
    r = evaluate_design_f("Feature-Only", fo_features, fo_ids, fo_id_to_idx, gt_f_fo)
    results["Feature-Only_F"] = r

    # Popularity
    scores = evaluate_popularity(gt_f_gs, pop_ranking_gs)
    results["Popularity_F"] = {"scores": scores, "n": len(scores)}
    logger.info("  Popularity: N=%d, mean NDCG@10=%.6f", len(scores), np.mean(scores) if scores else 0)

    # Random
    scores = evaluate_random(gt_f_gs, all_gs_ids)
    results["Random_F"] = {"scores": scores, "n": len(scores)}
    logger.info("  Random: N=%d, mean NDCG@10=%.6f", len(scores), np.mean(scores) if scores else 0)

    print_design_results(results, ["GraphSAGE-Jaccard_F", "Feature-Only_F", "Popularity_F", "Random_F"])
    logger.info("\n  Pairwise comparisons (Design F):")
    print_pairwise(results, "GraphSAGE-Jaccard_F", "Feature-Only_F")
    print_pairwise(results, "GraphSAGE-Jaccard_F", "Popularity_F")
    print_pairwise(results, "GraphSAGE-Jaccard_F", "Random_F")
    print_pairwise(results, "Feature-Only_F", "Popularity_F")

    # ═══════════════════════════════════════════════════════════════════════════
    # DESIGN C: Multi-Signal Retrieval
    # ═══════════════════════════════════════════════════════════════════════════
    print_design_header("DESIGN C: Multi-Signal Retrieval (top-3 popular brand_or_accord seeds, brand+accord GT)")

    # GS
    gt_c_gs = {fid: gt_brand_and[fid] for fid in gs_ids if fid in gt_brand_and}
    r = evaluate_design_c("GraphSAGE-Jaccard", gs_emb, gs_ids, gs_id_to_idx, item_map, gt_c_gs)
    results["GraphSAGE-Jaccard_C"] = r

    # FO
    gt_c_fo = {fid: gt_brand_and[fid] for fid in fo_ids if fid in gt_brand_and}
    r = evaluate_design_c("Feature-Only", fo_features, fo_ids, fo_id_to_idx, item_map, gt_c_fo)
    results["Feature-Only_C"] = r

    # Popularity
    scores = evaluate_popularity(gt_c_gs, pop_ranking_gs)
    results["Popularity_C"] = {"scores": scores, "n": len(scores)}
    logger.info("  Popularity: N=%d, mean NDCG@10=%.6f", len(scores), np.mean(scores) if scores else 0)

    # Random
    scores = evaluate_random(gt_c_gs, all_gs_ids)
    results["Random_C"] = {"scores": scores, "n": len(scores)}
    logger.info("  Random: N=%d, mean NDCG@10=%.6f", len(scores), np.mean(scores) if scores else 0)

    print_design_results(results, ["GraphSAGE-Jaccard_C", "Feature-Only_C", "Popularity_C", "Random_C"])
    logger.info("\n  Pairwise comparisons (Design C):")
    print_pairwise(results, "GraphSAGE-Jaccard_C", "Feature-Only_C")
    print_pairwise(results, "GraphSAGE-Jaccard_C", "Popularity_C")
    print_pairwise(results, "GraphSAGE-Jaccard_C", "Random_C")
    print_pairwise(results, "Feature-Only_C", "Popularity_C")

    # ═══════════════════════════════════════════════════════════════════════════
    # DESIGN B: Accord Retrieval
    # ═══════════════════════════════════════════════════════════════════════════
    print_design_header("DESIGN B: Accord Retrieval (per-accord seeds -> centroid -> retrieve rest of accord)")

    # GS
    r = evaluate_design_b("GraphSAGE-Jaccard", gs_emb, gs_ids, gs_id_to_idx, item_map, accord_groups)
    results["GraphSAGE-Jaccard_B"] = r

    # FO
    r = evaluate_design_b("Feature-Only", fo_features, fo_ids, fo_id_to_idx, item_map, accord_groups)
    results["Feature-Only_B"] = r

    gs_set = set(gs_ids)
    # Popularity (per-accord: same static ranking)
    scores_b_pop = []
    for accord, members in accord_groups.items():
        members_in = [fid for fid in members if fid in gs_set]
        if len(members_in) < 4:
            continue
        members_in.sort(key=lambda fid: item_map[fid]["rating_count"], reverse=True)
        seeds = set(members_in[:3])
        ground = set(members_in[3:])
        if not ground:
            continue
        top_k = pop_ranking_gs[:10]
        dcg = 0.0
        for rank, item_id in enumerate(top_k, start=1):
            if item_id in ground:
                dcg += 1.0 / np.log2(rank + 1)
        n_rel = min(len(ground), 10)
        idcg = sum(1.0 / np.log2(i + 1) for i in range(1, n_rel + 1))
        ndcg = dcg / idcg if idcg > 0 else 0.0
        scores_b_pop.append(ndcg)
    results["Popularity_B"] = {"scores": scores_b_pop, "n": len(scores_b_pop)}
    logger.info("  Popularity: accords=%d, mean NDCG@10=%.6f", len(scores_b_pop), np.mean(scores_b_pop) if scores_b_pop else 0)

    # Random (per-accord)
    rng = random.Random(42)
    scores_b_rnd = []
    for accord, members in accord_groups.items():
        members_in = [fid for fid in members if fid in gs_set]
        if len(members_in) < 4:
            continue
        members_in.sort(key=lambda fid: item_map[fid]["rating_count"], reverse=True)
        ground = set(members_in[3:])
        if not ground:
            continue
        shuffled = all_gs_ids.copy()
        rng.shuffle(shuffled)
        top_k = shuffled[:10]
        dcg = 0.0
        for rank, item_id in enumerate(top_k, start=1):
            if item_id in ground:
                dcg += 1.0 / np.log2(rank + 1)
        n_rel = min(len(ground), 10)
        idcg = sum(1.0 / np.log2(i + 1) for i in range(1, n_rel + 1))
        ndcg = dcg / idcg if idcg > 0 else 0.0
        scores_b_rnd.append(ndcg)
    results["Random_B"] = {"scores": scores_b_rnd, "n": len(scores_b_rnd)}
    logger.info("  Random: accords=%d, mean NDCG@10=%.6f", len(scores_b_rnd), np.mean(scores_b_rnd) if scores_b_rnd else 0)

    print_design_results(results, ["GraphSAGE-Jaccard_B", "Feature-Only_B", "Popularity_B", "Random_B"])
    logger.info("\n  Pairwise comparisons (Design B):")
    print_pairwise(results, "GraphSAGE-Jaccard_B", "Feature-Only_B")
    print_pairwise(results, "GraphSAGE-Jaccard_B", "Popularity_B")
    print_pairwise(results, "GraphSAGE-Jaccard_B", "Random_B")
    print_pairwise(results, "Feature-Only_B", "Popularity_B")

    # ═══════════════════════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════════════════════
    logger.info("")
    logger.info("=" * 80)
    logger.info("  SUMMARY TABLE (all designs, all methods)")
    logger.info("=" * 80)

    designs = [
        ("Design F: Self-Consistency", ["GraphSAGE-Jaccard_F", "Feature-Only_F", "Popularity_F", "Random_F"]),
        ("Design C: Multi-Signal Retrieval", ["GraphSAGE-Jaccard_C", "Feature-Only_C", "Popularity_C", "Random_C"]),
        ("Design B: Accord Retrieval", ["GraphSAGE-Jaccard_B", "Feature-Only_B", "Popularity_B", "Random_B"]),
    ]

    for design_name, methods in designs:
        logger.info(f"\n  {design_name}")
        logger.info(f"  {'Method':<30s} {'N':>6s} {'Mean':>10s} {'Std':>10s}")
        logger.info("  " + "-" * 60)
        for m in methods:
            if m in results and results[m]["scores"]:
                mn, sd = mean_std(results[m]["scores"])
                logger.info(f"  {m:<30s} {results[m]['n']:>6d} {mn:>10.6f} {sd:>10.6f}")

    logger.info("")
    logger.info("=" * 80)
    logger.info("  PAIRWISE COMPARISONS (GS-Jaccard vs Feature-Only across all designs)")
    logger.info("=" * 80)
    for design_code, design_name in [("F", "Self-Consistency"), ("C", "Multi-Signal"), ("B", "Accord")]:
        a_key = f"GraphSAGE-Jaccard_{design_code}"
        b_key = f"Feature-Only_{design_code}"
        if a_key in results and b_key in results:
            logger.info(f"\n  Design {design_code} ({design_name}):")
            print_pairwise(results, a_key, b_key)


if __name__ == "__main__":
    main()
