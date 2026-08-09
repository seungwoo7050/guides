#!/usr/bin/env python3
"""Exercise verify-log rejection before marker/tests can mutate repository data."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from repository_state import fingerprint, index_fingerprint

ROOT = Path(__file__).resolve().parents[1]


def invoke(repository: Path, log: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["VERIFY_LOG"] = log
    return subprocess.run(
        ["bash", "verify.sh"],
        cwd=repository,
        env=environment,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )


def require_rejection(name: str, result: subprocess.CompletedProcess[str]) -> None:
    output = result.stdout + result.stderr
    if result.returncode == 0 or "RESULT: PASS" in output or "RESULT: FAIL" not in output:
        raise AssertionError(f"verify preflight accepted {name}: status={result.returncode}\n{output}")


def copy_source(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git",
            ".guide",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".venv",
            "__pycache__",
            "workspace",
            "*.pyc",
            "*.pyo",
        ),
    )
    validator = destination / "scripts/validate.py"
    validator.write_text(
        "#!/usr/bin/env python3\nprint('fixture validator: PASS')\n",
        encoding="utf-8",
    )
    validator.chmod(0o755)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-data-verify-log-") as temporary:
        fixture = Path(temporary)
        repository = fixture / "repository"
        repository.mkdir()
        shutil.copy2(ROOT / "verify.sh", repository / "verify.sh")
        protected = repository / "README.md"
        protected.write_bytes(b"protected repository bytes\n")
        protected_before = protected.read_bytes()

        require_rejection("relative log", invoke(repository, "relative.log"))
        if (repository / "relative.log").exists():
            raise AssertionError("relative VERIFY_LOG was created")
        require_rejection("repository log", invoke(repository, str(protected)))
        require_rejection("nested repository log", invoke(repository, str(repository / "new/verify.log")))
        if (repository / "new").exists() or protected.read_bytes() != protected_before:
            raise AssertionError("repository VERIFY_LOG preflight mutated source")

        existing = fixture / "existing.log"
        existing.write_bytes(b"external sentinel\n")
        existing_before = existing.read_bytes()
        require_rejection("existing external file", invoke(repository, str(existing)))
        if existing.read_bytes() != existing_before:
            raise AssertionError("existing external log was truncated")

        target = fixture / "symlink-target"
        target.write_bytes(b"symlink sentinel\n")
        link = fixture / "verify-link.log"
        link.symlink_to(target)
        require_rejection("leaf symlink", invoke(repository, str(link)))
        if target.read_bytes() != b"symlink sentinel\n":
            raise AssertionError("VERIFY_LOG followed a leaf symlink")
        dangling = fixture / "dangling.log"
        dangling.symlink_to(fixture / "missing-target")
        require_rejection("dangling symlink", invoke(repository, str(dangling)))

        fifo = fixture / "verify.fifo"
        os.mkfifo(fifo)
        require_rejection("FIFO", invoke(repository, str(fifo)))
        missing_parent = fixture / "missing/verify.log"
        require_rejection("missing parent", invoke(repository, str(missing_parent)))
        if missing_parent.parent.exists():
            raise AssertionError("VERIFY_LOG preflight created a parent directory")

        valid = fixture / "first.log"
        first = invoke(repository, str(valid))
        require_rejection("missing Git/marker after safe log creation", first)
        if not valid.is_file():
            raise AssertionError("safe external log was not created")
        first_bytes = valid.read_bytes()
        second = invoke(repository, str(valid))
        require_rejection("second existing log", second)
        if valid.read_bytes() != first_bytes:
            raise AssertionError("second verify invocation overwrote the first log")

    with tempfile.TemporaryDirectory(prefix="guide-data-verify-failure-") as temporary:
        fixture = Path(temporary)
        repository = fixture / "repository"
        copy_source(repository)
        subprocess.run(["git", "init", "-q", "-b", "data-engineering", str(repository)], check=True)
        subprocess.run(["git", "-C", str(repository), "config", "user.name", "Guide Safety Test"], check=True)
        subprocess.run(
            ["git", "-C", str(repository), "config", "user.email", "guide-safety@example.invalid"],
            check=True,
        )
        subprocess.run(["git", "-C", str(repository), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(repository), "commit", "-q", "-m", "fixture"], check=True)
        learner = repository / "exercises/01-contracts-and-records/01-schema-evolution/workspace"
        learner.mkdir()
        (learner / "answer.py").write_text("learner sentinel\n", encoding="utf-8")
        (learner / "answer.py").chmod(0o640)
        prepared = subprocess.run(
            ["bash", "prepare.sh"],
            cwd=repository,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            timeout=45,
            check=False,
        )
        if prepared.returncode != 0:
            raise AssertionError(prepared.stdout + prepared.stderr)
        source_before = fingerprint(repository, "source")
        workspace_before = fingerprint(repository, "workspace")
        index_before = index_fingerprint(repository)
        temp_root = fixture / "temporary"
        temp_root.mkdir()
        log = fixture / "induced-failure.log"
        environment = os.environ.copy()
        environment.update(
            {
                "GUIDE_VERIFY_TEST_FAIL_AFTER_COPY": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "TMPDIR": str(temp_root),
                "VERIFY_LOG": str(log),
            }
        )
        failed = subprocess.run(
            ["bash", "verify.sh"],
            cwd=repository,
            env=environment,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        output = failed.stdout + failed.stderr + (log.read_text(encoding="utf-8") if log.is_file() else "")
        if failed.returncode == 0 or "RESULT: FAIL" not in output or "RESULT: PASS" in output:
            raise AssertionError(f"induced verify failure was misreported\n{output}")
        if fingerprint(repository, "source") != source_before:
            raise AssertionError("failed verify changed source")
        if fingerprint(repository, "workspace") != workspace_before:
            raise AssertionError("failed verify changed learner workspace")
        if index_fingerprint(repository) != index_before:
            raise AssertionError("failed verify changed Git index")
        if list(temp_root.glob("guide-data-engineering-work.*")):
            raise AssertionError("failed verify left isolated work directories")

    print(
        "VERIFY PREFLIGHT: PASS "
        "(relative/in-repo/existing/symlink/FIFO/missing-parent/no-overwrite/failure preservation)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
