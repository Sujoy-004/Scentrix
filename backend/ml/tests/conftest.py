"""Shared fixtures for evaluation infrastructure tests."""
import numpy as np
import pandas as pd
import pytest

from ml.eval.config import EvalConfig


@pytest.fixture
def sample_config():
    """Returns EvalConfig with default values."""
    return EvalConfig()


@pytest.fixture
def mock_fragrance_df():
    """Creates a mock DataFrame with 100 fragrances across 5 primary accords.

    Columns: fragrance_id (str), primary_accord (str)
    Distribution: Citrus(30), Gourmand(25), Woody(20), Fruity(15), Floral(10)
    This ensures all strata have >= 10 items.
    """
    np.random.seed(42)
    accords = ["Citrus"] * 30 + ["Gourmand"] * 25 + ["Woody"] * 20 + ["Fruity"] * 15 + ["Floral"] * 10
    fragrance_ids = [f"frag_{i:04d}" for i in range(100)]
    return pd.DataFrame({
        "fragrance_id": fragrance_ids,
        "primary_accord": accords,
    })


@pytest.fixture
def small_stratum_df():
    """Creates a DataFrame where one stratum has <10 items (triggers fallback).

    Columns: fragrance_id (str), primary_accord (str)
    Distribution: Citrus(30), Gourmand(25), Woody(20), Beeswax(5)
    """
    np.random.seed(42)
    accords = ["Citrus"] * 30 + ["Gourmand"] * 25 + ["Woody"] * 20 + ["Beeswax"] * 5
    fragrance_ids = [f"frag_{i:04d}" for i in range(len(accords))]
    return pd.DataFrame({
        "fragrance_id": fragrance_ids,
        "primary_accord": accords,
    })


@pytest.fixture
def mock_scores():
    """Creates mock model scores for 50 items (10 cold, 40 warm).

    Cold items get higher scores to simulate a good model.
    """
    np.random.seed(42)
    cold_ids = [f"cold_{i:04d}" for i in range(10)]
    warm_ids = [f"warm_{i:04d}" for i in range(40)]
    scores = {}
    for cid in cold_ids:
        scores[cid] = float(np.random.uniform(0.7, 1.0))
    for wid in warm_ids:
        scores[wid] = float(np.random.uniform(0.0, 0.3))
    return scores, cold_ids
