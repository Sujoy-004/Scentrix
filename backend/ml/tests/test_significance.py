"""Tests for BootstrapSignificance — paired sign-flip test, CI, Cohen's d effect size."""
import numpy as np
import pytest

from ml.eval.significance import BootstrapSignificance


class TestBootstrapSignificancePairedTest:
    """EVAL-07: BootstrapSignificance paired_bca_test — sign-flip permutation test."""

    def test_identical_scores_return_p_one(self):
        """When both models produce identical scores the p-value is 1.0."""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        bs = BootstrapSignificance(n_resamples=999, random_seed=42)
        p = bs.paired_bca_test(scores, scores)
        assert p == 1.0

    def test_better_model_returns_small_p(self):
        """Model A consistently > Model B gives a p-value < 0.05."""
        a_scores = [0.90, 0.80, 0.85, 0.95, 0.88, 0.92, 0.87, 0.91, 0.86, 0.89]
        b_scores = [0.30, 0.40, 0.35, 0.45, 0.38, 0.42, 0.37, 0.41, 0.36, 0.39]
        bs = BootstrapSignificance(n_resamples=999, random_seed=42)
        p = bs.paired_bca_test(a_scores, b_scores)
        assert p < 0.05

    def test_value_error_on_length_mismatch(self):
        """Mismatched score list lengths raise ValueError."""
        bs = BootstrapSignificance(random_seed=42)
        with pytest.raises(ValueError, match="same length"):
            bs.paired_bca_test([1.0, 2.0], [1.0])

    def test_less_than_two_samples_returns_one(self):
        """Fewer than 2 samples returns p=1.0 (insufficient data)."""
        bs = BootstrapSignificance(random_seed=42)
        assert bs.paired_bca_test([1.0], [2.0]) == 1.0
        assert bs.paired_bca_test([], []) == 1.0

    def test_deterministic_with_seed(self):
        """Same random_seed produces identical p-values across instances."""
        a = [0.90, 0.80, 0.85, 0.95, 0.88, 0.92, 0.87, 0.91, 0.86, 0.89]
        b = [0.30, 0.40, 0.35, 0.45, 0.38, 0.42, 0.37, 0.41, 0.36, 0.39]
        bs1 = BootstrapSignificance(n_resamples=999, random_seed=42)
        bs2 = BootstrapSignificance(n_resamples=999, random_seed=42)
        assert bs1.paired_bca_test(a, b) == bs2.paired_bca_test(a, b)

    def test_empty_lists_return_one(self):
        """Both empty lists return p=1.0 (n<2 case)."""
        bs = BootstrapSignificance(random_seed=42)
        assert bs.paired_bca_test([], []) == 1.0


class TestBootstrapSignificanceConfidenceInterval:
    """EVAL-07: BootstrapSignificance confidence_interval — percentile bootstrap CI."""

    def test_ci_contains_zero_for_identical(self):
        """95% CI for identical scores contains 0."""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        bs = BootstrapSignificance(n_resamples=999, random_seed=42)
        lower, upper = bs.confidence_interval(scores, scores, confidence=0.95)
        assert lower <= 0 <= upper

    def test_ci_positive_when_a_better(self):
        """95% CI entirely above 0 when model_a > model_b consistently."""
        a_scores = [0.90, 0.80, 0.85, 0.95, 0.88]
        b_scores = [0.30, 0.40, 0.35, 0.45, 0.38]
        bs = BootstrapSignificance(n_resamples=999, random_seed=42)
        lower, upper = bs.confidence_interval(a_scores, b_scores, confidence=0.95)
        assert lower > 0, f"Expected CI entirely above 0, got ({lower}, {upper})"

    def test_ci_symmetric_around_true_diff(self):
        """CI for equal models is symmetric around 0."""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        bs = BootstrapSignificance(n_resamples=9999, random_seed=42)
        lower, upper = bs.confidence_interval(scores, scores, confidence=0.95)
        # Should be approximately symmetric: lower ≈ -upper
        assert abs(lower + upper) < 0.01, f"CI ({lower}, {upper}) not symmetric around 0"

    def test_ci_less_than_two_returns_zero(self):
        """Fewer than 2 samples returns (0.0, 0.0)."""
        bs = BootstrapSignificance(random_seed=42)
        assert bs.confidence_interval([1.0], [2.0]) == (0.0, 0.0)
        assert bs.confidence_interval([], []) == (0.0, 0.0)

    def test_ci_value_error_on_mismatch(self):
        """Mismatched lengths raise ValueError for CI as well."""
        bs = BootstrapSignificance(random_seed=42)
        with pytest.raises(ValueError, match="same length"):
            bs.confidence_interval([1.0, 2.0], [1.0])

    def test_confidence_level_affects_width(self):
        """Higher confidence produces wider interval."""
        a = [0.9, 0.8, 0.85, 0.95, 0.88, 0.92, 0.87, 0.91, 0.86, 0.89]
        b = [0.3, 0.4, 0.35, 0.45, 0.38, 0.42, 0.37, 0.41, 0.36, 0.39]
        bs = BootstrapSignificance(n_resamples=999, random_seed=42)
        lo90, hi90 = bs.confidence_interval(a, b, confidence=0.90)
        lo99, hi99 = bs.confidence_interval(a, b, confidence=0.99)
        width90 = hi90 - lo90
        width99 = hi99 - lo99
        assert width99 > width90, "99% CI should be wider than 90% CI"


class TestBootstrapSignificanceEffectSize:
    """EVAL-07: BootstrapSignificance effect_size — Cohen's d."""

    def test_effect_size_zero_for_identical(self):
        """Cohen's d is 0 for identical score distributions."""
        scores = [1.0, 2.0, 3.0]
        bs = BootstrapSignificance(random_seed=42)
        assert bs.effect_size(scores, scores) == 0.0

    def test_effect_size_positive_when_a_better(self):
        """Cohen's d is positive when model_a mean > model_b mean."""
        a_scores = [1.0, 2.0, 3.0]
        b_scores = [0.5, 1.0, 1.5]
        bs = BootstrapSignificance(random_seed=42)
        d = bs.effect_size(a_scores, b_scores)
        assert d > 0

    def test_effect_size_negative_when_b_better(self):
        """Cohen's d is negative when model_b mean > model_a mean."""
        a_scores = [0.5, 1.0, 1.5]
        b_scores = [1.0, 2.0, 3.0]
        bs = BootstrapSignificance(random_seed=42)
        d = bs.effect_size(a_scores, b_scores)
        assert d < 0

    def test_effect_size_zero_variance(self):
        """Cohen's d is 0 when both groups have zero variance (pooled_std=0)."""
        bs = BootstrapSignificance(random_seed=42)
        d = bs.effect_size([1.0, 1.0, 1.0], [2.0, 2.0, 2.0])
        assert d == 0.0

    def test_effect_size_magnitude_increases_with_separation(self):
        """Absolute Cohen's d magnitude increases as groups separate further."""
        bs = BootstrapSignificance(random_seed=42)
        # Both cases: a > b, but far_b is even lower relative to far_a
        close_a = [1.5, 1.6, 1.4]
        close_b = [1.0, 1.1, 0.9]
        far_a = [5.0, 5.1, 4.9]
        far_b = [1.0, 1.1, 0.9]
        d_close = bs.effect_size(close_a, close_b)
        d_far = bs.effect_size(far_a, far_b)
        assert d_close > 0 and d_far > 0, "Both should be positive (a > b)"
        assert d_close < d_far, "More separated groups should have larger Cohen's d"
