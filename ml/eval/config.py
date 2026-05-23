"""Configuration for cold-start evaluation pipeline."""

import logging
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class EvalConfig(BaseSettings):
    model_config = {"env_prefix": "SCENTRIX_EVAL_"}

    cold_ratio: float = Field(default=0.2, ge=0.0, le=1.0)
    min_stratum_size: int = Field(default=10, ge=1)
    split_strategy: str = "stratified_leave_cold_out"
    k_values: list[int] = [10]
    seed: int = 42
    data_path: str = "ml/data/scentrix_master_cleaned.json"
    output_dir: str = "ml/eval/runs"

    @field_validator("cold_ratio")
    @classmethod
    def validate_cold_ratio(cls, v: float) -> float:
        if v <= 0.0 or v >= 1.0:
            raise ValueError(f"cold_ratio must be between 0 and 1 (exclusive), got {v}")
        return v

    @field_validator("min_stratum_size")
    @classmethod
    def validate_min_stratum_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"min_stratum_size must be >= 1, got {v}")
        return v

    @classmethod
    def from_yaml(cls, path: Path) -> "EvalConfig":
        if not path.exists():
            logger.warning("Config file not found at %s — using defaults", path)
            return cls()
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)
