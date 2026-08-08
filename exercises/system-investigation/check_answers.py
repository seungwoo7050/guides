#!/usr/bin/env python3
"""Validate the structured diagnosis contract for the Unix investigation lab."""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

EXPECTED: dict[str, dict[str, Any]] = {
    "01-command-resolution": {
        "layer": "execution-context",
        "primary_cause": "path-precedence",
        "safe_fix": "select-trusted-executable",
        "command_groups": [("command -v", "type -a"), ("path",)],
        "command_kinds": [("tool-resolution",), ("path-order",)],
        "evidence_groups": [("path",), ("stale", "오래된"), ("42",)],
        "evidence_facts": [
            "selected-executable-is-stale-bin",
            "trusted-candidate-is-later-in-path",
            "stale-exit-status-is-42",
        ],
        "regression_targets": [
            "fresh-shell-selects-trusted-bin",
            "trusted-tool-prints-ready-and-exits-zero",
        ],
    },
    "02-dangling-symlink": {
        "layer": "filesystem-path",
        "primary_cause": "dangling-symlink",
        "safe_fix": "atomically-repoint-link",
        "command_groups": [("readlink",), ("ls -ld", "test -e")],
        "command_kinds": [("link-target",), ("link-object",)],
        "evidence_groups": [("current",), ("링크", "symlink"), ("대상", "target")],
        "evidence_facts": ["current-is-symlink", "current-target-is-missing", "valid-release-remains-present"],
        "regression_targets": ["atomic-repoint-makes-config-readable", "existing-release-content-unchanged"],
    },
    "03-waiting-for-input": {
        "layer": "process-io",
        "primary_cause": "waiting-for-input",
        "safe_fix": "provide-or-close-input",
        "command_groups": [("ps ",), ("lsof", "fifo")],
        "command_kinds": [("process-status",), ("open-file-owner", "fifo-object")],
        "evidence_groups": [("reader",), ("fifo",), ("입력", "input", "eof")],
        "evidence_facts": ["reader-process-remains-alive", "reader-is-blocked-on-fifo", "holder-prevents-eof"],
        "regression_targets": ["valid-input-produces-output-and-exit", "reader-and-holder-are-gone-after-cleanup"],
    },
    "04-deleted-open-file": {
        "layer": "file-descriptor-lifetime",
        "primary_cause": "unlinked-open-file",
        "safe_fix": "close-or-reopen-owner",
        "command_groups": [("lsof", "/proc/"), ("test ! -e", "ls ")],
        "command_kinds": [("open-file-owner", "proc-fd"), ("missing-path",)],
        "evidence_groups": [("경로", "path"), ("fd", "열린"), ("writer", "프로세스")],
        "evidence_facts": ["log-path-is-unlinked", "writer-holds-open-fd", "object-lives-until-last-close"],
        "regression_targets": ["closing-owner-removes-open-deleted-fd", "reopened-log-path-grows"],
    },
    "05-working-directory": {
        "layer": "execution-context",
        "primary_cause": "working-directory-mismatch",
        "safe_fix": "use-explicit-config-or-cwd",
        "command_groups": [("pwd",), ("lsof", "ps ")],
        "command_kinds": [("cwd-shell",), ("process-cwd", "process-status")],
        "evidence_groups": [("config",), ("상대", "relative"), ("디렉터리", "cwd")],
        "evidence_facts": ["configured-path-is-relative", "wrong-cwd-lacks-config", "app-cwd-has-config"],
        "regression_targets": [
            "supervised-and-manual-runs-use-same-explicit-context",
            "missing-config-fails-nonzero",
        ],
    },
    "06-address-family-mismatch": {
        "layer": "network-endpoint",
        "primary_cause": "address-family-mismatch",
        "safe_fix": "match-bind-and-client-family",
        "command_groups": [("getaddrinfo", "localhost"), ("ss ", "lsof"), ("127.0.0.1", "::1")],
        "command_kinds": [
            ("host-resolution",),
            ("listener-enumeration",),
            ("ipv4-probe",),
            ("ipv6-probe",),
        ],
        "evidence_groups": [("ipv4", "127.0.0.1"), ("ipv6", "::1"), ("listen", "리스너")],
        "evidence_facts": [
            "listener-is-ipv4-loopback-only",
            "ipv6-loopback-connection-is-refused",
            "ipv4-loopback-connection-succeeds",
        ],
        "regression_targets": ["supported-address-family-connects", "no-unintended-external-bind"],
    },
    "07-running-not-ready": {
        "layer": "service-readiness",
        "primary_cause": "dependency-not-ready",
        "safe_fix": "satisfy-readiness-dependency",
        "command_groups": [("ps ",), ("health",), ("ss ", "lsof")],
        "command_kinds": [("process-status",), ("health-request",), ("listener-enumeration",)],
        "evidence_groups": [("프로세스", "process"), ("503",), ("dependency", "의존")],
        "evidence_facts": ["service-process-is-running", "listener-exists", "health-is-503-until-dependency-ready"],
        "regression_targets": ["health-is-200-after-dependency-ready", "health-returns-503-after-dependency-removal"],
    },
    "08-signal-not-forwarded": {
        "layer": "process-ownership",
        "primary_cause": "signal-not-forwarded",
        "safe_fix": "exec-or-forward-and-wait",
        "command_groups": [("ps ",), ("term", "signal", "시그널")],
        "command_kinds": [("process-ownership",), ("sigterm-event",)],
        "evidence_groups": [("wrapper",), ("worker", "child"), ("term", "시그널")],
        "evidence_facts": ["wrapper-exits-on-term", "worker-survives-wrapper-exit", "wrapper-did-not-forward-or-wait"],
        "regression_targets": [
            "single-term-stops-wrapper-and-worker",
            "supervisor-observes-worker-exit-with-no-child-left",
        ],
    },
    "09-reserved-not-resident": {
        "layer": "memory-observation",
        "primary_cause": "virtual-reservation-not-resident",
        "safe_fix": "measure-residency-before-action",
        "command_groups": [("vsz", "virtual"), ("rss", "resident"), ("/proc/", "vmmap", "ps ")],
        "command_kinds": [("memory-ps",), ("memory-map",)],
        "evidence_groups": [("virtual", "vsz"), ("rss", "상주"), ("예약", "mapping")],
        "evidence_facts": ["vsz-exceeds-rss", "only-touched-pages-are-resident", "rss-is-stable-under-same-workload"],
        "regression_targets": ["same-workload-keeps-rss-stable", "touching-more-pages-increases-rss"],
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

SAFE_COMMAND_FORMS = (
    ("command", "-v"),
    ("type", "-a"),
    ("printenv", "path"),
    ("pwd",),
    ("readlink",),
    ("ls",),
    ("test",),
    ("file",),
    ("ps",),
    ("lsof",),
    ("cat",),
    ("ss",),
    ("vmmap",),
    ("curl",),
    ("grep",),
    ("python3", "-c"),
    ("python", "-c"),
)
SHELL_CONTROL_TOKENS = {";", "&&", "||", "|", ">", ">>", "<", "<<"}
SAFE_PYTHON_OBSERVATIONS = (
    re.compile(r'''^import socket;\s*print\(socket\.getaddrinfo\(["']localhost["'],\s*0\)\)$'''),
    re.compile(
        r'''^import socket;\s*socket\.create_connection\(\(["']127\.0\.0\.1["'],\s*(?:PORT|[0-9]+)\),\s*timeout=1\)\.close\(\)$'''
    ),
    re.compile(
        r'''^import socket;\s*s=socket\.socket\(socket\.AF_INET6\);\s*s\.settimeout\(1\);\s*s\.connect\(\(["']::1["'],\s*(?:PORT|[0-9]+)\)\)$'''
    ),
)


def text_contains_any(text: str, alternatives: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(item.casefold() in lowered for item in alternatives)


def observation_command_error(command: str) -> str | None:
    """Validate an inspect-only command shape without executing learner input."""
    if "`" in command or "$(" in command:
        return "명령 치환은 자동 검수 가능한 읽기 전용 관찰 명령이 아닙니다."
    try:
        tokens = shlex.split(command)
    except ValueError:
        return "shell 인용 문법을 해석할 수 없습니다."
    if not tokens:
        return "빈 명령입니다."
    if any(token in SHELL_CONTROL_TOKENS or ">" in token or "<" in token for token in tokens):
        return "파이프·리다이렉션·명령 연결은 관찰 명령 계약에서 허용하지 않습니다."
    lowered = tuple(token.casefold() for token in tokens)
    if not any(lowered[: len(form)] == form for form in SAFE_COMMAND_FORMS):
        return "허용된 읽기 전용 관찰 명령 형태가 아닙니다."
    if lowered[0] == "ss":
        if len(tokens) < 2 or any(
            not token.startswith("-") or not set(token[1:]).issubset(set("alntup46H"))
            for token in tokens[1:]
        ):
            return "ss는 listener·connection을 읽는 옵션만 사용할 수 있습니다."
    if lowered[0] == "curl":
        allowed_flags = {"-i", "--include", "-s", "--silent", "-S", "--show-error"}
        urls = [token for token in tokens[1:] if token.startswith(("http://", "https://"))]
        if len(urls) != 1 or any(token not in allowed_flags and token not in urls for token in tokens[1:]):
            return "curl은 옵션 없는 GET 또는 출력 옵션을 붙인 GET 관찰만 허용합니다."
        endpoint = urlsplit(urls[0])
        if endpoint.username is not None or endpoint.password is not None:
            return "curl loopback URL에는 userinfo를 사용할 수 없습니다."
        if endpoint.hostname not in {"localhost", "127.0.0.1", "::1"}:
            return "curl 관찰 대상은 실습의 loopback endpoint여야 합니다."
    if lowered[0] in {"python", "python3"}:
        code = tokens[2] if len(tokens) > 2 else ""
        if not any(pattern.fullmatch(code) for pattern in SAFE_PYTHON_OBSERVATIONS):
            return "Python -c는 문서에 제시된 세 가지 loopback socket 관찰 형태만 허용합니다."
    return None


def observation_command_kinds(command: str) -> set[str]:
    """Classify the concrete state question a validated command can answer."""
    tokens = shlex.split(command)
    lowered = tuple(token.casefold() for token in tokens)
    text = command.casefold()
    kinds: set[str] = set()
    executable = lowered[0]

    if lowered[:2] in {("command", "-v"), ("type", "-a")} and lowered[2:] == ("unix-guide-tool",):
        kinds.add("tool-resolution")
    if lowered == ("printenv", "path"):
        kinds.add("path-order")
    if executable == "readlink" and "current" in text:
        kinds.add("link-target")
    if executable in {"ls", "test"} and "current" in text:
        kinds.add("link-object")
    if executable in {"ls", "test"} and "live.log" in text:
        kinds.add("missing-path")
    if executable == "pwd":
        kinds.add("cwd-shell")
    if executable == "ps" and "-p" in lowered:
        kinds.add("process-status")
        if "ppid" in text and "pgid" in text:
            kinds.add("process-ownership")
        if "vsz" in text and "rss" in text:
            kinds.add("memory-ps")
    if executable == "lsof":
        kinds.add("open-file-owner")
        if "cwd" in text:
            kinds.add("process-cwd")
        if "itcp" in text or "listen" in text:
            kinds.add("listener-enumeration")
    if executable == "ls" and "fifo" in text:
        kinds.add("fifo-object")
    if executable in {"ls", "cat"} and "/proc/" in text:
        if "/fd" in text:
            kinds.add("proc-fd")
        if "status" in text:
            kinds.add("memory-map")
    if executable == "ss":
        kinds.add("listener-enumeration")
    if executable == "vmmap":
        kinds.add("memory-map")
    if executable in {"python", "python3"}:
        code = tokens[2]
        if "socket.getaddrinfo" in code:
            kinds.add("host-resolution")
        if "socket.create_connection" in code and "127.0.0.1" in code:
            kinds.add("ipv4-probe")
        if "socket.AF_INET6" in code and "::1" in code:
            kinds.add("ipv6-probe")
    if executable == "curl" and "/health" in text:
        kinds.add("health-request")
    if executable == "grep" and "sigterm" in text and "wrapper-events" in text:
        kinds.add("sigterm-event")
    return kinds


def validate_exact_list(
    answer: dict[str, Any],
    spec: dict[str, Any],
    field: str,
    prefix: str,
    errors: list[str],
) -> None:
    value = answer.get(field)
    expected = spec[field]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(prefix + f"{field}에는 문서에 정의된 enum 목록이 필요합니다.")
        return
    if len(value) != len(set(value)) or set(value) != set(expected):
        errors.append(
            prefix + f"{field}가 관찰된 의미 계약과 일치하지 않습니다: {', '.join(expected)}"
        )


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
    if data.get("schema_version") != 2:
        errors.append("schema_version은 2여야 합니다.")

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
            command_kinds: set[str] = set()
            for command in commands:
                command_error = observation_command_error(command)
                if command_error:
                    errors.append(prefix + f"observation_commands: {command_error} 입력={command!r}")
                else:
                    command_kinds.update(observation_command_kinds(command))
            for fragment in UNSAFE_COMMAND_FRAGMENTS:
                if fragment.casefold() in command_text:
                    errors.append(prefix + f"관찰 단계에 위험하거나 상태를 크게 바꾸는 명령이 있습니다: {fragment}")
            for group in spec["command_groups"]:
                if not text_contains_any(command_text, group):
                    errors.append(prefix + "관찰 명령에 필요한 근거 종류가 빠졌습니다: " + " / ".join(group))
            for group in spec["command_kinds"]:
                if not any(kind in command_kinds for kind in group):
                    errors.append(prefix + "관찰 명령이 실제 상태 질문을 대상으로 하지 않습니다: " + " / ".join(group))

        evidence = answer.get("expected_evidence")
        if not isinstance(evidence, str) or len(evidence.strip()) < 40 or "TODO" in evidence.upper():
            errors.append(prefix + "expected_evidence에는 40자 이상의 구체적인 예상 근거가 필요합니다.")
        else:
            for group in spec["evidence_groups"]:
                if not text_contains_any(evidence, group):
                    errors.append(prefix + "예상 근거에 핵심 상태가 빠졌습니다: " + " / ".join(group))

        validate_exact_list(answer, spec, "evidence_facts", prefix, errors)

        regressions = answer.get("regression_checks")
        if not isinstance(regressions, list) or len(regressions) < 2 or not all(
            isinstance(v, str) and len(v.strip()) >= 15 and "TODO" not in v.upper() for v in regressions
        ):
            errors.append(prefix + "regression_checks에는 구체적인 검사 두 개 이상이 필요합니다.")
        validate_exact_list(answer, spec, "regression_targets", prefix, errors)

    return errors


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "--show-contract":
        case_id = argv[2]
        if case_id not in EXPECTED:
            print(f"알 수 없는 사례: {case_id}", file=sys.stderr)
            return 2
        spec = EXPECTED[case_id]
        contract = {
            "schema_version": 2,
            "case_id": case_id,
            "layer": spec["layer"],
            "primary_cause": spec["primary_cause"],
            "safe_fix": spec["safe_fix"],
            "required_command_kinds": spec["command_kinds"],
            "evidence_facts": spec["evidence_facts"],
            "regression_targets": spec["regression_targets"],
        }
        print(json.dumps(contract, ensure_ascii=False, indent=2))
        return 0
    if len(argv) != 2:
        print(
            f"사용법: {Path(argv[0]).name} ANSWERS.json | --show-contract CASE_ID",
            file=sys.stderr,
        )
        return 2
    path = Path(argv[1])
    errors = validate(path)
    if errors:
        print(f"FAIL {path}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"STRUCTURE PASS {path}")
    print("SEMANTIC REVIEW REQUIRED: 실제 출력과 기준 답안으로 설명·회귀 절차를 직접 대조하십시오.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
