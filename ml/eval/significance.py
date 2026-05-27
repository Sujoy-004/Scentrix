"""Bootstrap significance testing for model comparison."""

import logging
from typing import Optional

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class BootstrapSignificance:
    def __init__(self, n_resamples: int = 10000, random_seed: Optional[int] = None):
        self.n_resamples = n_resamples
        self._rng = np.random.default_rng(random_seed)

    def paired_bca_test(
        self, model_a_scores: list[float], model_b_scores: list[float]
    ) -> float:
        if len(model_a_scores) != len(model_b_scores):
            raise ValueError("Scores must have same length for paired test")
        n = len(model_a_scores)
        if n < 2:
            return 1.0

        diffs = np.array(model_a_scores) - np.array(model_b_scores)
        observed = np.mean(diffs)
        if observed == 0:
            return 1.0

        count = 0
        for _ in range(self.n_resamples):
            signs = self._rng.choice([-1, 1], size=n)
            resampled = diffs * signs
            if np.mean(resampled) >= observed:
                count += 1
        return (count + 1) / (self.n_resamples + 1)

    def confidence_interval(
        self,
        model_a_scores: list[float],
        model_b_scores: list[float],
        confidence: float = 0.95,
    ) -> tuple[float, float]:
        if len(model_a_scores) != len(model_b_scores):
            raise ValueError("Scores must have same length for paired test")
        n = len(model_a_scores)
        if n < 2:
            return (0.0, 0.0)

        diffs = np.array(model_a_scores) - np.array(model_b_scores)

        bootstrap_means: list[float] = []
        for _ in range(self.n_resamples):
            idx = self._rng.integers(0, n, size=n)
            bootstrap_means.append(float(np.mean(diffs[idx])))

        sorted_means = np.sort(bootstrap_means)
        alpha = 1 - confidence
        lower = float(np.percentile(sorted_means, 100 * alpha / 2))
        upper = float(np.percentile(sorted_means, 100 * (1 - alpha / 2)))
        return (lower, upper)

    def effect_size(self, model_a_scores: list[float], model_b_scores: list[float]) -> float:
        a = np.array(model_a_scores, dtype=float)
        b = np.array(model_b_scores, dtype=float)
        diff = np.mean(a) - np.mean(b)
        pooled_std = np.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2)
        if pooled_std == 0:
            return 0.0
        return float(diff / pooled_std)
