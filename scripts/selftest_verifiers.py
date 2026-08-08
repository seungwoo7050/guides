#!/usr/bin/env python3
"""Meta-tests for the repository's verification helpers.

The guide must reject crashes and arbitrary non-zero exits as learner progress;
it must also clean generated artifacts without touching source files.
"""

from __future__ import annotations

import importlib.util
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKELETON_VERIFIER = ROOT / "scripts/verify_modern_skeletons.py"
ARTIFACT_MANAGER = ROOT / "scripts/manage_artifacts.py"
TIMEOUT_RUNNER = ROOT / "scripts/run_with_timeout.py"
NETWORK_TEST_MODULES = [
    ROOT / "exercises/02-cpp98-systems/networking/line-server/tests.py",
    ROOT / "exercises/02-cpp98-systems/networking/http-server/03-nonblocking-server/tests.py",
    ROOT / "exercises/02-cpp98-systems/networking/http-server/05-integrated-server/tests.py",
]

CONTRACTS = [
    ("strong-types-and-cmake", "01-strong-types-and-cmake/strong_types_skeleton_tests"),
    ("unique-file", "02-unique-file/unique_file_skeleton_tests"),
    ("query-pipeline", "03-query-pipeline/query_pipeline_skeleton_tests"),
    ("local-job-runner", "04-local-job-runner/local_job_runner_skeleton_tests"),
]


def write_program(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "#!/bin/sh\nset -u\n" + "\n".join(lines) + "\n"
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def run_verifier(build: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SKELETON_VERIFIER), str(build)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


def expected_failure_lines(suite: str) -> list[str]:
    return [
        "printf '%s\\n' 'CHECK failed: intentional learner TODO' >&2",
        f"printf '%s\\n' '{suite}: 2 failure(s)' >&2",
        "exit 1",
    ]


def assert_rejected(build: Path, expected_text: str) -> None:
    result = run_verifier(build)
    output = result.stdout + result.stderr
    if result.returncode == 0 or expected_text not in output:
        raise AssertionError(
            f"verifier가 잘못된 시작점을 거부하지 못했습니다: "
            f"expected={expected_text!r}, exit={result.returncode}, output={output!r}"
        )


def test_skeleton_verifier(temp: Path) -> None:
    build = temp / "build"
    for suite, relative in CONTRACTS:
        write_program(build / relative, expected_failure_lines(suite))

    accepted = run_verifier(build)
    if accepted.returncode != 0:
        raise AssertionError(accepted.stdout + accepted.stderr)

    first = build / CONTRACTS[0][1]
    write_program(first, ["exit 2"])
    assert_rejected(build, "계약 실패가 아닌 종료 코드")

    write_program(
        first,
        expected_failure_lines(CONTRACTS[0][0])[:-1]
        + ["printf '%s\\n' 'Segmentation fault' >&2", "exit 1"],
    )
    assert_rejected(build, "비정상 종료")

    write_program(
        first,
        [
            f"printf '%s\\n' '{CONTRACTS[0][0]}: 1 failure(s)' >&2",
            "exit 1",
        ],
    )
    assert_rejected(build, "공통 test assertion 실패")


def run_manager(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ARTIFACT_MANAGER), *arguments],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


def test_artifact_manager(temp: Path) -> None:
    repository = temp / "repository"
    source = repository / "exercises/example/source.cpp"
    source.parent.mkdir(parents=True)
    source.write_text("int main() { return 0; }\n", encoding="utf-8")
    source.chmod(0o644)

    (repository / "build/cache").mkdir(parents=True)
    (repository / "build/cache/value").write_text("generated", encoding="utf-8")
    (repository / "make-out.txt").write_text("log", encoding="utf-8")
    (source.parent / "main.o").write_bytes(b"object")
    native = source.parent / "app"
    native.write_bytes(b"\x7fELF" + b"\0" * 32)
    native.chmod(0o755)

    before = run_manager("snapshot", str(repository))
    if before.returncode != 0:
        raise AssertionError(before.stdout + before.stderr)

    cleaned = run_manager("clean", str(repository))
    if cleaned.returncode != 0:
        raise AssertionError(cleaned.stdout + cleaned.stderr)
    audited = run_manager("audit", str(repository))
    if audited.returncode != 0:
        raise AssertionError(audited.stdout + audited.stderr)

    if source.read_text(encoding="utf-8") != "int main() { return 0; }\n":
        raise AssertionError("artifact cleanup이 source를 변경했습니다")
    for generated in (
        repository / "build",
        repository / "make-out.txt",
        source.parent / "main.o",
        native,
    ):
        if generated.exists() or generated.is_symlink():
            raise AssertionError(f"생성 산출물이 남았습니다: {generated}")

    after = run_manager("snapshot", str(repository))
    if after.returncode != 0 or before.stdout != after.stdout:
        raise AssertionError("생성 산출물 정리 전후 source snapshot이 달라졌습니다")


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_for_exit(pid: int, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not process_exists(pid):
            return True
        time.sleep(0.05)
    return not process_exists(pid)


def test_timeout_runner(temp: Path) -> None:
    temp.mkdir(parents=True, exist_ok=True)
    background_pid = temp / "background.pid"
    background_script = temp / "background.py"
    background_script.write_text(
        "import pathlib,subprocess,sys\n"
        "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])\n"
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid))\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(TIMEOUT_RUNNER), "5", "--", sys.executable, str(background_script), str(background_pid)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stdout + completed.stderr)
    pid = int(background_pid.read_text(encoding="utf-8"))
    if not wait_for_exit(pid):
        raise AssertionError(f"정상 종료 뒤 background descendant가 남았습니다: {pid}")

    direct_pid = temp / "direct.pid"
    timeout_script = temp / "timeout.py"
    timeout_script.write_text(
        "import os,pathlib,sys,time\n"
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    timed_out = subprocess.run(
        [sys.executable, str(TIMEOUT_RUNNER), "1", "--", sys.executable, str(timeout_script), str(direct_pid)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    if timed_out.returncode != 124 or "TIMEOUT after" not in timed_out.stderr:
        raise AssertionError(
            f"timeout runner 계약 위반: exit={timed_out.returncode}, stderr={timed_out.stderr!r}"
        )
    pid = int(direct_pid.read_text(encoding="utf-8"))
    if not wait_for_exit(pid):
        raise AssertionError(f"timeout 뒤 direct process가 남았습니다: {pid}")


def load_module(path: Path, index: int):
    spec = importlib.util.spec_from_file_location(f"guide_cpp_network_test_{index}", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"network test module을 읽을 수 없습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_network_harnesses() -> None:
    modules = [load_module(path, index) for index, path in enumerate(NETWORK_TEST_MODULES)]
    for module in modules:
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import sys,time;sys.stdout.write('PORT ');sys.stdout.flush();time.sleep(30)",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        started = time.monotonic()
        try:
            module.read_startup_line(process, timeout=0.2)
        except RuntimeError:
            pass
        else:
            raise AssertionError("부분 startup line을 완성된 포트 메시지로 인정했습니다")
        if time.monotonic() - started >= 2 or process.poll() is None:
            process.kill()
            process.wait()
            raise AssertionError("startup timeout이 서버 프로세스를 즉시 정리하지 못했습니다")

    line_module = modules[0]
    process = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(2)"])
    try:
        if line_module.fd_count(process.pid) <= 0:
            raise AssertionError("실행 중인 프로세스의 FD를 세지 못했습니다")
    finally:
        process.terminate()
        process.wait()

    first, second = socket.socketpair()
    try:
        line_module.assert_no_response(first, timeout=0.01)
        second.sendall(b"x")
        try:
            line_module.assert_no_response(first, timeout=0.1)
        except AssertionError:
            pass
        else:
            raise AssertionError("부분 프레임 뒤의 조기 응답을 감지하지 못했습니다")
    finally:
        first.close()
        second.close()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-cpp-verifier-selftest-") as directory:
        temp = Path(directory)
        test_skeleton_verifier(temp / "skeleton")
        test_artifact_manager(temp / "artifacts")
        test_timeout_runner(temp / "runner")
        test_network_harnesses()
    print("검증기 메타 검사: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
