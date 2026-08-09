from __future__ import annotations

from pathlib import Path


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def exercise_root() -> Path:
    return workspace_root().parent


def fixtures_dir() -> Path:
    return exercise_root() / "fixtures"


def reports_dir() -> Path:
    return workspace_root() / "reports"


def bundle_dir() -> Path:
    return workspace_root() / "artifacts" / "model-bundle"
