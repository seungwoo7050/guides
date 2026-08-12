#!/usr/bin/env python3
"""Prove that the capstone runner accepts and rejects the intended contracts."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CAPSTONE = ROOT / "exercises/07-verified-algorithms-capstone"
CHECKER = CAPSTONE / "check.py"
REFERENCE = CAPSTONE / "reference/algorithms.py"


def run(
    *arguments: str,
    extra_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("EXERCISE_IMPL", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra_environment:
        environment.update(extra_environment)
    return subprocess.run(
        [sys.executable, str(CHECKER), *arguments],
        cwd=CAPSTONE,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def require(condition: bool, label: str, result: subprocess.CompletedProcess[str]) -> None:
    if not condition:
        raise AssertionError(
            f"{label}\nreturncode={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def expected_success(label: str, *arguments: str, **kwargs: object) -> None:
    result = run(*arguments, **kwargs)
    require(result.returncode == 0, label, result)


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def require_process_gone(pid: int, label: str) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not process_exists(pid):
            return
        time.sleep(0.05)
    raise AssertionError(f"{label}: checker child process가 남았습니다: {pid}")


def expected_logical_failure(
    label: str,
    implementation: str,
    stage: str,
    expected_tests: tuple[str, ...],
) -> None:
    raw = run("--impl", implementation, "--stage", stage, "--expect", "pass")
    output = raw.stdout + raw.stderr
    require(raw.returncode not in {0, 124}, f"{label}: 논리 실패가 없습니다", raw)
    failure_headers = set(re.findall(r"^FAIL: ([^(\s]+)", output, flags=re.MULTILINE))
    error_headers = set(re.findall(r"^ERROR: ([^(\s]+)", output, flags=re.MULTILINE))
    require(not error_headers and "errors=" not in output, f"{label}: unittest ERROR 발생", raw)
    require(
        set(expected_tests) <= failure_headers,
        f"{label}: 지정 test의 FAIL header가 없습니다: {expected_tests}",
        raw,
    )
    for marker in ("ImportError", "ModuleNotFoundError", "SyntaxError", "NotImplementedError"):
        require(marker not in output, f"{label}: infrastructure 오류를 논리 실패로 오인했습니다", raw)
    expected_success(
        f"{label}: checker failure 방향",
        "--impl",
        implementation,
        "--stage",
        stage,
        "--expect",
        "fail",
    )


@contextmanager
def semantic_mutant(replacements: tuple[tuple[str, str], ...]) -> Iterator[str]:
    source = REFERENCE.read_text(encoding="utf-8")
    for original, replacement in replacements:
        if source.count(original) != 1:
            raise AssertionError(f"semantic mutant 대상이 정확히 하나가 아닙니다: {original!r}")
        source = source.replace(original, replacement)

    with tempfile.TemporaryDirectory(prefix=".semantic-", dir=CAPSTONE / "broken") as directory:
        path = Path(directory)
        (path / "algorithms.py").write_text(source, encoding="utf-8")
        yield path.relative_to(CAPSTONE).as_posix()


def main() -> int:
    cases = 0
    expected_success("reference 전체 계약", "--impl", "reference", "--stage", "all", "--expect", "pass")
    cases += 1

    for stage in ("data-structures", "design-techniques", "graphs", "strings"):
        expected_success(
            f"skeleton {stage} 미구현 경계",
            "--impl",
            "skeleton",
            "--stage",
            stage,
            "--expect",
            "not-implemented",
        )
        cases += 1

    broken_cases = (
        (
            "broken/off-by-one",
            "data-structures",
            "test_prefix_contract_and_random_ranges",
        ),
        (
            "broken/wrong-greedy",
            "design-techniques",
            "test_interval_selection_matches_exhaustive_optimum",
        ),
        (
            "broken/missed-negative-cycle",
            "graphs",
            "test_bellman_ford_handles_negative_edges_and_cycle_contract",
        ),
        ("broken/empty-pattern", "strings", "test_kmp_matches_builtin_find"),
    )
    for implementation, stage, expected_test in broken_cases:
        expected_logical_failure(
            f"{implementation} 결함 검출",
            implementation,
            stage,
            (expected_test,),
        )
        cases += 1

    wrong_failure_direction = run(
        "--impl",
        "skeleton",
        "--stage",
        "data-structures",
        "--expect",
        "fail",
    )
    require(
        wrong_failure_direction.returncode != 0
        and "unittest ERROR" in wrong_failure_direction.stderr,
        "NotImplementedError를 논리 결함 성공으로 오인",
        wrong_failure_direction,
    )
    cases += 1

    semantic_cases = (
        (
            "interval 결정적 tie-break 위반",
            "design-techniques",
            ("test_interval_selection_matches_exhaustive_optimum",),
            (("key=lambda item: (item[1], item[0])", "key=lambda item: (item[1], -item[0])"),),
        ),
        (
            "MST 원본 edge·연결·acyclic certificate 위반",
            "graphs",
            ("test_kruskal_matches_spanning_tree_enumeration",),
            (("    return total, chosen", "    return total, [(0, 0, 0)] * (vertex_count - 1)"),),
        ),
        (
            "max-flow capacity·conservation certificate 위반",
            "graphs",
            ("test_max_flow_value_and_certificate_match_all_cuts",),
            (("            return total, flow", "            return total, [[0] * size for _ in range(size)]"),),
        ),
        (
            "interval·MST·max-flow 결합 semantic 계약 위반",
            "all",
            (
                "test_interval_selection_matches_exhaustive_optimum",
                "test_kruskal_matches_spanning_tree_enumeration",
                "test_max_flow_value_and_certificate_match_all_cuts",
            ),
            (
                ("key=lambda item: (item[1], item[0])", "key=lambda item: (item[1], -item[0])"),
                ("    return total, chosen", "    return total, [(0, 0, 0)] * (vertex_count - 1)"),
                ("            return total, flow", "            return total, [[0] * size for _ in range(size)]"),
            ),
        ),
    )
    for label, stage, expected_tests, replacements in semantic_cases:
        with semantic_mutant(replacements) as implementation:
            expected_logical_failure(
                label,
                implementation,
                stage,
                expected_tests,
            )
        cases += 1

    with semantic_mutant(
        ((
            "def prefix_sums(values: Sequence[int]) -> list[int]:\n    prefix = [0]",
            "def prefix_sums(values: Sequence[int]) -> list[int]:\n    prefix = missing_prefix_name",
        ),)
    ) as implementation:
        infrastructure = run(
            "--impl",
            implementation,
            "--stage",
            "data-structures",
            "--expect",
            "fail",
        )
        require(
            infrastructure.returncode != 0
            and "unittest ERROR" in infrastructure.stderr,
            "NameError를 논리 계약 실패로 오인",
            infrastructure,
        )
    cases += 1

    expected_success(
        "비종료 구현 시간 제한",
        "--impl",
        "broken/non-terminating",
        "--stage",
        "strings",
        "--expect",
        "timeout",
        extra_environment={"EXERCISE_TIMEOUT": "1"},
    )
    cases += 1

    with tempfile.TemporaryDirectory(prefix=".signal-cleanup-", dir=CAPSTONE / "broken") as directory:
        signal_fixture = Path(directory)
        child_pid_file = signal_fixture / "child.pid"
        (signal_fixture / "algorithms.py").write_text(
            "import os\n"
            "from pathlib import Path\n"
            "Path(os.environ['GUIDE_CHECKER_CHILD_PID']).write_text(str(os.getpid()), encoding='utf-8')\n"
            "def kmp_find(text: str, pattern: str) -> int:\n"
            "    while True:\n"
            "        pass\n",
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment.update(
            PYTHONDONTWRITEBYTECODE="1",
            EXERCISE_TIMEOUT="30",
            GUIDE_CHECKER_CHILD_PID=str(child_pid_file),
        )
        checker_process = subprocess.Popen(
            [
                sys.executable,
                str(CHECKER),
                "--impl",
                signal_fixture.relative_to(CAPSTONE).as_posix(),
                "--stage",
                "strings",
                "--expect",
                "timeout",
            ],
            cwd=CAPSTONE,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 5
        while (
            not child_pid_file.is_file()
            and checker_process.poll() is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.02)
        if not child_pid_file.is_file():
            checker_process.kill()
            stdout, stderr = checker_process.communicate()
            raise AssertionError(f"checker child PID를 관찰하지 못했습니다\n{stdout}\n{stderr}")
        child_pid = int(child_pid_file.read_text(encoding="utf-8"))
        checker_process.send_signal(signal.SIGTERM)
        stdout, stderr = checker_process.communicate(timeout=8)
        if checker_process.returncode != 143:
            raise AssertionError(
                f"checker signal exit={checker_process.returncode}\n{stdout}\n{stderr}"
            )
        require_process_gone(child_pid, "checker external signal cleanup")
    cases += 1

    with tempfile.TemporaryDirectory(prefix=".timeout-spoof-", dir=CAPSTONE / "broken") as directory:
        spoof = Path(directory)
        (spoof / "algorithms.py").write_text(
            'print("TIMEOUT")\nraise SystemExit(124)\n',
            encoding="utf-8",
        )
        spoof_result = run(
            "--impl",
            spoof.relative_to(CAPSTONE).as_posix(),
            "--stage",
            "strings",
            "--expect",
            "timeout",
        )
        require(
            spoof_result.returncode != 0 and "시간 제한이 발생하지" in spoof_result.stderr,
            "exit 124·TIMEOUT 문자열을 실제 timeout으로 오인",
            spoof_result,
        )
    cases += 1

    with tempfile.TemporaryDirectory(prefix=".symlink-boundary-", dir=CAPSTONE / "broken") as directory:
        boundary = Path(directory)
        directory_link = boundary / "directory-link"
        directory_link.symlink_to(REFERENCE.parent, target_is_directory=True)
        directory_result = run(
            "--impl",
            directory_link.relative_to(CAPSTONE).as_posix(),
            "--stage",
            "all",
            "--expect",
            "pass",
        )
        require(
            directory_result.returncode != 0 and "symbolic link" in directory_result.stderr,
            "workspace directory symlink를 reference로 따라감",
            directory_result,
        )

        file_link = boundary / "file-link"
        file_link.mkdir()
        (file_link / "algorithms.py").symlink_to(REFERENCE)
        file_result = run(
            "--impl",
            file_link.relative_to(CAPSTONE).as_posix(),
            "--stage",
            "all",
            "--expect",
            "pass",
        )
        require(
            file_result.returncode != 0 and "symbolic link" in file_result.stderr,
            "workspace source symlink를 reference로 따라감",
            file_result,
        )
    cases += 2

    with tempfile.TemporaryDirectory(prefix="guide-algorithms-no-workspace-") as directory:
        checker_copy = Path(directory) / "check.py"
        shutil.copy2(CHECKER, checker_copy)
        missing_environment = os.environ.copy()
        missing_environment["EXERCISE_IMPL"] = "reference"
        missing = subprocess.run(
            [sys.executable, str(checker_copy)],
            cwd=checker_copy.parent,
            env=missing_environment,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        require(
            missing.returncode != 0
            and "scripts/new-workspace.sh exercises/07-verified-algorithms-capstone"
            in missing.stderr,
            "--impl 생략·외부 EXERCISE_IMPL 설정 시 workspace fail-closed 안내 누락",
            missing,
        )
    cases += 1

    traversal = run("--impl", "../../", "--stage", "all", "--expect", "pass")
    require(traversal.returncode != 0 and "capstone 내부" in traversal.stderr, "경로 이탈 거부", traversal)
    cases += 1

    invalid_timeout = run(
        "--impl",
        "reference",
        "--stage",
        "all",
        "--expect",
        "pass",
        extra_environment={"EXERCISE_TIMEOUT": "0"},
    )
    require(
        invalid_timeout.returncode != 0 and "양수" in invalid_timeout.stderr,
        "잘못된 시간 제한 거부",
        invalid_timeout,
    )
    cases += 1

    print(f"[PASS] checker contracts: {cases}개 positive/negative/timeout/boundary 사례")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
