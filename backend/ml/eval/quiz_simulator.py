"""Quiz simulation layer for quiz-initialized cold-start evaluation.

Generates per-accord confidence vectors that simulate user quiz responses.
This is the programmatic simulation layer per D-08 — no Docker or backend runtime.
"""

import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class QuizSimulator:
    """Generates 48-dim per-accord confidence vectors simulating user quiz responses.

    Samples accords from the dataset accord distribution, assigns confidence scores
    with configurable noise. The output is a 48-dim vector where each entry reflects
    simulated user preference for that accord category (D-09).

    Parameterized by quiz_length (num accords sampled) and quiz_noise (score noise level).
    """

    def __init__(
        self,
        all_accords: list[str],
        seed: Optional[int] = None,
    ):
        """Initialize with the full set of unique accord labels.

        Args:
            all_accords: Sorted list of unique accord strings (48 primary accords).
                This determines the dimension of the output confidence vector.
            seed: Random seed for reproducibility. If None, uses numpy default.
        """
        self.all_accords = sorted(all_accords)
        self.n_accords = len(self.all_accords)
        self._rng = np.random.default_rng(seed)
        logger.info(
            "QuizSimulator initialized with %d accords (seed=%s)",
            self.n_accords, seed,
        )

    def simulate(
        self,
        quiz_length: int,
        quiz_noise: float = 0.1,
    ) -> np.ndarray:
        """Generate a simulated quiz confidence vector.

        Samples `quiz_length` accords uniformly from the accord set, assigns each
        a high base confidence score (0.7–1.0), and adds Gaussian noise scaled by
        `quiz_noise`. Unsampled accords get low base scores (0.0–0.1) plus noise.
        Final values are clipped to [0.0, 1.0].

        Args:
            quiz_length: Number of accords to sample (k ∈ {1, 3, 5, 7, 10}).
            quiz_noise: Standard deviation of Gaussian noise added to scores.
                Default 0.1.

        Returns:
            np.ndarray of shape (n_accords,) with float32 values in [0.0, 1.0].
        """
        confidence = self._rng.uniform(0.0, 0.1, size=self.n_accords).astype(np.float32)

        if quiz_length <= 0 or quiz_length > self.n_accords:
            logger.warning(
                "quiz_length=%d out of range (max=%d) — clamping",
                quiz_length, self.n_accords,
            )
            quiz_length = max(1, min(quiz_length, self.n_accords))

        sampled_indices = self._rng.choice(
            self.n_accords, size=quiz_length, replace=False,
        )
        confidence[sampled_indices] = self._rng.uniform(
            0.7, 1.0, size=quiz_length,
        ).astype(np.float32)

        noise = self._rng.normal(0.0, quiz_noise, size=self.n_accords).astype(np.float32)
        confidence = np.clip(confidence + noise, 0.0, 1.0)

        logger.debug(
            "Quiz simulation: length=%d, noise=%.2f, sampled=%d, mean_conf=%.3f",
            quiz_length, quiz_noise, len(sampled_indices), float(confidence.mean()),
        )

        self._last_confidence = confidence
        return confidence

    def get_accord_confidence(self, accord: str) -> float:
        """Return quiz confidence score for a single accord label."""
        if not hasattr(self, '_last_confidence') or self._last_confidence is None:
            raise RuntimeError("simulate() must be called before get_accord_confidence()")
        if accord not in self.all_accords:
            return 0.0
        idx = self.all_accords.index(accord)
        return float(self._last_confidence[idx])
