#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK_RE = re.compile(r'!?(?:\[[^\]]*\])\(([^)]+)\)')
EXPECTED_CORE_DOCS = [
    'docs/01-visual-model/01-rendering-contract-and-frame.md',
    'docs/01-visual-model/02-coordinate-spaces-and-transforms.md',
    'docs/01-visual-model/03-camera-projection-and-clipping.md',
    'docs/01-visual-model/04-images-color-and-alpha.md',
    'docs/01-visual-model/05-sampling-filtering-and-aliasing.md',
    'docs/02-software-rasterization/06-triangle-setup-coverage-and-fill-rules.md',
    'docs/02-software-rasterization/07-interpolation-perspective-and-derivatives.md',
    'docs/02-software-rasterization/08-depth-culling-blending-and-transparency.md',
    'docs/02-software-rasterization/09-software-rasterizer-capstone.md',
    'docs/03-lighting-assets-scene/10-normals-lighting-and-materials.md',
    'docs/03-lighting-assets-scene/11-textures-mipmaps-and-normal-mapping.md',
    'docs/03-lighting-assets-scene/12-meshes-scenes-and-asset-contracts.md',
    'docs/03-lighting-assets-scene/13-visibility-spatial-organization-and-lod.md',
    'docs/04-gpu-rendering/14-gpu-execution-and-command-model.md',
    'docs/04-gpu-rendering/15-resources-layouts-transfers-and-formats.md',
    'docs/04-gpu-rendering/16-shaders-pipelines-and-render-passes.md',
    'docs/04-gpu-rendering/17-frame-lifecycle-synchronization-and-resize.md',
    'docs/04-gpu-rendering/18-debugging-validation-and-frame-capture.md',
    'docs/04-gpu-rendering/19-performance-profiling-and-frame-budget.md',
    'docs/04-gpu-rendering/20-gpu-renderer-capstone.md',
]
EXPECTED_EXERCISES = [
    '01-transform-trace',
    '02-sampling-and-color',
    '03-triangle-coverage',
    '04-perspective-depth-blend',
    '05-textured-lit-scene',
    '06-gpu-first-frame',
    '07-frame-debugging',
    '08-renderer-capstone',
]
REQUIRED_CORE_SECTIONS = ['## 목표', '## 시작하기 전에', '## 연결 실습', '## 완료 기준']
REQUIRED_CONTRACT_FIELDS = {
    'schema_version', 'id', 'title', 'related_docs', 'required_artifacts',
    'invariants', 'known_bad_mutations', 'completion_evidence',
}


def fail(message: str) -> None:
    raise AssertionError(message)


def check_required_files() -> None:
    paths = [
        'README.md', 'CONTRIBUTING.md', 'LICENSE.md',
        'LICENSES/CC-BY-4.0.txt', 'LICENSES/MIT.txt',
        'docs/00-roadmap.md', 'exercises/README.md',
        'exercises/contract.schema.json',
        'reference/glossary.md', 'reference/formulas-and-checklist.md',
        'reference/sources.md', 'reference/version-baseline.md',
        'tools/ppm_diff.py', 'scripts/source_fingerprint.py',
        'prepare.sh', 'verify.sh', 'Makefile',
        *EXPECTED_CORE_DOCS,
    ]
    for rel in paths:
        path = ROOT / rel
        if not path.is_file():
            fail(f'필수 파일이 없습니다: {rel}')


def check_core_documents() -> None:
    headings: set[str] = set()
    for rel in EXPECTED_CORE_DOCS:
        text = (ROOT / rel).read_text(encoding='utf-8')
        if len(text.split()) < 350:
            fail(f'{rel}: 개념 문서가 지나치게 짧습니다.')
        first = text.splitlines()[0] if text.splitlines() else ''
        if not first.startswith('# '):
            fail(f'{rel}: H1 제목이 필요합니다.')
        if first in headings:
            fail(f'{rel}: 중복 H1 제목 {first}')
        headings.add(first)
        for section in REQUIRED_CORE_SECTIONS:
            if section not in text:
                fail(f'{rel}: 공통 절 누락 {section}')
        for marker in ('TBD', 'FIXME', 'lorem ipsum'):
            if marker.lower() in text.lower():
                fail(f'{rel}: 미완성 marker {marker}')


def _strip_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith('<') and target.endswith('>'):
        target = target[1:-1]
    target = target.split('#', 1)[0]
    return unquote(target)


def check_markdown_links() -> None:
    files = sorted(ROOT.rglob('*.md'))
    if len(files) < 30:
        fail(f'Markdown 문서 수가 예상보다 적습니다: {len(files)}')
    for path in files:
        text = path.read_text(encoding='utf-8')
        for raw in MARKDOWN_LINK_RE.findall(text):
            target = _strip_target(raw)
            if not target or target.startswith(('http://', 'https://', 'mailto:')):
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(f'{path.relative_to(ROOT)}: 저장소 밖 상대 링크 {raw}')
            if not resolved.exists():
                fail(f'{path.relative_to(ROOT)}: 깨진 링크 {raw}')


def check_contracts() -> None:
    schema_path = ROOT / 'exercises/contract.schema.json'
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    if schema.get('type') != 'object':
        fail('contract schema root type은 object여야 합니다.')
    found = sorted(p.parent.name for p in (ROOT / 'exercises').glob('*/contract.json'))
    if found != EXPECTED_EXERCISES:
        fail(f'실습 contract 목록 불일치: {found}')
    for ex_id in EXPECTED_EXERCISES:
        directory = ROOT / 'exercises' / ex_id
        readme = directory / 'README.md'
        contract_path = directory / 'contract.json'
        if not readme.is_file():
            fail(f'{ex_id}: README.md가 없습니다.')
        payload = json.loads(contract_path.read_text(encoding='utf-8'))
        if set(payload) != REQUIRED_CONTRACT_FIELDS:
            fail(f'{ex_id}: contract field 불일치 {sorted(set(payload) ^ REQUIRED_CONTRACT_FIELDS)}')
        if payload['schema_version'] != 1 or payload['id'] != ex_id:
            fail(f'{ex_id}: schema_version 또는 id가 잘못됐습니다.')
        for field in ('related_docs', 'required_artifacts', 'invariants', 'known_bad_mutations', 'completion_evidence'):
            values = payload[field]
            if not isinstance(values, list) or not values:
                fail(f'{ex_id}.{field}: 비어 있지 않은 배열이어야 합니다.')
            if any(not isinstance(v, str) or not v.strip() for v in values):
                fail(f'{ex_id}.{field}: 모든 항목은 문자열이어야 합니다.')
            if len(values) != len(set(values)):
                fail(f'{ex_id}.{field}: 중복 항목이 있습니다.')
        for rel in payload['related_docs']:
            if not (ROOT / rel).is_file():
                fail(f'{ex_id}: related_docs가 존재하지 않습니다: {rel}')
        readme_text = readme.read_text(encoding='utf-8')
        if len(readme_text.split()) < 180:
            fail(f'{ex_id}: README가 지나치게 짧습니다.')


def check_convention_contract() -> None:
    roadmap = (ROOT / 'docs/00-roadmap.md').read_text(encoding='utf-8')
    formula = (ROOT / 'docs/90-appendix/01-math-conventions-and-formulas.md').read_text(encoding='utf-8')
    required_fragments = [
        'column vector', 'P * V * M', 'left-handed', '`+Z`',
        '`[0, 1]`', '왼쪽 위', '`+Y`는 아래', 'pixel center',
        'linear RGB', 'sRGB',
    ]
    for fragment in required_fragments:
        if fragment not in roadmap:
            fail(f'roadmap 좌표/색 정본 누락: {fragment}')
    for fragment in ('column vector', 'P * V * M', 'left-handed', 'linear RGB', 'sRGB'):
        if fragment not in formula:
            fail(f'formula 참조에 정본 누락: {fragment}')


def check_no_large_untracked_binaries() -> None:
    allowed_text_suffixes = {
        '.md', '.txt', '.json', '.py', '.sh', '.gitignore', ''
    }
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in {'.git', '.guide', '__pycache__'} for part in rel.parts):
            continue
        if path.stat().st_size > 2_000_000:
            fail(f'2MB를 넘는 파일은 provenance 검토가 필요합니다: {rel}')


def run_ppm_self_test() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / 'tools/ppm_diff.py'), '--self-test'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 0 or 'PPM_DIFF_SELF_TEST_OK' not in result.stdout:
        fail(f'ppm_diff self-test 실패\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true', help='구조·문서·contract 검사만 실행')
    args = parser.parse_args()

    check_required_files()
    check_core_documents()
    check_markdown_links()
    check_contracts()
    check_convention_contract()
    check_no_large_untracked_binaries()
    if not args.quick:
        run_ppm_self_test()
    markdown_count = len(list(ROOT.rglob('*.md')))
    print(f'VERIFY_REPOSITORY_OK docs={len(EXPECTED_CORE_DOCS)} markdown={markdown_count} exercises={len(EXPECTED_EXERCISES)} quick={args.quick}')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
