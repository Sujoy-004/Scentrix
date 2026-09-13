"""Pipeline-oracle gap decomposition under GT-D.

Controlled ablations isolating seed selection, centroid construction, and retrieval losses.

Usage:
    python -m ml.eval.pipeline_oracle_gap
"""

import json
import logging
import sys

import numpy as np

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
logger = logging.getLogger("gap_decomp")

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


def build_gt_accord_note_overlap(item_index: dict, threshold: float = NOTE_JACCARD_THRESHOLD) -> dict[str, set[str]]:
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
            union = t_notes | ometa["notes_set"]
            if union and len(t_notes & ometa["notes_set"]) / len(union) > threshold:
                relevant.add(oid)
        if relevant:
            gt[fid] = relevant
    return gt


def generate_target_quiz(
    target_id: str, item_index: dict, all_accords: list[str],
    accord_to_idx: dict[str, int], cooccurrence: dict[str, list[str]],
    rng: np.random.Generator, noise: float = 0.05,
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
    quiz_confidence: dict[str, float], catalog: list[dict], max_seeds: int = 5,
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
    embeddings: np.ndarray, id_to_idx: dict[str, int],
    seed_ids: list[str], weights: list[float] | None = None,
) -> np.ndarray | None:
    indices = [id_to_idx[sid] for sid in seed_ids if sid in id_to_idx]
    if not indices:
        return None
    seed_embs = embeddings[indices]
    if weights is not None:
        valid_w = np.array(
            [w for sid, w in zip(seed_ids, weights) if sid in id_to_idx], dtype=np.float64,
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
    embeddings: np.ndarray, node_ids: list[str],
    centroid: np.ndarray, top_k: int = 50, exclude_ids: set | None = None,
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


def compute_metrics(predictions: dict[str, list[tuple[str, float]]], gt: dict[str, set[str]], target_ids: list[str], k: int = 10) -> dict:
    ndcg_scores, hit_scores, recall_scores = [], [], []
    family_hits = 0
    for tid in target_ids:
        ranked = predictions.get(tid, [])
        if not ranked:
            continue
        top_k_ids = {iid for iid, _ in ranked[:k]}
        relevant = gt.get(tid, set())
        hit_scores.append(1.0 if tid in top_k_ids else 0.0)
        if top_k_ids & relevant:
            family_hits += 1
        if relevant:
            n_rel = len(relevant)
            dcg = sum(1.0 / np.log2(r + 1) for r, (iid, _) in enumerate(ranked[:k], 1) if iid in relevant)
            idcg = sum(1.0 / np.log2(i + 1) for i in range(1, min(n_rel, k) + 1))
            ndcg_scores.append(dcg / idcg if idcg > 0 else 0.0)
            recall_scores.append(len(top_k_ids & relevant) / n_rel)
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
    }


def main():
    seed = 42
    rng = np.random.default_rng(seed)

    logger.info("=" * 80)
    logger.info("  PIPELINE-ORACLE GAP DECOMPOSITION (GT-D)")
    logger.info("  Controlled ablations: seed selection, centroid, retrieval")
    logger.info("=" * 80)

    # ── Load data ──
    logger.info("\n[1] Loading data...")
    catalog = load_catalog()
    item_index = build_item_index(catalog)
    gs_emb, gs_ids, gs_id_to_idx = load_gs_embeddings()
    gs_set = set(gs_ids)

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
    gt = build_gt_accord_note_overlap(item_index, NOTE_JACCARD_THRESHOLD)

    targets = [
        fid for fid, meta in item_index.items()
        if meta["primary_accord"] in accord_to_idx and meta["primary_accord"] != "Unknown"
        and fid in gs_set and fid in gt and gt[fid]
    ]
    logger.info("  Targets with GT-D: %d", len(targets))

    # ── Run all ablations ──
    logger.info("\n[2] Running 7 ablation variants on %d targets...", len(targets))

    # predictions[ablation_name][target_id] = list[(rec_id, score)]
    preds: dict[str, dict[str, list[tuple[str, float]]]] = {
        "A: Oracle": {},
        "B: Oracle + production retrieval": {},
        "C: Prod seeds + oracle centroid": {},
        "D: Prod seeds + prod centroid": {},
        "E: Single-seed centroid": {},
        "F: Top-3 centroid": {},
        "G: Top-5 centroid": {},
    }
    failures: dict[str, int] = {k: 0 for k in preds}
    n_seeds_collected: dict[str, list[int]] = {k: [] for k in preds}

    for i, tid in enumerate(targets):
        if (i + 1) % 500 == 0:
            logger.info("  Progress: %d / %d", i + 1, len(targets))

        # Generate quiz and production seeds (shared across ablations D, E, F, G)
        quiz_conf = generate_target_quiz(tid, item_index, all_accords, accord_to_idx, cooccurrence, rng)
        prod_seed_ids, prod_weights = select_seeds_popularity(quiz_conf, catalog)

        valid_seeds = [(sid, w) for sid, w in zip(prod_seed_ids, prod_weights) if sid in gs_id_to_idx]
        top1 = valid_seeds[:1] if valid_seeds else []
        top3 = valid_seeds[:3] if valid_seeds else []
        top5 = valid_seeds[:5] if valid_seeds else []

        n_seeds_collected["D: Prod seeds + prod centroid"].append(len(top5))
        n_seeds_collected["E: Single-seed centroid"].append(len(top1))
        n_seeds_collected["F: Top-3 centroid"].append(len(top3))
        n_seeds_collected["G: Top-5 centroid"].append(len(top5))

        # Target embedding (oracle)
        tidx = gs_id_to_idx[tid]
        target_emb = gs_emb[tidx]

        # ── A: Oracle ──
        exclude_a = {tid}
        result_a = knn_search(gs_emb, gs_ids, target_emb, top_k=50, exclude_ids=exclude_a)
        preds["A: Oracle"][tid] = result_a

        # ── B: Oracle + production retrieval ──
        # Uses target embedding as centroid, excludes production seeds
        prod_seed_set = set(sid for sid, _ in valid_seeds)
        result_b = knn_search(gs_emb, gs_ids, target_emb, top_k=50, exclude_ids=prod_seed_set)
        preds["B: Oracle + production retrieval"][tid] = result_b

        # ── C: Production seeds + oracle centroid ──
        # Production seeds as basis, but centroid = target embedding
        # (Same centroid as A/B, different conceptual framing)
        result_c = knn_search(gs_emb, gs_ids, target_emb, top_k=50, exclude_ids=prod_seed_set)
        preds["C: Prod seeds + oracle centroid"][tid] = result_c

        # ── D: Production seeds + production centroid ──
        if valid_seeds:
            d_seed_ids = [s for s, _ in valid_seeds]
            d_weights = [w for _, w in valid_seeds]
            centroid_d = compute_centroid(gs_emb, gs_id_to_idx, d_seed_ids, d_weights)
            if centroid_d is not None:
                result_d = knn_search(gs_emb, gs_ids, centroid_d, top_k=50, exclude_ids=set(d_seed_ids))
                preds["D: Prod seeds + prod centroid"][tid] = result_d
            else:
                failures["D: Prod seeds + prod centroid"] += 1
        else:
            failures["D: Prod seeds + prod centroid"] += 1

        # ── E: Single-seed centroid ──
        if top1:
            e_seed_id = top1[0][0]
            centroid_e = compute_centroid(gs_emb, gs_id_to_idx, [e_seed_id], [1.0])
            if centroid_e is not None:
                result_e = knn_search(gs_emb, gs_ids, centroid_e, top_k=50, exclude_ids={e_seed_id})
                preds["E: Single-seed centroid"][tid] = result_e
            else:
                failures["E: Single-seed centroid"] += 1
        else:
            failures["E: Single-seed centroid"] += 1

        # ── F: Top-3 centroid ──
        if top3:
            f_seed_ids = [s for s, _ in top3]
            f_weights = [w for _, w in top3]
            centroid_f = compute_centroid(gs_emb, gs_id_to_idx, f_seed_ids, f_weights)
            if centroid_f is not None:
                result_f = knn_search(gs_emb, gs_ids, centroid_f, top_k=50, exclude_ids=set(f_seed_ids))
                preds["F: Top-3 centroid"][tid] = result_f
            else:
                failures["F: Top-3 centroid"] += 1
        else:
            failures["F: Top-3 centroid"] += 1

        # ── G: Top-5 centroid ──
        if top5:
            g_seed_ids = [s for s, _ in top5]
            g_weights = [w for _, w in top5]
            centroid_g = compute_centroid(gs_emb, gs_id_to_idx, g_seed_ids, g_weights)
            if centroid_g is not None:
                result_g = knn_search(gs_emb, gs_ids, centroid_g, top_k=50, exclude_ids=set(g_seed_ids))
                preds["G: Top-5 centroid"][tid] = result_g
            else:
                failures["G: Top-5 centroid"] += 1
        else:
            failures["G: Top-5 centroid"] += 1

    # ── Results ──
    logger.info("\n" + "=" * 80)
    logger.info("  RESULTS @ k=10")
    logger.info("=" * 80)

    logger.info(f"\n{'Ablation':<42s} {'FamilyHit':>10s} {'NDCG':>10s} {'Recall':>10s} {'Hits/N':>12s}")
    logger.info("  " + "-" * 84)

    results = {}
    for aname in ["A: Oracle", "B: Oracle + production retrieval", "C: Prod seeds + oracle centroid",
                   "D: Prod seeds + prod centroid", "E: Single-seed centroid",
                   "F: Top-3 centroid", "G: Top-5 centroid"]:
        m = compute_metrics(preds[aname], gt, list(preds[aname].keys()), k=10)
        results[aname] = m
        hit_str = f"{m['family_hits']}/{m['n']}"
        logger.info(f"  {aname:<42s} {m['family_hit_rate']:>10.4f} {m['ndcg_mean']:>10.6f} {m['recall_mean']:>10.6f} {hit_str:>12s}")

    # ── Loss decomposition ──
    logger.info("\n" + "=" * 80)
    logger.info("  LOSS DECOMPOSITION")
    logger.info("=" * 80)

    oracle_fh = results["A: Oracle"]["family_hit_rate"]
    oracle_ndcg = results["A: Oracle"]["ndcg_mean"]

    # Ablation keys
    B_key = "B: Oracle + production retrieval"
    C_key = "C: Prod seeds + oracle centroid"
    D_key = "D: Prod seeds + prod centroid"
    E_key = "E: Single-seed centroid"
    F_key = "F: Top-3 centroid"
    G_key = "G: Top-5 centroid"

    # Total gap
    total_loss_pp = (oracle_fh - results[D_key]["family_hit_rate"]) * 100
    logger.info(f"\n  Total gap (Oracle - Pipeline): {total_loss_pp:.2f} pp")

    # Component: Exclusion set loss (B vs A)
    # B uses target centroid but production seed exclusion set
    excl_loss_pp = (results["A: Oracle"]["family_hit_rate"] - results[B_key]["family_hit_rate"]) * 100
    logger.info(f"\n  [1] Exclusion set loss (A - B): {excl_loss_pp:.2f} pp")
    logger.info(f"      B = oracle centroid + production exclusion set")
    logger.info(f"      A - B isolates: do production seeds actively remove relevant items from results?")

    # The remaining gap after fixing centroid to oracle is the centroid loss
    # Compare D (prod centroid) vs C (oracle centroid, same seeds)
    # C uses oracle centroid + production exclusion set
    # D uses production centroid + production exclusion set
    centroid_loss_fh = (results[C_key]["family_hit_rate"] - results[D_key]["family_hit_rate"]) * 100
    centroid_loss_ndcg = (results[C_key]["ndcg_mean"] - results[D_key]["ndcg_mean"]) / results[C_key]["ndcg_mean"] * 100 if results[C_key]["ndcg_mean"] > 0 else 0
    logger.info(f"\n  [2] Centroid construction loss (C - D): {centroid_loss_fh:.2f} pp FH, {centroid_loss_ndcg:.1f}% NDCG")
    logger.info(f"      C = production seeds + oracle centroid (target embedding)")
    logger.info(f"      D = production seeds + production centroid (weighted average of seed embs)")
    logger.info(f"      C - D isolates: how much does the production centroid degrade retrieval?")

    # Seed count effect (E, F, G)
    logger.info(f"\n  [3] Seed count effect:")
    for label, key in [("1 seed (E)", E_key), ("3 seeds (F)", F_key), ("5 seeds = D (G)", G_key)]:
        fh = results[key]["family_hit_rate"]
        ndcg = results[key]["ndcg_mean"]
        loss_vs_oracle = (oracle_fh - fh) * 100
        logger.info(f"      {label:<25s} FH={fh:.4f}  NDCG={ndcg:.6f}  Loss vs oracle={loss_vs_oracle:.2f}pp")

    # ── Summary ──
    logger.info("\n" + "=" * 80)
    logger.info("  SUMMARY")
    logger.info("=" * 80)

    # Attribution
    logger.info(f"\n  Oracle ceiling (A):            {oracle_fh:.4f} ({results['A: Oracle']['family_hits']}/{results['A: Oracle']['n']})")
    logger.info(f"  Pipeline (D):                  {results[D_key]['family_hit_rate']:.4f} ({results[D_key]['family_hits']}/{results[D_key]['n']})")
    logger.info(f"  Total gap:                     {total_loss_pp:.2f} pp")
    logger.info(f"")

    # Net of exclusion set (B uses oracle centroid but production exclusions)
    # The real "centroid + retrieval" loss is B - D (both have same exclusion set)
    net_centroid_retrieval_loss = (results[B_key]["family_hit_rate"] - results[D_key]["family_hit_rate"]) * 100
    excl_alone = excl_loss_pp

    logger.info(f"  Attribution:")
    logger.info(f"    Exclusion set (seeds block relevant items):   {excl_alone:.2f} pp")
    logger.info(f"    Centroid + retrieval (centroid is diffuse):   {net_centroid_retrieval_loss:.2f} pp")
    logger.info(f"    Total:                                        {excl_alone + net_centroid_retrieval_loss:.2f} pp")
    logger.info(f"")

    # Seed count recommendation
    best_seed_count = max([(c, results[k]["family_hit_rate"]) for c, k in [("1", E_key), ("3", F_key), ("5", G_key)]], key=lambda x: x[1])
    logger.info(f"  Best seed count: {best_seed_count[0]} (FH={best_seed_count[1]:.4f})")

    # NDCG decomposition
    logger.info(f"\n  NDCG decomposition:")
    logger.info(f"    Oracle NDCG:                                   {oracle_ndcg:.6f}")
    logger.info(f"    + prod exclusion set (B):                      {results[B_key]['ndcg_mean']:.6f}")
    logger.info(f"    + prod centroid (D):                           {results[D_key]['ndcg_mean']:.6f}")
    logger.info(f"    Single-seed (E):                               {results[E_key]['ndcg_mean']:.6f}")
    logger.info(f"    Top-3 seeds (F):                               {results[F_key]['ndcg_mean']:.6f}")
    logger.info(f"    Top-5 seeds (G):                               {results[G_key]['ndcg_mean']:.6f}")


if __name__ == "__main__":
    main()
