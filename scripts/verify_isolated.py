#!/usr/bin/env python3
"""Run mandatory verification in a disposable copy without touching learner work."""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

from source_fingerprint import UnsafeTreeError, fingerprint

ROOT = Path(__file__).resolve().parents[1]
MARKER = ROOT / '.guide/platform-engineering/prepared.json'
WORKSPACE = ROOT / '.workspace'


class IsolationError(RuntimeError):
    pass


def strict_json(path: Path) -> Any:
    def no_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise IsolationError(f'duplicate JSON key in {path}: {key}')
            result[key] = value
        return result

    def no_constant(value: str) -> None:
        raise IsolationError(f'non-finite JSON number in {path}: {value}')

    try:
        return json.loads(
            path.read_text(encoding='utf-8'),
            object_pairs_hook=no_duplicate,
            parse_constant=no_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IsolationError(f'cannot read preparation marker {path}: {exc}') from exc


def validate_marker(source: tuple[str, int]) -> None:
    for directory in (ROOT / '.guide', ROOT / '.guide/platform-engineering'):
        if directory.is_symlink():
            raise IsolationError(f'preparation path must not be a symlink: {directory}')
        try:
            directory_mode = directory.lstat().st_mode
        except FileNotFoundError as exc:
            raise IsolationError('먼저 ./prepare.sh를 실행하십시오.') from exc
        if not stat.S_ISDIR(directory_mode):
            raise IsolationError(f'preparation path must be a directory: {directory}')
    if MARKER.is_symlink():
        raise IsolationError(f'preparation marker must not be a symlink: {MARKER}')
    try:
        mode = MARKER.lstat().st_mode
    except FileNotFoundError as exc:
        raise IsolationError('먼저 ./prepare.sh를 실행하십시오.') from exc
    if not stat.S_ISREG(mode):
        raise IsolationError(f'preparation marker is not a regular file: {MARKER}')
    marker = strict_json(MARKER)
    if not isinstance(marker, dict):
        raise IsolationError('preparation marker must be a JSON object')
    expected_keys = {
        'schemaVersion', 'guide', 'python', 'sourceSha256', 'sourceFiles', 'preparation',
    }
    if set(marker) != expected_keys:
        raise IsolationError('preparation marker has unknown or missing fields')
    if marker.get('schemaVersion') != 1 or marker.get('guide') != 'platform-engineering':
        raise IsolationError('preparation marker identifies the wrong guide or schema')
    if marker.get('sourceSha256') != source[0] or marker.get('sourceFiles') != source[1]:
        raise IsolationError(
            'prepare 이후 source가 바뀌었습니다. 변경을 검토한 뒤 ./prepare.sh를 다시 실행하십시오.'
        )


def workspace_fingerprint() -> tuple[str, int] | None:
    if WORKSPACE.is_symlink():
        raise IsolationError('.workspace must not be a symlink')
    if not WORKSPACE.exists():
        return None
    if not WORKSPACE.is_dir():
        raise IsolationError('.workspace must be a directory')
    return fingerprint(WORKSPACE, excluded_dirs=frozenset(), excluded_files=frozenset())


def ignore_generated(_directory: str, names: list[str]) -> set[str]:
    excluded = {'.git', '.guide', '.workspace', '__pycache__', '.DS_Store'}
    return set(names).intersection(excluded)


def external_temp_root(candidates: Iterable[Path] | None = None) -> Path:
    choices = list(candidates) if candidates is not None else [
        Path(tempfile.gettempdir()), Path('/private/tmp'), Path('/tmp'),
    ]
    inspected: set[Path] = set()
    for candidate in choices:
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if resolved in inspected:
            continue
        inspected.add(resolved)
        if not resolved.is_dir():
            continue
        if resolved == ROOT or ROOT in resolved.parents:
            continue
        return resolved
    raise IsolationError('no existing temporary directory outside the repository is available')


def run() -> None:
    source_before = fingerprint(ROOT)
    workspace_before = workspace_fingerprint()
    validate_marker(source_before)

    temporary_root = external_temp_root()
    with tempfile.TemporaryDirectory(
        prefix='platform-engineering-verify-',
        dir=temporary_root,
    ) as temporary:
        copy = Path(temporary) / 'source'
        shutil.copytree(
            ROOT,
            copy,
            symlinks=True,
            ignore=ignore_generated,
            copy_function=shutil.copy2,
        )
        copied = fingerprint(copy)
        if copied != source_before:
            raise IsolationError('isolated copy fingerprint differs from prepared source')

        environment = os.environ.copy()
        for key in ('PYTHONHOME', 'PYTHONPATH', 'PYTHONSTARTUP', 'PYTHONINSPECT'):
            environment.pop(key, None)
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        environment['PYTHONNOUSERSITE'] = '1'
        for key in ('TMPDIR', 'TEMP', 'TMP'):
            environment[key] = str(temporary_root)
        result = subprocess.run(
            [sys.executable, 'scripts/verify_repository.py', '--quick'],
            cwd=copy,
            env=environment,
            capture_output=True,
            text=True,
            timeout=240,
        )
        if result.stdout:
            print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr)
        if result.returncode != 0:
            raise IsolationError(f'isolated mandatory verification failed with exit {result.returncode}')

    source_after = fingerprint(ROOT)
    workspace_after = workspace_fingerprint()
    if source_after != source_before:
        raise IsolationError('verification modified tracked or untracked source files')
    if workspace_after != workspace_before:
        raise IsolationError('verification modified learner workspace files')
    print(
        'OK isolated=true '
        f'source_files={source_after[1]} workspace_preserved=true mandatory_skips=0'
    )


def main() -> int:
    try:
        run()
    except (IsolationError, UnsafeTreeError, OSError, subprocess.TimeoutExpired) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
