# 분산 관측 식별자 연결

## 목표

한 사용자 요청이 HTTP 명령, 이벤트 발행과 구독자 처리로 바뀌어도 같은 업무 흐름을 추적할 수 있게 식별자의 역할을 분리합니다.

## 문제 계약

실습은 다음 식별자를 사용합니다.

- `requestId`: 하나의 HTTP 요청
- `operationId`: 재시도 전체에서 유지되는 업무 명령
- `eventId`: 한 이벤트 봉투
- `causationId`: 현재 이벤트를 만든 명령이나 이전 이벤트
- `correlationId`: 전체 업무 흐름
- `aggregateId`: 상태가 바뀌는 업무 대상

이미 upstream에서 시작한 흐름은 5인자 `receive`에 `traceId`와 `correlationId`를
명시해 전달합니다. 기존 3인자 `receive`는 호환성을 위해 request ID에서 기본값을
만들지만, 명시적으로 받은 값을 덮어쓰는 경로로 사용하지 않습니다.

로그에는 필요한 식별자를 남기되, metric tag에는 `operationId`나 `aggregateId`처럼 값의 종류가 계속 늘어나는 식별자를 넣지 않습니다. 같은 이벤트가 재전달되면 처리 시도 로그는 여러 개 남을 수 있지만 업무 효과는 하나만 남아야 합니다.

## 실패 조건

skeleton은 hop마다 새 correlation ID를 만들고, operation ID를 metric tag에 넣습니다. 이 경우 로그를 연결하기 어렵고 metric 시계열 수가 요청 수에 비례해 늘어납니다.

## 권장 구현 순서

`reference/` 전체가 하나의 numbering scope입니다. 아래 Implementation 번호는 권장
구현 순서이며 실제 과거 작성 순서를 뜻하지 않습니다.

| 구현 단계 | 파일·경계 | 책임 |
|---:|---|---|
| Implementation 1 | `Command`, `Event`, `Observation` | 서로 다른 수명 주기의 식별자와 관찰 결과를 고정합니다. |
| Implementation 2 | `Flow` | 관찰 기록, event claim과 metric state를 소유합니다. |
| Implementation 2-1 | `Flow.receive` overloads | 명시적 ingress 값을 보존하고 기존 API 기본값을 위임합니다. |
| Implementation 2-2 | `Flow.publish` | 명령의 식별자와 causation을 event로 전달합니다. |
| Implementation 2-3 | `Flow.consume` | 중복 전달과 event ID 충돌을 효과 변경 전에 구분합니다. |
| Implementation 2-4 | `metricTagKeys` | 낮은 cardinality key만 허용합니다. |
| Implementation 2-5 | `observe` | hop 관찰값과 bounded metric을 함께 기록합니다. |

먼저 `./scripts/new-workspace.sh observability-correlation`로 안전한 복사본을 만들고
`.workspace/observability-correlation`만 수정합니다. 정본 검사를 통과하고 식별자별
수명 주기를 자기 말로 설명한 뒤에만 `reference/`의 위 순서와 결과를 비교합니다.

## 완료 기준

- 명령·이벤트·구독 로그가 하나의 trace와 correlation 흐름으로 연결됩니다.
- upstream에서 명시한 trace·correlation을 ingress와 이후 hop이 그대로 유지합니다.
- causation ID가 직접 원인을, operation ID가 재시도 전체의 업무 명령을 가리킵니다.
- metric tag 검사기가 고카디널리티 식별자를 거절하고 중복 효과는 하나로 유지합니다.

## 자기 설명

- trace ID와 operation ID를 같은 값으로 고정하면 어떤 분석이 어려워집니까?
- 고카디널리티 ID를 metric label로 쓰면 운영 비용과 질의에 어떤 영향이 있습니까?

## 검증

학습자 복사본은 다음 정본 명령으로 검사합니다.

```sh
./scripts/verify-java.sh .workspace/observability-correlation
```

workspace 검사가 통과하고 자기 설명을 마친 뒤에만 `reference/`의 관찰 결과와
권장 구현 순서를 비교합니다.

reference는 다음을 만족합니다.

- 명령과 이벤트, 구독자 로그가 같은 correlation ID를 가집니다.
- 이벤트의 causation ID가 원래 operation ID를 가리킵니다.
- 중복 전달은 여러 처리 시도로 보이지만 업무 효과는 하나입니다.
- metric tag key는 낮은 cardinality의 `component`, `outcome`만 사용합니다.
