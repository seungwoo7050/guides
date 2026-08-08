#!/usr/bin/env python3
"""Exercise VERIFY_LOG rejection without touching the source checkout or Docker."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


def require_rejection(name: str, result: subprocess.CompletedProcess[str]) -> None:
    output = result.stdout + result.stderr
    required = ("SUMMARY: pass=0 fail=1 skipped=0", "RESULT: FAIL", "VERIFY LOG:")
    if result.returncode != 2 or "RESULT: PASS" in output or not all(token in output for token in required):
        raise AssertionError(
            f"VERIFY_LOG preflight accepted {name}: status={result.returncode}\n{output}"
        )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-db-verify-log-") as temporary:
        fixture = Path(temporary)
        repository = fixture / "repo"
        repository.mkdir()
        shutil.copy2(ROOT / "verify.sh", repository / "verify.sh")
        protected = repository / "README.md"
        original = b"protected repository bytes\n"
        protected.write_bytes(original)

        require_rejection("relative path", invoke(repository, "relative.log"))
        require_rejection("repository path", invoke(repository, str(protected)))

        nested_log = repository / "new" / "deep" / "verify.log"
        require_rejection("nested repository path", invoke(repository, str(nested_log)))
        if nested_log.parent.exists():
            raise AssertionError("VERIFY_LOG preflight created an in-repository directory")

        symlink = fixture / "outside-name.log"
        symlink.symlink_to(protected)
        require_rejection("external symlink into repository", invoke(repository, str(symlink)))
        if protected.read_bytes() != original:
            raise AssertionError("VERIFY_LOG preflight truncated its in-repository symlink target")

    print("[PASS] VERIFY_LOG rejects relative, repository, and symlink-escape paths before mutation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
