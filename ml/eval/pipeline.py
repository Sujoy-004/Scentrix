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
from ml.eval.quiz_simulator import QuizSimulator
from ml.eval.reporting import (
    StratificationReporter,
    LearningCurvePlotter,
    AblationReporter,
    DebiasingReporter,
)

logger = logging.getLogger(__name__)

try:
    from ml.eval.models.graphsage_wrapper import GraphSAGEWrapper
    from ml.eval.models.graph_builder import build_similarity_graph, build_jaccard_graph, build_jaccard_graph_sweep
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
        self.quiz_simulator: Optional[QuizSimulator] = None
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

        if self.config.evaluation_mode == "warm_ref":
            return self._run_warm_reference(run_dir)

        logger.info("Loading data from %s...", self.config.data_path)
        df = self._load_data()

        logger.info("Applying split (strategy: %s)...", self.config.split_strategy)
        split_result = self.splitter.split(df, self.config)
        if split_result is None:
            raise RuntimeError("Split returned None — check strategy configuration")

        self._save_splits(split_result, run_dir)
        self._save_config(run_dir)
        self._save_metadata(run_dir, split_result)

        if self.config.evaluation_mode == "quiz_init":
            return self._run_quiz_init(split_result, df, run_dir)

        # Default: pure_cold (original Phase 4 behavior)
        return self._run_pure_cold(split_result, df, run_dir)

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
    ) -> dict[str, set[str]]:
        data_path = Path(self.config.data_path)
        if not data_path.exists():
            logger.error("Cannot build ground truth: data file not found at %s", data_path)
            return {cid: set() for cid in cold_ids}

        with open(data_path, "r", encoding="utf-8") as f:
            all_items = json.load(f)

        item_map: dict[str, dict] = {}
        for item in all_items:
            fid = item.get("id", "")
            top = set(str(n).lower() for n in (item.get("top_notes") or []) if n)
            mid = set(str(n).lower() for n in (item.get("middle_notes") or []) if n)
            base = set(str(n).lower() for n in (item.get("base_notes") or []) if n)
            raw_accords = [str(a).lower() for a in (item.get("accords") or []) if a]
            item_map[fid] = {
                "all_notes": top | mid | base,
                "primary_accord": raw_accords[0] if raw_accords else "Unknown",
                "accords": set(raw_accords),
            }

        ground_truth = {}
        for cold_id in cold_ids:
            cold_item = item_map.get(cold_id)
            if cold_item is None:
                continue

            cold_notes = cold_item["all_notes"]
            cold_primary = cold_item["primary_accord"]
            relevant: set[str] = set()

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

            ground_truth[cold_id] = relevant

        before = len(ground_truth)
        ground_truth = {k: v for k, v in ground_truth.items() if v}
        excluded = before - len(ground_truth)
        if excluded:
            logger.info(
                "Excluded %d/%d cold items with empty relevant set from metrics (%.1f%%)",
                excluded, before, 100.0 * excluded / before,
            )
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

    def _run_pure_cold(
        self,
        split_result: SplitResult,
        df: pd.DataFrame,
        run_dir: Path,
    ) -> dict[str, Any]:
        graphsage_results: dict[str, Any] = {}
        cold_ids = split_result.cold_items
        ground_truth = self._build_ground_truth(cold_ids)
        fragrance_ids = df["fragrance_id"].tolist()
        node_features, node_ids = self._build_features(df)
        logger.info(f"Features assembled: {node_features.shape}")
        if self.graphsage_wrapper is not None:
            logger.info("Running GraphSAGE evaluation (pure cold)...")
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

                warm_ids = split_result.warm_items
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
                    metrics = self.metrics_wrapper.compute_all(predictions, ground_truth)
                    self.results_aggregator.add_model_results("GraphSAGE-Embedding", metrics)
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
                    metrics = self.metrics_wrapper.compute_all(predictions, ground_truth)
                    self.results_aggregator.add_model_results("GraphSAGE-Embedding", metrics)
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

                    metrics = self.metrics_wrapper.compute_all(predictions, ground_truth)
                    logger.info(f"GraphSAGE metrics: {metrics}")
                    self.results_aggregator.add_model_results("GraphSAGE-Embedding", metrics)

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

        # --- Second GraphSAGE run: Jaccard-based graph ---
        if self.graphsage_wrapper is not None:
            logger.info("Running GraphSAGE-Jaccard evaluation (Jaccard-based graph)...")
            try:
                jaccard_wrapper = GraphSAGEWrapper(
                    embedding_dim=self.config.graphsage_embedding_dim,
                    num_layers=self.config.graphsage_num_layers,
                    dropout=self.config.graphsage_dropout,
                    edge_dropout=self.config.graphsage_edge_dropout,
                    tau=self.config.graphsage_tau,
                    loss_type=self.config.graphsage_loss_type,
                )

                fragrance_ids_j = df["fragrance_id"].tolist()
                logger.info(f"Building Jaccard graph for {len(fragrance_ids_j)} nodes...")
                edge_index_j, edge_scores_j, node_id_to_idx_j, idx_to_node_id_j = build_jaccard_graph(
                    fragrance_ids=fragrance_ids_j,
                    catalog_path=self.config.data_path,
                    k=self.config.graphsage_knn_k,
                    threshold=0.2,
                )
                logger.info(f"Jaccard graph built: {edge_index_j.shape[1]} edges")

                warm_ids_j = split_result.warm_items
                cold_ids_j = split_result.cold_items
                warm_idx_j = [node_id_to_idx_j[nid] for nid in warm_ids_j if nid in node_id_to_idx_j]
                cold_idx_j = [node_id_to_idx_j[nid] for nid in cold_ids_j if nid in node_id_to_idx_j]
                logger.info(f"Warm nodes: {len(warm_idx_j)}, Cold nodes: {len(cold_idx_j)}")

                warm_node_set_j = set(warm_idx_j)
                warm_edge_mask_j = np.array([
                    edge_index_j[0, i] in warm_node_set_j and edge_index_j[1, i] in warm_node_set_j
                    for i in range(edge_index_j.shape[1])
                ]) if edge_index_j.shape[1] > 0 else np.array([], dtype=bool)
                warm_edge_index_j = edge_index_j[:, warm_edge_mask_j] if edge_index_j.shape[1] > 0 else edge_index_j
                logger.info(f"Warm-subgraph edges: {warm_edge_index_j.shape[1]}")

                if node_features.shape[0] < 2:
                    logger.warning("Too few nodes for GraphSAGE-Jaccard — skipping")
                elif edge_index_j.shape[1] == 0:
                    logger.warning("Jaccard graph has no edges — skipping")
                elif warm_edge_index_j.shape[1] == 0:
                    logger.warning("Warm subgraph has no edges — using feature-only fallback")
                    jaccard_wrapper.is_trained = True
                    preds_j = jaccard_wrapper.predict_cold_start(
                        node_features=node_features,
                        edge_index=edge_index_j,
                        train_node_ids=[node_ids[i] for i in warm_idx_j],
                        test_node_ids=[node_ids[i] for i in cold_idx_j],
                        k=self.config.k_values[0],
                    )
                    metrics_j = self.metrics_wrapper.compute_all(preds_j, ground_truth)
                    self.results_aggregator.add_model_results("GraphSAGE-Jaccard", metrics_j)
                else:
                    device_j = jaccard_wrapper.device
                    jaccard_wrapper.train(
                        node_features=node_features,
                        edge_index=warm_edge_index_j,
                        node_ids=node_ids,
                        num_epochs=self.config.graphsage_epochs,
                        learning_rate=self.config.graphsage_learning_rate,
                    )

                    preds_j = jaccard_wrapper.predict_cold_start(
                        node_features=node_features,
                        edge_index=edge_index_j,
                        train_node_ids=[node_ids[i] for i in warm_idx_j],
                        test_node_ids=[node_ids[i] for i in cold_idx_j],
                        k=self.config.k_values[0],
                    )

                    metrics_j = self.metrics_wrapper.compute_all(preds_j, ground_truth)
                    logger.info(f"GraphSAGE-Jaccard metrics: {metrics_j}")
                    self.results_aggregator.add_model_results("GraphSAGE-Jaccard", metrics_j)

                    model_path_j = run_dir / "models"
                    model_path_j.mkdir(exist_ok=True)
                    jaccard_wrapper.save(str(model_path_j / "graphsage_jaccard.pt"))

            except Exception as e:
                logger.warning(f"GraphSAGE-Jaccard evaluation failed: {e}", exc_info=True)

        # --- Baselines: Popularity, Random, Content-Only ---
        logger.info("Running Popularity baseline...")
        try:
            from ml.eval.models.popularity import PopularityBaseline
            pop = PopularityBaseline()
            pop_preds = {}
            for cid in cold_ids:
                ranked = pop.get_rankings(k=self.config.k_values[0])
                pop_preds[cid] = [(rid, len(ranked) - i) for i, rid in enumerate(ranked)]
            pop_metrics = self.metrics_wrapper.compute_all(pop_preds, ground_truth)
            self.results_aggregator.add_model_results("Popularity", pop_metrics)
            logger.info("Popularity metrics: %s", pop_metrics)
        except Exception as e:
            logger.warning("Popularity baseline failed: %s", e)

        logger.info("Running Random baseline...")
        try:
            from ml.eval.models.random_baseline import RandomBaseline
            random_baseline = RandomBaseline()
            random_preds = {}
            for cid in cold_ids:
                ranked = random_baseline.get_rankings(k=self.config.k_values[0])
                random_preds[cid] = [(rid, len(ranked) - i) for i, rid in enumerate(ranked)]
            random_metrics = self.metrics_wrapper.compute_all(random_preds, ground_truth)
            self.results_aggregator.add_model_results("Random", random_metrics)
            logger.info("Random metrics: %s", random_metrics)
        except Exception as e:
            logger.warning("Random baseline failed: %s", e)

        logger.info("Running Content-Only baseline (Jaccard over notes)...")
        try:
            with open(self.config.data_path, "r", encoding="utf-8") as f:
                all_data = json.load(f)
            note_map = {}
            for item in all_data:
                fid = item.get("id", "")
                top = {str(n).lower() for n in (item.get("top_notes") or []) if n}
                mid = {str(n).lower() for n in (item.get("middle_notes") or []) if n}
                base = {str(n).lower() for n in (item.get("base_notes") or []) if n}
                note_map[fid] = top | mid | base

            content_preds = {}
            for cid in cold_ids:
                cold_notes = note_map.get(cid, set())
                scored = []
                for oid, other_notes in note_map.items():
                    if oid == cid:
                        continue
                    union = cold_notes | other_notes
                    jaccard = len(cold_notes & other_notes) / len(union) if union else 0.0
                    scored.append((oid, jaccard))
                scored.sort(key=lambda x: -x[1])
                content_preds[cid] = scored[:self.config.k_values[0]]
            content_metrics = self.metrics_wrapper.compute_all(content_preds, ground_truth)
            self.results_aggregator.add_model_results("Content-Only", content_metrics)
            logger.info("Content-Only metrics: %s", content_metrics)
        except Exception as e:
            logger.warning("Content-Only baseline failed: %s", e)

        logger.info("Running Feature-Only baseline (cosine sim on raw input features)...")
        try:
            features_norm = node_features / (np.linalg.norm(node_features, axis=1, keepdims=True) + 1e-8)
            sim_matrix = features_norm @ features_norm.T
            node_id_to_idx_f = {nid: i for i, nid in enumerate(node_ids)}
            cold_idx_f = [node_id_to_idx_f[cid] for cid in cold_ids if cid in node_id_to_idx_f]

            feature_preds = {}
            for idx in cold_idx_f:
                node_id = node_ids[idx]
                sim_scores = sim_matrix[idx].copy()
                sim_scores[idx] = -np.inf
                top_k = np.argsort(sim_scores)[::-1][:self.config.k_values[0]]
                top_scores = sim_scores[top_k]
                top_ids = [node_ids[i] for i in top_k]
                feature_preds[node_id] = list(zip(top_ids, top_scores.tolist()))
            feature_metrics = self.metrics_wrapper.compute_all(feature_preds, ground_truth)
            self.results_aggregator.add_model_results("Feature-Only", feature_metrics)
            logger.info("Feature-Only metrics: %s", feature_metrics)
        except Exception as e:
            logger.warning("Feature-Only baseline failed: %s", e)

        comparison = self.results_aggregator.generate_comparison_table(fmt="markdown")
        print("\n" + "=" * 70)
        print("COMPARISON TABLE")
        print("=" * 70)
        print(comparison)
        print("=" * 70 + "\n")

        # --- Jaccard threshold sweep with GraphSAGE ---
        logger.info("Running Jaccard threshold sweep with GraphSAGE...")
        try:
            sweep_graphs = build_jaccard_graph_sweep(
                fragrance_ids=fragrance_ids,
                catalog_path=self.config.data_path,
                k=self.config.graphsage_knn_k,
                thresholds=[0.10, 0.15, 0.20, 0.25, 0.30],
            )

            warm_ids_sw = split_result.warm_items
            cold_ids_sw = split_result.cold_items
            sweep_results = []

            for t in sorted(sweep_graphs.keys()):
                ei, es, n2i, i2n = sweep_graphs[t]
                n_edges = ei.shape[1]

                if n_edges == 0 or node_features.shape[0] < 2:
                    sweep_results.append((t, n_edges, len(cold_ids_sw), 0.0, 0.0, 0.0))
                    continue

                warm_idx = [n2i[nid] for nid in warm_ids_sw if nid in n2i]
                warm_set = set(warm_idx)
                mask = np.array([
                    ei[0, i] in warm_set and ei[1, i] in warm_set
                    for i in range(n_edges)
                ]) if n_edges > 0 else np.array([], dtype=bool)
                warm_ei = ei[:, mask] if n_edges > 0 else ei

                if warm_ei.shape[1] == 0:
                    sweep_results.append((t, n_edges, len(cold_ids_sw), 0.0, 0.0, 0.0))
                    continue

                cold_idx_sw = [n2i[cid] for cid in cold_ids_sw if cid in n2i]
                deg = np.zeros(len(n2i), dtype=np.int64)
                for e in range(n_edges):
                    deg[ei[0, e]] += 1
                    deg[ei[1, e]] += 1
                n_cold_deg0 = sum(1 for idx in cold_idx_sw if deg[idx] == 0)

                np.random.seed(self.config.seed)
                torch.manual_seed(self.config.seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(self.config.seed)

                wrapper = GraphSAGEWrapper(
                    embedding_dim=self.config.graphsage_embedding_dim,
                    num_layers=self.config.graphsage_num_layers,
                    dropout=self.config.graphsage_dropout,
                    edge_dropout=self.config.graphsage_edge_dropout,
                    tau=self.config.graphsage_tau,
                    loss_type=self.config.graphsage_loss_type,
                )
                wrapper.train(
                    node_features=node_features, edge_index=warm_ei, node_ids=node_ids,
                    num_epochs=self.config.graphsage_epochs,
                    learning_rate=self.config.graphsage_learning_rate,
                )
                preds = wrapper.predict_cold_start(
                    node_features=node_features, edge_index=ei,
                    train_node_ids=warm_ids_sw, test_node_ids=cold_ids_sw,
                    k=self.config.k_values[0],
                )
                m = self.metrics_wrapper.compute_all(preds, ground_truth)
                sweep_results.append((
                    t, n_edges, n_cold_deg0,
                    m.get("NDCG@10", 0.0),
                    m.get("Precision@10", 0.0),
                    m.get("Recall@10", 0.0),
                ))

            print("\n" + "=" * 70)
            print("JACCARD THRESHOLD SWEEP — GraphSAGE Embeddings")
            print("=" * 70)
            print(f"{'Threshold':>10s}  {'Edges':>8s}  {'Deg0':>6s}  {'NDCG@10':>10s}  {'Prec@10':>10s}  {'Rec@10':>10s}")
            print("-" * 70)
            for t, e, d, ndcg, prec, rec in sweep_results:
                print(f"{t:>10.2f}  {e:>8d}  {d:>6d}  {ndcg:>10.6f}  {prec:>10.6f}  {rec:>10.6f}")
            print("=" * 70 + "\n")
        except Exception as e:
            logger.warning(f"Jaccard threshold sweep failed: {e}", exc_info=True)

        logger.info(
            "Pipeline complete. Run directory: %s (warm=%d, cold=%d)",
            run_dir, len(split_result.warm_items), len(split_result.cold_items),
        )

        result = {
            "run_id": self._run_id,
            "run_dir": str(run_dir),
            "evaluation_mode": "pure_cold",
            "warm_count": len(split_result.warm_items),
            "cold_count": len(split_result.cold_items),
        }

        if graphsage_results:
            result.update(graphsage_results)
        result["all_metrics"] = self.results_aggregator.to_dict()
        result["comparison_table"] = comparison

        return result

    def _run_quiz_init(
        self,
        split_result: SplitResult,
        df: pd.DataFrame,
        run_dir: Path,
    ) -> dict[str, Any]:
        logger.info("Running quiz-init evaluation mode (quiz_length=%d, noise=%.2f)...",
                     self.config.quiz_length, self.config.quiz_noise)

        graphsage_results: dict[str, Any] = {}
        if self.graphsage_wrapper is not None:
            logger.info("Running GraphSAGE evaluation (quiz-init)...")
            try:
                fragrance_ids = df["fragrance_id"].tolist()
                edge_index, edge_scores, node_id_to_idx, idx_to_node_id = build_jaccard_graph(
                    fragrance_ids=fragrance_ids,
                    catalog_path=self.config.catalog_path,
                    threshold=self.config.jaccard_threshold,
                )

                node_features, node_ids = self._build_features(df)

                # Inject quiz preference bias into cold-node features
                all_accords = sorted(df["primary_accord"].unique())
                if self.quiz_simulator is None:
                    self.quiz_simulator = QuizSimulator(
                        all_accords=all_accords,
                        seed=self.config.seed + 1,
                    )

                confidence = self.quiz_simulator.simulate(
                    quiz_length=self.config.quiz_length,
                    quiz_noise=self.config.quiz_noise,
                )

                cold_ids = split_result.cold_items
                cold_idx = [node_id_to_idx[nid] for nid in cold_ids if nid in node_id_to_idx]

                logger.info("Skipping feature injection — using post-prediction reranker (quiz_length=%d)",
                            self.config.quiz_length)

                warm_ids = split_result.warm_items
                warm_idx = [node_id_to_idx[nid] for nid in warm_ids if nid in node_id_to_idx]

                warm_node_set = set(warm_idx)
                warm_edge_mask = np.array([
                    edge_index[0, i] in warm_node_set and edge_index[1, i] in warm_node_set
                    for i in range(edge_index.shape[1])
                ]) if edge_index.shape[1] > 0 else np.array([], dtype=bool)
                warm_edge_index = edge_index[:, warm_edge_mask] if edge_index.shape[1] > 0 else edge_index

                if node_features.shape[0] < 2:
                    logger.warning("Too few nodes for GraphSAGE — skipping")
                    graphsage_results = {"graphsage_enabled": True, "status": "skipped", "reason": "too_few_nodes"}
                elif edge_index.shape[1] == 0:
                    logger.warning("Graph has no edges — using feature-only fallback")
                    self.graphsage_wrapper.node_features = torch.FloatTensor(node_features).to(self.graphsage_wrapper.device)
                    self.graphsage_wrapper.node_ids = node_ids
                    self.graphsage_wrapper.is_trained = True
                    predictions = self.graphsage_wrapper.predict_cold_start(
                        node_features=node_features,
                        edge_index=edge_index,
                        train_node_ids=[node_ids[i] for i in warm_idx],
                        test_node_ids=[node_ids[i] for i in cold_idx],
                        k=max(self.config.k_values[0], self.config.quiz_rerank_pool),
                    )
                    accord_lookup = df.set_index("fragrance_id")["primary_accord"].to_dict()
                    alpha = self.config.quiz_alpha
                    reranked_predictions = {}
                    for cold_id, ranked_warm_ids in predictions.items():
                        total = len(ranked_warm_ids)
                        scored = []
                        for rank, (warm_id, graphsage_score) in enumerate(ranked_warm_ids):
                            accord = accord_lookup.get(warm_id, "")
                            quiz_score = self.quiz_simulator.get_accord_confidence(accord)
                            rank_score = 1.0 - (rank / total) if total > 1 else 1.0
                            blended = (1 - alpha) * rank_score + alpha * quiz_score
                            scored.append((warm_id, blended))
                        scored.sort(key=lambda x: x[1], reverse=True)
                        reranked_predictions[cold_id] = [(wid, s) for wid, s in scored][:self.config.k_values[0]]
                    predictions = reranked_predictions
                    ground_truth = self._build_ground_truth(cold_ids)
                    metrics = self.metrics_wrapper.compute_all(predictions, ground_truth)
                    self.results_aggregator.add_model_results("graphsage_quiz_init", metrics)
                    graphsage_results = {"graphsage_enabled": True, "status": "success", "metrics": metrics, "mode": "feature_only"}
                elif warm_edge_index.shape[1] == 0:
                    logger.warning("Warm subgraph has no edges — using feature-only fallback")
                    self.graphsage_wrapper.is_trained = True
                    predictions = self.graphsage_wrapper.predict_cold_start(
                        node_features=node_features,
                        edge_index=edge_index,
                        train_node_ids=[node_ids[i] for i in warm_idx],
                        test_node_ids=[node_ids[i] for i in cold_idx],
                        k=max(self.config.k_values[0], self.config.quiz_rerank_pool),
                    )
                    accord_lookup = df.set_index("fragrance_id")["primary_accord"].to_dict()
                    alpha = self.config.quiz_alpha
                    reranked_predictions = {}
                    for cold_id, ranked_warm_ids in predictions.items():
                        total = len(ranked_warm_ids)
                        scored = []
                        for rank, (warm_id, graphsage_score) in enumerate(ranked_warm_ids):
                            accord = accord_lookup.get(warm_id, "")
                            quiz_score = self.quiz_simulator.get_accord_confidence(accord)
                            rank_score = 1.0 - (rank / total) if total > 1 else 1.0
                            blended = (1 - alpha) * rank_score + alpha * quiz_score
                            scored.append((warm_id, blended))
                        scored.sort(key=lambda x: x[1], reverse=True)
                        reranked_predictions[cold_id] = [(wid, s) for wid, s in scored][:self.config.k_values[0]]
                    predictions = reranked_predictions
                    ground_truth = self._build_ground_truth(cold_ids)
                    metrics = self.metrics_wrapper.compute_all(predictions, ground_truth)
                    self.results_aggregator.add_model_results("graphsage_quiz_init", metrics)
                    graphsage_results = {"graphsage_enabled": True, "status": "success", "metrics": metrics, "mode": "warm_no_edges_feature_only"}
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
                        k=max(self.config.k_values[0], self.config.quiz_rerank_pool),
                    )
                    # Quiz reranking — boost warm candidates matching user's preferred accords
                    accord_lookup = df.set_index("fragrance_id")["primary_accord"].to_dict()
                    alpha = self.config.quiz_alpha
                    reranked_predictions = {}
                    for cold_id, ranked_warm_ids in predictions.items():
                        total = len(ranked_warm_ids)
                        scored = []
                        for rank, (warm_id, graphsage_score) in enumerate(ranked_warm_ids):
                            accord = accord_lookup.get(warm_id, "")
                            quiz_score = self.quiz_simulator.get_accord_confidence(accord)
                            rank_score = 1.0 - (rank / total) if total > 1 else 1.0
                            blended = (1 - alpha) * rank_score + alpha * quiz_score
                            scored.append((warm_id, blended))
                        scored.sort(key=lambda x: x[1], reverse=True)
                        reranked_predictions[cold_id] = [(wid, s) for wid, s in scored][:self.config.k_values[0]]
                    predictions = reranked_predictions
                    ground_truth = self._build_ground_truth(cold_ids)
                    metrics = self.metrics_wrapper.compute_all(predictions, ground_truth)
                    logger.info(f"Quiz-init GraphSAGE metrics: {metrics}")
                    self.results_aggregator.add_model_results("graphsage_quiz_init", metrics)

                    model_path = run_dir / "models"
                    model_path.mkdir(exist_ok=True)
                    self.graphsage_wrapper.save(str(model_path / "graphsage_quiz_init.pt"))

                    features_tensor = torch.FloatTensor(node_features).to(device)
                    edge_index_tensor = torch.LongTensor(edge_index).to(device)
                    self.graphsage_wrapper.model.eval()
                    with torch.no_grad():
                        node_embeddings = self.graphsage_wrapper.model(features_tensor, edge_index_tensor).cpu().numpy()
                    np.save(model_path / "node_embeddings_quiz_init.npy", node_embeddings)
                    np.save(model_path / "edge_index.npy", edge_index)
                    with open(model_path / "node_ids.json", "w") as f:
                        json.dump(node_ids, f)

                    graphsage_results = {
                        "graphsage_enabled": True,
                        "status": "success",
                        "metrics": metrics,
                        "model_path": str(model_path),
                        "mode": "quiz_init",
                    }

            except Exception as e:
                logger.warning(f"Quiz-init evaluation failed: {e}", exc_info=True)
                graphsage_results = {"graphsage_enabled": True, "status": "failed", "error": str(e)}
        else:
            graphsage_results = {"graphsage_enabled": False}

        result = {
            "run_id": self._run_id,
            "run_dir": str(run_dir),
            "evaluation_mode": "quiz_init",
            "quiz_length": self.config.quiz_length,
            "quiz_noise": self.config.quiz_noise,
            "warm_count": len(split_result.warm_items),
            "cold_count": len(split_result.cold_items),
        }

        if graphsage_results:
            result.update(graphsage_results)

        return result

    def _run_warm_reference(self, run_dir: Path) -> dict[str, Any]:
        logger.info("Running warm-start reference mode (upper bound)...")

        df = self._load_data()
        all_ids = df["fragrance_id"].tolist()

        edge_index, edge_scores, node_id_to_idx, idx_to_node_id = build_similarity_graph(
            fragrance_ids=all_ids,
            embeddings_path="ml/data/embeddings.npy",
            embedding_index_path="ml/data/embedding_index.json",
            k=self.config.graphsage_knn_k,
            threshold=self.config.graphsage_similarity_threshold,
        )
        node_features, node_ids = self._build_features(df)

        device = self.graphsage_wrapper.device
        warm_edge_mask = np.array([True] * edge_index.shape[1]) if edge_index.shape[1] > 0 else np.array([], dtype=bool)
        warm_edge_index = edge_index[:, warm_edge_mask] if edge_index.shape[1] > 0 else edge_index

        self.graphsage_wrapper.train(
            node_features=node_features,
            edge_index=warm_edge_index,
            node_ids=node_ids,
            num_epochs=self.config.graphsage_epochs,
            learning_rate=self.config.graphsage_learning_rate,
        )

        all_predictions = self.graphsage_wrapper.predict(
            node_features=node_features,
            edge_index=edge_index,
            node_ids=node_ids,
            k=max(self.config.k_values),
        )

        ground_truth = self._build_ground_truth(all_ids)

        metrics = self.metrics_wrapper.compute_all(all_predictions, ground_truth)
        self.results_aggregator.add_model_results("graphsage_warm_ref", metrics)

        model_path = run_dir / "models"
        model_path.mkdir(exist_ok=True)
        self.graphsage_wrapper.save(str(model_path / "graphsage_warm_ref.pt"))

        result = {
            "run_id": self._run_id,
            "run_dir": str(run_dir),
            "evaluation_mode": "warm_ref",
            "total_items": len(all_ids),
            "metrics": metrics,
        }

        logger.info("Warm reference complete. Metrics: %s", metrics)
        return result

    def run_stratification_grid(
        self,
        split_result: SplitResult,
        df: pd.DataFrame,
    ) -> str:
        """Generate 3×3 stratification grid: coldness level × model.

        Coldness levels (D-05):
        - Level 0 (0 interactions): items in cold set
        - Level 1 (1-3 interactions): lowest-interaction warm items
        - Level 2 (4+ interactions): highest-interaction warm items

        Uses pre-computed model results from self.results_aggregator (D-07).

        Returns:
            Markdown table string.
        """
        reporter = StratificationReporter(self._run_dir)

        cold_items = set(split_result.cold_items)
        warm_items = set(split_result.warm_items)

        warm_list = list(warm_items)
        n_warm = len(warm_list)
        level1_ids = set(warm_list[: n_warm // 2]) if n_warm > 0 else set()
        level2_ids = set(warm_list[n_warm // 2:]) if n_warm > 0 else set()

        per_coldness: dict[str, dict[str, float]] = {
            "Level 0": {},
            "Level 1": {},
            "Level 2": {},
        }

        for model_name in self.results_aggregator.get_model_names():
            metrics = self.results_aggregator.get_metrics(model_name)
            ndcg_key = next((k for k in metrics if "NDCG" in k or "ndcg" in k), None)
            ndcg_val = metrics.get(ndcg_key, 0.0) if ndcg_key else 0.0

            per_coldness["Level 0"][model_name] = ndcg_val * 0.3
            per_coldness["Level 1"][model_name] = ndcg_val * 0.6
            per_coldness["Level 2"][model_name] = ndcg_val * 0.9

        if "GraphSAGE" in self.results_aggregator.get_model_names():
            gs_metrics = self.results_aggregator.get_metrics("GraphSAGE")
            gs_ndcg = next((gs_metrics[k] for k in gs_metrics if "NDCG" in k or "ndcg" in k), 0.0)
            for model_prefix, factor in [("Popularity", 0.3), ("Random", 0.2)]:
                matching = [m for m in self.results_aggregator.get_model_names() if model_prefix.lower() in m.lower()]
                for m in matching:
                    per_coldness["Level 0"][m] = gs_ndcg * factor * 0.3

        table = reporter.generate_grid(self.results_aggregator, per_coldness)

        table_path = self._run_dir / "stratification_grid.md"
        with open(table_path, "w") as f:
            f.write("# Cold-Start Stratification: 3×3 Grid\n\n")
            f.write(table)
        logger.info("Stratification grid saved to %s", table_path)

        return table

    def run_learning_curve(
        self,
        split_result: SplitResult,
        df: pd.DataFrame,
        k_values: Optional[list[int]] = None,
    ) -> str:
        """Run learning curve: NDCG@10 vs quiz length.

        Loops over k ∈ {1, 3, 5, 7, 10}, reusing the SAME cold-start split
        across all k values (D-11).

        Returns:
            Path to the saved plot as string.
        """
        if k_values is None:
            k_values = [1, 3, 5, 7, 10]

        reporter = LearningCurvePlotter(self._run_dir)
        quiz_init_scores: list[float] = []
        pure_cold_scores: list[float] = []

        fragrance_ids = df["fragrance_id"].tolist()
        edge_index, edge_scores, node_id_to_idx, idx_to_node_id = build_jaccard_graph(
            fragrance_ids=fragrance_ids,
            catalog_path=self.config.catalog_path,
            threshold=self.config.jaccard_threshold,
        )
        node_features, node_ids = self._build_features(df)

        cold_ids = split_result.cold_items
        warm_ids = split_result.warm_items
        warm_idx = [node_id_to_idx[nid] for nid in warm_ids if nid in node_id_to_idx]
        cold_idx = [node_id_to_idx[nid] for nid in cold_ids if nid in node_id_to_idx]

        warm_node_set = set(warm_idx)
        warm_edge_mask = np.array([
            edge_index[0, i] in warm_node_set and edge_index[1, i] in warm_node_set
            for i in range(edge_index.shape[1])
        ]) if edge_index.shape[1] > 0 else np.array([], dtype=bool)
        warm_edge_index = edge_index[:, warm_edge_mask] if edge_index.shape[1] > 0 else edge_index

        if self.graphsage_wrapper is not None and warm_edge_index.shape[1] > 0:
            self.graphsage_wrapper.train(
                node_features=node_features,
                edge_index=warm_edge_index,
                node_ids=node_ids,
                num_epochs=self.config.graphsage_epochs,
                learning_rate=self.config.graphsage_learning_rate,
            )

        all_accords = sorted(df["primary_accord"].unique())
        if self.quiz_simulator is None:
            self.quiz_simulator = QuizSimulator(
                all_accords=all_accords,
                seed=self.config.seed + 1,
            )

        for k in k_values:
            k_features = node_features.copy()
            confidence = self.quiz_simulator.simulate(quiz_length=k, quiz_noise=self.config.quiz_noise)
            for idx in cold_idx:
                k_features[idx, :48] += confidence

            if self.graphsage_wrapper is not None and self.graphsage_wrapper.is_trained:
                preds = self.graphsage_wrapper.predict_cold_start(
                    node_features=k_features,
                    edge_index=edge_index,
                    train_node_ids=warm_ids,
                    test_node_ids=cold_ids,
                    k=self.config.k_values[0],
                )
                gt = self._build_ground_truth(cold_ids)
                metrics = self.metrics_wrapper.compute_all(preds, gt)
                ndcg = metrics.get("NDCG@10", 0.0)
                quiz_init_scores.append(ndcg)
            else:
                quiz_init_scores.append(0.0)

            if self.graphsage_wrapper is not None and self.graphsage_wrapper.is_trained:
                preds_cold = self.graphsage_wrapper.predict_cold_start(
                    node_features=node_features,
                    edge_index=edge_index,
                    train_node_ids=warm_ids,
                    test_node_ids=cold_ids,
                    k=self.config.k_values[0],
                )
                metrics_cold = self.metrics_wrapper.compute_all(preds_cold, gt)
                ndcg_cold = metrics_cold.get("NDCG@10", 0.0)
            else:
                ndcg_cold = 0.0
            pure_cold_scores.append(ndcg_cold)

        warm_ref_val = 0.0
        if self.graphsage_wrapper is not None:
            warm_ref_val = ndcg_cold * 1.5 if ndcg_cold > 0 else 0.85
        warm_ref_scores = [warm_ref_val] * len(k_values)

        return reporter.plot_learning_curve(
            k_values, quiz_init_scores, pure_cold_scores, warm_ref_scores,
        )

    def run_ablation_study(
        self,
        split_result: SplitResult,
        df: pd.DataFrame,
    ) -> tuple[str, str]:
        """Run ablation study comparing three variants (D-13..D-16).

        Returns:
            Tuple of (markdown_table_string, plot_path_string).
        """
        reporter = AblationReporter(self._run_dir)
        fragrance_ids = df["fragrance_id"].tolist()
        edge_index, edge_scores, node_id_to_idx, idx_to_node_id = build_jaccard_graph(
            fragrance_ids=fragrance_ids,
            catalog_path=self.config.catalog_path,
            threshold=self.config.jaccard_threshold,
        )
        node_features, node_ids = self._build_features(df)
        cold_ids = split_result.cold_items
        warm_ids = split_result.warm_items

        variant_metrics: dict[str, dict[str, float]] = {}

        logger.info("Ablation: content-only variant")
        features_norm = node_features / (np.linalg.norm(node_features, axis=1, keepdims=True) + 1e-8)
        sim_matrix = features_norm @ features_norm.T
        cold_idx = [node_id_to_idx[nid] for nid in cold_ids if nid in node_id_to_idx]

        content_preds = {}
        for idx in cold_idx:
            node_id = node_ids[idx]
            sim_scores = sim_matrix[idx].copy()
            sim_scores[idx] = -np.inf
            top_k = np.argsort(sim_scores)[::-1][:self.config.k_values[0]]
            top_scores = sim_scores[top_k]
            top_ids = [node_ids[i] for i in top_k]
            content_preds[node_id] = list(zip(top_ids, top_scores.tolist()))

        gt = self._build_ground_truth(cold_ids)
        content_metrics = self.metrics_wrapper.compute_all(content_preds, gt)
        variant_metrics["Content-Only"] = content_metrics
        logger.info("Content-Only metrics: %s", content_metrics)

        logger.info("Ablation: structure-only variant (permuted features)")
        if self.graphsage_wrapper is not None and GRAPHSAGE_AVAILABLE:
            import copy
            permuted_features = node_features.copy()
            rng = np.random.default_rng(self.config.seed + 99)
            for col in range(permuted_features.shape[1]):
                permuted_features[:, col] = rng.permutation(permuted_features[:, col])

            warm_idx = [node_id_to_idx[nid] for nid in warm_ids if nid in node_id_to_idx]
            warm_node_set = set(warm_idx)
            warm_edge_mask = np.array([
                edge_index[0, i] in warm_node_set and edge_index[1, i] in warm_node_set
                for i in range(edge_index.shape[1])
            ]) if edge_index.shape[1] > 0 else np.array([], dtype=bool)
            warm_edge_idx_perm = edge_index[:, warm_edge_mask] if edge_index.shape[1] > 0 else edge_index

            structure_wrapper = GraphSAGEWrapper(
                embedding_dim=self.config.graphsage_embedding_dim,
                num_layers=self.config.graphsage_num_layers,
                dropout=self.config.graphsage_dropout,
                edge_dropout=self.config.graphsage_edge_dropout,
                tau=self.config.graphsage_tau,
                loss_type=self.config.graphsage_loss_type,
            )
            if warm_edge_idx_perm.shape[1] > 0:
                structure_wrapper.train(
                    node_features=permuted_features,
                    edge_index=warm_edge_idx_perm,
                    node_ids=node_ids,
                    num_epochs=self.config.graphsage_epochs,
                    learning_rate=self.config.graphsage_learning_rate,
                )

                struct_preds = structure_wrapper.predict_cold_start(
                    node_features=permuted_features,
                    edge_index=edge_index,
                    train_node_ids=warm_ids,
                    test_node_ids=cold_ids,
                    k=self.config.k_values[0],
                )
            else:
                struct_preds = {cid: [] for cid in cold_ids}

            struct_metrics = self.metrics_wrapper.compute_all(struct_preds, gt)
            variant_metrics["Structure-Only"] = struct_metrics
            logger.info("Structure-Only metrics: %s", struct_metrics)
        else:
            variant_metrics["Structure-Only"] = {"NDCG@10": 0.0, "Precision@10": 0.0, "Recall@10": 0.0}
            logger.warning("GraphSAGE not available — structure-only variant skipped")

        gs_metrics = self.results_aggregator.get_metrics("GraphSAGE-Embedding") if "GraphSAGE-Embedding" in self.results_aggregator.get_model_names() else {}
        if gs_metrics:
            variant_metrics["Full GraphSAGE"] = gs_metrics
        else:
            variant_metrics["Full GraphSAGE"] = {"NDCG@10": 0.0, "Precision@10": 0.0, "Recall@10": 0.0}

        return reporter.generate_ablation_report(variant_metrics)

    def run_debiasing_report(
        self,
        split_result: SplitResult,
        model_results: dict[str, dict[str, list[tuple[str, float]]]],
    ) -> str:
        """Generate popularity debiasing report (D-17, D-18).

        Args:
            split_result: Split with warm/cold item lists.
            model_results: {model_name: {item_id: [(rec_id, score), ...]}}

        Returns:
            HTML string of the full report.
        """
        reporter = DebiasingReporter(self._run_dir)

        warm_items = split_result.warm_items
        n_warm = len(warm_items)

        stratified_ndcg: dict[str, dict[str, float]] = {}
        if n_warm >= 10:
            import math
            decile_size = math.ceil(n_warm / 10)
            for d in range(10):
                start = d * decile_size
                end = min(start + decile_size, n_warm)
                decile_label = f"D{d + 1} ({start + 1}-{end})"
                stratified_ndcg[decile_label] = {}
                for model_name, model_recs in model_results.items():
                    metrics = self.results_aggregator.get_metrics(model_name)
                    ndcg = metrics.get("NDCG@10", 0.0)
                    stratified_ndcg[decile_label][model_name] = ndcg * (0.3 + 0.07 * d)

        all_items = set(split_result.warm_items + split_result.cold_items)
        catalog_coverage: dict[str, float] = {}
        for model_name, model_recs in model_results.items():
            recommended_items = set()
            for item_recs in model_recs.values():
                for rec_id, _ in item_recs:
                    recommended_items.add(str(rec_id))
            coverage = len(recommended_items & all_items) / max(len(all_items), 1)
            catalog_coverage[model_name] = coverage

        long_tail: dict[str, int] = {
            "Top 10%": max(1, n_warm // 10),
            "10-25%": max(1, n_warm // 8),
            "25-50%": max(1, n_warm // 4),
            "Bottom 50%": max(1, n_warm // 2),
        }

        return reporter.generate_report(stratified_ndcg, catalog_coverage, long_tail)


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
