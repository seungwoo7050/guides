# Mica Conformance Specification

## 1. 범위

공개 conformance runner는 구현의 외부 CLI와 공개 fixture를 검사합니다. 내부 class·module·algorithm·AST 저장 방식을 강제하지 않습니다.

Runner 성공은 다음을 증명하지 않습니다.

- 모든 source에 대한 parser termination
- type soundness
- optimization 의미 보존
- 모든 Unicode와 editor 호환
- 악의적 입력에 대한 production security

## 2. Command invocation

기본 Python profile:

```text
python3 -m mica <subcommand> ...
```

Runner는 workspace의 `src`를 `PYTHONPATH` 앞에 추가합니다.

다른 implementation:

```text
check_submission.py --command './build/mica' ...
```

Command string은 shell처럼 해석하지 않고 `shlex.split`으로 argv를 만듭니다. Pipe, redirection과 shell expansion에 의존하지 않습니다.

## 3. Required subcommand

### `lex FILE --json`

Exit `0` 또는 lexical error면 `1`입니다. stdout JSON:

```json
{
  "schema_version": 1,
  "command": "lex",
  "source": {"id": "...", "byte_length": 12},
  "tokens": [
    {"kind": "FN", "lexeme": "fn", "span": {"source_id": "...", "start": 0, "end": 2}}
  ],
  "diagnostics": []
}
```

- Token은 source 순서입니다.
- 마지막 token kind는 `EOF`이며 zero-width EOF span입니다.
- Trivia token을 포함해도 되지만 `kind`와 span이 안정적이어야 합니다.
- Lex error 뒤에도 EOF를 생성하고 가능한 token을 반환할 수 있습니다.

### `parse FILE --json`

Exit `0` 또는 lexical/parse error면 `1`입니다. stdout JSON:

```json
{
  "schema_version": 1,
  "command": "parse",
  "source": {...},
  "ast": {"kind": "Module", "id": 0, "span": {...}, "functions": []},
  "diagnostics": []
}
```

Recovery AST를 출력할 수 있습니다. 모든 node에 `kind`, integer `id`, valid `span`이 있어야 하며 child node id는 한 dump 안에서 유일해야 합니다.

### `check FILE --json`

Exit `0` 또는 source error면 `1`입니다. stdout JSON에 `diagnostics`가 필요합니다. 추가로 symbol/type/flow summary를 제공할 수 있습니다.

Compile phase가 앞에서 실패했으면 뒤 phase는 crash하지 않아야 합니다. 오류가 있는 AST에 semantic pass를 실행하지 않거나 error node/type/symbol을 사용합니다.

### `run FILE --json`

Static check 성공 후 실행합니다. stdout JSON:

```json
{
  "schema_version": 1,
  "command": "run",
  "source": {...},
  "stdout": "42\n",
  "return_value": {"type": "Int", "value": 42},
  "diagnostics": []
}
```

Runtime/source error면 exit `1`, `return_value`는 `null`, `diagnostics`에 error가 있습니다. Program output은 envelope의 `stdout` 문자열에만 들어가며 process stdout JSON 앞뒤에 직접 출력하지 않습니다.

### `format FILE`

Formatter 경로를 선택한 구현만 필요합니다.

- 성공하면 canonical source를 stdout에 출력하고 exit `0`입니다.
- input file을 직접 수정하지 않습니다.
- parse가 불가능해 전체 formatting을 거부하면 exit `1`과 stderr diagnostic입니다.
- 같은 output을 다시 format하면 byte-for-byte 같습니다.
- formatted source를 parse/check했을 때 원본과 같은 관찰 의미를 가져야 합니다.

### `disassemble FILE`

VM 경로의 선택 command입니다. Stable text 형식을 권장하며 runner는 필수 opcode 존재와 deterministic output만 검사합니다.

## 4. Exit와 timeout

- command timeout 기본값은 5초입니다.
- timeout은 runner 실패이며 implementation이 정의된 resource diagnostic을 내지 못했다는 뜻입니다.
- exit `0`: 해당 command 성공
- exit `1`: 정의된 source/runtime 오류
- exit `2`: usage, unimplemented 또는 internal 오류
- signal/negative return code: crash

## 5. JSON invariant

- stdout는 정확히 JSON value 하나입니다.
- UTF-8로 decode됩니다.
- NaN/Infinity를 사용하지 않습니다.
- key order는 의미가 없지만 list order는 stable합니다.
- span은 source byte boundary 안에 있습니다.
- error exit `1`에는 최소 하나의 `severity=error` diagnostic이 있습니다.
- success exit `0`에는 error diagnostic이 없습니다.

## 6. Fixture manifest

`fixtures/manifest.json`의 category:

```text
valid
invalid
runtime
format
bytecode_invalid
```

각 case:

- `file`: fixture root 기준 path
- `stage`: 최소 검사 stage
- `exit`: 기대 exit
- `codes`: 기대 error code의 정확한 순서
- `stdout`: run envelope의 program output
- `return`: typed return value
- `notes`: 의도

Runner는 diagnostic message 전문을 비교하지 않습니다. Code, severity, phase와 span validity를 확인합니다.

## 7. Determinism

Runner는 주요 command를 같은 입력으로 두 번 실행할 수 있습니다. 다음은 같아야 합니다.

- exit status
- canonicalized JSON
- diagnostic 순서·code·span
- token/AST stable field
- format output
- disassembly

Timing, absolute temporary path와 process id를 외부 결과에 넣지 않습니다.

## 8. Implementation별 추가 검사

완료 제출은 공개 runner 외에 다음을 포함합니다.

- parser/lexer property 또는 fuzz test
- known-bad fixture
- interpreter/VM 또는 backend differential
- formatter idempotence와 round-trip
- source span Unicode case
- resource budget case
- automatic checker가 보장하지 못하는 범위
## 9. Optional VM verification command

VM 경로의 공개 검사에는 다음 command를 제공합니다.

```sh
mica verify-bytecode MODULE.json --json
```

성공 envelope의 `command`는 `verify-bytecode`입니다. Malformed module은 exit `1`과 `MICA500x` code를 반환합니다. `--stage all`은 core Stage 1–5만 실행하며, VM과 formatter는 선택 경로이므로 각각 `--stage vm`, `--stage format`으로 검사합니다.
