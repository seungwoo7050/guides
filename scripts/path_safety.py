"""Lexical path checks for guide-owned writes and cleanup.

The helpers deliberately inspect the path as the caller spelled it.  Resolving
first would hide an intermediate symlink and could redirect a later write or
recursive delete outside the intended directory.
"""
from __future__ import annotations

import os
from pathlib import Path


class UnsafePathError(RuntimeError):
    """Raised when a writable path contains ambiguous or linked components."""


def lexical_absolute(raw: Path, *, base: Path) -> Path:
    """Return an absolute path without following links or accepting ``..``."""
    expanded = raw.expanduser()
    if ".." in expanded.parts:
        raise UnsafePathError(f"parent traversal is not allowed: {raw}")
    if expanded.is_absolute():
        return expanded
    return base / expanded


def lexical_write_path(raw: Path, *, base: Path) -> tuple[Path, Path]:
    """Return a lexical target and the trusted boundary to inspect from.

    On systems such as macOS, top-level compatibility aliases (notably
    ``/var`` and ``/tmp``) are symlinks.  Only that privileged top-level
    component is canonicalized for an absolute path; every subsequent
    component remains lexical and is therefore auditable.
    """
    expanded = raw.expanduser()
    if ".." in expanded.parts:
        raise UnsafePathError(f"parent traversal is not allowed: {raw}")
    if not expanded.is_absolute():
        return base / expanded, base
    if len(expanded.parts) <= 1:
        anchor = Path(expanded.anchor)
        return anchor, anchor
    top_level = Path(expanded.anchor) / expanded.parts[1]
    boundary = top_level.resolve(strict=True) if top_level.is_symlink() else top_level
    return boundary.joinpath(*expanded.parts[2:]), boundary


def require_no_symlink_components(path: Path, *, boundary: Path | None = None) -> None:
    """Reject every existing symlink from ``boundary`` (or the anchor) to path."""
    if not path.is_absolute():
        raise UnsafePathError(f"path must be absolute: {path}")
    if ".." in path.parts:
        raise UnsafePathError(f"parent traversal is not allowed: {path}")

    if boundary is None:
        current = Path(path.anchor)
        parts = path.parts[1:]
    else:
        if not boundary.is_absolute():
            raise UnsafePathError(f"boundary must be absolute: {boundary}")
        try:
            relative = path.relative_to(boundary)
        except ValueError as exc:
            raise UnsafePathError(f"path escapes boundary: {path}") from exc
        current = boundary
        if current.is_symlink():
            raise UnsafePathError(f"symlink path component is not allowed: {current}")
        parts = relative.parts

    for part in parts:
        current = current / part
        if current.is_symlink():
            raise UnsafePathError(f"symlink path component is not allowed: {current}")


def require_real_directory(path: Path, *, boundary: Path | None = None) -> None:
    """Require an existing, non-linked directory at a checked path."""
    require_no_symlink_components(path, boundary=boundary)
    if not path.is_dir():
        raise UnsafePathError(f"expected a real directory: {path}")


def atomic_write_text(path: Path, text: str, *, boundary: Path) -> None:
    """Replace a guide-owned regular file without following a destination link."""
    require_no_symlink_components(path, boundary=boundary)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    require_no_symlink_components(temporary, boundary=boundary)
    if temporary.exists() or temporary.is_symlink():
        raise UnsafePathError(f"temporary path already exists: {temporary}")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(text)
        require_no_symlink_components(path, boundary=boundary)
        os.replace(temporary, path)
    finally:
        if temporary.exists() and not temporary.is_symlink():
            temporary.unlink()
