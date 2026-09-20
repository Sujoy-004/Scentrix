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

Fixes applied vs the recovered original (root causes documented in the task):
  (A) build_features: the primary-accord one-hot is scaled (~0.2) and the 384-d
      text block is L2-normalized first, so the accord spike no longer dominates
      the text signal -> same-accord items keep real within-accord structure
      instead of collapsing to near-duplicate vectors.
  (B) build_jaccard_graph: emits BOTH (i,j) and (j,i) so message passing is
      undirected and catalog-order-invariant (previously messages only flowed
      from higher->lower catalog index).
  (C) _info_nce_loss: now a properly ANCHORED InfoNCE: for each directed edge
      (i->j) the positive is bob j, negatives are sampled (without replacement,
      excluding the anchor/positive) from the GLOBAL node pool; a small
      uniformity (off-diagonal-Gram) term discourages collapse.
  (D) validate: extended with semantic quality gates (rounded-duplicate rows,
      within-vs-cross cosine separation + non-collapse bound, isolated-node
      fraction, catalog-order invariance self-check).
  (E) text-embedding cache is keyed by a CONTENT hash of the serialized catalog
      (and the text model name), not just matrix shape.
  (F) metadata.json gains catalog_sha256, text_model, reproducibility info and
      the train loss / semantic-gate numbers.
"""

import argparse
import hashlib
import importlib.metadata
import json
import logging
import math
import os
import random
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
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
TEXT_EMBEDDINGS_HASH_PATH = DATA_DIR / "text_embeddings.hash.json"
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

# (A) feature construction: accord one-hot is scaled so the 384-d text block
# (L2-normalized to unit norm) dominates in magnitude while the accord signal
# still separates families; see build_features().
ACCORD_SCALE = 0.2

# (C) anchored InfoNCE negative sampling / anti-collapse term.
# UNIFORM_REG_LAMBDA: weight of the log-sum-exp uniformity term (repels close
# pairs on the unit sphere — the centering-only closed form was useless here,
# so the full Gram is used). ANCHOR_REG_LAMBDA: weight of an optional per-node
# feature-anchor term (0 = disabled; a naive anchor collapses the projector).
DEFAULT_NUM_NEGATIVES = 64
NEGATIVE_SAMPLING_CHUNK = 8192
UNIFORM_REG_LAMBDA = 1.0
UNIFORM_TEMPERATURE = 0.5
ANCHOR_REG_LAMBDA = 0.0

# (D) semantic validation gates.
SEMANTIC_ROUND_DECIMALS = 6
SEMANTIC_WITHIN_CROSS_MAX_PAIRS = 2000
SEMANTIC_WITHIN_COLLAPSE_BOUND = 0.98
SEMANTIC_ISOLATED_FRACTION_BOUND = 0.25
SEMANTIC_ORDER_INVARIANCE_MAX_DIFF = 1e-3
SEMANTIC_ORDER_INVARIANCE_SUBSAMPLE = 500

_ATOMIC_JSON_INDENT = 2


# ── Atomic writes (another process may read the artifacts while we write) ──
def _atomic_npy_save(target_path, array):
    target_path = Path(target_path)
    directory = target_path.parent
    fd, tmp = tempfile.mkstemp(dir=str(directory), prefix=target_path.name + ".", suffix=".npy")
    os.close(fd)
    try:
        np.save(tmp, array)
        os.replace(tmp, str(target_path))
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def _atomic_json_write(target_path, obj):
    target_path = Path(target_path)
    directory = target_path.parent
    fd, tmp = tempfile.mkstemp(dir=str(directory), prefix=target_path.name + ".", suffix=".json")
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=_ATOMIC_JSON_INDENT)
        os.replace(tmp, str(target_path))
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


# ── Catalog content hash (cache invalidation + metadata) ──
def catalog_content_hash(catalog):
    """Deterministic sha256 of the serialized catalog (canonical key order)."""
    return hashlib.sha256(json.dumps(catalog, sort_keys=True).encode("utf-8")).hexdigest()


# ── Step 1: Text embeddings (ported from generate_embeddings.py encode step) ─
def generate_text_embeddings(catalog, model_name=TEXT_MODEL_DEFAULT, output_path=TEXT_EMBEDDINGS_PATH):
    from sentence_transformers import SentenceTransformer

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Initializing SentenceTransformer model: %s...", model_name)
    model = SentenceTransformer(model_name)

    texts = []
    for item in catalog:
        notes = " ".join(item.get("top_notes", []) or [])
        accords = " ".join(item.get("accords", []) or [])
        texts.append(f"{item.get('name','')} {item.get('brand','')} {notes} {accords} {item.get('category','')}".strip())

    logger.info("Generating text embeddings for %d items (this may take a few minutes)...", len(texts))
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True).astype(np.float32)

    _atomic_npy_save(output_path, embeddings)
    logger.info("Saved text embeddings: %s", output_path)
    return embeddings


def load_or_generate_text_embeddings(catalog, model_name=TEXT_MODEL_DEFAULT,
                                     output_path=TEXT_EMBEDDINGS_PATH, skip_text=False):
    """Load cached text embeddings if they match the *content hash* of the
    catalog and the requested model; otherwise regenerate.

    (E) The cache is keyed by sha256(json.dumps(catalog, sort_keys=True)) and the
    text-model name, not merely by shape, so a changed catalog or model
    transparently triggers regeneration.
    """
    output_path = Path(output_path)
    hash_path = output_path.with_name("text_embeddings.hash.json")
    current_hash = catalog_content_hash(catalog)

    cached_meta = {}
    if hash_path.exists():
        try:
            with open(hash_path, encoding="utf-8") as f:
                cached_meta = json.load(f)
        except (json.JSONDecodeError, OSError):
            cached_meta = {}

    cache_valid = False
    if output_path.exists():
        shape_matches = False
        try:
            embeddings = np.load(output_path)
            shape_matches = embeddings.shape == (len(catalog), TEXT_EMBEDDING_DIM)
        except (OSError, ValueError):
            shape_matches = False
        if shape_matches:
            if cached_meta.get("catalog_sha256") != current_hash:
                logger.warning(
                    "Cached text embeddings are stale (catalog sha256 %s != %s) — regenerating",
                    cached_meta.get("catalog_sha256"), current_hash)
            elif cached_meta.get("text_model") != model_name:
                logger.warning(
                    "Cached text embeddings were produced by '%s', requested '%s' — regenerating",
                    cached_meta.get("text_model"), model_name)
            else:
                cache_valid = True
        else:
            logger.warning("Cached embeddings shape %s does not match (%d, %d) — regenerating",
                           embeddings.shape if shape_matches else "unreadable", len(catalog), TEXT_EMBEDDING_DIM)

    if cache_valid:
        logger.info("Loading cached text embeddings: %s (catalog sha256 %s, model %s)",
                    output_path, current_hash, model_name)
        return embeddings.astype(np.float32)

    if skip_text:
        raise RuntimeError(f"--skip-text set but cache not found for catalog hash {current_hash} "
                           f"at {output_path}")

    embeddings = generate_text_embeddings(catalog, model_name=model_name, output_path=output_path)
    payload = {
        "catalog_sha256": current_hash,
        "catalog_size": len(catalog),
        "text_model": model_name,
        "text_embedding_dim": int(embeddings.shape[1]),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    _atomic_json_write(hash_path, payload)
    logger.info("Saved text-embedding cache manifest: %s", hash_path)
    return embeddings


# ── Step 2: Feature construction (FIX A: comparable accord + text signals) ──
def build_features(catalog, text_embeddings, accord_scale=ACCORD_SCALE, feature_source="full"):
    """Concatenate scaled primary-accord one-hot + L2-normalized text block.

    Old behaviour concatenated a full-magnitude (1.0) accord one-hot directly
    with the raw 384-d text block: the accord spike dominated the text, so
    same-accord items collapsed into near-duplicate vectors (measured within-
    accord median cosine 0.9923, 34 duplicate rows).

    New behaviour: the text row is L2-normalized to unit norm first, and the
    accord one-hot is scaled by ACCORD_SCALE (~0.2) and placed BEFORE it. The
    resulting feature norm is ~sqrt(1 + 0.2^2); the accord signal separates
    families while the text signal retains real within-accord structure.

    ``feature_source`` selects the input-signal ablation:
      full  = accord block + text block (the shipped artifact),
      text  = text block only  (tests the purely semantic signal),
      graph = accord block only (tests the purely structural signal).
    In the graph-only case ``text_embeddings`` may be None (it is unused).
    """
    primary_accords_set, records = set(), []
    for item in catalog:
        accords = item.get("accords") or []
        primary = str(accords[0]).lower() if accords else "Unknown"  # "Unknown" casing kept from original
        primary_accords_set.add(primary)
        records.append({"fragrance_id": str(item["id"]), "primary_accord": primary})
    all_accords = sorted(primary_accords_set)
    accord_to_idx = {a: i for i, a in enumerate(all_accords)}
    logger.info("Accord vocabulary: %d unique primary accords", len(all_accords))

    if text_embeddings is not None:
        text = text_embeddings.astype(np.float32)
        text_norms = np.linalg.norm(text, axis=1, keepdims=True)
        text_norm = text / np.maximum(text_norms, 1e-8)
        logger.info("Text block norms before normalize: min=%.4f max=%.4f mean=%.4f",
                    float(text_norms.min()), float(text_norms.max()), float(text_norms.mean()))
    else:
        logger.info("feature_source=%s: text block unused", feature_source)
        text_norm = None

    # Embeddings are regenerated in catalog order, so positional pairing replaces
    # the original embedding_index.json lookup.
    node_features_list, node_ids = [], []
    zipped = zip(records, text_norm, strict=False) if text_norm is not None else (
        (r, None) for r in records
    )
    for row, emb_norm in zipped:
        accord_vec = np.zeros(len(all_accords), dtype=np.float32)
        accord = row["primary_accord"]
        if accord in accord_to_idx:
            accord_vec[accord_to_idx[accord]] = 1.0
        accord_block = accord_vec * accord_scale
        if feature_source == "graph":
            node_features_list.append(accord_block)
        elif feature_source == "text":
            node_features_list.append(emb_norm)
        else:
            node_features_list.append(np.concatenate([accord_block, emb_norm]))
        node_ids.append(row["fragrance_id"])

    features = np.array(node_features_list, dtype=np.float32)
    f_norms = np.linalg.norm(features, axis=1)
    logger.info("Features assembled: shape=%s, dtype=%s", features.shape, features.dtype)
    logger.info("Feature-vector norm distribution: min=%.4f max=%.4f mean=%.4f std=%.4f",
                float(f_norms.min()), float(f_norms.max()), float(f_norms.mean()), float(f_norms.std()))
    return features, node_ids


# ── Step 3: Jaccard edge index (FIX B: undirected message passing) ──
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
    idx_to_node_id = dict(enumerate(local_ids))

    if len(local_ids) < 2:
        raise RuntimeError("Too few nodes for Jaccard graph")

    n = len(local_ids)
    all_scores = [[] for _ in range(n)]
    for i in range(n):
        _, notes_i, accord_i = local_ids[i], note_sets[local_ids[i]], primary_accords[local_ids[i]]
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

    # Build a symmetric (undirected) edge set: the pair (i,j) is an edge iff the
    # Jaccard threshold passed AND each side kept the other in its top-k list.
    # This is catalog-order-invariant.
    undirected = set()
    for i, neighbors in enumerate(all_scores):
        for j, _ in neighbors:
            undirected.add((i, j) if i < j else (j, i))
    undirected_list = sorted(undirected)

    if not undirected_list:
        raise RuntimeError("No edges passed Jaccard threshold")

    # (B) EMIT BOTH DIRECTIONS: each undirected edge becomes (i,j) and (j,i) so
    # aggregation is symmetric and independent of catalog ordering.
    directed_list = []
    for i, j in undirected_list:
        directed_list.append((i, j))
        directed_list.append((j, i))

    edge_index = np.array(directed_list, dtype=np.int64).T
    logger.info("Jaccard graph built: %d nodes, %d undirected edges, %d directed pairs",
                n, len(undirected_list), edge_index.shape[1])
    return edge_index, node_id_to_idx, idx_to_node_id


# ── Step 4: GraphSAGE (ported verbatim from graphsage_wrapper.py:GraphSAGE) ──
class GraphSAGE(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, dropout=0.1):
        super().__init__()
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


# ── Step 5: anchored InfoNCE loss (FIX C) ──
def _sample_negatives(num_nodes, src, dst, k, device):
    """Sample *k* negatives per edge, without replacement, excluding the anchor
    (src) and the positive (dst).

    Sampling uses the GLOBAL node pool (all num_nodes), not a mini-batch. The
    anchor/positive are excluded by rejection so no accidental positives leak
    into the negatives.
    """
    c = src.shape[0]
    if k <= 0 or num_nodes <= 2:
        return torch.zeros((c, 1), dtype=torch.long, device=device)

    neg = torch.randint(0, num_nodes, (c, k), device=device)
    for col in range(k):
        while True:
            ok = (neg[:, col] != src) & (neg[:, col] != dst)
            if col > 0:
                ok = ok & ~(neg[:, :col] == neg[:, col:col + 1]).any(dim=1)
            if bool(ok.all()):
                break
            bad = (~ok).nonzero(as_tuple=False).squeeze(1)
            neg[bad, col] = torch.randint(0, num_nodes, (int(bad.numel()),), device=device)
    return neg


def _info_nce_loss(embeddings, edge_index, tau=TAU, num_negatives=None,
                   uniform_lambda=UNIFORM_REG_LAMBDA, uniform_temperature=UNIFORM_TEMPERATURE):
    """Anchored InfoNCE (NT-Xent style) over the directed edge set.

    For each directed edge (i -> j): anchor = node i, positive = bob j,
    negatives = k nodes sampled WITHOUT replacement from the GLOBAL node pool
    (excluding the anchor and the positive, so no accidental positives). The
    returned loss is the mean per-edge cross-entropy over [positive + negatives]
    logits plus a small uniformity term, log-mean-exp over all pairwise cosine
    similarities, which penalizes representation collapse (its gradient repels
    close pairs; a plain mean-Gram term degenerates to mean-centring).

    API preserved: _info_nce_loss(embeddings, edge_index, tau=...) -> scalar.
    """
    num_nodes, num_edges = embeddings.size(0), edge_index.size(1)

    if num_edges == 0:
        return torch.tensor(0.0, device=embeddings.device, requires_grad=True)

    if num_negatives is None:
        num_negatives = DEFAULT_NUM_NEGATIVES
    num_negatives = min(int(num_negatives), max(1, num_nodes - 2))

    embed = F.normalize(embeddings, p=2, dim=1)  # scale-invariant, matches final artifact
    src, dst = edge_index[0], edge_index[1]

    total_nce = torch.tensor(0.0, device=embeddings.device)
    for start in range(0, num_edges, NEGATIVE_SAMPLING_CHUNK):
        c_src, c_dst = src[start:start + NEGATIVE_SAMPLING_CHUNK], dst[start:start + NEGATIVE_SAMPLING_CHUNK]
        anchors, positives = embed[c_src], embed[c_dst]
        neg = _sample_negatives(num_nodes, c_src, c_dst, num_negatives, embeddings.device)
        neg_emb = embed[neg]  # (C, k, d)

        pos_logits = (anchors * positives).sum(dim=1) / tau                       # (C,)
        neg_logits = torch.einsum("cd,ckd->ck", anchors, neg_emb) / tau           # (C, k)
        logits = torch.cat([pos_logits.unsqueeze(1), neg_logits], dim=1)          # (C, 1+k)
        labels = torch.zeros(logits.shape[0], dtype=torch.long, device=embeddings.device)
        total_nce = total_nce + F.cross_entropy(logits, labels)

    nce = total_nce / num_edges

    # Uniformity anti-collapse term (Wang & Isola style): gradient repels EVERY
    # pair proportionally to exp(cos/temperature), which is what breaks the
    # within-accord collapse (dense same-accord edges otherwise merge a family
    # into a single point). Uses the full Gram, so cost is O(N^2).
    n = embed.shape[0]
    if n > 1 and uniform_lambda > 0:
        gram = embed @ embed.t()
        off_diag = gram.flatten()[~torch.eye(n, dtype=torch.bool, device=embeddings.device).flatten()]
        uniformity = torch.logsumexp(off_diag / uniform_temperature, dim=0) - math.log(n * (n - 1))
    else:
        uniformity = torch.zeros((), device=embeddings.device)
    return nce + uniform_lambda * uniformity


# ── Step 6: Training loop (FIX: per-epoch edge dropout, seeded, anti-collapse) ──
def train_graphsage(node_features, edge_index, num_epochs=100, learning_rate=0.01,
                    edge_dropout=EDGE_DROPOUT, seed=SEED, device=None,
                    uniform_lambda=UNIFORM_REG_LAMBDA, anchor_lambda=ANCHOR_REG_LAMBDA):
    """Train GraphSAGE with anchored InfoNCE + anti-collapse regularization.

    Loss = _info_nce_loss(embeddings, edge_index, uniform_lambda=uniform_lambda)
         + anchor_lambda * mean(1 - cos(model(x_i), h(norm(x_i))))   # optional

    The anchored InfoNCE pulls graph-adjacent (Jaccard-similar) items together;
    its log-sum-exp uniformity term repels every pair, preventing the dense
    same-accord edges from collapsing a whole accord family into one point
    (measured without it: within-primary median cosine ~0.999). The optional
    anchor_lambda term pulls each node toward its own text-driven feature
    direction via a linear projector h and defaults to 0 (disabled).

    Edge dropout is applied INSIDE the training loop (fresh mask every epoch);
    the full graph is always used for the final forward/validation
    (compute_embeddings / validate), so train and eval see consistent graphs.
    All random sources are seeded for reproducibility.
    """
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    logger.info("Training device: %s", device)

    model = GraphSAGE(input_dim=node_features.shape[1], hidden_dim=EMBEDDING_DIM,
                      num_layers=NUM_LAYERS, dropout=DROPOUT).to(device)

    features_tensor = torch.FloatTensor(node_features).to(device)
    edge_full = torch.LongTensor(edge_index).to(device)

    optimizer_params = list(model.parameters())
    norm_features = None
    anchor_head = None
    if anchor_lambda > 0:
        anchor_head = nn.Linear(node_features.shape[1], EMBEDDING_DIM).to(device)
        optimizer_params += list(anchor_head.parameters())
        norm_features = F.normalize(features_tensor, p=2, dim=1)

    optimizer = torch.optim.Adam(optimizer_params, lr=learning_rate)
    loss_curve = []

    model.train()
    if anchor_head is not None:
        anchor_head.train()
    for epoch in range(num_epochs):
        optimizer.zero_grad()
        edge_epoch = edge_full.clone()
        if edge_dropout > 0:
            mask = torch.rand(edge_epoch.shape[1], device=device) > edge_dropout
            if mask.any():
                edge_epoch = edge_epoch[:, mask]
            else:
                edge_epoch = edge_full  # never train on a fully dropped graph

        embeddings = model(features_tensor, edge_epoch)
        nce_loss = _info_nce_loss(embeddings, edge_epoch, uniform_lambda=uniform_lambda)
        if anchor_lambda > 0 and anchor_head is not None:
            head_out = F.normalize(anchor_head(norm_features), p=2, dim=1)
            anchor_loss = torch.mean(1.0 - F.cosine_similarity(F.normalize(embeddings, p=2, dim=1), head_out, dim=1))
        else:
            anchor_loss = torch.zeros((), device=device)
        loss = nce_loss + anchor_lambda * anchor_loss
        loss.backward()
        optimizer.step()
        loss_curve.append(float(loss.item()))
        if epoch % 20 == 0 or epoch == num_epochs - 1:
            logger.info(f"Epoch {epoch}, Loss: {loss.item():.4f} "
                        f"(nce={nce_loss.item():.4f}, anchor={anchor_loss.item():.4f})")

    model.eval()
    logger.info("GraphSAGE training completed (loss_type=anchored_info_nce+uniform_reg, "
                "final loss=%.4f, min loss=%.4f)", loss_curve[-1], min(loss_curve))
    return model, loss_curve


# ── Step 7: Forward + normalize (port of export compute_embeddings / wrapper L196) ──
def compute_embeddings(model, node_features, edge_index, device):
    model.eval()
    features_tensor = torch.FloatTensor(node_features).to(device)
    edge_index_tensor = torch.LongTensor(edge_index).to(device)

    with torch.no_grad():
        normalized = F.normalize(model(features_tensor, edge_index_tensor), p=2, dim=1)

    return normalized.cpu().numpy()


# ── Step 7b: catalog-order invariance self-check (FIX D) ──
def check_order_invariance(model, node_features, edge_index, device,
                           subsample_nodes=SEMANTIC_ORDER_INVARIANCE_SUBSAMPLE,
                           max_abs_diff=SEMANTIC_ORDER_INVARIANCE_MAX_DIFF, seed=SEED):
    """Verify the GraphSAGE forward path is catalog-order invariant.

    A fixed subsample of feature rows is swapped via a permutation p
    (identity elsewhere); the edge indices are remapped through p. Embeddings
    are recomputed for the permuted features/graph and mapped back to the
    original rows. If aggregation secretly depended on row order the recovered
    embeddings would drift; we assert max abs diff < 1e-3.
    """
    n = node_features.shape[0]
    rng = np.random.default_rng(seed + 1)
    subsample = min(int(subsample_nodes), n)
    chosen = rng.choice(n, size=subsample, replace=False)
    shuffled = chosen.copy()
    rng.shuffle(shuffled)

    p = np.arange(n)          # p[i] = the ORIGINAL row now placed at new row i
    p[chosen] = shuffled
    p_inv = np.empty_like(p)
    p_inv[p] = np.arange(n)   # inverse permutation

    # features_perm[i] holds the feature of original row p[i]; to keep the graph
    # consistent each edge endpoint u must be moved to its new row p^{-1}(u).
    features_perm = node_features[p]
    edge_perm = p_inv[edge_index]

    base = compute_embeddings(model, node_features, edge_index, device)      # O
    perm = compute_embeddings(model, features_perm, edge_perm, device)       # O'
    recovered = np.empty_like(perm)
    recovered[p] = perm                                                     # recovered[p[i]] = O'[i] = O[p[i]]

    check = np.abs(recovered - base)
    max_diff = float(np.max(check[chosen]))
    passed = max_diff <= max_abs_diff
    logger.info("Order-invariance self-check: subsample=%d max_abs_diff=%.3e passed=%s",
                subsample, max_diff, passed)
    return {
        "order_invariance_max_abs_diff": max_diff,
        "order_invariance_subsample_size": int(subsample),
        "order_invariance_passed": bool(passed),
    }


# ── Semantic-quality helpers (FIX D) ──
def rounded_duplicate_stats(embeddings, decimals=SEMANTIC_ROUND_DECIMALS):
    """Count embedding rows identical to 6 decimal places."""
    rounded = np.round(embeddings, decimals)
    _, counts = np.unique(rounded, axis=0, return_counts=True)
    dup_rows = int(np.sum(counts > 1))
    return {"rounded_duplicate_rows": dup_rows, "no_rounded_duplicates": dup_rows == 0}


def semantic_separation_stats(embeddings, catalog, max_pairs=SEMANTIC_WITHIN_CROSS_MAX_PAIRS,
                              seed=SEED):
    """Median cosine within primary accord vs across primary accord.

    Samples at most `max_pairs` within-primary pairs and `max_pairs` cross-primary
    pairs (deterministic given seed). Returns medians + sampled counts.
    """
    primaries = []
    for item in catalog:
        accords = item.get("accords") or []
        primaries.append(str(accords[0]).lower() if accords else "Unknown")
    by_accord = {}
    for i, acc in enumerate(primaries):
        by_accord.setdefault(acc, []).append(i)
    accords = [acc for acc in by_accord if len(by_accord[acc]) >= 2]

    rng = np.random.default_rng(seed)
    within_sims, cross_sims = [], []

    for acc in accords:
        idxs = np.asarray(by_accord[acc], dtype=np.int64)
        perm = rng.permutation(len(idxs))
        perm = perm[: (len(perm) // 2) * 2]
        pairs = perm.reshape(-1, 2)
        for a, b in pairs:
            i, j = int(idxs[a]), int(idxs[b])
            within_sims.append(float(np.dot(embeddings[i], embeddings[j])))
            if len(within_sims) >= max_pairs:
                break
        if len(within_sims) >= max_pairs:
            break

    attempts = 0
    max_attempts = max(int(max_pairs * 100), 100_000)
    while len(cross_sims) < max_pairs and attempts < max_attempts and len(accords) >= 2:
        attempts += 1
        a1, a2 = rng.choice(len(accords), size=2, replace=False)
        i = int(rng.choice(np.asarray(by_accord[accords[int(a1)]])))
        j = int(rng.choice(np.asarray(by_accord[accords[int(a2)]])))
        cross_sims.append(float(np.dot(embeddings[i], embeddings[j])))

    within_median = float(np.median(within_sims)) if within_sims else float("nan")
    cross_median = float(np.median(cross_sims)) if cross_sims else float("nan")
    return {
        "within_primary_similarity_median": within_median,
        "cross_primary_similarity_median": cross_median,
        "within_primary_pairs_sampled": len(within_sims),
        "cross_primary_pairs_sampled": len(cross_sims),
    }


def isolated_node_stats(edge_index, num_nodes):
    """Report how many nodes have zero incident edges (fully isolated)."""
    if edge_index is None or getattr(edge_index, "size", 0) == 0:
        return {"isolated_node_count": int(num_nodes), "isolated_node_fraction": 1.0}
    touched = {int(v) for v in np.unique(edge_index)}
    count = int(num_nodes - len(touched))
    return {"isolated_node_count": count, "isolated_node_fraction": float(count / num_nodes)}


_VALIDATION_GATE_KEYS = [
    "shape_ok", "no_duplicates", "catalog_size_ok", "no_nan", "no_inf", "all_normalized",
    "no_rounded_duplicates", "semantic_separation_ok", "within_not_collapsed",
    "isolated_fraction_ok", "order_invariance_passed",
]


def finalize_validation_results(results):
    """Recompute all_checks_passed from the boolean gate keys present in results."""
    present = [k for k in _VALIDATION_GATE_KEYS if k in results]
    results["all_checks_passed"] = all(bool(results[k]) for k in present)
    return results


# ── Step 8: Validation (FIX D — structural + semantic quality gates) ──
def validate(embeddings, node_ids, expected_node_count=EXPECTED_CATALOG_SIZE,
             catalog=None, edge_index=None, relaxed=False):
    """Validate embeddings; raises RuntimeError on any gate failure.

    Structural checks (existing): shape, dtype, no duplicates in node ids,
    catalog size, no NaN/Inf, L2 unit norms.
    Semantic checks (new):
      - rounded-duplicate rows (6 dp) must be 0;
      - within-primary median cosine > cross-primary median, and
        within-primary median < 0.98 (structured, not collapsed);
      - isolated-node fraction < 0.25.

    ``relaxed=True`` (ablation runs) logs gate failures instead of raising —
    graph-only/text-only input ablations legitimately violate the collapse gates.
    """
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

    # Semantic gates (FIX D)
    results.update(rounded_duplicate_stats(embeddings))
    if catalog is not None:
        results.update(semantic_separation_stats(embeddings, catalog))
        results["semantic_separation_ok"] = bool(
            results["within_primary_similarity_median"] > results["cross_primary_similarity_median"])
        results["within_not_collapsed"] = bool(
            results["within_primary_similarity_median"] < SEMANTIC_WITHIN_COLLAPSE_BOUND)
    else:
        results["semantic_separation_ok"] = True
        results["within_not_collapsed"] = True

    if edge_index is not None:
        results.update(isolated_node_stats(edge_index, len(node_ids)))
    else:
        results["isolated_node_count"] = None
        results["isolated_node_fraction"] = None
    results["isolated_fraction_ok"] = bool(
        results.get("isolated_node_fraction") is not None
        and results["isolated_node_fraction"] < SEMANTIC_ISOLATED_FRACTION_BOUND)

    results = finalize_validation_results(results)

    # Convert numpy types to native Python for JSON serialization
    for k, v in results.items():
        if isinstance(v, (np.integer,)):
            results[k] = int(v)
        elif isinstance(v, (np.floating,)):
            results[k] = float(v)
        elif isinstance(v, (np.bool_,)):
            results[k] = bool(v)

    if not results["all_checks_passed"]:
        if relaxed:
            logger.warning("Validation gates failed (relaxed mode): %s", json.dumps(results))
        else:
            raise RuntimeError("Validation FAILED — artifact not saved: " + json.dumps(results))
    return results


# ── Step 9: Save artifacts (atomic os.replace to avoid torn reads) ──
def save_artifacts(embeddings, node_ids, validation, device, source_catalog=CATALOG_PATH,
                   num_epochs=100, catalog_sha256=None, text_model=None,
                   train_loss_curve_min=None, output_dir=None, feature_source="full"):
    output_dir = Path(output_dir) if output_dir is not None else DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", output_dir.resolve())

    emb_path = output_dir / OUTPUT_EMBEDDINGS_PATH.name
    ids_path = output_dir / OUTPUT_IDS_PATH.name
    meta_path = output_dir / OUTPUT_METADATA_PATH.name

    _atomic_npy_save(emb_path, embeddings)
    logger.info("Saved: %s (%.2f MB)", emb_path.name, embeddings.nbytes / 1024 / 1024)

    _atomic_json_write(ids_path, node_ids)
    logger.info("Saved: %s (%d ids)", ids_path.name, len(node_ids))

    git_hash = "unknown"
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            git_hash = result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    try:
        numpy_version = np.__version__
        torch_version = torch.__version__
        python_version = sys.version.split()[0]
        text_model_version = importlib.metadata.version("sentence-transformers")
    except Exception:
        numpy_version, torch_version, python_version, text_model_version = "unknown", "unknown", "unknown", "unknown"

    metadata = {
        "artifact_name": "node_embeddings_jaccard.npy",
        "description": "L2-normalized GraphSAGE-Jaccard embeddings for Phase 7 centroid retrieval",
        "training": {
            "method": "inline (checkpoint unrecoverable — trained from scratch by this script)",
            "loss": "anchored InfoNCE: per-edge positive (neighbor bob) with per-edge negatives "
                    "sampled without replacement from the global node pool + small off-diagonal "
                    "Gram uniformity term (anti-collapse)",
            "num_epochs": num_epochs, "learning_rate": 0.01,
            "seed": SEED, "graph_threshold": JACCARD_THRESHOLD, "graph_k": JACCARD_K,
            "tau": TAU, "edge_dropout": EDGE_DROPOUT,
            "num_negatives": DEFAULT_NUM_NEGATIVES,
            "uniform_reg_lambda": UNIFORM_REG_LAMBDA,
            "train_loss_curve_min": train_loss_curve_min,
        },
        "feature_construction": {
            "accord_scale": ACCORD_SCALE,
            "text_block": "L2-normalized before concatenation",
            "feature_source": feature_source,
            "feature_dim": int(embeddings.shape[1]),
        },
        "source_catalog": str(source_catalog),
        "catalog_sha256": catalog_sha256,
        "text_model": text_model,
        "export_timestamp": datetime.now(UTC).isoformat(),
        "node_count": len(node_ids),
        "embedding_dimension": int(embeddings.shape[1]),
        "graph_threshold": JACCARD_THRESHOLD,
        "graph_k": JACCARD_K,
        "normalization": "L2 (F.normalize, p=2, dim=1)",
        "normalization_location": "post-forward-pass, before save (replicating graphsage_wrapper.py L196)",
        "device": device,
        "git_commit_hash": git_hash,
        "reproducibility": {
            "seed": SEED,
            "numpy_version": numpy_version,
            "torch_version": torch_version,
            "python_version": python_version,
            "sentence_transformers_version": text_model_version,
        },
        "validation": validation,
    }

    _atomic_json_write(meta_path, metadata)
    logger.info("Saved: %s", meta_path.name)
    return metadata


# ── Main ──
def main():
    parser = argparse.ArgumentParser(description="Regenerate GraphSAGE-Jaccard embeddings into backend/app/data/.")
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs (default: 100)")
    parser.add_argument("--text-model", default=TEXT_MODEL_DEFAULT,
                        help=f"SentenceTransformer model (default: {TEXT_MODEL_DEFAULT})")
    parser.add_argument("--skip-text", action="store_true",
                        help="Skip text embedding regeneration if text_embeddings.npy exists")
    parser.add_argument("--feature-source", default="full", choices=("full", "text", "graph"),
                        help="Input-signal ablation: full (accord+text), text only, or graph (accord only). "
                        "graph needs no text embeddings (skips the MiniLM download).")
    parser.add_argument("--output", type=Path, default=None,
                        help="Optional output dir for node_embeddings_jaccard.npy + node_ids_jaccard.json. "
                        "Defaults to backend/app/data (overwrites the shipped artifacts).")
    parser.add_argument("--ablation", action="store_true",
                        help="Ablation mode: graph/text-only variants legitimately violate the semantic "
                        "collapse gates, so validation failure is logged, not fatal.")
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

    catalog_sha256 = catalog_content_hash(catalog)
    logger.info("Catalog content sha256: %s", catalog_sha256)

    # Step 1: text embeddings (cached by content hash to skip the model download on re-runs)
    if args.feature_source == "graph":
        text_embeddings = None
        logger.info("feature_source=graph: text embeddings not needed (no MiniLM download)")
    else:
        text_embeddings = load_or_generate_text_embeddings(
            catalog, model_name=args.text_model, output_path=TEXT_EMBEDDINGS_PATH, skip_text=args.skip_text)
        logger.info("Text embeddings: shape=%s dtype=%s", text_embeddings.shape, text_embeddings.dtype)

    # Step 2: features (node order = catalog order)
    node_features, node_ids = build_features(catalog, text_embeddings, feature_source=args.feature_source)
    logger.info("Model input dimension: %d", node_features.shape[1])

    # Step 3: Jaccard graph (both directions — undirected message passing)
    edge_index, nid2idx, _idx2nid = build_jaccard_graph(catalog, node_ids)
    assert node_features.shape[0] == len(node_ids) == len(nid2idx), (
        f"Size mismatch: features={node_features.shape[0]}, node_ids={len(node_ids)}, graph={len(nid2idx)}")

    # Step 4-7: train inline, forward, normalize, validate (raises on failure)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, loss_curve = train_graphsage(node_features, edge_index, num_epochs=args.epochs, device=device)
    embeddings = compute_embeddings(model, node_features, edge_index, device)

    # Catalog-order invariance self-check (uses the trained model).
    order_invariance = check_order_invariance(model, node_features, edge_index, device)

    validation = validate(embeddings, node_ids, expected_node_count=len(catalog),
                          catalog=catalog, edge_index=edge_index, relaxed=args.ablation)
    validation.update(order_invariance)
    validation = finalize_validation_results(validation)
    if not validation["all_checks_passed"]:
        if args.ablation:
            logger.warning("Validation FAILED but --ablation set (expected for signal ablations): %s",
                           json.dumps(validation))
        else:
            raise RuntimeError("Validation FAILED after order-invariance self-check: " + json.dumps(validation))

    logger.info("Validation results:")
    for key, val in validation.items():
        logger.info("  %s: %s", key, val)

    # Step 8: save (atomic)
    output_dir = args.output if args.output is not None else DATA_DIR
    save_artifacts(embeddings, node_ids, validation, device,
                   source_catalog=CATALOG_PATH, num_epochs=args.epochs,
                   catalog_sha256=catalog_sha256, text_model=args.text_model,
                   train_loss_curve_min=min(loss_curve) if loss_curve else None,
                   output_dir=output_dir, feature_source=args.feature_source)

    # Step 9: reload the saved artifacts and re-run validate + semantic gates on the FILE.
    logger.info("Re-loading saved artifacts for post-save validation...")
    reloaded_embeddings = np.load(output_dir / OUTPUT_EMBEDDINGS_PATH.name)
    with open(output_dir / OUTPUT_IDS_PATH.name, encoding="utf-8") as f:
        reloaded_node_ids = json.load(f)
    post_validation = validate(reloaded_embeddings, reloaded_node_ids,
                               expected_node_count=len(catalog), catalog=catalog, edge_index=edge_index,
                               relaxed=args.ablation)
    logger.info("Post-save validation on reloaded artifact: all_checks_passed=%s",
                post_validation["all_checks_passed"])

    logger.info("=" * 60)
    logger.info("Export complete")
    logger.info("  node_embeddings_jaccard.npy:  %s", output_dir / OUTPUT_EMBEDDINGS_PATH.name)
    logger.info("  node_ids_jaccard.json:        %s", output_dir / OUTPUT_IDS_PATH.name)
    logger.info("  metadata.json:                %s", output_dir / OUTPUT_METADATA_PATH.name)
    logger.info("  all_checks_passed:            %s", validation["all_checks_passed"])
    logger.info("  catalog_sha256:               %s", catalog_sha256)
    logger.info("  text_model:                   %s", args.text_model)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
