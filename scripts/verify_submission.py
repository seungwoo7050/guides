#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

MISSING = object()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        raise ValueError(f'파일이 없습니다: {path}')
    except json.JSONDecodeError as exc:
        raise ValueError(f'JSON 문법 오류: {path}:{exc.lineno}:{exc.colno}: {exc.msg}')


def pointer_get(value: Any, pointer: str) -> Any:
    if pointer == '':
        return value
    if not pointer.startswith('/'):
        raise ValueError(f'JSON Pointer는 /로 시작해야 합니다: {pointer}')
    current = value
    for raw in pointer.split('/')[1:]:
        token = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(current, dict):
            if token not in current:
                return MISSING
            current = current[token]
        elif isinstance(current, list):
            try:
                index = int(token)
            except ValueError:
                return MISSING
            if index < 0 or index >= len(current):
                return MISSING
            current = current[index]
        else:
            return MISSING
    return current


def is_non_empty(value: Any) -> bool:
    if value is MISSING or value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def walk_strings(value: Any, path: str = ''):
    if isinstance(value, str):
        yield path or '/', value
    elif isinstance(value, dict):
        for key, item in value.items():
            escaped = str(key).replace('~', '~0').replace('/', '~1')
            yield from walk_strings(item, f'{path}/{escaped}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_strings(item, f'{path}/{index}')


def validate(contract: dict[str, Any], submission: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(submission, dict):
        return ['제출물 최상위 값은 JSON object여야 합니다.']

    for pointer in contract.get('requiredPaths', []):
        if pointer_get(submission, pointer) is MISSING:
            errors.append(f'필수 경로가 없습니다: {pointer}')

    for pointer in contract.get('nonEmptyPaths', []):
        value = pointer_get(submission, pointer)
        if not is_non_empty(value):
            errors.append(f'비어 있으면 안 됩니다: {pointer}')

    for pointer, minimum in contract.get('minimumItems', {}).items():
        value = pointer_get(submission, pointer)
        if not isinstance(value, list):
            errors.append(f'배열이어야 합니다: {pointer}')
        elif len(value) < int(minimum):
            errors.append(f'{pointer}: 최소 {minimum}개 항목이 필요하지만 {len(value)}개입니다.')

    for pointer, fields in contract.get('arrayItemRequiredFields', {}).items():
        value = pointer_get(submission, pointer)
        if not isinstance(value, list):
            errors.append(f'항목 필드를 검사할 배열이 없습니다: {pointer}')
            continue
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                errors.append(f'{pointer}/{index}: object여야 합니다.')
                continue
            for field in fields:
                if field not in item or not is_non_empty(item[field]):
                    errors.append(f'{pointer}/{index}: 필수 field가 비어 있습니다: {field}')

    for pointer, field in contract.get('arrayUniqueBy', {}).items():
        value = pointer_get(submission, pointer)
        if not isinstance(value, list):
            continue
        seen: dict[Any, int] = {}
        for index, item in enumerate(value):
            if not isinstance(item, dict) or field not in item:
                continue
            marker = json.dumps(item[field], ensure_ascii=False, sort_keys=True)
            if marker in seen:
                errors.append(f'{pointer}: {field} 값이 중복됩니다. index {seen[marker]}와 {index}')
            else:
                seen[marker] = index

    for pointer, expected_values in contract.get('containsValues', {}).items():
        value = pointer_get(submission, pointer)
        if not isinstance(value, list):
            errors.append(f'포함 값을 검사할 배열이 없습니다: {pointer}')
            continue
        for expected in expected_values:
            if expected not in value:
                errors.append(f'{pointer}: 필수 값이 없습니다: {expected!r}')

    for pointer, allowed in contract.get('allowedValues', {}).items():
        value = pointer_get(submission, pointer)
        if value is MISSING:
            continue
        if value not in allowed:
            errors.append(f'{pointer}: 허용 값 {allowed!r} 중 하나여야 하지만 {value!r}입니다.')

    for pointer, pattern in contract.get('matches', {}).items():
        value = pointer_get(submission, pointer)
        if value is MISSING:
            continue
        if not isinstance(value, str) or re.fullmatch(pattern, value) is None:
            errors.append(f'{pointer}: 정규식 {pattern!r}과 일치해야 합니다.')

    forbidden = [str(x).casefold() for x in contract.get('forbiddenSubstrings', [])]
    for pointer, text in walk_strings(submission):
        folded = text.casefold()
        for token in forbidden:
            if token and token in folded:
                errors.append(f'{pointer}: 금지된 미완성 표시가 있습니다: {token!r}')

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print('사용법: verify_submission.py CONTRACT_JSON SUBMISSION_JSON', file=sys.stderr)
        return 2
    contract_path = Path(argv[1])
    submission_path = Path(argv[2])
    try:
        contract = load_json(contract_path)
        submission = load_json(submission_path)
        if not isinstance(contract, dict):
            raise ValueError('contract 최상위 값은 object여야 합니다.')
        errors = validate(contract, submission)
    except ValueError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2

    if errors:
        print(f'REJECTED {submission_path}', file=sys.stderr)
        for error in errors:
            print(f'- {error}', file=sys.stderr)
        return 1

    print(f'OK {submission_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
