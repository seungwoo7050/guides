from __future__ import annotations

from pathlib import Path


def analyze(metrics_path: Path, components_path: Path, policy_path: Path) -> dict:
    del metrics_path, components_path, policy_path
    return {"findings": []}
