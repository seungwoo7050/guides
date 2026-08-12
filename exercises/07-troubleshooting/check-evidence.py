#!/usr/bin/env python3
"""장애 조사 기록의 구조를 검사하며 learner 명령은 실행하지 않습니다."""
from __future__ import annotations

import re
import sys
from pathlib import Path


SCENARIOS = (
    "wrong-db-host",
    "wrong-db-password",
    "missing-secret",
    "wrong-fcgi-port",
    "broken-healthcheck",
    "data-loss",
)
FIELDS = (
    "최초 실패 구성요소",
    "관찰 명령",
    "핵심 출력",
    "2차 증상",
    "수정·복구 결정",
    "구성요소 재검증",
    "외부 사용자 경로 재검증",
    "데이터 상태 재검증",
)
PLACEHOLDERS = {"", "<작성>", "TODO", "TBD"}
DANGEROUS_OBSERVATION = re.compile(
    r"(?:^|[;&|]\s*)(?:sudo\s+)?(?:rm|rmdir|truncate|kill|pkill|reboot|shutdown)\b|"
    r"docker\s+(?:system\s+prune|volume\s+rm)|docker\s+compose\s+down\s+-v",
    re.IGNORECASE,
)


class EvidenceError(ValueError):
    """증거 문서가 자동 검사 가능한 구조를 만족하지 않습니다."""


def _section(text: str, scenario: str) -> str:
    match = re.search(
        rf"(?ms)^## {re.escape(scenario)}\s*\n(.*?)(?=^## |\Z)", text
    )
    if match is None:
        raise EvidenceError(f"시나리오 절이 없습니다: {scenario}")
    return match.group(1)


def validate(text: str, *, allow_placeholders: bool = False) -> None:
    for scenario in SCENARIOS:
        body = _section(text, scenario)
        values: dict[str, str] = {}
        for field in FIELDS:
            match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.+)$", body)
            if match is None:
                raise EvidenceError(f"{scenario}에 필드가 없습니다: {field}")
            value = match.group(1).strip()
            if not allow_placeholders and (value in PLACEHOLDERS or "<작성>" in value):
                raise EvidenceError(f"{scenario}의 필드를 직접 작성하세요: {field}")
            values[field] = value

        if allow_placeholders:
            continue
        command = values["관찰 명령"].strip("`")
        if not values["관찰 명령"].startswith("`") or not values["관찰 명령"].endswith("`"):
            raise EvidenceError(f"{scenario}의 관찰 명령은 backtick으로 구분하세요.")
        if DANGEROUS_OBSERVATION.search(command):
            raise EvidenceError(f"{scenario}의 관찰 명령은 상태를 변경하면 안 됩니다.")


def _complete_fixture() -> str:
    sections = ["# synthetic evidence"]
    for scenario in SCENARIOS:
        sections.extend(
            [
                f"## {scenario}",
                "- 최초 실패 구성요소: application boundary",
                "- 관찰 명령: `docker compose ps`",
                "- 핵심 출력: application container exited with status 1",
                "- 2차 증상: gateway returned an upstream error",
                "- 수정·복구 결정: configuration candidate was reverted",
                "- 구성요소 재검증: container and dependency checks passed",
                "- 외부 사용자 경로 재검증: verified HTTPS request passed",
                "- 데이터 상태 재검증: stored record remained readable",
            ]
        )
    return "\n\n".join(sections) + "\n"


def self_test() -> None:
    good = _complete_fixture()
    validate(good)
    mutations = (
        good.replace("## data-loss", "## omitted-data-loss", 1),
        good.replace("application boundary", "<작성>", 1),
        good.replace("`docker compose ps`", "`docker system prune`", 1),
    )
    for mutation in mutations:
        try:
            validate(mutation)
        except EvidenceError:
            continue
        raise AssertionError("known-bad evidence를 거부하지 못했습니다.")


def validate_template(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    validate(text, allow_placeholders=True)
    for scenario in SCENARIOS:
        body = _section(text, scenario)
        for field in FIELDS:
            match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.+)$", body)
            assert match is not None
            if "<작성>" not in match.group(1):
                raise EvidenceError(
                    f"template은 learner placeholder를 유지해야 합니다: {scenario}.{field}"
                )


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        print("증거 검사기 self-test 통과: missing section, placeholder, destructive command")
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "--template":
        try:
            validate_template(Path(sys.argv[2]))
        except (OSError, UnicodeError, EvidenceError) as error:
            print(f"증거 template 검사 실패: {error}", file=sys.stderr)
            return 1
        print("증거 template 구조 검사 통과")
        return 0
    if len(sys.argv) != 2:
        print("사용법: check-evidence.py PATH, --template PATH 또는 --self-test", file=sys.stderr)
        return 2
    try:
        validate(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, EvidenceError) as error:
        print(f"증거 검사 실패: {error}", file=sys.stderr)
        return 1
    print("증거 구조 검사 통과; 인과관계는 수동 검토가 필요합니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
