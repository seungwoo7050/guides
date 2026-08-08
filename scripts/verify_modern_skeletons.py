#!/usr/bin/env python3
"""Verify that each Modern C++ skeleton fails through the shared test suite.

A random non-zero exit is not enough: a crash, loader error, sanitizer abort, or
missing executable must never be accepted as a valid learner starting state.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print("usage: verify_modern_skeletons.py <cmake-build-directory>", file=sys.stderr)
    raise SystemExit(2)

build = Path(sys.argv[1]).resolve()
contracts = [
    (
        "strong-types-and-cmake",
        build / "01-strong-types-and-cmake/strong_types_skeleton_tests",
    ),
    ("unique-file", build / "02-unique-file/unique_file_skeleton_tests"),
    ("query-pipeline", build / "03-query-pipeline/query_pipeline_skeleton_tests"),
    (
        "local-job-runner",
        build / "04-local-job-runner/local_job_runner_skeleton_tests",
    ),
]

fatal_markers = [
    "AddressSanitizer",
    "UndefinedBehaviorSanitizer",
    "ThreadSanitizer",
    "runtime error:",
    "Segmentation fault",
    "Bus error",
    "Illegal instruction",
    "terminate called",
    "Traceback (most recent call last)",
    "error while loading shared libraries",
    "cannot open shared object file",
    "dyld: Library not loaded",
    "Library not loaded:",
]

errors: list[str] = []
environment = os.environ.copy()
environment.setdefault("TERM", "dumb")

for suite_name, executable in contracts:
    candidate = executable.with_suffix(".exe") if os.name == "nt" else executable
    if not candidate.is_file():
        errors.append(f"skeleton test executable을 찾을 수 없습니다: {candidate}")
        continue

    try:
        result = subprocess.run(
            [str(candidate)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
            env=environment,
            check=False,
        )
    except subprocess.TimeoutExpired:
        errors.append(f"skeleton test가 제한 시간 안에 종료되지 않습니다: {candidate}")
        continue
    except OSError as error:
        errors.append(f"skeleton test를 실행할 수 없습니다: {candidate}: {error}")
        continue

    output = result.stdout + result.stderr
    if result.returncode == 0:
        errors.append(f"미완성 skeleton이 예상과 달리 통과했습니다: {candidate}")
        continue
    if result.returncode != 1:
        errors.append(
            f"skeleton이 계약 실패가 아닌 종료 코드로 끝났습니다: "
            f"{candidate} (exit={result.returncode})"
        )
        continue
    if any(marker in output for marker in fatal_markers):
        errors.append(f"skeleton이 test assertion이 아니라 비정상 종료했습니다: {candidate}")
        continue
    if "CHECK failed:" not in output and "CHECK_EQ failed:" not in output:
        errors.append(f"공통 test assertion 실패를 확인할 수 없습니다: {candidate}")
        continue
    summary = re.compile(rf"^{re.escape(suite_name)}: [1-9][0-9]* failure\(s\)$", re.MULTILINE)
    if not summary.search(output):
        errors.append(f"예상한 test suite 실패 요약이 없습니다: {candidate}")
        continue

    print(f"예상된 계약 실패: {candidate.relative_to(build)}")

if errors:
    print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
    raise SystemExit(1)

print(f"Modern C++ skeleton {len(contracts)}개의 정상적인 초기 실패를 확인했습니다")
