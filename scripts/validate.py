#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import py_compile
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r'!?(?:\[[^\]]*\])\(([^)]+)\)')
CONCEPT_HEADINGS = {
    '## 학습 목표',
    '## 핵심 모델',
    '## 실패 모드',
    '## 검증 질문',
    '## 연결 연습',
    '## 완료 기준',
}
REQUIRED_ROOT = {
    'README.md', 'CONTRIBUTING.md', 'LICENSE.md', 'Makefile', '.gitignore',
    'prepare.sh', 'verify.sh', 'exercises/manifest.json',
    'scripts/fingerprint.py', 'scripts/validate.py', 'scripts/exercise_tool.py',
    'scripts/new-workspace.sh', 'scripts/check-workspace.sh',
}


def fail(message: str) -> None:
    raise AssertionError(message)


def markdown_target(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith('<') and '>' in raw:
        return raw[1:raw.index('>')]
    return raw.split(maxsplit=1)[0]


def check_structure() -> None:
    missing = sorted(path for path in REQUIRED_ROOT if not (ROOT / path).exists())
    if missing:
        fail(f'필수 파일 누락: {missing}')
    for directory in ('docs', 'examples', 'exercises', 'reference', 'scripts', 'tests', 'LICENSES'):
        if not (ROOT / directory).is_dir():
            fail(f'필수 디렉터리 누락: {directory}')


def check_markdown_links() -> None:
    files = sorted(ROOT.rglob('*.md'))
    if len(files) < 30:
        fail(f'Markdown 문서가 너무 적습니다: {len(files)}')
    for path in files:
        if any(part in {'.guide', 'workspace'} for part in path.parts):
            continue
        text = path.read_text(encoding='utf-8')
        if not text.startswith('# '):
            fail(f'{path.relative_to(ROOT)}: H1 제목이 없습니다.')
        for raw in LINK_RE.findall(text):
            target = markdown_target(raw).split('#', 1)[0]
            if not target or target.startswith(('http://', 'https://', 'mailto:', 'data:')):
                continue
            resolved = (path.parent / unquote(target)).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(f'{path.relative_to(ROOT)}: 저장소 밖 링크 {raw}')
            if not resolved.exists():
                fail(f'{path.relative_to(ROOT)}: 깨진 링크 {raw}')


def check_concept_docs() -> None:
    concept_files: list[Path] = []
    for section in range(1, 6):
        concept_files.extend(ROOT.glob(f'docs/{section:02d}-*/*.md'))
    if len(concept_files) < 15:
        fail(f'핵심 개념 문서가 너무 적습니다: {len(concept_files)}')
    for path in sorted(concept_files):
        text = path.read_text(encoding='utf-8')
        if len(text) < 4500:
            fail(f'{path.relative_to(ROOT)}: 개념 문서가 지나치게 짧습니다 ({len(text)} bytes)')
        headings = {line.strip() for line in text.splitlines() if line.startswith('## ')}
        missing = CONCEPT_HEADINGS - headings
        if missing:
            fail(f'{path.relative_to(ROOT)}: section 누락 {sorted(missing)}')


def load_manifest() -> dict:
    try:
        manifest = json.loads((ROOT / 'exercises/manifest.json').read_text(encoding='utf-8'))
    except Exception as exc:
        fail(f'exercise manifest를 읽을 수 없습니다: {exc}')
    exercises = manifest.get('exercises')
    if not isinstance(exercises, list) or not exercises:
        fail('manifest exercises는 비어 있지 않은 배열이어야 합니다.')
    return manifest


def check_exercises(manifest: dict) -> None:
    seen: set[str] = set()
    for item in manifest['exercises']:
        path_text = item.get('path')
        kind = item.get('kind')
        if not isinstance(path_text, str) or not path_text.startswith('exercises/'):
            fail(f'잘못된 exercise path: {path_text!r}')
        if path_text in seen:
            fail(f'중복 exercise: {path_text}')
        seen.add(path_text)
        path = ROOT / path_text
        if not path.is_dir() or not (path / 'README.md').is_file() or not (path / 'skeleton').is_dir():
            fail(f'{path_text}: README 또는 skeleton 누락')
        if any(candidate.is_symlink() for candidate in path.rglob('*')):
            fail(f'{path_text}: exercise 안의 symlink는 허용하지 않습니다.')
        if kind in {'code', 'design'}:
            checker = item.get('checker')
            semantic = item.get('semantic_failure')
            if not checker or not semantic:
                fail(f'{path_text}: checker/semantic_failure 누락')
            if not (path / checker).is_file() or not (path / 'reference').is_dir():
                fail(f'{path_text}: checker 또는 reference 누락')
        elif kind == 'capstone':
            rubric_path = path / 'rubric.json'
            if not rubric_path.is_file():
                fail(f'{path_text}: rubric.json 누락')
            rubric = json.loads(rubric_path.read_text(encoding='utf-8'))
            required = rubric.get('required_artifacts')
            if not isinstance(required, list) or not required:
                fail(f'{path_text}: required_artifacts 누락')
            for artifact in required:
                if not (path / 'skeleton' / artifact).is_file():
                    fail(f'{path_text}: capstone template 누락 {artifact}')
            if rubric.get('reference_implementation') is not False:
                fail(f'{path_text}: capstone은 reference 구현을 제공하지 않아야 합니다.')
        else:
            fail(f'{path_text}: 알 수 없는 kind {kind!r}')


def check_json() -> None:
    for path in sorted(ROOT.rglob('*.json')):
        if any(part in {'.guide', 'workspace'} for part in path.parts):
            continue
        try:
            json.loads(path.read_text(encoding='utf-8'))
        except Exception as exc:
            fail(f'{path.relative_to(ROOT)}: JSON 오류 {exc}')


def check_python() -> None:
    for path in sorted(ROOT.rglob('*.py')):
        if any(part in {'.guide', 'workspace', '__pycache__'} for part in path.parts):
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            fail(f'{path.relative_to(ROOT)}: Python compile 오류 {exc.msg}')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true')
    parser.parse_args()
    check_structure()
    check_markdown_links()
    check_concept_docs()
    manifest = load_manifest()
    check_exercises(manifest)
    check_json()
    check_python()
    print(f"OK docs={len(list(ROOT.rglob('*.md')))} exercises={len(manifest['exercises'])}")
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
