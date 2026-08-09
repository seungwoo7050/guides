#!/usr/bin/env python3
"""Validate the public behavior of the deterministic platform model."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import signal
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
IDENTIFIER_KEYS = (
    "service_id",
    "resource_id",
    "operation_id",
    "tenant_id",
    "artifact_id",
    "profile_id",
)


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


def validate_contract_metadata(contract: dict[str, Any]) -> None:
    declared_code = contract.get("contract_code")
    expected_path = CONTRACT_CODE.relative_to(ROOT).as_posix()
    if not isinstance(declared_code, dict) or declared_code.get("path") != expected_path:
        raise HarnessError("E_CONTRACT", f"contract_code.path must be {expected_path}")
    if declared_code.get("sha256") != sha256(CONTRACT_CODE):
        raise HarnessError("E_CONTRACT", "contract_code SHA-256 differs from tests/contract.py")

    identifiers = contract.get("identifiers")
    if not isinstance(identifiers, dict) or set(identifiers) != set(IDENTIFIER_KEYS):
        raise HarnessError("E_CONTRACT", "contract identifiers must contain exactly the six canonical keys")
    if any(not isinstance(identifiers[key], str) or not identifiers[key] for key in IDENTIFIER_KEYS):
        raise HarnessError("E_CONTRACT", "contract identifiers must be non-empty strings")


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


def install_learner_audit_guard() -> None:
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


def sanitized_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONINSPECT"):
        environment.pop(key, None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONHASHSEED"] = "0"
    return environment


def protocol_error(code: str, message: str) -> dict[str, Any]:
    return {"harness_error": {"code": code, "message": message}}


def learner_worker(implementation: str) -> int:
    """Serve learner API calls without loading executable checks in this process."""

    protocol_input = sys.stdin
    protocol_output = sys.stdout
    encode = json.dumps
    decode = json.loads

    def send(payload: dict[str, Any]) -> bool:
        try:
            line = encode(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            protocol_output.write(line)
            protocol_output.flush()
            return True
        except Exception:
            return False

    try:
        install_learner_audit_guard()
        module = load_module(Path(implementation), "learner_platform_model")
        required = load_json(CONTRACT_PATH).get("implementation_api", [])
        if not isinstance(required, list) or any(not isinstance(name, str) for name in required):
            raise HarnessError("E_CONTRACT", "implementation_api must be a list of names")
        available = [name for name in required if callable(getattr(module, name, None))]
        if not send({"api": available}):
            return 0
    except HarnessError as error:
        send(protocol_error(error.code, error.message))
        return 0
    except Exception as error:
        send(protocol_error("E_IMPORT", f"{type(error).__name__}: {error}"))
        return 0

    for line in protocol_input:
        request: Any = None
        try:
            request = decode(line, object_pairs_hook=strict_object, parse_constant=reject_constant)
            if not isinstance(request, dict) or set(request) != {"id", "name", "args"}:
                raise ValueError("call envelope must contain exactly id, name and args")
            call_id = request["id"]
            name = request["name"]
            arguments = request["args"]
            if not isinstance(call_id, int) or isinstance(call_id, bool) or call_id < 1:
                raise ValueError("call id must be a positive integer")
            if not isinstance(name, str) or name not in required:
                raise ValueError("call name is outside implementation_api")
            if not isinstance(arguments, list):
                raise ValueError("call args must be an array")
            function = getattr(module, name, None)
            if not callable(function):
                raise AttributeError(f"missing public API: {name}")
            before = encode(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            value = function(*arguments)
            after = encode(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if after != before:
                raise RuntimeError(f"{name} mutated its input arguments")
            if not send({"id": call_id, "value": value}):
                return 0
        except Exception as error:
            if not send(
                {
                    "id": request.get("id") if isinstance(request, dict) else None,
                    "call_error": f"{type(error).__name__}: {error}",
                }
            ):
                return 0
    return 0


class LearnerProxy:
    """Expose learner callables over a process boundary to immutable checks."""

    MAX_PROTOCOL_LINE = 1_000_000

    def __init__(self, implementation: str, required: list[str]):
        self.implementation = implementation
        self.required = tuple(required)
        self.next_id = 1
        self.fatal: HarnessError | None = None
        self.process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--_learner_worker", implementation],
            cwd=ROOT,
            env=sanitized_environment(),
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
        )
        handshake = self._read_payload()
        if isinstance(handshake.get("harness_error"), dict):
            item = handshake["harness_error"]
            raise HarnessError(str(item.get("code", "E_IMPORT")), str(item.get("message", "learner import failed")))
        available = handshake.get("api")
        if not isinstance(available, list) or any(not isinstance(name, str) for name in available):
            raise HarnessError("E_LEARNER_PROTOCOL", "learner worker omitted API handshake")
        missing = [name for name in required if name not in available]
        if missing:
            raise HarnessError("E_API", f"missing public API: {', '.join(missing)}")

    def _read_payload(self) -> dict[str, Any]:
        if self.process.stdout is None:
            raise HarnessError("E_LEARNER_PROTOCOL", "learner worker stdout is unavailable")
        line = self.process.stdout.readline(self.MAX_PROTOCOL_LINE + 1)
        if not line or len(line) > self.MAX_PROTOCOL_LINE or not line.endswith("\n"):
            raise HarnessError("E_LEARNER_PROTOCOL", "learner worker returned an invalid protocol line")
        try:
            payload = json.loads(line, object_pairs_hook=strict_object, parse_constant=reject_constant)
        except (json.JSONDecodeError, ValueError) as error:
            raise HarnessError("E_LEARNER_PROTOCOL", "learner worker returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise HarnessError("E_LEARNER_PROTOCOL", "learner worker payload must be an object")
        return payload

    def _call(self, name: str, arguments: tuple[Any, ...]) -> Any:
        if self.fatal is not None:
            raise self.fatal
        call_id = self.next_id
        self.next_id += 1
        request = json.dumps(
            {"id": call_id, "name": name, "args": list(arguments)},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        try:
            if self.process.stdin is None:
                raise BrokenPipeError("learner worker stdin is unavailable")
            self.process.stdin.write(request + "\n")
            self.process.stdin.flush()
            payload = self._read_payload()
        except (OSError, BrokenPipeError) as error:
            failure = HarnessError("E_LEARNER_PROTOCOL", f"learner worker communication failed: {error}")
            self.fatal = failure
            raise failure from error
        if payload.get("id") != call_id:
            failure = HarnessError("E_LEARNER_PROTOCOL", "learner worker response id differs from request")
            self.fatal = failure
            raise failure
        if isinstance(payload.get("call_error"), str):
            raise RuntimeError(payload["call_error"])
        if set(payload) != {"id", "value"}:
            failure = HarnessError("E_LEARNER_PROTOCOL", "learner worker response must contain id and value")
            self.fatal = failure
            raise failure
        return payload["value"]

    def __getattr__(self, name: str) -> Any:
        if name not in self.required:
            raise AttributeError(name)

        def remote_call(*arguments: Any) -> Any:
            try:
                return self._call(name, arguments)
            except HarnessError as error:
                self.fatal = error
                raise

        return remote_call

    def close(self) -> None:
        if self.process.stdin is not None:
            try:
                self.process.stdin.close()
            except OSError:
                pass
        try:
            self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


def worker(implementation: str) -> int:
    proxy: LearnerProxy | None = None
    try:
        contract = load_json(CONTRACT_PATH)
        validate_contract_metadata(contract)
        contract_module = load_module(CONTRACT_CODE, "platform_public_contract")
        required = contract.get("implementation_api", [])
        if not isinstance(required, list) or any(not isinstance(name, str) for name in required):
            raise HarnessError("E_CONTRACT", "implementation_api must be a list of names")
        proxy = LearnerProxy(implementation, required)
        checks = contract_module.run_contract(proxy)
        if proxy.fatal is not None:
            raise proxy.fatal
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
    finally:
        if proxy is not None:
            proxy.close()


def invoke_worker(implementation: Path, timeout_seconds: int) -> list[dict[str, Any]]:
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--_worker", str(implementation)],
        cwd=ROOT,
        env=sanitized_environment(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as error:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (AttributeError, OSError):
            process.kill()
        process.communicate()
        raise HarnessError("E_TIMEOUT", f"implementation exceeded {timeout_seconds}s") from error
    if process.returncode != 0:
        raise HarnessError("E_WORKER", f"worker exited {process.returncode}: {stderr.strip()}")
    try:
        payload = json.loads(stdout, object_pairs_hook=strict_object, parse_constant=reject_constant)
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
    identifiers = contract["identifiers"]
    first_observation = checks[0].get("observed") if checks else None
    if result == "PASS" and (
        not isinstance(first_observation, dict) or first_observation.get("identifiers") != identifiers
    ):
        raise HarnessError("E_CONTRACT", "PE-001 observed evidence must retain the six canonical identifiers")
    return {
        "schema_version": 1,
        "guide": "platform-engineering",
        "lab": "13-platform-control-plane",
        "implementation": {
            "path": implementation.relative_to(ROOT).as_posix(),
            "sha256": sha256(implementation),
        },
        "identifiers": identifiers,
        "contract": {
            "path": CONTRACT_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha256(CONTRACT_PATH),
            "check_ids": expected_ids,
        },
        "contract_code": {
            "path": CONTRACT_CODE.relative_to(ROOT).as_posix(),
            "sha256": sha256(CONTRACT_CODE),
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
            "contract_process_isolated_from_learner": True,
            "learner_rpc_process": True,
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
    parser.add_argument("--_learner_worker", help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)
    if arguments._learner_worker:
        return learner_worker(arguments._learner_worker)
    if arguments._worker:
        return worker(arguments._worker)
    if not arguments.implementation:
        print("PLATFORM MODEL ERROR [E_PATH] --implementation is required", file=sys.stderr)
        return HARNESS_EXIT
    try:
        contract = load_json(CONTRACT_PATH)
        validate_contract_metadata(contract)
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
