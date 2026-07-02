"""The detector registry — loaded from the top-level ``models.yaml``.

This is the single source of truth for *which* detectors the benchmark scores,
shared by every scoring script. Contributors add a model by appending an entry
to ``models.yaml`` (a PR), never by editing code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "models.yaml"


@dataclass
class ModelSpec:
    name: str
    hf_id: str
    attack_label: int | list[int]
    params: str | None = None
    gated: bool = False
    notes: str | None = None
    max_length: int | None = None  # None = auto-detect from config.max_position_embeddings


def load_models(path: str | Path | None = None) -> list[ModelSpec]:
    """Load the detector registry from ``models.yaml`` (or a custom path)."""
    import yaml  # PyYAML — declared in pyproject

    data = yaml.safe_load(Path(path or _DEFAULT_PATH).read_text())
    return [ModelSpec(**entry) for entry in data["models"]]
