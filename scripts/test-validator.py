#!/usr/bin/env python3
"""Prove that the structural validator rejects representative mutations."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def copy_source(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git", ".guide", ".verify", "workspace", "__pycache__", "*.pyc", "*.pyo"),
    )


def validator(root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GUIDE_ROOT"] = str(root)
    return subprocess.run(
        [sys.executable, str(root / "scripts/validate.py")],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def expect_rejection(name: str, mutate, expected: str) -> None:
    with tempfile.TemporaryDirectory(prefix=f"guide-db-validator-{name}-") as temporary:
        root = Path(temporary) / "repo"
        copy_source(root)
        mutate(root)
        result = validator(root)
        output = result.stdout + result.stderr
        if result.returncode == 0 or expected not in output:
            raise AssertionError(
                f"mutant {name!r} was not rejected as expected ({expected!r})\n{output}"
            )
        print(f"[PASS] validator mutant: {name}")


def main() -> int:
    baseline = validator(ROOT)
    if baseline.returncode != 0:
        print(baseline.stdout, file=sys.stderr)
        print(baseline.stderr, file=sys.stderr)
        return 1

    expect_rejection(
        "unexpected-file",
        lambda root: (root / "unexpected.txt").write_text("mutant\n", encoding="utf-8"),
        "exact-tree 예상 밖 파일",
    )
    expect_rejection(
        "missing-roadmap",
        lambda root: (root / "docs/00-roadmap.md").unlink(),
        "필수 파일 없음",
    )

    def remove_self_explanation(root: Path) -> None:
        path = root / "exercises/02-storage-and-indexes/01-slotted-page/README.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace("## 자기 설명", "## 설계 회고", 1)
        path.write_text(text, encoding="utf-8")

    expect_rejection("missing-self-explanation", remove_self_explanation, "학습 heading 누락")

    def break_link(root: Path) -> None:
        path = root / "README.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace("](docs/00-roadmap.md)", "](docs/missing-roadmap.md)", 1)
        path.write_text(text, encoding="utf-8")

    expect_rejection("broken-link", break_link, "깨진 링크")
    print("[PASS] validator mutant suite: 4/4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
