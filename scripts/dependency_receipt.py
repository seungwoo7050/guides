#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

from workspace_contract import WorkspaceContractError, load_declared_workspaces

ROOT = Path(__file__).resolve().parents[1]
BINARIES = ("expo", "jest", "tsc")


class DependencyReceiptError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise DependencyReceiptError(f"dependency receipt 대상이 regular file이 아닙니다: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _contained(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def installation_receipt(root: Path = ROOT) -> dict[str, object]:
    root = root.resolve(strict=True)
    node_modules = root / "node_modules"
    if node_modules.is_symlink() or not node_modules.is_dir():
        raise DependencyReceiptError("node_modules가 실제 directory가 아닙니다. ./prepare.sh가 필요합니다.")
    installed_lock = node_modules / ".package-lock.json"
    if installed_lock.is_symlink() or not installed_lock.is_file():
        raise DependencyReceiptError("node_modules/.package-lock.json installation receipt가 없습니다.")

    try:
        declared_workspaces = load_declared_workspaces(root)
    except WorkspaceContractError as error:
        raise DependencyReceiptError(str(error)) from error
    workspace_targets: dict[str, str] = {}
    for workspace in declared_workspaces:
        canonical = workspace.path
        link = node_modules / workspace.install_relative
        if not link.exists() and not link.is_symlink():
            raise DependencyReceiptError(f"workspace install link가 없습니다: {link.relative_to(root)}")
        actual = link.resolve(strict=True)
        if actual != canonical:
            raise DependencyReceiptError(
                f"workspace install link target 불일치: {link.relative_to(root)} -> {actual}; expected={canonical}"
            )
        workspace_targets[workspace.name] = canonical.relative_to(root).as_posix()

    bin_targets: dict[str, dict[str, str]] = {}
    node_modules_root = node_modules.resolve(strict=True)
    for name in BINARIES:
        binary = node_modules / ".bin" / name
        if not binary.exists() and not binary.is_symlink():
            raise DependencyReceiptError(f"필수 dependency binary가 없습니다: {binary.relative_to(root)}")
        resolved = binary.resolve(strict=True)
        if not _contained(resolved, node_modules_root):
            raise DependencyReceiptError(
                f"dependency binary가 node_modules 밖을 가리킵니다: {binary.relative_to(root)} -> {resolved}"
            )
        metadata = resolved.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise DependencyReceiptError(f"dependency binary target가 regular file이 아닙니다: {resolved}")
        bin_targets[name] = {
            "target": resolved.relative_to(node_modules_root).as_posix(),
            "sha256": sha256(resolved),
        }

    return {
        "schema": 2,
        "installed_lock_sha256": sha256(installed_lock),
        "workspace_targets": workspace_targets,
        "selected_bin_targets": bin_targets,
        "trust_limit": (
            "npm ci와 package-lock integrity를 신뢰하며 registry package 전체 content를 다시 hash하지 않는다; "
            "workspace realpath, installed lock, selected executable target만 재검사한다."
        ),
    }
