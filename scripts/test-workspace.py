#!/usr/bin/env python3
"""workspace 생성기의 보존, 경로와 원자 공개 계약을 검사합니다."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "new-workspace.py"
SPEC = importlib.util.spec_from_file_location("guide_new_workspace", MODULE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import bootstrap guard
    raise RuntimeError("new-workspace module을 불러올 수 없습니다.")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def expect_failure(root: Path, value: str, fragment: str) -> None:
    try:
        MODULE.create_workspace(root, value)
    except MODULE.WorkspaceError as error:
        if fragment not in str(error):
            raise AssertionError(f"예상하지 않은 실패입니다: {error}") from error
    else:
        raise AssertionError(f"거부해야 할 workspace 요청을 허용했습니다: {value}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-web-infra-workspace-test.") as raw:
        root = Path(raw)
        exercise01 = root / "exercises" / "01-request-and-process"
        skeleton = exercise01 / "skeleton"
        skeleton.mkdir(parents=True)
        (skeleton / "server.py").write_text("print('starter')\n", encoding="utf-8")

        exercise07 = root / "exercises" / "07-troubleshooting"
        template = exercise07 / "template"
        template.mkdir(parents=True)
        (template / "evidence.md").write_text("# evidence\n", encoding="utf-8")

        workspace = MODULE.create_workspace(root, "exercises/01-request-and-process")
        assert MODULE.is_safe_workspace(workspace)
        assert (workspace / "server.py").read_text(encoding="utf-8") == "print('starter')\n"
        (workspace / "server.py").write_text("learner change\n", encoding="utf-8")
        expect_failure(root, "exercises/01-request-and-process", "덮어쓰지 않습니다")
        assert (workspace / "server.py").read_text(encoding="utf-8") == "learner change\n"
        assert (skeleton / "server.py").read_text(encoding="utf-8") == "print('starter')\n"

        protected = workspace / "protected.log"
        protected.write_text("learner evidence\n", encoding="utf-8")
        in_progress = exercise01 / ".workspace.tmp.in-progress"
        (in_progress / "secrets").mkdir(parents=True)
        (in_progress / "backups").mkdir()
        temp_log = in_progress / "protected.log"
        temp_secret = in_progress / "secrets" / "runtime.txt"
        temp_backup = in_progress / "backups" / "runtime.sql"
        temp_log.write_text("in-progress log\n", encoding="utf-8")
        temp_secret.write_text("in-progress secret\n", encoding="utf-8")
        temp_backup.write_text("in-progress backup\n", encoding="utf-8")
        makefile = root / "Makefile"
        source_makefile = ROOT / "Makefile"
        shutil.copy2(source_makefile, makefile)
        subprocess.run(["make", "clean"], cwd=root, check=True)
        assert protected.read_text(encoding="utf-8") == "learner evidence\n"
        assert temp_log.read_text(encoding="utf-8") == "in-progress log\n"
        assert temp_secret.read_text(encoding="utf-8") == "in-progress secret\n"
        assert temp_backup.read_text(encoding="utf-8") == "in-progress backup\n"

        evidence_workspace = MODULE.create_workspace(root, "exercises/07-troubleshooting")
        assert (evidence_workspace / "evidence.md").is_file()

        (workspace / "outside-link").symlink_to(root / "outside-target")
        assert not MODULE.is_safe_workspace(workspace)
        (workspace / "outside-link").unlink()

        expect_failure(root, "exercises/../01-request-and-process", "경로 순회")
        expect_failure(root, "exercises/99-unknown", "알 수 없는 exercise")

        outside = root / "outside"
        outside.mkdir()
        symlink_exercise = root / "exercises" / "02-container"
        (symlink_exercise / "skeleton").mkdir(parents=True)
        (symlink_exercise / "skeleton" / "outside-link").symlink_to(
            outside, target_is_directory=True
        )
        expect_failure(root, "exercises/02-container", "symlink")

        destination_symlink_exercise = root / "exercises" / "04-gateway-runtime"
        (destination_symlink_exercise / "skeleton").mkdir(parents=True)
        (destination_symlink_exercise / "workspace").symlink_to(
            outside, target_is_directory=True
        )
        expect_failure(root, "exercises/04-gateway-runtime", "덮어쓰지 않습니다")

        lock_exercise = root / "exercises" / "03-compose"
        (lock_exercise / "skeleton").mkdir(parents=True)
        (lock_exercise / ".workspace.lock").mkdir()
        expect_failure(root, "exercises/03-compose", "stale lock")

    print("workspace 생성기 검사 통과: copy, non-overwrite, clean preservation, path, recursive symlink, lock")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
