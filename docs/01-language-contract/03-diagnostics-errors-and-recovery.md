# 진단, 오류 분류와 복구 계약

좋은 compiler는 오류를 많이 출력하는 compiler가 아니라 **첫 원인을 정확한 위치에서 설명하고, 이후 분석이 거짓 상태를 만들지 않도록 복구하는 compiler**입니다. Diagnostic은 문자열 로그가 아니라 editor, test와 사용자 문서가 소비하는 public data contract입니다.

## 학습 목표

- diagnostic code, severity, primary/secondary span과 fix를 구조화합니다.
- lexical, syntax, resolution, type, flow와 runtime 오류의 소유 phase를 구분합니다.
- parser recovery와 semantic error propagation이 무한 반복·연쇄 진단을 만들지 않게 합니다.
- 내부 오류와 지원되지 않는 기능을 사용자 오류와 분리합니다.

## Diagnostic data model

최소 구조는 다음과 같습니다.

```text
Diagnostic
  code:       stable identifier
  severity:   error | warning | info
  message:    짧은 핵심 설명
  primary:    SourceSpan
  labels:     0개 이상의 secondary span + 설명
  notes:      추가 문맥
  fixes:      안전 조건이 있는 text edit 후보
  phase:      lex | parse | resolve | type | flow | runtime | tool
```

사람이 읽는 message는 개선될 수 있지만 code는 test와 문서가 의존할 수 있으므로 안정적으로 관리합니다. `E3001`을 다른 의미로 재사용하지 않습니다.

## Primary span은 사용자가 처음 고칠 위치입니다

다음 프로그램에서 함수 인자 type이 잘못됐다고 가정합니다.

```text
fn twice(value: Int) -> Int { return value * 2; }
fn main() -> Int { return twice(true); }
```

Primary span은 `true`이고 secondary label은 parameter `value: Int` 선언을 가리킬 수 있습니다.

```text
error[E3001]: expected Int, found Bool
  --> main.mica:2:32
   |
 2 | fn main() -> Int { return twice(true); }
   |                                ^^^^ argument has type Bool
   |
 1 | fn twice(value: Int) -> Int { ... }
   |                --- parameter requires Int
```

함수 전체나 파일 첫 줄을 primary로 선택하면 사용자가 원인을 찾기 어렵습니다.

## Phase별 오류를 구분합니다

### Lexical

문자열이 token으로 분할될 수 없는 상태입니다.

- 잘못된 문자
- 닫히지 않은 문자열
- 잘못된 escape

### Syntax

Token 배열이 grammar 구조를 만들지 못합니다.

- 누락된 `;`
- 예상하지 않은 token
- 닫히지 않은 `)` 또는 `}`

### Resolution

구조는 맞지만 이름 binding을 만들 수 없습니다.

- 알 수 없는 이름
- 같은 scope의 중복 선언
- 사용할 수 없는 declaration order

### Type와 flow

Resolved program의 정적 규칙을 만족하지 않습니다.

- type mismatch
- argument 개수 오류
- 모든 경로에서 return하지 않음
- 초기화 전 사용

### Runtime

정적으로 유효한 프로그램이 실행 중 언어가 정의한 실패를 만납니다.

- 0으로 나누기
- checked integer overflow
- stack 또는 instruction budget 초과

오류가 어느 phase에 속하는지 정하면 test와 recovery 위치도 명확해집니다.

## Parser recovery는 token을 버리는 정책입니다

오류를 보고한 뒤 parser가 같은 token에서 다시 실패하면 무한 loop가 됩니다. Recovery는 최소한 하나를 보장해야 합니다.

- token index가 전진합니다.
- 현재 construct가 error node로 닫힙니다.
- synchronization token까지 건너뜁니다.

Statement language의 단순 synchronization set 예:

```text
;  }  let  var  if  while  return  fn  EOF
```

하지만 모든 오류에서 `;`까지 버리면 nested expression의 유용한 구조를 잃을 수 있습니다. Recovery level을 나눕니다.

1. insertion: 누락된 `)`처럼 안전한 token을 가상 삽입
2. deletion: 명백한 불필요 token 하나를 건너뜀
3. local sync: expression delimiter까지 이동
4. statement sync: 다음 statement boundary까지 이동
5. file abort: invariant를 유지할 수 없을 때 중단

가상 token은 실제 source span이 없으므로 zero-width span과 `synthetic` 표시를 가집니다.

## Error node와 error type으로 연쇄 진단을 줄입니다

다음 source를 생각합니다.

```text
let x: Int = unknown + true;
```

`unknown`의 resolution 오류 뒤 type checker가 다시 “unknown의 type을 모름”, “+의 왼쪽 type이 잘못됨”, “Int에 대입 불가”를 모두 출력하면 첫 원인이 묻힙니다.

해결 방법은 error sentinel을 사용해 후속 phase가 이미 보고된 실패를 인식하게 하는 것입니다.

```text
ErrorSymbol
ErrorType
ErrorExpression
```

규칙 예:

```text
ErrorType + T  => ErrorType, 새 mismatch 진단 없음
assign ErrorType to T => 새 mismatch 진단 없음
```

모든 오류를 숨기면 안 됩니다. 같은 식의 독립된 오른쪽 오류는 계속 보고할 수 있습니다. Suppression 단위와 error origin을 기록합니다.

## Diagnostic budget과 deduplication

잘못된 generated file이나 editor 중간 상태에서 수천 개 오류가 발생할 수 있습니다.

- 파일별·phase별 최대 diagnostic 수를 정합니다.
- 같은 code와 span의 진단을 중복 제거합니다.
- budget 초과 시 `추가 오류 N개 생략` note를 남깁니다.
- cancellation이 요청되면 오래된 진단을 게시하지 않습니다.

Budget은 compiler crash를 숨기는 장치가 아니라 사용자 신호를 보존하는 장치입니다.

## Fix는 적용 안전성을 가져야 합니다

`fix-it`은 단순 문자열 제안이 아닙니다.

```text
TextEdit(source_version, start, end, replacement)
Applicability = always | maybe | unsafe
```

다음 조건을 확인합니다.

- diagnostic을 계산한 source version과 적용 대상이 같습니다.
- edit 범위가 겹치지 않습니다.
- 이름 변경이 scope 충돌을 만들지 않습니다.
- formatter와 함께 적용해도 의미가 바뀌지 않습니다.

자동 적용할 수 없는 fix는 설명으로만 제공합니다.

## CLI 종료 코드

Mica capstone은 다음 기준을 사용합니다.

| 종료 코드 | 의미 |
|---:|---|
| 0 | 요청 성공, error diagnostic 없음 |
| 1 | 사용자 source 오류 또는 정의된 runtime 오류 |
| 2 | 잘못된 CLI 사용, 구현 미완성 또는 내부 compiler 오류 |

Diagnostic JSON은 stdout, 사람이 읽는 renderer는 stderr처럼 command별 channel contract도 고정합니다. 같은 command가 성공과 실패에서 출력 위치를 바꾸지 않게 합니다.

## 내부 오류를 잡아먹지 않습니다

다음은 사용자 오류가 아닙니다.

- AST node span이 source 범위를 벗어남
- resolved reference가 삭제된 symbol을 가리킴
- IR block에 terminator가 두 개 있음
- VM stack effect와 opcode 명세가 불일치

`internal compiler error`로 구분하고 phase, stable node id, 최소 stack trace와 재현 정보를 남깁니다. 민감한 source와 절대 경로는 기본 출력에서 제외할 수 있습니다.

## 실습 연결

[Source와 diagnostic exercise](../../exercises/01-source-and-diagnostics/README.md)에서 stable code 목록, JSON schema와 renderer를 설계합니다. Mica의 기준 code는 [diagnostic 명세](../../exercises/08-mica-capstone/spec/diagnostics.md)에 있습니다.

## 점검 질문

1. primary와 secondary span의 선택 기준은 무엇입니까?
2. parser recovery가 항상 전진한다는 것을 어떻게 검사합니까?
3. ErrorType이 숨겨야 하는 진단과 유지해야 하는 진단은 무엇입니까?
4. fix-it을 자동 적용하기 전에 어떤 version과 conflict를 확인합니까?
5. 사용자 오류와 내부 오류의 종료 코드·로그·재현 정보는 어떻게 다릅니까?
