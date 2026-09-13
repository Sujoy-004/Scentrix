"""Tests for EvalConfig loading and validation."""
import yaml
import pytest
from pathlib import Path

from ml.eval.config import EvalConfig


class TestEvalConfigDefaults:
    def test_default_values(self, sample_config):
        """Default config has correct cold_ratio, seed, etc."""
        assert sample_config.cold_ratio == 0.2
        assert sample_config.min_stratum_size == 10
        assert sample_config.seed == 42
        assert sample_config.k_values == [10]
        assert sample_config.split_strategy == "stratified_leave_cold_out"


class TestEvalConfigYaml:
    def test_yaml_loading(self, tmp_path):
        """Config loads from YAML with correct values."""
        yaml_path = tmp_path / "eval_config.yaml"
        yaml_data = {"cold_ratio": 0.3, "seed": 123, "min_stratum_size": 5}
        with open(yaml_path, "w") as f:
            yaml.dump(yaml_data, f)
        config = EvalConfig.from_yaml(yaml_path)
        assert config.cold_ratio == 0.3
        assert config.seed == 123
        assert config.min_stratum_size == 5

    def test_missing_yaml_uses_defaults(self, tmp_path):
        """Missing YAML file returns default config."""
        config = EvalConfig.from_yaml(tmp_path / "nonexistent.yaml")
        assert config.cold_ratio == 0.2


class TestEvalConfigValidation:
    def test_invalid_cold_ratio_raises(self):
        """cold_ratio must be between 0 and 1."""
        with pytest.raises(ValueError):
            EvalConfig(cold_ratio=0.0)
        with pytest.raises(ValueError):
            EvalConfig(cold_ratio=1.0)
        with pytest.raises(ValueError):
            EvalConfig(cold_ratio=-0.1)
        with pytest.raises(ValueError):
            EvalConfig(cold_ratio=1.5)

    def test_invalid_min_stratum_size_raises(self):
        """min_stratum_size must be >= 1."""
        with pytest.raises(ValueError):
            EvalConfig(min_stratum_size=0)
        with pytest.raises(ValueError):
            EvalConfig(min_stratum_size=-1)
