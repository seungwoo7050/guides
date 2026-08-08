#!/usr/bin/env python3
"""Validate the structured diagnosis contract for the Unix investigation lab."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

EXPECTED: dict[str, dict[str, Any]] = {
    "01-command-resolution": {
        "layer": "execution-context",
        "primary_cause": "path-precedence",
        "safe_fix": "select-trusted-executable",
        "command_groups": [("command -v", "type -a"), ("path",)],
        "evidence_groups": [("path",), ("stale", "오래된"), ("42",)],
    },
    "02-dangling-symlink": {
        "layer": "filesystem-path",
        "primary_cause": "dangling-symlink",
        "safe_fix": "atomically-repoint-link",
        "command_groups": [("readlink",), ("ls -ld", "test -e")],
        "evidence_groups": [("current",), ("링크", "symlink"), ("대상", "target")],
    },
    "03-waiting-for-input": {
        "layer": "process-io",
        "primary_cause": "waiting-for-input",
        "safe_fix": "provide-or-close-input",
        "command_groups": [("ps ",), ("lsof", "fifo")],
        "evidence_groups": [("reader",), ("fifo",), ("입력", "input", "eof")],
    },
    "04-deleted-open-file": {
        "layer": "file-descriptor-lifetime",
        "primary_cause": "unlinked-open-file",
        "safe_fix": "close-or-reopen-owner",
        "command_groups": [("lsof", "/proc/"), ("test ! -e", "ls ")],
        "evidence_groups": [("경로", "path"), ("fd", "열린"), ("writer", "프로세스")],
    },
    "05-working-directory": {
        "layer": "execution-context",
        "primary_cause": "working-directory-mismatch",
        "safe_fix": "use-explicit-config-or-cwd",
        "command_groups": [("pwd",), ("lsof", "ps ")],
        "evidence_groups": [("config",), ("상대", "relative"), ("디렉터리", "cwd")],
    },
    "06-address-family-mismatch": {
        "layer": "network-endpoint",
        "primary_cause": "address-family-mismatch",
        "safe_fix": "match-bind-and-client-family",
        "command_groups": [("getaddrinfo", "localhost"), ("ss ", "lsof"), ("127.0.0.1", "::1")],
        "evidence_groups": [("ipv4", "127.0.0.1"), ("ipv6", "::1"), ("listen", "리스너")],
    },
    "07-running-not-ready": {
        "layer": "service-readiness",
        "primary_cause": "dependency-not-ready",
        "safe_fix": "satisfy-readiness-dependency",
        "command_groups": [("ps ",), ("health",), ("ss ", "lsof")],
        "evidence_groups": [("프로세스", "process"), ("503",), ("dependency", "의존")],
    },
    "08-signal-not-forwarded": {
        "layer": "process-ownership",
        "primary_cause": "signal-not-forwarded",
        "safe_fix": "exec-or-forward-and-wait",
        "command_groups": [("ps ",), ("term", "signal", "시그널")],
        "evidence_groups": [("wrapper",), ("worker", "child"), ("term", "시그널")],
    },
    "09-reserved-not-resident": {
        "layer": "memory-observation",
        "primary_cause": "virtual-reservation-not-resident",
        "safe_fix": "measure-residency-before-action",
        "command_groups": [("vsz", "virtual"), ("rss", "resident"), ("/proc/", "vmmap", "ps ")],
        "evidence_groups": [("virtual", "vsz"), ("rss", "상주"), ("예약", "mapping")],
    },
}

UNSAFE_COMMAND_FRAGMENTS = (
    "sudo ",
    "chmod 777",
    "chmod -r 777",
    "rm -rf /",
    "kill -9 -1",
    "reinstall everything",
)


def text_contains_any(text: str, alternatives: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(item.casefold() in lowered for item in alternatives)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"파일이 없습니다: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 문법 오류: {path}:{exc.lineno}:{exc.colno}: {exc.msg}") from None


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = load_json(path)
    except ValueError as exc:
        return [str(exc)]

    if not isinstance(data, dict):
        return ["최상위 JSON 값은 object여야 합니다."]
    if data.get("schema_version") != 1:
        errors.append("schema_version은 1이어야 합니다.")

    cases = data.get("cases")
    if not isinstance(cases, dict):
        return errors + ["cases는 object여야 합니다."]

    expected_ids = set(EXPECTED)
    actual_ids = set(cases)
    missing = sorted(expected_ids - actual_ids)
    extra = sorted(actual_ids - expected_ids)
    if missing:
        errors.append("누락된 사례: " + ", ".join(missing))
    if extra:
        errors.append("알 수 없는 사례: " + ", ".join(extra))

    for case_id in sorted(expected_ids & actual_ids):
        prefix = f"{case_id}: "
        answer = cases[case_id]
        spec = EXPECTED[case_id]
        if not isinstance(answer, dict):
            errors.append(prefix + "답은 object여야 합니다.")
            continue

        for field in ("layer", "primary_cause", "safe_fix"):
            value = answer.get(field)
            if value != spec[field]:
                errors.append(prefix + f"{field}는 {spec[field]!r}이어야 합니다.")

        commands = answer.get("observation_commands")
        if not isinstance(commands, list) or len(commands) < 2 or not all(isinstance(v, str) and v.strip() for v in commands):
            errors.append(prefix + "observation_commands에는 비어 있지 않은 읽기 전용 명령이 두 개 이상 필요합니다.")
            command_text = ""
        else:
            command_text = "\n".join(commands).casefold()
            for fragment in UNSAFE_COMMAND_FRAGMENTS:
                if fragment.casefold() in command_text:
                    errors.append(prefix + f"관찰 단계에 위험하거나 상태를 크게 바꾸는 명령이 있습니다: {fragment}")
            for group in spec["command_groups"]:
                if not text_contains_any(command_text, group):
                    errors.append(prefix + "관찰 명령에 필요한 근거 종류가 빠졌습니다: " + " / ".join(group))

        evidence = answer.get("expected_evidence")
        if not isinstance(evidence, str) or len(evidence.strip()) < 40 or "TODO" in evidence.upper():
            errors.append(prefix + "expected_evidence에는 40자 이상의 구체적인 예상 근거가 필요합니다.")
        else:
            for group in spec["evidence_groups"]:
                if not text_contains_any(evidence, group):
                    errors.append(prefix + "예상 근거에 핵심 상태가 빠졌습니다: " + " / ".join(group))

        regressions = answer.get("regression_checks")
        if not isinstance(regressions, list) or len(regressions) < 2 or not all(
            isinstance(v, str) and len(v.strip()) >= 15 and "TODO" not in v.upper() for v in regressions
        ):
            errors.append(prefix + "regression_checks에는 구체적인 검사 두 개 이상이 필요합니다.")

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"사용법: {Path(argv[0]).name} ANSWERS.json", file=sys.stderr)
        return 2
    path = Path(argv[1])
    errors = validate(path)
    if errors:
        print(f"FAIL {path}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"PASS {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
