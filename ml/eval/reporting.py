"""Reporting and visualization for research experiments (Phase 5).

Stratification grid, learning curves, ablation study plots, and popularity debiasing reports.
All plots use matplotlib Agg backend for headless execution.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ml.eval.aggregator import ResultsAggregator

logger = logging.getLogger(__name__)

# ── Plot Style ──────────────────────────────────────────────────────────────

try:
    import seaborn as sns
    sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
except ImportError:
    logger.info("seaborn not available — using matplotlib defaults")
    plt.style.use("ggplot")

COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"]
MARKERS = ["o", "s", "D", "^", "v"]


# ── Stratification 3×3 Grid (D-05, D-06, D-07) ──────────────────────────

class StratificationReporter:
    """Generates 3×3 grid of NDCG@10 for coldness levels × models.

    Coldness levels (D-05):
    - Level 0: 0 interactions (pure cold)
    - Level 1: 1-3 interactions
    - Level 2: 4+ interactions (warm reference)

    Models (D-06): GraphSAGE-Embedding, GraphSAGE-Jaccard, Feature-Only, Popularity
    Primary metric (D-07): NDCG@10
    """

    COLDNESS_LEVELS = ["Level 0\n(0 int.)", "Level 1\n(1-3 int.)", "Level 2\n(4+ int.)"]
    MODEL_NAMES = ["GraphSAGE-Embedding", "GraphSAGE-Jaccard", "Feature-Only", "Popularity"]

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        (output_dir / "plots").mkdir(parents=True, exist_ok=True)

    def generate_grid(
        self,
        aggregator: ResultsAggregator,
        per_coldness_metrics: dict[str, dict[str, float]],
    ) -> str:
        """Generate 3×3 Markdown table and bar chart from per-coldness-level metrics.

        Args:
            aggregator: ResultsAggregator with overall model comparison.
            per_coldness_metrics: Nested dict {coldness_level: {model_name: ndcg_at_10}}.

        Returns:
            Markdown table string of the 3×3 grid.
        """
        col_labels = [f"{m} NDCG@10" for m in self.MODEL_NAMES]
        col_widths = [20] + [24 for _ in self.MODEL_NAMES]
        header_parts = [f"{'Coldness Level':<{col_widths[0]}}"]
        for i, label in enumerate(col_labels):
            header_parts.append(f"{label:<{col_widths[i + 1]}}")
        header = "| " + " | ".join(header_parts) + " |"
        sep = "|" + "|".join("-" * (w + 2) for w in col_widths) + "|"

        rows = []
        for level_label in self.COLDNESS_LEVELS:
            level_key = level_label.split("\n")[0]
            row_parts = [f"{level_label:<{col_widths[0]}}"]
            for mn in self.MODEL_NAMES:
                val = per_coldness_metrics.get(level_key, {}).get(mn, 0.0)
                row_parts.append(f"{val:.4f}")
            rows.append("| " + " | ".join(row_parts) + " |")

        table = "\n".join([header, sep] + rows)

        levels = [l.split("\n")[0] for l in self.COLDNESS_LEVELS]
        x = np.arange(len(levels))
        n_models = len(self.MODEL_NAMES)
        width = 0.8 / n_models

        fig, ax = plt.subplots(figsize=(10, 6))
        for i, model in enumerate(self.MODEL_NAMES):
            values = [per_coldness_metrics.get(lev, {}).get(model, 0.0) for lev in levels]
            ax.bar(x + i * width, values, width, label=model, color=COLORS[i])

        ax.set_xlabel("Coldness Level")
        ax.set_ylabel("NDCG@10")
        ax.set_title("Cold-Start Stratification: NDCG@10 by Coldness Level and Model")
        ax.set_xticks(x + (n_models - 1) * width / 2)
        ax.set_xticklabels(self.COLDNESS_LEVELS, fontsize=10)
        ax.legend()
        max_val = max(1.0, max(v for d in per_coldness_metrics.values() for v in d.values()))
        ax.set_ylim(0, max_val * 1.1)

        path = self.output_dir / "plots" / "stratification_3x3_grid.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        logger.info("Stratification grid saved to %s", path)

        return table


# ── Quiz Sensitivity (D-11, D-12) ──────────────────────────────────────────

class QuizSensitivityPlotter:
    """Plots NDCG@10 vs quiz length for quiz-init, pure-cold, and warm-ref.

    Uses the SAME cold-start split across all k values (D-11).
    Three lines (D-12):
    - Quiz-init GraphSAGE: rising with k
    - Pure cold-start baseline: flat
    - Warm-start reference: flat upper bound
    Note: despite the class name, the x-axis is quiz_length (k), NOT warm
    interaction count — this is a quiz sensitivity curve, not a true learning curve.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        (output_dir / "plots").mkdir(parents=True, exist_ok=True)

    def plot_quiz_sensitivity(
        self,
        k_values: list[int],
        quiz_init_scores: list[float],
        pure_cold_scores: list[float],
        warm_ref_scores: list[float],
    ) -> str:
        """Generate quiz sensitivity plot and return path.

        Args:
            k_values: Quiz lengths tested, e.g., [1, 3, 5, 7, 10].
            quiz_init_scores: NDCG@10 for quiz-init GraphSAGE at each k.
            pure_cold_scores: NDCG@10 for pure cold-start (flat — invariant to k).
            warm_ref_scores: NDCG@10 for warm-start reference (flat — invariant to k).

        Returns:
            Path to the saved plot image as string.
        """
        fig, ax = plt.subplots(figsize=(8, 5))

        ax.plot(k_values, quiz_init_scores, marker="o", color=COLORS[0],
                linewidth=2, markersize=8, label="Quiz-Init GraphSAGE")
        ax.plot(k_values, pure_cold_scores, marker="s", color=COLORS[1],
                linewidth=2, markersize=8, linestyle="--", label="Pure Cold-Start")
        ax.plot(k_values, warm_ref_scores, marker="D", color=COLORS[2],
                linewidth=2, markersize=8, linestyle=":", label="Warm-Start Reference")

        ax.set_xlabel("Quiz Length (k)")
        ax.set_ylabel("NDCG@10")
        ax.set_title("Quiz Sensitivity: NDCG@10 vs Quiz Length (k)")
        ax.set_xticks(k_values)
        ax.legend()
        ax.grid(True, alpha=0.3)

        path = self.output_dir / "plots" / "quiz_sensitivity.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        logger.info("Quiz sensitivity plot saved to %s", path)

        return str(path)


# ── Ablation Study (D-13, D-14, D-15, D-16) ──────────────────────────────

class AblationReporter:
    """Compares content-only, structure-only, and full GraphSAGE variants.

    Variants (D-13, D-14, D-15):
    - Content-only: direct cosine similarity on 432-dim features (no GraphSAGE)
    - Structure-only: GraphSAGE on row-permuted features (preserves per-dim distribution)
    - Full GraphSAGE: standard Phase 4 pipeline

    Output (D-16): Comparison table + side-by-side bar chart
    """

    VARIANT_NAMES = ["Content-Only", "Structure-Only", "Full GraphSAGE"]

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        (output_dir / "plots").mkdir(parents=True, exist_ok=True)

    def generate_ablation_report(
        self,
        variant_metrics: dict[str, dict[str, float]],
    ) -> tuple[str, str]:
        """Generate comparison table and bar chart.

        Args:
            variant_metrics: Dict {variant_name: {metric_name: value}}.

        Returns:
            Tuple of (markdown_table_string, plot_path_string).
        """
        all_metrics: list[str] = []
        for v in self.VARIANT_NAMES:
            if v in variant_metrics:
                for m in variant_metrics[v]:
                    if m not in all_metrics:
                        all_metrics.append(m)

        header = f"| {'Metric':<20}" + "".join(f"| {v:<18}" for v in self.VARIANT_NAMES) + " |"
        sep = "|" + "|".join("-" * 22 for _ in range(len(self.VARIANT_NAMES) + 1)) + "|"
        rows = []
        for metric in all_metrics:
            row = f"| {metric:<20}"
            for variant in self.VARIANT_NAMES:
                val = variant_metrics.get(variant, {}).get(metric, "—")
                row += f"| {str(val):<18}"
            rows.append(row + " |")
        table = "\n".join([header, sep] + rows)

        x = np.arange(len(self.VARIANT_NAMES))
        width = 0.25
        ndcg_key = next((m for m in all_metrics if "NDCG" in m), "NDCG@10")

        fig, ax = plt.subplots(figsize=(8, 5))
        ndcg_values = [variant_metrics.get(v, {}).get(ndcg_key, 0.0) for v in self.VARIANT_NAMES]
        bars = ax.bar(x, ndcg_values, width, color=COLORS[:3], edgecolor="white", linewidth=0.5)

        ax.set_xlabel("Variant")
        ax.set_ylabel(f"{ndcg_key}")
        ax.set_title("Ablation Study: Cold-Start NDCG@10 by Model Variant")
        ax.set_xticks(x)
        ax.set_xticklabels(self.VARIANT_NAMES, fontsize=10)

        for bar, val in zip(bars, ndcg_values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                    f"{val:.4f}", ha="center", va="bottom", fontsize=9)

        path = self.output_dir / "plots" / "ablation_bar_chart.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        logger.info("Ablation chart saved to %s", path)

        return table, str(path)


# ── Popularity Debiasing Report (D-17, D-18) ──────────────────────────────

class DebiasingReporter:
    """Generates popularity debiasing HTML report.

    Report includes (D-18):
    - Popularity-stratified NDCG table (decile × model)
    - Catalog coverage bar chart per model
    - Long-tail distribution curve

    Popularity computed from warm-set interaction counts (D-17).
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        (output_dir / "plots").mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        stratified_ndcg: dict[str, dict[str, float]],
        catalog_coverage: dict[str, float],
        long_tail_distribution: dict[str, int],
    ) -> str:
        """Generate a single HTML report page with all debiasing analysis.

        Args:
            stratified_ndcg: {decile_label: {model_name: ndcg_at_10}}.
            catalog_coverage: {model_name: coverage_fraction} (0.0 to 1.0).
            long_tail_distribution: {popularity_bin: item_count}.

        Returns:
            HTML string of the full report page.
        """
        deciles = sorted(stratified_ndcg.keys())
        models = set()
        for d in deciles:
            models.update(stratified_ndcg[d].keys())
        models = sorted(models)

        ndcg_rows = ""
        for decile in deciles:
            row = f"<tr><td>{decile}</td>"
            for model in models:
                val = stratified_ndcg.get(decile, {}).get(model, "—")
                row += f"<td>{val:.4f}</td>" if isinstance(val, float) else f"<td>{val}</td>"
            row += "</tr>"
            ndcg_rows += row

        model_cols = "".join(f"<th>{m}</th>" for m in models)

        fig, ax = plt.subplots(figsize=(8, 4))
        cov_models = list(catalog_coverage.keys())
        cov_values = list(catalog_coverage.values())
        ax.bar(cov_models, cov_values, color=COLORS[:len(cov_models)])
        ax.set_ylabel("Catalog Coverage")
        ax.set_title("Catalog Coverage by Model")
        ax.set_ylim(0, 1.0)
        for i, v in enumerate(cov_values):
            ax.text(i, v + 0.02, f"{v:.1%}", ha="center", fontsize=9)
        cov_path = self.output_dir / "plots" / "catalog_coverage.png"
        fig.tight_layout()
        fig.savefig(cov_path, dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 4))
        bins = sorted(long_tail_distribution.keys())
        counts = [long_tail_distribution[b] for b in bins]
        ax.bar(range(len(bins)), counts, color=COLORS[4])
        ax.set_xticks(range(len(bins)))
        ax.set_xticklabels(bins, rotation=45, ha="right")
        ax.set_ylabel("Number of Items")
        ax.set_title("Long-Tail Distribution: Items by Popularity")
        tail_path = self.output_dir / "plots" / "long_tail_distribution.png"
        fig.tight_layout()
        fig.savefig(tail_path, dpi=150)
        plt.close(fig)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Popularity Debiasing Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 960px; margin: 0 auto; padding: 20px; }}
  h1, h2 {{ color: #333; }}
  table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
  th {{ background-color: #4C72B0; color: white; }}
  tr:nth-child(even) {{ background-color: #f2f2f2; }}
  img {{ max-width: 100%; height: auto; margin: 16px 0; }}
</style></head>
<body>
<h1>Popularity Debiasing Report</h1>

<h2>Popularity-Stratified NDCG@10</h2>
<table><tr><th>Decile</th>{model_cols}</tr>{ndcg_rows}</table>

<h2>Catalog Coverage</h2>
<p>Fraction of catalog items that appear in each model's top-k recommendations.</p>
<img src="plots/catalog_coverage.png" alt="Catalog Coverage">

<h2>Long-Tail Distribution</h2>
<p>Distribution of items across popularity bins.</p>
<img src="plots/long_tail_distribution.png" alt="Long-Tail Distribution">

<p><em>Generated by Scentrix Evaluation Pipeline — Phase 5</em></p>
</body></html>"""

        report_path = self.output_dir / "debiasing_report.html"
        with open(report_path, "w") as f:
            f.write(html)
        logger.info("Debiasing report saved to %s", report_path)

        return html
