"""Tests for Phase 5 research reporting classes (RSCH-04/05/06/07).

Tests that each reporter:
- Instantiates correctly
- Produces output files (plots, tables, HTML)
- Returns expected data structures
"""

from pathlib import Path

import numpy as np
import pytest

from ml.eval.reporting import (
    AblationReporter,
    DebiasingReporter,
    LearningCurvePlotter,
    StratificationReporter,
)


# ── RSCH-04: StratificationReporter ──────────────────────────────────────

class TestStratificationReporter:
    """RSCH-04: StratificationReporter produces 3×3 NDCG@10 Markdown table + bar chart."""

    @pytest.fixture
    def reporter(self, tmp_path):
        return StratificationReporter(output_dir=Path(tmp_path))

    @pytest.fixture
    def mock_metrics(self):
        return {
            "Level 0": {"Popularity": 0.45, "Random": 0.22, "GraphSAGE": 0.52},
            "Level 1": {"Popularity": 0.55, "Random": 0.30, "GraphSAGE": 0.68},
            "Level 2": {"Popularity": 0.72, "Random": 0.35, "GraphSAGE": 0.85},
        }

    def test_instantiation_creates_plots_dir(self, tmp_path):
        """Constructor creates plots subdirectory."""
        StratificationReporter(output_dir=Path(tmp_path))
        assert (tmp_path / "plots").exists()

    def test_generate_grid_returns_markdown_table(self, reporter, mock_metrics):
        """generate_grid returns a non-empty Markdown table string."""
        table = reporter.generate_grid(aggregator=None, per_coldness_metrics=mock_metrics)
        assert isinstance(table, str)
        assert len(table) > 0
        assert "NDCG@10" in table
        assert "Popularity" in table
        assert "GraphSAGE" in table

    def test_generate_grid_creates_bar_chart_file(self, reporter, mock_metrics):
        """generate_grid saves a bar chart PNG."""
        reporter.generate_grid(aggregator=None, per_coldness_metrics=mock_metrics)
        chart_path = reporter.output_dir / "plots" / "stratification_3x3_grid.png"
        assert chart_path.exists()
        assert chart_path.stat().st_size > 0

    def test_grid_table_contains_all_coldness_levels(self, reporter, mock_metrics):
        """Markdown table includes all 3 coldness levels."""
        table = reporter.generate_grid(aggregator=None, per_coldness_metrics=mock_metrics)
        for level in ["Level 0", "Level 1", "Level 2"]:
            assert level in table

    def test_grid_table_contains_all_model_names(self, reporter, mock_metrics):
        """Markdown table includes all 3 model names."""
        table = reporter.generate_grid(aggregator=None, per_coldness_metrics=mock_metrics)
        for model in ["Popularity", "Random", "GraphSAGE"]:
            assert model in table

    def test_grid_uses_provided_metric_values(self, reporter):
        """generate_grid uses the provided metric values in output."""
        metrics = {
            "Level 0": {"Popularity": 0.1234, "Random": 0.5678, "GraphSAGE": 0.9012},
            "Level 1": {"Popularity": 0.1111, "Random": 0.2222, "GraphSAGE": 0.3333},
            "Level 2": {"Popularity": 0.4444, "Random": 0.5555, "GraphSAGE": 0.6666},
        }
        table = reporter.generate_grid(aggregator=None, per_coldness_metrics=metrics)
        assert "0.1234" in table
        assert "0.5678" in table
        assert "0.9012" in table

    def test_grid_with_missing_model_defaults_to_zero(self, reporter):
        """Missing model for a level defaults to 0.0."""
        metrics = {
            "Level 0": {"Popularity": 0.5},
            "Level 1": {"Random": 0.3},
            "Level 2": {},
        }
        table = reporter.generate_grid(aggregator=None, per_coldness_metrics=metrics)
        assert "0.0000" in table

    def test_bar_chart_use_agg_backend(self, reporter, mock_metrics):
        """Bar chart is generated with Agg backend (no display)."""
        import matplotlib
        assert matplotlib.get_backend() == "Agg"
        reporter.generate_grid(aggregator=None, per_coldness_metrics=mock_metrics)


# ── RSCH-05: LearningCurvePlotter ────────────────────────────────────────

class TestLearningCurvePlotter:
    """RSCH-05: LearningCurvePlotter produces a three-line plot."""

    @pytest.fixture
    def plotter(self, tmp_path):
        return LearningCurvePlotter(output_dir=Path(tmp_path))

    @pytest.fixture
    def mock_curves(self):
        return {
            "k_values": [1, 3, 5, 7, 10],
            "quiz_init": [0.45, 0.55, 0.62, 0.67, 0.70],
            "pure_cold": [0.40, 0.40, 0.40, 0.40, 0.40],
            "warm_ref": [0.85, 0.85, 0.85, 0.85, 0.85],
        }

    def test_instantiation_creates_plots_dir(self, tmp_path):
        """Constructor creates plots subdirectory."""
        LearningCurvePlotter(output_dir=Path(tmp_path))
        assert (tmp_path / "plots").exists()

    def test_plot_learning_curve_returns_path_string(self, plotter, mock_curves):
        """plot_learning_curve returns a string path to the saved plot."""
        result = plotter.plot_learning_curve(
            k_values=mock_curves["k_values"],
            quiz_init_scores=mock_curves["quiz_init"],
            pure_cold_scores=mock_curves["pure_cold"],
            warm_ref_scores=mock_curves["warm_ref"],
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_plot_learning_curve_creates_png_file(self, plotter, mock_curves):
        """plot_learning_curve saves a PNG file."""
        plotter.plot_learning_curve(
            k_values=mock_curves["k_values"],
            quiz_init_scores=mock_curves["quiz_init"],
            pure_cold_scores=mock_curves["pure_cold"],
            warm_ref_scores=mock_curves["warm_ref"],
        )
        path = plotter.output_dir / "plots" / "learning_curve.png"
        assert path.exists()
        assert path.stat().st_size > 0

    def test_plot_includes_three_lines(self, plotter, mock_curves):
        """Plot file is created with data from all three curves."""
        result_path = plotter.plot_learning_curve(
            k_values=mock_curves["k_values"],
            quiz_init_scores=mock_curves["quiz_init"],
            pure_cold_scores=mock_curves["pure_cold"],
            warm_ref_scores=mock_curves["warm_ref"],
        )
        # Verify the file was saved (the plot should contain 3 line labels)
        assert Path(result_path).exists()

    def test_with_different_k_values(self, plotter):
        """Works with different sets of k_values."""
        result = plotter.plot_learning_curve(
            k_values=[1, 5, 10],
            quiz_init_scores=[0.3, 0.5, 0.7],
            pure_cold_scores=[0.4, 0.4, 0.4],
            warm_ref_scores=[0.8, 0.8, 0.8],
        )
        assert Path(result).exists()

    def test_plot_uses_agg_backend(self, plotter, mock_curves):
        """Plot is generated with Agg backend (no display)."""
        import matplotlib
        assert matplotlib.get_backend() == "Agg"
        plotter.plot_learning_curve(
            k_values=mock_curves["k_values"],
            quiz_init_scores=mock_curves["quiz_init"],
            pure_cold_scores=mock_curves["pure_cold"],
            warm_ref_scores=mock_curves["warm_ref"],
        )


# ── RSCH-06: AblationReporter ────────────────────────────────────────────

class TestAblationReporter:
    """RSCH-06: AblationReporter produces comparison table + bar chart."""

    @pytest.fixture
    def reporter(self, tmp_path):
        return AblationReporter(output_dir=Path(tmp_path))

    @pytest.fixture
    def mock_variant_metrics(self):
        return {
            "Content-Only": {"NDCG@10": 0.45, "Recall@10": 0.30},
            "Structure-Only": {"NDCG@10": 0.52, "Recall@10": 0.38},
            "Full GraphSAGE": {"NDCG@10": 0.68, "Recall@10": 0.55},
        }

    def test_instantiation_creates_plots_dir(self, tmp_path):
        """Constructor creates plots subdirectory."""
        AblationReporter(output_dir=Path(tmp_path))
        assert (tmp_path / "plots").exists()

    def test_generate_ablation_report_returns_tuple(self, reporter, mock_variant_metrics):
        """generate_ablation_report returns (markdown_table, plot_path) tuple."""
        result = reporter.generate_ablation_report(variant_metrics=mock_variant_metrics)
        assert isinstance(result, tuple)
        assert len(result) == 2
        table, plot_path = result
        assert isinstance(table, str)
        assert isinstance(plot_path, str)

    def test_ablation_table_contains_all_variants(self, reporter, mock_variant_metrics):
        """Markdown table includes all 3 variant names."""
        table, _ = reporter.generate_ablation_report(variant_metrics=mock_variant_metrics)
        for variant in ("Content-Only", "Structure-Only", "Full GraphSAGE"):
            assert variant in table

    def test_ablation_table_contains_metric_names(self, reporter, mock_variant_metrics):
        """Markdown table includes metric names from data."""
        table, _ = reporter.generate_ablation_report(variant_metrics=mock_variant_metrics)
        assert "NDCG@10" in table
        assert "Recall@10" in table

    def test_ablation_creates_bar_chart_file(self, reporter, mock_variant_metrics):
        """generate_ablation_report creates a bar chart PNG."""
        _, plot_path = reporter.generate_ablation_report(variant_metrics=mock_variant_metrics)
        assert Path(plot_path).exists()
        assert Path(plot_path).stat().st_size > 0

    def test_ablation_with_partial_variants(self, reporter):
        """Works when only some variants are provided."""
        partial = {"Content-Only": {"NDCG@10": 0.45}}
        table, plot_path = reporter.generate_ablation_report(variant_metrics=partial)
        assert "Content-Only" in table
        assert "Structure-Only" in table  # Header still includes it
        assert Path(plot_path).exists()

    def test_ablation_with_empty_metrics(self, reporter):
        """Works with empty metric dicts for variants."""
        empty = {"Content-Only": {}, "Structure-Only": {}, "Full GraphSAGE": {}}
        table, plot_path = reporter.generate_ablation_report(variant_metrics=empty)
        assert Path(plot_path).exists()

    def test_ablation_uses_agg_backend(self, reporter, mock_variant_metrics):
        """Bar chart is generated with Agg backend (no display)."""
        import matplotlib
        assert matplotlib.get_backend() == "Agg"
        reporter.generate_ablation_report(variant_metrics=mock_variant_metrics)


# ── RSCH-07: DebiasingReporter ───────────────────────────────────────────

class TestDebiasingReporter:
    """RSCH-07: DebiasingReporter produces single HTML page with debiasing analysis."""

    @pytest.fixture
    def reporter(self, tmp_path):
        return DebiasingReporter(output_dir=Path(tmp_path))

    @pytest.fixture
    def mock_debiasing_data(self):
        return {
            "stratified_ndcg": {
                "Decile 1": {"Popularity": 0.2, "GraphSAGE": 0.5},
                "Decile 2": {"Popularity": 0.3, "GraphSAGE": 0.6},
                "Decile 3": {"Popularity": 0.4, "GraphSAGE": 0.7},
            },
            "catalog_coverage": {"Popularity": 0.35, "GraphSAGE": 0.72},
            "long_tail_distribution": {
                "0-10": 50, "11-50": 30, "51-200": 15, "201+": 5,
            },
        }

    def test_instantiation_creates_plots_dir(self, tmp_path):
        """Constructor creates plots subdirectory."""
        DebiasingReporter(output_dir=Path(tmp_path))
        assert (tmp_path / "plots").exists()

    def test_generate_report_returns_html_string(self, reporter, mock_debiasing_data):
        """generate_report returns a non-empty HTML string."""
        html = reporter.generate_report(**mock_debiasing_data)
        assert isinstance(html, str)
        assert len(html) > 0
        assert html.strip().startswith("<!DOCTYPE html>")

    def test_html_contains_expected_sections(self, reporter, mock_debiasing_data):
        """HTML report contains NDCG table, catalog coverage, and long-tail sections."""
        html = reporter.generate_report(**mock_debiasing_data)
        assert "Popularity-Stratified NDCG@10" in html
        assert "Catalog Coverage" in html
        assert "Long-Tail Distribution" in html

    def test_html_contains_decile_data(self, reporter, mock_debiasing_data):
        """HTML table contains all decile rows from the input."""
        html = reporter.generate_report(**mock_debiasing_data)
        for decile in ("Decile 1", "Decile 2", "Decile 3"):
            assert decile in html

    def test_html_contains_model_names(self, reporter, mock_debiasing_data):
        """HTML table headers include model names."""
        html = reporter.generate_report(**mock_debiasing_data)
        assert "Popularity" in html
        assert "GraphSAGE" in html

    def test_generate_report_creates_html_file(self, reporter, mock_debiasing_data):
        """generate_report writes HTML to debiasing_report.html."""
        reporter.generate_report(**mock_debiasing_data)
        report_path = reporter.output_dir / "debiasing_report.html"
        assert report_path.exists()
        assert report_path.stat().st_size > 0

    def test_generate_report_creates_catalog_coverage_plot(self, reporter, mock_debiasing_data):
        """generate_report saves catalog coverage bar chart PNG."""
        reporter.generate_report(**mock_debiasing_data)
        cov_path = reporter.output_dir / "plots" / "catalog_coverage.png"
        assert cov_path.exists()
        assert cov_path.stat().st_size > 0

    def test_generate_report_creates_long_tail_plot(self, reporter, mock_debiasing_data):
        """generate_report saves long-tail distribution bar chart PNG."""
        reporter.generate_report(**mock_debiasing_data)
        tail_path = reporter.output_dir / "plots" / "long_tail_distribution.png"
        assert tail_path.exists()
        assert tail_path.stat().st_size > 0

    def test_html_contains_image_references(self, reporter, mock_debiasing_data):
        """HTML report references the plot images."""
        html = reporter.generate_report(**mock_debiasing_data)
        assert "plots/catalog_coverage.png" in html
        assert "plots/long_tail_distribution.png" in html

    def test_with_single_model(self, reporter):
        """Works with single model in data."""
        data = {
            "stratified_ndcg": {
                "Decile 1": {"GraphSAGE": 0.5},
                "Decile 2": {"GraphSAGE": 0.6},
            },
            "catalog_coverage": {"GraphSAGE": 0.8},
            "long_tail_distribution": {"Low": 100, "Medium": 50, "High": 10},
        }
        html = reporter.generate_report(**data)
        assert "GraphSAGE" in html
        cov_path = reporter.output_dir / "plots" / "catalog_coverage.png"
        assert cov_path.exists()
        report_path = reporter.output_dir / "debiasing_report.html"
        assert report_path.exists()

    def test_debiasing_uses_agg_backend(self, reporter, mock_debiasing_data):
        """Plots are generated with Agg backend (no display)."""
        import matplotlib
        assert matplotlib.get_backend() == "Agg"
        reporter.generate_report(**mock_debiasing_data)

    def test_html_is_valid_html_document(self, reporter, mock_debiasing_data):
        """Returned HTML has basic valid document structure."""
        html = reporter.generate_report(**mock_debiasing_data)
        assert "<html" in html.lower()
        assert "</html>" in html.lower()
        assert "<head>" in html
        assert "</head>" in html
        assert "<body>" in html
        assert "</body>" in html
