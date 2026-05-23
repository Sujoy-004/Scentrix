"""Metric computation for cold-start evaluation via ranx."""

import logging
from typing import Optional

import numpy as np
from ranx import evaluate

logger = logging.getLogger(__name__)


class MetricsWrapper:
    def __init__(self, k_values: Optional[list[int]] = None):
        self.k_values = k_values or [10]
        self._metric_list = []
        for k in self.k_values:
            self._metric_list.append(f"precision@{k}")
            self._metric_list.append(f"ndcg@{k}")
            self._metric_list.append(f"recall@{k}")

    def compute(
        self,
        cold_ids: list[str],
        all_scores: dict[str, float],
        strata: Optional[dict[str, str]] = None,
    ) -> dict:
        if not cold_ids:
            logger.warning("No cold items provided — returning empty metrics")
            return {"aggregate_metrics": {}, "per_item_metrics": {}}

        qrels = {"eval": {cid: 1 for cid in cold_ids}}
        run_dict = {"eval": all_scores}

        try:
            aggregate = evaluate(qrels, run_dict, self._metric_list, return_mean=True)
        except Exception:
            logger.error("ranx evaluate failed", exc_info=True)
            raise

        sorted_items = sorted(all_scores.items(), key=lambda x: -x[1])
        ranked_ids = [item_id for item_id, _ in sorted_items]
        cold_set = set(cold_ids)

        per_item = {}
        for rank, item_id in enumerate(ranked_ids, start=1):
            if item_id not in cold_set:
                continue
            item_metrics = {}
            for k in self.k_values:
                if rank <= k:
                    item_metrics[f"Precision@{k}"] = 1.0 / k
                    item_metrics[f"NDCG@{k}"] = 1.0 / np.log2(rank + 1)
                    item_metrics[f"Recall@{k}"] = 1.0
                else:
                    item_metrics[f"Precision@{k}"] = 0.0
                    item_metrics[f"NDCG@{k}"] = 0.0
                    item_metrics[f"Recall@{k}"] = 0.0
            if strata and item_id in strata:
                item_metrics["cold_stratum"] = strata[item_id]
            per_item[item_id] = item_metrics

        aggregate_metrics = {}
        for k in self.k_values:
            aggregate_metrics[f"Precision@{k}"] = aggregate.get(f"precision@{k}", 0.0)
            aggregate_metrics[f"NDCG@{k}"] = aggregate.get(f"ndcg@{k}", 0.0)
            aggregate_metrics[f"Recall@{k}"] = aggregate.get(f"recall@{k}", 0.0)

        return {
            "aggregate_metrics": aggregate_metrics,
            "per_item_metrics": per_item,
        }
