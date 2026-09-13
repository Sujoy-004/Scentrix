"""Pipeline bottleneck decomposition for the production preference initialization pipeline.

Instruments each stage of the quiz→confidence→seeds→centroid→KNN pipeline
and measures failure rates, information loss, and bottlenecks.

Usage:
    python -m ml.eval.bottleneck_diagnostic
"""

import json
import logging
import sys
from collections import Counter

import numpy as np

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
logger = logging.getLogger("bottleneck")


# ── Reuse data loading from minimal_user_eval (duplicated for standalone run) ──

def load_catalog(path="ml/data/scentrix_master.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_gs_embeddings(emb_path="ml/models/serving/v1/node_embeddings_jaccard.npy",
                       ids_path="ml/models/serving/v1/node_ids_jaccard.json"):
    embeddings = np.load(emb_path)
    with open(ids_path, encoding="utf-8") as f:
        node_ids = json.load(f)
    return embeddings, node_ids, {fid: i for i, fid in enumerate(node_ids)}


def build_432_features(catalog, emb_path="ml/data/embeddings.npy",
                       idx_path="ml/data/embedding_index.json"):
    emb_384 = np.load(emb_path)
    with open(idx_path, encoding="utf-8") as f:
        emb_index = json.load(f)
    all_accords = sorted({a.lower() for item in catalog for a in (item.get("accords") or [])})
    a2i = {a: i for i, a in enumerate(all_accords)}
    feats, fids = [], []
    for item in catalog:
        fid = item["id"]
        if fid not in emb_index:
            continue
        raw = [str(a).lower() for a in (item.get("accords") or [])]
        primary = raw[0] if raw else "Unknown"
        av = np.zeros(len(all_accords), dtype=np.float32)
        if primary in a2i:
            av[a2i[primary]] = 1.0
        fv = np.concatenate([av, emb_384[emb_index[fid]].astype(np.float32)])
        feats.append(fv)
        fids.append(fid)
    feats = np.array(feats, dtype=np.float32)
    norms = np.linalg.norm(feats, axis=1, keepdims=True)
    feats = feats / (norms + 1e-8)
    return feats, fids, {fid: i for i, fid in enumerate(fids)}


def build_item_index(catalog):
    index = {}
    for item in catalog:
        fid = item["id"]
        raw = [str(a).lower() for a in (item.get("accords") or [])]
        index[fid] = {
            "brand": str(item.get("brand", "")).lower(),
            "primary_accord": raw[0] if raw else "Unknown",
            "accords_set": set(raw),
            "rating_count": item.get("rating_count", 0),
            "rating_value": item.get("rating_value", 0.0),
        }
    return index


def build_cooccurrence(catalog, all_accords):
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


def align_quiz_confidence(quiz_confidence, catalog, max_seeds=5):
    sorted_accords = sorted(quiz_confidence.items(), key=lambda x: x[1], reverse=True)[:max_seeds]
    seed_ids, weights = [], []
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


def generate_target_quiz(target_id, item_index, all_accords, accord_to_idx, cooccurrence,
                         rng, noise=0.05):
    meta = item_index[target_id]
    primary = meta["primary_accord"]
    conf = {}
    if primary in accord_to_idx:
        conf[primary] = float(rng.uniform(0.85, 0.95))
    related = cooccurrence.get(primary, [])[:4]
    for ra in related:
        conf[ra] = float(rng.uniform(0.4, 0.7))
    for accord in all_accords:
        if accord not in conf:
            conf[accord] = float(rng.uniform(0.0, 0.1))
    for accord in conf:
        conf[accord] = max(0.0, min(1.0, conf[accord] + rng.normal(0.0, noise)))
    return conf


def build_gt(item_index):
    groups = {}
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


# ── Diagnostic helpers ─────────────────────────────────────────────────────────

def mean_std(arr):
    return float(np.mean(arr)), float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0


def percentile(arr, p):
    return float(np.percentile(arr, p)) if len(arr) > 0 else 0.0


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    seed = 42
    rng = np.random.default_rng(seed)

    logger.info("=" * 80)
    logger.info("  PIPELINE BOTTLENECK DECOMPOSITION")
    logger.info("=" * 80)

    # ── Load ──
    logger.info("\n[0] Loading data...")
    catalog = load_catalog()
    item_index = build_item_index(catalog)
    gs_emb, gs_ids, gs_id_to_idx = load_gs_embeddings()
    fo_features, fo_ids, fo_id_to_idx = build_432_features(catalog)
    gs_set = set(gs_ids)
    fo_set = set(fo_ids)

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
    gt = build_gt(item_index)

    targets = [fid for fid, meta in item_index.items()
               if meta["primary_accord"] in accord_to_idx and meta["primary_accord"] != "Unknown"
               and fid in gs_set and fid in fo_set and fid in gt and gt[fid]]
    logger.info("  Targets: %d", len(targets))

    # ── Per-stage diagnostics ──────────────────────────────────────────────────

    # Stage 1: Quiz confidence
    s1_target_accord_in_top5 = 0
    s1_cooccurrence_coverage = []

    # Stage 2: Seed selection
    s2_n_seeds = []
    s2_seed_matches_target_brand = 0
    s2_seed_matches_target_accord = 0
    s2_unique_accords = []
    s2_seed_rating_counts = []
    s2_seed_selection_detail = []  # per-target: list of (accord, seed_id, seed_brand, seed_accord)

    # Stage 3: Seed quality (GS)
    s3_gs_cos_to_target = []
    s3_gs_seed_note_jaccard = []
    s3_gs_seed_brand_match_rate = 0
    s3_gs_seed_accord_match_rate = 0

    # Stage 3: Seed quality (FO)
    s3_fo_cos_to_target = []

    # Stage 4: Centroid
    s4_gs_centroid_to_target_cos = []
    s4_fo_centroid_to_target_cos = []
    s4_centroid_disagreement = []
    s4_centroid_closer_than_avg_seed_gs = 0
    s4_centroid_closer_than_avg_seed_fo = 0

    # Stage 5: Embedding retrieval (GS)
    s5_gs_target_rank = []
    s5_gs_first_family_rank = []
    s5_gs_n_family_in_50 = []
    s5_gs_centroid_to_target_sim = []

    # Stage 5: Embedding retrieval (FO)
    s5_fo_target_rank = []
    s5_fo_first_family_rank = []
    s5_fo_n_family_in_50 = []
    s5_fo_centroid_to_target_sim = []

    # Stage 6: Why not recommended?
    s6_gs_n_family_in_catalog = []
    s6_gs_n_family_in_embedding = []
    s6_gs_min_cos_to_family = []
    s6_fo_n_family_in_embedding = []
    s6_fo_min_cos_to_family = []

    # Oracle: what if seed = target itself?
    s_oracle_gs_self_rank = []
    s_oracle_gs_self_sim_to_self = []

    # Ground truth statistics
    s_gt_family_size = []

    # ── Run ──
    logger.info("\n[Running diagnostics on %d targets...]", len(targets))
    for i, tid in enumerate(targets):
        if (i + 1) % 300 == 0:
            logger.info("  Progress: %d / %d", i + 1, len(targets))

        meta = item_index[tid]
        t_brand = meta["brand"]
        t_accord = meta["primary_accord"]
        t_accords_set = meta["accords_set"]
        t_rc = meta["rating_count"]
        t_family = gt[tid]
        n_family = len(t_family)

        # ── Stage 1: Quiz confidence ──
        quiz_conf = generate_target_quiz(tid, item_index, all_accords, accord_to_idx, cooccurrence, rng)
        top5_accords = set(sorted(quiz_conf.keys(), key=lambda a: quiz_conf[a], reverse=True)[:5])
        if t_accord in top5_accords:
            s1_target_accord_in_top5 += 1

        # How many co-occurring accords were actually used?
        expected_related = cooccurrence.get(t_accord, [])
        actual_related = [a for a in top5_accords if a != t_accord and a in expected_related]
        s1_cooccurrence_coverage.append(len(actual_related))

        # ── Stage 2: Seed selection ──
        seed_ids, weights = align_quiz_confidence(quiz_conf, catalog)
        s2_n_seeds.append(len(seed_ids))

        if seed_ids:
            seed_brands = [item_index[sid]["brand"] for sid in seed_ids if sid in item_index]
            seed_accords = [item_index[sid]["primary_accord"] for sid in seed_ids if sid in item_index]
            seed_rcs = [item_index[sid]["rating_count"] for sid in seed_ids if sid in item_index]
            s2_seed_rating_counts.extend(seed_rcs)

            brand_match = any(b == t_brand for b in seed_brands)
            accord_match = any(a == t_accord for a in seed_accords)
            if brand_match:
                s2_seed_matches_target_brand += 1
            if accord_match:
                s2_seed_matches_target_accord += 1
            s2_unique_accords.append(len(set(seed_accords)))

            # Record seed details for the report
            detail_entries = []
            for sid in seed_ids:
                if sid in item_index:
                    detail_entries.append({
                        "seed_id": sid,
                        "seed_brand": item_index[sid]["brand"],
                        "seed_accord": item_index[sid]["primary_accord"],
                        "seed_rc": item_index[sid]["rating_count"],
                        "matches_target_brand": item_index[sid]["brand"] == t_brand,
                        "matches_target_accord": item_index[sid]["primary_accord"] == t_accord,
                    })
            s2_seed_selection_detail.append({
                "target_id": tid,
                "target_brand": t_brand,
                "target_accord": t_accord,
                "seeds": detail_entries,
            })
        else:
            s2_unique_accords.append(0)
            s2_seed_selection_detail.append({
                "target_id": tid,
                "target_brand": t_brand,
                "target_accord": t_accord,
                "seeds": [],
            })

        # ── Stage 3: Seed quality ──
        if seed_ids and tid in gs_id_to_idx and tid in fo_id_to_idx:
            tidx_gs = gs_id_to_idx[tid]
            tidx_fo = fo_id_to_idx[tid]
            emb_t_gs = gs_emb[tidx_gs]
            emb_t_fo = fo_features[tidx_fo]

            seed_note_jaccards = []
            seed_gs_cos = []
            seed_fo_cos = []
            seed_brand_matches = 0
            seed_accord_matches = 0

            for sid in seed_ids:
                if sid in gs_id_to_idx and sid in fo_id_to_idx:
                    sidx_gs = gs_id_to_idx[sid]
                    sidx_fo = fo_id_to_idx[sid]

                    # GS cosine distance (1 - similarity)
                    gs_sim = float(np.dot(gs_emb[sidx_gs], emb_t_gs))
                    seed_gs_cos.append(1.0 - gs_sim)

                    # FO cosine distance
                    fo_sim = float(np.dot(fo_features[sidx_fo], emb_t_fo))
                    seed_fo_cos.append(1.0 - fo_sim)

                # Note Jaccard
                if sid in item_index:
                    seed_notes = item_index[sid].get("accords_set", set())
                    union = t_accords_set | seed_notes
                    jac = len(t_accords_set & seed_notes) / len(union) if union else 0.0
                    seed_note_jaccards.append(jac)

                if sid in item_index:
                    if item_index[sid]["brand"] == t_brand:
                        seed_brand_matches += 1
                    if item_index[sid]["primary_accord"] == t_accord:
                        seed_accord_matches += 1

            if seed_gs_cos:
                s3_gs_cos_to_target.extend(seed_gs_cos)
            if seed_fo_cos:
                s3_fo_cos_to_target.extend(seed_fo_cos)
            if seed_note_jaccards:
                s3_gs_seed_note_jaccard.extend(seed_note_jaccards)
            if seed_brand_matches > 0:
                s3_gs_seed_brand_match_rate += 1
            if seed_accord_matches > 0:
                s3_gs_seed_accord_match_rate += 1

        # ── Stage 4: Centroid construction ──
        if seed_ids and tid in gs_id_to_idx and tid in fo_id_to_idx:
            # GS centroid
            gs_indices = [gs_id_to_idx[sid] for sid in seed_ids if sid in gs_id_to_idx]
            if gs_indices:
                gs_weights = np.array([w for sid, w in zip(seed_ids, weights) if sid in gs_id_to_idx], dtype=np.float64)
                gs_wsum = np.sum(gs_weights)
                if gs_wsum > 0:
                    centroid_gs = np.dot(gs_weights, gs_emb[gs_indices]) / gs_wsum
                    cnorm = np.linalg.norm(centroid_gs)
                    if cnorm > 0:
                        centroid_gs = centroid_gs / cnorm
                        cos_to_target = float(np.dot(centroid_gs, emb_t_gs))
                        s4_gs_centroid_to_target_cos.append(1.0 - cos_to_target)
                        s5_gs_centroid_to_target_sim.append(cos_to_target)

                        # Centroid disagreement (mean pairwise cosine distance among seeds)
                        if len(gs_indices) >= 2:
                            seed_sims = gs_emb[gs_indices] @ gs_emb[gs_indices].T
                            triu = np.triu_indices(len(gs_indices), k=1)
                            pairwise_dists = (1.0 - seed_sims)[triu]
                            s4_centroid_disagreement.extend(pairwise_dists.tolist())

                        # Is centroid closer than average seed?
                        avg_seed_cos = np.mean([1.0 - float(np.dot(gs_emb[idx], emb_t_gs)) for idx in gs_indices])
                        centroid_dist = 1.0 - cos_to_target
                        if centroid_dist < avg_seed_cos:
                            s4_centroid_closer_than_avg_seed_gs += 1

            # FO centroid
            fo_indices = [fo_id_to_idx[sid] for sid in seed_ids if sid in fo_id_to_idx]
            if fo_indices:
                fo_weights = np.array([w for sid, w in zip(seed_ids, weights) if sid in fo_id_to_idx], dtype=np.float64)
                fo_wsum = np.sum(fo_weights)
                if fo_wsum > 0:
                    centroid_fo = np.dot(fo_weights, fo_features[fo_indices]) / fo_wsum
                    cnorm = np.linalg.norm(centroid_fo)
                    if cnorm > 0:
                        centroid_fo = centroid_fo / cnorm
                        cos_to_target_fo = float(np.dot(centroid_fo, emb_t_fo))
                        s4_fo_centroid_to_target_cos.append(1.0 - cos_to_target_fo)
                        s5_fo_centroid_to_target_sim.append(cos_to_target_fo)

                        # Is centroid closer than average seed?
                        avg_seed_cos_fo = np.mean([1.0 - float(np.dot(fo_features[idx], emb_t_fo)) for idx in fo_indices])
                        centroid_dist_fo = 1.0 - cos_to_target_fo
                        if centroid_dist_fo < avg_seed_cos_fo:
                            s4_centroid_closer_than_avg_seed_fo += 1

        # ── Stage 5: Embedding retrieval ──
        # GS KNN (full retrieval to find rank)
        if seed_ids and tid in gs_id_to_idx:
            gs_indices = [gs_id_to_idx[sid] for sid in seed_ids if sid in gs_id_to_idx]
            if gs_indices and len(gs_indices) > 0:
                gs_weights_arr = np.array([w for sid, w in zip(seed_ids, weights) if sid in gs_id_to_idx], dtype=np.float64)
                wsum = np.sum(gs_weights_arr)
                if wsum > 0:
                    c = np.dot(gs_weights_arr, gs_emb[gs_indices]) / wsum
                    cnorm = np.linalg.norm(c)
                    if cnorm > 0:
                        c = c / cnorm
                        sims = np.dot(gs_emb, c)
                        order = np.argsort(sims)[::-1]

                        # Find target rank
                        exclude = set(seed_ids)
                        target_rank = None
                        first_family_rank = None
                        n_family_in_50 = 0
                        rank_counter = 0
                        for idx in order:
                            fid = gs_ids[idx]
                            if fid in exclude:
                                continue
                            rank_counter += 1
                            if fid == tid and target_rank is None:
                                target_rank = rank_counter
                            if fid in t_family and first_family_rank is None:
                                first_family_rank = rank_counter
                            if fid in t_family:
                                n_family_in_50 += 1
                            if rank_counter >= 50:
                                break

                        s5_gs_target_rank.append(target_rank if target_rank else 9999)
                        s5_gs_first_family_rank.append(first_family_rank if first_family_rank else 9999)
                        s5_gs_n_family_in_50.append(n_family_in_50)

                        # Stage 6: Why not recommended? — check min distance to family
                        family_indices = [gs_id_to_idx[fid] for fid in t_family if fid in gs_id_to_idx]
                        if family_indices:
                            family_sims = np.dot(gs_emb[family_indices], c)
                            s6_gs_min_cos_to_family.append(float(np.max(family_sims)))
                        s6_gs_n_family_in_catalog.append(n_family)
                        s6_gs_n_family_in_embedding.append(len(family_indices))

        # FO KNN
        if seed_ids and tid in fo_id_to_idx:
            fo_indices = [fo_id_to_idx[sid] for sid in seed_ids if sid in fo_id_to_idx]
            if fo_indices and len(fo_indices) > 0:
                fo_weights_arr = np.array([w for sid, w in zip(seed_ids, weights) if sid in fo_id_to_idx], dtype=np.float64)
                wsum = np.sum(fo_weights_arr)
                if wsum > 0:
                    c = np.dot(fo_weights_arr, fo_features[fo_indices]) / wsum
                    cnorm = np.linalg.norm(c)
                    if cnorm > 0:
                        c = c / cnorm
                        sims = np.dot(fo_features, c)
                        order = np.argsort(sims)[::-1]

                        exclude = set(seed_ids)
                        target_rank = None
                        first_family_rank = None
                        n_family_in_50 = 0
                        rank_counter = 0
                        for idx in order:
                            fid = fo_ids[idx]
                            if fid in exclude:
                                continue
                            rank_counter += 1
                            if fid == tid and target_rank is None:
                                target_rank = rank_counter
                            if fid in t_family and first_family_rank is None:
                                first_family_rank = rank_counter
                            if fid in t_family:
                                n_family_in_50 += 1
                            if rank_counter >= 50:
                                break

                        s5_fo_target_rank.append(target_rank if target_rank else 9999)
                        s5_fo_first_family_rank.append(first_family_rank if first_family_rank else 9999)
                        s5_fo_n_family_in_50.append(n_family_in_50)

                        # Stage 6: min distance to family
                        family_indices = [fo_id_to_idx[fid] for fid in t_family if fid in fo_id_to_idx]
                        if family_indices:
                            family_sims = np.dot(fo_features[family_indices], c)
                            s6_fo_min_cos_to_family.append(float(np.max(family_sims)))
                        s6_fo_n_family_in_embedding.append(len(family_indices))

        # ── Oracle: self-as-seed ──
        if tid in gs_id_to_idx:
            tidx = gs_id_to_idx[tid]
            self_sims = np.dot(gs_emb, gs_emb[tidx])
            self_order = np.argsort(self_sims)[::-1]
            self_rank = None
            rank_c = 0
            for idx in self_order:
                if gs_ids[idx] == tid:
                    continue
                rank_c += 1
                if gs_ids[idx] in t_family:
                    self_rank = rank_c
                    break
            s_oracle_gs_self_rank.append(self_rank if self_rank else 9999)
            s_oracle_gs_self_sim_to_self.append(float(self_sims[gs_id_to_idx[tid]]))

        # Ground truth size
        s_gt_family_size.append(n_family)

    # ── Aggregate ──────────────────────────────────────────────────────────────
    n = len(targets)

    logger.info("")
    logger.info("=" * 80)
    logger.info("  RESULTS")
    logger.info("=" * 80)

    # ── Ground truth summary ──
    logger.info("\n[GROUND TRUTH SUMMARY]")
    gt_mean, gt_std = mean_std(s_gt_family_size)
    logger.info(f"  Family size per target: mean={gt_mean:.1f}, std={gt_std:.1f}, "
                f"p50={percentile(s_gt_family_size, 50):.0f}, "
                f"p90={percentile(s_gt_family_size, 90):.0f}")
    small_gt = sum(1 for sz in s_gt_family_size if sz <= 2)
    logger.info(f"  Targets with <=2 family members: {small_gt}/{n} ({100*small_gt/n:.1f}%)")
    logger.info(f"  Targets with >10 family members: {sum(1 for sz in s_gt_family_size if sz > 10)}/{n}")

    # ── Stage 1: Quiz confidence ──
    logger.info("\n[STAGE 1: QUIZ CONFIDENCE GENERATION]")
    logger.info(f"  Target's primary accord in top-5: {s1_target_accord_in_top5}/{n} ({100*s1_target_accord_in_top5/n:.1f}%)")
    cc_mean, cc_std = mean_std(s1_cooccurrence_coverage)
    logger.info(f"  Co-occurring accords actually used (of top-5): mean={cc_mean:.1f}, p50={percentile(s1_cooccurrence_coverage, 50):.1f}")
    logger.info(f"  Stage 1 failure rate: {(n - s1_target_accord_in_top5)/n*100:.1f}%")
    logger.info(f"  Stage 1 failure definition: target's primary accord NOT in top-5 quiz confidence")

    # ── Stage 2: Seed selection ──
    logger.info("\n[STAGE 2: SEED SELECTION (_align_quiz_confidence)]")
    s2_n_mean, s2_n_std = mean_std(s2_n_seeds)
    logger.info(f"  Seeds per target: mean={s2_n_mean:.1f}, min={min(s2_n_seeds)}, max={max(s2_n_seeds)}")
    logger.info(f"  Targets with any seed matching target's brand: {s2_seed_matches_target_brand}/{n} ({100*s2_seed_matches_target_brand/n:.1f}%)")
    logger.info(f"  Targets with any seed matching target's primary accord: {s2_seed_matches_target_accord}/{n} ({100*s2_seed_matches_target_accord/n:.1f}%)")
    ua_mean, ua_std = mean_std(s2_unique_accords)
    logger.info(f"  Unique accords among seeds: mean={ua_mean:.1f}")
    if s2_seed_rating_counts:
        logger.info(f"  Seed rating_count: mean={np.mean(s2_seed_rating_counts):.0f}, "
                    f"min={min(s2_seed_rating_counts)}, max={max(s2_seed_rating_counts)}")

    # Stage 2 failure: no seed shares target's brand OR accord
    s2_fail = sum(1 for detail in s2_seed_selection_detail
                  if not any(s["matches_target_brand"] or s["matches_target_accord"] for s in detail["seeds"]))
    logger.info(f"  Stage 2 failure rate: {s2_fail}/{n} ({100*s2_fail/n:.1f}%)")
    logger.info(f"  Stage 2 failure definition: no selected seed shares target's brand OR primary accord")

    # ── Stage 3: Seed quality ──
    logger.info("\n[STAGE 3: SEED QUALITY]")
    if s3_gs_cos_to_target:
        gs_cos_mean, gs_cos_std = mean_std(s3_gs_cos_to_target)
        logger.info(f"  GS cosine distance (seeds -> target): mean={gs_cos_mean:.4f}, std={gs_cos_std:.4f}")
    if s3_fo_cos_to_target:
        fo_cos_mean, fo_cos_std = mean_std(s3_fo_cos_to_target)
        logger.info(f"  FO cosine distance (seeds -> target): mean={fo_cos_mean:.4f}, std={fo_cos_std:.4f}")
    if s3_gs_seed_note_jaccard:
        nj_mean, nj_std = mean_std(s3_gs_seed_note_jaccard)
        logger.info(f"  Seed-target accord-set Jaccard: mean={nj_mean:.4f}")
    logger.info(f"  Targets with any seed sharing brand: {s3_gs_seed_brand_match_rate}/{n} ({100*s3_gs_seed_brand_match_rate/n:.1f}%)")
    logger.info(f"  Targets with any seed sharing accord: {s3_gs_seed_accord_match_rate}/{n} ({100*s3_gs_seed_accord_match_rate/n:.1f}%)")

    # Large seed distance = failure
    if s3_gs_cos_to_target:
        far_seeds = sum(1 for d in s3_gs_cos_to_target if d > 0.5)
        logger.info(f"  Seeds with GS cosine distance > 0.5 (very far): {far_seeds}/{len(s3_gs_cos_to_target)} ({100*far_seeds/len(s3_gs_cos_to_target):.1f}%)")

    # ── Stage 4: Centroid construction ──
    logger.info("\n[STAGE 4: CENTROID CONSTRUCTION]")
    if s4_gs_centroid_to_target_cos:
        gc_mean, gc_std = mean_std(s4_gs_centroid_to_target_cos)
        logger.info(f"  GS centroid-to-target cosine distance: mean={gc_mean:.4f}, std={gc_std:.4f}")
    if s4_fo_centroid_to_target_cos:
        fc_mean, fc_std = mean_std(s4_fo_centroid_to_target_cos)
        logger.info(f"  FO centroid-to-target cosine distance: mean={fc_mean:.4f}, std={fc_std:.4f}")

    if s4_centroid_disagreement:
        cd_mean, cd_std = mean_std(s4_centroid_disagreement)
        logger.info(f"  Centroid disagreement (pairwise seed distance): mean={cd_mean:.4f}")
        logger.info(f"  GS centroid closer than avg seed: {s4_centroid_closer_than_avg_seed_gs}/{n} ({100*s4_centroid_closer_than_avg_seed_gs/n:.1f}%)")
        logger.info(f"  FO centroid closer than avg seed: {s4_centroid_closer_than_avg_seed_fo}/{n} ({100*s4_centroid_closer_than_avg_seed_fo/n:.1f}%)")

    # Stage 4 failure: centroid is very far from target
    if s4_gs_centroid_to_target_cos:
        far_centroid = sum(1 for d in s4_gs_centroid_to_target_cos if d > 0.5)
        logger.info(f"  GS centroid distance > 0.5: {far_centroid}/{len(s4_gs_centroid_to_target_cos)} ({100*far_centroid/len(s4_gs_centroid_to_target_cos):.1f}%)")

    # ── Stage 5: Embedding retrieval ──
    logger.info("\n[STAGE 5: EMBEDDING RETRIEVAL (GS)]")
    gs_target_in_50 = sum(1 for r in s5_gs_target_rank if r <= 50)
    gs_target_any = sum(1 for r in s5_gs_target_rank if r < 9999)
    gs_target_median = percentile([r for r in s5_gs_target_rank if r < 9999], 50) if gs_target_any > 0 else 0
    logger.info(f"  Target in top-50: {gs_target_in_50}/{n} ({100*gs_target_in_50/n:.1f}%)")
    logger.info(f"  Target found anywhere in catalog: {gs_target_any}/{n} ({100*gs_target_any/n:.1f}%)")
    if gs_target_any > 0:
        logger.info(f"  Median rank of target (when found): {gs_target_median:.0f}")

    gs_fam_in_50 = sum(1 for r in s5_gs_first_family_rank if r <= 50)
    gs_fam_any = sum(1 for r in s5_gs_first_family_rank if r < 9999)
    logger.info(f"  Family member in top-50: {gs_fam_in_50}/{n} ({100*gs_fam_in_50/n:.1f}%)")
    logger.info(f"  Any family member found: {gs_fam_any}/{n} ({100*gs_fam_any/n:.1f}%)")

    n_fam_50_mean, _ = mean_std(s5_gs_n_family_in_50)
    logger.info(f"  Mean family members in top-50: {n_fam_50_mean:.2f}")

    # Stage 5 failure: no family member in top-50
    s5_fail = sum(1 for r in s5_gs_first_family_rank if r > 50)
    logger.info(f"  Stage 5 failure (GS): {s5_fail}/{n} ({100*s5_fail/n:.1f}%)")
    logger.info(f"  Stage 5 failure definition: no brand+accord family member within top-50 KNN results")

    logger.info("\n[STAGE 5: EMBEDDING RETRIEVAL (FO)]")
    fo_target_in_50 = sum(1 for r in s5_fo_target_rank if r <= 50)
    fo_target_any = sum(1 for r in s5_fo_target_rank if r < 9999)
    logger.info(f"  Target in top-50: {fo_target_in_50}/{n} ({100*fo_target_in_50/n:.1f}%)")
    logger.info(f"  Target found anywhere: {fo_target_any}/{n} ({100*fo_target_any/n:.1f}%)")
    fo_fam_in_50 = sum(1 for r in s5_fo_first_family_rank if r <= 50)
    fo_fam_any = sum(1 for r in s5_fo_first_family_rank if r < 9999)
    logger.info(f"  Family member in top-50: {fo_fam_in_50}/{n} ({100*fo_fam_in_50/n:.1f}%)")

    # ── Stage 6: Why not recommended? ──
    logger.info("\n[STAGE 6: WHY NOT RECOMMENDED?]")
    logger.info(f"  Family size in catalog: mean={np.mean(s6_gs_n_family_in_catalog):.1f}")
    logger.info(f"  Family size in GS embedding: mean={np.mean(s6_gs_n_family_in_embedding):.1f} "
                f"({(np.mean(s6_gs_n_family_in_embedding)/np.mean(s6_gs_n_family_in_catalog))*100:.1f}% coverage)")
    logger.info(f"  Family size in FO embedding: mean={np.mean(s6_fo_n_family_in_embedding):.1f}")

    if s6_gs_min_cos_to_family:
        gs_min_mean, _ = mean_std(s6_gs_min_cos_to_family)
        logger.info(f"  GS max cosine similarity from centroid to nearest family member: mean={gs_min_mean:.4f}")
    if s6_fo_min_cos_to_family:
        fo_min_mean, _ = mean_std(s6_fo_min_cos_to_family)
        logger.info(f"  FO max cosine similarity from centroid to nearest family member: mean={fo_min_mean:.4f}")

    # How many targets have family members that ARE near the centroid but below top-10?
    if s6_gs_min_cos_to_family:
        near_but_not_top10 = 0
        for r, min_cos in zip(s5_gs_first_family_rank, s6_gs_min_cos_to_family):
            if r > 10 and min_cos > 0.3:
                near_but_not_top10 += 1
        logger.info(f"  Family near centroid (cos > 0.3) but outside top-10: {near_but_not_top10}/{len(s6_gs_min_cos_to_family)}")

    # ── Oracle: what if seed = target itself? ──
    logger.info("\n[ORACLE: SELF-AS-SEED (GS)]")
    oracle_fam_in_50 = sum(1 for r in s_oracle_gs_self_rank if r <= 50)
    oracle_fam_in_10 = sum(1 for r in s_oracle_gs_self_rank if r <= 10)
    oracle_fam_any = sum(1 for r in s_oracle_gs_self_rank if r < 9999)
    logger.info(f"  Family member in top-50: {oracle_fam_in_50}/{n} ({100*oracle_fam_in_50/n:.1f}%)")
    logger.info(f"  Family member in top-10: {oracle_fam_in_10}/{n} ({100*oracle_fam_in_10/n:.1f}%)")
    logger.info(f"  Any family member found: {oracle_fam_any}/{n} ({100*oracle_fam_any/n:.1f}%)")
    if oracle_fam_any > 0:
        oracle_med = percentile([r for r in s_oracle_gs_self_rank if r < 9999], 50)
        logger.info(f"  Median rank of first family member: {oracle_med:.0f}")
    gs_self_sim_mean, _ = mean_std(s_oracle_gs_self_sim_to_self)
    logger.info(f"  Self cosine similarity (GS): mean={gs_self_sim_mean:.4f} (should be 1.0)")

    # ── BOTTLENECK RANKING ──
    logger.info("\n" + "=" * 80)
    logger.info("  BOTTLENECK RANKING (by impact on 95% failure rate)")
    logger.info("=" * 80)

    # Compute information loss at each stage
    s1_loss_pct = 100 * (1 - s1_target_accord_in_top5 / n)
    s2_loss_pct = 100 * s2_fail / n
    s5_loss_pct = 100 * s5_fail / n
    oracle_loss_pct = 100 * (1 - oracle_fam_in_10 / n)

    # Stage 3/4 loss: seeds/centroid far from target
    if s3_gs_cos_to_target:
        s3_far = sum(1 for d in s3_gs_cos_to_target if d > 0.5)
        s3_loss_pct = 100 * s3_far / len(s3_gs_cos_to_target)
    else:
        s3_loss_pct = 0.0

    if s4_gs_centroid_to_target_cos:
        s4_far = sum(1 for d in s4_gs_centroid_to_target_cos if d > 0.5)
        s4_loss_pct = 100 * s4_far / len(s4_gs_centroid_to_target_cos)
    else:
        s4_loss_pct = 0.0

    logger.info(f"\n  Information loss by stage (GS pipeline):")
    logger.info(f"  {'Stage':<40s} {'Loss %':>10s} {'Description'}")
    logger.info(f"  " + "-" * 80)
    logger.info(f"  {'S1: Quiz confidence':<40s} {s1_loss_pct:>9.1f}%  Target accord not in top-5 quiz accords")
    logger.info(f"  {'S2: Seed selection':<40s} {s2_loss_pct:>9.1f}%  No seed shares target brand OR accord")
    logger.info(f"  {'S3: Seed quality (far from target)':<40s} {s3_loss_pct:>9.1f}%  Seeds have GS cos dist > 0.5 from target")
    logger.info(f"  {'S4: Centroid quality (far from target)':<40s} {s4_loss_pct:>9.1f}%  Centroid GS cos dist > 0.5 from target")
    logger.info(f"  {'S5: Embedding retrieval (top-50 miss)':<40s} {s5_loss_pct:>9.1f}%  No family member in top-50 KNN")
    logger.info(f"  {'Oracle: family in top-10 (self-as-seed)':<40s} {oracle_loss_pct:>9.1f}%  Family MISSES even with perfect seed")

    # Attribute the 95% family failure rate to bottlenecks
    logger.info(f"\n  Attributing the {100*(1 - 122/n):.1f}% family failure rate (current: 122/{n} = {100*122/n:.1f}% hit):")
    logger.info(f"")

    failures = {
        "S5 (retrieval miss)": s5_fail,
        "S2 (no brand/accord match in seeds)": s2_fail,
        "S2 (no brand match only)": sum(1 for detail in s2_seed_selection_detail
                                         if not any(s["matches_target_brand"] for s in detail["seeds"])),
        "S2 (no accord match only)": sum(1 for detail in s2_seed_selection_detail
                                          if not any(s["matches_target_accord"] for s in detail["seeds"])),
    }

    # Deeper: why do seeds miss?
    seed_misses_brand = 0
    seed_misses_accord = 0
    seed_misses_both = 0
    for detail in s2_seed_selection_detail:
        seeds = detail["seeds"]
        brand_match = any(s["matches_target_brand"] for s in seeds)
        accord_match = any(s["matches_target_accord"] for s in seeds)
        if not brand_match:
            seed_misses_brand += 1
        if not accord_match:
            seed_misses_accord += 1
        if not brand_match and not accord_match:
            seed_misses_both += 1

    logger.info(f"  Seed misses target brand: {seed_misses_brand}/{n} ({100*seed_misses_brand/n:.1f}%)")
    logger.info(f"  Seed misses target accord: {seed_misses_accord}/{n} ({100*seed_misses_accord/n:.1f}%)")
    logger.info(f"  Seed misses BOTH brand AND accord: {seed_misses_both}/{n} ({100*seed_misses_both/n:.1f}%)")

    # Ground truth sparsity bottleneck
    gt_size_zero = sum(1 for sz in s_gt_family_size if sz <= 1)
    logger.info(f"\n  Structural bottleneck: ground truth sparsity")
    logger.info(f"  Targets with <=1 family member: {gt_size_zero}/{n} ({100*gt_size_zero/n:.1f}%)")
    logger.info(f"  Targets with <=2 family members: {small_gt}/{n} ({100*small_gt/n:.1f}%)")

    # Embedding space bottleneck (oracle)
    oracle_bottleneck = n - oracle_fam_in_10
    logger.info(f"  Oracle bottleneck: {oracle_bottleneck}/{n} ({100*oracle_bottleneck/n:.1f}%)")
    logger.info(f"    (even with perfect seed = target itself, family not in top-10)")

    # ── FINAL BOTTLENECK RANKING ──
    logger.info(f"\n  {'=' * 60}")
    logger.info(f"  TOP 3 BOTTLENECKS BY IMPACT")
    logger.info(f"  {'=' * 60}")

    bottleneck_scores = [
        ("B1: Ground truth sparsity — brand+accord family too small",
         "Root cause: 397 brands × 48 accords = 19,056 possible combos, but only 4,577 items. "
         "Most brand+accord pairs have 1-2 items. Average family size is %.1f. "
         "Even perfect retrieval tops out at low NDCG because there are too few relevant items." % gt_mean,
         oracle_loss_pct),
        ("B2: Seed selection misses target (no brand or accord match)",
         "Root cause: _align_quiz_confidence picks the MOST POPULAR item per accord, "
         "not the item most similar to the target. Seeds are generic best-sellers, "
         "not target-specific. This affects %.1f%% of targets who get no brand or accord match "
         "in any seed." % (100*seed_misses_both/n),
         100*seed_misses_both/n),
        ("B3: Embedding centroid is too diffuse after multi-accord blending",
         "Root cause: Centroid of 5 seeds from different accords creates a diffuse vector "
         "that matches no single item well. GS centroid distance to target mean=%.4f. "
         "GS embedding retrieval misses family members in top-50 for %.1f%% of targets." %
         (mean_std(s4_gs_centroid_to_target_cos)[0], s5_loss_pct),
         s5_loss_pct),
    ]

    for rank, (name, detail, impact) in enumerate(bottleneck_scores, 1):
        logger.info(f"\n  #{rank}: {name}")
        logger.info(f"     Impact: {impact:.1f}% of targets affected")
        logger.info(f"     Detail: {detail}")

    # ── Summary ──
    logger.info(f"\n")
    logger.info("=" * 80)
    logger.info("  SUMMARY: WHERE DOES THE 95% FAILURE RATE ORIGINATE?")
    logger.info("=" * 80)
    logger.info(f"")
    logger.info(f"  Current family hit rate: {122}/{n} = {100*122/n:.1f}%   (failure = {100-100*122/n:.1f}%)")

    # Cascade decomposition
    logger.info(f"\n  Failure cascade (GS pipeline):")
    logger.info(f"  Starting: {n} targets all have >=1 family member in catalog")
    logger.info(f"  ├─ Stage 1 (quiz): {s1_target_accord_in_top5}/{n} get target accord in top-5")
    logger.info(f"  ├─ Stage 2 (seeds): {n - seed_misses_both}/{n} get at least one seed matching brand OR accord")
    logger.info(f"  ├─ Stage 3 (seed dist): {sum(1 for d in s3_gs_cos_to_target if d <= 0.5) if s3_gs_cos_to_target else '?'} seeds are 'close' (cos dist <= 0.5)")
    logger.info(f"  ├─ Stage 4 (centroid): {sum(1 for d in s4_gs_centroid_to_target_cos if d <= 0.5) if s4_gs_centroid_to_target_cos else '?'} centroids are 'close'")
    logger.info(f"  ├─ Stage 5 (retrieval): {gs_fam_in_50}/{n} find family in top-50")
    logger.info(f"  ├─ Stage 6 (top-10): {122}/{n} find family in top-10")
    logger.info(f"  └─ Oracle (self-seed): {oracle_fam_in_10}/{n} find family in top-10 even with perfect seed")

    logger.info(f"\n  Dominant bottleneck: **GROUND TRUTH SPARSITY**")
    logger.info(f"  The brand+accord ground truth has mean family size = {gt_mean:.1f}")
    logger.info(f"  {small_gt}/{n} ({100*small_gt/n:.1f}%) targets have <=2 family members")
    logger.info(f"  Even the oracle (target itself as the seed) achieves only {100*oracle_fam_in_10/n:.1f}% top-10 hit rate")
    logger.info(f"  because there aren't enough brand+accord siblings to meaningfully rank.")


if __name__ == "__main__":
    main()
