#!/usr/bin/env python3
"""Validate eight kernel-model checkpoints, skeleton boundaries and bad snapshots."""

from __future__ import annotations

import ast
from collections.abc import Mapping
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent
DEFAULT_TIMEOUT = 20.0
CHECKPOINTS = (
    "01-lifecycle",
    "02-synchronization",
    "03-scheduler",
    "04-deadlock",
    "05-paging",
    "06-storage",
    "07-device-io",
    "08-cli",
)


def timeout_seconds() -> float:
    raw = os.environ.get("KERNEL_MODEL_TIMEOUT", str(DEFAULT_TIMEOUT))
    try:
        value = float(raw)
    except ValueError as error:
        raise SystemExit(f"KERNEL_MODEL_TIMEOUT은 양수여야 합니다: {raw}") from error
    if value <= 0:
        raise SystemExit(f"KERNEL_MODEL_TIMEOUT은 양수여야 합니다: {raw}")
    return value


def target_path(name: str) -> Path:
    unresolved = ROOT / name
    if unresolved.is_symlink():
        raise SystemExit(f"검사 대상 symbolic link는 허용하지 않습니다: {name}")
    path = unresolved.resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as error:
        raise SystemExit(f"검사 대상은 kernel-model 디렉터리 안에 있어야 합니다: {name}") from error
    if path == ROOT or not path.is_dir():
        raise SystemExit(f"검사 대상 디렉터리가 없습니다: {path}")
    if not (path / "kernel_model").is_dir() or not (path / "kernel-model.py").is_file():
        raise SystemExit(f"검사 대상의 package 구조가 올바르지 않습니다: {path}")
    return path


def activate(path: Path) -> None:
    sys.path.insert(0, str(path))


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"fixture 최상위 값이 객체가 아닙니다: {path}")
    return data


def assert_subset(actual: Any, expected: Any, location: str = "result") -> None:
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            raise AssertionError(f"{location}: object가 아닙니다: {actual!r}")
        for key, value in expected.items():
            if key not in actual:
                raise AssertionError(f"{location}: key가 없습니다: {key}")
            assert_subset(actual[key], value, f"{location}.{key}")
        return
    if actual != expected:
        raise AssertionError(f"{location}: expected={expected!r}, actual={actual!r}")


def implementation_suite(target_name: str, checkpoint: str) -> unittest.TestSuite:
    if checkpoint != "all" and checkpoint not in CHECKPOINTS:
        raise SystemExit(f"알 수 없는 checkpoint입니다: {checkpoint}")
    target_directory = target_path(target_name)
    activate(target_directory)
    from kernel_model.deadlock import DeadlockInputError, detect_deadlocked, find_wait_cycle, safe_sequence
    from kernel_model.device_io import DeviceQueue, DeviceStateError, RequestState
    from kernel_model.filesystem import FileSystemModel
    from kernel_model.journal import Journal, JournalError
    from kernel_model.lifecycle import KernelState, TaskState
    from kernel_model.paging import FaultKind, MemoryFault, MemoryManager, simulate_replacement
    from kernel_model.scheduler import JobSpec, Policy, simulate
    from kernel_model.synchronization import ConditionChannel, CountingSemaphore, SynchronizationError, WaitToken

    class LifecycleTests(unittest.TestCase):
        def test_state_locations_remain_exclusive(self) -> None:
            model = KernelState()
            for tid in ("A", "B"):
                model.add(tid)
                model.admit(tid)
            trace = [
                ("dispatch-A", model.dispatch()),
                ("block-A", model.block("disk:0", "read")),
                ("dispatch-B", model.dispatch()),
                ("preempt-B", model.preempt()),
                ("wake-A", model.wake_one("disk:0")),
                ("dispatch-B-again", model.dispatch()),
                ("exit-B", model.exit_running()),
                ("dispatch-A-again", model.dispatch()),
                ("exit-A", model.exit_running()),
            ]
            self.assertEqual(
                trace,
                [
                    ("dispatch-A", "A"),
                    ("block-A", "A"),
                    ("dispatch-B", "B"),
                    ("preempt-B", "B"),
                    ("wake-A", "A"),
                    ("dispatch-B-again", "B"),
                    ("exit-B", "B"),
                    ("dispatch-A-again", "A"),
                    ("exit-A", "A"),
                ],
            )
            model.assert_invariants()
            self.assertEqual(model.tasks["A"].state, TaskState.TERMINATED)
            self.assertEqual(model.completed, ["B", "A"])

        def test_snapshot_validator_rejects_duplicate_location(self) -> None:
            snapshot = {
                "running": "A",
                "ready": ["A"],
                "wait_queues": {},
                "completed": [],
                "tasks": {"A": {"state": "running"}},
            }
            with self.assertRaisesRegex(ValueError, "실행 가능 큐"):
                KernelState.validate_snapshot(snapshot)

    class SynchronizationTests(unittest.TestCase):
        def test_generation_closes_lost_wakeup_window(self) -> None:
            channel = ConditionChannel("items")
            token = channel.prepare_wait()
            self.assertIsNone(channel.notify_one())
            self.assertFalse(channel.commit_wait("consumer", token))
            self.assertNotIn("consumer", channel.waiters)

            fresh = channel.prepare_wait()
            self.assertTrue(channel.commit_wait("consumer", fresh))
            self.assertEqual(channel.notify_all(), ["consumer"])

        def test_semaphore_hands_permit_to_waiter(self) -> None:
            semaphore = CountingSemaphore(1)
            self.assertTrue(semaphore.acquire("A"))
            self.assertFalse(semaphore.acquire("B"))
            self.assertEqual(semaphore.release("A"), "B")
            self.assertIn("B", semaphore.granted)
            self.assertIsNone(semaphore.release("B"))
            self.assertEqual(semaphore.permits, 1)
            semaphore.assert_invariants()

        def test_rejects_cross_channel_token_and_duplicate_owner(self) -> None:
            channel = ConditionChannel("items")
            with self.assertRaisesRegex(SynchronizationError, "다른 조건 채널"):
                channel.commit_wait("A", WaitToken("space", 0))
            semaphore = CountingSemaphore(1)
            self.assertTrue(semaphore.acquire("A"))
            with self.assertRaisesRegex(SynchronizationError, "중복 요청"):
                semaphore.acquire("A")

    class SchedulerTests(unittest.TestCase):
        def test_round_robin_and_metrics(self) -> None:
            jobs = [JobSpec("A", 0, (4,)), JobSpec("B", 1, (2,))]
            result = simulate(jobs, Policy.RR, quantum=2)
            self.assertEqual([tick.running for tick in result.timeline], ["A", "A", "B", "B", "A", "A"])
            self.assertEqual(result.completion_order, ("B", "A"))
            self.assertEqual(result.metrics["A"].response, 0)
            self.assertEqual(result.metrics["B"].response, 1)
            self.assertEqual(result.cpu_busy_ticks, 6)

        def test_io_wait_moves_job_out_of_ready_queue(self) -> None:
            jobs = [JobSpec("A", 0, (1, 1), (2,)), JobSpec("B", 0, (2,))]
            result = simulate(jobs, Policy.FCFS)
            self.assertEqual(result.completion_order, ("B", "A"))
            self.assertTrue(any(tid == "A" for tick in result.timeline for tid, _ in tick.blocked))

        def test_sjf_uses_current_cpu_burst(self) -> None:
            result = simulate([JobSpec("long", 0, (5,)), JobSpec("short", 0, (1,))], Policy.SJF)
            self.assertEqual(result.timeline[0].running, "short")

        def test_rejects_invalid_quantum_and_duplicate_ids(self) -> None:
            with self.assertRaisesRegex(ValueError, "퀀텀"):
                simulate([JobSpec("A", 0, (1,))], Policy.RR, quantum=0)
            with self.assertRaisesRegex(ValueError, "식별자가 중복"):
                simulate([JobSpec("A", 0, (1,)), JobSpec("A", 1, (1,))], Policy.FCFS)

    class DeadlockTests(unittest.TestCase):
        def test_cycle_and_multiple_instance_detection(self) -> None:
            cycle = find_wait_cycle({"A": ["B"], "B": ["C"], "C": ["A"]})
            self.assertIsNotNone(cycle)
            self.assertEqual(cycle[0], cycle[-1])
            self.assertEqual(
                detect_deadlocked(
                    [0, 0],
                    {"A": [1, 0], "B": [0, 1]},
                    {"A": [0, 1], "B": [1, 0]},
                ),
                {"A", "B"},
            )

        def test_safe_sequence(self) -> None:
            sequence = safe_sequence(
                [1, 1],
                {"A": [1, 0], "B": [0, 1]},
                {"A": [1, 1], "B": [1, 1]},
            )
            self.assertIsNotNone(sequence)
            self.assertEqual(set(sequence or []), {"A", "B"})

        def test_rejects_vector_shape_mismatch(self) -> None:
            with self.assertRaises(DeadlockInputError):
                detect_deadlocked([0], {"A": [1, 0]}, {"A": [0, 1]})

    class PagingTests(unittest.TestCase):
        def test_demand_zero_and_copy_on_write(self) -> None:
            memory = MemoryManager(max_frames=8)
            memory.create_process("parent")
            memory.map_demand_zero("parent", 0)
            self.assertEqual(memory.read("parent", 0), 0)
            memory.write("parent", 0, 7)
            memory.fork("parent", "child")
            self.assertEqual(memory.read("child", 0), 7)
            self.assertEqual(memory.write("child", 0, 9), FaultKind.COPY_ON_WRITE)
            self.assertEqual(memory.read("parent", 0), 7)
            self.assertEqual(memory.read("child", 0), 9)
            self.assertEqual(len(memory.frames), 2)
            memory.assert_invariants()

        def test_write_protection_fault(self) -> None:
            memory = MemoryManager()
            memory.create_process("p")
            memory.map_value("p", 1, 5, writable=False)
            with self.assertRaises(MemoryFault) as context:
                memory.write("p", 1, 6)
            self.assertEqual(context.exception.kind, FaultKind.PROTECTION)

        def test_read_only_demand_zero_write_does_not_allocate_frame(self) -> None:
            memory = MemoryManager()
            memory.create_process("p")
            memory.map_demand_zero("p", 2, writable=False)
            with self.assertRaises(MemoryFault) as context:
                memory.write("p", 2, 1)
            self.assertEqual(context.exception.kind, FaultKind.PROTECTION)
            self.assertEqual(memory.frames, {})
            self.assertFalse(memory.spaces["p"].pages[2].present)

        def test_replacement_policies_have_bounded_results(self) -> None:
            references = [1, 2, 3, 1, 4, 5]
            results = {
                policy: simulate_replacement(references, 3, policy)
                for policy in ("fifo", "lru", "clock")
            }
            self.assertEqual(results["fifo"].faults, 5)
            self.assertEqual(results["lru"].faults, 5)
            self.assertTrue(4 <= results["clock"].faults <= 6)

    class StorageTests(unittest.TestCase):
        def test_file_and_directory_durability_are_separate(self) -> None:
            filesystem = FileSystemModel()
            filesystem.create("draft", "v1")
            filesystem.fsync_file("draft")
            filesystem.crash_recover()
            self.assertNotIn("draft", filesystem.directory)

            filesystem.create("stable", "v2")
            filesystem.fsync_file("stable")
            filesystem.fsync_directory()
            filesystem.write("stable", "v3")
            filesystem.crash_recover()
            self.assertEqual(filesystem.read("stable"), "v2")

        def test_only_committed_journal_transactions_replay_once(self) -> None:
            filesystem = FileSystemModel()
            journal = Journal()
            committed = journal.begin()
            journal.append(committed, {"op": "create", "name": "a", "data": "x"})
            journal.append(committed, {"op": "fsync-file", "name": "a"})
            journal.append(committed, {"op": "fsync-directory"})
            journal.commit(committed)
            uncommitted = journal.begin()
            journal.append(uncommitted, {"op": "rename", "old": "a", "new": "b"})

            applied: set[int] = set()
            first = journal.recover(filesystem.apply_operation, already_applied=applied)
            second = journal.recover(filesystem.apply_operation, already_applied=applied)
            self.assertEqual((first, second), ([committed], []))
            self.assertIn("a", filesystem.directory)
            self.assertNotIn("b", filesystem.directory)

        def test_journal_rejects_commit_without_begin(self) -> None:
            with self.assertRaises(JournalError):
                Journal.from_snapshot([{"txid": 1, "kind": "commit", "payload": {}}])

    class DeviceTests(unittest.TestCase):
        def test_dma_pin_and_completion_lifetime(self) -> None:
            device = DeviceQueue(queue_depth=2)
            request_id = device.submit("process-A", (10, 11), 8192)
            request = device.start_next()
            self.assertEqual(request.request_id if request else None, request_id)
            self.assertTrue(device.requests[request_id].pinned)
            device.interrupt_complete(request_id, bytes_transferred=4096)
            self.assertFalse(device.requests[request_id].pinned)
            result = device.reap("process-A")
            self.assertEqual(result.state if result else None, RequestState.REAPED)
            with self.assertRaises(DeviceStateError):
                device.interrupt_complete(request_id, bytes_transferred=4096)

        def test_queued_cancel_is_reported_to_owner(self) -> None:
            device = DeviceQueue()
            request_id = device.submit("p", (1,), 512)
            self.assertEqual(device.cancel("p", request_id), RequestState.CANCELLED)
            result = device.reap("p")
            self.assertIsNotNone(result)
            self.assertEqual(result.state, RequestState.REAPED)

        def test_snapshot_rejects_active_requests_beyond_queue_depth(self) -> None:
            snapshot = {
                "queue_depth": 1,
                "pending": [1, 2],
                "in_flight": [],
                "completions": {},
                "requests": {
                    str(request_id): {
                        "owner": owner,
                        "buffer_pages": [request_id - 1],
                        "length": 1,
                        "state": "queued",
                        "pinned": False,
                    }
                    for request_id, owner in ((1, "a"), (2, "b"))
                },
            }
            with self.assertRaisesRegex(DeviceStateError, "큐 깊이"):
                DeviceQueue.validate_snapshot(snapshot)

    class FixtureAndCliTests(unittest.TestCase):
        def test_cli_fixtures_return_declared_results(self) -> None:
            specifications = (
                ("lifecycle", "lifecycle.json"),
                ("schedule", "schedule.json"),
                ("condition", "condition.json"),
                ("deadlock", "deadlock-cycle.json"),
                ("deadlock", "deadlock-safe.json"),
                ("memory", "translation.json"),
                ("replacement", "replacement.json"),
                ("filesystem", "filesystem.json"),
                ("io", "io.json"),
            )
            for model, filename in specifications:
                fixture = ROOT / "fixtures" / filename
                expected = load_json(fixture).get("expected")
                with self.subTest(model=model, fixture=filename):
                    self.assertIsInstance(expected, Mapping)
                    result = subprocess.run(
                        [sys.executable, str(target_directory / "kernel-model.py"), model, str(fixture)],
                        cwd=ROOT,
                        text=True,
                        capture_output=True,
                        timeout=5,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    assert_subset(json.loads(result.stdout), expected)

        def test_cli_reports_invalid_operation_without_traceback(self) -> None:
            with tempfile.TemporaryDirectory(prefix="guide-os-cli-") as temporary:
                fixture = Path(temporary) / "invalid.json"
                fixture.write_text('{"operations":[{"op":"unknown"}]}\n', encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(target_directory / "kernel-model.py"), "lifecycle", str(fixture)],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
            self.assertEqual(result.returncode, 1)
            self.assertIn("모델 실행 실패", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    classes: dict[str, type[unittest.TestCase]] = {
        "01-lifecycle": LifecycleTests,
        "02-synchronization": SynchronizationTests,
        "03-scheduler": SchedulerTests,
        "04-deadlock": DeadlockTests,
        "05-paging": PagingTests,
        "06-storage": StorageTests,
        "07-device-io": DeviceTests,
        "08-cli": FixtureAndCliTests,
    }
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    selected = CHECKPOINTS if checkpoint == "all" else (checkpoint,)
    for name in selected:
        suite.addTests(loader.loadTestsFromTestCase(classes[name]))
    return suite


def run_implementation(target_name: str, checkpoint: str) -> int:
    result = unittest.TextTestRunner(verbosity=2).run(implementation_suite(target_name, checkpoint))
    if not result.wasSuccessful():
        return 1
    print(f"[PASS] implementation={target_name} checkpoint={checkpoint} tests={result.testsRun}")
    return 0


def expect_not_implemented(label: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except NotImplementedError:
        return
    raise AssertionError(f"skeleton checkpoint가 NotImplementedError 경계에서 멈추지 않았습니다: {label}")


def run_skeleton() -> int:
    path = target_path("skeleton")
    python_files = sorted(path.rglob("*.py"))
    markers_by_module: dict[str, int] = {}
    for source_path in python_files:
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        markers_by_module[source_path.name] = markers_by_module.get(source_path.name, 0) + sum(
            isinstance(node, ast.Raise)
            and isinstance(node.exc, ast.Call)
            and isinstance(node.exc.func, ast.Name)
            and node.exc.func.id == "NotImplementedError"
            for node in ast.walk(tree)
        )
    required_modules = {
        "lifecycle.py",
        "synchronization.py",
        "scheduler.py",
        "deadlock.py",
        "paging.py",
        "filesystem.py",
        "journal.py",
        "device_io.py",
    }
    missing = sorted(name for name in required_modules if markers_by_module.get(name, 0) == 0)
    if missing:
        print(f"skeleton 구현 경계가 없는 module입니다: {missing}", file=sys.stderr)
        return 1

    activate(path)
    from kernel_model.deadlock import find_wait_cycle
    from kernel_model.device_io import DeviceQueue
    from kernel_model.filesystem import FileSystemModel
    from kernel_model.journal import Journal
    from kernel_model.lifecycle import KernelState
    from kernel_model.paging import simulate_replacement
    from kernel_model.scheduler import JobSpec, simulate
    from kernel_model.synchronization import ConditionChannel

    lifecycle = KernelState()
    lifecycle.add("A")
    channel = ConditionChannel("items")
    boundaries: tuple[tuple[str, Callable[[], Any]], ...] = (
        ("01-lifecycle", lambda: lifecycle.admit("A")),
        ("02-synchronization", lambda: channel.commit_wait("A", channel.prepare_wait())),
        ("03-scheduler", lambda: simulate([JobSpec("A", 0, (1,))], "fcfs")),
        ("04-deadlock", lambda: find_wait_cycle({"A": ["A"]})),
        ("05-paging", lambda: simulate_replacement([1, 2], 1, "fifo")),
        ("06-storage/filesystem", lambda: FileSystemModel().create("a")),
        ("06-storage/journal", lambda: Journal().begin()),
        ("07-device-io", lambda: DeviceQueue().submit("p", (1,), 1)),
    )
    try:
        for label, action in boundaries:
            expect_not_implemented(label, action)
    except AssertionError as error:
        print(error, file=sys.stderr)
        return 1

    cli = subprocess.run(
        [sys.executable, str(path / "kernel-model.py"), "lifecycle", str(ROOT / "fixtures/lifecycle.json")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    if cli.returncode != 1 or "모델 실행 실패" not in cli.stderr or "Traceback" in cli.stderr:
        print(f"skeleton CLI 경계가 잘못되었습니다:\n{cli.stdout}{cli.stderr}", file=sys.stderr)
        return 1
    total = sum(markers_by_module.values())
    print(f"[PASS] skeleton checkpoints=8 implementation-boundaries={total}")
    return 0


def run_failures() -> int:
    activate(target_path("reference"))
    from kernel_model.device_io import DeviceQueue
    from kernel_model.filesystem import FileSystemModel
    from kernel_model.journal import Journal
    from kernel_model.lifecycle import KernelState
    from kernel_model.paging import MemoryManager

    validators: dict[str, Callable[[Any], None]] = {
        "lifecycle": KernelState.validate_snapshot,
        "memory": MemoryManager.validate_snapshot,
        "device": DeviceQueue.validate_snapshot,
        "filesystem": FileSystemModel.validate_snapshot,
        "journal": Journal.from_snapshot,
    }
    paths = sorted((ROOT / "failure-fixtures").glob("*.json"))
    if len(paths) != 8:
        print(f"failure fixture는 정확히 8개여야 합니다: {len(paths)}", file=sys.stderr)
        return 1
    for path in paths:
        data = load_json(path)
        validator_name = str(data.get("validator"))
        expected_error = data.get("expected_error")
        if validator_name not in validators or not isinstance(expected_error, str) or not expected_error:
            print(f"failure fixture 계약이 불완전합니다: {path}", file=sys.stderr)
            return 1
        try:
            validators[validator_name](data.get("snapshot"))
        except (KeyError, TypeError, ValueError, RuntimeError) as error:
            if expected_error not in str(error):
                print(
                    f"failure fixture가 다른 이유로 거부됐습니다: {path}\n"
                    f"expected={expected_error!r}\nactual={str(error)!r}",
                    file=sys.stderr,
                )
                return 1
        else:
            print(f"잘못된 상태를 거부하지 못했습니다: {path}", file=sys.stderr)
            return 1
    print(f"[PASS] failure fixtures={len(paths)} exact-error-contracts")
    return 0


def run_bounded(arguments: list[str]) -> int:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), *arguments],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=timeout_seconds(),
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout.decode(errors="replace") if isinstance(error.stdout, bytes) else error.stdout or ""
        stderr = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr or ""
        print(stdout, end="")
        print(stderr, end="", file=sys.stderr)
        print(f"TIMEOUT: kernel-model checker: {' '.join(arguments)}", file=sys.stderr)
        return 124
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def usage() -> int:
    print(
        "사용법: check.py reference [checkpoint] | skeleton | failure | all | "
        "implementation <directory> [checkpoint]",
        file=sys.stderr,
    )
    print(f"checkpoints: {', '.join(CHECKPOINTS)}, all", file=sys.stderr)
    return 2


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "__implementation":
        return run_implementation(argv[2], argv[3]) if len(argv) == 4 else usage()
    if argv[1:] == ["__skeleton"]:
        return run_skeleton()
    if argv[1:] == ["__failure"]:
        return run_failures()
    if len(argv) in {2, 3} and argv[1] == "reference":
        checkpoint = argv[2] if len(argv) == 3 else "all"
        return run_bounded(["__implementation", "reference", checkpoint])
    if len(argv) in {3, 4} and argv[1] == "implementation":
        checkpoint = argv[3] if len(argv) == 4 else "all"
        return run_bounded(["__implementation", argv[2], checkpoint])
    if argv[1:] == ["skeleton"]:
        return run_bounded(["__skeleton"])
    if argv[1:] == ["failure"]:
        return run_bounded(["__failure"])
    if argv[1:] == ["all"]:
        statuses = [main([argv[0], item]) for item in ("skeleton", "reference", "failure")]
        return 0 if all(status == 0 for status in statuses) else 1
    return usage()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
