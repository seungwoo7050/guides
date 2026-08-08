#!/usr/bin/env python3
"""Prove directory fingerprints, raw-index safety and non-destructive clean."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
STATE_TOOL = ROOT / "scripts/repository_state.py"


def run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    values = os.environ.copy()
    if environment:
        values.update(environment)
    return subprocess.run(
        command,
        cwd=cwd,
        env=values,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def require(condition: bool, message: str, result: subprocess.CompletedProcess[str] | None = None) -> None:
    if condition:
        return
    detail = "" if result is None else f"\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    raise AssertionError(message + detail)


def state(command: str, root: Path, output: Path | None = None) -> str:
    arguments = [sys.executable, str(STATE_TOOL), command, "--root", str(root)]
    if output is not None:
        arguments.extend(("--output", str(output)))
    result = run(arguments, cwd=ROOT)
    require(result.returncode == 0, f"repository_state {command} 실패", result)
    return result.stdout.strip()


def check_directory_state(base: Path) -> None:
    tree = base / "state-tree"
    content = tree / "content"
    content.mkdir(parents=True)
    (content / "value.txt").write_text("value\n", encoding="utf-8")
    content.chmod(0o755)
    first = state("fingerprint", tree)
    content.chmod(0o700)
    second = state("fingerprint", tree)
    require(first != second, "directory mode 변경이 source fingerprint에 반영되지 않았습니다")
    content.chmod(0o755)
    (tree / "content-link").symlink_to("content", target_is_directory=True)
    third = state("fingerprint", tree)
    require(first != third, "directory symlink가 source fingerprint에 반영되지 않았습니다")
    manifest = base / "directory-manifest.json"
    state("manifest", tree, manifest)
    records = json.loads(manifest.read_text(encoding="utf-8"))
    by_path = {item["path"]: item for item in records}
    require(by_path["content"] == {"path": "content", "mode": 0o755, "type": "directory"}, "directory mode record 오류")
    require(by_path["content-link"]["type"] == "symlink", "directory symlink record 오류")


def check_raw_index(base: Path) -> None:
    repository = base / "git-index"
    repository.mkdir()
    tracked = repository / "tracked.txt"
    tracked.write_text("unchanged bytes\n", encoding="utf-8")
    for command in (
        ["git", "init", "-q"],
        ["git", "add", "--", "tracked.txt"],
        [
            "git",
            "-c",
            "user.name=Guide Audit",
            "-c",
            "user.email=guide-audit@example.invalid",
            "commit",
            "-q",
            "-m",
            "fixture",
        ],
    ):
        result = run(command, cwd=repository)
        require(result.returncode == 0, f"Git fixture 실패: {command}", result)
    before_index = state("index", repository)
    before_bytes = tracked.read_bytes()
    before_mode = stat.S_IMODE(tracked.stat().st_mode)
    metadata = tracked.stat()
    os.utime(tracked, ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 2_000_000_000))
    require(tracked.stat().st_mtime_ns != metadata.st_mtime_ns, "mtime-only fixture를 만들지 못했습니다")
    environment = {"GIT_OPTIONAL_LOCKS": "0"}
    status = run(["git", "status", "--porcelain=v2"], cwd=repository, environment=environment)
    require(status.returncode == 0, "optional-lock status probe 실패", status)
    require(before_index == state("index", repository), "GIT_OPTIONAL_LOCKS=0 status가 raw index를 변경했습니다")
    read_only_index = base / "read-only.index"
    shutil.copy2(Path(state("index-path", repository)), read_only_index)
    environment["GIT_INDEX_FILE"] = str(read_only_index)
    for command in (
        ["git", "diff", "--check"],
        ["git", "diff", "--cached", "--check"],
        ["git", "rev-parse", "HEAD"],
    ):
        result = run(command, cwd=repository, environment=environment)
        require(result.returncode == 0, f"read-only Git probe 실패: {command}", result)
    after_index = state("index", repository)
    require(before_index == after_index, "mtime-only Git 조회가 raw index bytes/mode를 변경했습니다")
    require(tracked.read_bytes() == before_bytes, "mtime-only probe가 tracked bytes를 변경했습니다")
    require(stat.S_IMODE(tracked.stat().st_mode) == before_mode, "mtime-only probe가 tracked mode를 변경했습니다")
    for script in (ROOT / "prepare.sh", ROOT / "verify.sh"):
        require("GIT_OPTIONAL_LOCKS=0" in script.read_text(encoding="utf-8"), f"{script.name} optional-lock 비활성화 누락")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_records(root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for base in (root / ".guide", root / "exercises/kernel-model/workspace"):
        for directory, names, files in os.walk(base, topdown=True, followlinks=False):
            current = Path(directory)
            metadata = current.lstat()
            records.append(
                {
                    "path": current.relative_to(root).as_posix(),
                    "type": "directory",
                    "mode": stat.S_IMODE(metadata.st_mode),
                }
            )
            traversable: list[str] = []
            for name in sorted(names):
                path = current / name
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode):
                    records.append(
                        {
                            "path": path.relative_to(root).as_posix(),
                            "type": "symlink",
                            "mode": stat.S_IMODE(info.st_mode),
                            "target": os.readlink(path),
                        }
                    )
                else:
                    traversable.append(name)
            names[:] = traversable
            for name in sorted(files):
                path = current / name
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode):
                    records.append(
                        {
                            "path": path.relative_to(root).as_posix(),
                            "type": "symlink",
                            "mode": stat.S_IMODE(info.st_mode),
                            "target": os.readlink(path),
                        }
                    )
                else:
                    records.append(
                        {
                            "path": path.relative_to(root).as_posix(),
                            "type": "file",
                            "mode": stat.S_IMODE(info.st_mode),
                            "size": info.st_size,
                            "sha256": digest(path),
                        }
                    )
    return sorted(records, key=lambda item: str(item["path"]))


def check_clean_preservation(base: Path) -> None:
    repository = base / "clean-repository"
    shutil.copytree(
        ROOT,
        repository,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git",
            ".guide",
            ".pytest_cache",
            ".venv",
            "__pycache__",
            "build",
            "build-sanitize",
            "workspace",
            "*.pyc",
            "*.pyo",
        ),
    )
    guide_state = repository / ".guide/operating-systems/private"
    guide_state.mkdir(parents=True)
    guide_state.parent.chmod(0o700)
    guide_state.chmod(0o700)
    marker = guide_state / "sentinel.json"
    marker.write_bytes(b'{"preserve": true}\n')
    marker.chmod(0o600)

    workspace = repository / "exercises/kernel-model/workspace"
    cache = workspace / "__pycache__"
    cache.mkdir(parents=True)
    learner = workspace / "learner.py"
    learner.write_text("VALUE = 9\n", encoding="utf-8")
    learner.chmod(0o700)
    (cache / "learner.cpython-312.pyc").write_bytes(b"learner cache bytes\x00")
    (workspace / "learner-link").symlink_to("learner.py")
    workspace.chmod(0o750)
    cache.chmod(0o700)

    generated_build = repository / "examples/build"
    generated_build.mkdir()
    (generated_build / "junk").write_text("remove\n", encoding="utf-8")
    generated_cache = repository / "exercises/kernel-model/skeleton/__pycache__"
    generated_cache.mkdir()
    (generated_cache / "junk.pyc").write_bytes(b"remove")

    before = protected_records(repository)
    result = run(["make", "clean"], cwd=repository)
    require(result.returncode == 0, "make clean 실패", result)
    after = protected_records(repository)
    require(before == after, "make clean이 .guide 또는 learner workspace bytes/mode/symlink를 변경했습니다")
    require(not generated_build.exists(), "make clean이 example build를 제거하지 않았습니다")
    require(not generated_cache.exists(), "make clean이 source cache를 제거하지 않았습니다")


def file_snapshot(path: Path) -> tuple[bytes, int]:
    metadata = path.stat()
    require(stat.S_ISREG(metadata.st_mode), f"regular sentinel이 아닙니다: {path}")
    return path.read_bytes(), stat.S_IMODE(metadata.st_mode)


def check_prepare_marker_safety(base: Path) -> None:
    repository = base / "prepare-marker"
    shutil.copytree(
        ROOT,
        repository,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git",
            ".guide",
            ".pytest_cache",
            ".venv",
            "__pycache__",
            "build",
            "build-sanitize",
            "workspace",
            "*.pyc",
            "*.pyo",
        ),
    )
    for command in (
        ["git", "init", "-q", "-b", "main"],
        ["git", "add", "--", *(
            relative
            for relative in (repository / "scripts/layout-manifest.txt").read_text(encoding="utf-8").splitlines()
            if relative
        )],
        [
            "git",
            "-c",
            "user.name=Guide Marker Tests",
            "-c",
            "user.email=guide-marker@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
    ):
        result = run(command, cwd=repository)
        require(result.returncode == 0, f"marker fixture Git 실패: {command[:2]}", result)

    source_before = state("fingerprint", repository)
    index_before = state("index", repository)
    baseline = run(["bash", "prepare.sh"], cwd=repository)
    require(
        baseline.returncode == 0 and "PREPARE RESULT: PASS" in baseline.stdout,
        "marker fixture baseline prepare 실패",
        baseline,
    )
    marker_dir = repository / ".guide/operating-systems"
    marker = marker_dir / "prepared.json"
    require(
        marker.is_file() and not marker.is_symlink() and stat.S_IMODE(marker.stat().st_mode) == 0o600,
        "baseline marker가 0600 regular file이 아닙니다",
    )
    marker_before = file_snapshot(marker)
    require(source_before == state("fingerprint", repository), "baseline prepare가 source를 변경했습니다")
    require(index_before == state("index", repository), "baseline prepare가 raw index를 변경했습니다")

    sentinel = base / "prepare-marker-sentinel"
    sentinel.write_bytes(b"external marker sentinel\n")
    sentinel.chmod(0o640)
    sentinel_before = file_snapshot(sentinel)
    real_mktemp = shutil.which("mktemp")
    require(real_mktemp is not None, "실제 mktemp를 찾지 못했습니다")
    fake_bin = base / "fake-mktemp"
    fake_bin.mkdir()
    fake_mktemp = fake_bin / "mktemp"
    fake_mktemp.write_text(
        "#!/bin/sh\n"
        "case ${1:-} in */.guide/operating-systems/.prepared.XXXXXX) "
        "printf '%s\\n' \"$GUIDE_FAKE_MKTEMP\"; exit 0 ;; esac\n"
        "exec \"$GUIDE_REAL_MKTEMP\" \"$@\"\n",
        encoding="utf-8",
    )
    fake_mktemp.chmod(0o755)
    base_environment = {
        "PATH": str(fake_bin) + os.pathsep + os.environ["PATH"],
        "GUIDE_REAL_MKTEMP": str(real_mktemp),
    }

    candidate = marker_dir / ".prepared.ATTACK"
    candidate.symlink_to(sentinel)
    symlink_result = run(
        ["bash", "prepare.sh"],
        cwd=repository,
        environment={**base_environment, "GUIDE_FAKE_MKTEMP": str(candidate)},
    )
    require(
        symlink_result.returncode != 0 and "PREPARE RESULT: FAIL" in symlink_result.stdout + symlink_result.stderr,
        "symlink를 반환한 mktemp를 fail-closed하지 않았습니다",
        symlink_result,
    )
    require(candidate.is_symlink(), "검증 전 mktemp symlink를 정리했습니다")
    require(file_snapshot(sentinel) == sentinel_before, "mktemp symlink 외부 sentinel을 변경했습니다")
    require(file_snapshot(marker) == marker_before, "mktemp symlink 실패가 final marker를 변경했습니다")
    candidate.unlink()

    outside = base / "outside/.prepared.OUTSID"
    outside.parent.mkdir()
    outside.write_bytes(b"outside regular sentinel\n")
    outside.chmod(0o640)
    outside_before = file_snapshot(outside)
    outside_result = run(
        ["bash", "prepare.sh"],
        cwd=repository,
        environment={**base_environment, "GUIDE_FAKE_MKTEMP": str(outside)},
    )
    require(
        outside_result.returncode != 0 and "PREPARE RESULT: FAIL" in outside_result.stdout + outside_result.stderr,
        "저장소 밖 regular file을 반환한 mktemp를 fail-closed하지 않았습니다",
        outside_result,
    )
    require(file_snapshot(outside) == outside_before, "mktemp outside regular sentinel을 변경했습니다")
    require(file_snapshot(marker) == marker_before, "mktemp outside 실패가 final marker를 변경했습니다")

    python_bin = base / "fake-python"
    python_bin.mkdir()
    real_python = shutil.which("python3")
    require(real_python is not None, "실제 python3를 찾지 못했습니다")
    fake_python = python_bin / "python3"
    fake_python.write_text(
        "#!/bin/sh\n"
        "case ${GUIDE_MARKER:-} in */.prepared.*) "
        ": >\"$GUIDE_MARKER_TEST_READY\"; "
        "while [ ! -e \"$GUIDE_MARKER_TEST_RELEASE\" ]; do sleep 0.02; done ;; esac\n"
        "exec \"$GUIDE_REAL_PYTHON\" \"$@\"\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    def start_held(label: str) -> tuple[subprocess.Popen[str], Path, Path]:
        ready = base / f"{label}.ready"
        release = base / f"{label}.release"
        environment = os.environ.copy()
        environment.update(
            PATH=str(python_bin) + os.pathsep + environment["PATH"],
            GUIDE_MARKER_TEST_READY=str(ready),
            GUIDE_MARKER_TEST_RELEASE=str(release),
            GUIDE_REAL_PYTHON=str(real_python),
        )
        process = subprocess.Popen(
            ["bash", "prepare.sh"],
            cwd=repository,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        deadline = time.monotonic() + 30
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        if not ready.exists():
            process.kill()
            stdout, stderr = process.communicate()
            raise AssertionError("owned marker temp 지점에 도달하지 못했습니다\n" + stdout + stderr)
        return process, ready, release

    process, _, release = start_held("identity")
    owned = list(marker_dir.glob(".prepared.*"))
    require(len(owned) == 1, f"owned marker temp가 정확히 하나가 아닙니다: {owned}")
    owned[0].unlink()
    owned[0].symlink_to(sentinel)
    release.touch()
    stdout, stderr = process.communicate(timeout=30)
    require(
        process.returncode != 0 and "PREPARE RESULT: FAIL" in stdout + stderr,
        "claim 뒤 marker identity 교체를 fail-closed하지 않았습니다",
    )
    require(owned[0].is_symlink(), "identity가 바뀐 temp symlink를 cleanup이 제거했습니다")
    require(file_snapshot(sentinel) == sentinel_before, "identity 교체가 외부 sentinel을 변경했습니다")
    require(file_snapshot(marker) == marker_before, "identity 교체가 final marker를 변경했습니다")
    owned[0].unlink()

    process, _, release = start_held("signal")
    owned = list(marker_dir.glob(".prepared.*"))
    require(len(owned) == 1 and owned[0].is_file() and not owned[0].is_symlink(), "signal fixture owned temp 오류")
    process.send_signal(signal.SIGTERM)
    release.touch()
    stdout, stderr = process.communicate(timeout=30)
    require(
        process.returncode != 0 and "PREPARE RESULT: FAIL" in stdout + stderr,
        "signal marker cleanup이 fail-closed하지 않았습니다",
    )
    require(not list(marker_dir.glob(".prepared.*")), "signal 종료가 owned marker temp를 남겼습니다")
    require(file_snapshot(marker) == marker_before, "signal 종료가 final marker를 변경했습니다")

    require(source_before == state("fingerprint", repository), "marker safety가 source를 변경했습니다")
    require(index_before == state("index", repository), "marker safety가 raw index를 변경했습니다")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-os-common-safety-") as temporary:
        base = Path(temporary).resolve()
        check_directory_state(base)
        check_raw_index(base)
        check_clean_preservation(base)
        check_prepare_marker_safety(base)
    print(
        "[PASS] directory/symlink fingerprint + raw-index + clean + "
        "marker candidate/identity/signal safety"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
