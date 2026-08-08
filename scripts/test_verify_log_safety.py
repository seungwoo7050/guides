#!/usr/bin/env python3
"""VERIFY_LOG 경계가 보호 파일을 열거나 자르기 전에 실패하는지 확인합니다."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def prove_index_fingerprint_safety() -> None:
    with tempfile.TemporaryDirectory(prefix="guide-cn-index-") as temporary:
        repository = Path(temporary) / "repo"
        repository.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
        tracked = repository / "tracked.txt"
        tracked.write_text("stable\n", encoding="utf-8")
        subprocess.run(["git", "add", "--", "tracked.txt"], cwd=repository, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Guide Tests", "-c", "user.email=guide@example.invalid", "commit", "-qm", "fixture"],
            cwd=repository,
            check=True,
        )
        index = Path(subprocess.check_output(["git", "rev-parse", "--git-path", "index"], cwd=repository, text=True).strip())
        if not index.is_absolute():
            index = repository / index
        os.utime(tracked, (1, 1))
        before = index.read_bytes()
        script = repository / "repository_state.py"
        shutil.copy2(ROOT / "scripts/repository_state.py", script)
        subprocess.run(
            [sys.executable, str(script), "index-fingerprint", "--root", str(repository)],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        if index.read_bytes() != before:
            raise AssertionError("index fingerprint 조회가 raw index를 변경했습니다")


def run(log: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["VERIFY_LOG"] = log
    return subprocess.run(
        [str(ROOT / "verify.sh")],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


def rejected(label: str, log: str, expected: str) -> None:
    result = run(log)
    output = result.stdout + result.stderr
    required = ("passed=0 failed=1 skipped=0", "VERIFY LOG:", "RESULT: FAIL")
    if result.returncode != 2 or expected not in output or any(item not in output for item in required):
        raise AssertionError(f"{label} boundary was not rejected before verification:\n{output}")
    print(f"[PASS] VERIFY_LOG rejected: {label}")


def main() -> int:
    verify_text = (ROOT / "verify.sh").read_text(encoding="utf-8")
    if "GIT_OPTIONAL_LOCKS=0" not in verify_text:
        raise AssertionError("verify가 Git optional index refresh를 비활성화하지 않았습니다")
    prove_index_fingerprint_safety()
    relative = "guide-cn-relative-negative.log"
    relative_path = ROOT / relative
    if relative_path.exists() or relative_path.is_symlink():
        raise AssertionError(f"negative-test path already exists: {relative_path}")
    rejected("relative", relative, "절대 경로")
    if relative_path.exists() or relative_path.is_symlink():
        raise AssertionError("relative VERIFY_LOG created a repository file")

    in_repository = ROOT / ".guide-cn-in-repository-negative.log"
    if in_repository.exists() or in_repository.is_symlink():
        raise AssertionError(f"negative-test path already exists: {in_repository}")
    rejected("in-repository", str(in_repository), "저장소 밖")
    if in_repository.exists() or in_repository.is_symlink():
        raise AssertionError("in-repository VERIFY_LOG created a file")

    with tempfile.TemporaryDirectory(prefix="guide-cn-log-symlink-") as temporary:
        protected = Path(temporary) / "protected-external.log"
        protected.write_bytes(b"external protected bytes\n")
        protected.chmod(0o640)
        protected_bytes = protected.read_bytes()
        protected_mode = stat.S_IMODE(protected.stat().st_mode)
        link = Path(temporary) / "verify.log"
        link.symlink_to(protected)
        rejected("external-leaf-symlink", str(link), "symlink")
        if not link.is_symlink():
            raise AssertionError("verify replaced or removed the log symlink")
        if protected.read_bytes() != protected_bytes:
            raise AssertionError("VERIFY_LOG symlink truncated or changed protected bytes")
        if stat.S_IMODE(protected.stat().st_mode) != protected_mode:
            raise AssertionError("VERIFY_LOG symlink changed protected mode")

    print("[PASS] log symlink bytes/mode and mtime-only raw-index safety")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
