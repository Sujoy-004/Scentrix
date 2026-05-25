"""Evaluation pipeline orchestrator: load → split → persist artifacts."""

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Dict, List
import os

import numpy as np
import pandas as pd
import torch

from ml.eval.config import EvalConfig
from ml.eval.split import ColdStartSplitter, LeaveColdOutStrategy, SplitResult
from ml.eval.metrics import MetricsWrapper
from ml.eval.aggregator import ResultsAggregator

logger = logging.getLogger(__name__)

try:
    from ml.eval.models.graphsage_wrapper import GraphSAGEWrapper
    from ml.eval.models.graph_builder import build_similarity_graph
    GRAPHSAGE_AVAILABLE = True
except ImportError as e:
    GRAPHSAGE_AVAILABLE = False
    logger.warning(f"GraphSAGE modules not available: {e}")


class EvaluationOrchestrator:
    """Coordinates full evaluation pipeline: load → split → metrics → persist.

    Pattern: composable but opinionated workflow (same as ml/pipeline/ingest.py).
    Provides programmatic API and CLI entry point (D-32).
    Accepts components via dependency injection (D-33).
    """

    def __init__(
        self,
        config: EvalConfig,
        splitter: ColdStartSplitter,
    ):
        self.config = config
        self.splitter = splitter
        self.graphsage_wrapper = None
        self.metrics_wrapper = MetricsWrapper(k_values=config.k_values)
        self.results_aggregator = ResultsAggregator()
        self._run_id: Optional[str] = None
        self._run_dir: Optional[Path] = None
        
        # Initialize GraphSAGE wrapper if enabled and available
        if getattr(config, 'graphsage_enabled', False) and GRAPHSAGE_AVAILABLE:
            self.graphsage_wrapper = GraphSAGEWrapper(
                embedding_dim=getattr(config, 'graphsage_embedding_dim', 64),
                num_layers=getattr(config, 'graphsage_num_layers', 2),
                dropout=getattr(config, 'graphsage_dropout', 0.1),
                edge_dropout=getattr(config, 'graphsage_edge_dropout', 0.1),
                tau=getattr(config, 'graphsage_tau', 0.5),
                loss_type=getattr(config, 'graphsage_loss_type', 'contrastive'),
            )

    def run(self) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._run_id = timestamp
        run_dir = Path(self.config.output_dir) / timestamp
        (run_dir / "splits").mkdir(parents=True, exist_ok=True)
        (run_dir / "metrics").mkdir(parents=True, exist_ok=True)
        (run_dir / "metadata").mkdir(parents=True, exist_ok=True)
        (run_dir / "logs").mkdir(parents=True, exist_ok=True)
        self._run_dir = run_dir

        logger.info("Loading data from %s...", self.config.data_path)
        df = self._load_data()

        logger.info("Applying split (strategy: %s)...", self.config.split_strategy)
        split_result = self.splitter.split(df, self.config)
        if split_result is None:
            raise RuntimeError("Split returned None — check strategy configuration")

        self._save_splits(split_result, run_dir)
        self._save_config(run_dir)
        self._save_metadata(run_dir, split_result)

        # Run GraphSAGE evaluation if enabled and available
        graphsage_results = {}
        if self.graphsage_wrapper is not None:
            logger.info("Running GraphSAGE evaluation...")
            try:
                fragrance_ids = df["fragrance_id"].tolist()
                logger.info(f"Building similarity graph for {len(fragrance_ids)} nodes...")
                edge_index, edge_scores, node_id_to_idx, idx_to_node_id = build_similarity_graph(
                    fragrance_ids=fragrance_ids,
                    embeddings_path="ml/data/embeddings.npy",
                    embedding_index_path="ml/data/embedding_index.json",
                    k=self.config.graphsage_knn_k,
                    threshold=self.config.graphsage_similarity_threshold,
                )
                logger.info(f"Graph built: {edge_index.shape[1]} edges")

                node_features, node_ids = self._build_features(df)
                logger.info(f"Features assembled: {node_features.shape}")

                warm_ids = split_result.warm_items
                cold_ids = split_result.cold_items
                warm_idx = [node_id_to_idx[nid] for nid in warm_ids if nid in node_id_to_idx]
                cold_idx = [node_id_to_idx[nid] for nid in cold_ids if nid in node_id_to_idx]
                logger.info(f"Warm nodes: {len(warm_idx)}, Cold nodes: {len(cold_idx)}")

                warm_node_set = set(warm_idx)
                warm_edge_mask = np.array([
                    edge_index[0, i] in warm_node_set and edge_index[1, i] in warm_node_set
                    for i in range(edge_index.shape[1])
                ])
                warm_edge_index = edge_index[:, warm_edge_mask] if edge_index.shape[1] > 0 else edge_index
                logger.info(f"Warm-subgraph edges: {warm_edge_index.shape[1]}")

                if node_features.shape[0] < 2:
                    logger.warning("Too few nodes for GraphSAGE — skipping")
                    graphsage_results = {"graphsage_enabled": True, "status": "skipped", "reason": "too_few_nodes"}
                elif edge_index.shape[1] == 0:
                    logger.warning("Graph has no edges — all nodes treated as degree-0 cold")
                    self.graphsage_wrapper.node_features = torch.FloatTensor(node_features).to(self.graphsage_wrapper.device)
                    self.graphsage_wrapper.node_ids = node_ids
                    self.graphsage_wrapper.is_trained = True
                    predictions = self.graphsage_wrapper.predict_cold_start(
                        node_features=node_features,
                        edge_index=edge_index,
                        train_node_ids=[node_ids[i] for i in warm_idx],
                        test_node_ids=[node_ids[i] for i in cold_idx],
                        k=self.config.k_values[0],
                    )
                    ground_truth = self._build_ground_truth(cold_ids, node_ids, edge_index, node_id_to_idx)
                    metrics = self.metrics_wrapper.compute_all(predictions, ground_truth)
                    self.results_aggregator.add_model_results("graphsage", metrics)
                    graphsage_results = {
                        "graphsage_enabled": True,
                        "status": "success",
                        "metrics": metrics,
                        "mode": "feature_only",
                    }
                elif warm_edge_index.shape[1] == 0:
                    logger.warning("Warm subgraph has no edges — training skipped, using feature-only fallback")
                    self.graphsage_wrapper.is_trained = True
                    predictions = self.graphsage_wrapper.predict_cold_start(
                        node_features=node_features,
                        edge_index=edge_index,
                        train_node_ids=[node_ids[i] for i in warm_idx],
                        test_node_ids=[node_ids[i] for i in cold_idx],
                        k=self.config.k_values[0],
                    )
                    ground_truth = self._build_ground_truth(cold_ids, node_ids, edge_index, node_id_to_idx)
                    metrics = self.metrics_wrapper.compute_all(predictions, ground_truth)
                    self.results_aggregator.add_model_results("graphsage", metrics)
                    graphsage_results = {
                        "graphsage_enabled": True,
                        "status": "success",
                        "metrics": metrics,
                        "mode": "warm_no_edges_feature_only",
                    }
                else:
                    device = self.graphsage_wrapper.device

                    self.graphsage_wrapper.train(
                        node_features=node_features,
                        edge_index=warm_edge_index,
                        node_ids=node_ids,
                        num_epochs=self.config.graphsage_epochs,
                        learning_rate=self.config.graphsage_learning_rate,
                    )

                    predictions = self.graphsage_wrapper.predict_cold_start(
                        node_features=node_features,
                        edge_index=edge_index,
                        train_node_ids=[node_ids[i] for i in warm_idx],
                        test_node_ids=[node_ids[i] for i in cold_idx],
                        k=self.config.k_values[0],
                    )

                    ground_truth = self._build_ground_truth(cold_ids, node_ids, edge_index, node_id_to_idx)
                    metrics = self.metrics_wrapper.compute_all(predictions, ground_truth)
                    logger.info(f"GraphSAGE metrics: {metrics}")
                    self.results_aggregator.add_model_results("graphsage", metrics)

                    model_path = run_dir / "models"
                    model_path.mkdir(exist_ok=True)
                    self.graphsage_wrapper.save(str(model_path / "graphsage_model.pt"))

                    features_tensor = torch.FloatTensor(node_features).to(device)
                    edge_index_tensor = torch.LongTensor(edge_index).to(device)
                    self.graphsage_wrapper.model.eval()
                    with torch.no_grad():
                        node_embeddings = self.graphsage_wrapper.model(features_tensor, edge_index_tensor).cpu().numpy()
                    np.save(model_path / "node_embeddings.npy", node_embeddings)
                    np.save(model_path / "edge_index.npy", edge_index)
                    with open(model_path / "node_ids.json", "w") as f:
                        json.dump(node_ids, f)

                    graphsage_results = {
                        "graphsage_enabled": True,
                        "status": "success",
                        "metrics": metrics,
                        "model_path": str(model_path),
                        "mode": "contrastive",
                    }

            except Exception as e:
                logger.warning(f"GraphSAGE evaluation failed: {e}", exc_info=True)
                graphsage_results = {"graphsage_enabled": True, "status": "failed", "error": str(e)}
        else:
            graphsage_results = {"graphsage_enabled": False}

        logger.info(
            "Pipeline complete. Run directory: %s (warm=%d, cold=%d)",
            run_dir, len(split_result.warm_items), len(split_result.cold_items),
        )

        result = {
            "run_id": self._run_id,
            "run_dir": str(run_dir),
            "warm_count": len(split_result.warm_items),
            "cold_count": len(split_result.cold_items),
        }
        
        # Add GraphSAGE results if available
        if graphsage_results:
            result.update(graphsage_results)
            
        return result

    def _load_data(self) -> pd.DataFrame:
        data_path = Path(self.config.data_path)
        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = []
        for item in data:
            accords = item.get("accords", [])
            if not accords:
                logger.warning(
                    "Item %s has empty accords — primary_accord will be 'Unknown'",
                    item.get("id", "UNKNOWN"),
                )
            records.append({
                "fragrance_id": item["id"],
                "primary_accord": accords[0] if accords else "Unknown",
            })

        return pd.DataFrame(records)

    def _build_features(self, df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
        embeddings = np.load("ml/data/embeddings.npy")
        with open("ml/data/embedding_index.json", "r") as f:
            embedding_index = json.load(f)

        all_accords = sorted(df["primary_accord"].unique())
        accord_to_idx = {a: i for i, a in enumerate(all_accords)}

        node_features_list = []
        node_ids = []

        for _, row in df.iterrows():
            fragrance_id = row["fragrance_id"]
            if fragrance_id not in embedding_index:
                logger.warning(f"Fragrance {fragrance_id} not in embedding index — skipping")
                continue

            accord = row.get("primary_accord", "Unknown")
            accord_vec = np.zeros(len(all_accords), dtype=np.float32)
            if accord in accord_to_idx:
                accord_vec[accord_to_idx[accord]] = 1.0

            emb_idx = embedding_index[fragrance_id]
            emb_vec = embeddings[emb_idx].astype(np.float32)

            feature_vec = np.concatenate([accord_vec, emb_vec])
            node_features_list.append(feature_vec)
            node_ids.append(fragrance_id)

        return np.array(node_features_list, dtype=np.float32), node_ids

    def _build_ground_truth(
        self,
        cold_ids: list[str],
        node_ids: list[str],
        full_edge_index: np.ndarray,
        node_id_to_idx: dict[str, int],
    ) -> dict[str, set[str]]:
        ground_truth = {}
        for cold_id in cold_ids:
            if cold_id not in node_id_to_idx:
                continue
            idx = node_id_to_idx[cold_id]
            neighbor_mask = (full_edge_index[0] == idx) | (full_edge_index[1] == idx)
            neighbor_indices = np.unique(np.concatenate([
                full_edge_index[0, neighbor_mask],
                full_edge_index[1, neighbor_mask],
            ]))
            neighbor_ids = [node_ids[n] for n in neighbor_indices if node_ids[n] != cold_id]
            ground_truth[cold_id] = set(neighbor_ids)
        return ground_truth

    def _save_splits(self, split_result: SplitResult, run_dir: Path) -> None:
        split_result.warm_df.to_csv(
            run_dir / "splits" / "warm_items.csv", index=False
        )
        split_result.cold_df.to_csv(
            run_dir / "splits" / "cold_items.csv", index=False
        )
        logger.info(
            "Saved splits: %d warm, %d cold",
            len(split_result.warm_items), len(split_result.cold_items),
        )

    def _save_config(self, run_dir: Path) -> None:
        import yaml
        config_dict = self.config.model_dump()
        with open(run_dir / "config.yaml", "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False)

    def _save_metadata(self, run_dir: Path, split_result: SplitResult) -> None:
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_hash": git_hash,
            "warm_count": len(split_result.warm_items),
            "cold_count": len(split_result.cold_items),
            "config_snapshot": self.config.model_dump(),
        }
        with open(run_dir / "metadata" / "run.json", "w") as f:
            json.dump(metadata, f, indent=2, default=str)


def run_evaluation(
    config_path: Optional[Path] = None,
    cold_ratio: Optional[float] = None,
    seed: Optional[int] = None,
) -> dict[str, Any]:
    if config_path:
        config = EvalConfig.from_yaml(Path(config_path))
    else:
        config = EvalConfig()

    if cold_ratio is not None:
        config.cold_ratio = cold_ratio
    if seed is not None:
        config.seed = seed

    strategy = LeaveColdOutStrategy(seed=config.seed)
    splitter = ColdStartSplitter(strategy=strategy)
    orchestrator = EvaluationOrchestrator(config=config, splitter=splitter)

    return orchestrator.run()


# --- CLI Entry Point ---

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Run Scentrix cold-start evaluation pipeline."
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to YAML configuration file (optional — uses defaults if omitted)",
    )
    parser.add_argument(
        "--cold-ratio",
        type=float,
        default=None,
        help="Override cold_ratio (e.g., 0.3 for 30%% cold items)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override random seed for reproducibility",
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help="Override path to cleaned fragrance JSON",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Override output directory for run artifacts",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug-level logging",
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        config = EvalConfig.from_yaml(Path(args.config)) if args.config else EvalConfig()

        if args.cold_ratio is not None:
            config.cold_ratio = args.cold_ratio
        if args.seed is not None:
            config.seed = args.seed
        if args.data_path is not None:
            config.data_path = args.data_path
        if args.output_dir is not None:
            config.output_dir = args.output_dir

        strategy = LeaveColdOutStrategy(seed=config.seed)
        splitter = ColdStartSplitter(strategy=strategy)
        orchestrator = EvaluationOrchestrator(config=config, splitter=splitter)
        result = orchestrator.run()

        print(json.dumps(result, indent=2))
        logger.info("Evaluation complete. Run ID: %s", result["run_id"])

    except Exception as e:
        logger.error("Evaluation failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
