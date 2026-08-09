#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from capstone_behavior import (
    BehaviorRunError,
    REPO_ROOT,
    SKELETON,
    capture,
    capture_known_bad_quality,
    expected_patch,
)


def refuse_symlink_chain(path: Path) -> None:
    current = path
    while True:
        if current.is_symlink():
            raise ValueError(f"symlink 경로는 사용할 수 없습니다: {current}")
        if current == REPO_ROOT:
            return
        if current.parent == current:
            break
        current = current.parent
    raise ValueError(f"저장소 밖 경로입니다: {path}")


def atomic_write(path: Path, text: str) -> None:
    if path.is_symlink():
        raise ValueError(f"symlink 출력은 덮어쓰지 않습니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capstone의 격리 행동 evidence와 patch를 생성합니다.")
    parser.add_argument("workdir", type=Path)
    args = parser.parse_args()

    unresolved_work = args.workdir.absolute()
    refuse_symlink_chain(unresolved_work)
    work = unresolved_work.resolve()
    if not work.is_dir():
        parser.error(f"작업 디렉터리가 없습니다: {work}")
    implementation = work / "behavior-lab/ledgerlab_policy.py"
    refuse_symlink_chain(implementation)
    if implementation.is_symlink() or not implementation.is_file():
        parser.error(f"일반 implementation 파일이 필요합니다: {implementation}")

    try:
        vulnerable_evidence, vulnerable_output = capture(SKELETON, "vulnerable")
        secure_evidence, secure_output = capture(implementation, "secure")
        known_bad_evidence = capture_known_bad_quality()
        patch = expected_patch(implementation)
    except BehaviorRunError as exc:
        if exc.output:
            print(exc.output, end="", file=sys.stderr)
        parser.error(str(exc))
    if not patch:
        parser.error("skeleton과 implementation이 같습니다. 보안 계약을 복원하는 patch가 필요합니다.")

    atomic_write(work / "vulnerable-evidence.json", json.dumps(vulnerable_evidence, ensure_ascii=False, indent=2) + "\n")
    atomic_write(work / "behavior-evidence.json", json.dumps(secure_evidence, ensure_ascii=False, indent=2) + "\n")
    atomic_write(work / "known-bad-evidence.json", json.dumps(known_bad_evidence, ensure_ascii=False, indent=2) + "\n")
    atomic_write(work / "behavior-patch.diff", patch)
    print(vulnerable_output, end="")
    print(secure_output, end="")
    print(known_bad_evidence["output"], end="")
    print("CAPSTONE BEHAVIOR READY files=4 profile=vulnerable+secure+known-bad")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
