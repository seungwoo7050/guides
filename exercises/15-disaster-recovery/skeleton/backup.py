from __future__ import annotations

import shutil
from pathlib import Path


def create_backup(source: Path, destination: Path, backup_id: str, created_at: str) -> Path:
    del created_at
    target = destination / backup_id
    shutil.copytree(source, target)
    return target


def restore_backup(backup_directory: Path, target: Path) -> dict:
    shutil.copytree(backup_directory, target, dirs_exist_ok=True)
    return {"status": "restored"}
