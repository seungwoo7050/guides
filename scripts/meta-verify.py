#!/usr/bin/env python3
"""정적 검증기가 알려진 구조 결함을 실제로 거부하는지 확인합니다."""
from __future__ import annotations

import os
import re
import shutil
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


@contextmanager
def preserve_absent_path(path: Path) -> Iterator[None]:
    if path.exists() or path.is_symlink():
        raise AssertionError(f"meta-test 전용 경로가 기준 저장소에 이미 있습니다: {path}")
    try:
        yield
    finally:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path)


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


def assert_added_path_rejected(
    label: str,
    path: Path,
    mutation: Callable[[Path], None],
    expected_fragment: str,
) -> str | None:
    with preserve_absent_path(path):
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

    legacy_solution = (
        ROOT / "exercises" / "01-request-and-process" / "solution"
    )

    def add_legacy_solution(path: Path) -> None:
        path.mkdir()
        (path / "server.py").write_text("# legacy duplicate answer\n", encoding="utf-8")

    error = assert_added_path_rejected(
        "legacy solution directory 재등장",
        legacy_solution,
        add_legacy_solution,
        "예상하지 않은 exercise direct path입니다",
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

    def remove_learning_mapping_row(path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"(?m)^\| 01 \|.*\n", "", text, count=1)
        path.write_text(text, encoding="utf-8")

    error = assert_rejected(
        "ordered learning mapping 행 제거",
        readme,
        remove_learning_mapping_row,
        "README learning mapping은 01–18 행을 정확히 한 번씩 가져야 합니다",
    )
    if error:
        errors.append(error)

    annotation_source = (
        ROOT / "exercises" / "01-request-and-process" / "reference" / "server.py"
    )

    def duplicate_implementation_marker(path: Path) -> None:
        prefix = "[" + "Implementation "
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                prefix + "2]", prefix + "1]", 1
            ),
            encoding="utf-8",
        )

    error = assert_rejected(
        "Implementation 번호 중복",
        annotation_source,
        duplicate_implementation_marker,
        "Implementation 번호가 중복됩니다",
    )
    if error:
        errors.append(error)

    def add_implementation_child_gap(path: Path) -> None:
        marker = "[" + "Implementation 1-2]"
        path.write_text(
            path.read_text(encoding="utf-8")
            + f"\n# {marker} child 1을 건너뛴 잘못된 표식\n",
            encoding="utf-8",
        )

    error = assert_rejected(
        "Implementation child gap",
        annotation_source,
        add_implementation_child_gap,
        "Implementation 1의 child 번호가 1부터 연속되지 않습니다",
    )
    if error:
        errors.append(error)

    skeleton_source = (
        ROOT / "exercises" / "01-request-and-process" / "skeleton" / "server.py"
    )

    def leak_annotation_to_skeleton(path: Path) -> None:
        marker = "[" + "Implementation 1]"
        path.write_text(
            path.read_text(encoding="utf-8")
            + f"\n# {marker} 정답 순서를 노출하는 잘못된 표식\n",
            encoding="utf-8",
        )

    error = assert_rejected(
        "skeleton annotation 누출",
        skeleton_source,
        leak_annotation_to_skeleton,
        "Implementation annotation은 reference 또는 owning README에만 허용됩니다",
    )
    if error:
        errors.append(error)

    expected_evidence_readme = (
        ROOT / "exercises" / "08-production-contract" / "README.md"
    )

    def move_readme_annotation_outside_section(path: Path) -> None:
        prefix = "[" + "Implementation "
        text = path.read_text(encoding="utf-8").replace(
            f"| {prefix}1] |", "| 1 |", 1
        )
        path.write_text(
            text + f"\n| {prefix}1] | misplaced marker |\n",
            encoding="utf-8",
        )

    error = assert_rejected(
        "README annotation section 이탈",
        expected_evidence_readme,
        move_readme_annotation_outside_section,
        "README exact annotation은 권장 작성 순서 section 안에만 있어야 합니다",
    )
    if error:
        errors.append(error)

    wrapper = ROOT / "exercises" / "09-host-hardening" / "verify.sh"

    def remove_workspace_mode(path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        text = text.replace("skeleton|workspace|reference", "skeleton|reference", 1)
        text = text.replace("mode=${1:-workspace}", "mode=${1:-reference}", 1)
        path.write_text(text, encoding="utf-8")

    error = assert_rejected(
        "exercise workspace mode 제거",
        wrapper,
        remove_workspace_mode,
        "exercise wrapper 기본 mode는 workspace여야 합니다",
    )
    if error:
        errors.append(error)

    analysis_wrapper = ROOT / "exercises" / "07-troubleshooting" / "verify.sh"

    def change_analysis_default_mode(path: Path) -> None:
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "mode=${1:-workspace}", "mode=${1:-template}", 1
            ),
            encoding="utf-8",
        )

    error = assert_rejected(
        "07 workspace 기본 mode 제거",
        analysis_wrapper,
        change_analysis_default_mode,
        "07 분석 실습 wrapper 기본 mode는 workspace여야 합니다",
    )
    if error:
        errors.append(error)

    cleanup_runtime = ROOT / "scripts" / "cleanup-runtime.sh"

    def drift_scenario_inventory(path: Path) -> None:
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "        data-loss\n", "        data-loss-drift\n", 1
            ),
            encoding="utf-8",
        )

    error = assert_rejected(
        "07 runtime cleanup scenario drift",
        cleanup_runtime,
        drift_scenario_inventory,
        "runtime cleanup의 scenario inventory가 canonical 6개와 다릅니다",
    )
    if error:
        errors.append(error)

    workspace_generator = ROOT / "scripts" / "new-workspace.py"

    def drift_workspace_mapping(path: Path) -> None:
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                '"exercises/08-production-contract": "skeleton"',
                '"exercises/08-production-contract": "template"',
                1,
            ),
            encoding="utf-8",
        )

    error = assert_rejected(
        "workspace source mapping drift",
        workspace_generator,
        drift_workspace_mapping,
        "workspace generator의 exercise/source mapping",
    )
    if error:
        errors.append(error)

    evidence_template = (
        ROOT / "exercises" / "07-troubleshooting" / "template" / "evidence.md"
    )

    def remove_evidence_field(path: Path) -> None:
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "- 데이터 상태 재검증: <작성>\n", "", 1
            ),
            encoding="utf-8",
        )

    error = assert_rejected(
        "07 evidence template 필드 제거",
        evidence_template,
        remove_evidence_field,
        "07 evidence template 검사에 실패했습니다",
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
        "검증기 meta-test 통과: 필수 파일, 링크, 학습 지도·루브릭, "
        "exercise layout, workspace·evidence, annotation, 개인키, 실행 권한, 구형 경로"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
