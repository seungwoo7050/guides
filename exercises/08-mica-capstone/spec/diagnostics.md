# Mica diagnostic와 외부 오류 계약

## 1. 목표

Diagnostic는 renderer용 문자열이 아니라 compiler phase와 editor가 공유하는 구조화 데이터입니다. Message 문구는 개선할 수 있지만 code, severity, source identity와 primary span은 compatibility 대상입니다.

## 2. 공통 envelope

`lex`, `parse`, `check`, `run`의 `--json` 출력은 다음 공통 필드를 가집니다.

```json
{
  "schema_version": 1,
  "command": "check",
  "source": {
    "id": "fixtures/invalid/unknown-name.mica",
    "byte_length": 49
  },
  "diagnostics": []
}
```

- `schema_version`은 integer `1`입니다.
- `command`는 실제 subcommand입니다.
- `source.id`는 command가 받은 path를 안정적으로 식별하는 문자열입니다.
- `source.byte_length`는 UTF-8 byte 수입니다.
- `diagnostics`는 오류가 없어도 빈 배열로 존재합니다.

## 3. Diagnostic object

```json
{
  "code": "MICA3003",
  "severity": "error",
  "phase": "resolution",
  "message": "unknown name 'missing'",
  "primary": {
    "source_id": "fixtures/invalid/unknown-name.mica",
    "start": 28,
    "end": 35
  },
  "secondary": [],
  "notes": [],
  "fixes": []
}
```

### 필수 필드

- `code`: stable uppercase code
- `severity`: `error`, `warning`, `information`, `hint` 중 하나
- `phase`: `lex`, `parse`, `resolution`, `type`, `flow`, `runtime`, `bytecode`, `internal`
- `message`: 한 줄 요약
- `primary`: 하나의 valid span

### 선택 배열

- `secondary`: 관련 declaration, previous definition와 caller span
- `notes`: span 없는 설명
- `fixes`: 안전성 분류가 있는 edit set

빈 배열을 생략할 수는 있지만 같은 command/version에서는 출력 shape를 일정하게 유지하는 편을 권장합니다.

## 4. Span

```json
{
  "source_id": "path/or/id",
  "start": 10,
  "end": 14
}
```

조건:

```text
0 <= start <= end <= source.byte_length
```

Offset은 UTF-8 byte입니다. `start == end`인 zero-width span은 EOF 삽입 위치 등에 허용합니다. 다른 source를 가리키는 secondary span은 해당 source metadata를 별도 table로 제공해야 합니다. Core fixture는 한 source만 사용합니다.

Line/column은 renderer 파생값이므로 core JSON 필수가 아닙니다. 제공한다면 byte offset과 일치해야 합니다.

## 5. 정렬과 중복

Diagnostic는 다음 key로 안정적으로 정렬합니다.

```text
(source_id, primary.start, primary.end, severity_rank, code, message)
```

Severity rank:

```text
error < warning < information < hint
```

동일한 `(code, primary, message)`는 한 번만 출력합니다. Recovery가 만든 synthetic node에서 파생된 오류가 root cause와 같은 위치·원인을 반복하면 error type/symbol로 억제합니다.

## 6. Exit status와 channel

| 상태 | Exit | stdout | stderr |
|---|---:|---|---|
| 성공, `--json` | 0 | JSON 하나 | 비어 있거나 log |
| 정의된 source/runtime 오류, `--json` | 1 | JSON 하나 | renderer/log 선택 |
| 성공, text command | 0 | command 결과 | log |
| 정의된 오류, text command | 1 | 부분 결과 없음 또는 명세된 결과 | diagnostic renderer |
| CLI 사용 오류·미구현·internal | 2 | JSON command면 가능한 경우 error envelope, 아니면 비움 | 오류 설명 |

JSON stdout에 progress, debug print 또는 traceback을 섞지 않습니다.

## 7. Stable code

### Driver/internal

| Code | 의미 |
|---|---|
| `MICA0000` | skeleton 또는 명시적 미구현 기능 |
| `MICA0001` | CLI 사용 오류 |
| `MICA9001` | internal compiler error / impossible state |

### Lex

| Code | 의미 |
|---|---|
| `MICA1001` | 인식할 수 없는 문자 |
| `MICA1002` | 닫히지 않은 string |
| `MICA1003` | 허용되지 않은 escape |
| `MICA1004` | integer literal 범위 초과 |

### Parse

| Code | 의미 |
|---|---|
| `MICA2001` | 예상 token 없음 |
| `MICA2002` | 현재 문맥에 올 수 없는 token |
| `MICA2003` | invalid assignment target 또는 malformed construct |
| `MICA2004` | parser recovery/error budget 초과 |

### Resolution

| Code | 의미 |
|---|---|
| `MICA3001` | duplicate function/builtin name |
| `MICA3002` | same-scope duplicate local/parameter |
| `MICA3003` | unknown name |
| `MICA3004` | immutable 또는 non-local assignment target |

### Type

| Code | 의미 |
|---|---|
| `MICA3101` | declared/expected type mismatch |
| `MICA3102` | operator operand type 오류 |
| `MICA3103` | call argument count 오류 |
| `MICA3104` | callable이 아닌 expression 호출 |
| `MICA3105` | `if`/`while` condition이 `Bool` 아님 |
| `MICA3106` | return value/type 오류 |
| `MICA3107` | `Unit` local 또는 parameter |

### Flow/entry

| Code | 의미 |
|---|---|
| `MICA3201` | non-`Unit` function의 reachable path에 return 없음 |
| `MICA3202` | `main` 없음·중복 또는 signature 오류 |
| `MICA3203` | unreachable statement warning |

### Runtime

| Code | 의미 |
|---|---|
| `MICA4001` | division/remainder by zero |
| `MICA4002` | checked integer overflow |
| `MICA4003` | call-depth limit 초과 |
| `MICA4004` | execution-step limit 초과 |

### Bytecode

| Code | 의미 |
|---|---|
| `MICA5001` | unknown opcode 또는 malformed operand |
| `MICA5002` | invalid jump target |
| `MICA5003` | stack underflow |
| `MICA5004` | branch merge stack mismatch |
| `MICA5005` | local/function/constant index 범위 오류 |
| `MICA5006` | return stack/type contract 오류 |

### Lint

| Code | 의미 |
|---|---|
| `MICA6001` | unused local |
| `MICA6002` | unreachable statement |
| `MICA6003` | shadowing declaration |

Lint code는 `phase: lint`, 기본 `severity: warning`입니다. Effect가 있는 initializer, effect가 있는 unreachable statement, symbol-aware rename이 필요한 shadowing에는 `machine-applicable` fix를 제공하지 않습니다.

Code의 의미를 재사용하지 않습니다. 기존 code의 더 자세한 경우는 note/subcode를 추가하거나 새 code를 도입합니다.

## 8. Fix

Fix object 권장 형식:

```json
{
  "title": "insert ';'",
  "applicability": "machine-applicable",
  "edits": [
    {
      "source_id": "example.mica",
      "start": 31,
      "end": 31,
      "replacement": ";"
    }
  ]
}
```

`applicability`:

- `machine-applicable`: 다른 의미 선택 없이 적용 가능
- `maybe-incorrect`: 사용자 검토 필요
- `has-placeholders`: 추가 입력 필요

겹치는 edit, stale source version과 invalid UTF-8 boundary는 적용하지 않습니다.

## 9. Renderer 최소 요구

Text renderer는 다음을 포함합니다.

```text
path:line:column: severity[code]: message
source line
caret/underline
secondary label와 note
```

Column은 1-based Unicode code point column을 기본으로 하되, protocol adapter는 협상된 encoding으로 따로 변환합니다. Tab display는 4칸을 기본으로 할 수 있지만 JSON byte span은 변하지 않습니다.
