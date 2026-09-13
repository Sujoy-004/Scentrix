"""Tests for cold-start data splitting."""
import pandas as pd
import pytest

from ml.eval.config import EvalConfig
from ml.eval.split import (
    ColdStartSplitter,
    LeaveColdOutStrategy,
    SplitResult,
    TemporalSplitStrategy,
    _check_accord_balance,
    _validate_columns,
)


class TestColumnValidation:
    """D-24, D-25: Fail-fast on missing columns."""

    def test_missing_fragrance_id_raises(self):
        df = pd.DataFrame({"primary_accord": ["Citrus"]})
        with pytest.raises(ValueError, match="fragrance_id"):
            _validate_columns(df)

    def test_missing_primary_accord_raises(self):
        df = pd.DataFrame({"fragrance_id": ["frag_001"]})
        with pytest.raises(ValueError, match="primary_accord"):
            _validate_columns(df)

    def test_both_columns_present_passes(self):
        df = pd.DataFrame({"fragrance_id": ["frag_001"], "primary_accord": ["Citrus"]})
        _validate_columns(df)


class TestAccordBalance:
    """D-21: Warn if any accord >50%."""

    def test_balanced_no_warning(self, caplog):
        df = pd.DataFrame({
            "fragrance_id": [f"frag_{i:04d}" for i in range(10)],
            "primary_accord": ["Citrus"] * 4 + ["Woody"] * 3 + ["Floral"] * 3,
        })
        _check_accord_balance(df)
        assert "represents" not in caplog.text

    def test_imbalanced_logs_warning(self, caplog):
        df = pd.DataFrame({
            "fragrance_id": [f"frag_{i:04d}" for i in range(10)],
            "primary_accord": ["Citrus"] * 7 + ["Woody"] * 3,
        })
        _check_accord_balance(df)
        assert "represents" in caplog.text
        assert "70.0%" in caplog.text


class TestColdStartSplitterIntegration:
    """End-to-end splitter behavior."""

    def test_splitter_with_none_strategy_returns_none(self, sample_config):
        splitter = ColdStartSplitter(strategy=None)
        result = splitter.split(pd.DataFrame(), sample_config)
        assert result is None

    def test_splitter_rejects_missing_columns(self, sample_config):
        strategy = LeaveColdOutStrategy(seed=42)
        splitter = ColdStartSplitter(strategy=strategy)
        df = pd.DataFrame({"wrong_col": ["a", "b"]})
        with pytest.raises(ValueError, match="Missing required columns"):
            splitter.split(df, sample_config)

    def test_splitter_returns_split_result(self, mock_fragrance_df, sample_config):
        strategy = LeaveColdOutStrategy(seed=42)
        splitter = ColdStartSplitter(strategy=strategy)
        result = splitter.split(mock_fragrance_df, sample_config)
        assert isinstance(result, SplitResult)
        assert len(result.warm_items) > 0
        assert len(result.cold_items) > 0


class TestLeaveColdOutStrategy:
    """Core stratified leave-cold-out behavior."""

    def test_cold_ratio_respected(self, mock_fragrance_df):
        config = EvalConfig(cold_ratio=0.2, seed=42)
        strategy = LeaveColdOutStrategy(seed=42)
        result = strategy.split(mock_fragrance_df, config)
        total = len(result.warm_items) + len(result.cold_items)
        actual_ratio = len(result.cold_items) / total
        assert abs(actual_ratio - 0.2) < 0.05

    def test_zero_contamination(self, mock_fragrance_df):
        config = EvalConfig(cold_ratio=0.2, seed=42)
        strategy = LeaveColdOutStrategy(seed=42)
        result = strategy.split(mock_fragrance_df, config)
        overlap = set(result.warm_items) & set(result.cold_items)
        assert len(overlap) == 0

    def test_stratified_preserves_accords(self, mock_fragrance_df):
        config = EvalConfig(cold_ratio=0.2, seed=42)
        strategy = LeaveColdOutStrategy(seed=42)
        result = strategy.split(mock_fragrance_df, config)
        warm_accords = result.warm_df["primary_accord"].value_counts(normalize=True)
        cold_accords = result.cold_df["primary_accord"].value_counts(normalize=True)
        for accord in mock_fragrance_df["primary_accord"].unique():
            assert accord in warm_accords.index, f"{accord} missing from warm"
            assert accord in cold_accords.index, f"{accord} missing from cold"

    def test_different_seeds_different_splits(self, mock_fragrance_df):
        config = EvalConfig(cold_ratio=0.2, seed=42)
        strat1 = LeaveColdOutStrategy(seed=42)
        strat2 = LeaveColdOutStrategy(seed=99)
        result1 = strat1.split(mock_fragrance_df, config)
        result2 = strat2.split(mock_fragrance_df, config)
        assert set(result1.cold_items) != set(result2.cold_items)

    def test_same_seed_same_split(self, mock_fragrance_df):
        config = EvalConfig(cold_ratio=0.2, seed=42)
        strat1 = LeaveColdOutStrategy(seed=42)
        strat2 = LeaveColdOutStrategy(seed=42)
        result1 = strat1.split(mock_fragrance_df, config)
        result2 = strat2.split(mock_fragrance_df, config)
        assert set(result1.cold_items) == set(result2.cold_items)
        assert set(result1.warm_items) == set(result2.warm_items)

    def test_warm_plus_cold_equals_all(self, mock_fragrance_df):
        config = EvalConfig(cold_ratio=0.2, seed=42)
        strategy = LeaveColdOutStrategy(seed=42)
        result = strategy.split(mock_fragrance_df, config)
        all_ids = set(result.warm_items) | set(result.cold_items)
        assert len(all_ids) == len(mock_fragrance_df)
        assert len(result.warm_items) + len(result.cold_items) == len(mock_fragrance_df)

    def test_stratified_ratios_per_accord(self, mock_fragrance_df):
        config = EvalConfig(cold_ratio=0.2, seed=42)
        strategy = LeaveColdOutStrategy(seed=42)
        result = strategy.split(mock_fragrance_df, config)
        cold_df = result.cold_df
        for accord in mock_fragrance_df["primary_accord"].unique():
            total = len(mock_fragrance_df[mock_fragrance_df["primary_accord"] == accord])
            n_cold = len(cold_df[cold_df["primary_accord"] == accord])
            stratum_ratio = n_cold / total
            assert abs(stratum_ratio - 0.2) < 0.15


class TestSmallStratumFallback:
    """D-20, D-26: Small strata fall back to random split."""

    def test_fallback_logs_warning(self, small_stratum_df, caplog):
        config = EvalConfig(min_stratum_size=10, cold_ratio=0.2, seed=42)
        strategy = LeaveColdOutStrategy(seed=42)
        with caplog.at_level("WARNING"):
            strategy.split(small_stratum_df, config)
        assert "min_stratum_size" in caplog.text
        assert "Beeswax" in caplog.text

    def test_small_stratum_still_gets_cold_items(self, small_stratum_df):
        config = EvalConfig(min_stratum_size=10, cold_ratio=0.2, seed=42)
        strategy = LeaveColdOutStrategy(seed=42)
        result = strategy.split(small_stratum_df, config)
        beeswax_cold = result.cold_df[result.cold_df["primary_accord"] == "Beeswax"]
        assert len(beeswax_cold) >= 1

    def test_default_min_stratum_size_10(self, small_stratum_df):
        config = EvalConfig(seed=42)
        strategy = LeaveColdOutStrategy(seed=42)
        result = strategy.split(small_stratum_df, config)
        beeswax_cold = result.cold_df[result.cold_df["primary_accord"] == "Beeswax"]
        assert len(beeswax_cold) >= 1


class TestTemporalSplitStrategy:
    """Secondary strategy: sequential split by fragrance ID."""

    def test_temporal_split_produces_disjoint_sets(self, mock_fragrance_df):
        config = EvalConfig(cold_ratio=0.2, seed=42)
        strategy = TemporalSplitStrategy(seed=42)
        result = strategy.split(mock_fragrance_df, config)
        overlap = set(result.warm_items) & set(result.cold_items)
        assert len(overlap) == 0

    def test_temporal_split_last_fraction_is_cold(self, mock_fragrance_df):
        config = EvalConfig(cold_ratio=0.2, seed=42)
        strategy = TemporalSplitStrategy(seed=42)
        result = strategy.split(mock_fragrance_df, config)
        sorted_ids = sorted(mock_fragrance_df["fragrance_id"].tolist())
        expected_cold_count = max(1, round(len(sorted_ids) * config.cold_ratio))
        assert len(result.cold_items) == expected_cold_count
        assert result.cold_items == sorted_ids[-expected_cold_count:]

    def test_temporal_split_cold_ratio_configurable(self, mock_fragrance_df):
        config = EvalConfig(cold_ratio=0.5, seed=42)
        strategy = TemporalSplitStrategy(seed=42)
        result = strategy.split(mock_fragrance_df, config)
        expected = max(1, round(100 * 0.5))
        assert abs(len(result.cold_items) - expected) <= 1

    def test_temporal_split_warm_plus_cold_equals_all(self, mock_fragrance_df):
        config = EvalConfig(cold_ratio=0.2, seed=42)
        strategy = TemporalSplitStrategy(seed=42)
        result = strategy.split(mock_fragrance_df, config)
        all_ids = set(result.warm_items) | set(result.cold_items)
        assert len(all_ids) == len(mock_fragrance_df)


class TestSplitResult:
    """SplitResult dataclass behavior."""

    def test_zero_contamination_enforced(self):
        with pytest.raises(ValueError, match="Zero-contamination"):
            SplitResult(
                warm_items=["a", "b"],
                cold_items=["b", "c"],
                warm_df=pd.DataFrame(),
                cold_df=pd.DataFrame(),
            )

    def test_no_overlap_passes(self):
        result = SplitResult(
            warm_items=["a", "b"],
            cold_items=["c", "d"],
            warm_df=pd.DataFrame(),
            cold_df=pd.DataFrame(),
        )
        assert len(result.warm_items) == 2
        assert len(result.cold_items) == 2
