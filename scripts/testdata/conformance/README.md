# Conformance runner calibration adapter

이 디렉터리는 Mica 정답 compiler를 제공하지 않습니다. `adapter.py`는 공개
`fixtures/manifest.json`의 file별 exit, diagnostic code, stdout와 return value를
읽어 checker의 positive path를 만드는 **fixture-backed test double**입니다.
일반 입력의 정확한 parsing, typing 또는 execution을 보장하지 않으므로 학습자
구현의 출발점이나 reference compiler로 사용하면 안 됩니다.

## 공개 command surface

Runner는 adapter 뒤에 다음 argv를 붙입니다.

```text
lex FILE --json
parse FILE --json
check FILE --json
run FILE --engine interpreter|vm --json
verify-bytecode MODULE.json --json
disassemble SOURCE --json
format FILE
lint FILE --json
```

Positive payload가 의도적으로 제공하는 최소 근거는 다음과 같습니다.

- 입력 경로를 resolve한 하나의 `source.id`, UTF-8 byte length와 동일 source의
  half-open span
- source slice와 일치하는 non-EOF token 및 마지막 zero-width `EOF`
- 비어 있지 않은 `Module → FunctionDecl → BlockStmt`와 모든 node의 `id/span`;
  단순 return에는 `ReturnStmt → IntLiteral` projection
- 성공한 `check`의 `semantic.symbols/references/types/functions`, symbol의
  `declaration_node`와 function의 `all_paths_return`
- manifest가 정한 interpreter result, 같은 VM result, valid bytecode module과
  deterministic disassembly
- exact formatter output, lint warning과 `machine-applicable`/unsafe fix 구분

이는 checker가 올바른 shape를 거부하지 않는다는 것만 확인합니다. Adapter가
fixture 경로를 인식해 결과를 재생하므로 언어 의미의 독립적인 oracle이 아닙니다.

## Mutant surface

`--mutant NAME` 또는 `MICA_ADAPTER_MUTANT=NAME`으로 하나의 알려진 오답을
활성화합니다.

| 이름 | 깨뜨리는 공개 불변식 |
|---|---|
| `eof-only` | 실제 source를 소비하지 않고 EOF만 반환 |
| `empty-module` | 정상 입력을 빈 `Module`로 반환 |
| `partial-node` | `kind`만 있고 `id/span`이 없는 AST child 삽입 |
| `wrong-source-id` | envelope와 다른 token/AST `source_id` |
| `split-utf8` | multibyte code point 내부를 span boundary로 사용 |
| `wrong-phase` | diagnostic code family와 phase 불일치 |
| `nan` | JSON에 비유한 숫자 `NaN` 포함 |
| `wrong-run` | manifest와 다른 stdout/return |
| `accept-invalid-bytecode` | malformed bytecode를 성공 처리 |
| `vm-mismatch` | VM 결과를 interpreter 결과와 다르게 반환 |
| `non-idempotent-format` | 두 번째 format에서 output 변경 |
| `unsafe-lint-fix` | effectful/semantic edit를 `machine-applicable`이라고 표시 |
| `timeout` | command budget을 넘도록 대기 |
| `output-flood` | stdout limit보다 큰 stream 생성 |

`scripts/test_conformance_runner.py`는 positive adapter가 core/VM/tooling 경로를
통과하고 위 mutant가 각각 거부되는지 black-box로 검사합니다. Timeout과 output
limit은 OS sandbox가 아니라 checker의 resource containment 회귀 검사입니다.
