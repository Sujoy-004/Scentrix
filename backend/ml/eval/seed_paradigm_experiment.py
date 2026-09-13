"""Seed paradigm experiment: 4 strategies for seed generation.

Compares:
  A: Current baseline (most popular per accord, independent)
  B: Top-K pool + centroid-aware selection (single-pass)
  C: Global joint selection (greedy, one pass)
  D: Quiz-region retrieval (embedding-space proximity)

All evaluated on GT-D with GS embeddings.

Usage:
    python -m ml.eval.seed_paradigm_experiment
"""

import json
import logging
import sys
from collections import Counter

import numpy as np

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
logger = logging.getLogger("paradigm_exp")

NOTE_JACCARD_THRESHOLD = 0.15
TOP_K = 10
LAMBDA = 3.0


def load_catalog(path: str = "ml/data/scentrix_master.json") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_gs_embeddings(emb_path: str = "ml/models/serving/v1/node_embeddings_jaccard.npy",
                       ids_path: str = "ml/models/serving/v1/node_ids_jaccard.json"):
    embeddings = np.load(emb_path)
    with open(ids_path, encoding="utf-8") as f:
        node_ids = json.load(f)
    return embeddings, node_ids, {fid: i for i, fid in enumerate(node_ids)}


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


def generate_target_quiz(target_id, item_index, all_accords, accord_to_idx, cooccurrence, rng, noise=0.05):
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


def compute_centroid(embeddings, id_to_idx, seed_ids, weights=None):
    indices = [id_to_idx[sid] for sid in seed_ids if sid in id_to_idx]
    if not indices:
        return None
    seed_embs = embeddings[indices]
    if weights is not None:
        valid_w = np.array([w for sid, w in zip(seed_ids, weights) if sid in id_to_idx], dtype=np.float64)
    else:
        valid_w = np.ones(len(indices), dtype=np.float64)
    w_sum = np.sum(valid_w)
    if w_sum <= 0:
        return None
    centroid = np.dot(valid_w, seed_embs) / w_sum
    norm = np.linalg.norm(centroid)
    return centroid / norm if norm > 0 else None


def knn_search(embeddings, node_ids, centroid, top_k=50, exclude_ids=None):
    sims = np.dot(embeddings, centroid)
    order = np.argsort(sims)[::-1]
    exclude = exclude_ids or set()
    results = []
    for idx in order:
        fid = node_ids[idx]
        if fid in exclude:
            continue
        results.append((fid, float(sims[idx])))
        if len(results) >= top_k:
            break
    return results


def compute_metrics(predictions, gt, target_ids, k=10):
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


# ── Precomputed structures for quiz centroid and accord item lists ────────────

def precompute_per_accord_lists(catalog, gs_id_to_idx):
    """For each accord, precompute a list of (fid, rc, emb_sim_to_mean) of items containing it."""
    from collections import defaultdict
    per_accord: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for item in catalog:
        accords_set = {str(a).lower() for a in (item.get("accords") or [])}
        fid = str(item["id"])
        if fid not in gs_id_to_idx:
            continue
        rc = item.get("rating_count", 0)
        for acc in accords_set:
            per_accord[acc].append((fid, rc))
    # Sort each by rating_count descending
    for acc in per_accord:
        per_accord[acc].sort(key=lambda x: -x[1])
    return per_accord


# ── Broad quiz centroid ───────────────────────────────────────────────────────

def get_broad_quiz_centroid(catalog, gs_emb, gs_id_to_idx, quiz_confidence, max_seeds=5):
    sorted_accords = sorted(quiz_confidence.items(), key=lambda x: x[1], reverse=True)[:max_seeds]
    top_accords = {a for a, _ in sorted_accords}
    region_embs = []
    for item in catalog:
        raw = [str(a).lower() for a in (item.get("accords") or [])]
        primary = raw[0] if raw else ""
        fid = str(item["id"])
        if primary in top_accords and fid in gs_id_to_idx:
            region_embs.append(gs_emb[gs_id_to_idx[fid]])
    if not region_embs:
        return None
    c = np.mean(region_embs, axis=0)
    n = np.linalg.norm(c)
    return c / n if n > 0 else None


# ── Strategy A: Baseline ─────────────────────────────────────────────────────

def strategy_a(quiz_confidence, per_accord, max_seeds=5):
    sorted_accords = sorted(quiz_confidence.items(), key=lambda x: x[1], reverse=True)[:max_seeds]
    seeds, weights = [], []
    for accord, confidence in sorted_accords:
        items = per_accord.get(accord, [])
        if items:
            seeds.append(items[0][0])
            weights.append(confidence)
    return seeds, weights


# ── Strategy B: Top-K + centroid-aware (single-pass) ─────────────────────────

def strategy_b(quiz_confidence, per_accord, gs_emb, gs_id_to_idx, broad_centroid, max_seeds=5, top_k=TOP_K):
    """Top-K candidates per accord, pick closest to broad quiz centroid."""
    sorted_accords = sorted(quiz_confidence.items(), key=lambda x: x[1], reverse=True)[:max_seeds]
    if broad_centroid is None:
        return strategy_a(quiz_confidence, per_accord, max_seeds)

    seeds, weights = [], []
    for accord, confidence in sorted_accords:
        candidates = per_accord.get(accord, [])[:top_k]
        if not candidates:
            continue
        best_fid = candidates[0][0]
        best_score = -1.0
        for fid, rc in candidates:
            if fid not in gs_id_to_idx:
                continue
            emb_sim = float(np.dot(gs_emb[gs_id_to_idx[fid]], broad_centroid))
            score = LAMBDA * emb_sim + np.log1p(rc) * 1e-4  # tiny popularity tiebreaker
            if score > best_score:
                best_score = score
                best_fid = fid
        seeds.append(best_fid)
        weights.append(confidence)
    return seeds, weights


# ── Strategy C: Global joint selection (greedy) ──────────────────────────────

def strategy_c(quiz_confidence, per_accord, gs_emb, gs_id_to_idx, broad_centroid, max_seeds=5):
    """Greedy global: pick seeds one at a time, each covering a new accord,
    maximizing proximity of progressive centroid to broad centroid."""
    sorted_accords = sorted(quiz_confidence.items(), key=lambda x: x[1], reverse=True)[:max_seeds]
    if broad_centroid is None:
        return strategy_a(quiz_confidence, per_accord, max_seeds)

    selected: list[str] = []
    selected_weights: list[float] = []
    covered_accords: set[str] = set()

    for round_idx in range(max_seeds):
        # Determine target accord (prefer uncovered)
        target_accord = None
        for accord, _ in sorted_accords:
            if accord not in covered_accords:
                target_accord = accord
                break
        if target_accord is None:
            target_accord = sorted_accords[-1][0]

        # Build candidate pool: items covering target accord NOT already selected
        candidates = [fid for fid, _ in per_accord.get(target_accord, []) if fid not in selected and fid in gs_id_to_idx]
        if not candidates:
            # Try any accord
            for accord, _ in sorted_accords:
                cands = [fid for fid, _ in per_accord.get(accord, []) if fid not in selected and fid in gs_id_to_idx]
                candidates.extend(cands)
            if not candidates:
                break

        best_fid = None
        best_score = -1.0
        for fid in candidates:
            test_seeds = selected + [fid]
            test_weights = selected_weights + [quiz_confidence.get(target_accord, 0.5)]
            centroid = compute_centroid(gs_emb, gs_id_to_idx, test_seeds, test_weights)
            if centroid is None:
                continue
            score = float(np.dot(centroid, broad_centroid))
            if score > best_score:
                best_score = score
                best_fid = fid

        if best_fid is None:
            break

        selected.append(best_fid)
        # Weight = max quiz confidence of item's matching accords
        if best_fid in gs_id_to_idx:
            pass  # we'll use the target accord confidence
        selected_weights.append(quiz_confidence.get(target_accord, 0.5))
        covered_accords.add(target_accord)

    if not selected:
        return strategy_a(quiz_confidence, per_accord, max_seeds)
    return selected, selected_weights


# ── Strategy D: Quiz-region retrieval ────────────────────────────────────────

def strategy_d(quiz_confidence, per_accord, gs_emb, gs_id_to_idx, broad_centroid, max_seeds=5):
    """Find seeds by embedding proximity to broad quiz centroid.
    Score all items by cos_sim to broad centroid, pick top 5 with accord diversity."""
    sorted_accords = sorted(quiz_confidence.items(), key=lambda x: x[1], reverse=True)[:max_seeds]
    top_accord_set = {a for a, _ in sorted_accords}
    if broad_centroid is None:
        return strategy_a(quiz_confidence, per_accord, max_seeds)

    # Score all items matching any top accord
    scored: list[tuple[str, float, set[str]]] = []
    for accord in top_accord_set:
        for fid, rc in per_accord.get(accord, []):
            if fid not in gs_id_to_idx:
                continue
            emb_sim = float(np.dot(gs_emb[gs_id_to_idx[fid]], broad_centroid))
            # deduplicate: keep best score per fid
            scored.append((fid, LAMBDA * emb_sim + np.log1p(rc) * 1e-4, accord))

    # Consolidate per fid (keep best score)
    best_per_fid: dict[str, tuple[float, set[str]]] = {}
    for fid, score, accord in scored:
        if fid not in best_per_fid or score > best_per_fid[fid][0]:
            best_per_fid[fid] = (score, {accord})
        elif score == best_per_fid[fid][0]:
            best_per_fid[fid][1].add(accord)

    items = [(fid, score, matched_accords) for fid, (score, matched_accords) in best_per_fid.items()]
    items.sort(key=lambda x: -x[1])

    # Greedy diverse selection: cover all top accords if possible
    selected: list[str] = []
    covered: set[str] = set()
    for fid, score, matched_accords in items:
        if len(selected) >= max_seeds:
            break
        new_accords = matched_accords - covered
        if new_accords or len(covered) == len(top_accord_set):
            selected.append(fid)
            covered |= matched_accords

    if not selected:
        return strategy_a(quiz_confidence, per_accord, max_seeds)

    # Weights: sum quiz confidences for matching accords
    weights = []
    for fid in selected:
        w = 0.0
        for accord, qc in sorted_accords:
            if fid in gs_id_to_idx and fid in gs_id_to_idx:
                pass  # check accord membership below
        # Simplified: weight = sum of confidences of all top accords this item matches
        w_sum = 0.0
        if fid in per_accord:
            for accord, qc in sorted_accords:
                if any(fid == pfid for pfid, _ in per_accord.get(accord, [])):
                    w_sum += qc
        weights.append(w_sum if w_sum > 0 else 0.1)

    return selected, weights


# ── Oracle ────────────────────────────────────────────────────────────────────

def run_oracle(target_id, gs_emb, gs_ids, gs_id_to_idx):
    if target_id not in gs_id_to_idx:
        return []
    tidx = gs_id_to_idx[target_id]
    return knn_search(gs_emb, gs_ids, gs_emb[tidx], top_k=50, exclude_ids={target_id})


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    seed = 42
    rng = np.random.default_rng(seed)

    logger.info("=" * 80)
    logger.info("  SEED PARADIGM EXPERIMENT")
    logger.info("  4 strategies evaluated on GT-D")
    logger.info("=" * 80)

    # ── Load ──
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

    # Precompute per-accord item lists
    logger.info("\n[2] Precomputing per-accord item lists...")
    per_accord = precompute_per_accord_lists(catalog, gs_id_to_idx)

    # ── Run ──
    def strat_a(qc):
        return strategy_a(qc, per_accord)

    def strat_b(qc, bc):
        return strategy_b(qc, per_accord, gs_emb, gs_id_to_idx, bc)

    def strat_c(qc, bc):
        return strategy_c(qc, per_accord, gs_emb, gs_id_to_idx, bc)

    def strat_d(qc, bc):
        return strategy_d(qc, per_accord, gs_emb, gs_id_to_idx, bc)

    oracle_preds: dict[str, list[tuple[str, float]]] = {}
    pipeline_preds: dict[str, dict[str, list[tuple[str, float]]]] = {
        "A: Baseline (popularity per accord)": {},
        "B: Top-K + centroid-aware": {},
        "C: Global joint selection": {},
        "D: Quiz-region retrieval": {},
    }
    seed_counts: dict[str, list[int]] = {n: [] for n in pipeline_preds}

    logger.info("\n[3] Running 4 strategies on %d targets...", len(targets))
    for i, tid in enumerate(targets):
        if (i + 1) % 500 == 0:
            logger.info("  Progress: %d / %d", i + 1, len(targets))

        quiz_conf = generate_target_quiz(tid, item_index, all_accords, accord_to_idx, cooccurrence, rng)
        oracle_preds[tid] = run_oracle(tid, gs_emb, gs_ids, gs_id_to_idx)

        broad_c = get_broad_quiz_centroid(catalog, gs_emb, gs_id_to_idx, quiz_conf)

        # A
        sids_a, sw_a = strat_a(quiz_conf)
        seed_counts["A: Baseline (popularity per accord)"].append(len(sids_a))
        if sids_a:
            c_a = compute_centroid(gs_emb, gs_id_to_idx, sids_a, sw_a)
            if c_a is not None:
                pipeline_preds["A: Baseline (popularity per accord)"][tid] = knn_search(
                    gs_emb, gs_ids, c_a, top_k=50, exclude_ids=set(sids_a))

        # B
        sids_b, sw_b = strat_b(quiz_conf, broad_c)
        seed_counts["B: Top-K + centroid-aware"].append(len(sids_b))
        if sids_b:
            c_b = compute_centroid(gs_emb, gs_id_to_idx, sids_b, sw_b)
            if c_b is not None:
                pipeline_preds["B: Top-K + centroid-aware"][tid] = knn_search(
                    gs_emb, gs_ids, c_b, top_k=50, exclude_ids=set(sids_b))

        # C
        sids_c, sw_c = strat_c(quiz_conf, broad_c)
        seed_counts["C: Global joint selection"].append(len(sids_c))
        if sids_c:
            c_c = compute_centroid(gs_emb, gs_id_to_idx, sids_c, sw_c)
            if c_c is not None:
                pipeline_preds["C: Global joint selection"][tid] = knn_search(
                    gs_emb, gs_ids, c_c, top_k=50, exclude_ids=set(sids_c))

        # D
        sids_d, sw_d = strat_d(quiz_conf, broad_c)
        seed_counts["D: Quiz-region retrieval"].append(len(sids_d))
        if sids_d:
            c_d = compute_centroid(gs_emb, gs_id_to_idx, sids_d, sw_d)
            if c_d is not None:
                pipeline_preds["D: Quiz-region retrieval"][tid] = knn_search(
                    gs_emb, gs_ids, c_d, top_k=50, exclude_ids=set(sids_d))

    # ── Results ──
    logger.info("\n" + "=" * 80)
    logger.info("  RESULTS @ k=10")
    logger.info("=" * 80)

    logger.info(f"\n{'Strategy':<40s} {'FamilyHit':>10s} {'NDCG@10':>10s} {'Recall@10':>10s} {'Hits/N':>12s} {'Seeds':>8s}")
    logger.info("  " + "-" * 90)

    oracle_m = compute_metrics(oracle_preds, gt, targets, k=10)
    logger.info(f"  {'ORACLE (self-as-seed)':<40s} {oracle_m['family_hit_rate']:>10.4f} {oracle_m['ndcg_mean']:>10.6f} {oracle_m['recall_mean']:>10.6f} {oracle_m['family_hits']:>5d}/{oracle_m['n']:<5d} {'—':>8s}")

    results = {}
    for sname in pipeline_preds:
        m = compute_metrics(pipeline_preds[sname], gt, list(pipeline_preds[sname].keys()), k=10)
        results[sname] = m
        mean_seeds = np.mean(seed_counts[sname]) if seed_counts[sname] else 0
        logger.info(f"  {sname:<40s} {m['family_hit_rate']:>10.4f} {m['ndcg_mean']:>10.6f} {m['recall_mean']:>10.6f} {m['family_hits']:>5d}/{m['n']:<5d} {mean_seeds:>6.1f}")

    # P/O ratio
    logger.info(f"\n[PIPELINE / ORACLE RATIO]")
    logger.info(f"  {'Strategy':<40s} {'Pipeline FH':>12s} {'Oracle FH':>12s} {'Ratio':>8s} {'vs A':>14s}")
    logger.info("  " + "-" * 86)
    base_ratio = results["A: Baseline (popularity per accord)"]['family_hit_rate'] / max(1e-10, oracle_m['family_hit_rate'])
    for sname in pipeline_preds:
        m = results[sname]
        ratio = m['family_hit_rate'] / max(1e-10, oracle_m['family_hit_rate'])
        imp = (ratio / max(1e-10, base_ratio) - 1) * 100
        logger.info(f"  {sname:<40s} {m['family_hit_rate']:>12.4f} {oracle_m['family_hit_rate']:>12.4f} {ratio:>7.3f} {imp:>+13.1f}%")

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("  SUMMARY")
    logger.info("=" * 80)

    best_name = max(results, key=lambda n: results[n]['family_hit_rate'])
    best_m = results[best_name]
    baseline_m = results["A: Baseline (popularity per accord)"]
    logger.info(f"\n  Baseline (A): FH={baseline_m['family_hit_rate']:.4f} NDCG={baseline_m['ndcg_mean']:.6f} P/O={baseline_m['family_hit_rate']/max(1e-10, oracle_m['family_hit_rate']):.3f}")
    logger.info(f"  Winner ({best_name}): FH={best_m['family_hit_rate']:.4f} NDCG={best_m['ndcg_mean']:.6f} P/O={best_m['family_hit_rate']/max(1e-10, oracle_m['family_hit_rate']):.3f}")
    logger.info(f"  FH improvement: {(best_m['family_hit_rate'] / max(1e-10, baseline_m['family_hit_rate']) - 1) * 100:.1f}%")
    logger.info(f"  NDCG improvement: {(best_m['ndcg_mean'] / max(1e-10, baseline_m['ndcg_mean']) - 1) * 100:.1f}%")

    for sname in pipeline_preds:
        m = results[sname]
        fh = m['family_hit_rate']
        ndcg = m['ndcg_mean']
        imp = (fh / max(1e-10, baseline_m['family_hit_rate']) - 1) * 100
        ratio = fh / max(1e-10, oracle_m['family_hit_rate'])
        logger.info(f"  {sname:<40s} FH={fh:.4f} NDCG={ndcg:.6f} vsA={imp:+.1f}% P/O={ratio:.3f}")


if __name__ == "__main__":
    main()
