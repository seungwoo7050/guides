#!/usr/bin/env python3
"""구조 validator가 대표 결함을 실제로 거부하는지 검사합니다."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[1]


def copy_source(destination: Path) -> None:
    shutil.copytree(
        SOURCE,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git", ".guide", "workspace", "build", "__pycache__", "*.pyc"
        ),
    )


def validate(root: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GUIDE_ROOT"] = str(root)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        ["python3", str(root / "scripts/validate_docs.py")],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def require_rejection(name: str, mutate, needle: str) -> None:
    with tempfile.TemporaryDirectory(prefix="guide-architecture-validator-") as temporary:
        root = Path(temporary) / "repo"
        copy_source(root)
        mutate(root)
        completed = validate(root)
        output = completed.stdout + completed.stderr
        if completed.returncode == 0 or needle not in output:
            raise AssertionError(
                f"{name} mutant를 지정된 계약에서 거부하지 못했습니다.\n{output}"
            )
        print(f"[PASS] validator rejects {name}")


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"mutant 기준 문자열이 없습니다: {path} -> {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def copy_section(root: Path, source_relative: str, target_relative: str, heading: str) -> None:
    marker = f"## {heading}\n"

    def body(text: str) -> tuple[int, int]:
        start = text.index(marker) + len(marker)
        end = text.find("\n## ", start)
        return start, len(text) if end < 0 else end + 1

    source = (root / source_relative).read_text(encoding="utf-8")
    target_path = root / target_relative
    target = target_path.read_text(encoding="utf-8")
    source_start, source_end = body(source)
    target_start, target_end = body(target)
    target_path.write_text(
        target[:target_start] + source[source_start:source_end] + target[target_end:],
        encoding="utf-8",
    )


def main() -> int:
    baseline = validate(SOURCE)
    if baseline.returncode != 0:
        raise AssertionError("validator 기준본이 실패했습니다.\n" + baseline.stdout + baseline.stderr)

    require_rejection(
        "missing-document",
        lambda root: (root / "docs/00-roadmap.md").unlink(),
        "필수 파일을 찾을 수 없습니다",
    )
    require_rejection(
        "unexpected-path",
        lambda root: (root / "unexpected-guide.txt").write_text("unexpected\n", encoding="utf-8"),
        "예상 밖 최상위 경로",
    )
    require_rejection(
        "broken-link",
        lambda root: replace(
            root / "docs/01-representation-and-isa/01-data-representation-and-arithmetic.md",
            "../../exercises/processor-model/README.md",
            "../../exercises/missing/README.md",
        ),
        "대상이 없는 링크",
    )
    require_rejection(
        "copied-concept-rubric",
        lambda root: copy_section(
            root,
            "docs/01-representation-and-isa/01-data-representation-and-arithmetic.md",
            "docs/01-representation-and-isa/02-isa-assembly-and-program-execution.md",
            "완료 기준",
        ),
        "완료 기준을 복사",
    )
    require_rejection(
        "non-executable-script",
        lambda root: (root / "prepare.sh").chmod(
            (root / "prepare.sh").stat().st_mode & ~stat.S_IXUSR
        ),
        "실행 권한이 없습니다",
    )
    require_rejection(
        "unfinished-reference",
        lambda root: (root / "exercises/processor-model/reference/processor_model/bits.py").write_text(
            (root / "exercises/processor-model/reference/processor_model/bits.py").read_text(encoding="utf-8")
            + "\n# TODO: mutant\n",
            encoding="utf-8",
        ),
        "reference에 미완성 표시",
    )
    require_rejection(
        "runtime-version-drift",
        lambda root: replace(
            root / "reference/version-baseline.md", "Python >= 3.12", "Python >= 3.11"
        ),
        "실행·판본 계약이 없습니다",
    )

    def add_symlink(root: Path) -> None:
        (root / "unexpected-symlink").symlink_to("README.md")

    require_rejection("source-symlink", add_symlink, "source tree에 symlink")
    require_rejection(
        "missing-roadmap-outcome",
        lambda root: replace(
            root / "docs/00-roadmap.md",
            "## 완료 후 할 수 있어야 하는 일",
            "## 과정 참고",
        ),
        "로드맵 학습 계약",
    )
    print("validator mutant suite: PASS (9/9)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
