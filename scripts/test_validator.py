#!/usr/bin/env python3
"""Mutation-test the curriculum validator in disposable copies."""
from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def copy_source(parent: Path) -> Path:
    target = parent / "repository"
    shutil.copytree(
        ROOT, target, symlinks=True,
        ignore=shutil.ignore_patterns(".git", ".guide", ".workspace", "__pycache__", "*.pyc", "*.pyo", "*.log"),
    )
    return target


def validate(root: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["GUIDE_VALIDATOR_NESTED"] = "1"
    with tempfile.TemporaryDirectory(prefix="guide-ds-mutant-cache-") as cache:
        environment["PYTHONPYCACHEPREFIX"] = cache
        return subprocess.run(
            [sys.executable, "scripts/verify.py", "--quick"], cwd=root, env=environment,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False,
        )


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise AssertionError(f"mutant target is not unique: {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def contract_mutant(root: Path) -> None:
    path = root / "config/guide.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["kind"] = "field-entry"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def link_mutant(root: Path) -> None:
    replace_once(root / "README.md", "docs/00-roadmap.md", "docs/missing-roadmap.md")


def reference_mutant(root: Path) -> None:
    (root / "exercises/01-model-and-time/01-causality-trace/reference.md").unlink()


def unexpected_file(root: Path) -> None:
    (root / "unexpected.txt").write_text("mutant\n", encoding="utf-8")


def source_symlink(root: Path) -> None:
    os.symlink("README.md", root / "README-link.md")


def executable_mode_mutant(root: Path) -> None:
    (root / "scripts/check_exercises.py").chmod(0o644)


def expected_mutant(root: Path) -> None:
    path = root / "exercises/03-consensus-and-membership/01-election-trace/expected.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["manual_review"] = []
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def license_mutant(root: Path) -> None:
    (root / "LICENSES/MIT.txt").write_text("MIT License\n", encoding="utf-8")


def secret_mutant(root: Path) -> None:
    synthetic = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
    with (root / "README.md").open("a", encoding="utf-8") as handle:
        handle.write(f"\nSynthetic scanner mutant: {synthetic}\n")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-ds-validator-baseline-") as temporary:
        baseline = validate(copy_source(Path(temporary)))
        if baseline.returncode != 0:
            raise AssertionError(f"validator baseline failed\n{baseline.stdout}\n{baseline.stderr}")
    mutants: list[tuple[str, Callable[[Path], None], str]] = [
        ("catalog contract", contract_mutant, "main catalog contract mismatch: kind"),
        ("internal link", link_mutant, "broken link"),
        ("exercise reference", reference_mutant, "reference"),
        ("unexpected source", unexpected_file, "repository-files.txt does not match exact source tree"),
        ("source symlink", source_symlink, "source symlink is not allowed"),
        ("executable mode", executable_mode_mutant, "shebang file must be executable"),
        ("empty manual review", expected_mutant, "manual_review"),
        ("truncated license", license_mutant, "MIT license attribution is missing"),
        ("secret pattern", secret_mutant, "potential secret (aws-access-key)"),
    ]
    for label, mutate, expected in mutants:
        with tempfile.TemporaryDirectory(prefix="guide-ds-validator-mutant-") as temporary:
            root = copy_source(Path(temporary))
            mutate(root)
            result = validate(root)
            output = result.stdout + result.stderr
            if result.returncode == 0 or expected not in output:
                raise AssertionError(
                    f"mutant not rejected for intended reason: {label}\n"
                    f"expected={expected!r}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
                )
    print(f"VALIDATOR MUTANTS OK baseline=1 rejected={len(mutants)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
