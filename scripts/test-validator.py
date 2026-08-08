#!/usr/bin/env python3
"""Prove that the structural validator rejects representative mutations."""

from __future__ import annotations

import os
import re
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


def expect_command_rejection(name: str, mutate, command: list[str], expected: str) -> None:
    with tempfile.TemporaryDirectory(prefix=f"guide-db-contract-{name}-") as temporary:
        root = Path(temporary) / "repo"
        copy_source(root)
        mutate(root)
        result = subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        output = result.stdout + result.stderr
        if result.returncode == 0 or expected not in output:
            raise AssertionError(
                f"contract mutant {name!r} was not rejected as expected ({expected!r})\n{output}"
            )
        print(f"[PASS] contract mutant: {name}")


def read_section(path: Path, heading: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"(?ms)^{re.escape(heading)}\s*$\n(.*?)(?=^##\s|\Z)", text)
    if match is None:
        raise AssertionError(f"section not found: {path}: {heading}")
    return match.group(1).strip()


def replace_section(path: Path, heading: str, body: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf"(?ms)^{re.escape(heading)}\s*$\n.*?(?=^##\s|\Z)")
    updated, count = pattern.subn(f"{heading}\n\n{body.strip()}\n\n", text, count=1)
    if count != 1:
        raise AssertionError(f"section not replaced: {path}: {heading}")
    path.write_text(updated, encoding="utf-8")


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
        "workspace-name-bypass",
        lambda root: (root / "docs/workspace/unexpected.md").parent.mkdir(parents=True)
        or (root / "docs/workspace/unexpected.md").write_text("mutant\n", encoding="utf-8"),
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

    def break_anchor(root: Path) -> None:
        path = root / "README.md"
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n[깨진 anchor](docs/00-roadmap.md#missing-section)\n",
            encoding="utf-8",
        )

    expect_rejection("broken-anchor", break_anchor, "깨진 anchor")

    def remove_executable_mode(root: Path) -> None:
        (root / "verify.sh").chmod(0o644)

    expect_rejection("missing-executable-mode", remove_executable_mode, "실행 권한 누락")

    def add_reference_todo(root: Path) -> None:
        path = root / "exercises/02-storage-and-indexes/01-slotted-page/reference/slotted_page.py"
        path.write_text(path.read_text(encoding="utf-8") + "\n# TODO mutant\n", encoding="utf-8")

    expect_rejection("reference-todo", add_reference_todo, "reference 미완성 표식")

    def break_version_pin(root: Path) -> None:
        path = root / "prepare.sh"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("postgres:18.4-alpine@sha256:", "postgres:18.3-alpine@sha256:", 1), encoding="utf-8")

    expect_rejection("postgres-version-pin", break_version_pin, "prepare version/marker 계약 누락")

    def remove_question_marks(root: Path) -> None:
        path = root / "exercises/02-storage-and-indexes/01-slotted-page/README.md"
        text = path.read_text(encoding="utf-8")
        start = text.index("## 자기 설명")
        end = text.index("## 검증", start)
        section = text[start:end].replace("?", ".")
        path.write_text(text[:start] + section + text[end:], encoding="utf-8")

    expect_rejection("self-explanation-punctuation", remove_question_marks, "자기 설명 질문 2개 미만")

    def copy_completion(root: Path) -> None:
        source = root / "exercises/02-storage-and-indexes/01-slotted-page/README.md"
        target = root / "exercises/02-storage-and-indexes/02-bplus-tree/README.md"
        replace_section(target, "## 완료 기준", read_section(source, "## 완료 기준"))

    expect_rejection("copied-completion", copy_completion, "복사형 완료 기준")

    def copy_questions(root: Path) -> None:
        source = root / "exercises/03-transactions-and-recovery/02-wal-recovery/README.md"
        target = root / "exercises/04-execution-and-optimization/01-join-algorithms/README.md"
        replace_section(target, "## 자기 설명", read_section(source, "## 자기 설명"))

    expect_rejection("copied-questions", copy_questions, "복사형 자기 설명")

    def remove_completion_evidence(root: Path) -> None:
        path = root / "exercises/02-storage-and-indexes/01-slotted-page/README.md"
        body = read_section(path, "## 완료 기준")
        body = re.sub(r"(?m)^- .*\n", "", body, count=1)
        replace_section(path, "## 완료 기준", body)

    expect_rejection("completion-bullets", remove_completion_evidence, "관찰 가능한 완료 기준 3개 미만")

    def replace_canonical_command(root: Path) -> None:
        path = root / "exercises/01-relational-semantics-and-design/01-sql-semantics/README.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace(
            "./scripts/check-workspace.sh exercises/01-relational-semantics-and-design/01-sql-semantics",
            "./scripts/check-workspace.sh exercises/not-this-exercise",
            1,
        ), encoding="utf-8")

    expect_rejection("canonical-workspace-command", replace_canonical_command, "실행 가능한 검증 명령 누락")

    def disconnect_workspace_dispatcher(root: Path) -> None:
        path = root / "scripts/check-workspace.sh"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace(
            '"$ROOT/scripts/run-postgres-exercises.sh" --workspace "$requested"',
            '"$ROOT/scripts/run-postgres-exercises.sh" --reference "$requested"',
            1,
        ), encoding="utf-8")

    expect_rejection("workspace-runtime-dispatch", disconnect_workspace_dispatcher, "workspace checker 계약 누락")

    def break_capstone_index_order(root: Path) -> None:
        path = root / "exercises/05-capstones/01-application-database-review/reference/indexes.sql"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace(
            "ON tickets(org_id, priority DESC, created_at DESC, id DESC)",
            "ON tickets(org_id, priority, created_at DESC, id DESC)",
            1,
        ), encoding="utf-8")

    expect_rejection("capstone-index-order", break_capstone_index_order, "application capstone index 계약 누락")

    def remove_contributing_public_command(root: Path) -> None:
        path = root / "CONTRIBUTING.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("make clean\n", "clean command omitted\n", 1), encoding="utf-8")

    expect_rejection(
        "contributing-public-command",
        remove_contributing_public_command,
        "기여 안내 공개 make 명령 계약 누락",
    )

    def change_designated_skeleton_token(root: Path) -> None:
        path = root / "exercises/02-storage-and-indexes/01-slotted-page/skeleton/slotted_page.py"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("GUIDE_SEMANTIC:slotted-page-insert", "GUIDE_SEMANTIC:wrong-contract", 1), encoding="utf-8")

    expect_command_rejection(
        "designated-skeleton-failure",
        change_designated_skeleton_token,
        [sys.executable, "scripts/check-exercises.py"],
        "지정된 학습 계약",
    )
    print("[PASS] validator/contract mutant suite: 18/18")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
