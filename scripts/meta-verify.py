#!/usr/bin/env python3
"""정적 검증기가 알려진 구조 결함을 실제로 거부하는지 확인합니다."""
from __future__ import annotations

import os
import stat
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "scripts" / "static-verify.py"


def run_static() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(STATIC), "--allow-generated-exercise-state"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


@contextmanager
def preserve_file(path: Path) -> Iterator[None]:
    existed = path.exists()
    content = path.read_bytes() if existed else b""
    mode = stat.S_IMODE(path.stat().st_mode) if existed else None
    try:
        yield
    finally:
        if existed:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            assert mode is not None
            path.chmod(mode)
        else:
            path.unlink(missing_ok=True)


def assert_rejected(
    label: str,
    path: Path,
    mutation: Callable[[Path], None],
    expected_fragment: str,
) -> str | None:
    with preserve_file(path):
        mutation(path)
        completed = run_static()
    output = completed.stdout
    if completed.returncode == 0:
        return f"{label}: 결함이 있는데 정적 검증기가 성공했습니다."
    if expected_fragment not in output:
        return (
            f"{label}: 실패 이유가 기대한 계약과 다릅니다. "
            f"기대 문자열={expected_fragment!r}\n{output}"
        )
    print(f"[PASS] mutant rejected: {label}")
    return None


def main() -> int:
    baseline = run_static()
    if baseline.returncode != 0:
        print("meta-test를 시작하기 전에 기준 저장소의 정적 검사가 실패했습니다.", file=sys.stderr)
        print(baseline.stdout, file=sys.stderr)
        return 1

    errors: list[str] = []

    missing_doc = ROOT / "docs" / "18-production-rebuild-capstone.md"
    error = assert_rejected(
        "필수 문서 삭제",
        missing_doc,
        lambda path: path.unlink(),
        "필수 파일이 없습니다: docs/18-production-rebuild-capstone.md",
    )
    if error:
        errors.append(error)

    readme = ROOT / "README.md"

    def add_broken_link(path: Path) -> None:
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n[meta broken link](docs/__meta_missing__.md)\n",
            encoding="utf-8",
        )

    error = assert_rejected(
        "깨진 내부 링크",
        readme,
        add_broken_link,
        "Markdown 링크 대상이 없습니다",
    )
    if error:
        errors.append(error)

    exercise_readme = ROOT / "exercises" / "01-request-and-process" / "README.md"

    def remove_self_explanation_contract(path: Path) -> None:
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "## 자기 설명", "## 설명 메모", 1
            ),
            encoding="utf-8",
        )

    error = assert_rejected(
        "학습 자기 설명 계약 제거",
        exercise_readme,
        remove_self_explanation_contract,
        "exercise 학습 자기 설명이 없습니다",
    )
    if error:
        errors.append(error)

    leaked_key = ROOT / "exercises" / "10-public-tls" / "reference" / "leaked.key"
    error = assert_rejected(
        "추적된 개인키 부산물",
        leaked_key,
        lambda path: path.write_text("not-a-real-key\n", encoding="utf-8"),
        "생성 파일을 배포 자료에 포함할 수 없습니다",
    )
    if error:
        errors.append(error)

    shell = ROOT / "exercises" / "01-request-and-process" / "verify.sh"

    def remove_execute_permission(path: Path) -> None:
        path.chmod(stat.S_IMODE(path.stat().st_mode) & ~stat.S_IXUSR)

    error = assert_rejected(
        "검증 스크립트 실행 권한 제거",
        shell,
        remove_execute_permission,
        "셸 스크립트에 실행 권한이 없습니다",
    )
    if error:
        errors.append(error)

    legacy = ROOT / "before-verify.sh"
    error = assert_rejected(
        "구형 최종화 스크립트 재등장",
        legacy,
        lambda path: path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8"),
        "구형 또는 생성 파일 경로가 남아 있습니다",
    )
    if error:
        errors.append(error)

    final = run_static()
    if final.returncode != 0:
        errors.append(f"mutation 복원 뒤 기준 정적 검사가 실패했습니다.\n{final.stdout}")

    if errors:
        print(f"검증기 meta-test 실패: {len(errors)}건", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        return 1

    print(
        "검증기 meta-test 통과: 필수 파일, 링크, 학습 루브릭, "
        "개인키, 실행 권한, 구형 경로"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
