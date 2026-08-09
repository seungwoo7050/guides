#!/usr/bin/env python3
"""Validate the public behavior of the deterministic platform model."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "exercises/13-platform-control-plane"
CONTRACT_PATH = LAB / "contract.json"
CONTRACT_CODE = LAB / "tests/contract.py"
HARNESS_EXIT = 2


class HarnessError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value: {value}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise HarnessError("E_CONTRACT", f"cannot load {path.relative_to(ROOT)}: {error}") from error
    if not isinstance(value, dict):
        raise HarnessError("E_CONTRACT", "contract top level must be an object")
    return value


def safe_implementation(raw: str) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        absolute = candidate.absolute()
        resolved = absolute.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise HarnessError("E_PATH", f"implementation does not exist: {raw}") from error
    try:
        relative = resolved.relative_to(ROOT)
    except ValueError as error:
        raise HarnessError("E_PATH", "implementation must remain inside the repository") from error
    current = ROOT
    for part in relative.parts:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as error:
            raise HarnessError("E_PATH", f"cannot inspect implementation path: {relative}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise HarnessError("E_PATH", f"implementation path contains a symlink: {relative}")
    if not resolved.is_file():
        raise HarnessError("E_PATH", "implementation must be a regular file")
    return resolved


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise HarnessError("E_IMPORT", f"cannot create module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    except Exception as error:  # implementation failure becomes a stable harness error
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        raise HarnessError("E_IMPORT", f"{type(error).__name__}: {error}") from error
    finally:
        try:
            sys.path.remove(str(path.parent))
        except ValueError:
            pass
    return module


def install_worker_audit_guard() -> None:
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND

    def guard(event: str, args: tuple[Any, ...]) -> None:
        if event.startswith("socket."):
            raise PermissionError("network access is disabled by the platform model validator")
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.posix_spawnp"}:
            raise PermissionError("child process creation is disabled inside learner code")
        if event == "open" and len(args) >= 3:
            mode = args[1]
            flags = args[2]
            if (isinstance(mode, str) and any(token in mode for token in ("w", "a", "x", "+"))) or (
                isinstance(flags, int) and flags & write_flags
            ):
                raise PermissionError("file writes are disabled inside learner code")

    sys.addaudithook(guard)


def worker(implementation: str) -> int:
    try:
        contract_module = load_module(CONTRACT_CODE, "platform_public_contract")
        install_worker_audit_guard()
        module = load_module(Path(implementation), "learner_platform_model")
        required = load_json(CONTRACT_PATH).get("implementation_api", [])
        missing = [name for name in required if not callable(getattr(module, name, None))]
        if missing:
            raise HarnessError("E_API", f"missing public API: {', '.join(missing)}")
        checks = contract_module.run_contract(module)
        print(json.dumps({"checks": checks}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except HarnessError as error:
        print(
            json.dumps(
                {"harness_error": {"code": error.code, "message": error.message}},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    except Exception as error:
        print(
            json.dumps(
                {"harness_error": {"code": "E_WORKER", "message": f"{type(error).__name__}: {error}"}},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0


def invoke_worker(implementation: Path, timeout_seconds: int) -> list[dict[str, Any]]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONHASHSEED"] = "0"
    try:
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--_worker", str(implementation)],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        raise HarnessError("E_TIMEOUT", f"implementation exceeded {timeout_seconds}s") from error
    if completed.returncode != 0:
        raise HarnessError("E_WORKER", f"worker exited {completed.returncode}")
    try:
        payload = json.loads(completed.stdout, object_pairs_hook=strict_object, parse_constant=reject_constant)
    except (json.JSONDecodeError, ValueError) as error:
        raise HarnessError("E_WORKER", "worker did not return one JSON object") from error
    if not isinstance(payload, dict):
        raise HarnessError("E_WORKER", "worker payload is not an object")
    if isinstance(payload.get("harness_error"), dict):
        item = payload["harness_error"]
        raise HarnessError(str(item.get("code", "E_WORKER")), str(item.get("message", "worker error")))
    checks = payload.get("checks")
    if not isinstance(checks, list) or any(not isinstance(item, dict) for item in checks):
        raise HarnessError("E_WORKER", "worker omitted checks")
    return checks


def make_report(implementation: Path, contract: dict[str, Any], checks: list[dict[str, Any]]) -> dict[str, Any]:
    expected_ids = contract.get("check_ids", [])
    actual_ids = [item.get("id") for item in checks]
    if actual_ids != expected_ids:
        raise HarnessError("E_CONTRACT", "public check IDs differ from contract.json")
    failed_ids = [item["id"] for item in checks if item.get("status") == "fail"]
    error_ids = [item["id"] for item in checks if item.get("status") == "error"]
    passed = len(checks) - len(failed_ids) - len(error_ids)
    result = "PASS" if passed == len(checks) else "FAIL"
    return {
        "schema_version": 1,
        "guide": "platform-engineering",
        "lab": "13-platform-control-plane",
        "implementation": {
            "path": implementation.relative_to(ROOT).as_posix(),
            "sha256": sha256(implementation),
        },
        "contract": {
            "path": CONTRACT_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha256(CONTRACT_PATH),
            "check_ids": expected_ids,
        },
        "checks": checks,
        "summary": {
            "result": result,
            "total": len(checks),
            "passed": passed,
            "failed": len(failed_ids),
            "errors": len(error_ids),
            "failed_ids": failed_ids,
            "error_ids": error_ids,
        },
        "execution": {
            "child_process": True,
            "timeout_seconds": int(contract.get("execution", {}).get("timeout_seconds", 5)),
            "network_required": False,
            "network_denied_by_python_audit": True,
            "external_resources_created": False,
            "file_writes_denied_in_learner": True,
            "os_sandboxed": False,
        },
        "limitations": [
            "The Python audit hook is not an operating-system sandbox.",
            "The contract does not verify real IAM, networks, Kubernetes, providers, concurrency, crashes, or physical deletion.",
            "A passing synthetic model still requires human review before a production claim.",
        ],
    }


def write_report(path_text: str, report: dict[str, Any]) -> None:
    path = Path(path_text)
    if not path.is_absolute():
        raise HarnessError("E_REPORT", "report path must be absolute")
    parent = path.parent
    try:
        parent_metadata = parent.lstat()
    except OSError as error:
        raise HarnessError("E_REPORT", "report parent must already exist") from error
    if stat.S_ISLNK(parent_metadata.st_mode) or not stat.S_ISDIR(parent_metadata.st_mode):
        raise HarnessError("E_REPORT", "report parent must be a non-symlink directory")
    try:
        resolved_parent = parent.resolve(strict=True)
    except OSError as error:
        raise HarnessError("E_REPORT", "cannot resolve report parent") from error
    resolved = resolved_parent / path.name
    if resolved == ROOT or ROOT in resolved.parents:
        raise HarnessError("E_REPORT", "report must remain outside the repository")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(resolved, flags, 0o600)
    except OSError as error:
        raise HarnessError("E_REPORT", "report path must be a new regular file") from error
    payload = (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation")
    parser.add_argument("--report")
    parser.add_argument("--_worker", help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)
    if arguments._worker:
        return worker(arguments._worker)
    if not arguments.implementation:
        print("PLATFORM MODEL ERROR [E_PATH] --implementation is required", file=sys.stderr)
        return HARNESS_EXIT
    try:
        contract = load_json(CONTRACT_PATH)
        implementation = safe_implementation(arguments.implementation)
        timeout_seconds = int(contract.get("execution", {}).get("timeout_seconds", 5))
        checks = invoke_worker(implementation, timeout_seconds)
        report = make_report(implementation, contract, checks)
        if arguments.report:
            write_report(arguments.report, report)
    except HarnessError as error:
        print(f"PLATFORM MODEL ERROR [{error.code}] {error.message}", file=sys.stderr)
        return HARNESS_EXIT

    summary = report["summary"]
    print(
        "PLATFORM MODEL "
        f"{summary['result']} total={summary['total']} passed={summary['passed']} "
        f"failed={summary['failed']} errors={summary['errors']}"
    )
    for item in report["checks"]:
        print(f"[{item['status'].upper()}] {item['id']} {item['title']}: {item['message']}")
    return 0 if summary["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
