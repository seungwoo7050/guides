#!/usr/bin/env python3
"""Meta-test kernel-model checkpoints, timeout behavior and test uniqueness."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
EXERCISE = ROOT / "exercises/kernel-model"
CHECKER = EXERCISE / "check.py"
CHECKPOINTS = (
    "01-lifecycle",
    "02-synchronization",
    "03-scheduler",
    "04-deadlock",
    "05-paging",
    "06-storage",
    "07-device-io",
    "08-cli",
)


def signal_probe(info_path: Path, residual_path: Path) -> int:
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(600)"],
        start_new_session=False,
    )
    residual_path.write_text("owned temporary bytes\n", encoding="utf-8")
    temporary = info_path.with_name(info_path.name + f".tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(
            {
                "probe_pid": os.getpid(),
                "grandchild_pid": child.pid,
                "process_group": os.getpgid(0) if os.name == "posix" else 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(info_path)
    while True:
        time.sleep(60)


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_processes_gone(pids: tuple[int, ...], timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any(process_alive(pid) for pid in pids):
            return True
        time.sleep(0.05)
    return not any(process_alive(pid) for pid in pids)


def run(*arguments: str, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    values = os.environ.copy()
    values["PYTHONDONTWRITEBYTECODE"] = "1"
    if environment:
        values.update(environment)
    return subprocess.run(
        [sys.executable, str(CHECKER), *arguments],
        cwd=EXERCISE,
        env=values,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def require(condition: bool, label: str, result: subprocess.CompletedProcess[str] | None = None) -> None:
    if condition:
        return
    detail = "" if result is None else (
        f"\nreturncode={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    raise AssertionError(label + detail)


def check_test_ast() -> int:
    source = CHECKER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names: set[str] = set()
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
            continue
        require(node.name not in names, f"중복 test 이름: {node.name}")
        names.add(node.name)
        count += 1
        assertions: set[str] = set()
        assertion_count = 0
        for child in ast.walk(node):
            if not (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr.startswith("assert")
            ):
                continue
            normalized = ast.dump(child, include_attributes=False)
            require(normalized not in assertions, f"중복 assertion: {node.name}")
            assertions.add(normalized)
            assertion_count += 1
        require(assertion_count > 0, f"assertion 없는 test: {node.name}")
    require(count >= 20, f"checkpoint test가 부족합니다: {count}")
    return count


def main() -> int:
    test_count = check_test_ast()
    cases = 0
    for checkpoint in CHECKPOINTS:
        result = run("reference", checkpoint)
        require(
            result.returncode == 0 and f"checkpoint={checkpoint}" in result.stdout,
            f"reference checkpoint 실패: {checkpoint}",
            result,
        )
        cases += 1

    for mode, marker in (("skeleton", "checkpoints=8"), ("failure", "fixtures=8")):
        result = run(mode)
        require(result.returncode == 0 and marker in result.stdout, f"{mode} 계약 실패", result)
        cases += 1

    invalid = run("reference", "09-missing")
    require(invalid.returncode != 0 and "알 수 없는 checkpoint" in invalid.stderr, "checkpoint 경계", invalid)
    cases += 1
    traversal = run("implementation", "../../", "all")
    require(traversal.returncode != 0 and "kernel-model 디렉터리 안" in traversal.stderr, "경로 이탈", traversal)
    cases += 1
    invalid_timeout = run(
        "reference",
        "01-lifecycle",
        environment={"KERNEL_MODEL_TIMEOUT": "0"},
    )
    require(
        invalid_timeout.returncode != 0 and "양수여야 합니다" in invalid_timeout.stderr,
        "0 timeout 입력 거부",
        invalid_timeout,
    )
    cases += 1

    with tempfile.TemporaryDirectory(prefix=".checker-mutant.", dir=EXERCISE) as temporary:
        mutant = Path(temporary)
        shutil.copytree(EXERCISE / "reference", mutant, dirs_exist_ok=True)
        scheduler = mutant / "kernel_model/scheduler.py"
        scheduler.write_text(
            scheduler.read_text(encoding="utf-8")
            + "\n\ndef simulate(*_args: object, **_kwargs: object) -> object:\n"
            + "    while True:\n"
            + "        pass\n",
            encoding="utf-8",
        )
        timeout = run(
            "implementation",
            mutant.name,
            "03-scheduler",
            environment={"KERNEL_MODEL_TIMEOUT": "1"},
        )
        require(timeout.returncode == 124 and "TIMEOUT" in timeout.stderr, "checker timeout mutant", timeout)
        cases += 1

    timeout_runner = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_with_timeout.py"),
            "--timeout",
            "0.2",
            "--",
            sys.executable,
            "-c",
            "while True: pass",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    require(
        timeout_runner.returncode == 124 and "TIMEOUT" in timeout_runner.stderr,
        "공통 timeout runner",
        timeout_runner,
    )
    cases += 1

    with tempfile.TemporaryDirectory(prefix="guide-os-runner-signal-") as temporary:
        fixture = Path(temporary)
        info = fixture / "processes.json"
        residual = fixture / "owned.residual"
        runner = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "scripts/run_with_timeout.py"),
                "--timeout",
                "30",
                "--",
                sys.executable,
                str(Path(__file__).resolve()),
                "--signal-probe",
                str(info),
                str(residual),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 5
        while not info.exists() and runner.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        require(info.is_file(), "runner signal probe process tree를 관찰하지 못했습니다")
        pids_data = json.loads(info.read_text(encoding="utf-8"))
        pids = (int(pids_data["probe_pid"]), int(pids_data["grandchild_pid"]))
        runner.send_signal(signal.SIGTERM)
        stdout, stderr = runner.communicate(timeout=8)
        signal_result = subprocess.CompletedProcess(runner.args, runner.returncode, stdout, stderr)
        require(runner.returncode == 143 and "SIGNAL" in stderr, "runner SIGTERM 반환 계약", signal_result)
        require(wait_processes_gone(pids), f"runner 종료 뒤 owned process가 남았습니다: {pids}")
        require(residual.is_file(), "runner signal fixture가 residual 파일을 만들지 못했습니다")
        cases += 1

    print(f"[PASS] checker meta: tests={test_count}, checkpoint/boundary/timeout cases={cases}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--signal-probe":
        raise SystemExit(signal_probe(Path(sys.argv[2]), Path(sys.argv[3])))
    raise SystemExit(main())
