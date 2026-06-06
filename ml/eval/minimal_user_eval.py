"""Minimal user-level evaluation using the production pipeline end-to-end.

For each fragrance in the catalog:
  1. Treat it as a hidden target preference.
  2. Generate quiz confidence biased toward the target's accord family.
  3. Run _align_quiz_confidence → seed IDs + weights.
  4. Compute centroid + KNN in GraphSAGE and Feature-Only embedding spaces.
  5. Evaluate: does the target (or brand-accord equivalents) appear in top-10?

Compare: Graph pipeline enabled vs Feature-Only fallback.

Usage:
    python -m ml.eval.minimal_user_eval
"""

import json
import logging
import random
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
logger = logging.getLogger("minimal_user_eval")

# ── Data loading ──────────────────────────────────────────────────────────────

def load_catalog(path: str = "ml/data/scentrix_master.json") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_gs_embeddings(
    emb_path: str = "ml/models/serving/v1/node_embeddings_jaccard.npy",
    ids_path: str = "ml/models/serving/v1/node_ids_jaccard.json",
) -> tuple[np.ndarray, list[str], dict[str, int]]:
    embeddings = np.load(emb_path)
    with open(ids_path, encoding="utf-8") as f:
        node_ids = json.load(f)
    id_to_idx = {fid: i for i, fid in enumerate(node_ids)}
    return embeddings, node_ids, id_to_idx


def build_432_features(
    catalog: list[dict],
    emb_path: str = "ml/data/embeddings.npy",
    idx_path: str = "ml/data/embedding_index.json",
) -> tuple[np.ndarray, list[str], dict[str, int]]:
    embeddings_384 = np.load(emb_path)
    with open(idx_path, encoding="utf-8") as f:
        emb_index = json.load(f)

    all_accords = sorted({
        a.lower()
        for item in catalog
        for a in (item.get("accords") or [])
    })
    accord_to_idx = {a: i for i, a in enumerate(all_accords)}

    features = []
    feature_ids = []
    for item in catalog:
        fid = item["id"]
        if fid not in emb_index:
            continue
        raw_accords = [str(a).lower() for a in (item.get("accords") or [])]
        primary = raw_accords[0] if raw_accords else "Unknown"
        accord_vec = np.zeros(len(all_accords), dtype=np.float32)
        if primary in accord_to_idx:
            accord_vec[accord_to_idx[primary]] = 1.0
        emb_vec = embeddings_384[emb_index[fid]].astype(np.float32)
        feature_vec = np.concatenate([accord_vec, emb_vec])
        features.append(feature_vec)
        feature_ids.append(fid)

    features = np.array(features, dtype=np.float32)
    norms = np.linalg.norm(features, axis=1, keepdims=True)
    features = features / (norms + 1e-8)
    id_to_idx = {fid: i for i, fid in enumerate(feature_ids)}
    return features, feature_ids, id_to_idx


# ── Build item index ──────────────────────────────────────────────────────────

def build_item_index(catalog: list[dict]) -> dict:
    """Build a lookup dict for each catalog item."""
    index = {}
    for item in catalog:
        fid = item["id"]
        raw_accords = [str(a).lower() for a in (item.get("accords") or [])]
        accords_set = set(raw_accords)
        index[fid] = {
            "brand": str(item.get("brand", "")).lower(),
            "primary_accord": raw_accords[0] if raw_accords else "Unknown",
            "accords_set": accords_set,
            "rating_count": item.get("rating_count", 0),
            "rating_value": item.get("rating_value", 0.0),
            "top_notes": {str(n).lower() for n in (item.get("top_notes") or [])},
            "middle_notes": {str(n).lower() for n in (item.get("middle_notes") or [])},
            "base_notes": {str(n).lower() for n in (item.get("base_notes") or [])},
        }
    return index


# ── Accord co-occurrence ──────────────────────────────────────────────────────

def build_cooccurrence(
    catalog: list[dict], all_accords: list[str]
) -> dict[str, list[str]]:
    """For each accord, find the top-4 most co-occurring accords."""
    n = len(all_accords)
    accord_to_idx = {a: i for i, a in enumerate(all_accords)}
    cooccur = np.zeros((n, n), dtype=np.int32)

    for item in catalog:
        accords = [str(a).lower() for a in (item.get("accords") or [])]
        accords = [a for a in accords if a in accord_to_idx]
        for i, a in enumerate(accords):
            for b in accords[i + 1 :]:
                ia, ib = accord_to_idx[a], accord_to_idx[b]
                cooccur[ia, ib] += 1
                cooccur[ib, ia] += 1

    result = {}
    for accord in all_accords:
        idx = accord_to_idx[accord]
        pairs = [(all_accords[j], cooccur[idx, j]) for j in range(n) if j != idx and cooccur[idx, j] > 0]
        pairs.sort(key=lambda x: -x[1])
        result[accord] = [a for a, _ in pairs[:4]]
    return result


# ── Production _align_quiz_confidence (ported) ────────────────────────────────

def align_quiz_confidence(
    quiz_confidence: dict[str, float],
    catalog: list[dict],
    item_index: dict,
    max_seeds: int = 5,
) -> tuple[list[str], list[float]]:
    """Port of dispatcher._align_quiz_confidence.

    For each accord in quiz_confidence, find the catalog item with the
    highest rating_count whose accords_set contains that accord.
    """
    sorted_accords = sorted(
        quiz_confidence.items(), key=lambda x: x[1], reverse=True
    )[:max_seeds]

    seed_ids: list[str] = []
    weights: list[float] = []

    for accord, confidence in sorted_accords:
        best_item: dict | None = None
        best_rc = -1
        for item in catalog:
            raw_accords = [str(a).lower() for a in (item.get("accords") or [])]
            accords_set = set(raw_accords)
            if accord in accords_set:
                rc = item.get("rating_count", 0)
                if rc > best_rc:
                    best_rc = rc
                    best_item = item
        if best_item is not None:
            seed_ids.append(str(best_item["id"]))
            weights.append(confidence)

    return seed_ids, weights


# ── Centroid + KNN ────────────────────────────────────────────────────────────

def compute_centroid(
    embeddings: np.ndarray,
    id_to_idx: dict[str, int],
    seed_ids: list[str],
    weights: list[float] | None = None,
) -> np.ndarray | None:
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
    return centroid / norm if norm > 0 else None


def knn_search(
    embeddings: np.ndarray,
    node_ids: list[str],
    centroid: np.ndarray,
    top_k: int = 10,
    exclude_ids: set | None = None,
) -> list[tuple[str, float]]:
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


# ── Ground truth ──────────────────────────────────────────────────────────────

def build_ground_truth(item_index: dict) -> dict[str, set[str]]:
    """Items sharing brand AND primary_accord with each target."""
    groups: dict[tuple[str, str], list[str]] = {}
    for fid, meta in item_index.items():
        key = (meta["brand"], meta["primary_accord"])
        groups.setdefault(key, []).append(fid)

    gt = {}
    for fid, meta in item_index.items():
        key = (meta["brand"], meta["primary_accord"])
        relevant = set(groups.get(key, []))
        relevant.discard(fid)
        if relevant:
            gt[fid] = relevant
    return gt


# ── Quiz generation (biased toward target) ────────────────────────────────────

def generate_target_quiz(
    target_id: str,
    item_index: dict,
    all_accords: list[str],
    accord_to_idx: dict[str, int],
    cooccurrence: dict[str, list[str]],
    rng: np.random.Generator,
    noise: float = 0.05,
) -> dict[str, float]:
    """Generate quiz confidence dict biased toward the target's accord family.

    The target's primary accord gets high confidence.
    Top-4 co-occurring accords get medium confidence.
    All others get low confidence + noise.
    """
    meta = item_index[target_id]
    primary = meta["primary_accord"]

    # Build confidence dict
    conf: dict[str, float] = {}

    if primary in accord_to_idx:
        conf[primary] = float(rng.uniform(0.85, 0.95))

    # Related accords (co-occurring)
    related = cooccurrence.get(primary, [])[:4]
    for ra in related:
        conf[ra] = float(rng.uniform(0.4, 0.7))

    # Add low background for non-selected accords
    for accord in all_accords:
        if accord not in conf:
            conf[accord] = float(rng.uniform(0.0, 0.1))

    # Add noise
    for accord in conf:
        conf[accord] = max(0.0, min(1.0, conf[accord] + rng.normal(0.0, noise)))

    return conf


# ── Metrics ───────────────────────────────────────────────────────────────────

def compute_metrics(
    predictions: dict[str, list[tuple[str, float]]],
    gt: dict[str, set[str]],
    target_ids: list[str],
    k: int = 10,
) -> dict:
    """Compute NDCG@10, hit rate, and recall across targets."""
    ndcg_scores = []
    hit_scores = []    # is target in top-10?
    recall_scores = []  # fraction of ground truth retrieved

    for tid in target_ids:
        ranked = predictions.get(tid, [])
        top_k_ids = {item_id for item_id, _ in ranked[:k]}
        relevant = gt.get(tid, set())

        # Hit: is the target itself in top-10?
        hit_scores.append(1.0 if tid in top_k_ids else 0.0)

        # NDCG@10 against ground truth
        if relevant:
            n_rel = len(relevant)
            dcg = 0.0
            for rank, (item_id, _) in enumerate(ranked[:k], start=1):
                if item_id in relevant:
                    dcg += 1.0 / np.log2(rank + 1)
            idcg = sum(1.0 / np.log2(i + 1) for i in range(1, min(n_rel, k) + 1))
            ndcg_scores.append(dcg / idcg if idcg > 0 else 0.0)

            # Recall
            found = len(top_k_ids & relevant)
            recall_scores.append(found / n_rel if n_rel > 0 else 0.0)
        else:
            ndcg_scores.append(0.0)
            recall_scores.append(0.0)

    return {
        "ndcg_mean": float(np.mean(ndcg_scores)) if ndcg_scores else 0.0,
        "ndcg_std": float(np.std(ndcg_scores, ddof=1)) if len(ndcg_scores) > 1 else 0.0,
        "hit_rate": float(np.mean(hit_scores)) if hit_scores else 0.0,
        "recall_mean": float(np.mean(recall_scores)) if recall_scores else 0.0,
        "n": len(target_ids),
        "gt_nonempty": sum(1 for tid in target_ids if gt.get(tid)),
    }


# ── Bootstrap significance ────────────────────────────────────────────────────

def bootstrap_test(a: list[float], b: list[float], n: int = 10000, seed: int = 42) -> float:
    rng = np.random.default_rng(seed)
    diffs = np.array(a) - np.array(b)
    observed = np.mean(diffs)
    if abs(observed) < 1e-15:
        return 1.0
    count = 0
    for _ in range(n):
        if np.mean(diffs * rng.choice([-1, 1], size=len(diffs))) >= observed:
            count += 1
    return (count + 1) / (n + 1)


def cohens_d(a: list[float], b: list[float]) -> float:
    arr_a, arr_b = np.array(a, dtype=float), np.array(b, dtype=float)
    diff = float(np.mean(arr_a) - np.mean(arr_b))
    pooled = np.sqrt((np.var(arr_a, ddof=1) + np.var(arr_b, ddof=1)) / 2)
    return diff / pooled if pooled > 0 else 0.0


def pairwise_ndcg(gs_predictions: dict, fo_predictions: dict, gt: dict, target_ids: list[str], k: int = 10) -> tuple[list[float], list[float]]:
    gs_scores, fo_scores = [], []
    for tid in target_ids:
        gs_ranked = gs_predictions.get(tid, [])
        fo_ranked = fo_predictions.get(tid, [])
        relevant = gt.get(tid, set())
        n_rel = len(relevant)

        # GS NDCG
        gs_dcg = sum(1.0 / np.log2(r + 1) for r, (iid, _) in enumerate(gs_ranked[:k], 1) if iid in relevant)
        fo_dcg = sum(1.0 / np.log2(r + 1) for r, (iid, _) in enumerate(fo_ranked[:k], 1) if iid in relevant)

        idcg = sum(1.0 / np.log2(i + 1) for i in range(1, min(n_rel, k) + 1)) if n_rel > 0 else 1.0
        gs_scores.append(gs_dcg / idcg if idcg > 0 else 0.0)
        fo_scores.append(fo_dcg / idcg if idcg > 0 else 0.0)
    return gs_scores, fo_scores


# ── Recommendation overlap ────────────────────────────────────────────────────

def compute_overlap(
    gs_predictions: dict, fo_predictions: dict, target_ids: list[str], k: int = 10
) -> dict:
    """Jaccard overlap between GS and FO recommendation sets per target."""
    overlaps = []
    for tid in target_ids:
        gs_set = {iid for iid, _ in gs_predictions.get(tid, [])[:k]}
        fo_set = {iid for iid, _ in fo_predictions.get(tid, [])[:k]}
        union = gs_set | fo_set
        if union:
            overlaps.append(len(gs_set & fo_set) / len(union))
    return {
        "mean_overlap": float(np.mean(overlaps)) if overlaps else 0.0,
        "std_overlap": float(np.std(overlaps, ddof=1)) if len(overlaps) > 1 else 0.0,
        "n": len(overlaps),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    seed = 42
    rng = np.random.default_rng(seed)

    logger.info("=" * 80)
    logger.info("  MINIMAL USER-LEVEL EVALUATION")
    logger.info("  Evaluates the production preference initialization pipeline")
    logger.info("=" * 80)

    # ── Load data ──
    logger.info("\n[1] Loading data...")
    catalog = load_catalog()
    item_index = build_item_index(catalog)
    logger.info("  Catalog items: %d", len(catalog))

    # Standard 48 accord list
    all_accords = [
        "aldehydes", "amber", "animalic", "aquatic", "aromatic", "balm", "balsamic", "bitter",
        "camphor", "citrus", "coffee", "conifer", "creamy", "earthy", "floral", "frankincense",
        "fresh", "fruity", "gourmand", "grassy", "green", "herbal", "honey", "incense",
        "iris", "lactic", "lavender", "leather", "marine", "medicinal", "metallic", "mossy",
        "musk", "myrrh", "nutty", "ozonic", "peppery", "powdery", "resinous", "rose",
        "smoky", "soapy", "spicy", "sulfurous", "tea", "tobacco", "vanilla", "woody",
    ]
    accord_to_idx = {a: i for i, a in enumerate(all_accords)}

    # Load embeddings
    gs_emb, gs_ids, gs_id_to_idx = load_gs_embeddings()
    fo_features, fo_ids, fo_id_to_idx = build_432_features(catalog)
    logger.info("  GraphSAGE-Jaccard: %d items, %s", len(gs_ids), gs_emb.shape)
    logger.info("  Feature-Only: %d items, %s", len(fo_ids), fo_features.shape)

    gs_set = set(gs_ids)
    fo_set = set(fo_ids)

    # ── Build co-occurrence ──
    logger.info("\n[2] Building accord co-occurrence matrix...")
    cooccurrence = build_cooccurrence(catalog, all_accords)
    logger.info("  Computed co-occurrence for %d accords", len(cooccurrence))

    # ── Build ground truth ──
    logger.info("\n[3] Building ground truth (brand + accord)...")
    gt = build_ground_truth(item_index)
    logger.info("  Queries with non-empty GT: %d / %d", sum(1 for v in gt.values() if v), len(gt))

    # ── Select targets: items with a known primary accord AND in both embedding spaces ──
    logger.info("\n[4] Selecting targets...")
    targets = [
        fid for fid, meta in item_index.items()
        if meta["primary_accord"] in accord_to_idx
        and meta["primary_accord"] != "Unknown"
        and fid in gs_set
        and fid in fo_set
        and fid in gt
        and gt[fid]  # must have at least 1 relevant item
    ]
    logger.info("  Targets: %d / %d items", len(targets), len(catalog))

    # ── Run evaluation ──
    gs_predictions: dict[str, list[tuple[str, float]]] = {}
    fo_predictions: dict[str, list[tuple[str, float]]] = {}
    failed = 0

    logger.info("\n[5] Running preference initialization for each target...")
    for i, tid in enumerate(targets):
        if (i + 1) % 500 == 0:
            logger.info("  Progress: %d / %d", i + 1, len(targets))

        # 5a. Generate quiz confidence
        quiz_conf = generate_target_quiz(
            tid, item_index, all_accords, accord_to_idx, cooccurrence, rng, noise=0.05,
        )

        # 5b. Align quiz confidence to seed IDs (production dispatcher logic)
        seed_ids, weights = align_quiz_confidence(quiz_conf, catalog, item_index, max_seeds=5)
        if not seed_ids:
            failed += 1
            continue

        seed_set = set(seed_ids)

        # 5c. Graph variant: centroid + KNN in GS embedding space
        centroid_gs = compute_centroid(gs_emb, gs_id_to_idx, seed_ids, weights)
        if centroid_gs is None:
            failed += 1
            continue
        gs_predictions[tid] = knn_search(gs_emb, gs_ids, centroid_gs, top_k=50, exclude_ids=seed_set)

        # 5d. Feature-Only variant: centroid + KNN in 432-dim feature space
        centroid_fo = compute_centroid(fo_features, fo_id_to_idx, seed_ids, weights)
        if centroid_fo is None:
            failed += 1
            continue
        fo_predictions[tid] = knn_search(fo_features, fo_ids, centroid_fo, top_k=50, exclude_ids=seed_set)

    logger.info("  Complete. Successful: %d, Failed: %d", len(gs_predictions), failed)

    # ── Evaluate at k=10 ──
    logger.info("\n[6] Results (k=10)")
    logger.info("=" * 80)

    for k in [5, 10, 20]:
        logger.info(f"\n  k = {k}")
        logger.info(f"  {'Method':<30s} {'NDCG@k':>10s} {'Std':>8s} {'HitRate':>10s} {'Recall':>10s}")
        logger.info("  " + "-" * 70)

        # GS metrics
        gs_m = compute_metrics(gs_predictions, gt, list(gs_predictions.keys()), k=k)
        logger.info(f"  {'GraphSAGE-Jaccard':<30s} {gs_m['ndcg_mean']:>10.6f} {gs_m['ndcg_std']:>8.6f} {gs_m['hit_rate']:>10.6f} {gs_m['recall_mean']:>10.6f}")

        # FO metrics
        fo_m = compute_metrics(fo_predictions, gt, list(fo_predictions.keys()), k=k)
        logger.info(f"  {'Feature-Only':<30s} {fo_m['ndcg_mean']:>10.6f} {fo_m['ndcg_std']:>8.6f} {fo_m['hit_rate']:>10.6f} {fo_m['recall_mean']:>10.6f}")

        # Pairwise NDCG
        gs_scores, fo_scores = pairwise_ndcg(gs_predictions, fo_predictions, gt, list(gs_predictions.keys()), k=k)
        if len(gs_scores) > 1:
            p = bootstrap_test(gs_scores, fo_scores)
            d = cohens_d(gs_scores, fo_scores)
            diff = np.mean(gs_scores) - np.mean(fo_scores)
            logger.info(f"\n  {'GS vs FO paired test':<30s} diff={diff:+.6f}  p={p:.4f}  d={d:+.4f}")

    # ── Target hit analysis ──
    logger.info("\n[7] Target hit analysis (is the hidden target itself in top-10?)")
    logger.info("=" * 80)
    gs_hits = sum(1 for tid in gs_predictions if any(iid == tid for iid, _ in gs_predictions[tid][:10]))
    fo_hits = sum(1 for tid in fo_predictions if any(iid == tid for iid, _ in fo_predictions[tid][:10]))
    gs_any_hits = sum(1 for tid in gs_predictions if any(iid in gt.get(tid, set()) for iid, _ in gs_predictions[tid][:10]))
    fo_any_hits = sum(1 for tid in fo_predictions if any(iid in gt.get(tid, set()) for iid, _ in fo_predictions[tid][:10]))
    n = len(gs_predictions)

    logger.info(f"  {'Metric':<45s} {'GraphSAGE':>12s} {'Feature-Only':>14s}")
    logger.info("  " + "-" * 72)
    logger.info(f"  {'Target itself in top-10':<45s} {gs_hits:>7d}/{n:<4d} {fo_hits:>7d}/{n:<4d}")
    logger.info(f"  {'Target itself hit rate':<45s} {gs_hits/n:>12.6f} {fo_hits/n:>14.6f}")
    logger.info(f"  {'Any brand-accord family in top-10':<45s} {gs_any_hits:>7d}/{n:<4d} {fo_any_hits:>7d}/{n:<4d}")
    logger.info(f"  {'Family hit rate':<45s} {gs_any_hits/n:>12.6f} {fo_any_hits/n:>14.6f}")

    # ── Recommendation overlap ──
    logger.info("\n[8] Recommendation overlap (Jaccard between GS and FO top-10)")
    logger.info("=" * 80)
    overlap = compute_overlap(gs_predictions, fo_predictions, list(gs_predictions.keys()), k=10)
    logger.info(f"  Mean Jaccard overlap: {overlap['mean_overlap']:.4f} (std={overlap['std_overlap']:.4f}, n={overlap['n']})")
    logger.info(f"  Interpretation: {overlap['mean_overlap']*100:.1f}% of recommended items are shared between GS and FO")

    # ── Summary ──
    logger.info("\n[9] Summary")
    logger.info("=" * 80)
    logger.info(f"  Total targets: {n}")
    logger.info(f"  Targets with non-empty brand+accord GT: {gs_m['gt_nonempty']} / {n}")
    logger.info(f"  Seed selection failures: {failed}")

    logger.info(f"\n  {'Method':<30s} {'NDCG@10':>10s} {'HitRate':>10s} {'Rec@10':>10s}")
    logger.info("  " + "-" * 60)
    gs_m10 = compute_metrics(gs_predictions, gt, list(gs_predictions.keys()), k=10)
    fo_m10 = compute_metrics(fo_predictions, gt, list(fo_predictions.keys()), k=10)
    logger.info(f"  {'GraphSAGE-Jaccard':<30s} {gs_m10['ndcg_mean']:>10.6f} {gs_m10['hit_rate']:>10.6f} {gs_m10['recall_mean']:>10.6f}")
    logger.info(f"  {'Feature-Only':<30s} {fo_m10['ndcg_mean']:>10.6f} {fo_m10['hit_rate']:>10.6f} {fo_m10['recall_mean']:>10.6f}")

    gs_scores10, fo_scores10 = pairwise_ndcg(gs_predictions, fo_predictions, gt, list(gs_predictions.keys()), k=10)
    p10 = bootstrap_test(gs_scores10, fo_scores10)
    d10 = cohens_d(gs_scores10, fo_scores10)
    diff10 = np.mean(gs_scores10) - np.mean(fo_scores10)
    logger.info(f"\n  GS vs FO paired test: diff={diff10:+.6f}  p={p10:.4f}  d={d10:+.4f}")
    logger.info(f"  Winner: {'GraphSAGE-Jaccard' if diff10 > 0 else 'Feature-Only'}")
    logger.info(f"  Overlap: {overlap['mean_overlap']*100:.1f}%")


if __name__ == "__main__":
    main()
