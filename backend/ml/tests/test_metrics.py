"""Tests for metric computation via ranx."""
import numpy as np
import pytest

from ml.eval.metrics import MetricsWrapper


class TestMetricsWrapperInit:
    """MetricsWrapper construction."""

    def test_default_k_values(self):
        m = MetricsWrapper()
        assert m.k_values == [10]
        assert "precision@10" in m._metric_list

    def test_custom_k_values(self):
        m = MetricsWrapper(k_values=[5, 10, 20])
        assert 5 in m.k_values
        assert "ndcg@5" in m._metric_list
        assert "recall@20" in m._metric_list

    def test_multiple_k_generates_correct_metrics(self):
        m = MetricsWrapper(k_values=[5, 10])
        expected = {"precision@5", "ndcg@5", "recall@5", "precision@10", "ndcg@10", "recall@10"}
        assert set(m._metric_list) == expected


class TestMetricsComputeAggregate:
    """Aggregate metric computation (ranx evaluate)."""

    def test_all_cold_in_top10(self, mock_scores):
        scores, cold_ids = mock_scores
        m = MetricsWrapper(k_values=[10])
        result = m.compute(cold_ids, scores)
        agg = result["aggregate_metrics"]
        assert agg["Precision@10"] == 1.0
        assert agg["NDCG@10"] > 0.9
        assert agg["Recall@10"] == 1.0

    def test_no_cold_in_top10(self):
        cold_ids = [f"cold_{i}" for i in range(5)]
        scores = {f"cold_{i}": 0.01 for i in range(5)}
        scores.update({f"warm_{i}": 1.0 for i in range(20)})
        m = MetricsWrapper(k_values=[10])
        result = m.compute(cold_ids, scores)
        agg = result["aggregate_metrics"]
        assert agg["Precision@10"] == 0.0
        assert agg["NDCG@10"] == 0.0

    def test_mixed_ranking(self):
        cold_ids = [f"cold_{i}" for i in range(20)]
        scores = {}
        for i in range(5):
            scores[f"cold_{i}"] = 1.0 - i * 0.01
        for i in range(5, 20):
            scores[f"cold_{i}"] = 0.01
        for i in range(20):
            scores[f"warm_{i}"] = 0.5 + i * 0.01
        m = MetricsWrapper(k_values=[10])
        result = m.compute(cold_ids, scores)
        agg = result["aggregate_metrics"]
        assert agg["Precision@10"] == 0.5
        assert abs(agg["Recall@10"] - 0.25) < 0.01

    def test_no_cold_items(self):
        m = MetricsWrapper(k_values=[10])
        result = m.compute([], {"item_1": 0.5, "item_2": 0.3})
        assert result["aggregate_metrics"] == {}
        assert result["per_item_metrics"] == {}


class TestPerItemMetrics:
    """Per-item metric extraction from ranked positions."""

    def test_per_item_precision_ndcg_recall(self, mock_scores):
        scores, cold_ids = mock_scores
        m = MetricsWrapper(k_values=[10])
        result = m.compute(cold_ids, scores)
        per_item = result["per_item_metrics"]
        assert len(per_item) == 10
        for cid in cold_ids:
            assert cid in per_item
            assert "Precision@10" in per_item[cid]
            assert "NDCG@10" in per_item[cid]
            assert "Recall@10" in per_item[cid]

    def test_per_item_with_strata(self, mock_scores):
        scores, cold_ids = mock_scores
        strata = {cid: "Citrus" for cid in cold_ids[:5]}
        strata.update({cid: "Woody" for cid in cold_ids[5:]})
        m = MetricsWrapper(k_values=[10])
        result = m.compute(cold_ids, scores, strata=strata)
        per_item = result["per_item_metrics"]
        for cid in cold_ids[:5]:
            assert per_item[cid].get("cold_stratum") == "Citrus"
        for cid in cold_ids[5:]:
            assert per_item[cid].get("cold_stratum") == "Woody"

    def test_per_item_metric_values_correct(self):
        cold_ids = ["cold_A", "cold_B"]
        all_scores = {
            "cold_A": 0.9,
            "cold_B": 0.8,
            "warm_1": 0.7,
            "warm_2": 0.6,
        }
        m = MetricsWrapper(k_values=[10])
        result = m.compute(cold_ids, all_scores)
        per_item = result["per_item_metrics"]
        assert per_item["cold_A"]["Precision@10"] == 0.1
        assert per_item["cold_A"]["NDCG@10"] == 1.0 / np.log2(2)
        assert per_item["cold_A"]["Recall@10"] == 1.0
        assert per_item["cold_B"]["Precision@10"] == 0.1
        assert per_item["cold_B"]["NDCG@10"] == 1.0 / np.log2(3)
        assert per_item["cold_B"]["Recall@10"] == 1.0

    def test_per_item_not_in_top10(self):
        cold_ids = ["cold_Z"]
        all_scores = {f"warm_{i}": 0.9 - i * 0.01 for i in range(15)}
        all_scores["cold_Z"] = 0.1
        m = MetricsWrapper(k_values=[10])
        result = m.compute(cold_ids, all_scores)
        per_item = result["per_item_metrics"]
        assert per_item["cold_Z"]["Precision@10"] == 0.0
        assert per_item["cold_Z"]["NDCG@10"] == 0.0
        assert per_item["cold_Z"]["Recall@10"] == 0.0
