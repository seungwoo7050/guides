#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRANCHES_PATH = ROOT / 'catalog' / 'branches.json'
TRACKS_PATH = ROOT / 'catalog' / 'tracks.json'

KIND_TITLES = {
    'common-foundation': '공통 기반',
    'language-entry': '언어 진입',
    'field-entry': '분야 진입',
    'specialization': '심화·전문화',
}
KIND_ORDER = ['common-foundation', 'language-entry', 'field-entry', 'specialization']

FIELD_FLOW_GROUPS = [
    (
        '웹·데이터·분산·플랫폼',
        [
            'web-app', 'web-front-react-nextjs', 'java',
            'backend-spring-boot', 'database-systems',
            'distributed-services', 'operating-systems',
            'computer-networks', 'distributed-systems', 'python',
            'data-engineering', 'unix-systems', 'web-infra',
            'platform-engineering',
        ],
    ),
    (
        'AI·모바일·보안',
        [
            'python', 'machine-learning', 'agentic-systems', 'web-app',
            'web-front-react-nextjs', 'mobile-app', 'unix-systems',
            'computer-networks', 'cybersecurity',
        ],
    ),
    (
        '시스템·도구·그래픽스·임베디드',
        [
            'c', 'cpp', 'python', 'algorithms', 'computer-architecture',
            'operating-systems', 'embedded-systems',
            'language-implementation', 'computer-graphics',
        ],
    ),
]


def load() -> tuple[list[dict], list[dict]]:
    branches = json.loads(BRANCHES_PATH.read_text(encoding='utf-8'))['branches']
    tracks = json.loads(TRACKS_PATH.read_text(encoding='utf-8'))['tracks']
    return branches, tracks


def link(branch_id: str, title_by_id: dict[str, str]) -> str:
    return f'[`{branch_id}`](https://github.com/seungwoo7050/guides/tree/{branch_id})'


def join_links(ids: list[str], title_by_id: dict[str, str]) -> str:
    return ', '.join(link(i, title_by_id) for i in ids) if ids else '없음'


def render_branch_catalog(branches: list[dict]) -> str:
    title_by_id = {b['id']: b['title'] for b in branches}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for branch in branches:
        grouped[branch['kind']].append(branch)

    lines = [
        '# 브랜치 카탈로그',
        '',
        '> 이 문서는 `catalog/branches.json`에서 생성된다. 직접 수정하지 않는다.',
        '',
        f'전체 학습 브랜치는 **{len(branches)}개**다. 브랜치 종류는 난이도가 아니라 저장소 안에서의 역할을 나타낸다.',
        '',
        '## 한눈에 보기',
        '',
        '| 브랜치 | 종류 | 핵심 역할 |',
        '|---|---|---|',
    ]
    for kind in KIND_ORDER:
        for b in grouped.get(kind, []):
            lines.append(f"| {link(b['id'], title_by_id)} | {KIND_TITLES[kind]} | {b['summary']} |")

    for kind in KIND_ORDER:
        lines.extend(['', f"## {KIND_TITLES[kind]}", ''])
        for b in grouped.get(kind, []):
            lines.extend([
                f"### `{b['id']}` — {b['title']}",
                '',
                b['summary'],
                '',
                f"- **필수 의존성:** {join_links(b['requires'], title_by_id)}",
                f"- **권장 기반:** {join_links(b['recommends'], title_by_id)}",
                f"- **인접 연결:** {join_links(b['connects'], title_by_id)}",
                f"- **일반적 후속 심화:** {join_links(b['continues_to'], title_by_id)}",
                '',
                '**소유 범위**',
                '',
            ])
            lines.extend([f"- {item}" for item in b['owns']])
            lines.extend(['', '**비소유 범위**', ''])
            lines.extend([f"- {item}" for item in b['excludes']])
            lines.extend(['', '**종료 능력**', ''])
            lines.extend([f"- {item}" for item in b['exit_capabilities']])
            lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def transitive_requires(branch_ids: list[str], branch_by_id: dict[str, dict]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def visit(branch_id: str) -> None:
        if branch_id in seen:
            return
        if branch_id not in branch_by_id:
            raise ValueError(f'unknown branch reference while rendering: {branch_id}')
        for dependency in branch_by_id[branch_id]['requires']:
            visit(dependency)
        seen.add(branch_id)
        ordered.append(branch_id)

    for branch_id in branch_ids:
        visit(branch_id)
    return ordered


def summary_core(track: dict) -> str:
    parts = [f"`{branch_id}`" for branch_id in track['common'] + track['required']]
    for group in track['required_any']:
        choices = ' / '.join(f"`{branch_id}`" for branch_id in group)
        parts.append(f'({choices} 중 하나)')
    return ', '.join(parts) if parts else '없음'


def mermaid_id(branch_id: str) -> str:
    return branch_id.replace('-', '_')


def render_field_flow(branch_by_id: dict[str, dict], branch_ids: list[str]) -> list[str]:
    selected_ids = [branch_id for branch_id in branch_ids if branch_id in branch_by_id]
    selected = set(selected_ids)
    lines = ['```mermaid', 'flowchart LR']
    for branch_id in selected_ids:
        lines.append(f'  {mermaid_id(branch_id)}["{branch_id}"]')
    for branch_id in selected_ids:
        branch = branch_by_id[branch_id]
        required = set(branch['requires'])
        for dependency in branch['requires']:
            if dependency in selected:
                lines.append(f'  {mermaid_id(dependency)} --> {mermaid_id(branch_id)}')
        for dependency in branch['recommends']:
            if dependency in selected and dependency not in required:
                lines.append(f'  {mermaid_id(dependency)} -.-> {mermaid_id(branch_id)}')
    lines.append('```')
    return lines


def render_tracks(branches: list[dict], tracks: list[dict]) -> str:
    title_by_id = {b['id']: b['title'] for b in branches}
    branch_by_id = {b['id']: b for b in branches}
    lines = [
        '# 업무 분야별 트랙',
        '',
        '> 이 문서는 `catalog/tracks.json`과 브랜치 의존성에서 생성된다. 직접 수정하지 않는다.',
        '',
        '트랙은 모든 브랜치를 나열하는 커리큘럼이 아니다. 목표 업무에 필요한 **핵심 경로**, 인접 협업에 필요한 **권장 폭**, 이후 전문화를 위한 **심화 경로**를 구분한다.',
        '',
        '## 트랙 요약',
        '',
        '| 트랙 | 핵심 브랜치 | 목표 |',
        '|---|---|---|',
    ]
    for t in tracks:
        lines.append(f"| [{t['title']}](#{t['id']}) | {summary_core(t)} | {t['summary']} |")

    for t in tracks:
        direct_core = t['common'] + t['required']
        expanded = transitive_requires(direct_core, branch_by_id)
        lines.extend([
            '',
            f"## {t['title']}",
            '',
            f"<a id=\"{t['id']}\"></a>",
            '',
            t['summary'],
            '',
            f"- **공통:** {join_links(t['common'], title_by_id)}",
            f"- **핵심 브랜치:** {join_links(t['required'], title_by_id)}",
        ])
        if t['required_any']:
            rendered_groups = []
            for group in t['required_any']:
                rendered_groups.append(join_links(group, title_by_id) + ' 중 하나')
            lines.append('- **택일 필수:** ' + ' / '.join(rendered_groups))
        else:
            lines.append('- **택일 필수:** 없음')
        lines.append(
            f"- **공통·핵심 브랜치와 직접 의존성 순서:** "
            f"{join_links(expanded, title_by_id)}"
        )
        if t['required_any']:
            lines.append('- **택일 선택별 추가 의존성 순서:**')
            multiple_groups = len(t['required_any']) > 1
            for group_index, group in enumerate(t['required_any'], start=1):
                for choice in group:
                    choice_path = transitive_requires([choice], branch_by_id)
                    group_label = f'그룹 {group_index}, ' if multiple_groups else ''
                    lines.append(
                        f"  - {group_label}{link(choice, title_by_id)} 선택: "
                        f"{join_links(choice_path, title_by_id)}"
                    )
        lines.extend([
            f"- **권장 인접 지식:** {join_links(t['recommended'], title_by_id)}",
            f"- **후속 심화:** {join_links(t['advanced'], title_by_id)}",
            '',
            '**트랙 종료 능력**',
            '',
        ])
        lines.extend([f"- {item}" for item in t['exit_capabilities']])
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def render_dependency_map(branches: list[dict]) -> str:
    title_by_id = {b['id']: b['title'] for b in branches}
    branch_by_id = {b['id']: b for b in branches}
    lines = [
        '# 브랜치 의존성 지도',
        '',
        '> 이 문서는 `catalog/branches.json`에서 생성된다. 직접 수정하지 않는다.',
        '',
        '전체 graph의 화살표 `A → B`는 B의 핵심 학습이 A를 직접 전제로 한다는 뜻이다. 권장·연결 관계는 표에서 별도로 확인한다.',
        '',
        '## 직접 필수 의존성',
        '',
        '| 브랜치 | 직접 필수 의존성 | 권장 기반 |',
        '|---|---|---|',
    ]
    for b in branches:
        lines.append(f"| {link(b['id'], title_by_id)} | {join_links(b['requires'], title_by_id)} | {join_links(b['recommends'], title_by_id)} |")

    lines.extend([
        '',
        '## 전체 graph',
        '',
        '```mermaid',
        'flowchart LR',
        '  classDef foundation fill:#eef,stroke:#445;',
        '  classDef language fill:#efe,stroke:#454;',
        '  classDef entry fill:#ffe,stroke:#665;',
        '  classDef specialization fill:#fee,stroke:#655;',
    ])
    for b in branches:
        label = b['id']
        lines.append(f"  {mermaid_id(b['id'])}[\"{label}\"]")
    for b in branches:
        for dep in b['requires']:
            lines.append(f"  {mermaid_id(dep)} --> {mermaid_id(b['id'])}")
    kind_class = {
        'common-foundation': 'foundation',
        'language-entry': 'language',
        'field-entry': 'entry',
        'specialization': 'specialization',
    }
    for b in branches:
        lines.append(f"  class {mermaid_id(b['id'])} {kind_class[b['kind']]};")
    lines.extend(['```', ''])

    lines.extend([
        '## 분야별 흐름',
        '',
        '아래 graph는 카탈로그의 관계에서 생성된다. 실선 `A --> B`는 `requires`, 점선 `A -.-> B`는 `recommends`다. `connects`와 `continues_to`는 순서를 뜻하지 않으므로 표시하지 않는다.',
        '',
    ])
    for title, branch_ids in FIELD_FLOW_GROUPS:
        lines.extend([f'### {title}', ''])
        lines.extend(render_field_flow(branch_by_id, branch_ids))
        lines.append('')

    lines.extend([
        '## 해석 규칙',
        '',
        '- 필수 의존성은 브랜치 전체를 무조건 다시 공부하라는 뜻이 아니다. roadmap과 종료 검사를 이용해 이미 가진 능력을 확인한다.',
        '- 권장 관계는 프로젝트 성격에 따라 순서가 달라질 수 있다.',
        '- 업무 트랙의 핵심 목록은 직접 의존성을 생략할 수 있으므로 `docs/03-career-tracks.md`의 “공통·핵심 브랜치와 직접 의존성 순서”를 함께 본다.',
        '- graph에 없더라도 `connects` 관계는 실제 협업에서 중요하다. 상세 내용은 `docs/01-branch-catalog.md`를 본다.',
    ])
    return '\n'.join(lines).rstrip() + '\n'


def write_or_check(path: Path, content: str, check: bool) -> bool:
    if check:
        if not path.exists() or path.read_text(encoding='utf-8') != content:
            print(f'OUTDATED: {path.relative_to(ROOT)}', file=sys.stderr)
            return False
        return True
    path.write_text(content, encoding='utf-8')
    print(f'WROTE: {path.relative_to(ROOT)}')
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    branches, tracks = load()
    outputs = {
        ROOT / 'docs' / '01-branch-catalog.md': render_branch_catalog(branches),
        ROOT / 'docs' / '03-career-tracks.md': render_tracks(branches, tracks),
        ROOT / 'docs' / '04-dependency-map.md': render_dependency_map(branches),
    }
    ok = all(write_or_check(path, content, args.check) for path, content in outputs.items())
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
