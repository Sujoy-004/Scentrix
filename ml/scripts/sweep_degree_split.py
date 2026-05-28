"""Degree-split: re-run sweep, split cold items by degree >0 vs =0, report NDCG per group."""

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from ml.eval.config import EvalConfig
from ml.eval.split import ColdStartSplitter, LeaveColdOutStrategy
from ml.eval.models.graph_builder import build_jaccard_graph_sweep
from ml.eval.models.graphsage_wrapper import GraphSAGEWrapper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sweep_degree_split")


def per_item_ndcg_at_k(
    predictions: dict[str, list[tuple[str, float]]],
    ground_truth: dict[str, set[str]],
    k: int = 10,
) -> dict[str, float]:
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
    config.graphsage_epochs = 100
    config.seed = 42
    k = 10

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
    logger.info("Split: %d warm, %d cold", len(warm_ids), len(cold_ids))

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
    fragrance_ids = df["fragrance_id"].tolist()
    logger.info("Features: %s", node_features.shape)

    thresholds = [0.10, 0.15, 0.20, 0.25, 0.30]
    sweep_graphs = build_jaccard_graph_sweep(
        fragrance_ids=fragrance_ids,
        catalog_path=config.data_path,
        k=config.graphsage_knn_k,
        thresholds=thresholds,
    )

    print()
    print("=" * 95)
    print("DEGREE-SPLIT ANALYSIS: Jaccard Threshold Sweep with GraphSAGE")
    print("=" * 95)
    print(f"{'Threshold':>10s}  {'Edges':>8s}  {'A_n':>6s}  {'A_NDCG':>10s}  {'B_n':>6s}  {'B_NDCG':>10s}  {'Aggregate_NDCG':>15s}")
    print("-" * 95)

    for t in sorted(sweep_graphs.keys()):
        ei, es, n2i, i2n = sweep_graphs[t]
        n_edges = ei.shape[1]

        if n_edges == 0 or node_features.shape[0] < 2:
            print(f"{t:>10.2f}  {n_edges:>8d}  {'':>6s}  {'':>10s}  {'':>6s}  {'':>10s}  {'':>15s}")
            continue

        warm_idx = [n2i[nid] for nid in warm_ids if nid in n2i]
        warm_set = set(warm_idx)
        mask = np.array([
            ei[0, i] in warm_set and ei[1, i] in warm_set
            for i in range(n_edges)
        ]) if n_edges > 0 else np.array([], dtype=bool)
        warm_ei = ei[:, mask] if n_edges > 0 else ei

        if warm_ei.shape[1] == 0:
            print(f"{t:>10.2f}  {n_edges:>8d}  {'':>6s}  {'':>10s}  {'':>6s}  {'':>10s}  {'':>15s}")
            continue

        cold_idx = [n2i[cid] for cid in cold_ids_filtered if cid in n2i]

        deg = np.zeros(len(n2i), dtype=np.int64)
        for e in range(n_edges):
            deg[ei[0, e]] += 1
            deg[ei[1, e]] += 1

        group_a_idx = [idx for idx in cold_idx if deg[idx] > 0]
        group_b_idx = [idx for idx in cold_idx if deg[idx] == 0]
        group_a_ids = [node_ids[idx] for idx in group_a_idx]
        group_b_ids = [node_ids[idx] for idx in group_b_idx]

        np.random.seed(config.seed)
        torch.manual_seed(config.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(config.seed)

        wrapper = GraphSAGEWrapper(
            embedding_dim=64, num_layers=2, dropout=0.1,
            edge_dropout=0.1, tau=0.5, loss_type="contrastive",
        )
        wrapper.train(
            node_features=node_features, edge_index=warm_ei, node_ids=node_ids,
            num_epochs=config.graphsage_epochs, learning_rate=0.01,
        )
        preds = wrapper.predict_cold_start(
            node_features=node_features, edge_index=ei,
            train_node_ids=warm_ids, test_node_ids=cold_ids_filtered,
            k=k,
        )

        ndcg_per_item = per_item_ndcg_at_k(preds, ground_truth, k=k)

        a_scores = [ndcg_per_item[cid] for cid in group_a_ids if cid in ndcg_per_item]
        a_ndcg = float(np.mean(a_scores)) if a_scores else 0.0

        b_scores = [ndcg_per_item[cid] for cid in group_b_ids if cid in ndcg_per_item]
        b_ndcg = float(np.mean(b_scores)) if b_scores else 0.0

        all_scores = [ndcg_per_item[cid] for cid in cold_ids_filtered if cid in ndcg_per_item]
        agg_ndcg = float(np.mean(all_scores)) if all_scores else 0.0

        print(f"{t:>10.2f}  {n_edges:>8d}  {len(group_a_ids):>6d}  {a_ndcg:>10.6f}  {len(group_b_ids):>6d}  {b_ndcg:>10.6f}  {agg_ndcg:>15.6f}")

    print("=" * 95)
    print()
    print("A = Group A (cold items with degree > 0 in Jaccard graph)")
    print("B = Group B (cold items with degree = 0, use feature-only fallback)")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
