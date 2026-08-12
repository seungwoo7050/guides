#!/usr/bin/env python3
"""Prove repository validation rejects representative structural mutations."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def copy_repository(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git", ".guide", ".verify", "workspace", "__pycache__", ".pytest_cache", "*.pyc"
        ),
    )


def validate(root: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GUIDE_ROOT"] = str(root)
    return subprocess.run(
        [sys.executable, "scripts/validate.py"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def mutate_text(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"mutant precondition missing: {relative}: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def swap_lines(root: Path, relative: str, first_prefix: str, second_prefix: str) -> None:
    path = root / relative
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    first = [index for index, line in enumerate(lines) if line.startswith(first_prefix)]
    second = [index for index, line in enumerate(lines) if line.startswith(second_prefix)]
    if len(first) != 1 or len(second) != 1:
        raise AssertionError(
            f"swap precondition failed: {relative}: first={first_prefix}: {first}, "
            f"second={second_prefix}: {second}"
        )
    lines[first[0]], lines[second[0]] = lines[second[0]], lines[first[0]]
    path.write_text("".join(lines), encoding="utf-8")


def implementation_token(label: str) -> str:
    return "[" + "Implementation " + label + "]"


def copy_section(root: Path, source_relative: str, target_relative: str, title: str) -> None:
    marker = f"## {title}\n"

    def bounds(text: str) -> tuple[int, int]:
        start = text.find(marker)
        if start < 0:
            raise AssertionError(f"section precondition missing: {title}")
        content_start = start + len(marker)
        content_end = text.find("\n## ", content_start)
        return content_start, len(text) if content_end < 0 else content_end + 1

    source = (root / source_relative).read_text(encoding="utf-8")
    target_path = root / target_relative
    target = target_path.read_text(encoding="utf-8")
    source_start, source_end = bounds(source)
    target_start, target_end = bounds(target)
    target_path.write_text(
        target[:target_start] + source[source_start:source_end] + target[target_end:],
        encoding="utf-8",
    )


def remove_roadmap_limit(root: Path) -> None:
    mutate_text(root, "docs/00-roadmap.md", "## 자동 검증의 한계", "## 자동 검사 참고")


def expect(name: str, mutation, expected: str) -> None:
    with tempfile.TemporaryDirectory(prefix=f"guide-cn-validator-{name}-") as temporary:
        root = Path(temporary) / "repo"
        copy_repository(root)
        mutation(root)
        result = validate(root)
        output = result.stdout + result.stderr
        if result.returncode == 0 or expected not in output:
            raise AssertionError(f"validator mutant not rejected: {name}, expected={expected}\n{output}")
        print(f"[PASS] validator mutant rejected: {name}")


def main() -> int:
    baseline = validate(ROOT)
    if baseline.returncode:
        raise SystemExit(baseline.stdout + baseline.stderr)
    expect("unexpected-file", lambda root: (root / "unexpected.txt").write_text("mutant\n", encoding="utf-8"), "exact layout 예상 밖 파일")
    expect("missing-document", lambda root: (root / "docs/01-link-and-path/01-layers-encapsulation-and-path.md").unlink(), "필수 파일 없음")
    expect(
        "missing-pedagogy",
        lambda root: mutate_text(root, "exercises/protocol-inspector/README.md", "## 자기 설명", "## 회고"),
        "학습 heading 누락",
    )
    expect(
        "broken-link",
        lambda root: mutate_text(root, "README.md", "](docs/00-roadmap.md)", "](docs/missing.md)"),
        "깨진 링크",
    )
    expect(
        "unfinished-reference",
        lambda root: mutate_text(root, "exercises/protocol-inspector/reference/protocol_inspector/checksum.py", "def internet_checksum", "# TODO\ndef internet_checksum"),
        "reference 미완성 표식",
    )
    expect(
        "source-symlink",
        lambda root: ((root / "reference/glossary.md").unlink(), (root / "reference/glossary.md").symlink_to("command-reference.md")),
        "source symlink 금지",
    )
    expect(
        "source-directory-symlink",
        lambda root: (root / "docs-link").symlink_to("docs"),
        "source symlink 금지",
    )
    expect(
        "floating-image",
        lambda root: mutate_text(root, "scripts/prepare_network_image.py", "python:3.12-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2", "python:3.12-slim-bookworm:latest"),
        "verifier image digest",
    )
    expect(
        "copied-completion-rubric",
        lambda root: copy_section(
            root,
            "exercises/protocol-inspector/README.md",
            "exercises/packet-observation/README.md",
            "완료 기준",
        ),
        "실습 복사형 완료 기준",
    )
    expect("missing-roadmap-limit", remove_roadmap_limit, "roadmap 학습 계약 누락")
    expect(
        "package-version-drift",
        lambda root: mutate_text(
            root,
            "scripts/prepare_network_image.py",
            '"iproute2": "6.1.0-3"',
            '"iproute2": "unfixed"',
        ),
        "package version pin",
    )
    expect(
        "missing-root-ordered-mapping-row",
        lambda root: mutate_text(
            root,
            "README.md",
            "| 13 | [표준 지도](docs/90-standards-map.md)",
            "| 13 | 표준 지도",
        ),
        "ordered mapping 문서 누락",
    )
    expect(
        "root-ordered-mapping-header-drift",
        lambda root: mutate_text(
            root,
            "README.md",
            "| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |",
            "| 단계 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |",
        ),
        "ordered mapping 열 구성이",
    )
    expect(
        "missing-roadmap-ordered-mapping",
        lambda root: mutate_text(
            root,
            "README.md",
            "| 0 | [학습 로드맵](docs/00-roadmap.md)",
            "| 0 | 학습 로드맵",
        ),
        "ordered mapping 문서 누락: docs/00-roadmap.md",
    )
    expect(
        "root-ordered-mapping-row-order",
        lambda root: swap_lines(
            root,
            "README.md",
            "| 7 | [UDP·TCP 서비스 계약]",
            "| 8 | [TCP 상태·순서 번호]",
        ),
        "ordered mapping 순서는 0부터 13까지",
    )
    expect(
        "forbidden-skeleton-annotation",
        lambda root: mutate_text(
            root,
            "exercises/protocol-inspector/skeleton/protocol_inspector/checksum.py",
            "def internet_checksum",
            f"# {implementation_token('1')} 잘못된 skeleton 위치입니다.\ndef internet_checksum",
        ),
        "허용되지 않은 Implementation annotation 위치",
    )
    expect(
        "duplicate-annotation",
        lambda root: mutate_text(
            root,
            "exercises/protocol-inspector/reference/protocol_inspector/checksum.py",
            "def checksum_is_valid",
            f"# {implementation_token('1')} 중복된 기준 위치입니다.\ndef checksum_is_valid",
        ),
        "Implementation annotation 중복",
    )
    expect(
        "annotation-number-gap",
        lambda root: mutate_text(
            root,
            "exercises/protocol-inspector/reference/protocol_inspector/cli.py",
            implementation_token("6"),
            implementation_token("7"),
        ),
        "Implementation 상위 번호가 1부터 연속",
    )
    expect(
        "readme-annotation-index-drift",
        lambda root: mutate_text(
            root,
            "exercises/path-diagnosis/README.md",
            "| 3-1 | `cli.py::main`",
            "| 3-2 | `cli.py::main`",
        ),
        "README 구현 순서와 source annotation",
    )
    expect(
        "readme-annotation-row-order",
        lambda root: swap_lines(
            root,
            "exercises/protocol-inspector/README.md",
            "| 1 | `checksum.py::internet_checksum`",
            "| 1-1 | `checksum.py::tcp_checksum_ipv4`",
        ),
        "README 구현 순서가 의미적 번호 순서",
    )
    expect(
        "readme-annotation-file-drift",
        lambda root: mutate_text(
            root,
            "exercises/protocol-inspector/README.md",
            "| 1 | `checksum.py::internet_checksum`",
            "| 1 | `routing.py::internet_checksum`",
        ),
        "README 구현 순서 파일과 source annotation",
    )
    expect(
        "two-annotations-on-one-comment",
        lambda root: mutate_text(
            root,
            "exercises/protocol-inspector/reference/protocol_inspector/checksum.py",
            implementation_token("1"),
            f"{implementation_token('1')} {implementation_token('2')}",
        ),
        "Implementation annotation은 한 comment line에 하나",
    )
    expect(
        "learner-defaults-to-reference",
        lambda root: mutate_text(
            root,
            "Makefile",
            "EXERCISE_IMPL := workspace\n",
            "EXERCISE_IMPL := reference\n",
        ),
        "protocol 학습자 Make 기본값은 workspace",
    )
    expect(
        "path-learner-defaults-to-reference",
        lambda root: mutate_text(
            root,
            "Makefile",
            "PATH_EXERCISE_IMPL := workspace\n",
            "PATH_EXERCISE_IMPL := reference\n",
        ),
        "path 학습자 Make 기본값은 workspace",
    )
    print("[PASS] validator mutant suite: 24/24")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
