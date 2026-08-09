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

TRACK_GROUPS = [
    ('common', '공통 시작점', '목표 직무를 아직 정하지 않았을 때 구현 언어 하나와 변경·검증 기반을 선택한다.'),
    ('web', '웹 개발', '프런트엔드·백엔드·풀스택은 책임 범위가 다르므로 직무별 선형 경로를 제공한다.'),
    ('infra-security', '인프라·플랫폼·보안', '서비스 운영, 내부 플랫폼, 공격·방어는 인접하지만 서로 다른 상태와 실패를 소유한다.'),
    ('mobile', '모바일 애플리케이션', '웹·React 기반을 모바일 수명 주기·오프라인·기기 기능·배포로 확장한다.'),
    ('ai-data', 'AI·데이터', '모델 학습, 에이전틱 시스템, 데이터 파이프라인을 독립적인 결과물 기준으로 분리한다.'),
    ('systems', '시스템·저수준·개발 도구', '운영체제·하드웨어·DBMS·컴파일러·그래픽스·임베디드 내부구조를 구현 수준으로 확장한다.'),
    ('game', '게임회사 개발 직군', '게임회사 전체에 공통인 단일 기술 경로는 없다. 클라이언트·엔진·렌더링·서버·도구·데이터·보안 중 목표 개발 직군 하나를 선택한다. 기획·아트·사운드·사업 직군은 이 저장소의 범위가 아니다.'),
]

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
    (
        '게임 개발',
        [
            'c', 'cpp', 'python', 'java', 'algorithms',
            'computer-architecture', 'operating-systems',
            'computer-networks', 'web-app', 'backend-spring-boot',
            'database-systems', 'distributed-services', 'web-infra',
            'game-development', 'computer-graphics', 'data-engineering',
            'machine-learning', 'cybersecurity', 'platform-engineering',
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


def arrow_links(ids: list[str], title_by_id: dict[str, str]) -> str:
    return ' → '.join(link(i, title_by_id) for i in ids)


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
        for branch in grouped.get(kind, []):
            lines.append(
                f"| {link(branch['id'], title_by_id)} | "
                f"{KIND_TITLES[kind]} | {branch['summary']} |"
            )

    for kind in KIND_ORDER:
        lines.extend(['', f'## {KIND_TITLES[kind]}', ''])
        for branch in grouped.get(kind, []):
            lines.extend([
                f"### `{branch['id']}` — {branch['title']}",
                '',
                branch['summary'],
                '',
                f"- **필수 의존성:** {join_links(branch['requires'], title_by_id)}",
                f"- **권장 기반:** {join_links(branch['recommends'], title_by_id)}",
                f"- **인접 연결:** {join_links(branch['connects'], title_by_id)}",
                f"- **일반적 후속 심화:** {join_links(branch['continues_to'], title_by_id)}",
                '',
                '**소유 범위**',
                '',
            ])
            lines.extend([f"- {item}" for item in branch['owns']])
            lines.extend(['', '**비소유 범위**', ''])
            lines.extend([f"- {item}" for item in branch['excludes']])
            lines.extend(['', '**종료 능력**', ''])
            lines.extend([f"- {item}" for item in branch['exit_capabilities']])
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


def render_tracks(branches: list[dict], tracks: list[dict]) -> str:
    title_by_id = {b['id']: b['title'] for b in branches}
    branch_by_id = {b['id']: b for b in branches}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for track in tracks:
        grouped[track['group']].append(track)

    lines = [
        '# 업무 분야별 트랙',
        '',
        '> 이 문서는 `catalog/tracks.json`과 브랜치 의존성에서 생성된다. 직접 수정하지 않는다.',
        '',
        '트랙은 모든 브랜치를 나열하는 커리큘럼이 아니다. 목표 업무에 필요한 **핵심 경로**, 인접 협업에 필요한 **권장 폭**, 이후 전문화를 위한 **심화 경로**를 구분한다.',
        '',
        '`권장 선형 경로`는 처음 시작하는 사람이 순서대로 진행할 실제 학습 경로다. 엄밀한 필수 의존성만 뜻하지 않으며, 직무 진입에 유용한 권장 기반을 포함할 수 있다.',
        '',
        '## 트랙 요약',
        '',
        '| 분야 | 트랙 | 권장 경로 | 목표 |',
        '|---|---|---|---|',
    ]
    for group_id, group_title, _ in TRACK_GROUPS:
        for track in grouped.get(group_id, []):
            if len(track['linear_paths']) == 1:
                path_branches = track['linear_paths'][0]['branches']
                path_text = ' → '.join(f'`{branch_id}`' for branch_id in path_branches)
            else:
                path_titles = ' / '.join(path['title'] for path in track['linear_paths'])
                path_text = f"{len(track['linear_paths'])}개 — {path_titles}"
            lines.append(
                f"| {group_title} | [{track['title']}](#{track['id']}) | "
                f"{path_text} | {track['summary']} |"
            )

    for group_id, group_title, group_description in TRACK_GROUPS:
        group_tracks = grouped.get(group_id, [])
        if not group_tracks:
            continue
        lines.extend(['', f'## {group_title}', '', group_description, ''])
        for track in group_tracks:
            direct_core = track['common'] + track['required']
            expanded = transitive_requires(direct_core, branch_by_id)
            lines.extend([
                f"### {track['title']}",
                '',
                f"<a id=\"{track['id']}\"></a>",
                '',
                track['summary'],
                '',
                '**권장 선형 경로**',
                '',
            ])
            for index, path in enumerate(track['linear_paths'], start=1):
                lines.append(
                    f"{index}. **{path['title']}** — "
                    f"{arrow_links(path['branches'], title_by_id)}"
                )
            lines.extend([
                '',
                f"- **공통:** {join_links(track['common'], title_by_id)}",
                f"- **핵심 브랜치:** {join_links(track['required'], title_by_id)}",
            ])
            if track['required_any']:
                rendered_groups = []
                for group in track['required_any']:
                    rendered_groups.append(join_links(group, title_by_id) + ' 중 하나')
                lines.append('- **택일 필수:** ' + ' / '.join(rendered_groups))
            else:
                lines.append('- **택일 필수:** 없음')
            lines.append(
                '- **공통·핵심 브랜치와 직접 의존성 순서:** '
                + join_links(expanded, title_by_id)
            )
            if track['required_any']:
                lines.append('- **택일 선택별 추가 의존성 순서:**')
                multiple_groups = len(track['required_any']) > 1
                for group_index, group in enumerate(track['required_any'], start=1):
                    for choice in group:
                        choice_path = transitive_requires([choice], branch_by_id)
                        group_label = f'그룹 {group_index}, ' if multiple_groups else ''
                        lines.append(
                            f"  - {group_label}{link(choice, title_by_id)} 선택: "
                            f"{join_links(choice_path, title_by_id)}"
                        )
            lines.extend([
                f"- **권장 인접 지식:** {join_links(track['recommended'], title_by_id)}",
                f"- **후속 심화:** {join_links(track['advanced'], title_by_id)}",
                '',
                '**트랙 종료 능력**',
                '',
            ])
            lines.extend([f"- {item}" for item in track['exit_capabilities']])
            lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


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
    for branch in branches:
        lines.append(
            f"| {link(branch['id'], title_by_id)} | "
            f"{join_links(branch['requires'], title_by_id)} | "
            f"{join_links(branch['recommends'], title_by_id)} |"
        )

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
    for branch in branches:
        lines.append(f"  {mermaid_id(branch['id'])}[\"{branch['id']}\"]")
    for branch in branches:
        for dependency in branch['requires']:
            lines.append(
                f"  {mermaid_id(dependency)} --> {mermaid_id(branch['id'])}"
            )
    kind_class = {
        'common-foundation': 'foundation',
        'language-entry': 'language',
        'field-entry': 'entry',
        'specialization': 'specialization',
    }
    for branch in branches:
        lines.append(
            f"  class {mermaid_id(branch['id'])} {kind_class[branch['kind']]};"
        )
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
        '업무 분야별 실제 선형 순서는 `docs/03-career-tracks.md`를 따른다.',
        '',
        '## 해석 규칙',
        '',
        '- 필수 의존성은 브랜치 전체를 무조건 다시 공부하라는 뜻이 아니다. roadmap과 종료 검사를 이용해 이미 가진 능력을 확인한다.',
        '- 권장 관계는 프로젝트 성격에 따라 순서가 달라질 수 있다.',
        '- 업무 트랙은 `docs/03-career-tracks.md`의 권장 선형 경로를 먼저 따르고, 엄밀한 필수 관계는 이 문서의 직접 의존성 표에서 확인한다.',
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
    ok = all(
        write_or_check(path, content, args.check)
        for path, content in outputs.items()
    )
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
