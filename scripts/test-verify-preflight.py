#!/usr/bin/env python3
"""Prove every VERIFY_LOG/preflight failure has one exact safe summary."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def invoke(
    repository: Path,
    log_path: str,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["VERIFY_LOG"] = log_path
    return subprocess.run(
        ["bash", "verify.sh", *arguments],
        cwd=repository,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )


def reject(label: str, result: subprocess.CompletedProcess[str], expected: str) -> None:
    output = result.stdout + result.stderr
    summaries = re.findall(r"^passed=\d+ failed=1 skipped=\d+$", output, flags=re.MULTILINE)
    if (
        result.returncode != 2
        or expected not in output
        or len(summaries) != 1
        or output.count("VERIFY LOG:") != 1
        or output.count("RESULT: FAIL") != 1
        or output.count("[verify] ERROR:") != 1
    ):
        raise AssertionError(
            f"{label} preflight를 exact-once 계약으로 거부하지 못했습니다.\n"
            f"returncode={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def bytes_mode(path: Path) -> tuple[bytes, int]:
    return path.read_bytes(), stat.S_IMODE(path.stat().st_mode)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-os-preflight-") as temporary:
        fixture = Path(temporary).resolve()
        repository = fixture / "repo"
        repository.mkdir()
        shutil.copy2(ROOT / "verify.sh", repository / "verify.sh")

        reject("relative log", invoke(repository, "relative.log"), "절대 경로")
        if (repository / "relative.log").exists():
            raise AssertionError("상대 log 파일이 생성됐습니다")

        protected_in_repo = repository / "protected.log"
        protected_in_repo.write_bytes(b"repository protected bytes\n")
        protected_in_repo.chmod(0o640)
        before_repo = bytes_mode(protected_in_repo)
        reject("repository log", invoke(repository, str(protected_in_repo)), "저장소 밖")
        if bytes_mode(protected_in_repo) != before_repo:
            raise AssertionError("repository 내부 log target의 bytes/mode가 바뀌었습니다")

        protected_external = fixture / "external-protected.log"
        protected_external.write_bytes(b"external protected bytes\n")
        protected_external.chmod(0o640)
        before_external = bytes_mode(protected_external)
        leaf_symlink = fixture / "verify-link.log"
        leaf_symlink.symlink_to(protected_external)
        reject("leaf symlink", invoke(repository, str(leaf_symlink)), "leaf symlink")
        if bytes_mode(protected_external) != before_external or not leaf_symlink.is_symlink():
            raise AssertionError("leaf symlink preflight가 외부 target bytes/mode 또는 link를 변경했습니다")

        directory_leaf = fixture / "directory-log"
        directory_leaf.mkdir()
        reject("directory leaf", invoke(repository, str(directory_leaf)), "디렉터리")
        if not directory_leaf.is_dir():
            raise AssertionError("directory log leaf가 변경됐습니다")

        reject("extra argument", invoke(repository, str(fixture / "extra.log"), "unexpected"), "사용법")
        reject("missing state tool", invoke(repository, str(fixture / "missing-tool.log")), "repository state")

        scripts = repository / "scripts"
        scripts.mkdir()
        state_tool = scripts / "repository_state.py"
        state_tool.write_text(
            "#!/bin/sh\n"
            "if [ \"${1:-}\" = index ]; then printf '%s\\n' fixture-index; exit 0; fi\n"
            "exit 2\n",
            encoding="utf-8",
        )
        state_tool.chmod(0o755)
        runner = scripts / "run_with_timeout.py"
        runner.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
        runner.chmod(0o755)
        reject("missing marker", invoke(repository, str(fixture / "missing-marker.log")), "prepare.sh")

    print("[PASS] verify preflight: relative/repository/symlink/directory/args/tool/marker exact-once 7개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
