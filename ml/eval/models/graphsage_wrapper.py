import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class GraphSAGEWrapper:
    def __init__(
        self,
        embedding_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.1,
        edge_dropout: float = 0.1,
        tau: float = 0.5,
        loss_type: str = "contrastive",
        device: str = None,
    ):
        self.embedding_dim = embedding_dim
        self.num_layers = num_layers
        self.dropout = dropout
        self.edge_dropout = edge_dropout
        self.tau = tau
        self.loss_type = loss_type
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.model = None
        self.node_features = None
        self.node_ids = None
        self.is_trained = False

    def _build_model(self, input_dim: int):
        self.model = GraphSAGE(
            input_dim=input_dim,
            hidden_dim=self.embedding_dim,
            num_layers=self.num_layers,
            dropout=self.dropout,
        ).to(self.device)

    def _info_nce_loss(
        self,
        embeddings: torch.Tensor,
        edge_index: torch.Tensor,
        num_negatives: Optional[int] = None,
    ) -> torch.Tensor:
        num_nodes = embeddings.size(0)
        num_edges = edge_index.size(1)

        if num_edges == 0:
            return torch.tensor(0.0, device=self.device, requires_grad=True)

        src, dst = edge_index[0], edge_index[1]
        pos_sim = F.cosine_similarity(embeddings[src], embeddings[dst], dim=1)

        if num_negatives is None:
            num_negatives = num_edges * 2

        neg_src = torch.randint(0, num_nodes, (num_negatives,), device=self.device)
        neg_dst = torch.randint(0, num_nodes, (num_negatives,), device=self.device)
        neg_sim = F.cosine_similarity(embeddings[neg_src], embeddings[neg_dst], dim=1)

        pos_sim = pos_sim / self.tau
        neg_sim = neg_sim / self.tau

        pos_loss = -torch.log(torch.exp(pos_sim).mean() + 1e-8)
        neg_loss = torch.log(torch.exp(neg_sim).mean() + 1e-8)

        return pos_loss + neg_loss

    def _reconstruction_loss(
        self, embeddings: torch.Tensor, node_features: torch.Tensor
    ) -> torch.Tensor:
        pred_features = F.linear(embeddings, torch.randn_like(embeddings.T, device=self.device))
        return F.mse_loss(pred_features, node_features)

    def train(
        self,
        node_features: np.ndarray,
        edge_index: np.ndarray,
        node_ids: List[str],
        num_epochs: int = 100,
        learning_rate: float = 0.01,
        loss_type: Optional[str] = None,
    ):
        self.node_features = torch.FloatTensor(node_features).to(self.device)
        self.node_ids = node_ids

        if self.model is None:
            self._build_model(input_dim=node_features.shape[1])

        edge_index_tensor = torch.LongTensor(edge_index).to(self.device)

        if self.edge_dropout > 0:
            num_edges = edge_index_tensor.shape[1]
            mask = torch.rand(num_edges, device=self.device) > self.edge_dropout
            edge_index_tensor = edge_index_tensor[:, mask]

        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        effective_loss_type = loss_type or self.loss_type

        self.model.train()
        for epoch in range(num_epochs):
            optimizer.zero_grad()

            embeddings = self.model(self.node_features, edge_index_tensor)

            if effective_loss_type == "contrastive":
                loss = self._info_nce_loss(embeddings, edge_index_tensor)
            else:
                loss = self._reconstruction_loss(embeddings, self.node_features)

            loss.backward()
            optimizer.step()

            if epoch % 20 == 0:
                logger.info(f"Epoch {epoch}, Loss ({effective_loss_type}): {loss.item():.4f}")

        self.is_trained = True
        logger.info(f"GraphSAGE training completed (loss_type={effective_loss_type})")

    def predict(
        self,
        node_features: np.ndarray,
        edge_index: np.ndarray,
        node_ids: List[str],
        k: int = 10,
    ) -> Dict[str, List[Tuple[str, float]]]:
        if not self.is_trained:
            raise RuntimeError("Model must be trained before making predictions")

        self.model.eval()
        with torch.no_grad():
            features_tensor = torch.FloatTensor(node_features).to(self.device)
            edge_index_tensor = torch.LongTensor(edge_index).to(self.device)

            embeddings = self.model(features_tensor, edge_index_tensor)

            embeddings_norm = F.normalize(embeddings, p=2, dim=1)
            similarity_matrix = torch.mm(embeddings_norm, embeddings_norm.transpose(0, 1))
            similarity_matrix = similarity_matrix.cpu().numpy()

            recommendations = {}
            for i, node_id in enumerate(node_ids):
                sim_scores = similarity_matrix[i]
                sim_scores[i] = -np.inf
                top_k_indices = np.argsort(sim_scores)[::-1][:k]
                top_k_scores = sim_scores[top_k_indices]
                top_k_node_ids = [node_ids[idx] for idx in top_k_indices]
                recommendations[node_id] = list(zip(top_k_node_ids, top_k_scores.tolist()))

        return recommendations

    def predict_cold_start(
        self,
        node_features: np.ndarray,
        edge_index: np.ndarray,
        train_node_ids: List[str],
        test_node_ids: List[str],
        k: int = 10,
    ) -> Dict[str, List[Tuple[str, float]]]:
        if not self.is_trained:
            raise RuntimeError("Model must be trained before making predictions")

        node_id_to_idx = {nid: i for i, nid in enumerate(self.node_ids)}
        train_idx = [node_id_to_idx[nid] for nid in train_node_ids if nid in node_id_to_idx]
        test_idx = [node_id_to_idx[nid] for nid in test_node_ids if nid in node_id_to_idx]

        edge_index_tensor = torch.LongTensor(edge_index).to(self.device)
        node_degrees = torch.zeros(len(self.node_ids), device=self.device)
        node_degrees.index_add_(0, edge_index_tensor[0], torch.ones(edge_index_tensor.shape[1], device=self.device))
        node_degrees = node_degrees.cpu().numpy()

        cold_degree_zero = [i for i in test_idx if node_degrees[i] == 0]
        cold_with_edges = [i for i in test_idx if node_degrees[i] > 0]

        if cold_degree_zero:
            logger.info(f"Degree-0 cold nodes: {len(cold_degree_zero)} — using feature-only fallback")

        if cold_with_edges:
            logger.info(f"Cold nodes with edges: {len(cold_with_edges)} — using inductive inference")

        features_tensor = torch.FloatTensor(node_features).to(self.device)

        self.model.eval()
        with torch.no_grad():
            if cold_with_edges:
                embeddings = self.model(features_tensor, edge_index_tensor)
                embeddings_norm = F.normalize(embeddings, p=2, dim=1)
                similarity_matrix = torch.mm(embeddings_norm, embeddings_norm.transpose(0, 1))
                similarity_matrix = similarity_matrix.cpu().numpy()

                cold_start_preds = {}
                for idx in cold_with_edges:
                    node_id = self.node_ids[idx]
                    sim_scores = similarity_matrix[idx]
                    sim_scores[idx] = -np.inf
                    top_k_indices = np.argsort(sim_scores)[::-1][:k]
                    top_k_scores = sim_scores[top_k_indices]
                    top_k_node_ids = [self.node_ids[ni] for ni in top_k_indices]
                    cold_start_preds[node_id] = list(zip(top_k_node_ids, top_k_scores.tolist()))
            else:
                cold_start_preds = {}

            if cold_degree_zero:
                features_norm = F.normalize(features_tensor, p=2, dim=1)
                feature_sim_matrix = torch.mm(features_norm, features_norm.transpose(0, 1)).cpu().numpy()

                for idx in cold_degree_zero:
                    node_id = self.node_ids[idx]
                    sim_scores = feature_sim_matrix[idx]
                    sim_scores[idx] = -np.inf
                    top_k_indices = np.argsort(sim_scores)[::-1][:k]
                    top_k_scores = sim_scores[top_k_indices]
                    top_k_node_ids = [self.node_ids[ni] for ni in top_k_indices]
                    cold_start_preds[node_id] = list(zip(top_k_node_ids, top_k_scores.tolist()))

        return cold_start_preds

    def save(self, filepath: str):
        if not self.is_trained:
            raise RuntimeError("Model must be trained before saving")

        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "embedding_dim": self.embedding_dim,
                "num_layers": self.num_layers,
                "dropout": self.dropout,
                "edge_dropout": self.edge_dropout,
                "tau": self.tau,
                "loss_type": self.loss_type,
                "node_ids": self.node_ids,
            },
            filepath,
        )
        logger.info(f"Model saved to {filepath}")

    def load(self, filepath: str, input_dim: int):
        checkpoint = torch.load(filepath, map_location=self.device)

        self.embedding_dim = checkpoint["embedding_dim"]
        self.num_layers = checkpoint["num_layers"]
        self.dropout = checkpoint["dropout"]
        self.edge_dropout = checkpoint["edge_dropout"]
        self.tau = checkpoint.get("tau", 0.5)
        self.loss_type = checkpoint.get("loss_type", "contrastive")
        self.node_ids = checkpoint["node_ids"]

        self._build_model(input_dim=input_dim)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.is_trained = True

        logger.info(f"Model loaded from {filepath}")


class GraphSAGE(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int, dropout: float = 0.1):
        super(GraphSAGE, self).__init__()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout

        self.convs = nn.ModuleList()
        self.convs.append(nn.Linear(input_dim, hidden_dim))

        for _ in range(num_layers - 1):
            self.convs.append(nn.Linear(hidden_dim, hidden_dim))

        self.convs.append(nn.Linear(hidden_dim, hidden_dim))

        self.dropout_layer = nn.Dropout(dropout)

    def forward(self, x, edge_index):
        num_nodes = x.size(0)

        if edge_index.numel() == 0 or edge_index.shape[1] == 0:
            logger.warning("Empty edge_index in GraphSAGE forward — returning zero-centered embeddings")
            for conv in self.convs:
                x = conv(x)
                x = F.relu(x)
                x = self.dropout_layer(x)
            return x

        self_loop_edges = torch.arange(num_nodes, device=x.device).unsqueeze(0).repeat(2, 1)
        edge_index_with_self_loops = torch.cat([edge_index, self_loop_edges], dim=1)

        for i, conv in enumerate(self.convs):
            agg = torch.zeros_like(x)
            agg.index_add_(0, edge_index_with_self_loops[0], x[edge_index_with_self_loops[1]])
            deg = torch.bincount(edge_index_with_self_loops[0], minlength=num_nodes).unsqueeze(1).float() + 1e-8
            agg = agg / deg

            combined = x + agg
            x = conv(combined)

            if i < len(self.convs) - 1:
                x = F.relu(x)
                x = self.dropout_layer(x)

        return x
