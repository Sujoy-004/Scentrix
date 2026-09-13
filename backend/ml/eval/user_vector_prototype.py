"""User vector prototype experiment.

Compares:
  A — Current pipeline: 5 seeds → centroid → KNN
  B — UserVector-5:    5 seeds → rating-weighted u → KNN
  C — UserVector-16:   16 seeds → rating-weighted u → KNN
  D — Oracle:          target embedding → KNN

Uses GT-D (primary accord match OR note overlap >= 0.15).

The core question: does preserving per-item rating information (instead of
collapsing to accord averages) improve retrieval?

Usage:
    python -m ml.eval.user_vector_prototype
"""

import json
import logging
import sys

import numpy as np

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
logger = logging.getLogger("uv_proto")

SEED = 42
NOTE_OVERLAP_THRESHOLD = 0.15


# ── Data loading ──────────────────────────────────────────────────────────────

def load_catalog(path: str = "ml/data/scentrix_master.json") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_gs_embeddings(
    emb_path: str = "ml/models/serving/v1/node_embeddings_jaccard.npy",
    ids_path: str = "ml/models/serving/v1/node_ids_jaccard.json",
) -> tuple[np.ndarray, list[str], dict[str, int]]:
    embeddings = np.load(emb_path)
    with open(ids_path) as f:
        node_ids = json.load(f)
    id_to_idx = {fid: i for i, fid in enumerate(node_ids)}
    return embeddings, node_ids, id_to_idx


def build_item_index(catalog: list[dict]) -> dict:
    index = {}
    for item in catalog:
        fid = item["id"]
        raw_accords = [str(a).lower() for a in (item.get("accords") or [])]
        raw_notes = set()
        for key in ("top_notes", "middle_notes", "base_notes"):
            for n in item.get(key) or []:
                s = str(n).strip().lower()
                if s:
                    raw_notes.add(s)
        index[fid] = {
            "brand": str(item.get("brand", "")).lower(),
            "primary_accord": raw_accords[0] if raw_accords else "Unknown",
            "accords_set": set(raw_accords),
            "notes_set": raw_notes,
            "rating_count": item.get("rating_count", 0),
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


# ── GT-D ground truth ─────────────────────────────────────────────────────────

def build_ground_truth_gt_d(item_index: dict) -> dict[str, set[str]]:
    """GT-D: items share primary accord OR note Jaccard >= threshold."""
    gt: dict[str, set[str]] = {}
    all_ids = list(item_index.keys())
    for i, fid in enumerate(all_ids):
        meta = item_index[fid]
        primary = meta["primary_accord"]
        notes = meta["notes_set"]
        relevant: set[str] = set()
        for oid in all_ids:
            if oid == fid:
                continue
            other = item_index[oid]
            # Primary accord match
            if other["primary_accord"] == primary:
                relevant.add(oid)
                continue
            # Note overlap
            if notes and other["notes_set"]:
                union = notes | other["notes_set"]
                jac = len(notes & other["notes_set"]) / len(union)
                if jac >= NOTE_OVERLAP_THRESHOLD:
                    relevant.add(oid)
        if relevant:
            gt[fid] = relevant
    return gt


# ── Quiz simulation ───────────────────────────────────────────────────────────

def simulate_quiz_conf(
    target_id: str,
    item_index: dict,
    all_accords: list[str],
    accord_to_idx: dict[str, int],
    cooccurrence: dict[str, list[str]],
    rng: np.random.Generator,
) -> list[str]:
    """Return top-5 accords for this target (current quiz simulation)."""
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
    sorted_accords = sorted(conf.items(), key=lambda x: x[1], reverse=True)[:5]
    return [a for a, _ in sorted_accords]


# ── Seed selection ────────────────────────────────────────────────────────────

def select_top_k_for_accord(accord: str, catalog: list[dict], k: int = 1, exclude: set[str] | None = None) -> list[str]:
    items = []
    for item in catalog:
        accords_set = {str(a).lower() for a in (item.get("accords") or [])}
        if accord in accords_set:
            items.append(item)
    items.sort(key=lambda x: x.get("rating_count", 0), reverse=True)
    exclude = exclude or set()
    result = []
    for it in items:
        fid = str(it["id"])
        if fid in exclude:
            continue
        result.append(fid)
        if len(result) >= k:
            break
    return result


def simulate_rating(target_emb: np.ndarray, item_emb: np.ndarray) -> float:
    """Simulate a user rating 1-10 based on embedding similarity to target."""
    cos_sim = float(np.dot(target_emb, item_emb))
    rating = 1.0 + 9.0 * (cos_sim + 1.0) / 2.0
    return float(np.clip(rating, 1.0, 10.0))


# ── Query construction ────────────────────────────────────────────────────────

def compute_centroid(embeddings: np.ndarray, id_to_idx: dict[str, int], seed_ids: list[str]) -> np.ndarray | None:
    """Equal-weight centroid (current pipeline)."""
    indices = [id_to_idx[sid] for sid in seed_ids if sid in id_to_idx]
    if not indices:
        return None
    centroid = np.mean(embeddings[indices], axis=0)
    norm = np.linalg.norm(centroid)
    return centroid / norm if norm > 0 else None


def compute_user_vector(
    embeddings: np.ndarray,
    id_to_idx: dict[str, int],
    item_ratings: list[tuple[str, float]],
) -> np.ndarray | None:
    """u = mean(rating_weight × item_embedding)"""
    weighted_sum = None
    total_weight = 0.0
    for fid, rating in item_ratings:
        if fid not in id_to_idx:
            continue
        idx = id_to_idx[fid]
        emb = embeddings[idx]
        weight = rating / 10.0
        if weighted_sum is None:
            weighted_sum = weight * emb
        else:
            weighted_sum += weight * emb
        total_weight += weight

    if weighted_sum is None or total_weight <= 0:
        return None
    u = weighted_sum / total_weight
    norm = np.linalg.norm(u)
    return u / norm if norm > 0 else None


# ── Retrieval ─────────────────────────────────────────────────────────────────

def knn_search(
    embeddings: np.ndarray,
    node_ids: list[str],
    query: np.ndarray,
    top_k: int = 10,
    exclude_ids: set[str] | None = None,
) -> list[tuple[str, float]]:
    similarities = np.dot(embeddings, query)
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
        top_k_ids = {item_id for item_id, _ in ranked[:k]}
        relevant = gt.get(tid, set())

        hit_scores.append(1.0 if tid in top_k_ids else 0.0)

        family_members = top_k_ids & relevant
        if family_members:
            family_hits += 1

        if relevant:
            dcg = sum(1.0 / np.log2(r + 1) for r, (iid, _) in enumerate(ranked[:k], 1) if iid in relevant)
            idcg = sum(1.0 / np.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
            ndcg_scores.append(dcg / idcg if idcg > 0 else 0.0)
            recall_scores.append(len(top_k_ids & relevant) / len(relevant))
        else:
            ndcg_scores.append(0.0)
            recall_scores.append(0.0)

    n = len(target_ids)
    return {
        "ndcg_mean": float(np.mean(ndcg_scores)) if ndcg_scores else 0.0,
        "hit_rate": float(np.mean(hit_scores)) if hit_scores else 0.0,
        "family_hit_rate": family_hits / n if n > 0 else 0.0,
        "recall_mean": float(np.mean(recall_scores)) if recall_scores else 0.0,
        "family_hits": family_hits,
        "n": n,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    rng = np.random.default_rng(SEED)

    logger.info("=" * 80)
    logger.info("  USER VECTOR PROTOTYPE  (GT-D ground truth)")
    logger.info("  Does per-item rating info improve retrieval vs accord-averaged centroid?")
    logger.info("=" * 80)

    # ── Load ──
    logger.info("\n[1] Loading data...")
    catalog = load_catalog()
    item_index = build_item_index(catalog)
    gs_emb, gs_ids, gs_id_to_idx = load_gs_embeddings()
    gs_set = set(gs_ids)
    logger.info("  Catalog: %d items", len(catalog))
    logger.info("  GS embeddings: %d items, %s", len(gs_ids), gs_emb.shape)

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
    logger.info("\n[2] Building GT-D ground truth...")
    gt = build_ground_truth_gt_d(item_index)
    logger.info("  Non-empty GT-D queries: %d / %d", sum(1 for v in gt.values() if v), len(gt))

    targets = [
        fid for fid, meta in item_index.items()
        if meta["primary_accord"] in accord_to_idx
        and meta["primary_accord"] != "Unknown"
        and fid in gs_set
        and fid in gt
        and gt[fid]
    ]
    logger.info("  Targets with non-empty GT-D: %d", len(targets))

    gt_d_family_sizes = [len(gt[tid]) for tid in targets]
    logger.info("  GT-D family size: mean=%.1f median=%d max=%d",
                np.mean(gt_d_family_sizes), int(np.median(gt_d_family_sizes)), max(gt_d_family_sizes))

    # ── Pre-aggregate: for each accord, top-16 popular items ──
    logger.info("\n[3] Precomputing per-accord item pools...")
    accord_pools: dict[str, list[str]] = {}
    for accord in all_accords:
        accord_pools[accord] = select_top_k_for_accord(accord, catalog, k=16)

    # ── Run all 4 strategies ──
    logger.info("\n[4] Running strategies on %d targets...", len(targets))

    all_preds: dict[str, dict[str, list[tuple[str, float]]]] = {
        "A: Centroid (5 seeds)": {},
        "B: UserVector-5": {},
        "C: UserVector-16": {},
    }
    all_n_seeds: dict[str, list[int]] = {name: [] for name in all_preds}

    for i, tid in enumerate(targets):
        if (i + 1) % 500 == 0:
            logger.info("  Progress: %d / %d", i + 1, len(targets))

        tidx = gs_id_to_idx[tid]
        target_emb = gs_emb[tidx]

        # Top-5 accords (simulated quiz)
        top5 = simulate_quiz_conf(tid, item_index, all_accords, accord_to_idx, cooccurrence, rng)

        # Build seed sets
        seeds_5: list[str] = []
        seeds_16: list[str] = []
        for accord in top5:
            pool = accord_pools.get(accord, [])
            pool = [fid for fid in pool if fid != tid]
            seeds_5.extend(pool[:1])
            seeds_16.extend(pool[:4])

        seeds_5 = list(dict.fromkeys(seeds_5))
        seeds_16 = list(dict.fromkeys(seeds_16))

        # Simulate ratings based on embedding similarity to target
        def rate_items(fids: list[str]) -> list[tuple[str, float]]:
            out = []
            for fid in fids:
                if fid in gs_id_to_idx:
                    r = simulate_rating(target_emb, gs_emb[gs_id_to_idx[fid]])
                    out.append((fid, r))
            return out

        ratings_5 = rate_items(seeds_5)
        ratings_16 = rate_items(seeds_16)

        exclude_5 = set(seeds_5)
        exclude_16 = set(seeds_16)

        # Strategy A: Centroid (current pipeline)
        centroid = compute_centroid(gs_emb, gs_id_to_idx, seeds_5)
        if centroid is not None:
            all_preds["A: Centroid (5 seeds)"][tid] = knn_search(
                gs_emb, gs_ids, centroid, top_k=10, exclude_ids=exclude_5
            )
        all_n_seeds["A: Centroid (5 seeds)"].append(len(seeds_5))

        # Strategy B: UserVector-5
        uv5 = compute_user_vector(gs_emb, gs_id_to_idx, ratings_5)
        if uv5 is not None:
            all_preds["B: UserVector-5"][tid] = knn_search(
                gs_emb, gs_ids, uv5, top_k=10, exclude_ids=exclude_5
            )
        all_n_seeds["B: UserVector-5"].append(len(ratings_5))

        # Strategy C: UserVector-16
        uv16 = compute_user_vector(gs_emb, gs_id_to_idx, ratings_16)
        if uv16 is not None:
            all_preds["C: UserVector-16"][tid] = knn_search(
                gs_emb, gs_ids, uv16, top_k=10, exclude_ids=exclude_16
            )
        all_n_seeds["C: UserVector-16"].append(len(ratings_16))

    # ── Results ──
    logger.info("\n" + "=" * 80)
    logger.info("  RESULTS @ k=10  (GT-D)")
    logger.info("=" * 80)

    logger.info(f"\n  {'Strategy':<30s} {'FamHit@10':>10s} {'NDCG@10':>10s} {'Recall@10':>10s} {'Seeds':>6s}")
    logger.info("  " + "-" * 68)

    strat_names = ["A: Centroid (5 seeds)", "B: UserVector-5", "C: UserVector-16"]
    for sname in strat_names:
        preds = all_preds[sname]
        m = compute_metrics(preds, gt, list(preds.keys()))
        mean_n = np.mean(all_n_seeds[sname]) if all_n_seeds[sname] else 0
        logger.info(f"  {sname:<30s} {m['family_hit_rate']:>10.4f} {m['ndcg_mean']:>10.6f} {m['recall_mean']:>10.6f} {mean_n:>5.1f}")

    # Oracle
    oracle_hits = 0
    oracle_n = 0
    for tid in targets:
        if tid not in gs_id_to_idx:
            continue
        tidx = gs_id_to_idx[tid]
        sims = np.dot(gs_emb, gs_emb[tidx])
        order = np.argsort(sims)[::-1]
        found = False
        rc = 0
        for idx in order:
            if gs_ids[idx] == tid:
                continue
            rc += 1
            if gs_ids[idx] in gt.get(tid, set()):
                found = True
                break
            if rc >= 10:
                break
        if found:
            oracle_hits += 1
        oracle_n += 1
    oracle_fh = oracle_hits / oracle_n if oracle_n > 0 else 0

    logger.info(f"  {'Oracle (self-as-seed)':<30s} {oracle_fh:>10.4f} {'—':>10s} {'—':>10s} {'—':>5s}")
    logger.info(f"  {'':30s} {oracle_hits}/{oracle_n} ({100*oracle_fh:.1f}%)")

    # Improvement vs baseline (A)
    logger.info("\n[PIPELINE / ORACLE RATIO]")
    logger.info(f"  {'Strategy':<30s} {'Pipeline FH':>12s} {'Oracle FH':>12s} {'P/O':>8s} {'vs A':>8s}")
    logger.info("  " + "-" * 70)
    base_m = compute_metrics(all_preds["A: Centroid (5 seeds)"], gt, list(all_preds["A: Centroid (5 seeds)"].keys()))
    base_fh = base_m["family_hit_rate"]
    for sname in strat_names:
        m = compute_metrics(all_preds[sname], gt, list(all_preds[sname].keys()))
        p_o = m["family_hit_rate"] / oracle_fh if oracle_fh > 0 else 0
        vs_a = (m["family_hit_rate"] / base_fh - 1) * 100 if base_fh > 0 else 0
        logger.info(f"  {sname:<30s} {m['family_hit_rate']:>12.4f} {oracle_fh:>12.4f} {p_o:>7.3f} {vs_a:>+7.1f}%")

    logger.info("\n" + "=" * 80)
    logger.info("  SUMMARY")
    logger.info("=" * 80)

    best_fh = -1
    best_name = ""
    for sname in strat_names:
        m = compute_metrics(all_preds[sname], gt, list(all_preds[sname].keys()))
        logger.info(f"  {sname:<30s} FH={m['family_hit_rate']:.4f} NDCG={m['ndcg_mean']:.6f} ({m['family_hits']}/{m['n']})")
        if m['family_hit_rate'] > best_fh:
            best_fh = m['family_hit_rate']
            best_name = sname

    logger.info(f"\n  Winner: {best_name} (FH={best_fh:.4f})")
    logger.info(f"  Oracle: FH={oracle_fh:.4f} ({oracle_hits}/{oracle_n})")
    logger.info(f"  P/O ratio: {best_fh / oracle_fh:.3f}" if oracle_fh > 0 else "")


if __name__ == "__main__":
    main()
