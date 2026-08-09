#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "exercises/07-local-cloud-model/tests/contract.py"
WORKER_TIMEOUT_SECONDS = 5
REQUIRED_API = (
    "CloudModel",
    "CloudModelError",
    "AccessDenied",
    "QuotaExceeded",
    "TenantInactive",
    "EventConflict",
)
LIMITATIONS = [
    "합성 in-process 상태 모델이며 실제 cloud provider emulator가 아닙니다.",
    "실제 IAM·network·queue·billing·physical deletion을 검증하지 않습니다.",
    "분산 transaction, process crash와 concurrent writer 원자성을 검증하지 않습니다.",
    "학습자 Python은 제한 시간의 child process에서 실행되지만 OS sandbox가 아닙니다.",
]


class VerifyError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_label(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError as error:
        raise VerifyError("E_PATH", "implementation must be inside the guide repository") from error


def regular_file(path: Path, label: str) -> Path:
    root = ROOT.resolve(strict=True)
    candidate = (path if path.is_absolute() else Path.cwd() / path).absolute()
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise VerifyError("E_PATH", f"{label} escapes the guide repository") from error
    if not relative.parts or any(component in ("", ".", "..") for component in relative.parts):
        raise VerifyError("E_PATH", f"{label} must use a canonical in-repository path")

    current = root
    for component in relative.parts:
        current = current / component
        try:
            mode = current.lstat().st_mode
        except OSError as error:
            raise VerifyError("E_PATH", f"{label} does not exist: {path}") from error
        if stat.S_ISLNK(mode):
            raise VerifyError("E_PATH", f"{label} may not use symlinks: {path}")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError) as error:
        raise VerifyError("E_PATH", f"{label} escapes the guide repository") from error
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise VerifyError("E_PATH", f"{label} must be a regular file: {path}")
    if resolved.suffix != ".py":
        raise VerifyError("E_PATH", f"{label} must be a Python file: {path}")
    return resolved


def load_module(path: Path, module_name: str) -> tuple[ModuleType, int, int]:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise VerifyError("E_IMPORT", f"cannot create import spec for {relative_label(path)}")
    module = importlib.util.module_from_spec(spec)
    stdout = io.StringIO()
    stderr = io.StringIO()
    sys.modules[spec.name] = module
    sys.path.insert(0, str(path.parent))
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            spec.loader.exec_module(module)
    except Exception as error:  # noqa: BLE001 - convert learner import to stable CLI error
        raise VerifyError(
            "E_IMPORT",
            f"{relative_label(path)} import failed: {type(error).__name__}: {error}",
        ) from error
    finally:
        if sys.path and sys.path[0] == str(path.parent):
            sys.path.pop(0)
    return module, len(stdout.getvalue().encode("utf-8")), len(stderr.getvalue().encode("utf-8"))


def validate_api(module: ModuleType) -> None:
    missing = [name for name in REQUIRED_API if not hasattr(module, name)]
    if missing:
        raise VerifyError("E_API", f"implementation is missing public API: {', '.join(missing)}")
    model = module.CloudModel()
    required_methods = (
        "provision_tenant",
        "store_document",
        "read_document",
        "enqueue_event",
        "process_next",
        "drain_events",
        "usage_for",
        "delete_tenant",
        "resource_inventory",
        "evidence_snapshot",
    )
    absent = [name for name in required_methods if not callable(getattr(model, name, None))]
    if absent:
        raise VerifyError("E_API", f"CloudModel is missing methods: {', '.join(absent)}")


def build_report(
    implementation: Path,
    results: list[dict[str, Any]],
    stdout_bytes: int,
    stderr_bytes: int,
) -> dict[str, Any]:
    passed = sum(record["status"] == "pass" for record in results)
    failed = sum(record["status"] == "fail" for record in results)
    errors = sum(record["status"] == "error" for record in results)
    return {
        "schema_version": 1,
        "guide_id": "cloud-computing",
        "exercise_id": "07-local-cloud-model",
        "implementation": {
            "path": relative_label(implementation),
            "sha256": sha256(implementation),
        },
        "contract": {
            "path": CONTRACT_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha256(CONTRACT_PATH),
            "check_ids": [record["id"] for record in results],
        },
        "execution": {
            "captured_stdout_bytes": stdout_bytes,
            "captured_stderr_bytes": stderr_bytes,
            "timeout_seconds": WORKER_TIMEOUT_SECONDS,
            "network_required": False,
            "external_resources_created": False,
            "os_sandboxed": False,
        },
        "checks": results,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "failed_ids": [record["id"] for record in results if record["status"] != "pass"],
            "result": "PASS" if failed == 0 and errors == 0 else "FAIL",
        },
        "limitations": LIMITATIONS,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    target = path if path.is_absolute() else Path.cwd() / path
    target = target.absolute()
    parent = target.parent
    try:
        parent_mode = parent.lstat().st_mode
    except FileNotFoundError as error:
        raise VerifyError("E_REPORT", f"report parent does not exist: {parent}") from error
    if stat.S_ISLNK(parent_mode) or not stat.S_ISDIR(parent_mode):
        raise VerifyError("E_REPORT", f"report parent must be a regular directory: {parent}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(target, flags, 0o600)
    except FileExistsError as error:
        raise VerifyError("E_REPORT", f"report already exists and will not be overwritten: {target}") from error
    try:
        payload = (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            target.unlink()
        except OSError:
            pass
        raise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify the deterministic public contract of exercise 07."
    )
    parser.add_argument("--implementation", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def worker_payload(implementation: Path) -> dict[str, Any]:
    try:
        contract_module, _, _ = load_module(CONTRACT_PATH, "cloud_model_contract")
        module, import_stdout, import_stderr = load_module(
            implementation,
            "cloud_model_" + sha256(implementation)[:16],
        )
        validate_api(module)
        runtime_stdout = io.StringIO()
        runtime_stderr = io.StringIO()
        with contextlib.redirect_stdout(runtime_stdout), contextlib.redirect_stderr(runtime_stderr):
            results = contract_module.run_contract(module)
        report = build_report(
            implementation,
            results,
            import_stdout + len(runtime_stdout.getvalue().encode("utf-8")),
            import_stderr + len(runtime_stderr.getvalue().encode("utf-8")),
        )
        return {"ok": True, "report": report}
    except VerifyError as error:
        return {"ok": False, "code": error.code, "message": str(error)}
    except Exception as error:  # noqa: BLE001 - isolate unexpected learner/harness failures
        return {
            "ok": False,
            "code": "E_WORKER",
            "message": f"worker failed: {type(error).__name__}: {error}",
        }


def run_worker(implementation: Path) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--implementation",
        str(implementation),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=WORKER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise VerifyError(
            "E_TIMEOUT",
            f"implementation exceeded {WORKER_TIMEOUT_SECONDS}s child-process limit",
        ) from error
    if completed.returncode != 0:
        raise VerifyError(
            "E_WORKER",
            f"worker exited {completed.returncode} without a contract result",
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise VerifyError("E_WORKER", "worker returned invalid JSON") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("ok"), bool):
        raise VerifyError("E_WORKER", "worker returned an invalid result envelope")
    if not payload["ok"]:
        raise VerifyError(str(payload.get("code", "E_WORKER")), str(payload.get("message", "worker failed")))
    report = payload.get("report")
    if not isinstance(report, dict):
        raise VerifyError("E_WORKER", "worker omitted the report")
    return report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        implementation = regular_file(args.implementation, "implementation")
        if args.worker:
            payload = worker_payload(implementation)
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0
        report = run_worker(implementation)
        if args.report is not None:
            write_report(args.report, report)
    except VerifyError as error:
        print(f"MODEL VERIFY ERROR [{error.code}]: {error}", file=sys.stderr)
        return 2

    for record in report["checks"]:
        marker = record["status"].upper()
        print(f"[{marker}] {record['id']} {record['title']}: {record['message']}")
    summary = report["summary"]
    print(
        "MODEL SUMMARY "
        f"total={summary['total']} passed={summary['passed']} "
        f"failed={summary['failed']} errors={summary['errors']}"
    )
    print(f"MODEL RESULT: {summary['result']}")
    if args.report is not None:
        print(f"MODEL REPORT: {args.report}")
    return 0 if summary["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
