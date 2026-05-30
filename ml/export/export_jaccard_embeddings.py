"""Build-time export of GraphSAGE-Jaccard embeddings for Phase 7 serving.

Reuses the exact evaluation code paths from:
  - pipeline.py:_build_features        (feature construction)
  - graph_builder.py:build_jaccard_graph (Jaccard edge index)
  - graphsage_wrapper.py:load           (checkpoint loading)
  - graphsage_wrapper.py:predict_cold_start L195-196 (forward pass + normalization)

Produces:
  - node_embeddings_jaccard.npy (L2-normalized, [N, 64])
  - node_ids_jaccard.json        (aligned 1:1 with embeddings)
  - metadata.json                (provenance + validation results)
"""

import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
CATALOG_PATH = "ml/data/scentrix_master_cleaned.json"
EMBEDDINGS_PATH = "ml/data/embeddings.npy"
EMBEDDING_INDEX_PATH = "ml/data/embedding_index.json"
CHECKPOINT_PATH = "ml/eval/runs/20260528_165737/models/graphsage_jaccard.pt"
OUTPUT_DIR = Path("ml/models/serving/v1")

JACCARD_K = 10
JACCARD_THRESHOLD = 0.2

# ── Step 1: Feature construction ─────────────────────────────────────────────
# Reuses exact logic from pipeline.py:_build_features (lines 136-165)
def build_features() -> tuple[np.ndarray, list[str]]:
    logger.info("Loading SentenceTransformer embeddings...")
    embeddings = np.load(EMBEDDINGS_PATH)

    logger.info("Loading embedding index...")
    with open(EMBEDDING_INDEX_PATH) as f:
        embedding_index = json.load(f)

    logger.info("Loading catalog...")
    with open(CATALOG_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # Replicate pipeline.py:_load_data + _build_features exactly:
    # primary_accord = first accord from each item's accords list (pipeline.py L131)
    # all_accords = sorted unique primary accords (pipeline.py L141)
    primary_accords_set: set[str] = set()
    records: list[dict] = []
    for item in data:
        accords = item.get("accords") or []
        primary = str(accords[0]).lower() if accords else "Unknown"
        primary_accords_set.add(primary)
        records.append({"fragrance_id": item["id"], "primary_accord": primary})
    all_accords = sorted(primary_accords_set)
    accord_to_idx = {a: i for i, a in enumerate(all_accords)}
    logger.info("Accord vocabulary: %d unique primary accords", len(all_accords))

    node_features_list = []
    node_ids = []

    for row in records:
        fragrance_id = row["fragrance_id"]
        if fragrance_id not in embedding_index:
            logger.warning("Fragrance %s not in embedding index — skipping", fragrance_id)
            continue

        accord = row["primary_accord"]
        accord_vec = np.zeros(len(all_accords), dtype=np.float32)
        if accord in accord_to_idx:
            accord_vec[accord_to_idx[accord]] = 1.0

        emb_idx = embedding_index[fragrance_id]
        emb_vec = embeddings[emb_idx].astype(np.float32)

        feature_vec = np.concatenate([accord_vec, emb_vec])
        node_features_list.append(feature_vec)
        node_ids.append(fragrance_id)

    features = np.array(node_features_list, dtype=np.float32)
    logger.info("Features assembled: shape=%s, dtype=%s", features.shape, features.dtype)
    return features, node_ids


# ── Step 2: Jaccard edge index ───────────────────────────────────────────────
# Reuses exact logic from graph_builder.py:build_jaccard_graph (lines 75-141)
def build_jaccard_graph(fragrance_ids: list[str]) -> tuple[np.ndarray, dict[str, int], dict[int, str]]:
    logger.info("Building Jaccard graph (k=%d, threshold=%.2f)...", JACCARD_K, JACCARD_THRESHOLD)
    with open(CATALOG_PATH, encoding="utf-8") as f:
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
        raise RuntimeError("Too few nodes for Jaccard graph")

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
            if jaccard > JACCARD_THRESHOLD:
                all_scores[i].append((j, jaccard))
                all_scores[j].append((i, jaccard))

    for i in range(n):
        all_scores[i].sort(key=lambda x: -x[1])
        all_scores[i] = all_scores[i][:JACCARD_K]

    edge_list = []
    score_list = []
    for i, neighbors in enumerate(all_scores):
        for j, score in neighbors:
            if i < j:
                edge_list.append((i, j))
                score_list.append(score)

    if len(edge_list) == 0:
        raise RuntimeError("No edges passed Jaccard threshold")

    edge_index = np.array(edge_list, dtype=np.int64).T
    logger.info("Jaccard graph built: %d nodes, %d edges", n, edge_index.shape[1])
    return edge_index, node_id_to_idx, idx_to_node_id


# ── Step 3: Load checkpoint and run forward pass ────────────────────────────
def load_model(input_dim: int, device: str) -> torch.nn.Module:
    from ml.eval.models.graphsage_wrapper import GraphSAGEWrapper

    wrapper = GraphSAGEWrapper(embedding_dim=64, device=device)
    wrapper.load(CHECKPOINT_PATH, input_dim=input_dim)
    if not wrapper.is_trained:
        raise RuntimeError("Checkpoint loaded but model reports is_trained=False")

    wrapper.model.eval()
    logger.info("Checkpoint loaded: %s", CHECKPOINT_PATH)
    return wrapper.model


def compute_embeddings(
    model: torch.nn.Module,
    node_features: np.ndarray,
    edge_index: np.ndarray,
    device: str,
) -> np.ndarray:
    features_tensor = torch.FloatTensor(node_features).to(device)
    edge_index_tensor = torch.LongTensor(edge_index).to(device)

    with torch.no_grad():
        raw_embeddings = model(features_tensor, edge_index_tensor)
        # Reuse exact normalization from graphsage_wrapper.py L196:
        #   embeddings_norm = F.normalize(embeddings, p=2, dim=1)
        normalized = F.normalize(raw_embeddings, p=2, dim=1)

    return normalized.cpu().numpy()


# ── Step 4: Validation ──────────────────────────────────────────────────────
def validate(embeddings: np.ndarray, node_ids: list[str]) -> dict:
    results = {}

    results["shape"] = list(embeddings.shape)
    results["expected_shape"] = [len(node_ids), 64]
    results["shape_ok"] = embeddings.shape == (len(node_ids), 64)

    results["dtype"] = str(embeddings.dtype)
    results["node_count"] = len(node_ids)
    results["unique_node_count"] = len(set(node_ids))
    results["no_duplicates"] = len(node_ids) == len(set(node_ids))

    nan_count = int(np.sum(np.isnan(embeddings)))
    inf_count = int(np.sum(~np.isfinite(embeddings)))
    results["nan_count"] = nan_count
    results["inf_count"] = inf_count
    results["no_nan"] = nan_count == 0
    results["no_inf"] = inf_count == 0

    norms = np.linalg.norm(embeddings, axis=1)
    results["l2_norm_min"] = round(float(np.min(norms)), 6)
    results["l2_norm_max"] = round(float(np.max(norms)), 6)
    results["l2_norm_mean"] = round(float(np.mean(norms)), 6)
    near_one = np.sum((norms > 0.999) & (norms < 1.001))
    results["rows_near_unit_norm"] = int(near_one)
    results["all_normalized"] = near_one == len(node_ids)

    all_ok = all([
        results["shape_ok"],
        results["no_duplicates"],
        results["no_nan"],
        results["no_inf"],
        results["all_normalized"],
    ])
    results["all_checks_passed"] = bool(all_ok)

    # Convert numpy types to native Python for JSON serialization
    for k, v in results.items():
        if isinstance(v, (np.integer,)):
            results[k] = int(v)
        elif isinstance(v, (np.floating,)):
            results[k] = float(v)
        elif isinstance(v, (np.bool_,)):
            results[k] = bool(v)

    return results


# ── Step 5: Save artifacts ──────────────────────────────────────────────────
def save_artifacts(
    embeddings: np.ndarray,
    node_ids: list[str],
    validation: dict,
    device: str,
):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", OUTPUT_DIR.resolve())

    npy_path = OUTPUT_DIR / "node_embeddings_jaccard.npy"
    np.save(npy_path, embeddings)
    logger.info("Saved: %s (%.2f MB)", npy_path.name, embeddings.nbytes / 1024 / 1024)

    ids_path = OUTPUT_DIR / "node_ids_jaccard.json"
    with open(ids_path, "w") as f:
        json.dump(node_ids, f)
    logger.info("Saved: %s (%d ids)", ids_path.name, len(node_ids))

    git_hash = "unknown"
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            git_hash = result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    metadata = {
        "artifact_name": "node_embeddings_jaccard.npy",
        "description": "L2-normalized GraphSAGE-Jaccard embeddings for Phase 7 centroid retrieval",
        "source_checkpoint": CHECKPOINT_PATH,
        "source_catalog": CATALOG_PATH,
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "node_count": len(node_ids),
        "embedding_dimension": int(embeddings.shape[1]),
        "graph_threshold": JACCARD_THRESHOLD,
        "graph_k": JACCARD_K,
        "normalization": "L2 (F.normalize, p=2, dim=1)",
        "normalization_location": "post-forward-pass, before save (replicating graphsage_wrapper.py L196)",
        "device": device,
        "git_commit_hash": git_hash,
        "validation": validation,
    }

    meta_path = OUTPUT_DIR / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved: %s", meta_path.name)

    return metadata


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    logger.info("=" * 60)
    logger.info("Jaccard Embedding Export Pipeline")
    logger.info("=" * 60)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Device: %s", device)

    # Step 1: Build features
    node_features, node_ids = build_features()
    input_dim = node_features.shape[1]
    logger.info("Model input dimension: %d", input_dim)

    # Step 2: Build Jaccard graph
    edge_index, nid2idx, idx2nid = build_jaccard_graph(node_ids)
    assert node_features.shape[0] == len(node_ids) == len(nid2idx), (
        f"Size mismatch: features={node_features.shape[0]}, node_ids={len(node_ids)}, graph={len(nid2idx)}"
    )

    # Step 3: Load model and compute embeddings
    model = load_model(input_dim, device)
    embeddings = compute_embeddings(model, node_features, edge_index, device)

    # Step 4: Validate
    validation = validate(embeddings, node_ids)
    logger.info("Validation results:")
    for key, val in validation.items():
        logger.info("  %s: %s", key, val)

    if not validation["all_checks_passed"]:
        logger.error("Validation FAILED — artifact not saved")
        sys.exit(1)

    # Step 5: Save
    metadata = save_artifacts(embeddings, node_ids, validation, device)

    logger.info("=" * 60)
    logger.info("Export complete")
    logger.info("  node_embeddings_jaccard.npy:  %s", OUTPUT_DIR / "node_embeddings_jaccard.npy")
    logger.info("  node_ids_jaccard.json:        %s", OUTPUT_DIR / "node_ids_jaccard.json")
    logger.info("  metadata.json:                %s", OUTPUT_DIR / "metadata.json")
    logger.info("  all_checks_passed:            %s", validation["all_checks_passed"])
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
