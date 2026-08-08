#!/usr/bin/env python3
"""Validate the one intentional failure for each learner skeleton."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Contract:
    module: str
    classname: str
    method: str
    outcome: str
    exception_type: str
    messages: tuple[str, ...]
    first_guide_frame: str


CONTRACTS = {
    "application-boundaries": Contract(
        "application-boundaries",
        "dev.guides.spring.boundaries.PreviewControllerTest",
        "rejectsBusinessPolicyAsConflict",
        "failure",
        "java.lang.AssertionError",
        ("Status expected:<409> but was:<200>",),
        "dev.guides.spring.boundaries.PreviewControllerTest.rejectsBusinessPolicyAsConflict",
    ),
    "security-boundaries": Contract(
        "security-boundaries",
        "dev.guides.spring.security.SecurityBoundaryTest",
        "authenticationIsRequired",
        "failure",
        "java.lang.AssertionError",
        ("Status expected:<401> but was:<200>",),
        "dev.guides.spring.security.SecurityBoundaryTest.authenticationIsRequired",
    ),
    "transaction-locking": Contract(
        "transaction-locking",
        "dev.guides.spring.locking.InventoryConcurrencyIntegrationTest",
        "exactlyTenOfTwentyConcurrentDebitsSucceed",
        "failure",
        "org.opentest4j.AssertionFailedError",
        ("expected: 10", "but was: 20"),
        "dev.guides.spring.locking.InventoryConcurrencyIntegrationTest.exactlyTenOfTwentyConcurrentDebitsSucceed",
    ),
    "idempotency-outbox": Contract(
        "idempotency-outbox",
        "dev.guides.spring.idempotency.IdempotencyIntegrationTest",
        "concurrentSameKeyCreatesOneOperationWhenRedisFails",
        "error",
        "java.util.concurrent.ExecutionException",
        (
            "org.springframework.dao.DataIntegrityViolationException",
            'duplicate key value violates unique constraint "operation_record_pkey"',
        ),
        "dev.guides.spring.idempotency.IdempotencyIntegrationTest.concurrentSameKeyCreatesOneOperationWhenRedisFails",
    ),
    "kafka-avro-contract": Contract(
        "kafka-avro-contract",
        "dev.guides.spring.kafkaavro.KafkaAvroContractIntegrationTest",
        "preservesPartitionKeyAndAvroFields",
        "failure",
        "java.lang.AssertionError",
        ("Expecting actual not to be null",),
        "dev.guides.spring.kafkaavro.KafkaAvroContractIntegrationTest.preservesPartitionKeyAndAvroFields",
    ),
    "resilient-http-client": Contract(
        "resilient-http-client",
        "dev.guides.spring.failclosed.DecisionClientIntegrationTest",
        "retryBudgetReusesTheSameRequestIdentifier",
        "error",
        "dev.guides.spring.failclosed.DependencyUnavailableException",
        ("외부 시스템을 사용할 수 없습니다.",),
        "dev.guides.spring.failclosed.DecisionClient.check",
    ),
    "single-service-capstone": Contract(
        "single-service-capstone",
        "dev.guides.spring.capstone.PublicationServiceIntegrationTest",
        "creationWritesPublicationOutboxCacheAndMetric",
        "failure",
        "org.opentest4j.AssertionFailedError",
        ("expected: 1L", "but was: 0L"),
        "dev.guides.spring.capstone.PublicationServiceIntegrationTest.creationWritesPublicationOutboxCacheAndMetric",
    ),
}


def reject(message: str) -> None:
    raise SystemExit(f"skeleton 지정 실패 보고서가 다릅니다: {message}")


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in CONTRACTS:
        reject("사용법: check-skeleton-report.py CONTRACT REPOSITORY_ROOT")
    contract = CONTRACTS[sys.argv[1]]
    root = Path(sys.argv[2]).resolve()
    report = (
        root
        / "exercises"
        / contract.module
        / "skeleton/target/surefire-reports"
        / f"TEST-{contract.classname}.xml"
    )
    if not report.is_file():
        reject(f"Surefire XML이 없습니다: {report}")

    suite = ET.parse(report).getroot()
    expected_counts = {
        "tests": "1",
        "failures": "1" if contract.outcome == "failure" else "0",
        "errors": "1" if contract.outcome == "error" else "0",
        "skipped": "0",
    }
    if any(suite.get(key) != value for key, value in expected_counts.items()):
        reject(f"suite 집계가 다릅니다: {suite.attrib}")

    cases = suite.findall("testcase")
    if len(cases) != 1:
        reject(f"testcase 수가 1이 아닙니다: {len(cases)}")
    case = cases[0]
    if case.get("classname") != contract.classname or case.get("name") != contract.method:
        reject(f"test mapping이 다릅니다: {case.attrib}")
    outcome = case.find(contract.outcome)
    other = case.find("error" if contract.outcome == "failure" else "failure")
    if outcome is None or other is not None:
        reject(f"{contract.outcome} outcome이 정확히 하나가 아닙니다.")
    if outcome.get("type") != contract.exception_type:
        reject(
            f"예외 종류가 다릅니다: 예상={contract.exception_type}, "
            f"실제={outcome.get('type')}"
        )
    detail = "\n".join((outcome.get("message") or "", outcome.text or ""))
    for message in contract.messages:
        if message not in detail:
            reject(f"지정 메시지가 없습니다: {message}")

    guide_frames = []
    for line in (outcome.text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("at dev.guides.spring."):
            guide_frames.append(stripped.removeprefix("at ").split("(", 1)[0])
    if not guide_frames or guide_frames[0] != contract.first_guide_frame:
        reject(
            "첫 guide frame이 지정 실패 위치가 아닙니다: "
            f"예상={contract.first_guide_frame}, 실제={guide_frames[:1]}"
        )

    print(
        f"[PASS] {sys.argv[1]} Surefire 지정 실패: "
        f"{contract.classname}#{contract.method} -> "
        f"{contract.exception_type}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
