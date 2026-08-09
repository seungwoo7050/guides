"""Choose and implement a model library without changing the public report contract."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def load_dataset(dataset: Path, split_manifest: Path) -> Any:
    """Load rows while preserving row_id, entity_id and split identity."""
    raise NotImplementedError("implement dataset loading and split joins")


def fit_candidate(data: Any, config: dict[str, Any]) -> Any:
    """Fit preprocessing and a model using training rows only."""
    raise NotImplementedError("choose a classical or neural implementation profile")


def evaluate_candidate(model: Any, data: Any, *, threshold: float) -> dict[str, Any]:
    """Return structured metrics without changing model or threshold state."""
    raise NotImplementedError("implement validation and final-test evaluation")


def export_bundle(model: Any, destination: Path, metadata: dict[str, Any]) -> None:
    """Export model, fitted preprocessing and contract metadata as one bundle."""
    raise NotImplementedError("implement only after the artifact contract is defined")
