#!/usr/bin/env python3
"""Prove prepare marker path, ownership, publication, and cleanup safety."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
GUIDE_ID = "computer-networks"
MARKER = Path(".guide") / GUIDE_ID / "prepared.json"


def run(
    repository: Path,
    environment: dict[str, str],
    *,
    timeout: float = 30,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sh", "prepare.sh"],
        cwd=repository,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def require_failure(label: str, result: subprocess.CompletedProcess[str]) -> None:
    output = result.stdout + result.stderr
    if result.returncode == 0 or "PREPARE RESULT: FAIL" not in output or "PREPARE RESULT: PASS" in output:
        raise AssertionError(f"{label} prepare가 fail-closed하지 않았습니다.\n{output}")


def require_verify_path_failure(
    label: str,
    repository: Path,
    environment: dict[str, str],
    log: Path,
) -> None:
    verify_environment = environment.copy()
    verify_environment["VERIFY_LOG"] = str(log)
    result = subprocess.run(
        ["sh", "verify.sh"],
        cwd=repository,
        env=verify_environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    output = result.stdout + result.stderr
    required = ("경로가 안전하지 않습니다", "passed=0 failed=1 skipped=0", "RESULT: FAIL")
    if result.returncode != 2 or any(item not in output for item in required):
        raise AssertionError(f"{label} verify가 marker symlink를 fail-closed하지 않았습니다.\n{output}")


def snapshot(path: Path) -> tuple[bytes, int, int]:
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise AssertionError(f"regular sentinel이 아닙니다: {path}")
    return path.read_bytes(), stat.S_IMODE(metadata.st_mode), metadata.st_size


def raw_index(repository: Path) -> str:
    relative = subprocess.check_output(
        ["git", "rev-parse", "--git-path", "index"],
        cwd=repository,
        text=True,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    ).strip()
    path = Path(relative)
    if not path.is_absolute():
        path = repository / path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprint(repository: Path) -> str:
    return subprocess.check_output(
        ["python3", "scripts/repository_state.py", "fingerprint", "--root", str(repository)],
        cwd=repository,
        text=True,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "PYTHONDONTWRITEBYTECODE": "1"},
    ).strip()


def stable_before(repository: Path) -> tuple[str, str]:
    return source_fingerprint(repository), raw_index(repository)


def assert_stable(repository: Path, before: tuple[str, str], label: str) -> None:
    after = source_fingerprint(repository), raw_index(repository)
    if after != before:
        raise AssertionError(f"{label} 검사가 source 또는 raw index를 변경했습니다")


def make_fake_docker(directory: Path) -> Path:
    wrapper = directory / "docker"
    wrapper.write_text(
        """#!/usr/bin/env python3
import json
import sys

base = "python:3.12-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2"
packages = {
    "ca-certificates": "20230311+deb12u1",
    "grep": "3.8-5",
    "iproute2": "6.1.0-3",
    "iptables": "1.8.9-2",
    "iputils-ping": "3:20221126-1+deb12u1",
    "make": "4.3-4.1",
    "procps": "2:4.0.2-3",
    "tcpdump": "4.99.3-1",
}
lock = ",".join(f"{name}={version}" for name, version in sorted(packages.items()))
labels = {
    "guide.computer-networks.verifier": "1",
    "guide.computer-networks.base-image": base,
    "guide.computer-networks.debian-snapshot": "20260803T000000Z",
    "guide.computer-networks.package-lock": lock,
    "guide.computer-networks.recipe": "3",
}
arguments = sys.argv[1:]
if arguments == ["info"] or arguments[:1] == ["pull"]:
    raise SystemExit(0)
if arguments[:1] == ["version"]:
    print("99.0-marker-test")
    raise SystemExit(0)
if arguments[:3] == ["image", "inspect", "--format"]:
    if arguments[3] == "{{json .Config.Labels}}":
        print(json.dumps(labels, sort_keys=True))
    elif arguments[3] == "{{.Id}}":
        print("sha256:marker-test-image")
    else:
        raise SystemExit(2)
    raise SystemExit(0)
if arguments[:1] == ["run"] and "dpkg-query" in arguments:
    for name, version in sorted(packages.items()):
        print(f"{name}\\t{version}")
    raise SystemExit(0)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    return wrapper


def initialize_fixture(destination: Path, fake_bin: Path) -> tuple[dict[str, str], tuple[str, str]]:
    shutil.copytree(
        ROOT,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git", ".guide", "workspace", "__pycache__", "*.pyc"),
    )
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=destination, check=True)
    for relative in (destination / "scripts/layout-manifest.txt").read_text(encoding="utf-8").splitlines():
        subprocess.run(["git", "add", "--", relative], cwd=destination, check=True)
    subprocess.run(
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
        cwd=destination,
        check=True,
    )
    environment = os.environ.copy()
    environment.update(
        PATH=str(fake_bin) + os.pathsep + environment["PATH"],
        GIT_OPTIONAL_LOCKS="0",
        PYTHONDONTWRITEBYTECODE="1",
    )
    before = stable_before(destination)
    result = run(destination, environment)
    if result.returncode or "PREPARE RESULT: PASS" not in result.stdout:
        raise AssertionError("baseline marker 준비 실패\n" + result.stdout + result.stderr)
    marker = destination / MARKER
    if marker.is_symlink() or not marker.is_file() or stat.S_IMODE(marker.stat().st_mode) != 0o600:
        raise AssertionError("baseline final marker가 안전한 0600 regular file이 아닙니다")
    assert_stable(destination, before, "baseline")
    return environment, before


def copy_prepared(prepared: Path, destination: Path) -> tuple[str, str]:
    shutil.copytree(prepared, destination, symlinks=True)
    return stable_before(destination)


def fake_mktemp_environment(
    fixture: Path,
    base: dict[str, str],
    candidate: Path,
) -> dict[str, str]:
    shim = fixture / ("mktemp-" + hashlib.sha256(str(candidate).encode()).hexdigest()[:8])
    shim.mkdir()
    real = shutil.which("mktemp", path=base["PATH"])
    if real is None:
        raise AssertionError("실제 mktemp를 찾지 못했습니다")
    wrapper = shim / "mktemp"
    wrapper.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$GUIDE_FAKE_MKTEMP\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    environment = base.copy()
    environment.update(PATH=str(shim) + os.pathsep + base["PATH"], GUIDE_FAKE_MKTEMP=str(candidate))
    return environment


def test_fake_mktemp(prepared: Path, fixture: Path, base: dict[str, str]) -> None:
    repository = fixture / "mktemp-symlink"
    before = copy_prepared(prepared, repository)
    sentinel = fixture / "mktemp-symlink-sentinel"
    sentinel.write_bytes(b"mktemp symlink sentinel\n")
    sentinel.chmod(0o640)
    sentinel_before = snapshot(sentinel)
    marker_before = snapshot(repository / MARKER)
    candidate = repository / ".guide/computer-networks/.prepared.ATTACK"
    candidate.symlink_to(sentinel)
    require_failure("fake mktemp symlink", run(repository, fake_mktemp_environment(fixture, base, candidate)))
    if not candidate.is_symlink() or snapshot(sentinel) != sentinel_before:
        raise AssertionError("검증 전 mktemp symlink 또는 외부 sentinel이 변경됐습니다")
    if snapshot(repository / MARKER) != marker_before:
        raise AssertionError("fake mktemp symlink 실패가 final marker를 변경했습니다")
    assert_stable(repository, before, "fake mktemp symlink")

    repository = fixture / "mktemp-outside"
    before = copy_prepared(prepared, repository)
    outside = fixture / "outside/.prepared.OUTSID"
    outside.parent.mkdir()
    outside.write_bytes(b"outside regular sentinel\n")
    outside.chmod(0o640)
    outside_before = snapshot(outside)
    marker_before = snapshot(repository / MARKER)
    require_failure("fake mktemp outside regular", run(repository, fake_mktemp_environment(fixture, base, outside)))
    if snapshot(outside) != outside_before or snapshot(repository / MARKER) != marker_before:
        raise AssertionError("저장소 밖 mktemp regular file 또는 final marker가 변경됐습니다")
    assert_stable(repository, before, "fake mktemp outside regular")


def test_symlink_boundaries(prepared: Path, fixture: Path, base: dict[str, str]) -> None:
    sentinel = fixture / "symlink-boundary-sentinel"
    sentinel.write_bytes(b"symlink boundary sentinel\n")
    sentinel.chmod(0o640)
    sentinel_before = snapshot(sentinel)

    leaf = fixture / "leaf-symlink"
    before = copy_prepared(prepared, leaf)
    marker = leaf / MARKER
    marker.unlink()
    marker.symlink_to(sentinel)
    require_failure("final marker leaf symlink", run(leaf, base))
    require_verify_path_failure("final marker leaf symlink", leaf, base, fixture / "leaf-verify.log")
    if not marker.is_symlink() or snapshot(sentinel) != sentinel_before:
        raise AssertionError("final marker leaf symlink 또는 외부 sentinel이 변경됐습니다")
    assert_stable(leaf, before, "final marker leaf symlink")

    state_root = fixture / "state-root-symlink"
    before = copy_prepared(prepared, state_root)
    shutil.rmtree(state_root / ".guide")
    external_root = fixture / "external-state-root/computer-networks"
    external_root.mkdir(parents=True)
    external_marker = external_root / "prepared.json"
    external_marker.write_bytes(b"state root sentinel\n")
    external_marker.chmod(0o640)
    external_before = snapshot(external_marker)
    (state_root / ".guide").symlink_to(external_root.parent, target_is_directory=True)
    require_failure(".guide ancestor symlink", run(state_root, base))
    require_verify_path_failure(".guide ancestor symlink", state_root, base, fixture / "root-verify.log")
    if not (state_root / ".guide").is_symlink() or snapshot(external_marker) != external_before:
        raise AssertionError(".guide ancestor symlink 또는 외부 marker가 변경됐습니다")
    assert_stable(state_root, before, ".guide ancestor symlink")

    guide_id = fixture / "guide-id-symlink"
    before = copy_prepared(prepared, guide_id)
    shutil.rmtree(guide_id / ".guide/computer-networks")
    external_guide = fixture / "external-guide-id"
    external_guide.mkdir()
    external_marker = external_guide / "prepared.json"
    external_marker.write_bytes(b"guide id sentinel\n")
    external_marker.chmod(0o640)
    external_before = snapshot(external_marker)
    (guide_id / ".guide/computer-networks").symlink_to(external_guide, target_is_directory=True)
    require_failure("guide-id ancestor symlink", run(guide_id, base))
    require_verify_path_failure("guide-id ancestor symlink", guide_id, base, fixture / "guide-verify.log")
    if not (guide_id / ".guide/computer-networks").is_symlink() or snapshot(external_marker) != external_before:
        raise AssertionError("guide-id ancestor symlink 또는 외부 marker가 변경됐습니다")
    assert_stable(guide_id, before, "guide-id ancestor symlink")


def held_environment(
    fixture: Path,
    base: dict[str, str],
    label: str,
) -> tuple[dict[str, str], Path, Path]:
    shim = fixture / f"python-{label}"
    shim.mkdir()
    ready = fixture / f"{label}.ready"
    release = fixture / f"{label}.release"
    real_python = shutil.which("python3", path=base["PATH"])
    if real_python is None:
        raise AssertionError("실제 python3를 찾지 못했습니다")
    wrapper = shim / "python3"
    wrapper.write_text(
        "#!/bin/sh\n"
        "case ${1:-}:${2:-} in */scripts/prepare_marker.py:write) "
        ": >\"$GUIDE_TEST_READY\"; while [ ! -e \"$GUIDE_TEST_RELEASE\" ]; do sleep 0.02; done ;; esac\n"
        "exec \"$GUIDE_REAL_PYTHON\" \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    environment = base.copy()
    environment.update(
        PATH=str(shim) + os.pathsep + base["PATH"],
        GUIDE_TEST_READY=str(ready),
        GUIDE_TEST_RELEASE=str(release),
        GUIDE_REAL_PYTHON=real_python,
    )
    return environment, ready, release


def start_held(repository: Path, environment: dict[str, str], ready: Path) -> subprocess.Popen[str]:
    process = subprocess.Popen(
        ["sh", "prepare.sh"],
        cwd=repository,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    deadline = time.monotonic() + 20
    while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.02)
    if not ready.exists():
        process.kill()
        stdout, stderr = process.communicate()
        raise AssertionError("owned marker temp 지점에 도달하지 못했습니다\n" + stdout + stderr)
    return process


def owned_temp(repository: Path) -> Path:
    paths = list((repository / ".guide/computer-networks").glob(".prepared.*"))
    if len(paths) != 1:
        raise AssertionError(f"owned marker temp가 정확히 하나가 아닙니다: {paths}")
    metadata = paths[0].lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise AssertionError("owned marker temp type/link/mode가 안전하지 않습니다")
    return paths[0]


def test_identity_and_signal(prepared: Path, fixture: Path, base: dict[str, str]) -> None:
    interrupted = fixture / "signal-cleanup"
    before = copy_prepared(prepared, interrupted)
    marker_before = snapshot(interrupted / MARKER)
    environment, ready, _ = held_environment(fixture, base, "signal")
    process = start_held(interrupted, environment, ready)
    owned_temp(interrupted)
    os.killpg(process.pid, signal.SIGTERM)
    stdout, stderr = process.communicate(timeout=20)
    output = stdout + stderr
    if process.returncode == 0 or "PREPARE RESULT: FAIL" not in output:
        raise AssertionError("signal 종료가 fail-closed 계약을 지키지 않았습니다\n" + output)
    if list((interrupted / ".guide/computer-networks").glob(".prepared.*")):
        raise AssertionError("signal 종료가 owned marker temp를 남겼습니다")
    if snapshot(interrupted / MARKER) != marker_before:
        raise AssertionError("signal 종료가 기존 final marker를 변경했습니다")
    assert_stable(interrupted, before, "signal cleanup")

    replaced = fixture / "identity-replacement"
    before = copy_prepared(prepared, replaced)
    marker_before = snapshot(replaced / MARKER)
    sentinel = fixture / "identity-replacement-sentinel"
    sentinel.write_bytes(b"identity replacement sentinel\n")
    sentinel.chmod(0o640)
    sentinel_before = snapshot(sentinel)
    environment, ready, release = held_environment(fixture, base, "identity")
    process = start_held(replaced, environment, ready)
    temporary = owned_temp(replaced)
    temporary.unlink()
    temporary.symlink_to(sentinel)
    release.touch()
    stdout, stderr = process.communicate(timeout=20)
    require_failure(
        "claimed marker identity replacement",
        subprocess.CompletedProcess(["sh", "prepare.sh"], process.returncode, stdout, stderr),
    )
    if not temporary.is_symlink() or snapshot(sentinel) != sentinel_before:
        raise AssertionError("교체된 temp symlink 또는 외부 sentinel이 변경됐습니다")
    if snapshot(replaced / MARKER) != marker_before:
        raise AssertionError("identity 교체 실패가 final marker를 변경했습니다")
    assert_stable(replaced, before, "claimed marker identity replacement")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-cn-marker-") as temporary:
        fixture = Path(temporary)
        fake_bin = fixture / "fake-bin"
        fake_bin.mkdir()
        make_fake_docker(fake_bin)
        prepared = fixture / "prepared"
        base, _ = initialize_fixture(prepared, fake_bin)
        test_fake_mktemp(prepared, fixture, base)
        test_symlink_boundaries(prepared, fixture, base)
        test_identity_and_signal(prepared, fixture, base)
    print(
        "[PASS] prepare marker safety: mktemp symlink/outside, leaf/ancestor symlink, "
        "device+inode replacement, signal cleanup, source/raw-index stable"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
