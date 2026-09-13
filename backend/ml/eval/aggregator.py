"""Results aggregation and comparison for multi-model evaluation."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ResultsAggregator:
    def __init__(self):
        self._results: dict[str, dict[str, float]] = {}

    def add_model_results(self, model_name: str, metrics: dict[str, float]) -> None:
        if not metrics:
            logger.warning("Empty metrics for model '%s' — skipping", model_name)
            return
        self._results[model_name] = dict(metrics)

    def get_model_names(self) -> list[str]:
        return list(self._results.keys())

    def get_metrics(self, model_name: str) -> dict[str, float]:
        return dict(self._results.get(model_name, {}))

    def generate_comparison_table(self, fmt: str = "markdown") -> str:
        if not self._results:
            return "No results to compare." if fmt == "plain" else "[]" if fmt == "json" else ""

        model_names = list(self._results.keys())
        all_metrics: list[str] = []
        for m in model_names:
            for k in self._results[m]:
                if k not in all_metrics:
                    all_metrics.append(k)

        if fmt == "json":
            return json.dumps(self._results, indent=2)

        if fmt == "plain":
            lines = [f"{'Metric':<20}" + "".join(f"{m:<20}" for m in model_names)]
            lines.append("-" * len(lines[0]))
            for metric in all_metrics:
                row = f"{metric:<20}"
                for m in model_names:
                    val = self._results[m].get(metric, "—")
                    row += f"{str(val):<20}"
                lines.append(row)
            return "\n".join(lines)

        # markdown (default)
        header = f"| {'Metric':<20}" + "".join(f"| {m:<15}" for m in model_names) + " |"
        sep = "|" + "|".join("-" * 22 for _ in range(len(model_names) + 1)) + "|"
        rows = []
        for metric in all_metrics:
            row = f"| {metric:<20}"
            for m in model_names:
                row += f"| {str(self._results[m].get(metric, '—')):<15}"
            rows.append(row + " |")
        return "\n".join([header, sep] + rows)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._results)
