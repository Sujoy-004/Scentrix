"""Ground truth sensitivity analysis for B1 bottleneck.

Tests 4 progressively relaxed ground truth definitions:
  GT-A: brand + accord (current)
  GT-B: accord only
  GT-C: brand OR accord
  GT-D: accord + note-overlap > threshold

For each: family size stats, oracle hit rate, pipeline hit rate, NDCG@10, Recall@10.

Usage:
    python -m ml.eval.ground_truth_sensitivity
"""

import json
import logging
import sys
from collections import Counter

import numpy as np

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
logger = logging.getLogger("gt_sensitivity")

NOTE_JACCARD_THRESHOLD = 0.15


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


def build_item_index(catalog: list[dict]) -> dict:
    index = {}
    for item in catalog:
        fid = item["id"]
        raw_accords = [str(a).lower() for a in (item.get("accords") or [])]
        top = {str(n).lower() for n in (item.get("top_notes") or [])}
        mid = {str(n).lower() for n in (item.get("middle_notes") or [])}
        base = {str(n).lower() for n in (item.get("base_notes") or [])}
        index[fid] = {
            "brand": str(item.get("brand", "")).lower(),
            "primary_accord": raw_accords[0] if raw_accords else "Unknown",
            "accords_set": set(raw_accords),
            "rating_count": item.get("rating_count", 0),
            "rating_value": item.get("rating_value", 0.0),
            "notes_set": top | mid | base,
        }
    return index


def build_cooccurrence(catalog: list[dict], all_accords: list[str]) -> dict[str, list[str]]:
    n = len(all_accords)
    a2i = {a: i for i, a in enumerate(all_accords)}
    cooc = np.zeros((n, n), dtype=np.int32)
    for item in catalog:
        accs = [str(a).lower() for a in (item.get("accords") or [])]
        accs = [a for a in accs if a in a2i]
        for i, a in enumerate(accs):
            for b in accs[i + 1:]:
                ia, ib = a2i[a], a2i[b]
                cooc[ia, ib] += 1
                cooc[ib, ia] += 1
    result = {}
    for accord in all_accords:
        idx = a2i[accord]
        pairs = [(all_accords[j], cooc[idx, j]) for j in range(n) if j != idx and cooc[idx, j] > 0]
        pairs.sort(key=lambda x: -x[1])
        result[accord] = [a for a, _ in pairs[:4]]
    return result


# ── Ground truth definitions ──────────────────────────────────────────────────

def build_gt_brand_accord(item_index: dict) -> dict[str, set[str]]:
    """GT-A: same brand AND same primary accord."""
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


def build_gt_accord_only(item_index: dict) -> dict[str, set[str]]:
    """GT-B: same primary accord (ignoring brand)."""
    groups: dict[str, list[str]] = {}
    for fid, meta in item_index.items():
        groups.setdefault(meta["primary_accord"], []).append(fid)
    gt = {}
    for fid, meta in item_index.items():
        accord = meta["primary_accord"]
        relevant = set(groups.get(accord, []))
        relevant.discard(fid)
        if relevant:
            gt[fid] = relevant
    return gt


def build_gt_brand_or_accord(item_index: dict) -> dict[str, set[str]]:
    """GT-C: same brand OR same primary accord."""
    gt: dict[str, set[str]] = {}
    for fid, meta in item_index.items():
        relevant: set[str] = set()
        for oid, ometa in item_index.items():
            if oid == fid:
                continue
            if ometa["brand"] == meta["brand"] or ometa["primary_accord"] == meta["primary_accord"]:
                relevant.add(oid)
        if relevant:
            gt[fid] = relevant
    return gt


def build_gt_accord_note_overlap(
    item_index: dict, threshold: float = NOTE_JACCARD_THRESHOLD,
) -> dict[str, set[str]]:
    """GT-D: same primary accord AND note-set Jaccard > threshold."""
    gt: dict[str, set[str]] = {}
    for fid, meta in item_index.items():
        relevant: set[str] = set()
        t_accord = meta["primary_accord"]
        t_notes = meta["notes_set"]
        for oid, ometa in item_index.items():
            if oid == fid:
                continue
            if ometa["primary_accord"] != t_accord:
                continue
            o_notes = ometa["notes_set"]
            union = t_notes | o_notes
            if union:
                jac = len(t_notes & o_notes) / len(union)
                if jac > threshold:
                    relevant.add(oid)
        if relevant:
            gt[fid] = relevant
    return gt


# ── Quiz generation (same as minimal_user_eval) ───────────────────────────────

def generate_target_quiz(
    target_id: str,
    item_index: dict,
    all_accords: list[str],
    accord_to_idx: dict[str, int],
    cooccurrence: dict[str, list[str]],
    rng: np.random.Generator,
    noise: float = 0.05,
) -> dict[str, float]:
    meta = item_index[target_id]
    primary = meta["primary_accord"]
    conf: dict[str, float] = {}
    if primary in accord_to_idx:
        conf[primary] = float(rng.uniform(0.85, 0.95))
    related = cooccurrence.get(primary, [])[:4]
    for ra in related:
        conf[ra] = float(rng.uniform(0.4, 0.7))
    for accord in all_accords:
        if accord not in conf:
            conf[accord] = float(rng.uniform(0.0, 0.1))
    for accord in list(conf.keys()):
        conf[accord] = max(0.0, min(1.0, conf[accord] + rng.normal(0.0, noise)))
    return conf


def select_seeds_popularity(
    quiz_confidence: dict[str, float],
    catalog: list[dict],
    max_seeds: int = 5,
) -> tuple[list[str], list[float]]:
    sorted_accords = sorted(quiz_confidence.items(), key=lambda x: x[1], reverse=True)[:max_seeds]
    seed_ids: list[str] = []
    weights: list[float] = []
    for accord, confidence in sorted_accords:
        best_item, best_rc = None, -1
        for item in catalog:
            accords_set = {str(a).lower() for a in (item.get("accords") or [])}
            if accord in accords_set:
                rc = item.get("rating_count", 0)
                if rc > best_rc:
                    best_rc = rc
                    best_item = item
        if best_item is not None:
            seed_ids.append(str(best_item["id"]))
            weights.append(confidence)
    return seed_ids, weights


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
    top_k: int = 50,
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


# ── Metrics ───────────────────────────────────────────────────────────────────

def compute_metrics(
    predictions: dict[str, list[tuple[str, float]]],
    gt: dict[str, set[str]],
    target_ids: list[str],
    k: int = 10,
) -> dict:
    ndcg_scores = []
    hit_scores = []
    recall_scores = []
    family_hits = 0

    for tid in target_ids:
        ranked = predictions.get(tid, [])
        if not ranked:
            continue
        top_k_ids = {item_id for item_id, _ in ranked[:k]}
        relevant = gt.get(tid, set())

        hit_scores.append(1.0 if tid in top_k_ids else 0.0)

        family_members_in_top_k = top_k_ids & relevant
        if family_members_in_top_k:
            family_hits += 1

        if relevant:
            n_rel = len(relevant)
            dcg = 0.0
            for rank, (item_id, _) in enumerate(ranked[:k], start=1):
                if item_id in relevant:
                    dcg += 1.0 / np.log2(rank + 1)
            idcg = sum(1.0 / np.log2(i + 1) for i in range(1, min(n_rel, k) + 1))
            ndcg_scores.append(dcg / idcg if idcg > 0 else 0.0)
            found = len(top_k_ids & relevant)
            recall_scores.append(found / n_rel if n_rel > 0 else 0.0)
        else:
            ndcg_scores.append(0.0)
            recall_scores.append(0.0)

    n = len(target_ids)
    return {
        "ndcg_mean": float(np.mean(ndcg_scores)) if ndcg_scores else 0.0,
        "hit_rate": float(np.mean(hit_scores)) if hit_scores else 0.0,
        "family_hit_rate": family_hits / n if n > 0 else 0.0,
        "recall_mean": float(np.mean(recall_scores)) if recall_scores else 0.0,
        "n": n,
        "family_hits": family_hits,
        "gt_nonempty": sum(1 for tid in target_ids if gt.get(tid)),
    }


def family_size_stats(gt: dict[str, set[str]]) -> dict:
    sizes = [len(v) for v in gt.values()]
    return {
        "mean": float(np.mean(sizes)) if sizes else 0,
        "median": float(np.median(sizes)) if sizes else 0,
        "p25": float(np.percentile(sizes, 25)) if sizes else 0,
        "p90": float(np.percentile(sizes, 90)) if sizes else 0,
        "min": int(min(sizes)) if sizes else 0,
        "max": int(max(sizes)) if sizes else 0,
        "le2": sum(1 for s in sizes if s <= 2),
        "le5": sum(1 for s in sizes if s <= 5),
        "n_queries": len(sizes),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    seed = 42
    rng = np.random.default_rng(seed)

    logger.info("=" * 80)
    logger.info("  GROUND TRUTH SENSITIVITY ANALYSIS (B1 Validation)")
    logger.info("  Testing 4 GT definitions on production pipeline + oracle")
    logger.info("=" * 80)

    # ── Load ──
    logger.info("\n[1] Loading data...")
    catalog = load_catalog()
    item_index = build_item_index(catalog)
    gs_emb, gs_ids, gs_id_to_idx = load_gs_embeddings()
    gs_set = set(gs_ids)
    logger.info("  Catalog: %d items", len(catalog))
    logger.info("  GS embeddings: %d items", len(gs_ids))

    all_accords = [
        "aldehydes", "amber", "animalic", "aquatic", "aromatic", "balm", "balsamic", "bitter",
        "camphor", "citrus", "coffee", "conifer", "creamy", "earthy", "floral", "frankincense",
        "fresh", "fruity", "gourmand", "grassy", "green", "herbal", "honey", "incense",
        "iris", "lactic", "lavender", "leather", "marine", "medicinal", "metallic", "mossy",
        "musk", "myrrh", "nutty", "ozonic", "peppery", "powdery", "resinous", "rose",
        "smoky", "soapy", "spicy", "sulfurous", "tea", "tobacco", "vanilla", "woody",
    ]
    accord_to_idx = {a: i for i, a in enumerate(all_accords)}

    cooccurrence = build_cooccurrence(catalog, all_accords)

    # ── Build all ground truths ──
    logger.info("\n[2] Building ground truths...")
    gt_defs = {
        "GT-A: brand + accord": build_gt_brand_accord(item_index),
        "GT-B: accord only": build_gt_accord_only(item_index),
        "GT-C: brand OR accord": build_gt_brand_or_accord(item_index),
        "GT-D: accord + note overlap": build_gt_accord_note_overlap(item_index, NOTE_JACCARD_THRESHOLD),
    }

    for gt_name, gt in gt_defs.items():
        stats = family_size_stats(gt)
        logger.info(f"  {gt_name:<30s} queries={stats['n_queries']:<6d} mean={stats['mean']:<6.1f} median={stats['median']:<4.0f} p90={stats['p90']:<5.0f} <=2={stats['le2']:<5d} <=5={stats['le5']:<5d}")

    # ── Determine common target set ──
    # Items must have a known primary accord, be in GS embeddings, and have non-empty GT for ALL definitions
    all_gt_keys = set()
    for gt in gt_defs.values():
        all_gt_keys.update(gt.keys())

    targets = [
        fid for fid, meta in item_index.items()
        if meta["primary_accord"] in accord_to_idx
        and meta["primary_accord"] != "Unknown"
        and fid in gs_set
        and fid in all_gt_keys
        and all(gt.get(fid) for gt in gt_defs.values())
    ]
    logger.info("\n  Common targets across all GTs: %d", len(targets))

    # ── Run oracle (self-as-seed) ──
    logger.info("\n[3] Oracle evaluation (self-as-seed)...")
    oracle_predictions: dict[str, list[tuple[str, float]]] = {}
    oracle_failures = 0
    for tid in targets:
        if tid not in gs_id_to_idx:
            oracle_failures += 1
            continue
        tidx = gs_id_to_idx[tid]
        preds = knn_search(gs_emb, gs_ids, gs_emb[tidx], top_k=50, exclude_ids={tid})
        oracle_predictions[tid] = preds

    logger.info("  Oracle predictions: %d, failures: %d", len(oracle_predictions), oracle_failures)

    # ── Run pipeline ──
    logger.info("\n[4] Pipeline evaluation (quiz -> seeds -> centroid -> KNN)...")
    pipeline_predictions: dict[str, list[tuple[str, float]]] = {}
    pipeline_failures = 0

    for i, tid in enumerate(targets):
        if (i + 1) % 500 == 0:
            logger.info("  Progress: %d / %d", i + 1, len(targets))

        quiz_conf = generate_target_quiz(tid, item_index, all_accords, accord_to_idx, cooccurrence, rng)
        seed_ids, weights = select_seeds_popularity(quiz_conf, catalog)
        if not seed_ids:
            pipeline_failures += 1
            continue

        centroid = compute_centroid(gs_emb, gs_id_to_idx, seed_ids, weights)
        if centroid is None:
            pipeline_failures += 1
            continue

        preds = knn_search(gs_emb, gs_ids, centroid, top_k=50, exclude_ids=set(seed_ids))
        pipeline_predictions[tid] = preds

    logger.info("  Pipeline predictions: %d, failures: %d", len(pipeline_predictions), pipeline_failures)

    # ── Results table ──
    logger.info("\n" + "=" * 80)
    logger.info("  RESULTS")
    logger.info("=" * 80)

    # Family size
    logger.info("\n[FAMILY SIZE DISTRIBUTION]")
    logger.info(f"  {'GT':<30s} {'Queries':>8s} {'Mean':>8s} {'Median':>8s} {'P90':>8s} {'Min':>6s} {'Max':>6s} {'<=2':>6s} {'<=5':>6s}")
    logger.info("  " + "-" * 86)
    for gt_name, gt in gt_defs.items():
        stats = family_size_stats(gt)
        logger.info(f"  {gt_name:<30s} {stats['n_queries']:>8d} {stats['mean']:>8.1f} {stats['median']:>8.0f} {stats['p90']:>8.0f} {stats['min']:>6d} {stats['max']:>6d} {stats['le2']:>6d} {stats['le5']:>6d}")

    # Oracle results
    logger.info(f"\n[ORACLE (self-as-seed) @ k=10]")
    logger.info(f"  {'GT':<30s} {'FamilyHit':>10s} {'HitRate':>10s} {'NDCG@10':>10s} {'Recall@10':>10s} {'GT-nonempty':>12s}")
    logger.info("  " + "-" * 72)
    for gt_name, gt in gt_defs.items():
        m = compute_metrics(oracle_predictions, gt, list(oracle_predictions.keys()), k=10)
        logger.info(f"  {gt_name:<30s} {m['family_hit_rate']:>10.4f} {m['hit_rate']:>10.6f} {m['ndcg_mean']:>10.6f} {m['recall_mean']:>10.6f} {m['gt_nonempty']:>5d}/{m['n']:<5d}")

    # Pipeline results
    logger.info(f"\n[PIPELINE (production) @ k=10]")
    logger.info(f"  {'GT':<30s} {'FamilyHit':>10s} {'HitRate':>10s} {'NDCG@10':>10s} {'Recall@10':>10s} {'GT-nonempty':>12s}")
    logger.info("  " + "-" * 72)
    for gt_name, gt in gt_defs.items():
        m = compute_metrics(pipeline_predictions, gt, list(pipeline_predictions.keys()), k=10)
        logger.info(f"  {gt_name:<30s} {m['family_hit_rate']:>10.4f} {m['hit_rate']:>10.6f} {m['ndcg_mean']:>10.6f} {m['recall_mean']:>10.6f} {m['gt_nonempty']:>5d}/{m['n']:<5d}")

    # Pipeline-to-oracle ratio
    logger.info(f"\n[PIPELINE / ORACLE RATIO]")
    logger.info(f"  {'GT':<30s} {'Pipeline FH':>12s} {'Oracle FH':>12s} {'Ratio':>8s} {'Pipeline NDCG':>14s} {'Oracle NDCG':>12s} {'Ratio':>8s}")
    logger.info("  " + "-" * 84)
    for gt_name, gt in gt_defs.items():
        pm = compute_metrics(pipeline_predictions, gt, list(pipeline_predictions.keys()), k=10)
        om = compute_metrics(oracle_predictions, gt, list(oracle_predictions.keys()), k=10)
        fh_ratio = pm['family_hit_rate'] / om['family_hit_rate'] if om['family_hit_rate'] > 0 else 0
        ndcg_ratio = pm['ndcg_mean'] / om['ndcg_mean'] if om['ndcg_mean'] > 0 else 0
        logger.info(f"  {gt_name:<30s} {pm['family_hit_rate']:>12.4f} {om['family_hit_rate']:>12.4f} {fh_ratio:>7.3f} {pm['ndcg_mean']:>14.6f} {om['ndcg_mean']:>12.6f} {ndcg_ratio:>7.3f}")

    # ── Blow-up: what happens to the "95% failure" under each GT? ──
    logger.info(f"\n[FAILURE CASCADE UNDER EACH GT]")
    logger.info(f"  {'GT':<30s} {'Oracle FH%':>12s} {'Pipeline FH%':>14s} {'Gap':>8s} {'Failure':>10s}")
    logger.info("  " + "-" * 74)
    for gt_name, gt in gt_defs.items():
        pm = compute_metrics(pipeline_predictions, gt, list(pipeline_predictions.keys()), k=10)
        om = compute_metrics(oracle_predictions, gt, list(oracle_predictions.keys()), k=10)
        n = pm['n']
        failure = 1.0 - pm['family_hit_rate']
        logger.info(f"  {gt_name:<30s} {om['family_hit_rate']:>11.4f} {pm['family_hit_rate']:>13.4f} {failure - (1 - om['family_hit_rate']):>7.4f} {failure:>9.2%}")

    # ── Summary ──
    logger.info("\n" + "=" * 80)
    logger.info("  SUMMARY")
    logger.info("=" * 80)

    for gt_name, gt in gt_defs.items():
        pm = compute_metrics(pipeline_predictions, gt, list(pipeline_predictions.keys()), k=10)
        om = compute_metrics(oracle_predictions, gt, list(oracle_predictions.keys()), k=10)
        stats = family_size_stats(gt)
        logger.info(f"")
        logger.info(f"  {gt_name}")
        logger.info(f"    Family size:   mean={stats['mean']:.1f}, median={stats['median']:.0f}, p90={stats['p90']:.0f}, <=2: {stats['le2']}/{stats['n_queries']} ({100*stats['le2']/stats['n_queries']:.1f}%)")
        logger.info(f"    Oracle FH@10:  {om['family_hit_rate']:.4f} ({om['family_hits']}/{om['n']})")
        logger.info(f"    Pipeline FH@10: {pm['family_hit_rate']:.4f} ({pm['family_hits']}/{pm['n']})")
        logger.info(f"    Pipeline NDCG@10: {pm['ndcg_mean']:.6f}")
        logger.info(f"    Failure rate:  {1-pm['family_hit_rate']:.2%}")

    # GT-D note threshold info
    logger.info(f"\n  GT-D note overlap threshold: {NOTE_JACCARD_THRESHOLD}")

    # Key comparison
    logger.info(f"\n" + "=" * 80)
    logger.info("  KEY QUESTION: Is the 18.1% oracle ceiling an artifact of GT-A?")
    logger.info("=" * 80)
    logger.info(f"  GT-A oracle: {compute_metrics(oracle_predictions, gt_defs['GT-A: brand + accord'], list(oracle_predictions.keys()), k=10)['family_hit_rate']:.4f}")
    logger.info(f"  GT-B oracle: {compute_metrics(oracle_predictions, gt_defs['GT-B: accord only'], list(oracle_predictions.keys()), k=10)['family_hit_rate']:.4f}")
    logger.info(f"  GT-C oracle: {compute_metrics(oracle_predictions, gt_defs['GT-C: brand OR accord'], list(oracle_predictions.keys()), k=10)['family_hit_rate']:.4f}")
    logger.info(f"  GT-D oracle: {compute_metrics(oracle_predictions, gt_defs['GT-D: accord + note overlap'], list(oracle_predictions.keys()), k=10)['family_hit_rate']:.4f}")


if __name__ == "__main__":
    main()
