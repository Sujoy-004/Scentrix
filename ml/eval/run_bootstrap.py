"""Bootstrap significance: GraphSAGE-Jaccard vs three baselines per-item NDCG@10."""

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ml.eval.config import EvalConfig
from ml.eval.split import ColdStartSplitter, LeaveColdOutStrategy
from ml.eval.models.graph_builder import build_jaccard_graph, build_similarity_graph
from ml.eval.models.graphsage_wrapper import GraphSAGEWrapper
from ml.eval.models.popularity import PopularityBaseline
from ml.eval.models.random_baseline import RandomBaseline
from ml.eval.significance import BootstrapSignificance

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("bootstrap_test")


def per_item_ndcg(
    predictions: dict[str, list[tuple[str, float]]],
    ground_truth: dict[str, set[str]],
    k: int = 10,
) -> dict[str, float]:
    """Compute per-item NDCG@10 scores."""
    scores = {}
    for cid in predictions:
        if cid not in ground_truth or not ground_truth[cid]:
            continue
        ranked = predictions.get(cid, [])
        all_scores = {rec_id: score for rec_id, score in ranked}
        relevant = ground_truth.get(cid, set())
        ranked_list = sorted(all_scores.items(), key=lambda x: -x[1])
        ndcg = 0.0
        for rank, (item_id, _) in enumerate(ranked_list, start=1):
            if item_id in relevant and rank <= k:
                ndcg = 1.0 / np.log2(rank + 1)
                break
        scores[cid] = ndcg
    return scores


def main():
    config = EvalConfig()
    config.graphsage_knn_k = 10
    config.graphsage_similarity_threshold = 0.5
    config.graphsage_epochs = 100
    config.seed = 42

    # Load & split
    data_path = Path(config.data_path)
    with open(data_path, "r") as f:
        raw_data = json.load(f)

    records = []
    for item in raw_data:
        accords = item.get("accords", [])
        records.append({
            "fragrance_id": item["id"],
            "primary_accord": accords[0] if accords else "Unknown",
        })
    df = pd.DataFrame(records)

    strategy = LeaveColdOutStrategy(seed=config.seed)
    splitter = ColdStartSplitter(strategy=strategy)
    split_result = splitter.split(df, config)

    cold_ids = split_result.cold_items
    warm_ids = split_result.warm_items

    # Ground truth
    item_map = {}
    for item in raw_data:
        fid = item.get("id", "")
        top = {str(n).lower() for n in (item.get("top_notes") or []) if n}
        mid = {str(n).lower() for n in (item.get("middle_notes") or []) if n}
        base = {str(n).lower() for n in (item.get("base_notes") or []) if n}
        raw_accords = [str(a).lower() for a in (item.get("accords") or []) if a]
        item_map[fid] = {
            "all_notes": top | mid | base,
            "primary_accord": raw_accords[0] if raw_accords else "Unknown",
        }

    ground_truth = {}
    for cold_id in cold_ids:
        cold_item = item_map.get(cold_id)
        if cold_item is None:
            continue
        cold_notes = cold_item["all_notes"]
        cold_primary = cold_item["primary_accord"]
        relevant = set()
        for other_id, other_item in item_map.items():
            if other_id == cold_id:
                continue
            if other_item["primary_accord"] != cold_primary:
                continue
            other_notes = other_item["all_notes"]
            union = cold_notes | other_notes
            jaccard = len(cold_notes & other_notes) / len(union) if union else 0.0
            if jaccard > 0.20:
                relevant.add(other_id)
        if relevant:
            ground_truth[cold_id] = relevant

    logger.info("Ground truth: %d cold items with relevant sets", len(ground_truth))
    cold_ids_filtered = list(ground_truth.keys())

    # Build features
    embeddings = np.load("ml/data/embeddings.npy")
    with open("ml/data/embedding_index.json", "r") as f:
        embedding_index = json.load(f)

    all_accords = sorted(df["primary_accord"].unique())
    accord_to_idx = {a: i for i, a in enumerate(all_accords)}

    node_features_list = []
    node_ids = []
    for _, row in df.iterrows():
        fid = row["fragrance_id"]
        if fid not in embedding_index:
            continue
        accord_vec = np.zeros(len(all_accords), dtype=np.float32)
        accord = row.get("primary_accord", "Unknown")
        if accord in accord_to_idx:
            accord_vec[accord_to_idx[accord]] = 1.0
        emb_vec = embeddings[embedding_index[fid]].astype(np.float32)
        node_features_list.append(np.concatenate([accord_vec, emb_vec]))
        node_ids.append(fid)

    node_features = np.array(node_features_list, dtype=np.float32)
    logger.info("Features: %s", node_features.shape)

    fragrance_ids = df["fragrance_id"].tolist()

    # ======================== 1. GraphSAGE-Jaccard ========================
    logger.info("Building Jaccard graph...")
    edge_index_j, _, nid2idx_j, _ = build_jaccard_graph(
        fragrance_ids=fragrance_ids,
        catalog_path=config.data_path,
        k=config.graphsage_knn_k,
        threshold=0.2,
    )
    logger.info("Jaccard graph: %d edges", edge_index_j.shape[1])

    warm_idx_j = [nid2idx_j[nid] for nid in warm_ids if nid in nid2idx_j]
    cold_idx_j = [nid2idx_j[nid] for nid in cold_ids_filtered if nid in nid2idx_j]
    warm_node_set_j = set(warm_idx_j)
    warm_edge_mask_j = np.array([
        edge_index_j[0, i] in warm_node_set_j and edge_index_j[1, i] in warm_node_set_j
        for i in range(edge_index_j.shape[1])
    ]) if edge_index_j.shape[1] > 0 else np.array([], dtype=bool)
    warm_edge_index_j = edge_index_j[:, warm_edge_mask_j] if edge_index_j.shape[1] > 0 else edge_index_j

    jaccard_wrapper = GraphSAGEWrapper(
        embedding_dim=64, num_layers=2, dropout=0.1,
        edge_dropout=0.1, tau=0.5, loss_type="contrastive",
    )
    if warm_edge_index_j.shape[1] > 0:
        jaccard_wrapper.train(
            node_features=node_features, edge_index=warm_edge_index_j, node_ids=node_ids,
            num_epochs=config.graphsage_epochs, learning_rate=0.01,
        )
    else:
        jaccard_wrapper.is_trained = True

    j_preds = jaccard_wrapper.predict_cold_start(
        node_features=node_features, edge_index=edge_index_j,
        train_node_ids=warm_ids, test_node_ids=cold_ids_filtered, k=10,
    )
    j_ndcg = per_item_ndcg(j_preds, ground_truth, k=10)

    # ==================== 2. GraphSAGE-Embedding ====================
    logger.info("Building embedding similarity graph...")
    edge_index_e, _, nid2idx_e, _ = build_similarity_graph(
        fragrance_ids=fragrance_ids,
        embeddings_path="ml/data/embeddings.npy",
        embedding_index_path="ml/data/embedding_index.json",
        k=config.graphsage_knn_k,
        threshold=config.graphsage_similarity_threshold,
    )
    logger.info("Embedding graph: %d edges", edge_index_e.shape[1])

    warm_idx_e = [nid2idx_e[nid] for nid in warm_ids if nid in nid2idx_e]
    cold_idx_e = [nid2idx_e[nid] for nid in cold_ids_filtered if nid in nid2idx_e]
    warm_node_set_e = set(warm_idx_e)
    warm_edge_mask_e = np.array([
        edge_index_e[0, i] in warm_node_set_e and edge_index_e[1, i] in warm_node_set_e
        for i in range(edge_index_e.shape[1])
    ]) if edge_index_e.shape[1] > 0 else np.array([], dtype=bool)
    warm_edge_index_e = edge_index_e[:, warm_edge_mask_e] if edge_index_e.shape[1] > 0 else edge_index_e

    embed_wrapper = GraphSAGEWrapper(
        embedding_dim=64, num_layers=2, dropout=0.1,
        edge_dropout=0.1, tau=0.5, loss_type="contrastive",
    )
    if warm_edge_index_e.shape[1] > 0:
        embed_wrapper.train(
            node_features=node_features, edge_index=warm_edge_index_e, node_ids=node_ids,
            num_epochs=config.graphsage_epochs, learning_rate=0.01,
        )
    else:
        embed_wrapper.is_trained = True

    e_preds = embed_wrapper.predict_cold_start(
        node_features=node_features, edge_index=edge_index_e,
        train_node_ids=warm_ids, test_node_ids=cold_ids_filtered, k=10,
    )
    e_ndcg = per_item_ndcg(e_preds, ground_truth, k=10)

    # ==================== 3. Popularity ====================
    logger.info("Running Popularity baseline...")
    pop_baseline = PopularityBaseline()
    pop_preds = {}
    for cid in cold_ids_filtered:
        ranked = pop_baseline.get_rankings(k=10)
        pop_preds[cid] = [(rid, len(ranked) - i) for i, rid in enumerate(ranked)]
    pop_ndcg = per_item_ndcg(pop_preds, ground_truth, k=10)

    # ==================== 4. Random ====================
    logger.info("Running Random baseline...")
    rnd_baseline = RandomBaseline()
    rnd_preds = {}
    for cid in cold_ids_filtered:
        ranked = rnd_baseline.get_rankings(k=10)
        rnd_preds[cid] = [(rid, len(ranked) - i) for i, rid in enumerate(ranked)]
    rnd_ndcg = per_item_ndcg(rnd_preds, ground_truth, k=10)

    # ==================== 5. Feature-Only ====================
    logger.info("Running Feature-Only baseline (cosine sim on raw input features)...")
    features_norm = node_features / (np.linalg.norm(node_features, axis=1, keepdims=True) + 1e-8)
    sim_matrix = features_norm @ features_norm.T
    node_id_to_idx_f = {nid: i for i, nid in enumerate(node_ids)}
    cold_idx_f = [node_id_to_idx_f[cid] for cid in cold_ids_filtered if cid in node_id_to_idx_f]

    fo_preds = {}
    for idx in cold_idx_f:
        node_id = node_ids[idx]
        sim_scores = sim_matrix[idx].copy()
        sim_scores[idx] = -np.inf
        top_k_idx = np.argsort(sim_scores)[::-1][:10]
        top_scores = sim_scores[top_k_idx]
        top_ids = [node_ids[i] for i in top_k_idx]
        fo_preds[node_id] = list(zip(top_ids, top_scores.tolist()))
    fo_ndcg = per_item_ndcg(fo_preds, ground_truth, k=10)

    # ==================== Align items across all models ====================
    common = sorted(set(j_ndcg.keys()) & set(e_ndcg.keys()) & set(pop_ndcg.keys()) & set(rnd_ndcg.keys()) & set(fo_ndcg.keys()))
    logger.info("Common cold items across all models: %d", len(common))

    def align(d: dict) -> list[float]:
        return [d[c] for c in common]

    j_scores = align(j_ndcg)
    e_scores = align(e_ndcg)
    p_scores = align(pop_ndcg)
    r_scores = align(rnd_ndcg)

    fo_scores = align(fo_ndcg)

    models = {
        "GraphSAGE-Jaccard":   j_scores,
        "GraphSAGE-Embedding": e_scores,
        "Popularity":          p_scores,
        "Random":              r_scores,
        "Feature-Only":        fo_scores,
    }

    print("\n" + "=" * 70)
    print("PER-ITEM NDCG@10 SUMMARY")
    print("=" * 70)
    for name, scores in models.items():
        arr = np.array(scores)
        print(f"{name:24s}  mean={arr.mean():.6f}  "
              f"std={arr.std():.6f}  median={np.median(arr):.6f}  n={len(scores)}")
    print()

    # ==================== Bootstrap comparisons ====================
    comparisons = [
        ("GraphSAGE-Jaccard", "GraphSAGE-Embedding", j_scores, e_scores),
        ("GraphSAGE-Jaccard", "Popularity",           j_scores, p_scores),
        ("GraphSAGE-Jaccard", "Random",               j_scores, r_scores),
    ]

    comparisons_10000 = [
        ("GraphSAGE-Jaccard", "Feature-Only",        j_scores, fo_scores),
    ]

    bs = BootstrapSignificance(n_resamples=1000, random_seed=42)
    bs_10000 = BootstrapSignificance(n_resamples=10000, random_seed=42)

    for model_a_name, model_b_name, a_scores, b_scores in comparisons:
        arr_a = np.array(a_scores)
        arr_b = np.array(b_scores)
        diff = arr_a - arr_b
        obs_diff = diff.mean()

        p_val = bs.paired_bca_test(a_scores, b_scores)
        ci_a = bs.confidence_interval(a_scores, [0.0] * len(a_scores), confidence=0.95)
        ci_b = bs.confidence_interval(b_scores, [0.0] * len(b_scores), confidence=0.95)
        cohens_d = bs.effect_size(a_scores, b_scores)

        print("=" * 70)
        print(f"Bootstrap: {model_a_name}  vs  {model_b_name}")
        print(f"  (one-sided: {model_a_name} > {model_b_name})")
        print("-" * 70)
        print(f"  {model_a_name} mean NDCG@10:     {arr_a.mean():.6f}")
        print(f"    95% CI:                        [{ci_a[0]:.6f}, {ci_a[1]:.6f}]")
        print(f"  {model_b_name} mean NDCG@10:     {arr_b.mean():.6f}")
        print(f"    95% CI:                        [{ci_b[0]:.6f}, {ci_b[1]:.6f}]")
        print(f"  Mean difference:                 {obs_diff:.6f}")
        print(f"  Effect size (Cohen's d):         {cohens_d:.4f}")
        print(f"  Paired bootstrap p-value:        {p_val:.4f}")
        sig = "YES" if p_val < 0.05 else "NO"
        print(f"  Statistically significant (alpha=0.05): {sig}")
        print()

    for model_a_name, model_b_name, a_scores, b_scores in comparisons_10000:
        arr_a = np.array(a_scores)
        arr_b = np.array(b_scores)
        diff = arr_a - arr_b
        obs_diff = diff.mean()

        p_val = bs_10000.paired_bca_test(a_scores, b_scores)
        ci_a = bs_10000.confidence_interval(a_scores, [0.0] * len(a_scores), confidence=0.95)
        ci_b = bs_10000.confidence_interval(b_scores, [0.0] * len(b_scores), confidence=0.95)
        cohens_d = bs_10000.effect_size(a_scores, b_scores)

        print("=" * 70)
        print(f"Bootstrap: {model_a_name}  vs  {model_b_name}")
        print(f"  (one-sided: {model_a_name} > {model_b_name})  [n_resamples={bs_10000.n_resamples}]")
        print("-" * 70)
        print(f"  {model_a_name} mean NDCG@10:     {arr_a.mean():.6f}")
        print(f"    95% CI:                        [{ci_a[0]:.6f}, {ci_a[1]:.6f}]")
        print(f"  {model_b_name} mean NDCG@10:     {arr_b.mean():.6f}")
        print(f"    95% CI:                        [{ci_b[0]:.6f}, {ci_b[1]:.6f}]")
        print(f"  Mean difference:                 {obs_diff:.6f}")
        print(f"  Effect size (Cohen's d):         {cohens_d:.4f}")
        print(f"  Paired bootstrap p-value:        {p_val:.4f}")
        sig = "YES" if p_val < 0.05 else "NO"
        print(f"  Statistically significant (alpha=0.05): {sig}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
