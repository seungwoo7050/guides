#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import stat
from dataclasses import dataclass
from pathlib import Path

GLOB_CHARACTERS = frozenset("*?[]{}!")
PACKAGE_NAME = re.compile(r"^(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*$")


class WorkspaceContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class Workspace:
    name: str
    relative: Path
    path: Path
    install_relative: Path


def _regular_json(path: Path, label: str) -> dict[str, object]:
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise WorkspaceContractError(f"{label} 누락: {path}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise WorkspaceContractError(f"{label}가 regular non-symlink file이 아닙니다: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise WorkspaceContractError(f"{label} JSON을 읽지 못했습니다: {error}") from error
    if not isinstance(value, dict):
        raise WorkspaceContractError(f"{label} JSON이 object가 아닙니다.")
    return value


def _safe_relative(raw: object) -> Path:
    if not isinstance(raw, str) or not raw or raw != raw.strip():
        raise WorkspaceContractError(f"workspace path가 non-empty trimmed string이 아닙니다: {raw!r}")
    if "\\" in raw or any(character in raw for character in GLOB_CHARACTERS):
        raise WorkspaceContractError(f"workspace path에 glob/backslash를 허용하지 않습니다: {raw!r}")
    segments = raw.split("/")
    if raw.startswith("/") or any(segment in ("", ".", "..") for segment in segments):
        raise WorkspaceContractError(f"workspace path가 안전한 repo-relative path가 아닙니다: {raw!r}")
    if any(":" in segment or "\x00" in segment for segment in segments):
        raise WorkspaceContractError(f"workspace path에 허용하지 않는 문자가 있습니다: {raw!r}")
    return Path(*segments)


def _install_relative(name: object) -> tuple[str, Path]:
    if not isinstance(name, str) or not PACKAGE_NAME.fullmatch(name):
        raise WorkspaceContractError(f"workspace package name이 안전한 npm name이 아닙니다: {name!r}")
    parts = name.split("/")
    return name, Path(*parts)


def load_declared_workspaces(root: Path) -> tuple[Workspace, ...]:
    root = root.resolve(strict=True)
    package = _regular_json(root / "package.json", "root package.json")
    raw_workspaces = package.get("workspaces")
    if not isinstance(raw_workspaces, list) or not raw_workspaces:
        raise WorkspaceContractError("root package.json workspaces는 explicit non-empty list여야 합니다.")

    workspaces: list[Workspace] = []
    seen_paths: set[Path] = set()
    seen_names: set[str] = set()
    for raw in raw_workspaces:
        relative = _safe_relative(raw)
        if relative in seen_paths:
            raise WorkspaceContractError(f"duplicate workspace path: {relative}")
        candidate = root / relative
        current = root
        for part in relative.parts:
            current /= part
            try:
                metadata = current.lstat()
            except FileNotFoundError as error:
                raise WorkspaceContractError(f"workspace path 누락: {relative}") from error
            if stat.S_ISLNK(metadata.st_mode):
                raise WorkspaceContractError(f"workspace path component symlink는 허용하지 않습니다: {current}")
        if not candidate.is_dir():
            raise WorkspaceContractError(f"workspace가 directory가 아닙니다: {relative}")
        resolved = candidate.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as error:
            raise WorkspaceContractError(f"workspace가 repository 밖입니다: {relative} -> {resolved}") from error
        child_package = _regular_json(candidate / "package.json", f"workspace {relative} package.json")
        name, install_relative = _install_relative(child_package.get("name"))
        if name in seen_names:
            raise WorkspaceContractError(f"duplicate workspace package name: {name}")
        seen_paths.add(relative)
        seen_names.add(name)
        workspaces.append(
            Workspace(
                name=name,
                relative=relative,
                path=resolved,
                install_relative=install_relative,
            )
        )
    return tuple(workspaces)
