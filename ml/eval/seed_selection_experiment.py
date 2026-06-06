"""Seed selection experiment: 3 strategies for B2 bottleneck.

Strategies:
  A — Popularity (baseline): highest rating_count item per accord
  B — Popularity + Note Overlap: rating_count + note Jaccard with quiz profile
  C — Popularity + Embedding Similarity: rating_count + GS embedding cos sim with quiz-region centroid

Usage:
    python -m ml.eval.seed_selection_experiment
"""

import json
import logging
import sys
from collections import Counter

import numpy as np

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
logger = logging.getLogger("seed_exp")

LAMBDA = 3.0  # weight for relevance signal vs popularity

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
        index[fid] = {
            "brand": str(item.get("brand", "")).lower(),
            "primary_accord": raw_accords[0] if raw_accords else "Unknown",
            "accords_set": set(raw_accords),
            "rating_count": item.get("rating_count", 0),
            "rating_value": item.get("rating_value", 0.0),
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


# ── Strategy A: Popularity (current baseline) ─────────────────────────────────

def select_seeds_popularity(
    quiz_confidence: dict[str, float],
    catalog: list[dict],
    max_seeds: int = 5,
) -> tuple[list[str], list[float]]:
    """For each accord, pick highest rating_count item."""
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


# ── Strategy B: Popularity + Note Overlap ─────────────────────────────────────

def select_seeds_note_overlap(
    quiz_confidence: dict[str, float],
    catalog: list[dict],
    item_index: dict,
    max_seeds: int = 5,
    lam: float = LAMBDA,
) -> tuple[list[str], list[float]]:
    """For each accord, score by: norm(rating_count) + lam * note_jaccard.

    note_jaccard = Jaccard(item.accords_set, set of top-5 quiz accords).
    """
    sorted_accords = sorted(quiz_confidence.items(), key=lambda x: x[1], reverse=True)[:max_seeds]
    quiz_accord_set = {a for a, _ in sorted_accords}
    seed_ids: list[str] = []
    weights: list[float] = []

    for accord, confidence in sorted_accords:
        candidates: list[tuple[str, float]] = []
        for item in catalog:
            accords_set = {str(a).lower() for a in (item.get("accords") or [])}
            if accord not in accords_set:
                continue
            fid = str(item["id"])
            rc = item.get("rating_count", 0)
            # Note Jaccard: item's full accord set vs quiz profile
            union = accords_set | quiz_accord_set
            note_jac = len(accords_set & quiz_accord_set) / len(union) if union else 0.0
            candidates.append((fid, rc, note_jac))

        if not candidates:
            continue

        rc_vals = np.array([c[1] for c in candidates], dtype=np.float64)
        rc_min, rc_max = float(rc_vals.min()), float(rc_vals.max())
        rc_range = rc_max - rc_min if rc_max > rc_min else 1.0

        best_score = -1.0
        best_id: str | None = None
        for fid, rc, n_jac in candidates:
            rc_norm = (rc - rc_min) / rc_range
            score = rc_norm + lam * n_jac
            if score > best_score:
                best_score = score
                best_id = fid

        if best_id is not None:
            seed_ids.append(best_id)
            weights.append(confidence)

    return seed_ids, weights


# ── Strategy C: Popularity + Embedding Similarity ─────────────────────────────

def select_seeds_embedding_sim(
    quiz_confidence: dict[str, float],
    catalog: list[dict],
    item_index: dict,
    gs_embeddings: np.ndarray,
    gs_id_to_idx: dict[str, int],
    max_seeds: int = 5,
    lam: float = LAMBDA,
) -> tuple[list[str], list[float]]:
    """For each accord, score by: norm(rating_count) + lam * emb_sim.

    emb_sim = cosine similarity between item's GS embedding and a
    'quiz-region centroid' (mean embedding of items whose primary accord
    is among the top-5 quiz accords).
    """
    sorted_accords = sorted(quiz_confidence.items(), key=lambda x: x[1], reverse=True)[:max_seeds]
    top_accord_set = {a for a, _ in sorted_accords}

    # Build quiz-region centroid: mean embedding of items whose primary accord is in top-5
    region_embeddings: list[np.ndarray] = []
    for item in catalog:
        fid = str(item["id"])
        raw_accords = [str(a).lower() for a in (item.get("accords") or [])]
        primary = raw_accords[0] if raw_accords else ""
        if primary in top_accord_set and fid in gs_id_to_idx:
            region_embeddings.append(gs_embeddings[gs_id_to_idx[fid]])

    if not region_embeddings:
        # Fall back to popularity
        return select_seeds_popularity(quiz_confidence, catalog, max_seeds)

    quiz_centroid = np.mean(region_embeddings, axis=0)
    quiz_norm = np.linalg.norm(quiz_centroid)
    if quiz_norm > 0:
        quiz_centroid = quiz_centroid / quiz_norm

    seed_ids: list[str] = []
    weights: list[float] = []

    for accord, confidence in sorted_accords:
        candidates: list[tuple[str, float, float]] = []
        for item in catalog:
            accords_set = {str(a).lower() for a in (item.get("accords") or [])}
            if accord not in accords_set:
                continue
            fid = str(item["id"])
            rc = item.get("rating_count", 0)
            if fid in gs_id_to_idx:
                emb_sim = float(np.dot(gs_embeddings[gs_id_to_idx[fid]], quiz_centroid))
                candidates.append((fid, rc, emb_sim))

        if not candidates:
            continue

        rc_vals = np.array([c[1] for c in candidates], dtype=np.float64)
        rc_min, rc_max = float(rc_vals.min()), float(rc_vals.max())
        rc_range = rc_max - rc_min if rc_max > rc_min else 1.0

        best_score = -1.0
        best_id: str | None = None
        for fid, rc, e_sim in candidates:
            rc_norm = (rc - rc_min) / rc_range
            # emb_sim is in [-1, 1]; map to [0, 1]
            e_sim_norm = (e_sim + 1.0) / 2.0
            score = rc_norm + lam * e_sim_norm
            if score > best_score:
                best_score = score
                best_id = fid

        if best_id is not None:
            seed_ids.append(best_id)
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


# ── Ground truth ──────────────────────────────────────────────────────────────

def build_ground_truth(item_index: dict) -> dict[str, set[str]]:
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

        # Family hit
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
        "ndcg_std": float(np.std(ndcg_scores, ddof=1)) if len(ndcg_scores) > 1 else 0.0,
        "hit_rate": float(np.mean(hit_scores)) if hit_scores else 0.0,
        "family_hit_rate": family_hits / n if n > 0 else 0.0,
        "recall_mean": float(np.mean(recall_scores)) if recall_scores else 0.0,
        "n": n,
        "family_hits": family_hits,
    }


def bootstrap_test(a: list[float], b: list[float], n_iter: int = 10000, seed: int = 42) -> float:
    rng = np.random.default_rng(seed)
    diffs = np.array(a) - np.array(b)
    observed = np.mean(diffs)
    if abs(observed) < 1e-15:
        return 1.0
    count = 0
    for _ in range(n_iter):
        if np.mean(diffs * rng.choice([-1, 1], size=len(diffs))) >= observed:
            count += 1
    return (count + 1) / (n_iter + 1)


def pairwise_ndcg(
    predictions_a: dict, predictions_b: dict, gt: dict, target_ids: list[str], k: int = 10
) -> tuple[list[float], list[float]]:
    scores_a, scores_b = [], []
    for tid in target_ids:
        ranked_a = predictions_a.get(tid, [])
        ranked_b = predictions_b.get(tid, [])
        relevant = gt.get(tid, set())
        n_rel = len(relevant)
        dcg_a = sum(1.0 / np.log2(r + 1) for r, (iid, _) in enumerate(ranked_a[:k], 1) if iid in relevant)
        dcg_b = sum(1.0 / np.log2(r + 1) for r, (iid, _) in enumerate(ranked_b[:k], 1) if iid in relevant)
        idcg = sum(1.0 / np.log2(i + 1) for i in range(1, min(n_rel, k) + 1)) if n_rel > 0 else 1.0
        scores_a.append(dcg_a / idcg if idcg > 0 else 0.0)
        scores_b.append(dcg_b / idcg if idcg > 0 else 0.0)
    return scores_a, scores_b


# ── B2 diagnostics per strategy ────────────────────────────────────────────────

def diagnose_seeds(
    seed_ids: list[str],
    target_id: str,
    item_index: dict,
) -> dict:
    """Check seed relevance: brand match, accord match, brand OR accord match."""
    meta = item_index[target_id]
    t_brand = meta["brand"]
    t_accord = meta["primary_accord"]

    brand_match = False
    accord_match = False
    for sid in seed_ids:
        if sid in item_index:
            if item_index[sid]["brand"] == t_brand:
                brand_match = True
            if item_index[sid]["primary_accord"] == t_accord:
                accord_match = True

    return {
        "brand_match": brand_match,
        "accord_match": accord_match,
        "either_match": brand_match or accord_match,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    seed = 42
    rng = np.random.default_rng(seed)

    logger.info("=" * 80)
    logger.info("  SEED SELECTION EXPERIMENT (B2 Bottleneck)")
    logger.info("  Comparing 3 strategies: A=Popularity, B=+NoteOverlap, C=+EmbeddingSim")
    logger.info("=" * 80)

    # ── Load data ──
    logger.info("\n[1] Loading data...")
    catalog = load_catalog()
    item_index = build_item_index(catalog)
    gs_emb, gs_ids, gs_id_to_idx = load_gs_embeddings()
    gs_set = set(gs_ids)
    logger.info("  Catalog items: %d", len(catalog))
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
    gt = build_ground_truth(item_index)
    logger.info("  Non-empty GT queries: %d / %d", sum(1 for v in gt.values() if v), len(gt))

    targets = [
        fid for fid, meta in item_index.items()
        if meta["primary_accord"] in accord_to_idx
        and meta["primary_accord"] != "Unknown"
        and fid in gs_set
        and fid in gt
        and gt[fid]
    ]
    logger.info("  Targets: %d / %d", len(targets), len(catalog))

    # ── Run all 3 strategies ──
    strategies = {
        "A (Popularity)": lambda qc: select_seeds_popularity(qc, catalog),
        "B (+NoteOverlap)": lambda qc: select_seeds_note_overlap(qc, catalog, item_index),
        "C (+EmbeddingSim)": lambda qc: select_seeds_embedding_sim(qc, catalog, item_index, gs_emb, gs_id_to_idx),
    }

    all_predictions: dict[str, dict] = {name: {} for name in strategies}
    all_seed_diagnostics: dict[str, list] = {name: [] for name in strategies}
    all_n_seeds: dict[str, list[int]] = {name: [] for name in strategies}
    all_seed_ids_per_target: dict[str, list[list[str]]] = {name: [] for name in strategies}
    strat_names = list(strategies.keys())

    logger.info("\n[2] Running experiment on %d targets...", len(targets))
    for i, tid in enumerate(targets):
        if (i + 1) % 500 == 0:
            logger.info("  Progress: %d / %d", i + 1, len(targets))

        quiz_conf = generate_target_quiz(tid, item_index, all_accords, accord_to_idx, cooccurrence, rng)

        # Collect all seed IDs first, then process
        target_seed_ids: dict[str, list[str]] = {}
        for sname, sfn in strategies.items():
            seed_ids, weights = sfn(quiz_conf)
            target_seed_ids[sname] = seed_ids
            all_seed_ids_per_target[sname].append(seed_ids)

            all_n_seeds[sname].append(len(seed_ids))
            diag = diagnose_seeds(seed_ids, tid, item_index)
            all_seed_diagnostics[sname].append(diag)

            if not seed_ids:
                continue

            centroid = compute_centroid(gs_emb, gs_id_to_idx, seed_ids, weights)
            if centroid is None:
                continue

            preds = knn_search(gs_emb, gs_ids, centroid, top_k=50, exclude_ids=set(seed_ids))
            all_predictions[sname][tid] = preds

    # ── Results ──
    logger.info("\n" + "=" * 80)
    logger.info("  RESULTS")
    logger.info("=" * 80)

    # B2 diagnostic: seed brand/accord match rates
    logger.info("\n[B2 DIAGNOSTIC: SEED RELEVANCE]")
    logger.info(f"  {'Strategy':<25s} {'BrandMatch':>12s} {'AccordMatch':>13s} {'EitherMatch':>12s}")
    logger.info("  " + "-" * 62)
    for sname in strat_names:
        diags = all_seed_diagnostics[sname]
        bm = sum(1 for d in diags if d["brand_match"]) / len(diags) * 100 if diags else 0
        am = sum(1 for d in diags if d["accord_match"]) / len(diags) * 100 if diags else 0
        em = sum(1 for d in diags if d["either_match"]) / len(diags) * 100 if diags else 0
        ns = np.mean(all_n_seeds[sname]) if all_n_seeds[sname] else 0
        logger.info(f"  {sname:<25s} {bm:>11.1f}% {am:>12.1f}% {em:>11.1f}%  (mean seeds={ns:.1f})")

    # Metrics at k=5, 10, 20
    for k in [5, 10, 20]:
        logger.info(f"\n[METRICS @ k={k}]")
        logger.info(f"  {'Strategy':<25s} {'NDCG@k':>10s} {'HitRate':>10s} {'FamHitRate':>12s} {'Recall@k':>10s}")
        logger.info("  " + "-" * 68)

        perf = {}
        for sname in strat_names:
            preds = all_predictions[sname]
            m = compute_metrics(preds, gt, list(preds.keys()), k=k)
            perf[sname] = m
            logger.info(f"  {sname:<25s} {m['ndcg_mean']:>10.6f} {m['hit_rate']:>10.6f} {m['family_hit_rate']:>12.6f} {m['recall_mean']:>10.6f}")

        # Pairwise significance vs baseline (A)
        base_preds = all_predictions[strat_names[0]]
        for sname in strat_names[1:]:
            a_scores, b_scores = pairwise_ndcg(
                base_preds, all_predictions[sname], gt,
                list(base_preds.keys()), k=k,
            )
            if len(a_scores) > 1:
                p = bootstrap_test(b_scores, a_scores)  # is B > A?
                diff = np.mean(b_scores) - np.mean(a_scores)
                sig = "SIGNIFICANT" if p < 0.05 else "trend" if p < 0.10 else "n.s."
                logger.info(f"  {sname:<25s} vs A: DeltaNDCG={diff:+.6f}  p={p:.4f}  ({sig})")

    # Top-10 family hit detail
    logger.info("\n[FAMILY HIT DETAIL @ k=10]")
    logger.info(f"  {'Strategy':<25s} {'Hits':>6s} {'/N':>5s} {'Rate':>8s} {'Improvement':>12s}")
    logger.info("  " + "-" * 58)
    base_fh = max(1, sum(
        1 for tid in all_predictions[strat_names[0]]
        if any(iid in gt.get(tid, set()) for iid, _ in all_predictions[strat_names[0]][tid][:10])
    ))
    for sname in strat_names:
        preds = all_predictions[sname]
        hits = sum(1 for tid in preds if any(iid in gt.get(tid, set()) for iid, _ in preds[tid][:10]))
        n = len(preds)
        rate = hits / n * 100 if n else 0
        imp = (hits / base_fh - 1) * 100 if base_fh else 0
        logger.info(f"  {sname:<25s} {hits:>6d} /{n:>4d} {rate:>7.2f}% {imp:>+11.1f}%")

    # Seed overlap
    logger.info("\n[SEED OVERLAP (mean Jaccard between strategy seed sets)]")
    for si in range(len(strat_names)):
        for sj in range(si + 1, len(strat_names)):
            jaccards = []
            for t_idx in range(len(targets)):
                set_i = set(all_seed_ids_per_target[strat_names[si]][t_idx])
                set_j = set(all_seed_ids_per_target[strat_names[sj]][t_idx])
                union = set_i | set_j
                if union:
                    jaccards.append(len(set_i & set_j) / len(union))
            mean_jac = np.mean(jaccards) if jaccards else 0.0
            logger.info(f"  {strat_names[si]} vs {strat_names[sj]}: mean Jaccard={mean_jac:.4f}")

    # ── Summary ──
    logger.info("\n" + "=" * 80)
    logger.info("  SUMMARY")
    logger.info("=" * 80)

    best_ndcg = -1.0
    best_name = ""
    for sname in strat_names:
        m = compute_metrics(all_predictions[sname], gt, list(all_predictions[sname].keys()), k=10)
        logger.info(f"  {sname:<25s} NDCG@10={m['ndcg_mean']:.6f}  FamilyHitRate={m['family_hit_rate']:.4f} ({m['family_hits']}/{m['n']})")
        if m['ndcg_mean'] > best_ndcg:
            best_ndcg = m['ndcg_mean']
            best_name = sname

    logger.info(f"\n  Winner: {best_name}")
    logger.info(f"  Baseline (A): {compute_metrics(all_predictions[strat_names[0]], gt, list(all_predictions[strat_names[0]].keys()), k=10)['ndcg_mean']:.6f}")
    logger.info(f"  Improvement: {(best_ndcg / max(1e-10, compute_metrics(all_predictions[strat_names[0]], gt, list(all_predictions[strat_names[0]].keys()), k=10)['ndcg_mean']) - 1) * 100:.1f}%")

    # Oracle comparison
    oracle_hits = 0
    oracle_n = 0
    for tid in targets:
        if tid not in gs_id_to_idx:
            continue
        tidx = gs_id_to_idx[tid]
        self_sims = np.dot(gs_emb, gs_emb[tidx])
        order = np.argsort(self_sims)[::-1]
        rank_c = 0
        found = False
        for idx in order:
            if gs_ids[idx] == tid:
                continue
            rank_c += 1
            if gs_ids[idx] in gt.get(tid, set()):
                found = True
                break
            if rank_c >= 10:
                break
        if found:
            oracle_hits += 1
        oracle_n += 1

    logger.info(f"\n  Oracle (self-as-seed) top-10 family hit: {oracle_hits}/{oracle_n} ({100*oracle_hits/oracle_n:.1f}%)")


if __name__ == "__main__":
    main()
