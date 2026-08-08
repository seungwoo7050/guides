#!/usr/bin/env python3
"""prepare marker의 누락·손상·stale 상태를 verify가 거부하는지 검사합니다."""

from __future__ import annotations

import os
from pathlib import Path
import json
import shutil
import signal
import stat
import subprocess
import tempfile
import time

SOURCE = Path(__file__).resolve().parents[1]
MARKER = Path(".guide/computer-architecture/prepared.json")


def run(command: list[str], cwd: Path, **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=45,
        check=False,
        **kwargs,
    )


def invoke_verify(repository: Path, log_file: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["VERIFY_LOG"] = str(log_file)
    return run(["bash", "verify.sh"], repository, env=environment)


def require_rejection(name: str, completed: subprocess.CompletedProcess[str], needle: str) -> None:
    output = completed.stdout + completed.stderr
    required = ("passed=0 failed=1 skipped=0", "VERIFY LOG:", "RESULT: FAIL")
    if completed.returncode == 0 or needle not in output or any(item not in output for item in required) or "RESULT: PASS" in output:
        raise AssertionError(f"{name} marker를 거부하지 못했습니다.\n{output}")
    print(f"[PASS] verify rejects {name} marker")


def bytes_mode(path: Path) -> tuple[bytes, int]:
    return path.read_bytes(), stat.S_IMODE(path.stat().st_mode)


def require_prepare_failure(label: str, result: subprocess.CompletedProcess[str]) -> None:
    output = result.stdout + result.stderr
    if result.returncode == 0 or "PREPARE RESULT: FAIL" not in output or "PREPARE RESULT: PASS" in output:
        raise AssertionError(f"{label} prepare가 fail-closed하지 않았습니다.\n{output}")


def publication_safety(prepared: Path, fixture: Path) -> None:
    predictable = fixture / "predictable-temp"
    shutil.copytree(prepared, predictable, symlinks=True)
    sentinel = fixture / "predictable-sentinel"
    sentinel.write_bytes(b"predictable sentinel\n")
    sentinel.chmod(0o640)
    before = bytes_mode(sentinel)
    result = run(
        [
            "bash",
            "-c",
            'link=".guide/computer-architecture/.prepared.json.$$"; '
            'ln -s "$1" "$link"; exec bash prepare.sh',
            "_",
            str(sentinel),
        ],
        predictable,
    )
    if result.returncode or "PREPARE RESULT: PASS" not in result.stdout:
        raise AssertionError("예측 가능 구경로 sentinel fixture prepare 실패\n" + result.stdout + result.stderr)
    if bytes_mode(sentinel) != before:
        raise AssertionError("예측 가능 temp symlink가 sentinel bytes/mode를 변경했습니다")
    if not any(path.is_symlink() for path in (predictable / ".guide/computer-architecture").glob(".prepared.json.*")):
        raise AssertionError("예측 가능 구경로 symlink fixture가 보존되지 않았습니다")

    untrusted_mktemp = fixture / "untrusted-mktemp"
    shutil.copytree(prepared, untrusted_mktemp, symlinks=True)
    mktemp_sentinel = fixture / "mktemp-sentinel"
    mktemp_sentinel.write_bytes(b"mktemp sentinel\n")
    mktemp_sentinel.chmod(0o640)
    mktemp_before = bytes_mode(mktemp_sentinel)
    final_before = bytes_mode(untrusted_mktemp / MARKER)
    candidate = untrusted_mktemp / ".guide/computer-architecture/.prepared.untrusted"
    mktemp = shutil.which("mktemp")
    if mktemp is None:
        raise AssertionError("mktemp 경로를 찾지 못했습니다")
    mktemp_shim = fixture / "mktemp-shim"
    mktemp_shim.mkdir()
    wrapper = mktemp_shim / "mktemp"
    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        "case ${1:-} in */.prepared.XXXXXX) "
        "ln -s \"$GUIDE_MKTEMP_SENTINEL\" \"$GUIDE_MKTEMP_CANDIDATE\"; "
        "printf '%s\\n' \"$GUIDE_MKTEMP_CANDIDATE\"; exit 0 ;; esac\n"
        "exec \"$GUIDE_REAL_MKTEMP\" \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    environment = os.environ.copy()
    environment.update(
        PATH=str(mktemp_shim) + os.pathsep + environment["PATH"],
        GUIDE_REAL_MKTEMP=mktemp,
        GUIDE_MKTEMP_SENTINEL=str(mktemp_sentinel),
        GUIDE_MKTEMP_CANDIDATE=str(candidate),
    )
    require_prepare_failure(
        "untrusted mktemp symlink",
        run(["bash", "prepare.sh"], untrusted_mktemp, env=environment),
    )
    if bytes_mode(mktemp_sentinel) != mktemp_before or not candidate.is_symlink():
        raise AssertionError("검증 전 mktemp 반환 symlink가 sentinel을 변경했거나 정리되었습니다")
    if bytes_mode(untrusted_mktemp / MARKER) != final_before:
        raise AssertionError("검증 전 mktemp 실패가 기존 final marker를 변경했습니다")

    state_root_escape = fixture / "state-root-escape"
    shutil.copytree(prepared, state_root_escape, symlinks=True)
    shutil.rmtree(state_root_escape / ".guide")
    root_external = fixture / "root-external"
    external_marker = root_external / "computer-architecture/prepared.json"
    external_marker.parent.mkdir(parents=True)
    external_marker.write_bytes(b"root escape final marker\n")
    external_marker.chmod(0o640)
    external_before = bytes_mode(external_marker)
    (state_root_escape / ".guide").symlink_to(root_external, target_is_directory=True)
    require_prepare_failure(".guide symlink escape", run(["bash", "prepare.sh"], state_root_escape))
    if bytes_mode(external_marker) != external_before or not (state_root_escape / ".guide").is_symlink():
        raise AssertionError(".guide symlink escape가 외부 final marker를 변경했습니다")

    guide_escape = fixture / "guide-id-escape"
    shutil.copytree(prepared, guide_escape, symlinks=True)
    shutil.rmtree(guide_escape / ".guide/computer-architecture")
    guide_external = fixture / "guide-external"
    guide_external.mkdir()
    guide_marker = guide_external / "prepared.json"
    guide_marker.write_bytes(b"guide escape final marker\n")
    guide_marker.chmod(0o640)
    guide_before = bytes_mode(guide_marker)
    (guide_escape / ".guide/computer-architecture").symlink_to(guide_external, target_is_directory=True)
    require_prepare_failure("guide-id symlink escape", run(["bash", "prepare.sh"], guide_escape))
    if bytes_mode(guide_marker) != guide_before or not (guide_escape / ".guide/computer-architecture").is_symlink():
        raise AssertionError("guide-id symlink escape가 외부 final marker를 변경했습니다")

    leaf = fixture / "leaf-symlink"
    shutil.copytree(prepared, leaf, symlinks=True)
    leaf_sentinel = fixture / "leaf-sentinel"
    leaf_sentinel.write_bytes(b"leaf sentinel\n")
    leaf_sentinel.chmod(0o640)
    leaf_before = bytes_mode(leaf_sentinel)
    leaf_marker = leaf / MARKER
    leaf_marker.unlink()
    leaf_marker.symlink_to(leaf_sentinel)
    leaf_result = run(["bash", "prepare.sh"], leaf)
    if leaf_result.returncode or "PREPARE RESULT: PASS" not in leaf_result.stdout:
        raise AssertionError("leaf symlink 안전 교체 prepare 실패\n" + leaf_result.stdout + leaf_result.stderr)
    if bytes_mode(leaf_sentinel) != leaf_before or leaf_marker.is_symlink():
        raise AssertionError("final marker leaf symlink target을 변경했거나 symlink를 남겼습니다")
    if stat.S_IMODE(leaf_marker.stat().st_mode) != 0o600:
        raise AssertionError("게시된 final marker mode가 0600이 아닙니다")

    interrupted = fixture / "interrupted"
    shutil.copytree(prepared, interrupted, symlinks=True)
    final_before = bytes_mode(interrupted / MARKER)
    shim = fixture / "shim"
    shim.mkdir()
    ready = fixture / "marker-temp-ready"
    python = shutil.which("python3")
    if python is None:
        raise AssertionError("python3 경로를 찾지 못했습니다")
    wrapper = shim / "python3"
    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ ${GUIDE_ID:-} == computer-architecture ]]; then "
        "for argument in \"$@\"; do case $argument in */.prepared.*) "
        ": >\"$GUIDE_TEST_READY\"; sleep 30 ;; esac; done; fi\n"
        "exec \"$GUIDE_REAL_PYTHON\" \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    environment = os.environ.copy()
    environment.update(
        PATH=str(shim) + os.pathsep + environment["PATH"],
        GUIDE_TEST_READY=str(ready),
        GUIDE_REAL_PYTHON=python,
    )
    process = subprocess.Popen(
        ["bash", "prepare.sh"],
        cwd=interrupted,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    deadline = time.monotonic() + 60
    while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    if not ready.exists():
        process.kill()
        stdout, stderr = process.communicate()
        raise AssertionError("marker temp 생성 지점에 도달하지 못했습니다\n" + stdout + stderr)
    os.killpg(process.pid, signal.SIGTERM)
    stdout, stderr = process.communicate(timeout=30)
    if process.returncode == 0 or "PREPARE RESULT: FAIL" not in stdout + stderr:
        raise AssertionError("중단된 prepare가 실패 계약을 지키지 않았습니다\n" + stdout + stderr)
    if list((interrupted / ".guide/computer-architecture").glob(".prepared.*")):
        raise AssertionError("중단된 prepare가 owned marker temp를 남겼습니다")
    if bytes_mode(interrupted / MARKER) != final_before:
        raise AssertionError("중단된 prepare가 기존 final marker를 변경했습니다")

    print("[PASS] marker publication: candidate ownership/random-temp/root+id nofollow/leaf replace/interrupt cleanup 6/6")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-architecture-marker-") as temporary:
        fixture = Path(temporary)
        prepared = fixture / "prepared"
        shutil.copytree(
            SOURCE,
            prepared,
            symlinks=True,
            ignore=shutil.ignore_patterns(
                ".git", ".guide", "workspace", "build", "__pycache__", "*.pyc"
            ),
        )
        if run(["git", "init", "-q", "-b", "main"], prepared).returncode != 0:
            raise AssertionError("marker fixture Git 초기화가 실패했습니다.")
        for relative in (prepared / "scripts/layout-manifest.txt").read_text(encoding="utf-8").splitlines():
            if relative and run(["git", "add", "--", relative], prepared).returncode != 0:
                raise AssertionError(f"marker fixture stage가 실패했습니다: {relative}")
        committed = run(
            [
                "git", "-c", "user.name=Guide Tests", "-c", "user.email=guide-tests@example.invalid",
                "commit", "-q", "-m", "fixture",
            ],
            prepared,
        )
        if committed.returncode != 0:
            raise AssertionError("marker fixture commit이 실패했습니다.\n" + committed.stderr)
        prepared_result = run(["bash", "prepare.sh"], prepared)
        if prepared_result.returncode != 0 or "PREPARE RESULT: PASS" not in prepared_result.stdout:
            raise AssertionError("marker fixture prepare가 실패했습니다.\n" + prepared_result.stdout + prepared_result.stderr)

        publication_safety(prepared, fixture)

        missing = fixture / "missing"
        shutil.copytree(prepared, missing, symlinks=True)
        (missing / MARKER).unlink()
        require_rejection(
            "missing", invoke_verify(missing, fixture / "missing.log"), "먼저 ./prepare.sh"
        )

        corrupt = fixture / "corrupt"
        shutil.copytree(prepared, corrupt, symlinks=True)
        (corrupt / MARKER).write_text("{broken\n", encoding="utf-8")
        require_rejection(
            "corrupt", invoke_verify(corrupt, fixture / "corrupt.log"), "marker가 손상"
        )

        stale = fixture / "stale"
        shutil.copytree(prepared, stale, symlinks=True)
        with (stale / "README.md").open("a", encoding="utf-8") as stream:
            stream.write("\nstale marker mutant\n")
        require_rejection(
            "stale", invoke_verify(stale, fixture / "stale.log"), "source가 prepare 이후"
        )

        stale_tool = fixture / "stale-tool"
        shutil.copytree(prepared, stale_tool, symlinks=True)
        tool_marker = stale_tool / MARKER
        payload = json.loads(tool_marker.read_text(encoding="utf-8"))
        payload["git_version"] = "git version stale-mutant"
        tool_marker.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        require_rejection(
            "stale-tool", invoke_verify(stale_tool, fixture / "stale-tool.log"), "Git 버전"
        )

    print("prepare marker negative suite: PASS (4/4)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
