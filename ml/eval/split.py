"""Cold-start data splitting with stratified leave-cold-out and temporal strategies."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from ml.eval.config import EvalConfig

logger = logging.getLogger(__name__)


@dataclass
class SplitResult:
    """Container for split operation results."""
    warm_items: list[str]
    cold_items: list[str]
    warm_df: pd.DataFrame
    cold_df: pd.DataFrame

    def __post_init__(self):
        overlap = set(self.warm_items) & set(self.cold_items)
        if overlap:
            raise ValueError(
                f"Zero-contamination violation: {len(overlap)} items appear in both warm and cold sets"
            )


class SplitStrategy(ABC):
    @abstractmethod
    def split(self, df: pd.DataFrame, config: EvalConfig) -> SplitResult:
        ...


def _validate_columns(df: pd.DataFrame) -> None:
    required = {"fragrance_id", "primary_accord"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"DataFrame must have columns: {required}"
        )


def _check_accord_balance(df: pd.DataFrame) -> None:
    proportions = df["primary_accord"].value_counts(normalize=True)
    max_accord = proportions.idxmax()
    max_pct = proportions.max() * 100
    if max_pct > 50:
        logger.warning(
            "Accord '%s' represents %.1f%% of data (>50%%). "
            "Consider revisiting the stratification field.",
            max_accord, max_pct,
        )


class LeaveColdOutStrategy(SplitStrategy):
    def __init__(self, seed: Optional[int] = None):
        self._rng = np.random.default_rng(seed)

    def split(self, df: pd.DataFrame, config: EvalConfig) -> SplitResult:
        _validate_columns(df)
        _check_accord_balance(df)

        cold_ids: list[str] = []
        warm_ids: list[str] = []
        cold_rows: list[pd.DataFrame] = []
        warm_rows: list[pd.DataFrame] = []

        for accord, group in df.groupby("primary_accord"):
            n = len(group)
            n_cold = max(1, round(n * config.cold_ratio))

            if n < config.min_stratum_size:
                logger.warning(
                    "Stratum '%s' has %d items (< min_stratum_size=%d) — "
                    "falling back to random split within this stratum",
                    accord, n, config.min_stratum_size,
                )

            perm = self._rng.permutation(n)
            cold_idx = perm[:n_cold]
            warm_idx = perm[n_cold:]

            cold_group = group.iloc[cold_idx]
            warm_group = group.iloc[warm_idx]

            cold_ids.extend(cold_group["fragrance_id"].tolist())
            warm_ids.extend(warm_group["fragrance_id"].tolist())
            cold_rows.append(cold_group)
            warm_rows.append(warm_group)

        result = SplitResult(
            warm_items=warm_ids,
            cold_items=cold_ids,
            warm_df=pd.concat(warm_rows, ignore_index=True),
            cold_df=pd.concat(cold_rows, ignore_index=True),
        )

        total = len(warm_ids) + len(cold_ids)
        actual_ratio = len(cold_ids) / total if total > 0 else 0
        logger.info(
            "Split complete: %d warm, %d cold (actual cold ratio: %.3f)",
            len(warm_ids), len(cold_ids), actual_ratio,
        )

        return result


class TemporalSplitStrategy(SplitStrategy):
    def __init__(self, seed: Optional[int] = None, test_ratio: float = 0.2):
        self._rng = np.random.default_rng(seed)
        self._test_ratio = test_ratio

    def split(self, df: pd.DataFrame, config: EvalConfig) -> SplitResult:
        _validate_columns(df)

        sorted_df = df.sort_values("fragrance_id").reset_index(drop=True)
        n = len(sorted_df)
        n_cold = max(1, round(n * config.cold_ratio))

        cold_df = sorted_df.iloc[-n_cold:]
        warm_df = sorted_df.iloc[:-n_cold]

        return SplitResult(
            warm_items=warm_df["fragrance_id"].tolist(),
            cold_items=cold_df["fragrance_id"].tolist(),
            warm_df=warm_df,
            cold_df=cold_df,
        )


class ColdStartSplitter:
    """Accepts a strategy via dependency injection.

    Follows Phase 1's catalog.py pattern: lazy init, graceful None fallback.
    """

    def __init__(self, strategy: Optional["SplitStrategy"] = None):
        self._strategy = strategy
        self._last_result: Optional[SplitResult] = None

    def split(self, df: pd.DataFrame, config: EvalConfig) -> Optional[SplitResult]:
        if self._strategy is None:
            logger.warning("No split strategy configured — returning None")
            return None
        self._last_result = self._strategy.split(df, config)
        return self._last_result
