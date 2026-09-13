import json
import logging
from typing import Tuple, Dict, List

import numpy as np
from sklearn.neighbors import NearestNeighbors

logger = logging.getLogger(__name__)


def build_similarity_graph(
    fragrance_ids: List[str],
    embeddings_path: str = "ml/data/embeddings.npy",
    embedding_index_path: str = "ml/data/embedding_index.json",
    k: int = 10,
    threshold: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, int], Dict[int, str]]:
    embeddings = np.load(embeddings_path)
    with open(embedding_index_path, "r") as f:
        embedding_index = json.load(f)

    local_indices = []
    local_ids = []
    for fid in fragrance_ids:
        if fid not in embedding_index:
            logger.warning(f"Fragrance {fid} not in embedding index — skipping")
            continue
        local_indices.append(embedding_index[fid])
        local_ids.append(fid)

    if len(local_ids) == 0:
        logger.warning("No valid fragrance IDs found in embedding index")
        return np.empty((2, 0), dtype=np.int64), np.empty((0,), dtype=np.float32), {}, {}

    local_embeddings = embeddings[local_indices].astype(np.float32)
    node_id_to_idx = {nid: i for i, nid in enumerate(local_ids)}
    idx_to_node_id = {i: nid for i, nid in enumerate(local_ids)}

    effective_k = min(k, max(1, len(local_ids) - 1))
    if effective_k < k:
        logger.warning(f"Reducing KNN k from {k} to {effective_k} (only {len(local_ids)} nodes available)")

    if len(local_ids) == 1:
        logger.warning("Only 1 node in graph — returning empty edge_index")
        return np.empty((2, 0), dtype=np.int64), np.empty((0,), dtype=np.float32), node_id_to_idx, idx_to_node_id

    nn = NearestNeighbors(n_neighbors=effective_k + 1, metric="cosine", algorithm="brute")
    nn.fit(local_embeddings)
    distances, indices = nn.kneighbors(local_embeddings)

    edge_list = []
    score_list = []
    for i in range(len(local_ids)):
        for j in range(1, effective_k + 1):
            neighbor_idx = int(indices[i][j])
            similarity = 1.0 - float(distances[i][j])
            if similarity > threshold and i < neighbor_idx:
                edge_list.append((i, neighbor_idx))
                score_list.append(similarity)

    if len(edge_list) == 0:
        logger.warning(f"No edges passed similarity threshold {threshold} — returning empty edge_index")
        empty_edge = np.empty((2, 0), dtype=np.int64)
        empty_score = np.empty((0,), dtype=np.float32)
        return empty_edge, empty_score, node_id_to_idx, idx_to_node_id

    edge_index = np.array(edge_list, dtype=np.int64).T
    edge_scores = np.array(score_list, dtype=np.float32)

    logger.info(f"Built similarity graph: {len(local_ids)} nodes, {edge_index.shape[1]} edges (k={effective_k}, threshold={threshold})")

    return edge_index, edge_scores, node_id_to_idx, idx_to_node_id


def build_jaccard_graph(
    fragrance_ids: List[str],
    catalog_path: str = "ml/data/scentrix_master_cleaned.json",
    k: int = 10,
    threshold: float = 0.2,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, int], Dict[int, str]]:
    with open(catalog_path, "r") as f:
        catalog = json.load(f)

    note_sets = {}
    primary_accords = {}
    for item in catalog:
        fid = item.get("id", "")
        top = {str(n).lower() for n in (item.get("top_notes") or []) if n}
        mid = {str(n).lower() for n in (item.get("middle_notes") or []) if n}
        base = {str(n).lower() for n in (item.get("base_notes") or []) if n}
        note_sets[fid] = top | mid | base
        accords = item.get("accords") or []
        primary_accords[fid] = str(accords[0]).lower() if accords else "unknown"

    local_ids = [fid for fid in fragrance_ids if fid in note_sets]
    node_id_to_idx = {nid: i for i, nid in enumerate(local_ids)}
    idx_to_node_id = {i: nid for i, nid in enumerate(local_ids)}

    if len(local_ids) < 2:
        logger.warning("Too few nodes for Jaccard graph — returning empty edge_index")
        return np.empty((2, 0), dtype=np.int64), np.empty((0,), dtype=np.float32), node_id_to_idx, idx_to_node_id

    n = len(local_ids)
    all_scores = [[] for _ in range(n)]
    for i in range(n):
        id_i = local_ids[i]
        notes_i = note_sets[id_i]
        accord_i = primary_accords[id_i]
        for j in range(i + 1, n):
            id_j = local_ids[j]
            if primary_accords[id_j] != accord_i:
                continue
            notes_j = note_sets[id_j]
            union = notes_i | notes_j
            jaccard = len(notes_i & notes_j) / len(union) if union else 0.0
            if jaccard > threshold:
                all_scores[i].append((j, jaccard))
                all_scores[j].append((i, jaccard))

    for i in range(n):
        all_scores[i].sort(key=lambda x: -x[1])
        all_scores[i] = all_scores[i][:k]

    edge_list = []
    score_list = []
    for i, neighbors in enumerate(all_scores):
        for j, score in neighbors:
            if i < j:
                edge_list.append((i, j))
                score_list.append(score)

    if len(edge_list) == 0:
        logger.warning("No edges passed Jaccard threshold — returning empty edge_index")
        return np.empty((2, 0), dtype=np.int64), np.empty((0,), dtype=np.float32), node_id_to_idx, idx_to_node_id

    edge_index = np.array(edge_list, dtype=np.int64).T
    edge_scores = np.array(score_list, dtype=np.float32)

    logger.info(f"Built Jaccard graph: {len(local_ids)} nodes, {edge_index.shape[1]} edges (k={k}, threshold={threshold})")

    return edge_index, edge_scores, node_id_to_idx, idx_to_node_id


def build_jaccard_graph_sweep(
    fragrance_ids: List[str],
    catalog_path: str = "ml/data/scentrix_master_cleaned.json",
    k: int = 10,
    thresholds: List[float] = None,
) -> Dict[float, Tuple[np.ndarray, np.ndarray, Dict[str, int], Dict[int, str]]]:
    if thresholds is None:
        thresholds = [0.10, 0.15, 0.20, 0.25, 0.30]

    results = {}
    for t in thresholds:
        logger.info(f"Jaccard graph sweep: threshold={t}")
        edge_index, edge_scores, nid2idx, idx2nid = build_jaccard_graph(
            fragrance_ids=fragrance_ids,
            catalog_path=catalog_path,
            k=k,
            threshold=t,
        )
        results[t] = (edge_index, edge_scores, nid2idx, idx2nid)
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    import json
    with open("ml/data/scentrix_master_cleaned.json", "r") as f:
        data = json.load(f)

    sample_ids = [item["id"] for item in data[:100]]
    edge_index, edge_scores, nid2idx, idx2nid = build_similarity_graph(sample_ids)

    print(f"Edge index shape: {edge_index.shape}")
    print(f"Edge scores shape: {edge_scores.shape}")
    print(f"Edge scores range: [{edge_scores.min():.4f}, {edge_scores.max():.4f}]")
    print(f"Number of nodes in graph: {len(nid2idx)}")
    print(f"Sample edges (first 5): {edge_index[:, :5].tolist()}")
