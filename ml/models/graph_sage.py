import json
import logging
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch
from torch_geometric.data import Data
from torch_geometric.nn import SAGEConv
import torch.nn.functional as F
from pinecone import Pinecone, ServerlessSpec

logger = logging.getLogger(__name__)

class GraphSAGEModel(torch.nn.Module):
    def __init__(self, in_channels: int, hidden_channels: int = 128, out_channels: int = 384):
        super(GraphSAGEModel, self).__init__()
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.5, training=self.training)
        x = self.conv2(x, edge_index)
        return x

class GraphEmbedder:
    def __init__(self, dim: int = 384):
        self.dim = dim
        pinecone_api_key = os.environ.get("PINECONE_API_KEY")
        if pinecone_api_key and pinecone_api_key != "your_pinecone_api_key_here":
            self.pc = Pinecone(api_key=pinecone_api_key)
            self.index_name = "scentrix-graph"
            self._ensure_index()
        else:
            logger.warning("Pinecone API key not configured. Graph embeddings will not be uploaded.")
            self.pc = None

    @staticmethod
    def _normalize_year(raw_year: Any) -> float:
        """Map release year into a bounded [0, 1] range for stable model input."""
        try:
            year = int(raw_year)
        except (TypeError, ValueError):
            return 0.5

        if year < 1900:
            year = 1900
        if year > 2035:
            year = 2035
        return (year - 1900) / (2035 - 1900)

    @staticmethod
    def _normalize_concentration(raw_concentration: Any) -> float:
        """Project concentration labels onto a monotonic strength scalar."""
        text = str(raw_concentration or "").strip().lower()
        if "extrait" in text:
            return 1.0
        if "eau de parfum" in text or "edp" in text:
            return 0.8
        if "eau de toilette" in text or "edt" in text:
            return 0.6
        if "cologne" in text:
            return 0.4
        return 0.5

    @staticmethod
    def _encode_gender(raw_gender: Any) -> Tuple[float, float, float]:
        """One-hot-like representation for gender label handling unknowns robustly."""
        text = str(raw_gender or "").strip().lower()
        if text in {"male", "man", "men", "for men"}:
            return 1.0, 0.0, 0.0
        if text in {"female", "woman", "women", "for women"}:
            return 0.0, 1.0, 0.0
        if text in {"unisex", "for women and men", "both"}:
            return 0.0, 0.0, 1.0
        return 0.0, 0.0, 0.0

    def _build_node_features(self, frag: Dict[str, Any]) -> torch.Tensor:
        """Build deterministic 10-dimensional node features from canonical fragrance fields."""
        top_notes = frag.get("top_notes", []) or []
        middle_notes = frag.get("middle_notes", []) or []
        base_notes = frag.get("base_notes", []) or []
        accords = frag.get("accords", []) or []
        description = str(frag.get("description", "") or "")

        gender_m, gender_f, gender_u = self._encode_gender(frag.get("gender_label"))
        desc_len_norm = min(len(description.split()) / 120.0, 1.0)
        note_density = min((len(top_notes) + len(middle_notes) + len(base_notes)) / 24.0, 1.0)

        features = torch.tensor(
            [
                self._normalize_year(frag.get("year")),
                min(len(top_notes) / 8.0, 1.0),
                min(len(middle_notes) / 8.0, 1.0),
                min(len(base_notes) / 8.0, 1.0),
                min(len(accords) / 8.0, 1.0),
                desc_len_norm,
                note_density,
                gender_m,
                gender_f,
                max(gender_u, self._normalize_concentration(frag.get("concentration"))),
            ],
            dtype=torch.float32,
        )
        return features

    @staticmethod
    def _build_split_masks(
        num_nodes: int,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        seed: int = 42,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Create reproducible train/val/test masks across graph nodes."""
        if num_nodes <= 0:
            raise ValueError("Cannot build train/val/test split for empty graph")

        indices = list(range(num_nodes))
        random.Random(seed).shuffle(indices)

        train_count = int(num_nodes * train_ratio)
        val_count = int(num_nodes * val_ratio)

        if num_nodes >= 3:
            train_count = max(1, train_count)
            val_count = max(1, val_count)
            test_count = num_nodes - train_count - val_count
            if test_count <= 0:
                test_count = 1
                if train_count >= val_count and train_count > 1:
                    train_count -= 1
                elif val_count > 1:
                    val_count -= 1
        else:
            test_count = max(0, num_nodes - train_count - val_count)

        train_end = train_count
        val_end = train_count + val_count

        train_ids = set(indices[:train_end])
        val_ids = set(indices[train_end:val_end])
        test_ids = set(indices[val_end:])

        train_mask = torch.zeros(num_nodes, dtype=torch.bool)
        val_mask = torch.zeros(num_nodes, dtype=torch.bool)
        test_mask = torch.zeros(num_nodes, dtype=torch.bool)

        for idx in train_ids:
            train_mask[idx] = True
        for idx in val_ids:
            val_mask[idx] = True
        for idx in test_ids:
            test_mask[idx] = True

        if not train_mask.any():
            train_mask[0] = True
            if val_mask[0]:
                val_mask[0] = False
            if test_mask[0]:
                test_mask[0] = False

        return train_mask, val_mask, test_mask

    def _train_embeddings(self, data: Data, in_channels: int) -> Tuple[torch.Tensor, Dict[str, float]]:
        """Train GraphSAGE with train/val/test node split using reconstruction objective."""
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        data = data.to(device)

        model = GraphSAGEModel(in_channels=in_channels, hidden_channels=64, out_channels=self.dim).to(device)
        decoder = torch.nn.Linear(self.dim, in_channels).to(device)
        optimizer = torch.optim.Adam(
            list(model.parameters()) + list(decoder.parameters()),
            lr=0.01,
            weight_decay=5e-4,
        )

        best_val = float("inf")
        best_epoch = 0
        best_model_state = None
        best_decoder_state = None
        patience = 20

        max_epochs = 120
        for epoch in range(1, max_epochs + 1):
            model.train()
            decoder.train()
            optimizer.zero_grad()

            embeddings = model(data.x, data.edge_index)
            reconstructed = decoder(embeddings)
            train_loss = F.mse_loss(reconstructed[data.train_mask], data.x[data.train_mask])
            train_loss.backward()
            optimizer.step()

            model.eval()
            decoder.eval()
            with torch.no_grad():
                embeddings_eval = model(data.x, data.edge_index)
                reconstructed_eval = decoder(embeddings_eval)
                if data.val_mask.any():
                    val_loss = F.mse_loss(reconstructed_eval[data.val_mask], data.x[data.val_mask]).item()
                else:
                    val_loss = train_loss.item()

            if val_loss < best_val:
                best_val = val_loss
                best_epoch = epoch
                best_model_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                best_decoder_state = {k: v.detach().cpu().clone() for k, v in decoder.state_dict().items()}

            if epoch - best_epoch >= patience:
                break

        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        if best_decoder_state is not None:
            decoder.load_state_dict(best_decoder_state)

        model.eval()
        decoder.eval()
        with torch.no_grad():
            final_embeddings = model(data.x, data.edge_index)
            final_reconstructed = decoder(final_embeddings)
            if data.test_mask.any():
                test_loss = F.mse_loss(final_reconstructed[data.test_mask], data.x[data.test_mask]).item()
            else:
                test_loss = F.mse_loss(final_reconstructed, data.x).item()

        metrics = {
            "best_val_loss": float(best_val),
            "test_loss": float(test_loss),
            "epochs_trained": float(best_epoch),
        }
        return final_embeddings.cpu(), metrics

    def _ensure_index(self):
        """Ensure the Pinecone index exists, create if it doesn't."""
        existing_indexes = [index_info["name"] for index_info in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            logger.info(f"Creating Pinecone index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dim,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        self.index = self.pc.Index(self.index_name)

    def _build_graph(self, fragrances: List[Dict[str, Any]]) -> Tuple[Data, Dict[str, int]]:
        """Build PyTorch Geometric graph data from seed JSON."""
        # This graph uses deterministic catalog features so train/val/test behavior is stable across runs.
        node_features = []
        node_mapping = {}
        edge_index = [[], []]
        
        # 1. Create nodes and feature vectors
        for i, frag in enumerate(fragrances):
            node_mapping[frag["id"]] = i
            node_features.append(self._build_node_features(frag))
            
        # 2. Build edges based on shared notes (Naive approach for offline generation)
        notes_to_frags = {}
        for frag in fragrances:
            all_notes = frag.get("top_notes", []) + frag.get("middle_notes", []) + frag.get("base_notes", [])
            for note in set(all_notes):
                if note not in notes_to_frags:
                    notes_to_frags[note] = []
                notes_to_frags[note].append(frag["id"])
                
        for note, frag_ids in notes_to_frags.items():
            for i in range(len(frag_ids)):
                for j in range(i + 1, len(frag_ids)):
                    n1 = node_mapping[frag_ids[i]]
                    n2 = node_mapping[frag_ids[j]]
                    edge_index[0].extend([n1, n2])
                    edge_index[1].extend([n2, n1])

        # Add self-loops so every node participates even when shared-note edges are sparse.
        for idx in range(len(fragrances)):
            edge_index[0].append(idx)
            edge_index[1].append(idx)
                    
        x = torch.stack(node_features)
        edge_index = torch.tensor(edge_index, dtype=torch.long)
        
        return Data(x=x, edge_index=edge_index), node_mapping

    def generate_and_upload(self, fragrances: List[Dict[str, Any]]):
        """Train GraphSAGE and upload the node embeddings."""
        if not fragrances:
            logger.error("No fragrances provided for GraphSAGE generation.")
            return
            
        data, node_mapping = self._build_graph(fragrances)

        train_mask, val_mask, test_mask = self._build_split_masks(data.num_nodes)
        data.train_mask = train_mask
        data.val_mask = val_mask
        data.test_mask = test_mask

        out_embeddings, metrics = self._train_embeddings(data, in_channels=data.num_node_features)
        logger.info(
            "GraphSAGE split complete: train=%s val=%s test=%s best_val_loss=%.6f test_loss=%.6f",
            int(train_mask.sum().item()),
            int(val_mask.sum().item()),
            int(test_mask.sum().item()),
            metrics["best_val_loss"],
            metrics["test_loss"],
        )
            
        if not self.pc:
            logger.info("Graph embeddings generated successfully. Skipping Pinecone upload.")
            return
            
        vectors_to_upsert = []
        for frag in fragrances:
            n_idx = node_mapping[frag["id"]]
            emb = out_embeddings[n_idx].tolist()
            
            clean_meta = {
                "name": str(frag.get("name", "")),
                "brand": str(frag.get("brand", ""))
            }
            vectors_to_upsert.append({
                "id": frag["id"],
                "values": emb,
                "metadata": clean_meta
            })
            
        logger.info(f"Upserting {len(vectors_to_upsert)} GraphSAGE embeddings to Pinecone...")
        # Batch upsert
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i + batch_size]
            self.index.upsert(vectors=batch)
        logger.info("GraphSAGE embeddings uploaded.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    seed_path = Path(__file__).parent.parent / "data" / "scentrix_master.json"
    if seed_path.exists():
        with open(seed_path, "r", encoding="utf-8") as f:
            fragrances = json.load(f)
        
        embedder = GraphEmbedder()
        embedder.generate_and_upload(fragrances)
    else:
        logger.error("Seed fragrances data not found.")
