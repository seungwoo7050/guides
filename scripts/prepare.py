#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

import environment_report
import source_fingerprint
from process_runner import CommandSpawnError, ProcessInterrupted, run_process
from toolchain_contract import validate

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"PREPARE ERROR: {message}")


def main() -> None:
    actual = validate()
    lockfile = ROOT / "package-lock.json"
    if lockfile.is_symlink() or not lockfile.is_file():
        fail("package-lock.json이 regular file로 존재해야 합니다.")

    node_modules = ROOT / "node_modules"
    if node_modules.is_symlink() or (node_modules.exists() and not node_modules.is_dir()):
        fail("node_modules가 symlink이거나 directory가 아닙니다. 자동 삭제하지 않습니다.")

    source_fingerprint.ensure_safe_state_dir()
    marker = source_fingerprint.MARKER
    if marker.exists():
        marker.unlink()

    before_sha, before_count = source_fingerprint.fingerprint()
    print(
        f"REQUIRED Node {actual['node']} npm {actual['npm']} Python {actual['python']}"
    )
    print(
        f"SOURCE BEFORE files={before_count} sha256={before_sha}\n"
        "+ npm ci (검증된 repository node_modules만 재생성)"
    )
    try:
        result = run_process(
            ["npm", "ci"],
            cwd=ROOT,
            env={**os.environ, "CI": "1"},
            timeout_seconds=1200,
            capture_output=False,
            grace_seconds=5,
        )
    except CommandSpawnError as error:
        fail(f"npm ci를 시작하지 못했습니다: {error}")
    except ProcessInterrupted as error:
        print(f"PREPARE INTERRUPTED signal={error}", flush=True)
        raise SystemExit(128 + error.signum) from error
    except KeyboardInterrupt as error:
        print("PREPARE INTERRUPTED signal=SIGINT", flush=True)
        raise SystemExit(130) from error
    if result.timed_out:
        fail("npm ci timed out after 1200s; process group을 종료했고 prepared marker는 생성하지 않았습니다.")
    if result.returncode != 0:
        fail(f"npm ci failed exit={result.returncode}; prepared marker는 생성하지 않았습니다.")

    after_sha, after_count = source_fingerprint.fingerprint()
    if (after_sha, after_count) != (before_sha, before_count):
        fail(
            "npm ci 동안 source가 변경됐습니다. prepared marker를 생성하지 않습니다. "
            f"before={before_sha}/{before_count} after={after_sha}/{after_count}"
        )

    environment_report.main()
    current = source_fingerprint.current_contract()
    source_fingerprint.write_marker(current)
    print(
        f"PREPARE OK files={after_count} sha256={after_sha}\n"
        f"CREATED {node_modules}\n"
        f"CREATED {source_fingerprint.STATE_DIR}\n"
        "DEPENDENCY RECEIPT installed lock, workspace targets, selected bins (registry content는 npm ci integrity 신뢰)\n"
        "NOT PREPARED Android/iOS device, signing, cloud/store account\n"
        "verify: ./verify.sh"
    )


if __name__ == "__main__":
    main()
