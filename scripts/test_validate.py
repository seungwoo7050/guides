#!/usr/bin/env python3
"""Prove that the repository validator rejects representative mutations."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

sys.dont_write_bytecode = True
from guide_state import capture, copy_source, git_index_state

ROOT = Path(__file__).resolve().parents[1]
Mutation = Callable[[Path], None]


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"mutant target이 없습니다: {path}: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"mutant target이 없습니다: {path}: {old}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def copy_markdown_section(
    root: Path, heading: str, source_relative: str, target_relative: str
) -> None:
    pattern = re.compile(
        rf"(^## {re.escape(heading)}\s*$\n)(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    source = (root / source_relative).read_text(encoding="utf-8")
    target_path = root / target_relative
    target = target_path.read_text(encoding="utf-8")
    source_match = pattern.search(source)
    target_match = pattern.search(target)
    if source_match is None or target_match is None:
        raise AssertionError(f"section mutant target이 없습니다: {heading}")
    replacement = source_match.group(1) + source_match.group(2)
    target_path.write_text(
        target[: target_match.start()] + replacement + target[target_match.end() :],
        encoding="utf-8",
    )


def run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/validate.py"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=20,
    )


def write_text(path: Path, text: str = "mutant\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_git(root: Path, *arguments: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=20,
    )
    if result.returncode != 0:
        raise AssertionError(f"git 명령 실패: {' '.join(arguments)}\n{result.stdout}")


def verify_raw_index_contract(temporary_root: Path) -> None:
    repository = temporary_root / "index-repository"
    linked = temporary_root / "index-linked-worktree"
    repository.mkdir()
    run_git(repository, "init", "-q")
    write_text(repository / "alpha.txt", "alpha\n")
    write_text(repository / "nested/beta.txt", "beta\n")
    run_git(repository, "add", "--", "alpha.txt", "nested/beta.txt")
    run_git(
        repository,
        "-c",
        "user.name=Guide Contract Test",
        "-c",
        "user.email=guide-contract@example.invalid",
        "commit",
        "-qm",
        "fixture",
    )
    run_git(repository, "worktree", "add", "--detach", str(linked), "HEAD")
    run_git(linked, "update-index", "--index-version=2")
    version_two = git_index_state(linked)
    run_git(linked, "update-index", "--index-version=4")
    version_four = git_index_state(linked)
    if version_two["staged_entries_sha256"] != version_four["staged_entries_sha256"]:
        raise AssertionError("index version 변경이 staged entries까지 바꿨습니다.")
    if version_two["raw_bytes_sha256"] == version_four["raw_bytes_sha256"]:
        raise AssertionError("raw-index-only mutation을 감지하지 못했습니다.")
    print("[PASS] linked worktree raw-index-only mutation 감지")


def assert_failed_preflight(
    root: Path, requested_log: str, expected_status: int = 2
) -> subprocess.CompletedProcess[str]:
    before = capture(root)
    environment = os.environ.copy()
    environment["VERIFY_LOG"] = requested_log
    result = subprocess.run(
        ["./verify.sh"],
        cwd=root,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=20,
    )
    if result.returncode != expected_status:
        raise AssertionError(
            f"VERIFY_LOG preflight rc={result.returncode}, expected={expected_status}\n{result.stdout}"
        )
    for required in ("RESULT: FAIL", "passed=0 failed=1 skipped=0", "VERIFY LOG:"):
        if required not in result.stdout:
            raise AssertionError(f"preflight 집계가 빠졌습니다: {required}\n{result.stdout}")
    match = re.search(r"^VERIFY LOG: (/.+)$", result.stdout, re.MULTILINE)
    if match is None:
        raise AssertionError(f"외부 fallback log 경로가 없습니다.\n{result.stdout}")
    fallback = Path(match.group(1)).resolve()
    try:
        fallback.relative_to(root.resolve())
    except ValueError:
        pass
    else:
        raise AssertionError(f"fallback log가 저장소 안에 있습니다: {fallback}")
    if not fallback.is_file():
        raise AssertionError(f"fallback log가 생성되지 않았습니다: {fallback}")
    fallback.unlink()
    if capture(root) != before:
        raise AssertionError(f"거부된 VERIFY_LOG가 저장소를 변경했습니다: {requested_log}")
    return result


def verify_log_preflight_contract(temporary_root: Path) -> None:
    fixture = temporary_root / "verify-log-fixture"
    fixture.mkdir()
    copy_source(ROOT, fixture)

    assert_failed_preflight(fixture, "relative/verify.log")
    if (fixture / "relative").exists():
        raise AssertionError("상대 VERIFY_LOG의 parent가 생성되었습니다.")

    internal = fixture / "docs/preflight-created/verify.log"
    assert_failed_preflight(fixture, str(internal))
    if internal.parent.exists():
        raise AssertionError("저장소 내부 VERIFY_LOG의 parent가 생성되었습니다.")

    protected = fixture / "docs/00-roadmap.md"
    protected_before = protected.read_bytes()
    symlink_log = temporary_root / "verify-log-symlink"
    symlink_log.symlink_to(protected)
    assert_failed_preflight(fixture, str(symlink_log))
    if protected.read_bytes() != protected_before or not symlink_log.is_symlink():
        raise AssertionError("symlink escape VERIFY_LOG가 대상 또는 링크를 변경했습니다.")

    environment = os.environ.copy()
    environment.pop("VERIFY_LOG", None)
    default_result = subprocess.run(
        ["./verify.sh"],
        cwd=fixture,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=20,
    )
    if default_result.returncode != 1 or "RESULT: FAIL" not in default_result.stdout:
        raise AssertionError(f"기본 외부 log 계약이 올바르지 않습니다.\n{default_result.stdout}")
    match = re.search(r"^VERIFY LOG: (/.+)$", default_result.stdout, re.MULTILINE)
    if match is None:
        raise AssertionError("기본 외부 log 경로가 출력되지 않았습니다.")
    default_log = Path(match.group(1)).resolve()
    try:
        default_log.relative_to(fixture.resolve())
    except ValueError:
        pass
    else:
        raise AssertionError(f"기본 log가 저장소 안에 있습니다: {default_log}")
    if not default_log.is_file():
        raise AssertionError(f"기본 log가 생성되지 않았습니다: {default_log}")
    default_log.unlink()
    print("[PASS] VERIFY_LOG 상대·내부·symlink escape 무변경 거부와 기본 외부 log")


def verify_arbitrary_assertion_rejected(temporary_root: Path) -> None:
    if not (
        os.environ.get("GUIDE_MAVEN_REPOSITORY")
        and os.environ.get("MAVEN_USER_HOME")
    ):
        print("[INFO] skeleton runtime mutant는 전체 verify에서 실행됩니다.")
        return
    mutant = temporary_root / "arbitrary-assertion-skeleton"
    mutant.mkdir()
    copy_source(ROOT, mutant)
    source = (
        mutant
        / "exercises/01-language-and-domain/01-first-program/skeleton/src/main/java/dev/guides/java/firstprogram/NumberReportApplication.java"
    )
    replace(
        source,
        '    output.println("count=" + args.length);',
        '    if (args.length == 0) {\n'
        '      throw new AssertionError("ARBITRARY_ASSERTION_MUTANT");\n'
        '    }\n'
        '    output.println("count=" + args.length);',
    )
    result = subprocess.run(
        ["./scripts/verify-skeletons.sh", "first-program"],
        cwd=mutant,
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=120,
    )
    if result.returncode == 0 or "지정된 학습 계약이 아닌 이유" not in result.stdout:
        raise AssertionError(f"임의 AssertionError mutant를 허용했습니다.\n{result.stdout}")
    print("[PASS] 임의 AssertionError skeleton mutant 거부")


def verify_workspace_tools(temporary_root: Path) -> None:
    fixture = temporary_root / "workspace-tools"
    fixture.mkdir()
    copy_source(ROOT, fixture)
    inherited_workspace = fixture / ".workspace"
    if inherited_workspace.is_symlink():
        inherited_workspace.unlink()
    elif inherited_workspace.exists():
        shutil.rmtree(inherited_workspace)
    exercise = "exercises/01-language-and-domain/01-first-program"

    rejected = subprocess.run(
        ["./scripts/new-workspace.sh", "../../outside"],
        cwd=fixture,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=20,
    )
    if rejected.returncode == 0 or (fixture / ".workspace").exists():
        raise AssertionError(f"manifest 밖 경로를 허용했습니다.\n{rejected.stdout}")

    created = subprocess.run(
        ["./scripts/new-workspace.sh", exercise],
        cwd=fixture,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=20,
    )
    if created.returncode != 0:
        raise AssertionError(f"learner workspace를 만들지 못했습니다.\n{created.stdout}")
    workspace = fixture / ".workspace/first-program"
    expected_parent = "<relativePath>../../pom.xml</relativePath>"
    if expected_parent not in (workspace / "pom.xml").read_text(encoding="utf-8"):
        raise AssertionError("workspace POM parent 경로를 안전하게 바꾸지 못했습니다.")

    test_file = workspace / (
        "src/test/java/dev/guides/java/firstprogram/NumberReportApplicationTest.java"
    )
    test_file.write_text(test_file.read_text(encoding="utf-8") + "// mutant\n", encoding="utf-8")
    changed_test = subprocess.run(
        ["./scripts/check-workspace.sh", exercise],
        cwd=fixture,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=20,
    )
    if changed_test.returncode == 0 or "공개 테스트를 변경했습니다" not in changed_test.stdout:
        raise AssertionError(f"변경한 공용 테스트를 허용했습니다.\n{changed_test.stdout}")
    test_file.unlink()
    test_file.symlink_to("/tmp/guide-java-test-escape")
    symlink = subprocess.run(
        ["./scripts/check-workspace.sh", exercise],
        cwd=fixture,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=20,
    )
    if symlink.returncode == 0 or "symlink는 허용하지 않습니다" not in symlink.stdout:
        raise AssertionError(f"workspace symlink escape를 허용했습니다.\n{symlink.stdout}")
    print("[PASS] learner workspace manifest·POM·공용 테스트·symlink 안전성")


def mutations() -> list[tuple[str, Mutation]]:
    return [
        (
            "missing-required-doc",
            lambda root: (root / "docs/00-roadmap.md").unlink(),
        ),
        (
            "unexpected-tree-entry",
            lambda root: (root / "unexpected-guide-file.txt").write_text(
                "mutant\n", encoding="utf-8"
            ),
        ),
        (
            "docs-target-bypass",
            lambda root: write_text(root / "docs/target/hidden.txt"),
        ),
        (
            "docs-workspace-bypass",
            lambda root: write_text(root / "docs/.workspace/hidden.txt"),
        ),
        (
            "missing-self-explanation",
            lambda root: replace_all(
                root / "exercises/01-language-and-domain/01-first-program/README.md",
                "## 자기 설명",
                "## 회고",
            ),
        ),
        (
            "copied-completion-only",
            lambda root: copy_markdown_section(
                root,
                "완료 기준",
                "exercises/01-language-and-domain/01-first-program/README.md",
                "exercises/01-language-and-domain/02-value-object-contract/README.md",
            ),
        ),
        (
            "copied-questions-only",
            lambda root: copy_markdown_section(
                root,
                "자기 설명",
                "exercises/01-language-and-domain/01-first-program/README.md",
                "exercises/01-language-and-domain/02-value-object-contract/README.md",
            ),
        ),
        (
            "fewer-than-three-completion-bullets",
            lambda root: replace(
                root / "exercises/01-language-and-domain/01-first-program/README.md",
                "- [ ] 별도 JVM 프로세스 실행에서도 표준 출력·표준 오류·종료 상태가 같은 계약을 보입니다.\n",
                "",
            ),
        ),
        (
            "fewer-than-two-questions",
            lambda root: replace(
                root / "exercises/01-language-and-domain/01-first-program/README.md",
                "- `double` 대신 `BigDecimal`과 `HALF_UP`을 명시하면 어떤 모호함이 사라지나요?\n",
                "",
            ),
        ),
        (
            "missing-canonical-verification-command",
            lambda root: replace_all(
                root / "exercises/01-language-and-domain/01-first-program/README.md",
                "./scripts/check-workspace.sh exercises/01-language-and-domain/01-first-program",
                "echo 검증하지-않음",
            ),
        ),
        (
            "different-skeleton-test",
            lambda root: (
                root
                / "exercises/01-language-and-domain/02-value-object-contract/skeleton/src/test/java/dev/guides/java/valueobject/MoneyTest.java"
            ).write_text(
                (
                    root
                    / "exercises/01-language-and-domain/02-value-object-contract/skeleton/src/test/java/dev/guides/java/valueobject/MoneyTest.java"
                ).read_text(encoding="utf-8")
                + "// mutant\n",
                encoding="utf-8",
            ),
        ),
        (
            "wrong-wrapper-version",
            lambda root: replace(
                root / ".mvn/wrapper/maven-wrapper.properties", "3.9.16", "3.9.15"
            ),
        ),
        (
            "reference-todo",
            lambda root: replace(
                root
                / "exercises/01-language-and-domain/02-value-object-contract/reference/src/main/java/dev/guides/java/valueobject/Money.java",
                "public record Money",
                "// TODO mutant\npublic record Money",
            ),
        ),
        (
            "broken-markdown-link",
            lambda root: (
                root / "docs/00-roadmap.md"
            ).write_text(
                (root / "docs/00-roadmap.md").read_text(encoding="utf-8")
                + "\n[mutant](missing-document.md)\n",
                encoding="utf-8",
            ),
        ),
        (
            "broken-markdown-anchor",
            lambda root: replace(
                root / "README.md",
                "docs/00-roadmap.md",
                "docs/00-roadmap.md#missing-anchor",
            ),
        ),
        (
            "wrong-executable-mode",
            lambda root: (root / "scripts/preflight.sh").chmod(0o644),
        ),
    ]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-java-contracts-") as temporary:
        contract_root = Path(temporary)
        fixture = contract_root / "fixture"
        copied = Path(temporary) / "copied"
        fixture.mkdir()
        (fixture / "tracked.txt").write_text("tracked\n", encoding="utf-8")
        git_file = fixture / ".git"
        git_file.write_text("gitdir: /tmp/example-worktree\n", encoding="utf-8")
        linked_fingerprint = capture(fixture)
        git_file.unlink()
        regular_fingerprint = capture(fixture)
        if linked_fingerprint != regular_fingerprint:
            print("linked worktree의 .git 파일이 source fingerprint에 포함됩니다.", file=sys.stderr)
            return 1
        git_file.write_text("gitdir: /tmp/example-worktree\n", encoding="utf-8")
        copy_source(fixture, copied)
        if (copied / ".git").exists():
            print("linked worktree의 .git 파일이 격리 복사본에 포함됩니다.", file=sys.stderr)
            return 1
        print("[PASS] linked worktree .git 파일을 source 상태에서 제외")
        verify_raw_index_contract(contract_root)
        verify_log_preflight_contract(contract_root)
        verify_arbitrary_assertion_rejected(contract_root)
        verify_workspace_tools(contract_root)

        workspace_state = contract_root / "workspace-state"
        copied_state = contract_root / "workspace-state-copy"
        workspace_state.mkdir()
        copy_source(ROOT, workspace_state)
        full_before = capture(workspace_state)
        prepared_before = capture(workspace_state, include_learner_workspace=False)
        write_text(workspace_state / ".workspace/learner/note.txt", "learner\n")
        if capture(workspace_state) == full_before:
            raise AssertionError("learner workspace가 source manifest에서 빠졌습니다.")
        if capture(workspace_state, include_learner_workspace=False) != prepared_before:
            raise AssertionError("learner workspace가 준비 fingerprint를 불필요하게 바꿨습니다.")
        copy_source(workspace_state, copied_state)
        if not (copied_state / ".workspace/learner/note.txt").is_file():
            raise AssertionError("격리 source 복사가 learner workspace를 누락했습니다.")
        print("[PASS] learner workspace는 source 복사·불변성에 포함하고 준비 fingerprint에서만 제외")

    baseline = run_validator(ROOT)
    if baseline.returncode != 0:
        print("validator baseline이 실패했습니다.", file=sys.stderr)
        print(baseline.stdout, file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="guide-java-validator-") as temporary:
        temporary_root = Path(temporary)
        linked_root = temporary_root / "linked-worktree"
        linked_root.mkdir()
        copy_source(ROOT, linked_root)
        (linked_root / ".git").write_text(
            "gitdir: /tmp/example-worktree\n", encoding="utf-8"
        )
        linked_result = run_validator(linked_root)
        if linked_result.returncode != 0:
            print("validator가 linked worktree의 .git 파일을 제외하지 못했습니다.", file=sys.stderr)
            print(linked_result.stdout, file=sys.stderr)
            return 1
        print("[PASS] validator가 linked worktree .git 파일을 정확한 tree에서 제외")
        shutil.rmtree(linked_root)

        workspace_root = temporary_root / "workspace-exact-tree"
        workspace_root.mkdir()
        copy_source(ROOT, workspace_root)
        write_text(workspace_root / ".workspace/learner/note.txt", "learner\n")
        workspace_result = run_validator(workspace_root)
        if workspace_result.returncode != 0:
            print("validator가 top-level learner workspace를 curriculum tree로 오인했습니다.", file=sys.stderr)
            print(workspace_result.stdout, file=sys.stderr)
            return 1
        print("[PASS] validator가 top-level learner workspace를 exact curriculum tree에서 제외")
        shutil.rmtree(workspace_root)

        for name, mutate in mutations():
            mutant = temporary_root / name
            mutant.mkdir()
            copy_source(ROOT, mutant)
            mutate(mutant)
            result = run_validator(mutant)
            if result.returncode == 0:
                print(f"validator가 mutant를 놓쳤습니다: {name}", file=sys.stderr)
                return 1
            print(f"[PASS] validator mutant 거부: {name}")
            shutil.rmtree(mutant)
    print("validator mutant suite를 통과했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
