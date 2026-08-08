#!/usr/bin/env python3
"""VERIFY_LOG가 원본을 자를 수 없음을 독립 fixture로 검증합니다."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def invoke(repository: Path, log_path: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["VERIFY_LOG"] = log_path
    return subprocess.run(
        ["bash", "verify.sh"], cwd=repository, env=environment,
        check=False, capture_output=True, text=True, timeout=15,
    )


def require_rejection(name: str, result: subprocess.CompletedProcess[str]) -> None:
    output = result.stdout + result.stderr
    required = ("passed=0 failed=1 skipped=0", "VERIFY LOG:", "RESULT: FAIL")
    if result.returncode != 2 or any(item not in output for item in required) or "RESULT: PASS" in output:
        raise AssertionError(f"VERIFY_LOG가 {name}을 허용했습니다.\n{output}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-architecture-log-") as temporary:
        fixture = Path(temporary)
        repository = fixture / "repo"
        repository.mkdir()
        shutil.copy2(ROOT / "verify.sh", repository / "verify.sh")
        protected = repository / "README.md"
        original = b"protected bytes\n"
        protected.write_bytes(original)
        require_rejection("relative path", invoke(repository, "relative.log"))
        require_rejection("repository path", invoke(repository, str(protected)))
        external = fixture / "external-protected.log"
        external.write_bytes(b"external protected bytes\n")
        external.chmod(0o640)
        before_external = (external.read_bytes(), stat.S_IMODE(external.stat().st_mode))
        symlink = fixture / "outside-name.log"
        symlink.symlink_to(external)
        require_rejection("leaf symlink", invoke(repository, str(symlink)))
        if protected.read_bytes() != original:
            raise AssertionError("검증 로그 preflight가 원본 파일을 변경했습니다.")
        after_external = (external.read_bytes(), stat.S_IMODE(external.stat().st_mode))
        if after_external != before_external:
            raise AssertionError("검증 로그 preflight가 외부 파일 bytes 또는 mode를 변경했습니다.")
    print("[PASS] VERIFY_LOG relative/in-repository/symlink rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
