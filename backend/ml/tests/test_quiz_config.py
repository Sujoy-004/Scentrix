"""Tests for EvalConfig quiz fields (PIPE-03) and QuizSimulator (RSCH-03)."""

import numpy as np
import pydantic
import pytest

from ml.eval.config import EvalConfig
from ml.eval.quiz_simulator import QuizSimulator

# ── PIPE-03: EvalConfig Quiz Fields ─────────────────────────────────────────

ACCORDS_48 = [
    "Aldehydes", "Amber", "Animalic", "Aquatic", "Aromatic", "Balm",
    "Balsamic", "Bitter", "Camphor", "Citrus", "Coffee", "Conifer",
    "Creamy", "Earthy", "Floral", "Frankincense", "Fresh", "Fruity",
    "Gourmand", "Grassy", "Green", "Herbal", "Honey", "Incense",
    "Iris", "Lactic", "Lavender", "Leather", "Marine", "Medicinal",
    "Metallic", "Mossy", "Musk", "Myrrh", "Nutty", "Ozonic",
    "Peppery", "Powdery", "Resinous", "Rose", "Smoky", "Soapy",
    "Spicy", "Sulfurous", "Tea", "Tobacco", "Vanilla", "Woody",
]


class TestEvalConfigQuizFields:
    """PIPE-03: EvalConfig accepts evaluation_mode, quiz_length, quiz_noise."""

    def test_default_evaluation_mode_is_pure_cold(self):
        """Default evaluation_mode is 'pure_cold'."""
        config = EvalConfig()
        assert config.evaluation_mode == "pure_cold"

    def test_accepts_valid_evaluation_modes(self):
        """All valid evaluation modes are accepted."""
        for mode in ("pure_cold", "quiz_init", "warm_ref"):
            config = EvalConfig(evaluation_mode=mode)
            assert config.evaluation_mode == mode

    def test_rejects_invalid_evaluation_mode(self):
        """Invalid evaluation_mode raises ValidationError."""
        for invalid_mode in ("hot_start", "PURE_COLD", "quiz init", "", "pure_cold "):
            with pytest.raises(pydantic.ValidationError):
                EvalConfig(evaluation_mode=invalid_mode)

    def test_default_quiz_length_is_5(self):
        """Default quiz_length is 5."""
        config = EvalConfig()
        assert config.quiz_length == 5

    def test_quiz_length_accepts_valid_range(self):
        """quiz_length accepts values 1 through 10."""
        for length in (1, 3, 5, 7, 10):
            config = EvalConfig(quiz_length=length)
            assert config.quiz_length == length

    def test_quiz_length_rejects_below_minimum(self):
        """quiz_length < 1 raises ValidationError."""
        with pytest.raises(pydantic.ValidationError):
            EvalConfig(quiz_length=0)
        with pytest.raises(pydantic.ValidationError):
            EvalConfig(quiz_length=-1)

    def test_quiz_length_rejects_above_maximum(self):
        """quiz_length > 10 raises ValidationError."""
        with pytest.raises(pydantic.ValidationError):
            EvalConfig(quiz_length=11)
        with pytest.raises(pydantic.ValidationError):
            EvalConfig(quiz_length=100)

    def test_default_quiz_noise_is_0_1(self):
        """Default quiz_noise is 0.1."""
        config = EvalConfig()
        assert config.quiz_noise == 0.1

    def test_quiz_noise_accepts_boundary_values(self):
        """quiz_noise accepts boundary values 0.0 and 1.0."""
        config_low = EvalConfig(quiz_noise=0.0)
        assert config_low.quiz_noise == 0.0
        config_high = EvalConfig(quiz_noise=1.0)
        assert config_high.quiz_noise == 1.0

    def test_quiz_noise_rejects_negative(self):
        """quiz_noise < 0 raises ValidationError."""
        with pytest.raises(pydantic.ValidationError):
            EvalConfig(quiz_noise=-0.01)

    def test_quiz_noise_rejects_above_one(self):
        """quiz_noise > 1 raises ValidationError."""
        with pytest.raises(pydantic.ValidationError):
            EvalConfig(quiz_noise=1.01)

    def test_can_set_all_quiz_fields_together(self):
        """All three quiz fields can be set in one config."""
        config = EvalConfig(
            evaluation_mode="quiz_init",
            quiz_length=7,
            quiz_noise=0.3,
        )
        assert config.evaluation_mode == "quiz_init"
        assert config.quiz_length == 7
        assert config.quiz_noise == 0.3


# ── RSCH-03: QuizSimulator ───────────────────────────────────────────────

class TestQuizSimulator:
    """RSCH-03: QuizSimulator generates 48-dim float32 confidence vectors."""

    def test_output_shape_is_48(self):
        """Generated vector has shape (48,) for 48 accords."""
        sim = QuizSimulator(all_accords=ACCORDS_48, seed=42)
        result = sim.simulate(quiz_length=5)
        assert result.shape == (48,)

    def test_output_dtype_is_float32(self):
        """Generated vector dtype is float32."""
        sim = QuizSimulator(all_accords=ACCORDS_48, seed=42)
        result = sim.simulate(quiz_length=5)
        assert result.dtype == np.float32

    def test_output_values_in_0_to_1_range(self):
        """All values in output vector are in [0.0, 1.0]."""
        sim = QuizSimulator(all_accords=ACCORDS_48, seed=42)
        result = sim.simulate(quiz_length=5)
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_same_seed_gives_same_result(self):
        """Same seed produces identical vectors."""
        sim1 = QuizSimulator(all_accords=ACCORDS_48, seed=123)
        sim2 = QuizSimulator(all_accords=ACCORDS_48, seed=123)
        r1 = sim1.simulate(quiz_length=5)
        r2 = sim2.simulate(quiz_length=5)
        np.testing.assert_array_equal(r1, r2)

    def test_different_seed_gives_different_result(self):
        """Different seeds produce different vectors."""
        sim1 = QuizSimulator(all_accords=ACCORDS_48, seed=42)
        sim2 = QuizSimulator(all_accords=ACCORDS_48, seed=999)
        r1 = sim1.simulate(quiz_length=5)
        r2 = sim2.simulate(quiz_length=5)
        assert not np.allclose(r1, r2)

    def test_seed_none_gives_varying_results(self):
        """No seed (None) gives different results on successive calls."""
        sim = QuizSimulator(all_accords=ACCORDS_48, seed=None)
        r1 = sim.simulate(quiz_length=5)
        r2 = sim.simulate(quiz_length=5)
        # With no seed, each call may differ; this is a probabilistic check
        # but should almost always pass with 48 dims
        assert not np.allclose(r1, r2)

    def test_reproducibility_across_multiple_calls_advances_rng(self):
        """Each simulate() call advances the RNG, producing different results."""
        sim = QuizSimulator(all_accords=ACCORDS_48, seed=42)
        r1 = sim.simulate(quiz_length=5)
        r2 = sim.simulate(quiz_length=5)
        # RNG state advances — different result each time
        assert not np.allclose(r1, r2), (
            "simulate() should advance RNG state each call"
        )

    def test_quiz_length_affects_sampled_high_scores(self):
        """Longer quiz_length produces more high-confidence entries."""
        sim = QuizSimulator(all_accords=ACCORDS_48, seed=42)
        r_short = sim.simulate(quiz_length=1)
        r_long = sim.simulate(quiz_length=10)
        # Longer quiz should have more entries > 0.5
        count_short = int((r_short > 0.5).sum())
        count_long = int((r_long > 0.5).sum())
        assert count_long >= count_short, (
            f"Expected longer quiz ({count_long}) to have at least as many "
            f"high-confidence entries as short quiz ({count_short})"
        )

    def test_quiz_noise_adds_variability(self):
        """Higher quiz_noise produces more variable outputs."""
        sim_low = QuizSimulator(all_accords=ACCORDS_48, seed=42)
        sim_high = QuizSimulator(all_accords=ACCORDS_48, seed=42)
        r_low = sim_low.simulate(quiz_length=5, quiz_noise=0.01)
        r_high = sim_high.simulate(quiz_length=5, quiz_noise=0.9)
        # Higher noise should cause more variance in the output
        std_low = r_low.std()
        std_high = r_high.std()
        assert std_high >= std_low, (
            f"Expected high-noise std ({std_high:.4f}) >= low-noise std ({std_low:.4f})"
        )

    def test_simulate_returns_new_array_each_call(self):
        """Each simulate call returns a new array, not a reference to internal state."""
        sim = QuizSimulator(all_accords=ACCORDS_48, seed=42)
        r1 = sim.simulate(quiz_length=5)
        r2 = sim.simulate(quiz_length=5)
        # They should be equal (same seed) but not the same object
        assert r1 is not r2

    def test_accuracy_of_quiz_length_sampling(self):
        """quiz_length controls how many accords get high confidence scores."""
        sim = QuizSimulator(all_accords=ACCORDS_48, seed=42)
        for length in (1, 3, 5, 7, 10):
            result = sim.simulate(quiz_length=length, quiz_noise=0.001)
            high_conf = int((result > 0.5).sum())
            assert high_conf == length, (
                f"Expected {length} high-confidence entries, got {high_conf}"
            )
