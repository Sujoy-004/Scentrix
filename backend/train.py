"""Regenerate GraphSAGE-Jaccard embeddings for Scentrix serving.

Recovered from git commit 8d1c501 (pre-cleanup):
  - ml/scripts/generate_embeddings.py       (encode step)
  - ml/eval/models/graph_builder.py         (build_jaccard_graph)
  - ml/eval/models/graphsage_wrapper.py     (GraphSAGE + _info_nce_loss + train loop)
  - ml/export/export_jaccard_embeddings.py  (build_features, validate, save)

The original checkpoint and ml/data/embeddings.npy were gitignored, so the same
architecture is trained inline and 384-d text embeddings are regenerated via
sentence-transformers. Exports byte-compatible artifacts to backend/app/data/:
node_embeddings_jaccard.npy [4559x64] float32 L2-normalized, node_ids_jaccard.json
(4559 ids in catalog order), metadata.json. Dependencies: torch, numpy,
sentence-transformers only. Overwrites artifacts only when run.
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "app" / "data"
CATALOG_PATH = DATA_DIR / "scentrix_master_cleaned.json"
TEXT_EMBEDDINGS_PATH = DATA_DIR / "text_embeddings.npy"
OUTPUT_EMBEDDINGS_PATH = DATA_DIR / "node_embeddings_jaccard.npy"
OUTPUT_IDS_PATH = DATA_DIR / "node_ids_jaccard.json"
OUTPUT_METADATA_PATH = DATA_DIR / "metadata.json"

EXPECTED_CATALOG_SIZE = 4559
EMBEDDING_DIM = 64
NUM_LAYERS = 2
DROPOUT = 0.1
EDGE_DROPOUT = 0.1
TAU = 0.5
JACCARD_K = 10
JACCARD_THRESHOLD = 0.2
TEXT_EMBEDDING_DIM = 384
TEXT_MODEL_DEFAULT = "all-MiniLM-L6-v2"
SEED = 42


# ── Step 1: Text embeddings (ported from generate_embeddings.py encode step) ─
def generate_text_embeddings(catalog, model_name=TEXT_MODEL_DEFAULT, output_path=TEXT_EMBEDDINGS_PATH):
    from sentence_transformers import SentenceTransformer

    logger.info("Initializing SentenceTransformer model: %s...", model_name)
    model = SentenceTransformer(model_name)

    texts = []
    for item in catalog:
        notes = " ".join(item.get("top_notes", []) or [])
        accords = " ".join(item.get("accords", []) or [])
        texts.append(f"{item.get('name','')} {item.get('brand','')} {notes} {accords} {item.get('category','')}".strip())

    logger.info("Generating text embeddings for %d items (this may take a few minutes)...", len(texts))
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True).astype(np.float32)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, embeddings)
    logger.info("Saved text embeddings: %s", output_path)
    return embeddings


def load_or_generate_text_embeddings(catalog, model_name=TEXT_MODEL_DEFAULT,
                                     output_path=TEXT_EMBEDDINGS_PATH, skip_text=False):
    if output_path.exists():
        embeddings = np.load(output_path)
        if embeddings.shape == (len(catalog), TEXT_EMBEDDING_DIM):
            logger.info("Loading cached text embeddings: %s", output_path)
            return embeddings.astype(np.float32)
        logger.warning("Cached embeddings shape %s does not match (%d, %d) — regenerating",
                       embeddings.shape, len(catalog), TEXT_EMBEDDING_DIM)
    elif skip_text:
        raise RuntimeError(f"--skip-text set but cache not found at {output_path}")
    return generate_text_embeddings(catalog, model_name=model_name, output_path=output_path)


# ── Step 2: Feature construction (ported from export_jaccard_embeddings.build_features) ──
def build_features(catalog, text_embeddings):
    primary_accords_set, records = set(), []
    for item in catalog:
        accords = item.get("accords") or []
        primary = str(accords[0]).lower() if accords else "Unknown"  # "Unknown" casing kept from original
        primary_accords_set.add(primary)
        records.append({"fragrance_id": str(item["id"]), "primary_accord": primary})
    all_accords = sorted(primary_accords_set)
    accord_to_idx = {a: i for i, a in enumerate(all_accords)}
    logger.info("Accord vocabulary: %d unique primary accords", len(all_accords))

    # Embeddings are regenerated in catalog order, so positional pairing replaces
    # the original embedding_index.json lookup.
    node_features_list, node_ids = [], []
    for row, emb_vec in zip(records, text_embeddings):
        accord_vec = np.zeros(len(all_accords), dtype=np.float32)
        accord = row["primary_accord"]
        if accord in accord_to_idx:
            accord_vec[accord_to_idx[accord]] = 1.0
        node_features_list.append(np.concatenate([accord_vec, emb_vec.astype(np.float32)]))
        node_ids.append(row["fragrance_id"])

    features = np.array(node_features_list, dtype=np.float32)
    logger.info("Features assembled: shape=%s, dtype=%s", features.shape, features.dtype)
    return features, node_ids


# ── Step 3: Jaccard edge index (ported from graph_builder.build_jaccard_graph) ──
def build_jaccard_graph(catalog, fragrance_ids):
    logger.info("Building Jaccard graph (k=%d, threshold=%.2f)...", JACCARD_K, JACCARD_THRESHOLD)

    note_sets, primary_accords = {}, {}
    for item in catalog:
        fid = str(item.get("id", ""))
        top = {str(n).lower() for n in (item.get("top_notes") or []) if n}
        mid = {str(n).lower() for n in (item.get("middle_notes") or []) if n}
        base = {str(n).lower() for n in (item.get("base_notes") or []) if n}
        note_sets[fid] = top | mid | base
        accords = item.get("accords") or []
        primary_accords[fid] = str(accords[0]).lower() if accords else "unknown"  # "unknown" casing kept from original

    local_ids = [fid for fid in fragrance_ids if fid in note_sets]
    node_id_to_idx = {nid: i for i, nid in enumerate(local_ids)}
    idx_to_node_id = {i: nid for i, nid in enumerate(local_ids)}

    if len(local_ids) < 2:
        raise RuntimeError("Too few nodes for Jaccard graph")

    n = len(local_ids)
    all_scores = [[] for _ in range(n)]
    for i in range(n):
        id_i, notes_i, accord_i = local_ids[i], note_sets[local_ids[i]], primary_accords[local_ids[i]]
        for j in range(i + 1, n):
            id_j = local_ids[j]
            if primary_accords[id_j] != accord_i:
                continue
            union = notes_i | note_sets[id_j]
            jaccard = len(notes_i & note_sets[id_j]) / len(union) if union else 0.0
            if jaccard > JACCARD_THRESHOLD:  # STRICT >, not >=
                all_scores[i].append((j, jaccard))
                all_scores[j].append((i, jaccard))

    for i in range(n):
        all_scores[i].sort(key=lambda x: -x[1])
        all_scores[i] = all_scores[i][:JACCARD_K]

    edge_list = [(i, j) for i, neighbors in enumerate(all_scores) for j, _ in neighbors if i < j]
    if not edge_list:
        raise RuntimeError("No edges passed Jaccard threshold")

    edge_index = np.array(edge_list, dtype=np.int64).T
    logger.info("Jaccard graph built: %d nodes, %d edges", n, edge_index.shape[1])
    return edge_index, node_id_to_idx, idx_to_node_id


# ── Step 4: GraphSAGE (ported verbatim from graphsage_wrapper.py:GraphSAGE) ──
class GraphSAGE(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, dropout=0.1):
        super(GraphSAGE, self).__init__()
        self.input_dim, self.hidden_dim, self.num_layers, self.dropout = input_dim, hidden_dim, num_layers, dropout

        self.convs = nn.ModuleList([nn.Linear(input_dim, hidden_dim)])
        for _ in range(num_layers - 1):
            self.convs.append(nn.Linear(hidden_dim, hidden_dim))
        self.convs.append(nn.Linear(hidden_dim, hidden_dim))

        self.dropout_layer = nn.Dropout(dropout)

    def forward(self, x, edge_index):
        num_nodes = x.size(0)

        if edge_index.numel() == 0 or edge_index.shape[1] == 0:
            logger.warning("Empty edge_index in GraphSAGE forward — returning zero-centered embeddings")
            for conv in self.convs:
                x = self.dropout_layer(F.relu(conv(x)))
            return x

        self_loop_edges = torch.arange(num_nodes, device=x.device).unsqueeze(0).repeat(2, 1)
        edge_index_with_self_loops = torch.cat([edge_index, self_loop_edges], dim=1)

        for i, conv in enumerate(self.convs):
            agg = torch.zeros_like(x)
            agg.index_add_(0, edge_index_with_self_loops[0], x[edge_index_with_self_loops[1]])
            deg = torch.bincount(edge_index_with_self_loops[0], minlength=num_nodes).unsqueeze(1).float() + 1e-8
            agg = agg / deg

            x = conv(x + agg)
            if i < len(self.convs) - 1:
                x = self.dropout_layer(F.relu(x))

        return x


# ── Step 5: InfoNCE loss (ported verbatim from graphsage_wrapper._info_nce_loss) ──
def _info_nce_loss(embeddings, edge_index, tau=TAU, num_negatives=None):
    num_nodes, num_edges = embeddings.size(0), edge_index.size(1)

    if num_edges == 0:
        return torch.tensor(0.0, device=embeddings.device, requires_grad=True)

    src, dst = edge_index[0], edge_index[1]
    pos_sim = F.cosine_similarity(embeddings[src], embeddings[dst], dim=1)

    if num_negatives is None:
        num_negatives = num_edges * 2
    neg_src = torch.randint(0, num_nodes, (num_negatives,), device=embeddings.device)
    neg_dst = torch.randint(0, num_nodes, (num_negatives,), device=embeddings.device)
    neg_sim = F.cosine_similarity(embeddings[neg_src], embeddings[neg_dst], dim=1)

    pos_loss = -torch.log(torch.exp(pos_sim / tau).mean() + 1e-8)
    neg_loss = torch.log(torch.exp(neg_sim / tau).mean() + 1e-8)
    return pos_loss + neg_loss


# ── Step 6: Training loop (ported from graphsage_wrapper.train, contrastive path) ──
def train_graphsage(node_features, edge_index, num_epochs=100, learning_rate=0.01,
                    edge_dropout=EDGE_DROPOUT, seed=SEED, device=None):
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(seed)
    np.random.seed(seed)
    logger.info("Training device: %s", device)

    model = GraphSAGE(input_dim=node_features.shape[1], hidden_dim=EMBEDDING_DIM,
                      num_layers=NUM_LAYERS, dropout=DROPOUT).to(device)

    features_tensor = torch.FloatTensor(node_features).to(device)
    edge_index_tensor = torch.LongTensor(edge_index).to(device)

    if edge_dropout > 0:
        mask = torch.rand(edge_index_tensor.shape[1], device=device) > edge_dropout
        edge_index_tensor = edge_index_tensor[:, mask]

    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    model.train()
    for epoch in range(num_epochs):
        optimizer.zero_grad()
        loss = _info_nce_loss(model(features_tensor, edge_index_tensor), edge_index_tensor)
        loss.backward()
        optimizer.step()
        if epoch % 20 == 0:
            logger.info(f"Epoch {epoch}, Loss (contrastive): {loss.item():.4f}")

    model.eval()
    logger.info("GraphSAGE training completed (loss_type=contrastive)")
    return model


# ── Step 7: Forward + normalize (port of export compute_embeddings / wrapper L196) ──
def compute_embeddings(model, node_features, edge_index, device):
    features_tensor = torch.FloatTensor(node_features).to(device)
    edge_index_tensor = torch.LongTensor(edge_index).to(device)

    with torch.no_grad():
        normalized = F.normalize(model(features_tensor, edge_index_tensor), p=2, dim=1)

    return normalized.cpu().numpy()


# ── Step 8: Validation (ported from export validate; raises on failure) ──
def validate(embeddings, node_ids, expected_node_count=EXPECTED_CATALOG_SIZE):
    results = {}

    results["shape"] = list(embeddings.shape)
    results["expected_shape"] = [len(node_ids), EMBEDDING_DIM]
    results["shape_ok"] = embeddings.shape == (len(node_ids), EMBEDDING_DIM)

    results["dtype"] = str(embeddings.dtype)
    results["node_count"] = len(node_ids)
    results["unique_node_count"] = len(set(node_ids))
    results["no_duplicates"] = len(node_ids) == len(set(node_ids))
    results["catalog_size_ok"] = len(node_ids) == expected_node_count

    nan_count = int(np.sum(np.isnan(embeddings)))
    inf_count = int(np.sum(~np.isfinite(embeddings)))
    results["nan_count"], results["inf_count"] = nan_count, inf_count
    results["no_nan"], results["no_inf"] = nan_count == 0, inf_count == 0

    norms = np.linalg.norm(embeddings, axis=1)
    results["l2_norm_min"] = round(float(np.min(norms)), 6)
    results["l2_norm_max"] = round(float(np.max(norms)), 6)
    results["l2_norm_mean"] = round(float(np.mean(norms)), 6)
    near_one = int(np.sum((norms > 0.999) & (norms < 1.001)))
    results["rows_near_unit_norm"] = near_one
    results["all_normalized"] = near_one == len(node_ids)

    results["all_checks_passed"] = bool(all([
        results["shape_ok"], results["no_duplicates"], results["catalog_size_ok"],
        results["no_nan"], results["no_inf"], results["all_normalized"],
    ]))

    # Convert numpy types to native Python for JSON serialization
    for k, v in results.items():
        if isinstance(v, (np.integer,)):
            results[k] = int(v)
        elif isinstance(v, (np.floating,)):
            results[k] = float(v)
        elif isinstance(v, (np.bool_,)):
            results[k] = bool(v)

    if not results["all_checks_passed"]:
        raise RuntimeError("Validation FAILED — artifact not saved: " + json.dumps(results))
    return results


# ── Step 9: Save artifacts ──
def save_artifacts(embeddings, node_ids, validation, device, source_catalog=CATALOG_PATH,
                   num_epochs=100):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", DATA_DIR.resolve())

    np.save(OUTPUT_EMBEDDINGS_PATH, embeddings)
    logger.info("Saved: %s (%.2f MB)", OUTPUT_EMBEDDINGS_PATH.name, embeddings.nbytes / 1024 / 1024)

    with open(OUTPUT_IDS_PATH, "w") as f:
        json.dump(node_ids, f)
    logger.info("Saved: %s (%d ids)", OUTPUT_IDS_PATH.name, len(node_ids))

    git_hash = "unknown"
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            git_hash = result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    metadata = {
        "artifact_name": "node_embeddings_jaccard.npy",
        "description": "L2-normalized GraphSAGE-Jaccard embeddings for Phase 7 centroid retrieval",
        "training": {
            "method": "inline (checkpoint unrecoverable — trained from scratch by this script)",
            "loss": "InfoNCE contrastive", "num_epochs": num_epochs, "learning_rate": 0.01,
            "seed": SEED, "graph_threshold": JACCARD_THRESHOLD, "graph_k": JACCARD_K,
        },
        "source_catalog": str(source_catalog),
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

    with open(OUTPUT_METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved: %s", OUTPUT_METADATA_PATH.name)
    return metadata


# ── Main ──
def main():
    parser = argparse.ArgumentParser(description="Regenerate GraphSAGE-Jaccard embeddings into backend/app/data/.")
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs (default: 100)")
    parser.add_argument("--text-model", default=TEXT_MODEL_DEFAULT,
                        help=f"SentenceTransformer model (default: {TEXT_MODEL_DEFAULT})")
    parser.add_argument("--skip-text", action="store_true",
                        help="Skip text embedding regeneration if text_embeddings.npy exists")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("GraphSAGE-Jaccard Embedding Regeneration")
    logger.info("=" * 60)

    if not CATALOG_PATH.exists():
        logger.error("Catalog not found at %s", CATALOG_PATH)
        sys.exit(1)

    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = json.load(f)

    logger.info("Loaded %d fragrances from %s", len(catalog), CATALOG_PATH)
    if len(catalog) != EXPECTED_CATALOG_SIZE:
        logger.warning("WARNING: expected %d fragrances from the cleaned catalog, got %d. "
                       "Embeddings will not match the committed artifacts.",
                       EXPECTED_CATALOG_SIZE, len(catalog))

    # Step 1: text embeddings (cached to skip the model download on re-runs)
    text_embeddings = load_or_generate_text_embeddings(
        catalog, model_name=args.text_model, output_path=TEXT_EMBEDDINGS_PATH, skip_text=args.skip_text)
    logger.info("Text embeddings: shape=%s dtype=%s", text_embeddings.shape, text_embeddings.dtype)

    # Step 2: features (node order = catalog order)
    node_features, node_ids = build_features(catalog, text_embeddings)
    logger.info("Model input dimension: %d", node_features.shape[1])

    # Step 3: Jaccard graph
    edge_index, nid2idx, _idx2nid = build_jaccard_graph(catalog, node_ids)
    assert node_features.shape[0] == len(node_ids) == len(nid2idx), (
        f"Size mismatch: features={node_features.shape[0]}, node_ids={len(node_ids)}, graph={len(nid2idx)}")

    # Step 4-7: train inline, forward, normalize, validate (raises on failure)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = train_graphsage(node_features, edge_index, num_epochs=args.epochs, device=device)
    embeddings = compute_embeddings(model, node_features, edge_index, device)

    validation = validate(embeddings, node_ids, expected_node_count=len(catalog))
    logger.info("Validation results:")
    for key, val in validation.items():
        logger.info("  %s: %s", key, val)

    # Step 8: save
    metadata = save_artifacts(embeddings, node_ids, validation, device,
                              source_catalog=CATALOG_PATH, num_epochs=args.epochs)

    logger.info("=" * 60)
    logger.info("Export complete")
    logger.info("  node_embeddings_jaccard.npy:  %s", OUTPUT_EMBEDDINGS_PATH)
    logger.info("  node_ids_jaccard.json:        %s", OUTPUT_IDS_PATH)
    logger.info("  metadata.json:                %s", OUTPUT_METADATA_PATH)
    logger.info("  all_checks_passed:            %s", validation["all_checks_passed"])
    logger.info("=" * 60)


if __name__ == "__main__":
    main()