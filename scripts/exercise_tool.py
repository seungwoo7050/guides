#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'exercises/manifest.json'


class ExerciseError(RuntimeError):
    pass


def load_items() -> dict[str, dict]:
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    return {item['path']: item for item in data['exercises']}


def resolve_registered(raw: str, items: dict[str, dict]) -> tuple[str, Path, dict]:
    candidate = raw.strip().rstrip('/')
    if candidate.startswith('./'):
        candidate = candidate[2:]
    if candidate not in items:
        raise ExerciseError(f'manifest에 등록되지 않은 exercise입니다: {raw}')
    path = (ROOT / candidate).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ExerciseError('exercise path가 저장소 밖을 가리킵니다.') from exc
    return candidate, path, items[candidate]


def reject_symlinks(root: Path) -> None:
    if root.is_symlink():
        raise ExerciseError(f'symlink는 허용하지 않습니다: {root}')
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ExerciseError(f'symlink는 허용하지 않습니다: {path}')


def capstone_check(path: Path, target: Path) -> None:
    rubric = json.loads((path / 'rubric.json').read_text(encoding='utf-8'))
    for artifact in rubric['required_artifacts']:
        file = target / artifact
        if not file.is_file():
            raise ExerciseError(f'capstone artifact 누락: {artifact}')
        if file.suffix == '.json':
            json.loads(file.read_text(encoding='utf-8'))
    print('OK capstone structure; 실제 runtime 검증은 submission의 verify_command로 수행하십시오.')


def run_checker(path: Path, item: dict, target: Path) -> subprocess.CompletedProcess[str]:
    checker = path / item['checker']
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return subprocess.run(
        [sys.executable, '-B', str(checker), str(target)],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def command_list(items: dict[str, dict]) -> int:
    for path, item in items.items():
        print(f"{item['kind']:<8} {path}")
    return 0


def command_new(raw: str, items: dict[str, dict]) -> int:
    _, path, _ = resolve_registered(raw, items)
    skeleton = path / 'skeleton'
    workspace = path / 'workspace'
    reject_symlinks(skeleton)
    if workspace.exists() or workspace.is_symlink():
        raise ExerciseError(f'workspace가 이미 있습니다: {workspace.relative_to(ROOT)}')
    shutil.copytree(skeleton, workspace, symlinks=False)
    print(workspace.relative_to(ROOT))
    return 0


def target_for(path: Path, source: str) -> Path:
    target = path / source
    if not target.is_dir():
        raise ExerciseError(f'{source}가 없습니다: {path.relative_to(ROOT)}')
    reject_symlinks(target)
    return target


def command_check(raw: str, source: str, items: dict[str, dict]) -> int:
    _, path, item = resolve_registered(raw, items)
    target = target_for(path, source)
    if item['kind'] == 'capstone':
        capstone_check(path, target)
        return 0
    result = run_checker(path, item, target)
    print(result.stdout, end='')
    return result.returncode


def command_verify_all(items: dict[str, dict]) -> int:
    for raw in items:
        _, path, item = resolve_registered(raw, items)
        reject_symlinks(path)
        if item['kind'] == 'capstone':
            capstone_check(path, path / 'skeleton')
            print(f'OK template {raw}')
            continue
        reference = run_checker(path, item, path / 'reference')
        if reference.returncode != 0:
            raise ExerciseError(f"reference 실패: {raw}\n{reference.stdout}")
        skeleton = run_checker(path, item, path / 'skeleton')
        expected = item['semantic_failure']
        if skeleton.returncode == 0:
            raise ExerciseError(f'skeleton이 통과했습니다: {raw}')
        if expected not in skeleton.stdout:
            raise ExerciseError(
                f'skeleton이 지정된 이유로 실패하지 않았습니다: {raw}\n'
                f'expected={expected}\nactual={skeleton.stdout}'
            )
        print(f'OK contract {raw}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    new = sub.add_parser('new')
    new.add_argument('exercise')
    check = sub.add_parser('check')
    check.add_argument('exercise')
    check.add_argument('--source', choices=('skeleton', 'reference', 'workspace'), default='workspace')
    sub.add_parser('verify-all')
    args = parser.parse_args()
    items = load_items()
    if args.command == 'list':
        return command_list(items)
    if args.command == 'new':
        return command_new(args.exercise, items)
    if args.command == 'check':
        return command_check(args.exercise, args.source, items)
    if args.command == 'verify-all':
        return command_verify_all(items)
    raise ExerciseError('unknown command')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ExerciseError, json.JSONDecodeError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
