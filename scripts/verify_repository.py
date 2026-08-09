#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

from source_fingerprint import fingerprint

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK_RE = re.compile(r'!?(?:\[[^\]]*\])\(([^)]+)\)')
EXCLUDED_DIRS = {'.git', '.guide', '.workspace', '__pycache__'}


class VerificationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise VerificationError(message)


def relative_files() -> list[str]:
    result: list[str] = []
    for path in ROOT.rglob('*'):
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.is_file() and path.name != '.DS_Store':
            result.append(rel.as_posix())
    return sorted(result)


def check_required_structure() -> None:
    required = [
        'README.md', 'CONTRIBUTING.md', 'LICENSE.md', 'LICENSES/MIT.txt', 'LICENSES/CC-BY-4.0.txt',
        'Makefile', 'prepare.sh', 'verify.sh', 'scripts/verify_submission.py',
        'scripts/verify_repository.py', 'scripts/source_fingerprint.py', 'config/repository-files.txt',
        'reference/source-index.md', 'reference/glossary.md', 'docs/00-roadmap.md', 'docs/17-capstone.md',
    ]
    for rel in required:
        if not (ROOT / rel).is_file():
            fail(f'필수 파일이 없습니다: {rel}')

    core_docs = sorted((ROOT / 'docs').glob('[0-9][0-9]-*.md'))
    if len(core_docs) != 18:
        fail(f'핵심 문서는 00~17의 18개여야 합니다: 현재 {len(core_docs)}개')
    optional_labs = sorted((ROOT / 'docs/90-optional-labs').glob('*.md'))
    if len(optional_labs) < 6:
        fail(f'선택 실습 문서가 부족합니다: {len(optional_labs)}개')
    runbooks = sorted((ROOT / 'docs/runbooks').glob('*.md'))
    if len(runbooks) < 8:
        fail(f'runbook이 부족합니다: {len(runbooks)}개')

    exercise_dirs = sorted(p for p in (ROOT / 'exercises').iterdir() if p.is_dir())
    if len(exercise_dirs) != 12:
        fail(f'핵심 실습은 12개여야 합니다: 현재 {len(exercise_dirs)}개')
    for exercise in exercise_dirs:
        for rel in ('README.md', 'contract.json', 'skeleton/submission.json', 'reference/submission.json'):
            if not (exercise / rel).is_file():
                fail(f'{exercise.name}: 파일 누락 {rel}')


def check_manifest() -> None:
    manifest_path = ROOT / 'config/repository-files.txt'
    expected = [line.strip() for line in manifest_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    actual = relative_files()
    if expected != actual:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        details = []
        if missing:
            details.append(f'누락={missing[:10]}')
        if extra:
            details.append(f'추가={extra[:10]}')
        fail('repository manifest가 실제 파일 목록과 다릅니다. ' + ' '.join(details))


def check_markdown() -> None:
    markdown_files = sorted(ROOT.rglob('*.md'))
    for path in markdown_files:
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        text = path.read_text(encoding='utf-8')
        first_nonempty = next((line for line in text.splitlines() if line.strip()), '')
        if not first_nonempty.startswith('# '):
            fail(f'Markdown 첫 제목이 없습니다: {rel}')
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = raw_target.strip()
            if not target or target.startswith(('#', 'http://', 'https://', 'mailto:')):
                continue
            target = unquote(target.split('#', 1)[0])
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(f'{rel}: 저장소 밖을 가리키는 링크 {raw_target}')
            if not resolved.exists():
                fail(f'{rel}: 깨진 내부 링크 {raw_target}')


def check_json() -> None:
    for path in sorted(ROOT.rglob('*.json')):
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        try:
            json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            fail(f'JSON 문법 오류: {rel}:{exc.lineno}:{exc.colno}: {exc.msg}')


def check_shell_and_modes() -> None:
    shell_files = [ROOT / 'prepare.sh', ROOT / 'verify.sh']
    for path in shell_files:
        result = subprocess.run(['sh', '-n', str(path)], capture_output=True, text=True)
        if result.returncode != 0:
            fail(f'셸 문법 오류: {path.relative_to(ROOT)}: {result.stderr.strip()}')

    executable = [
        ROOT / 'prepare.sh', ROOT / 'verify.sh', ROOT / 'scripts/verify_submission.py',
        ROOT / 'scripts/verify_repository.py', ROOT / 'scripts/source_fingerprint.py',
    ]
    for path in executable:
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & stat.S_IXUSR == 0:
            fail(f'실행 권한이 없습니다: {path.relative_to(ROOT)}')


def check_exercises() -> tuple[int, int]:
    accepted = 0
    rejected = 0
    verifier = ROOT / 'scripts/verify_submission.py'
    for exercise in sorted(p for p in (ROOT / 'exercises').iterdir() if p.is_dir()):
        contract = exercise / 'contract.json'
        reference = exercise / 'reference/submission.json'
        skeleton = exercise / 'skeleton/submission.json'

        ref_result = subprocess.run(
            [sys.executable, str(verifier), str(contract), str(reference)],
            cwd=ROOT, capture_output=True, text=True,
        )
        if ref_result.returncode != 0:
            fail(f'{exercise.name}: reference가 계약에 실패합니다.\n{ref_result.stderr}')
        accepted += 1

        skel_result = subprocess.run(
            [sys.executable, str(verifier), str(contract), str(skeleton)],
            cwd=ROOT, capture_output=True, text=True,
        )
        if skel_result.returncode == 0:
            fail(f'{exercise.name}: skeleton이 계약을 잘못 통과했습니다.')
        rejected += 1
    return accepted, rejected


def check_prepared_fingerprint() -> None:
    marker_path = ROOT / '.guide/platform-engineering/prepared.json'
    if not marker_path.is_file():
        fail('준비 marker가 없습니다. 먼저 ./prepare.sh를 실행하십시오.')
    try:
        marker = json.loads(marker_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        fail(f'준비 marker JSON 오류: {exc}')
    current, count = fingerprint(ROOT)
    if marker.get('sourceSha256') != current or marker.get('sourceFiles') != count:
        fail('prepare 이후 추적 source가 바뀌었습니다. 변경을 검토한 뒤 ./prepare.sh를 다시 실행하십시오.')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true', help='준비 fingerprint를 제외한 정적·교육 계약 검사')
    parser.add_argument('--full', action='store_true', help='prepare fingerprint까지 포함한 전체 검사')
    args = parser.parse_args()
    if args.quick and args.full:
        fail('--quick과 --full은 함께 사용할 수 없습니다.')

    check_required_structure()
    check_manifest()
    check_markdown()
    check_json()
    check_shell_and_modes()
    accepted, rejected = check_exercises()
    if args.full:
        check_prepared_fingerprint()

    mode = 'full' if args.full else 'quick'
    print(f'OK mode={mode} files={len(relative_files())} references={accepted} skeletons_rejected={rejected}')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except VerificationError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
