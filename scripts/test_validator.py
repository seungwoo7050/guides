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
    shutil.copytree(ROOT, destination, symlinks=True, ignore=shutil.ignore_patterns(".git", ".guide", "workspace", "__pycache__", "*.pyc"))


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
    print("[PASS] validator mutant suite: 11/11")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
