#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable

MISSING = object()
SCHEMA_VERSION = 2
TYPE_NAMES = {'array', 'boolean', 'integer', 'null', 'number', 'object', 'string'}
CONTRACT_KEYS = {
    'schemaVersion',
    'title',
    'requiredPaths',
    'nonEmptyPaths',
    'minimumItems',
    'arrayItemRequiredFields',
    'arrayUniqueBy',
    'containsValues',
    'allowedValues',
    'matches',
    'forbiddenSubstrings',
    'valueTypes',
    'arrayContainsObjects',
    'pathComparisons',
    'conditionalRequirements',
}
THEN_KEYS = {'requiredPaths', 'nonEmptyPaths', 'valueTypes'}


class HarnessError(ValueError):
    pass


class ContractError(ValueError):
    pass


class SubmissionError(ValueError):
    pass


def reject_constant(value: str) -> None:
    raise ValueError(f'비유한 숫자는 JSON에서 허용되지 않습니다: {value}')


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'중복 JSON key가 있습니다: {key!r}')
        result[key] = value
    return result


def load_json(path: Path, *, submission: bool = False) -> Any:
    try:
        text = path.read_text(encoding='utf-8')
    except FileNotFoundError as exc:
        raise HarnessError(f'파일이 없습니다: {path}') from exc
    except UnicodeError as exc:
        error_type = SubmissionError if submission else ContractError
        raise error_type(f'UTF-8 파일이어야 합니다: {path}: {exc}') from exc
    except OSError as exc:
        raise HarnessError(f'파일을 읽을 수 없습니다: {path}: {exc}') from exc

    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except (json.JSONDecodeError, UnicodeError, ValueError) as exc:
        error_type = SubmissionError if submission else ContractError
        if isinstance(exc, json.JSONDecodeError):
            detail = f'{exc.lineno}:{exc.colno}: {exc.msg}'
        else:
            detail = str(exc)
        raise error_type(f'JSON 오류: {path}:{detail}') from exc


def validate_pointer(pointer: Any, *, wildcard: bool = False) -> str:
    if not isinstance(pointer, str) or (pointer and not pointer.startswith('/')):
        raise ContractError(f'JSON Pointer는 빈 문자열이거나 /로 시작해야 합니다: {pointer!r}')
    for raw in pointer.split('/')[1:]:
        if re.search(r'~(?![01])', raw):
            raise ContractError(f'잘못된 JSON Pointer escape입니다: {pointer!r}')
        if '*' in raw and (not wildcard or raw != '*'):
            raise ContractError(f'와일드카드는 valueTypes의 전체 segment로만 사용할 수 있습니다: {pointer!r}')
    return pointer


def decode_pointer_token(raw: str) -> str:
    return raw.replace('~1', '/').replace('~0', '~')


def pointer_get(value: Any, pointer: str) -> Any:
    if pointer == '':
        return value
    current = value
    for raw in pointer.split('/')[1:]:
        token = decode_pointer_token(raw)
        if isinstance(current, dict):
            if token not in current:
                return MISSING
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit():
                return MISSING
            index = int(token)
            if index >= len(current):
                return MISSING
            current = current[index]
        else:
            return MISSING
    return current


def pointer_values(value: Any, pointer: str) -> list[tuple[str, Any]]:
    states: list[tuple[str, Any]] = [('', value)]
    if pointer == '':
        return states
    for raw in pointer.split('/')[1:]:
        token = decode_pointer_token(raw)
        next_states: list[tuple[str, Any]] = []
        for path, current in states:
            if token == '*':
                if not isinstance(current, list):
                    next_states.append((f'{path}/*', MISSING))
                    continue
                next_states.extend((f'{path}/{index}', item) for index, item in enumerate(current))
            elif isinstance(current, dict) and token in current:
                next_states.append((f'{path}/{raw}', current[token]))
            elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
                next_states.append((f'{path}/{token}', current[int(token)]))
            else:
                next_states.append((f'{path}/{raw}', MISSING))
        states = next_states
    return states


def is_non_empty(value: Any) -> bool:
    if value is MISSING or value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def walk_strings(value: Any, path: str = '') -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path or '/', value
    elif isinstance(value, dict):
        for key, item in value.items():
            escaped = str(key).replace('~', '~0').replace('/', '~1')
            yield from walk_strings(item, f'{path}/{escaped}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_strings(item, f'{path}/{index}')


def ensure_finite(value: Any, path: str = '') -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError(f'계약에 비유한 숫자가 있습니다: {path or "/"}')
    if isinstance(value, dict):
        for key, item in value.items():
            ensure_finite(item, f'{path}/{key}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            ensure_finite(item, f'{path}/{index}')


def require_list(value: Any, label: str, *, strings: bool = False) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f'{label}: 배열이어야 합니다.')
    if strings and any(not isinstance(item, str) or not item for item in value):
        raise ContractError(f'{label}: 비어 있지 않은 문자열 배열이어야 합니다.')
    if strings and len(set(value)) != len(value):
        raise ContractError(f'{label}: 중복 항목이 있습니다.')
    return value


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f'{label}: object여야 합니다.')
    return value


def validate_pointer_list(value: Any, label: str) -> None:
    for pointer in require_list(value, label, strings=True):
        validate_pointer(pointer)


def normalize_types(value: Any, label: str) -> tuple[str, ...]:
    values = [value] if isinstance(value, str) else require_list(value, label, strings=True)
    if not values or any(item not in TYPE_NAMES for item in values):
        raise ContractError(f'{label}: 지원 type은 {sorted(TYPE_NAMES)}입니다.')
    return tuple(values)


def validate_value_types(value: Any, label: str) -> None:
    for pointer, expected in require_mapping(value, label).items():
        validate_pointer(pointer, wildcard=True)
        normalize_types(expected, f'{label}/{pointer}')


def validate_contract(contract: Any) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise ContractError('contract 최상위 값은 object여야 합니다.')
    ensure_finite(contract)
    unknown = sorted(set(contract) - CONTRACT_KEYS)
    if unknown:
        raise ContractError(f'알 수 없는 contract key입니다: {unknown}')
    if contract.get('schemaVersion') != SCHEMA_VERSION:
        raise ContractError(f'schemaVersion은 {SCHEMA_VERSION}여야 합니다.')
    if not isinstance(contract.get('title'), str) or not contract['title'].strip():
        raise ContractError('title은 비어 있지 않은 문자열이어야 합니다.')

    validate_pointer_list(contract.get('requiredPaths', []), 'requiredPaths')
    validate_pointer_list(contract.get('nonEmptyPaths', []), 'nonEmptyPaths')

    for pointer, minimum in require_mapping(contract.get('minimumItems', {}), 'minimumItems').items():
        validate_pointer(pointer)
        if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 0:
            raise ContractError(f'minimumItems/{pointer}: 0 이상의 integer여야 합니다.')

    for pointer, fields in require_mapping(
        contract.get('arrayItemRequiredFields', {}), 'arrayItemRequiredFields'
    ).items():
        validate_pointer(pointer)
        require_list(fields, f'arrayItemRequiredFields/{pointer}', strings=True)

    for pointer, field in require_mapping(contract.get('arrayUniqueBy', {}), 'arrayUniqueBy').items():
        validate_pointer(pointer)
        if not isinstance(field, str) or not field:
            raise ContractError(f'arrayUniqueBy/{pointer}: field 문자열이 필요합니다.')

    for key in ('containsValues', 'allowedValues'):
        for pointer, values in require_mapping(contract.get(key, {}), key).items():
            validate_pointer(pointer)
            items = require_list(values, f'{key}/{pointer}')
            if key == 'allowedValues' and not items:
                raise ContractError(f'{key}/{pointer}: 하나 이상의 허용 값이 필요합니다.')

    for pointer, pattern in require_mapping(contract.get('matches', {}), 'matches').items():
        validate_pointer(pointer)
        if not isinstance(pattern, str):
            raise ContractError(f'matches/{pointer}: 정규식 문자열이 필요합니다.')
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ContractError(f'matches/{pointer}: 잘못된 정규식입니다: {exc}') from exc

    require_list(contract.get('forbiddenSubstrings', []), 'forbiddenSubstrings', strings=True)
    validate_value_types(contract.get('valueTypes', {}), 'valueTypes')

    for pointer, expected_objects in require_mapping(
        contract.get('arrayContainsObjects', {}), 'arrayContainsObjects'
    ).items():
        validate_pointer(pointer)
        objects = require_list(expected_objects, f'arrayContainsObjects/{pointer}')
        if not objects or any(not isinstance(item, dict) or not item for item in objects):
            raise ContractError(f'arrayContainsObjects/{pointer}: 비어 있지 않은 partial object가 필요합니다.')

    comparisons = require_list(contract.get('pathComparisons', []), 'pathComparisons')
    for index, comparison in enumerate(comparisons):
        mapping = require_mapping(comparison, f'pathComparisons/{index}')
        if set(mapping) != {'left', 'op', 'right'}:
            raise ContractError(f'pathComparisons/{index}: left, op, right만 허용됩니다.')
        validate_pointer(mapping['left'])
        validate_pointer(mapping['right'])
        if not isinstance(mapping['op'], str) or mapping['op'] not in {'eq', 'ne'}:
            raise ContractError(f'pathComparisons/{index}: op는 eq 또는 ne여야 합니다.')

    rules = require_list(contract.get('conditionalRequirements', []), 'conditionalRequirements')
    for index, rule in enumerate(rules):
        mapping = require_mapping(rule, f'conditionalRequirements/{index}')
        if set(mapping) != {'if', 'then'}:
            raise ContractError(f'conditionalRequirements/{index}: if와 then만 허용됩니다.')
        condition = require_mapping(mapping['if'], f'conditionalRequirements/{index}/if')
        if set(condition) not in ({'path', 'equals'}, {'path', 'notEquals'}):
            raise ContractError(
                f'conditionalRequirements/{index}/if: path와 equals 또는 notEquals가 필요합니다.'
            )
        validate_pointer(condition['path'])
        then = require_mapping(mapping['then'], f'conditionalRequirements/{index}/then')
        unknown_then = sorted(set(then) - THEN_KEYS)
        if not then or unknown_then:
            raise ContractError(
                f'conditionalRequirements/{index}/then: {sorted(THEN_KEYS)}만 허용됩니다.'
            )
        if 'requiredPaths' in then:
            validate_pointer_list(then['requiredPaths'], f'conditionalRequirements/{index}/then/requiredPaths')
        if 'nonEmptyPaths' in then:
            validate_pointer_list(then['nonEmptyPaths'], f'conditionalRequirements/{index}/then/nonEmptyPaths')
        if 'valueTypes' in then:
            validate_value_types(then['valueTypes'], f'conditionalRequirements/{index}/then/valueTypes')
    return contract


def type_matches(value: Any, expected: str) -> bool:
    if expected == 'null':
        return value is None
    if expected == 'boolean':
        return isinstance(value, bool)
    if expected == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == 'number':
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if expected == 'string':
        return isinstance(value, str)
    if expected == 'array':
        return isinstance(value, list)
    if expected == 'object':
        return isinstance(value, dict)
    return False


def json_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    return left == right


def apply_value_types(rules: dict[str, Any], submission: Any, errors: list[str]) -> None:
    for pointer, expected_raw in rules.items():
        expected = normalize_types(expected_raw, f'valueTypes/{pointer}')
        for resolved, value in pointer_values(submission, pointer):
            if value is MISSING:
                errors.append(f'type을 검사할 경로가 없습니다: {resolved or pointer}')
            elif not any(type_matches(value, item) for item in expected):
                errors.append(f'{resolved or pointer}: type은 {list(expected)} 중 하나여야 합니다.')


def apply_requirement_set(rules: dict[str, Any], submission: Any, errors: list[str]) -> None:
    for pointer in rules.get('requiredPaths', []):
        if pointer_get(submission, pointer) is MISSING:
            errors.append(f'필수 경로가 없습니다: {pointer}')
    for pointer in rules.get('nonEmptyPaths', []):
        if not is_non_empty(pointer_get(submission, pointer)):
            errors.append(f'비어 있으면 안 됩니다: {pointer}')
    apply_value_types(rules.get('valueTypes', {}), submission, errors)


def validate(contract: dict[str, Any], submission: Any) -> list[str]:
    validate_contract(contract)
    errors: list[str] = []
    if not isinstance(submission, dict):
        return ['제출물 최상위 값은 JSON object여야 합니다.']

    apply_requirement_set(contract, submission, errors)

    for pointer, minimum in contract.get('minimumItems', {}).items():
        value = pointer_get(submission, pointer)
        if not isinstance(value, list):
            errors.append(f'배열이어야 합니다: {pointer}')
        elif len(value) < minimum:
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
            errors.append(f'고유 값을 검사할 배열이 없습니다: {pointer}')
            continue
        seen: dict[str, int] = {}
        for index, item in enumerate(value):
            if not isinstance(item, dict) or field not in item:
                errors.append(f'{pointer}/{index}: 고유 key {field!r}가 필요합니다.')
                continue
            marker = json.dumps(item[field], ensure_ascii=False, sort_keys=True, allow_nan=False)
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
            if not any(json_equal(expected, actual) for actual in value):
                errors.append(f'{pointer}: 필수 값이 없습니다: {expected!r}')

    for pointer, allowed in contract.get('allowedValues', {}).items():
        value = pointer_get(submission, pointer)
        if value is MISSING:
            errors.append(f'허용 값을 검사할 경로가 없습니다: {pointer}')
        elif not any(json_equal(value, expected) for expected in allowed):
            errors.append(f'{pointer}: 허용 값 {allowed!r} 중 하나여야 하지만 {value!r}입니다.')

    for pointer, pattern in contract.get('matches', {}).items():
        value = pointer_get(submission, pointer)
        if value is MISSING:
            errors.append(f'정규식을 검사할 경로가 없습니다: {pointer}')
        elif not isinstance(value, str) or re.fullmatch(pattern, value) is None:
            errors.append(f'{pointer}: 정규식 {pattern!r}과 일치해야 합니다.')

    for pointer, expected_objects in contract.get('arrayContainsObjects', {}).items():
        value = pointer_get(submission, pointer)
        if not isinstance(value, list):
            errors.append(f'object 포함 여부를 검사할 배열이 없습니다: {pointer}')
            continue
        for expected in expected_objects:
            found = any(
                isinstance(item, dict)
                and all(
                    key in item and json_equal(item[key], expected_value)
                    for key, expected_value in expected.items()
                )
                for item in value
            )
            if not found:
                errors.append(f'{pointer}: 필수 category/invariant object가 없습니다: {expected!r}')

    for comparison in contract.get('pathComparisons', []):
        left = pointer_get(submission, comparison['left'])
        right = pointer_get(submission, comparison['right'])
        if left is MISSING or right is MISSING:
            errors.append(
                f'경로 비교 대상이 없습니다: {comparison["left"]}, {comparison["right"]}'
            )
            continue
        equal = json_equal(left, right)
        if (comparison['op'] == 'eq' and not equal) or (comparison['op'] == 'ne' and equal):
            errors.append(
                f'경로 비교가 실패했습니다: {comparison["left"]} '
                f'{comparison["op"]} {comparison["right"]}'
            )

    for rule in contract.get('conditionalRequirements', []):
        condition = rule['if']
        actual = pointer_get(submission, condition['path'])
        triggered = False
        if actual is not MISSING:
            if 'equals' in condition:
                triggered = json_equal(actual, condition['equals'])
            else:
                triggered = not json_equal(actual, condition['notEquals'])
        if triggered:
            apply_requirement_set(rule['then'], submission, errors)

    forbidden = [item.casefold() for item in contract.get('forbiddenSubstrings', [])]
    for pointer, text in walk_strings(submission):
        folded = text.casefold()
        for token in forbidden:
            if token in folded:
                errors.append(f'{pointer}: 금지된 미완성 표시가 있습니다: {token!r}')
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print('사용법: verify_submission.py CONTRACT_JSON SUBMISSION_JSON', file=sys.stderr)
        return 2
    contract_path = Path(argv[1])
    submission_path = Path(argv[2])
    try:
        contract = validate_contract(load_json(contract_path))
        submission = load_json(submission_path, submission=True)
        errors = validate(contract, submission)
    except SubmissionError as exc:
        print(f'REJECTED {submission_path}', file=sys.stderr)
        print(f'- {exc}', file=sys.stderr)
        return 1
    except (HarnessError, ContractError) as exc:
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
