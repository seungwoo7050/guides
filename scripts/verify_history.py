#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from process_runner import CommandSpawnError, run_process

ROOT = Path(__file__).resolve().parents[1]
def git(*args: str, check: bool = True) -> str:
    try:
        result = run_process(["git", *args], cwd=ROOT, timeout_seconds=30)
    except CommandSpawnError as error:
        raise SystemExit(f"HISTORY ERROR: {error}") from error
    if result.timed_out:
        raise SystemExit(f"HISTORY ERROR: git {' '.join(args)} timed out")
    if check and result.returncode != 0:
        raise SystemExit(f"HISTORY ERROR: git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def fail(message: str) -> None:
    raise SystemExit(f"HISTORY ERROR: {message}")


def main() -> None:
    branch = git("branch", "--show-current") or "detached"

    commits = git("rev-list", "--reverse", "HEAD").splitlines()
    if len(commits) < 2:
        fail("기초와 학습 내용을 한 commit에 넣은 history는 검토할 수 없습니다.")

    roots = git("rev-list", "--max-parents=0", "HEAD").splitlines()
    if len(roots) != 1:
        fail(f"독립 history root는 하나여야 합니다: roots={len(roots)}")
    root_files = set(git("show", "--pretty=format:", "--name-only", roots[0]).splitlines())

    merge_commits = git("rev-list", "--min-parents=2", "HEAD").splitlines()

    subjects = git("log", "--format=%s", "--reverse").splitlines()
    subject_pattern = re.compile(r"^(chore|docs|feat|test|fix|refactor)(\([^)]+\))?: .+")
    for subject in subjects:
        if subject.startswith("Merge "):
            continue
        if not subject_pattern.match(subject):
            fail(f"commit subject가 의미 단위 형식을 따르지 않습니다: {subject}")
        lowered = subject.lower()
        if lowered.startswith(("fixup!", "squash!")) or "initial import" in lowered:
            fail(f"사후 정리용 또는 전체 import commit은 허용하지 않습니다: {subject}")

    prefixes = {subject.split(":", 1)[0].split("(", 1)[0] for subject in subjects}
    missing = {"chore", "docs", "feat", "test"} - prefixes
    if missing:
        fail(f"기초·문서·구현·검증 단위가 모두 필요합니다: missing={sorted(missing)}")

    try:
        main_ref = run_process(
            ["git", "rev-parse", "--verify", "main^{commit}"], cwd=ROOT, timeout_seconds=15
        )
    except CommandSpawnError as error:
        fail(str(error))
    if main_ref.timed_out or main_ref.returncode != 0:
        fail("main ref를 확인할 수 없어 독립 history를 검증하지 못했습니다.")
    try:
        merge_base = run_process(["git", "merge-base", "main", "HEAD"], cwd=ROOT, timeout_seconds=15)
    except CommandSpawnError as error:
        fail(str(error))
    if merge_base.timed_out or merge_base.returncode not in (0, 1):
        fail(f"main merge-base를 확인하지 못했습니다: {merge_base.stderr.strip()}")
    independent = "yes" if merge_base.returncode == 1 else "no"
    if independent == "no":
        fail("main과 parent history를 공유합니다. 독립 branch history 계약을 검토하십시오.")

    print(
        f"HISTORY REPORT branch={branch} commits={len(commits)} root={roots[0][:8]} "
        f"root_files={len(root_files)} merge_commits={len(merge_commits)} "
        f"independent_from_main={independent} units={','.join(sorted(prefixes))}"
    )
    print("HISTORY LIMIT: commit 수와 subject 형식은 의미 단위의 교육 품질을 자동 판정하지 않음")


if __name__ == "__main__":
    main()
