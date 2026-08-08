"""단계 검사에서 skeleton, workspace와 reference를 같은 계약으로 실행합니다."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

EXERCISE_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = EXERCISE_ROOT / "fixtures"
OVERRIDE_ROOT = os.environ.get("EXERCISE_IMPL_ROOT")
if OVERRIDE_ROOT:
    IMPLEMENTATION = "override"
    IMPLEMENTATION_ROOT = Path(OVERRIDE_ROOT).resolve()
else:
    IMPLEMENTATION = os.environ.get("EXERCISE_IMPL", "reference")
    if IMPLEMENTATION not in {"reference", "skeleton", "workspace"}:
        raise RuntimeError(f"지원하지 않는 EXERCISE_IMPL: {IMPLEMENTATION}")
    IMPLEMENTATION_ROOT = EXERCISE_ROOT / IMPLEMENTATION
if not IMPLEMENTATION_ROOT.is_dir():
    raise RuntimeError(
        f"구현 디렉터리가 없습니다: {IMPLEMENTATION_ROOT}. "
        "workspace는 scripts/new-workspace.sh로 만드십시오."
    )

sys.path.insert(0, str(IMPLEMENTATION_ROOT))


def module(name: str):
    return importlib.import_module(f"command_checker.{name}")


def run_python(code: str, *, timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        str(IMPLEMENTATION_ROOT)
        if not existing
        else str(IMPLEMENTATION_ROOT) + os.pathsep + existing
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
        env=environment,
    )


def run_cli(
    arguments: list[str],
    *,
    input_text: str = "",
    cwd: Path | None = None,
    environment: dict[str, str] | None = None,
    timeout: float = 8.0,
) -> subprocess.CompletedProcess[str]:
    child_environment = os.environ.copy()
    existing = child_environment.get("PYTHONPATH")
    child_environment["PYTHONPATH"] = (
        str(IMPLEMENTATION_ROOT)
        if not existing
        else str(IMPLEMENTATION_ROOT) + os.pathsep + existing
    )
    if environment:
        child_environment.update(environment)
    return subprocess.run(
        [sys.executable, "-m", "command_checker", *arguments],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
        cwd=cwd,
        env=child_environment,
    )


def write_cases(directory: Path, payload: Any, name: str = "cases.json") -> Path:
    path = directory / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
