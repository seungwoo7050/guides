#!/usr/bin/env python3
"""Prove missing, corrupt, source-stale, and tool-stale markers are rejected."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
MARKER = Path(".guide/algorithms/prepared.json")


def run(command: list[str], cwd: Path, *, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )


def invoke(repository: Path, log: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["VERIFY_LOG"] = str(log)
    return run(["bash", "verify.sh"], repository, environment=environment)


def reject(label: str, result: subprocess.CompletedProcess[str], reason: str) -> None:
    output = result.stdout + result.stderr
    required = (reason, "passed=0 failed=1 skipped=0", "VERIFY LOG:", "RESULT: FAIL")
    if result.returncode != 2 or any(item not in output for item in required) or "RESULT: PASS" in output:
        raise AssertionError(f"{label} marker를 정확히 거부하지 못했습니다.\n{output}")


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
            'link=".guide/algorithms/prepared.json.tmp.$$"; '
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
    if not any(path.is_symlink() for path in (predictable / ".guide/algorithms").glob("prepared.json.tmp.*")):
        raise AssertionError("예측 가능 구경로 symlink fixture가 보존되지 않았습니다")

    untrusted_mktemp = fixture / "untrusted-mktemp"
    shutil.copytree(prepared, untrusted_mktemp, symlinks=True)
    mktemp_sentinel = fixture / "mktemp-sentinel"
    mktemp_sentinel.write_bytes(b"mktemp sentinel\n")
    mktemp_sentinel.chmod(0o640)
    mktemp_before = bytes_mode(mktemp_sentinel)
    final_before = bytes_mode(untrusted_mktemp / MARKER)
    candidate = untrusted_mktemp / ".guide/algorithms/.prepared.untrusted"
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
        run(["bash", "prepare.sh"], untrusted_mktemp, environment=environment),
    )
    if bytes_mode(mktemp_sentinel) != mktemp_before or not candidate.is_symlink():
        raise AssertionError("검증 전 mktemp 반환 symlink가 sentinel을 변경했거나 정리되었습니다")
    if bytes_mode(untrusted_mktemp / MARKER) != final_before:
        raise AssertionError("검증 전 mktemp 실패가 기존 final marker를 변경했습니다")

    state_root_escape = fixture / "state-root-escape"
    shutil.copytree(prepared, state_root_escape, symlinks=True)
    shutil.rmtree(state_root_escape / ".guide")
    root_external = fixture / "root-external"
    external_marker = root_external / "algorithms/prepared.json"
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
    shutil.rmtree(guide_escape / ".guide/algorithms")
    guide_external = fixture / "guide-external"
    guide_external.mkdir()
    guide_marker = guide_external / "prepared.json"
    guide_marker.write_bytes(b"guide escape final marker\n")
    guide_marker.chmod(0o640)
    guide_before = bytes_mode(guide_marker)
    (guide_escape / ".guide/algorithms").symlink_to(guide_external, target_is_directory=True)
    require_prepare_failure("guide-id symlink escape", run(["bash", "prepare.sh"], guide_escape))
    if bytes_mode(guide_marker) != guide_before or not (guide_escape / ".guide/algorithms").is_symlink():
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
        "case ${GUIDE_MARKER:-} in */.prepared.*) : >\"$GUIDE_TEST_READY\"; sleep 30 ;; esac\n"
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
    if list((interrupted / ".guide/algorithms").glob(".prepared.*")):
        raise AssertionError("중단된 prepare가 owned marker temp를 남겼습니다")
    if bytes_mode(interrupted / MARKER) != final_before:
        raise AssertionError("중단된 prepare가 기존 final marker를 변경했습니다")

    print("[PASS] marker publication: candidate ownership/random-temp/root+id nofollow/leaf replace/interrupt cleanup 6/6")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-algorithms-marker-") as temporary:
        fixture = Path(temporary)
        prepared = fixture / "prepared"
        shutil.copytree(
            ROOT,
            prepared,
            symlinks=True,
            ignore=shutil.ignore_patterns(".git", ".guide", "workspace", "__pycache__", "*.pyc"),
        )
        run(["git", "init", "-q", "-b", "main"], prepared)
        for relative in (prepared / "scripts/layout-manifest.txt").read_text(encoding="utf-8").splitlines():
            staged = run(["git", "add", "--", relative], prepared)
            if staged.returncode:
                raise AssertionError(staged.stderr)
        committed = run(
            ["git", "-c", "user.name=Guide Tests", "-c", "user.email=guide@example.invalid", "commit", "-qm", "fixture"],
            prepared,
        )
        if committed.returncode:
            raise AssertionError(committed.stderr)
        result = run(["bash", "prepare.sh"], prepared)
        if result.returncode or "PREPARE RESULT: PASS" not in result.stdout:
            raise AssertionError(result.stdout + result.stderr)

        publication_safety(prepared, fixture)

        missing = fixture / "missing"
        shutil.copytree(prepared, missing, symlinks=True)
        (missing / MARKER).unlink()
        reject("missing", invoke(missing, fixture / "missing.log"), "먼저 ./prepare.sh")

        corrupt = fixture / "corrupt"
        shutil.copytree(prepared, corrupt, symlinks=True)
        (corrupt / MARKER).write_text("{broken\n", encoding="utf-8")
        reject("corrupt", invoke(corrupt, fixture / "corrupt.log"), "marker field 오류")

        stale = fixture / "stale"
        shutil.copytree(prepared, stale, symlinks=True)
        with (stale / "README.md").open("a", encoding="utf-8") as stream:
            stream.write("\nstale source mutant\n")
        reject("stale source", invoke(stale, fixture / "stale.log"), "source가 prepare 이후")

        stale_role = fixture / "stale-role"
        shutil.copytree(prepared, stale_role, symlinks=True)
        hidden_before = stale_role / "docs/workspace/unexpected.md"
        hidden_before.parent.mkdir()
        hidden_before.write_text("# workspace 이름을 쓴 source mutant\n", encoding="utf-8")
        reject(
            "role-aware workspace source",
            invoke(stale_role, fixture / "stale-role.log"),
            "source가 prepare 이후",
        )

        stale_tool = fixture / "stale-tool"
        shutil.copytree(prepared, stale_tool, symlinks=True)
        marker = stale_tool / MARKER
        payload = json.loads(marker.read_text(encoding="utf-8"))
        payload["git_version"] = "git version stale-mutant"
        marker.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        reject("stale tool", invoke(stale_tool, fixture / "stale-tool.log"), "Git 버전")

    print("[PASS] prepare marker negative suite: missing/corrupt/source-stale/role-stale/tool-stale 5/5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
