#!/usr/bin/env python3
"""VERIFY_LOG가 상대·저장소·symlink 경로를 안전하게 거부함을 증명합니다."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def prove_optional_lock_safety() -> None:
    verify_text = (ROOT / "verify.sh").read_text(encoding="utf-8")
    if "GIT_OPTIONAL_LOCKS=0" not in verify_text:
        raise AssertionError("verify가 Git optional index refresh를 비활성화하지 않았습니다")
    with tempfile.TemporaryDirectory(prefix="guide-algorithms-index-") as temporary:
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
        shadow = repository.parent / "index-shadow"
        shutil.copy2(index, shadow)
        environment = os.environ.copy()
        environment["GIT_OPTIONAL_LOCKS"] = "0"
        environment["GIT_INDEX_FILE"] = str(shadow)
        subprocess.run(["git", "diff", "--check"], cwd=repository, env=environment, check=True)
        subprocess.run(["git", "diff", "--cached", "--check"], cwd=repository, env=environment, check=True)
        if index.read_bytes() != before:
            raise AssertionError("shadow-index Git hygiene 검사가 raw index를 변경했습니다")


def invoke(repository: Path, log_path: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["VERIFY_LOG"] = log_path
    return subprocess.run(
        ["bash", "verify.sh"],
        cwd=repository,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )


def reject(label: str, result: subprocess.CompletedProcess[str]) -> None:
    output = result.stdout + result.stderr
    required = ("passed=0 failed=1 skipped=0", "VERIFY LOG:", "RESULT: FAIL")
    if result.returncode != 2 or any(item not in output for item in required):
        raise AssertionError(f"{label} VERIFY_LOG를 정확히 거부하지 못했습니다.\n{output}")


def main() -> int:
    prove_optional_lock_safety()
    with tempfile.TemporaryDirectory(prefix="guide-algorithms-log-") as temporary:
        fixture = Path(temporary)
        repository = fixture / "repo"
        repository.mkdir()
        shutil.copy2(ROOT / "verify.sh", repository / "verify.sh")
        protected_in_repo = repository / "README.md"
        protected_in_repo.write_bytes(b"repository bytes\n")
        reject("relative", invoke(repository, "relative.log"))
        reject("repository", invoke(repository, str(protected_in_repo)))

        protected_external = fixture / "protected.log"
        protected_external.write_bytes(b"external bytes\n")
        protected_external.chmod(0o640)
        before = (protected_external.read_bytes(), stat.S_IMODE(protected_external.stat().st_mode))
        symlink = fixture / "verify-link.log"
        symlink.symlink_to(protected_external)
        reject("leaf symlink", invoke(repository, str(symlink)))
        after = (protected_external.read_bytes(), stat.S_IMODE(protected_external.stat().st_mode))
        if after != before:
            raise AssertionError("VERIFY_LOG symlink preflight가 외부 파일 bytes 또는 mode를 변경했습니다")
    print("[PASS] VERIFY_LOG safety and mtime-only raw-index stability")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
