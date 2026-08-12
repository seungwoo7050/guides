#!/usr/bin/env python3
"""Meta-tests for the repository's verification helpers.

The guide must reject crashes and arbitrary non-zero exits as learner progress;
it must also clean generated artifacts without touching source files.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import validate_annotations

ROOT = Path(__file__).resolve().parents[1]
SKELETON_VERIFIER = ROOT / "scripts/verify_modern_skeletons.py"
ARTIFACT_MANAGER = ROOT / "scripts/manage_artifacts.py"
TIMEOUT_RUNNER = ROOT / "scripts/run_with_timeout.py"
NEW_WORKSPACE = ROOT / "scripts/new_workspace.py"
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

    learner = repository / ".workspace/01-modern-cpp/skeleton/main.cpp"
    learner.parent.mkdir(parents=True)
    learner.write_text("int learner() { return 1; }\n", encoding="utf-8")
    learner_build = repository / ".workspace/01-modern-cpp/build/result.o"
    learner_build.parent.mkdir(parents=True)
    learner_build.write_bytes(b"learner object")

    before = run_manager("snapshot", str(repository))
    if before.returncode != 0:
        raise AssertionError(before.stdout + before.stderr)
    before_records = json.loads(before.stdout)
    if any(str(record["path"]).startswith(".workspace/") for record in before_records):
        raise AssertionError("artifact snapshot이 learner workspace를 포함했습니다")

    cleaned = run_manager("clean", str(repository))
    if cleaned.returncode != 0:
        raise AssertionError(cleaned.stdout + cleaned.stderr)
    audited = run_manager("audit", str(repository))
    if audited.returncode != 0:
        raise AssertionError(audited.stdout + audited.stderr)

    if source.read_text(encoding="utf-8") != "int main() { return 0; }\n":
        raise AssertionError("artifact cleanup이 source를 변경했습니다")
    if learner.read_text(encoding="utf-8") != "int learner() { return 1; }\n":
        raise AssertionError("artifact cleanup이 learner workspace를 변경했습니다")
    if learner_build.read_bytes() != b"learner object":
        raise AssertionError("artifact cleanup이 learner workspace build를 삭제했습니다")
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


def create_workspace_fixture(root: Path) -> Path:
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(NEW_WORKSPACE, scripts / "new_workspace.py")
    shutil.copy2(ARTIFACT_MANAGER, scripts / "manage_artifacts.py")

    modern = root / "exercises/01-modern-cpp/skeleton"
    cpp98 = root / "exercises/02-cpp98-systems/skeleton"
    modern.mkdir(parents=True)
    cpp98.mkdir(parents=True)
    (modern / "main.cpp").write_text("int modern;\n", encoding="utf-8")
    (cpp98 / "main.cpp").write_text("int cpp98;\n", encoding="utf-8")
    return scripts / "new_workspace.py"


def run_workspace_creator(script: Path, track: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), track],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


def test_workspace_creator(temp: Path) -> None:
    repository = temp / "basic"
    script = create_workspace_fixture(repository)

    created = run_workspace_creator(script, "modern")
    if created.returncode != 0:
        raise AssertionError(created.stdout + created.stderr)
    destination = repository / ".workspace/01-modern-cpp"
    if (destination / "skeleton/main.cpp").read_text(encoding="utf-8") != "int modern;\n":
        raise AssertionError("workspace 기본 생성이 canonical source를 복사하지 못했습니다")

    learner = destination / "learner-note.txt"
    learner.write_text("preserve\n", encoding="utf-8")
    repeated = run_workspace_creator(script, "modern")
    if repeated.returncode != 2 or learner.read_text(encoding="utf-8") != "preserve\n":
        raise AssertionError("workspace creator가 기존 destination을 보존하며 exit 2하지 않았습니다")

    symlink_target = repository / "outside.cpp"
    symlink_target.write_text("outside\n", encoding="utf-8")
    source_link = repository / "exercises/02-cpp98-systems/skeleton/link.cpp"
    source_link.symlink_to(symlink_target)
    rejected = run_workspace_creator(script, "cpp98")
    if rejected.returncode != 2 or (repository / ".workspace/02-cpp98-systems").exists():
        raise AssertionError("workspace creator가 canonical source symlink를 거부하지 않았습니다")

    concurrent_repository = temp / "concurrent"
    concurrent_script = create_workspace_fixture(concurrent_repository)
    processes = [
        subprocess.Popen(
            [sys.executable, str(concurrent_script), "modern"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for _ in range(2)
    ]
    results = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=30)
        results.append((process.returncode, stdout, stderr))
    if sorted(result[0] for result in results) != [0, 2]:
        raise AssertionError(f"동시 workspace 생성 결과가 0/2가 아닙니다: {results}")
    concurrent_destination = concurrent_repository / ".workspace/01-modern-cpp"
    if not (concurrent_destination / "skeleton/main.cpp").is_file():
        raise AssertionError("동시 workspace 생성 뒤 완전한 destination이 없습니다")


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


def implementation_token(label: str) -> str:
    # Construct tokens so this verifier source is not itself an annotation.
    return "[" + "Implementation " + label + "]"


def write_annotation_fixture(
    root: Path,
    source_labels: list[str],
    index_labels: list[str] | None = None,
) -> tuple[validate_annotations.ScopeSpec, Path, Path]:
    source = root / "exercise/reference/main.cpp"
    readme = root / "exercise/README.md"
    source.parent.mkdir(parents=True)
    readme.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "".join(f"// {implementation_token(label)} contract\n" for label in source_labels),
        encoding="utf-8",
    )
    rows = source_labels if index_labels is None else index_labels
    readme.write_text(
        "# Exercise\n\n"
        "<!-- implementation-scope: synthetic -->\n"
        "권장 구현 순서입니다.\n\n"
        "| 번호 | anchor | 책임 |\n"
        "|---|---|---|\n"
        + "".join(
            f"| `{label}` | `reference/main.cpp` | contract |\n" for label in rows
        )
        + "<!-- /implementation-scope -->\n",
        encoding="utf-8",
    )
    scope = validate_annotations.ScopeSpec(
        "synthetic",
        "exercise/README.md",
        ("exercise/reference/main.cpp",),
        (),
    )
    return scope, source, readme


def assert_validation_error(errors: list[str], expected: str) -> None:
    if not any(expected in error for error in errors):
        raise AssertionError(f"검증기가 {expected!r} 결함을 거부하지 못했습니다: {errors}")


def test_annotation_validator(temp: Path) -> None:
    valid = temp / "valid"
    scope, _, _ = write_annotation_fixture(valid, ["1", "2", "2-1", "2-2", "3"])
    errors = validate_annotations.validate_annotation_contracts(valid, (scope,))
    if errors:
        raise AssertionError(f"유효한 annotation fixture가 거부되었습니다: {errors}")

    duplicate = temp / "duplicate"
    scope, _, _ = write_annotation_fixture(duplicate, ["1", "1"], ["1"])
    assert_validation_error(
        validate_annotations.validate_annotation_contracts(duplicate, (scope,)),
        "marker 중복",
    )

    gap = temp / "gap"
    scope, _, _ = write_annotation_fixture(gap, ["1", "3"])
    assert_validation_error(
        validate_annotations.validate_annotation_contracts(gap, (scope,)),
        "1부터 연속적이지 않음",
    )

    parentless = temp / "parentless"
    scope, _, _ = write_annotation_fixture(parentless, ["1", "2-1"])
    assert_validation_error(
        validate_annotations.validate_annotation_contracts(parentless, (scope,)),
        "parent marker 없는 substep",
    )

    forbidden = temp / "forbidden"
    scope, _, _ = write_annotation_fixture(forbidden, ["1"])
    skeleton = forbidden / "exercise/skeleton/main.cpp"
    skeleton.parent.mkdir(parents=True)
    skeleton.write_text(f"// {implementation_token('2')} forbidden\n", encoding="utf-8")
    assert_validation_error(
        validate_annotations.validate_annotation_contracts(forbidden, (scope,)),
        "금지 경계",
    )

    mismatch = temp / "mismatch"
    scope, _, _ = write_annotation_fixture(mismatch, ["1", "2"], ["1", "3"])
    assert_validation_error(
        validate_annotations.validate_annotation_contracts(mismatch, (scope,)),
        "source/README implementation index 불일치",
    )

    malformed = temp / "malformed"
    scope, source, _ = write_annotation_fixture(malformed, ["1"])
    source.write_text(
        source.read_text(encoding="utf-8") + "// " + implementation_token("01") + " malformed\n",
        encoding="utf-8",
    )
    assert_validation_error(
        validate_annotations.validate_annotation_contracts(malformed, (scope,)),
        "malformed implementation marker",
    )


def learning_map_block(map_id: str) -> str:
    rows = "".join(
        f"| {number} <!-- learning-row: {map_id}-{number:02d} --> "
        "| doc | example | exercise | path | verify | next |\n"
        for number in range(1, 10)
    )
    return (
        f"<!-- learning-map: {map_id} -->\n"
        "| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |\n"
        "|---|---|---|---|---|---|---|\n"
        f"{rows}"
        "<!-- /learning-map -->\n"
    )


def test_learning_map_and_shell_cd_validators(temp: Path) -> None:
    repository = temp / "repository"
    existing = repository / "exercises/example"
    existing.mkdir(parents=True)
    readme = repository / "README.md"
    readme.write_text(
        "# Guide\n\n"
        + learning_map_block("modern")
        + "\n"
        + learning_map_block("cpp98")
        + (
            "\n```sh\n"
            "cd exercises/example\n"
            "command --flag \\\n"
            "  value\n"
            "command --another-flag \\\n"
            "  cd missing/path\n"
            "```\n"
        ),
        encoding="utf-8",
    )
    learning_errors = validate_annotations.validate_learning_maps(repository)
    shell_errors = validate_annotations.validate_fenced_shell_cd(repository)
    if learning_errors or shell_errors:
        raise AssertionError(
            f"유효한 learning map/shell fixture가 거부되었습니다: "
            f"{learning_errors + shell_errors}"
        )

    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "| 9 <!-- learning-row: modern-09 --> | doc | example | exercise | path | verify | next |\n",
            "",
        ),
        encoding="utf-8",
    )
    assert_validation_error(
        validate_annotations.validate_learning_maps(repository),
        "row coverage 불일치",
    )

    bad_cd = repository / "docs/bad.md"
    bad_cd.parent.mkdir(parents=True)
    bad_cd.write_text("# Bad\n\n```sh\ncd missing/path\n```\n", encoding="utf-8")
    assert_validation_error(
        validate_annotations.validate_fenced_shell_cd(repository),
        "cd target이 없음",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-cpp-verifier-selftest-") as directory:
        temp = Path(directory)
        test_skeleton_verifier(temp / "skeleton")
        test_artifact_manager(temp / "artifacts")
        test_workspace_creator(temp / "workspace")
        test_timeout_runner(temp / "runner")
        test_network_harnesses()
        test_annotation_validator(temp / "annotations")
        test_learning_map_and_shell_cd_validators(temp / "documentation")
    print("검증기 메타 검사: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
