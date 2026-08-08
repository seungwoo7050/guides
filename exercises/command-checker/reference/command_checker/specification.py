"""외부 JSON을 검증된 실행 사례로 변환합니다."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .model import Case, DEFAULT_OUTPUT_LIMIT, SpecificationError

_ALLOWED_FIELDS = {
    "name",
    "args",
    "stdin",
    "stdout",
    "stderr",
    "returncode",
    "timeout",
    "cwd",
    "env",
    "output_limit",
}


def _string(value: Any, field: str, index: int) -> str:
    if not isinstance(value, str):
        raise SpecificationError(f"cases[{index}].{field}는 문자열이어야 합니다.")
    return value


def _strings(value: Any, field: str, index: int) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SpecificationError(f"cases[{index}].{field}는 문자열 배열이어야 합니다.")
    if any("\0" in item for item in value):
        raise SpecificationError(f"cases[{index}].{field}에는 NUL 문자를 사용할 수 없습니다.")
    return tuple(value)


def _environment(value: Any, index: int) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in value.items()
    ):
        raise SpecificationError(
            f"cases[{index}].env는 문자열 키와 값으로 이루어진 객체여야 합니다."
        )
    for key, item in value.items():
        if "\0" in key or "=" in key or "\0" in item:
            raise SpecificationError(
                f"cases[{index}].env의 키와 값이 운영체제 환경 변수 형식에 맞지 않습니다."
            )
    return tuple(sorted(value.items()))


def _case(raw: Any, index: int, base: Path) -> Case:
    if not isinstance(raw, dict):
        raise SpecificationError(f"cases[{index}]는 객체여야 합니다.")

    unknown = sorted(set(raw) - _ALLOWED_FIELDS)
    if unknown:
        raise SpecificationError(
            f"cases[{index}]에 알 수 없는 필드가 있습니다: {', '.join(unknown)}"
        )

    name = _string(raw.get("name"), "name", index)
    if not name.strip():
        raise SpecificationError(f"cases[{index}].name은 비어 있을 수 없습니다.")

    returncode = raw.get("returncode", 0)
    if isinstance(returncode, bool) or not isinstance(returncode, int):
        raise SpecificationError(f"cases[{index}].returncode는 정수여야 합니다.")

    timeout = raw.get("timeout", 2.0)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise SpecificationError(f"cases[{index}].timeout은 숫자여야 합니다.")
    timeout = float(timeout)
    if not math.isfinite(timeout) or timeout <= 0:
        raise SpecificationError(f"cases[{index}].timeout은 유한한 양수여야 합니다.")

    output_limit = raw.get("output_limit", DEFAULT_OUTPUT_LIMIT)
    if isinstance(output_limit, bool) or not isinstance(output_limit, int):
        raise SpecificationError(f"cases[{index}].output_limit은 정수여야 합니다.")
    if output_limit <= 0:
        raise SpecificationError(f"cases[{index}].output_limit은 양수여야 합니다.")

    cwd_value = raw.get("cwd")
    cwd: Path | None = None
    if cwd_value is not None:
        cwd_text = _string(cwd_value, "cwd", index)
        if "\0" in cwd_text:
            raise SpecificationError(f"cases[{index}].cwd에는 NUL 문자를 사용할 수 없습니다.")
        cwd = (base / cwd_text).resolve()
        if not cwd.is_dir():
            raise SpecificationError(f"cases[{index}].cwd 디렉터리가 없습니다: {cwd}")

    return Case(
        name=name,
        args=_strings(raw.get("args", []), "args", index),
        stdin=_string(raw.get("stdin", ""), "stdin", index),
        stdout=_string(raw.get("stdout", ""), "stdout", index),
        stderr=_string(raw.get("stderr", ""), "stderr", index),
        returncode=returncode,
        timeout=timeout,
        cwd=cwd,
        env=_environment(raw.get("env", {}), index),
        output_limit=output_limit,
    )


def load_cases(path: Path) -> tuple[Case, ...]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SpecificationError(f"명세 파일을 읽을 수 없습니다: {error}") from error
    except json.JSONDecodeError as error:
        raise SpecificationError(
            f"JSON 형식이 잘못되었습니다: {error.msg} "
            f"(line {error.lineno}, column {error.colno})"
        ) from error

    if not isinstance(raw, list):
        raise SpecificationError("명세의 최상위 값은 배열이어야 합니다.")
    if not raw:
        raise SpecificationError("검사할 항목이 하나 이상 필요합니다.")

    names: set[str] = set()
    cases: list[Case] = []
    for index, item in enumerate(raw):
        case = _case(item, index, path.parent.resolve())
        if case.name in names:
            raise SpecificationError(f"중복된 항목 이름입니다: {case.name}")
        names.add(case.name)
        cases.append(case)
    return tuple(cases)
