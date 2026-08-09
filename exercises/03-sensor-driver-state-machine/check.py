#!/usr/bin/env python3
"""Behavior checker for exercise 3.

Exit 0 means the submitted public contract passed, 1 means it was evaluated
and rejected, and 2 means the checker could not start (bad path/fixture/usage).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lab_support import (  # noqa: E402
    REG_STATUS,
    STATUS_DATA_READY,
    FakeSensorBus,
)


class ContractFailure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractFailure(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read {path}: {error}") from error


def load_driver(submission: Path):
    driver_path = submission / "driver.py"
    if not submission.is_dir() or not driver_path.is_file():
        raise RuntimeError("--submission must contain driver.py")
    spec = importlib.util.spec_from_file_location(f"exercise3_submission_{id(submission)}", driver_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {driver_path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:  # submission import is a contract failure
        raise ContractFailure(f"driver.py import failed: {type(error).__name__}: {error}") from error
    if not hasattr(module, "SensorDriver"):
        raise ContractFailure("driver.py must export SensorDriver")
    return module.SensorDriver


def check_generated_config(submission: Path) -> None:
    devicetree = load_json(submission / "generated-config" / "devicetree.json")
    kconfig = load_json(submission / "generated-config" / "kconfig.json")
    node = devicetree.get("nodes", {}).get("sensor0", {})
    require(node.get("status") == "okay", "sensor0 must be enabled")
    require(isinstance(node.get("bus"), str) and node["bus"], "generated bus evidence is missing")
    require(isinstance(node.get("address"), int), "generated address/chip-select evidence is missing")
    for key in ("interrupt", "power"):
        gpio = node.get(key, {})
        require(isinstance(gpio.get("controller"), str), f"{key} GPIO controller is missing")
        require(isinstance(gpio.get("pin"), int), f"{key} GPIO pin is missing")
        require(isinstance(gpio.get("flags"), str), f"{key} GPIO flags are missing")
    require(kconfig.get("CONFIG_SENSOR_DRIVER") is True, "driver Kconfig is not enabled")
    require(kconfig.get("CONFIG_SENSOR_TRIGGER_MODE") in {"interrupt", "poll"}, "trigger mode is invalid")
    require(isinstance(kconfig.get("CONFIG_SENSOR_EVENT_QUEUE_SIZE"), int), "queue capacity is missing")
    require(kconfig["CONFIG_SENSOR_EVENT_QUEUE_SIZE"] > 0, "queue capacity must be bounded and positive")
    require(isinstance(kconfig.get("CONFIG_SENSOR_DMA"), bool), "DMA selection evidence is missing")


DEFAULT_CONFIG = {"reset_timeout": 5, "mode": 3, "threshold": 9}


def make_driver(driver_type, fixture):
    bus = FakeSensorBus(**fixture["bus"])
    driver = driver_type(bus, **fixture.get("driver", {}))
    return bus, driver


def init_ready(driver) -> None:
    result = driver.initialize(DEFAULT_CONFIG, now=0)
    require(result.get("status") == "READY", f"initialization did not reach READY: {result!r}")


def assert_w1c(bus: FakeSensorBus) -> None:
    require(bus.registers[REG_STATUS] & STATUS_DATA_READY == 0, "data-ready status was not acknowledged")
    require(
        any(entry.get("semantic") == "W1C" and entry.get("value") == STATUS_DATA_READY for entry in bus.log),
        "status acknowledgement did not preserve W1C semantics",
    )


def run_fixture(driver_type, fixture: dict[str, Any]) -> None:
    bus, driver = make_driver(driver_type, fixture)
    scenario = fixture["scenario"]
    request = fixture.get("request", {})

    if scenario == "wrong_identity":
        result = driver.initialize(DEFAULT_CONFIG, now=0)
        require(result.get("class") == "identity" and driver.state == "FAULT", "wrong identity was accepted")
        return
    if scenario == "reset_timeout":
        result = driver.initialize(DEFAULT_CONFIG, now=0)
        require(result.get("raw") == "RESET_TIMEOUT" and driver.state == "FAULT", "reset timeout was hidden")
        return
    if scenario == "configuration_fault":
        result = driver.initialize(DEFAULT_CONFIG, now=0)
        require(result.get("class") == "transport", "configuration bus failure lost its class")
        require(result.get("configuration") == "UNKNOWN" and driver.state == "FAULT", "partial config claimed rollback")
        return

    init_ready(driver)
    if scenario in {"normal", "dma", "exact_deadline"}:
        generation = driver.start_sample(now=request["start"], deadline=request["deadline"])
        ready_at = request.get("ready", request["deadline"])
        bus.raise_data_ready(generation=generation, sample=request["sample"])
        status = driver.on_data_ready(generation, now=ready_at)
        if scenario == "dma":
            require(status == "DMA_PENDING", "DMA receive was not left pending")
            buffer = driver.dma_buffer(generation)
            require(buffer is not None and buffer.owner == "DMA", "DMA did not own the buffer during transfer")
            status = driver.on_dma_complete(generation, now=request["complete"])
            require(status == "COMPLETE", "DMA completion did not finish the request")
            require(buffer.owner == "CPU" and buffer.cpu_visible, "DMA buffer was not reacquired by CPU")
            require(buffer.pre_dma_invalidations == 1 and buffer.post_dma_invalidations == 1, "cache handoff is incomplete")
        else:
            require(status == "COMPLETE", "ready sample did not complete")
        result = driver.result(generation)
        require(result and result.get("status") == "OK", "successful request has no terminal result")
        require(result.get("sample") == request["sample"], "sample payload changed")
        require(result.get("unit") == "raw16" and result.get("valid") is True, "sample metadata is incomplete")
        assert_w1c(bus)
        return

    if scenario == "timeout_late":
        generation = driver.start_sample(now=request["start"], deadline=request["deadline"])
        require(driver.poll(now=request["poll"]) == "TIMEOUT", "expired request did not time out")
        bus.raise_data_ready(generation=generation, sample=request["sample"])
        require(driver.on_data_ready(generation, now=request["ready"]) == "STALE", "late event was accepted")
        require(driver.result(generation).get("status") == "TIMEOUT", "late event rewrote terminal result")
        assert_w1c(bus)
        return

    if scenario == "cancel_stale":
        first = driver.start_sample(now=2, deadline=10)
        require(driver.cancel(first, now=3) == "CANCELLED", "cancel did not terminate first request")
        second = driver.start_sample(now=4, deadline=12)
        bus.raise_data_ready(generation=first, sample=request["first_sample"])
        require(driver.on_data_ready(first, now=5) == "STALE", "cancelled generation completed current request")
        require(driver.snapshot().get("active_generation") == second, "stale event changed current generation")
        require(driver.result(second) is None, "stale payload produced a result for the current request")
        bus.raise_data_ready(generation=second, sample=request["second_sample"])
        require(driver.on_data_ready(second, now=6) == "COMPLETE", "current generation did not complete")
        require(driver.result(second).get("sample") == request["second_sample"], "current result used stale payload")
        return

    if scenario == "suspend_resume":
        generation = driver.start_sample(now=2, deadline=10)
        require(driver.suspend(now=3) == "SUSPENDED", "suspend state is missing")
        require(driver.result(generation).get("status") == "CANCELLED", "suspend did not terminate in-flight work")
        require(driver.resume() == "REINITIALIZE" and driver.state == "UNBOUND", "resume assumed register retention")
        return
    raise RuntimeError(f"unknown fixture scenario: {scenario}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    submission = Path(args.submission).resolve()
    report: dict[str, Any] = {"exercise": "03-sensor-driver-state-machine", "submission": str(submission), "checks": []}

    try:
        if not submission.is_dir() or not (submission / "driver.py").is_file():
            raise RuntimeError("--submission must name a directory containing driver.py")
        fixture_paths = sorted((ROOT / "fixtures").glob("*.json"))
        if not fixture_paths:
            raise RuntimeError("checker fixtures are missing")
        fixtures = [load_json(path) for path in fixture_paths]
    except RuntimeError as error:
        report.update(status="ERROR", error=str(error))
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.as_json else f"ERROR: {error}")
        return 2

    failures = 0
    try:
        driver_type = load_driver(submission)
    except ContractFailure as error:
        report["checks"].append({"name": "load", "status": "FAIL", "detail": str(error)})
        driver_type = None
        failures += 1

    if driver_type is not None:
        checks = [("generated-config", lambda: check_generated_config(submission))]
        checks.extend((fixture["name"], lambda item=fixture: run_fixture(driver_type, item)) for fixture in fixtures)
        for name, check in checks:
            try:
                check()
            except Exception as error:
                failures += 1
                report["checks"].append(
                    {"name": name, "status": "FAIL", "detail": f"{type(error).__name__}: {error}"}
                )
            else:
                report["checks"].append({"name": name, "status": "PASS"})

    report["status"] = "PASS" if failures == 0 else "FAIL"
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["checks"]:
            detail = f" - {item['detail']}" if "detail" in item else ""
            print(f"{item['status']:4} {item['name']}{detail}")
        print(f"CHECK {report['status']}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
