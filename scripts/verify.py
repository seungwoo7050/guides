#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shlex
import signal
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from process_runner import CommandSpawnError, run_process

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = Path(tempfile.mkdtemp(prefix="mobile-app-verify-"))
LOG_PATH = RUN_DIR / "verify.log"
SUMMARY_PATH = RUN_DIR / "summary.json"

Status = Literal["PASS", "FAIL", "NOT-RUN"]
Kind = Literal["required", "informational", "manual"]
Lifecycle = Literal["RUNNING", "COMPLETE", "INTERRUPTED", "INFRA_ERROR"]
OverallStatus = Literal["PASS", "FAIL", "INCOMPLETE"]


@dataclass(frozen=True)
class Gate:
    gate_id: str
    label: str
    command: tuple[str, ...]
    kind: Kind = "required"
    dependencies: tuple[str, ...] = ()
    timeout_seconds: int = 180


@dataclass
class Result:
    gate_id: str
    label: str
    kind: Kind
    status: Status
    command: list[str]
    duration_seconds: float
    exit_code: int | None = None
    reason: str | None = None
    failure_class: str | None = None
    evidence: dict[str, object] | None = None


class InfrastructureAbort(RuntimeError):
    pass


class VerificationInterrupted(KeyboardInterrupt):
    def __init__(self, signum: int):
        self.signum = signum
        super().__init__(signal.Signals(signum).name)


RESULTS: list[Result] = []
STARTED_AT = datetime.now(UTC)
FINISHED_AT: datetime | None = None
LIFECYCLE: Lifecycle = "RUNNING"
INTERRUPTED_BY: str | None = None
INFRASTRUCTURE_ERROR: str | None = None
ACTIVE_GATE_ID: str | None = None
EXPECTED_GATES: tuple[Gate, ...] = ()


def append_log(message: str = "") -> None:
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(message)
        handle.write("\n")
    print(message, flush=True)


def atomic_write_json(path: Path, value: dict[str, object]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def read_json_identity(path: Path, keys: tuple[str, ...]) -> dict[str, object] | None:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return {key: payload.get(key) for key in keys}


def source_identity() -> dict[str, object] | None:
    return read_json_identity(
        ROOT / ".guide/mobile-app/prepared.json",
        (
            "schema",
            "guide",
            "source_sha256",
            "source_file_count",
            "package_lock_sha256",
            "dependency_receipt",
            "node",
            "npm",
            "python",
            "prepared_at_utc",
        ),
    )


def environment_identity() -> dict[str, object] | None:
    return read_json_identity(
        ROOT / ".guide/mobile-app/environment.json",
        ("checked_at_utc", "host", "android", "ios", "claim_limit"),
    )


def overall_status() -> OverallStatus:
    if LIFECYCLE in ("RUNNING", "INTERRUPTED", "INFRA_ERROR"):
        return "INCOMPLETE"
    expected_required = sum(gate.kind == "required" for gate in EXPECTED_GATES)
    required = [result for result in RESULTS if result.kind == "required"]
    if len(required) != expected_required or any(result.status != "PASS" for result in required):
        return "FAIL"
    return "PASS"


def summary_payload() -> dict[str, object]:
    required = [result for result in RESULTS if result.kind == "required"]
    informational = [result for result in RESULTS if result.kind == "informational"]
    manual = [result for result in RESULTS if result.kind == "manual"]
    automatic = required + informational
    payload: dict[str, object] = {
        "schema": 2,
        "guide": "mobile-app",
        "lifecycle": LIFECYCLE,
        "overall_status": overall_status(),
        "started_at_utc": STARTED_AT.isoformat(),
        "interrupted_by": INTERRUPTED_BY,
        "infrastructure_error": INFRASTRUCTURE_ERROR,
        "active_gate_id": ACTIVE_GATE_ID,
        "run_directory": str(RUN_DIR),
        "log_path": str(LOG_PATH),
        "summary_path": str(SUMMARY_PATH),
        "prepared_identity": source_identity(),
        "environment_identity": environment_identity(),
        "expected": {
            "automatic_total": len(EXPECTED_GATES),
            "required_total": sum(gate.kind == "required" for gate in EXPECTED_GATES),
            "informational_total": sum(gate.kind == "informational" for gate in EXPECTED_GATES),
            "manual_total": len(MANUAL),
        },
        "completed": {
            "automatic_results": len(automatic),
            "manual_results": len(manual),
        },
        "counts": {
            "required_pass": sum(result.status == "PASS" for result in required),
            "required_fail": sum(result.status == "FAIL" for result in required),
            "required_not_run": sum(result.status == "NOT-RUN" for result in required),
            "informational_pass": sum(result.status == "PASS" for result in informational),
            "informational_fail": sum(result.status == "FAIL" for result in informational),
            "informational_not_run": sum(result.status == "NOT-RUN" for result in informational),
            "manual_not_run": sum(result.status == "NOT-RUN" for result in manual),
        },
        "results": [asdict(result) for result in RESULTS],
        "claim_limit": (
            "자동 검사는 구조와 공개 행동의 일부만 확인하며 교육적 완성, 실제 기기·서명·store 결과, "
            "stable 상태를 선언하지 않는다."
        ),
    }
    if FINISHED_AT is not None:
        payload["finished_at_utc"] = FINISHED_AT.isoformat()
    return payload


def write_summary() -> None:
    atomic_write_json(SUMMARY_PATH, summary_payload())


def dependency_reason(gate: Gate, statuses: dict[str, Status]) -> str | None:
    blocked = [dependency for dependency in gate.dependencies if statuses.get(dependency) != "PASS"]
    if not blocked:
        return None
    detail = ", ".join(f"{name}={statuses.get(name, 'NOT-RUN')}" for name in blocked)
    return f"dependency가 통과하지 않아 실행하지 않음: {detail}"


def evidence_from_output(output: str) -> dict[str, object] | None:
    raw_values = [line.removeprefix("EVIDENCE_JSON ") for line in output.splitlines() if line.startswith("EVIDENCE_JSON ")]
    if not raw_values:
        return None
    if len(raw_values) != 1:
        raise ValueError(f"EVIDENCE_JSON line은 정확히 하나여야 합니다: count={len(raw_values)}")
    value = json.loads(raw_values[0])
    if not isinstance(value, dict):
        raise ValueError("EVIDENCE_JSON payload가 object가 아닙니다.")
    return value


def record_result(result: Result, statuses: dict[str, Status]) -> None:
    RESULTS.append(result)
    statuses[result.gate_id] = result.status
    write_summary()


def run_gate(gate: Gate, statuses: dict[str, Status]) -> None:
    blocked = dependency_reason(gate, statuses)
    if blocked:
        result = Result(
            gate_id=gate.gate_id,
            label=gate.label,
            kind=gate.kind,
            status="NOT-RUN",
            command=list(gate.command),
            duration_seconds=0.0,
            reason=blocked,
            failure_class="dependency",
        )
        append_log(f"[NOT-RUN] {gate.label} — {blocked}")
        record_result(result, statuses)
        return

    append_log()
    append_log(f"[RUN] {gate.label}")
    append_log(f"+ {shlex.join(gate.command)}")
    try:
        completed = run_process(
            list(gate.command),
            cwd=ROOT,
            timeout_seconds=gate.timeout_seconds,
            combine_output=True,
            grace_seconds=5,
            env={**os.environ, "CI": "1", "EXPO_NO_TELEMETRY": "1"},
        )
    except CommandSpawnError as error:
        result = Result(
            gate_id=gate.gate_id,
            label=gate.label,
            kind=gate.kind,
            status="FAIL",
            command=list(gate.command),
            duration_seconds=0.0,
            reason=str(error),
            failure_class="infrastructure",
        )
        append_log(f"[FAIL][INFRA] {gate.label} — {error}")
        record_result(result, statuses)
        raise InfrastructureAbort(str(error)) from error

    output = completed.stdout.rstrip()
    if output:
        append_log(output)
    status: Status
    failure_class: str | None = None
    reason: str | None = None
    evidence: dict[str, object] | None = None
    abort: str | None = None
    if completed.timed_out:
        status = "FAIL"
        failure_class = "timeout"
        reason = f"timeout={gate.timeout_seconds}s; process-group-terminated"
    elif completed.returncode != 0:
        status = "FAIL"
        failure_class = "command"
        reason = f"exit={completed.returncode}"
    else:
        status = "PASS"
        try:
            evidence = evidence_from_output(output)
        except (ValueError, json.JSONDecodeError) as error:
            status = "FAIL"
            failure_class = "infrastructure"
            reason = f"malformed structured evidence: {error}"
            abort = reason
    result = Result(
        gate_id=gate.gate_id,
        label=gate.label,
        kind=gate.kind,
        status=status,
        command=list(gate.command),
        duration_seconds=completed.duration_seconds,
        exit_code=completed.returncode,
        reason=reason,
        failure_class=failure_class,
        evidence=evidence,
    )
    append_log(
        f"[{status}] {gate.label} duration={completed.duration_seconds:.3f}s"
        + (f" {reason}" if reason else "")
    )
    record_result(result, statuses)
    if abort:
        raise InfrastructureAbort(abort)


def manual_result(gate_id: str, label: str, reason: str) -> Result:
    return Result(
        gate_id=gate_id,
        label=label,
        kind="manual",
        status="NOT-RUN",
        command=[],
        duration_seconds=0.0,
        reason=reason,
        failure_class="manual-evidence",
    )


def gates() -> list[Gate]:
    prepared_dependencies = ("toolchain", "prepared-source")
    return [
        Gate("toolchain", "pinned toolchain contract", ("python3", "scripts/toolchain_contract.py"), timeout_seconds=45),
        Gate("prepared-source", "prepared source, dependency, and runtime identity", ("python3", "scripts/source_fingerprint.py", "--check"), dependencies=("toolchain",), timeout_seconds=60),
        Gate("structure", "role-based branch structure", ("python3", "scripts/verify_structure.py"), timeout_seconds=60),
        Gate("links", "local documentation links", ("python3", "scripts/verify_links.py"), timeout_seconds=60),
        Gate("exercise-contracts", "exercise and capstone mechanical contracts", ("python3", "scripts/verify_exercise_contracts.py"), timeout_seconds=60),
        Gate("verification-infrastructure", "verification infrastructure negative fixtures", ("python3", "-m", "unittest", "discover", "-s", "scripts/tests", "-p", "test_*.py", "-v"), timeout_seconds=180),
        Gate("environment", "required host capability observation report", ("python3", "scripts/environment_report.py"), timeout_seconds=90),
        Gate("history", "independent meaning-unit history report", ("python3", "scripts/verify_history.py"), timeout_seconds=60),
        Gate("dependency-tree", "installed dependency tree", ("npm", "ls", "--all", "--workspaces", "--include-workspace-root"), dependencies=prepared_dependencies, timeout_seconds=240),
        Gate("typecheck", "TypeScript public boundaries", ("npm", "run", "typecheck"), dependencies=prepared_dependencies, timeout_seconds=300),
        Gate("app-profiles", "development, preview, and production public app config", ("python3", "scripts/check_app_profiles.py"), dependencies=prepared_dependencies, timeout_seconds=180),
        Gate("reference", "reference behavior suites", ("npm", "run", "test:reference"), dependencies=prepared_dependencies, timeout_seconds=600),
        Gate("skeleton-rejection", "intentional skeleton rejected for named behaviors", ("npm", "run", "test:skeleton:reject"), dependencies=prepared_dependencies, timeout_seconds=420),
        Gate("mutants", "known-wrong implementations rejected", ("npm", "run", "test:mutants"), dependencies=prepared_dependencies, timeout_seconds=240),
        Gate("sync-model", "sync history model", ("node", "--test", "examples/sync-model/sync-model.test.mjs"), dependencies=prepared_dependencies, timeout_seconds=120),
        Gate("reference-android-bundle", "reference Android JS bundle", ("python3", "scripts/export_bundle.py", "--project", "reference", "--platform", "android"), dependencies=prepared_dependencies, timeout_seconds=720),
        Gate("reference-ios-bundle", "reference iOS JS bundle", ("python3", "scripts/export_bundle.py", "--project", "reference", "--platform", "ios"), dependencies=prepared_dependencies, timeout_seconds=720),
        Gate("skeleton-android-bundle", "skeleton Android JS bundle", ("python3", "scripts/export_bundle.py", "--project", "skeleton", "--platform", "android"), dependencies=prepared_dependencies, timeout_seconds=720),
        Gate("skeleton-ios-bundle", "skeleton iOS JS bundle", ("python3", "scripts/export_bundle.py", "--project", "skeleton", "--platform", "ios"), dependencies=prepared_dependencies, timeout_seconds=720),
        Gate("cng", "generated native identity and link configuration", ("npm", "run", "check:cng"), dependencies=prepared_dependencies, timeout_seconds=900),
        Gate("expo-dependencies", "Expo dependency compatibility", ("npm", "run", "check:expo"), dependencies=prepared_dependencies, timeout_seconds=300),
        Gate("source-unchanged", "source and dependency identity unchanged after generated checks", ("python3", "scripts/source_fingerprint.py", "--check"), dependencies=prepared_dependencies, timeout_seconds=60),
    ]


MANUAL = (
    manual_result("android-native-device", "Android native compile, sign, install, and physical-device journey", "Android SDK 36 and authorized device evidence are external to this run"),
    manual_result("ios-native-device", "iOS native compile, sign, install, and physical-device journey", "full Xcode, signing identity, and authorized device evidence are external to this run"),
    manual_result("device-capabilities", "camera, location, notification, and background OS behavior", "simulated ports do not prove OS prompts, scheduling, interruption, or delivery"),
    manual_result("accessibility-performance", "TalkBack, VoiceOver, lifecycle, and release-like performance", "human assistive-technology review and release-like device measurements are required"),
    manual_result("distribution", "signing ownership, store submission/review, and rollout", "store accounts, credentials, review, and rollout are intentionally not automated"),
    manual_result("educational-review", "owns-to-exit trace and capstone evidence judgment", "mechanical checks cannot declare educational completion or stable status"),
)


def validate_gate_manifest(gate_list: tuple[Gate, ...], manual: tuple[Result, ...] = MANUAL) -> None:
    ids = [gate.gate_id for gate in gate_list]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate automatic gate id")
    manual_ids = [result.gate_id for result in manual]
    if len(manual_ids) != len(set(manual_ids)) or set(ids).intersection(manual_ids):
        raise ValueError("duplicate/colliding manual gate id")
    indexes = {gate_id: index for index, gate_id in enumerate(ids)}
    for index, gate in enumerate(gate_list):
        if not gate.command or gate.kind == "manual" or gate.timeout_seconds <= 0:
            raise ValueError(f"invalid gate contract: {gate.gate_id}")
        for dependency in gate.dependencies:
            if dependency not in indexes:
                raise ValueError(f"unknown dependency: {gate.gate_id} -> {dependency}")
            if indexes[dependency] >= index:
                raise ValueError(f"dependency is not topologically earlier: {gate.gate_id} -> {dependency}")


def handle_signal(signum: int, _frame: object) -> None:
    global INTERRUPTED_BY
    INTERRUPTED_BY = signal.Signals(signum).name
    raise VerificationInterrupted(signum)


def append_missing(gate_list: tuple[Gate, ...], reason: str, *, active_as_fail: bool = False) -> None:
    existing = {result.gate_id for result in RESULTS}
    for gate in gate_list:
        if gate.gate_id in existing:
            continue
        is_active = active_as_fail and gate.gate_id == ACTIVE_GATE_ID
        RESULTS.append(
            Result(
                gate_id=gate.gate_id,
                label=gate.label,
                kind=gate.kind,
                status="FAIL" if is_active else "NOT-RUN",
                command=list(gate.command),
                duration_seconds=0.0,
                reason=reason,
                failure_class="infrastructure" if is_active else "incomplete",
            )
        )


def append_manual_results() -> None:
    existing = {result.gate_id for result in RESULTS}
    for result in MANUAL:
        if result.gate_id not in existing:
            RESULTS.append(Result(**asdict(result)))
            append_log(f"[NOT-RUN][MANUAL] {result.label} — {result.reason}")


def main() -> int:
    global ACTIVE_GATE_ID, EXPECTED_GATES, FINISHED_AT, INFRASTRUCTURE_ERROR, LIFECYCLE
    EXPECTED_GATES = tuple(gates())
    LOG_PATH.touch(mode=0o600)
    append_log(f"VERIFY RUN {RUN_DIR}")
    append_log(f"VERIFY LOG {LOG_PATH}")
    append_log(f"VERIFY SUMMARY JSON {SUMMARY_PATH}")
    append_log("결과는 required/informational/manual과 PASS/FAIL/NOT-RUN을 구분합니다.")
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    statuses: dict[str, Status] = {}
    exit_code = 1
    try:
        validate_gate_manifest(EXPECTED_GATES)
        write_summary()
        for gate in EXPECTED_GATES:
            ACTIVE_GATE_ID = gate.gate_id
            run_gate(gate, statuses)
            ACTIVE_GATE_ID = None
        LIFECYCLE = "COMPLETE"
    except VerificationInterrupted as error:
        LIFECYCLE = "INTERRUPTED"
        append_log(f"[INTERRUPTED] signal={INTERRUPTED_BY} active_gate={ACTIVE_GATE_ID}")
        append_missing(EXPECTED_GATES, f"verification interrupted by {INTERRUPTED_BY}")
        exit_code = 128 + error.signum
    except InfrastructureAbort as error:
        LIFECYCLE = "INFRA_ERROR"
        INFRASTRUCTURE_ERROR = str(error)
        append_log(f"[INFRA_ERROR] {error}")
        append_missing(EXPECTED_GATES, f"not run after infrastructure error: {error}")
    except BaseException as error:
        LIFECYCLE = "INFRA_ERROR"
        INFRASTRUCTURE_ERROR = f"{type(error).__name__}: {error}"
        append_log(f"[INFRA_ERROR] {INFRASTRUCTURE_ERROR}")
        append_missing(EXPECTED_GATES, INFRASTRUCTURE_ERROR, active_as_fail=True)
    finally:
        ACTIVE_GATE_ID = None
        append_manual_results()
        FINISHED_AT = datetime.now(UTC)
        write_summary()

    payload = summary_payload()
    counts = payload["counts"]
    assert isinstance(counts, dict)
    append_log()
    append_log(
        "VERIFY SUMMARY "
        f"lifecycle={LIFECYCLE} overall={payload['overall_status']} "
        f"required_pass={counts['required_pass']} "
        f"required_fail={counts['required_fail']} "
        f"required_not_run={counts['required_not_run']} "
        f"manual_not_run={counts['manual_not_run']}"
    )
    append_log(f"VERIFY LOG {LOG_PATH}")
    append_log(f"VERIFY SUMMARY JSON {SUMMARY_PATH}")
    append_log("자동 결과는 교육적 완성, 실제 기기·서명·store 결과 또는 stable 상태를 선언하지 않습니다.")
    write_summary()
    if LIFECYCLE == "COMPLETE":
        exit_code = 0 if payload["overall_status"] == "PASS" else 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
