#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER_PREFIX = "[" + "Implementation"


def fail(message: str) -> None:
    print(f"validator self-test 실패: {message}", file=sys.stderr)
    raise SystemExit(1)


def copy_repository(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git", "build", "workspace", ".workspace.*", "__pycache__",
            ".guide-prepare.env",
        ),
    )


def validate(repository: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "scripts/validate_repository.py"],
        cwd=repository,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def append_marker(path: Path, label: str) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"\n/* {MARKER_PREFIX} {label}] validator mutant */\n")


def replace_marker(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    old_token = f"{MARKER_PREFIX} {old}]"
    new_token = f"{MARKER_PREFIX} {new}]"
    if text.count(old_token) != 1:
        fail(f"mutation target 표식이 정확히 하나가 아닙니다: {path}: {old}")
    path.write_text(text.replace(old_token, new_token), encoding="utf-8")


def mutate_skeleton_marker(repository: Path) -> None:
    append_marker(
        repository / "exercises/02-c-language/03-int-vector/skeleton/src/int_vector.c",
        "1",
    )


def mutate_duplicate(repository: Path) -> None:
    append_marker(
        repository / "exercises/01-foundations/01-number-report/reference/number_report.c",
        "1",
    )


def mutate_gap(repository: Path) -> None:
    replace_marker(
        repository / "exercises/01-foundations/01-number-report/reference/number_report.c",
        "5",
        "6",
    )


def mutate_orphan(repository: Path) -> None:
    replace_marker(
        repository / "exercises/01-foundations/01-number-report/reference/number_report.c",
        "5",
        "5-1",
    )


def mutate_zero_child(repository: Path) -> None:
    append_marker(
        repository / "exercises/01-foundations/01-number-report/reference/number_report.c",
        "0-1",
    )


def mutate_valid_substep_gap(repository: Path) -> None:
    append_marker(
        repository / "exercises/01-foundations/01-number-report/reference/number_report.c",
        "2-2",
    )


def mutate_missing_index(repository: Path) -> None:
    path = repository / "exercises/02-c-language/01-textkit/reference/README.md"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    filtered = [line for line in lines if not line.startswith("| `3` |")]
    if len(filtered) != len(lines) - 1:
        fail("README index mutation target을 찾지 못했습니다")
    path.write_text("".join(filtered), encoding="utf-8")


def mutate_missing_markers(repository: Path) -> None:
    path = repository / "exercises/02-c-language/01-textkit/reference/src/textkit.c"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    filtered = [line for line in lines if MARKER_PREFIX not in line]
    if len(filtered) == len(lines):
        fail("source marker mutation target을 찾지 못했습니다")
    path.write_text("".join(filtered), encoding="utf-8")


def mutate_legacy_alias(repository: Path) -> None:
    alias = repository / "exercises/02-c-language/03-int-vector/solution"
    alias.mkdir()
    (alias / "README.md").write_text("legacy alias\n", encoding="utf-8")


def mutate_unexpected_example(repository: Path) -> None:
    (repository / "examples/unplanned").mkdir()


MUTATIONS: tuple[tuple[str, Callable[[Path], None]], ...] = (
    ("skeleton marker", mutate_skeleton_marker),
    ("duplicate marker", mutate_duplicate),
    ("top-level gap", mutate_gap),
    ("orphan substep", mutate_orphan),
    ("Implementation 0 substep", mutate_zero_child),
    ("substep gap", mutate_valid_substep_gap),
    ("missing README index", mutate_missing_index),
    ("missing source markers", mutate_missing_markers),
    ("legacy solution alias", mutate_legacy_alias),
    ("unexpected example", mutate_unexpected_example),
)


def main() -> None:
    baseline = validate(ROOT)
    if baseline.returncode != 0:
        fail("baseline validator가 실패했습니다:\n" + baseline.stderr.strip())

    with tempfile.TemporaryDirectory(prefix="guide-c-validator-") as temporary:
        temporary_root = Path(temporary)
        for index, (label, mutation) in enumerate(MUTATIONS, start=1):
            repository = temporary_root / f"mutant-{index}"
            copy_repository(repository)
            mutation(repository)
            result = validate(repository)
            if result.returncode == 0:
                fail(f"known-bad mutation을 허용했습니다: {label}")

    print(f"validator self-test 통과: known-bad {len(MUTATIONS)}개 거부")


if __name__ == "__main__":
    main()
