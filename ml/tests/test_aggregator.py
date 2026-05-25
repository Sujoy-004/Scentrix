"""Tests for ResultsAggregator — comparison tables and model result collection."""
import json

import pytest

from ml.eval.aggregator import ResultsAggregator


class TestResultsAggregator:
    """EVAL-06: ResultsAggregator collects per-model metrics and generates comparison tables."""

    # --- Add / retrieve ---

    def test_add_and_retrieve_single_model(self):
        """Single model results can be added and retrieved as a copy."""
        agg = ResultsAggregator()
        metrics = {"precision@10": 0.5, "recall@10": 0.3, "ndcg@10": 0.4}
        agg.add_model_results("PopularityBaseline", metrics)
        assert agg.get_model_names() == ["PopularityBaseline"]
        assert agg.get_metrics("PopularityBaseline") == metrics

    def test_get_metrics_returns_copy(self):
        """get_metrics returns a copy — mutating it doesn't affect internal state."""
        agg = ResultsAggregator()
        agg.add_model_results("Model", {"p@10": 0.5})
        metrics = agg.get_metrics("Model")
        metrics["p@10"] = 999
        assert agg.get_metrics("Model")["p@10"] == 0.5

    def test_multiple_models_store_independently(self):
        """Multiple models can be added and retrieved independently."""
        agg = ResultsAggregator()
        agg.add_model_results("ModelA", {"precision@10": 0.5, "recall@10": 0.3})
        agg.add_model_results("ModelB", {"precision@10": 0.7, "recall@10": 0.4})
        assert set(agg.get_model_names()) == {"ModelA", "ModelB"}
        assert agg.get_metrics("ModelA")["precision@10"] == 0.5
        assert agg.get_metrics("ModelB")["precision@10"] == 0.7

    def test_add_model_overwrites_previous(self):
        """Adding same model name overwrites previous results."""
        agg = ResultsAggregator()
        agg.add_model_results("Model", {"p@10": 0.5})
        agg.add_model_results("Model", {"p@10": 0.9})
        assert agg.get_metrics("Model")["p@10"] == 0.9

    def test_unknown_model_returns_empty_dict(self):
        """get_metrics for unknown model returns empty dict, not error."""
        agg = ResultsAggregator()
        assert agg.get_metrics("NonExistent") == {}

    # --- Format: markdown ---

    def test_markdown_table_has_header_separator_and_rows(self):
        """Markdown table includes pipe-delimited header, separator, and data rows."""
        agg = ResultsAggregator()
        agg.add_model_results("ModelA", {"precision@10": 0.5})
        agg.add_model_results("ModelB", {"precision@10": 0.7})
        table = agg.generate_comparison_table(fmt="markdown")
        lines = table.split("\n")
        assert len(lines) >= 3  # header + separator + at least one data row
        assert lines[0].startswith("|")  # header row
        assert "|-" in table  # separator row (pipe then dash)
        assert "ModelA" in table
        assert "ModelB" in table
        assert "precision@10" in table

    def test_markdown_default_format(self):
        """Default format (no argument) produces markdown table."""
        agg = ResultsAggregator()
        agg.add_model_results("M", {"p@10": 0.5})
        table = agg.generate_comparison_table()
        assert table.startswith("|")

    # --- Format: plain ---

    def test_plain_text_table_has_columns_and_separator(self):
        """Plain text table includes metric column header and dashed separator."""
        agg = ResultsAggregator()
        agg.add_model_results("ModelA", {"p@10": 0.5})
        agg.add_model_results("ModelB", {"p@10": 0.7})
        table = agg.generate_comparison_table(fmt="plain")
        assert "Metric" in table
        assert "ModelA" in table
        assert "ModelB" in table
        assert "----" in table  # some separator dashes

    def test_plain_text_aligns_columns(self):
        """Plain text values appear as strings in correct column positions."""
        agg = ResultsAggregator()
        agg.add_model_results("X", {"m1": 0.5, "m2": 0.9})
        agg.add_model_results("Y", {"m1": 0.3})
        table = agg.generate_comparison_table(fmt="plain")
        assert "0.5" in table
        assert "0.9" in table
        assert "0.3" in table

    # --- Format: json ---

    def test_json_format_returns_valid_json(self):
        """JSON format returns parseable JSON with all model results."""
        agg = ResultsAggregator()
        agg.add_model_results("ModelA", {"p@10": 0.5})
        agg.add_model_results("ModelB", {"p@10": 0.7})
        json_str = agg.generate_comparison_table(fmt="json")
        parsed = json.loads(json_str)
        assert "ModelA" in parsed
        assert "ModelB" in parsed
        assert parsed["ModelA"]["p@10"] == 0.5

    def test_json_format_multiple_metrics(self):
        """JSON format includes all metrics for each model."""
        agg = ResultsAggregator()
        agg.add_model_results("M", {"p@10": 0.5, "r@10": 0.3, "n@10": 0.4})
        json_str = agg.generate_comparison_table(fmt="json")
        parsed = json.loads(json_str)
        assert parsed["M"] == {"p@10": 0.5, "r@10": 0.3, "n@10": 0.4}

    # --- Edge cases ---

    def test_empty_results_plain(self):
        """Empty aggregator returns appropriate message for plain format."""
        agg = ResultsAggregator()
        assert agg.generate_comparison_table(fmt="plain") == "No results to compare."

    def test_empty_results_json(self):
        """Empty aggregator returns empty JSON array."""
        agg = ResultsAggregator()
        assert agg.generate_comparison_table(fmt="json") == "[]"

    def test_empty_results_markdown(self):
        """Empty aggregator returns empty string for markdown."""
        agg = ResultsAggregator()
        assert agg.generate_comparison_table(fmt="markdown") == ""

    def test_add_empty_metrics_logs_warning(self, caplog):
        """Adding empty metrics dict logs a warning and does not store."""
        agg = ResultsAggregator()
        agg.add_model_results("EmptyModel", {})
        assert "EmptyModel" not in agg.get_model_names()
        assert "Empty metrics" in caplog.text

    # --- to_dict ---

    def test_to_dict_returns_all_results(self):
        """to_dict returns dict of all model results."""
        agg = ResultsAggregator()
        agg.add_model_results("A", {"p": 0.5})
        agg.add_model_results("B", {"p": 0.7})
        assert agg.to_dict() == {"A": {"p": 0.5}, "B": {"p": 0.7}}
