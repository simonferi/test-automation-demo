"""Scenario loading utilities."""

from __future__ import annotations

from pathlib import Path
import yaml

from .models import Scenario


def load_scenario(path: Path) -> Scenario:
    """Load and validate a scenario YAML file."""

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Scenario file {path} must contain a mapping")
    return Scenario.model_validate(data)
