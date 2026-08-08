#!/usr/bin/env python3
"""The answer checker must reject fifteen independent known-bad answers."""

from __future__ import annotations

import copy
from contextlib import redirect_stdout
import importlib.util
import io
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
EXERCISE = ROOT / "exercises/system-investigation"
REFERENCE = EXERCISE / "reference/diagnoses.json"
spec = importlib.util.spec_from_file_location("check_answers", EXERCISE / "check_answers.py")
if spec is None or spec.loader is None:
    raise RuntimeError("check_answers.py를 불러오지 못했습니다.")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@dataclass(frozen=True)
class Mutant:
    name: str
    expected: str
    apply: Callable[[dict], None]


def first(data: dict) -> dict:
    return data["cases"][sorted(data["cases"])[0]]


def missing_case(data: dict) -> None:
    del data["cases"][sorted(data["cases"])[0]]


def wrong_layer(data: dict) -> None:
    first(data)["layer"] = "unknown-layer"


def unsafe_command(data: dict) -> None:
    first(data)["observation_commands"].append("sudo rm -rf /tmp/example")


def vague_evidence(data: dict) -> None:
    first(data)["expected_evidence"] = "근거 없음"


def one_regression(data: dict) -> None:
    first(data)["regression_checks"] = ["한 번만 확인하는 불충분한 회귀 검사입니다."]


def no_op_observations(data: dict) -> None:
    first(data)["observation_commands"] = [
        "printf 'command -v unix-guide-tool'",
        "echo 'PATH stale 42'",
    ]


def wrong_evidence_fact(data: dict) -> None:
    first(data)["evidence_facts"][0] = "cpu-temperature-selected-the-executable"


def generic_regression_target(data: dict) -> None:
    first(data)["regression_targets"][0] = "run-it-once"


def allowed_form_keyword_soup(data: dict) -> None:
    answer = first(data)
    answer["observation_commands"] = ["command -v PATH", "type -a PATH"]
    answer["expected_evidence"] = (
        "PATH와 stale 및 42라는 단어는 있지만 실제 원인은 CPU 온도라는 잘못된 결론을 적은 문장이다."
    )
    answer["regression_checks"] = [
        "아무 명령이나 실행하고 충분히 오래 기다리기만 한다.",
        "화면이 조용하면 근거 없이 정상이라고 표시한다.",
    ]


def mutating_ss(data: dict) -> None:
    data["cases"]["06-address-family-mismatch"]["observation_commands"][1] = "ss -K dst 127.0.0.1"


def mutating_curl(data: dict) -> None:
    data["cases"]["07-running-not-ready"]["observation_commands"][-1] = (
        "curl --request=POST http://127.0.0.1:PORT/health"
    )


def mutating_python(data: dict) -> None:
    data["cases"]["06-address-family-mismatch"]["observation_commands"][0] = (
        "python3 -c 'import socket, pathlib; print(socket.getaddrinfo(\"localhost\", 0)); "
        "pathlib.Path(\"changed\").write_bytes(b\"x\")'"
    )


def curl_loopback_subdomain(data: dict) -> None:
    data["cases"]["07-running-not-ready"]["observation_commands"][-1] = (
        "curl -i http://localhost.evil.example/health"
    )


def curl_loopback_userinfo(data: dict) -> None:
    data["cases"]["07-running-not-ready"]["observation_commands"][-1] = (
        "curl -i http://127.0.0.1@evil.example/health"
    )


def curl_loopback_query_decoy(data: dict) -> None:
    data["cases"]["07-running-not-ready"]["observation_commands"][-1] = (
        "curl -i http://evil.example/health?next=localhost"
    )


MUTANTS = (
    Mutant("missing case", "누락된 사례", missing_case),
    Mutant("wrong layer", "layer는", wrong_layer),
    Mutant("unsafe observation", "위험하거나", unsafe_command),
    Mutant("vague evidence", "40자 이상", vague_evidence),
    Mutant("single regression", "두 개 이상", one_regression),
    Mutant("no-op observations", "허용된 읽기 전용", no_op_observations),
    Mutant("wrong evidence fact", "evidence_facts가", wrong_evidence_fact),
    Mutant("generic regression target", "regression_targets가", generic_regression_target),
    Mutant("allowed-form keyword soup", "실제 상태 질문", allowed_form_keyword_soup),
    Mutant("mutating ss", "listener·connection", mutating_ss),
    Mutant("mutating curl", "옵션 없는 GET", mutating_curl),
    Mutant("mutating Python", "세 가지 loopback", mutating_python),
    Mutant("curl loopback subdomain", "loopback endpoint", curl_loopback_subdomain),
    Mutant("curl loopback userinfo", "userinfo", curl_loopback_userinfo),
    Mutant("curl loopback query decoy", "loopback endpoint", curl_loopback_query_decoy),
)


def main() -> int:
    baseline = json.loads(REFERENCE.read_text(encoding="utf-8"))
    if module.validate(REFERENCE):
        print("FAIL answer validator baseline")
        return 1
    output = io.StringIO()
    with redirect_stdout(output):
        result = module.main(["check_answers.py", str(REFERENCE)])
    if result != 0 or "STRUCTURE PASS" not in output.getvalue() or "SEMANTIC REVIEW REQUIRED" not in output.getvalue():
        print("FAIL answer validator가 자동·수동 검수 경계를 표시하지 않습니다.")
        return 1
    with tempfile.TemporaryDirectory(prefix="unix-answer-mutants-") as directory:
        for index, mutant in enumerate(MUTANTS, 1):
            data = copy.deepcopy(baseline)
            mutant.apply(data)
            path = Path(directory) / f"mutant-{index}.json"
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            errors = module.validate(path)
            if not errors or not any(mutant.expected in message for message in errors):
                print(f"FAIL mutant survived or failed unexpectedly: {mutant.name}: {errors}")
                return 1
            print(f"PASS answer mutant rejected: {mutant.name}")
    print(f"ANSWER MUTANTS: PASS ({len(MUTANTS)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
