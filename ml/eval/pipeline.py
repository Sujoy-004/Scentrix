"""Evaluation pipeline orchestrator: load → split → persist artifacts."""

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Dict, List
import os

import pandas as pd

from ml.eval.config import EvalConfig
from ml.eval.split import ColdStartSplitter, LeaveColdOutStrategy, SplitResult
from ml.eval.metrics import MetricsWrapper
from ml.eval.aggregator import ResultsAggregator

# Try to import GraphSAGE components (optional dependency)
try:
    from ml.eval.models.graphsage_wrapper import GraphSAGEWrapper
    GRAPHSAGE_AVAILABLE = True
except ImportError:
    GRAPHSAGE_AVAILABLE = False
    logger.warning("GraphSAGE not available - install torch and torch-geometric for GraphSAGE support")

logger = logging.getLogger(__name__)


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
                edge_dropout=getattr(config, 'graphsage_edge_dropout', 0.1)
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
                # For now, we'll just verify the GraphSAGE wrapper can be instantiated
                # In a full implementation, this would load data, build graph, train, and infer
                logger.info("GraphSAGE wrapper initialized successfully")
                graphsage_results = {"graphsage_enabled": True, "status": "initialized"}
            except Exception as e:
                logger.warning(f"GraphSAGE evaluation failed: {e}")
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
