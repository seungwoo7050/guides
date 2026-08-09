# Trace, replay, 비용과 품질 지표

## 목표

최종 pass/fail만 보지 않고 코딩 에이전트가 어떤 근거로 무엇을 읽고 바꾸고 실행했는지 재현합니다. 품질·비용·지연·사용자 개입을 함께 측정합니다.

## trace 계층

```text
Session span
├── repository discovery
├── model turn
│   ├── context assembly
│   ├── provider request
│   └── action parse
├── tool call
│   ├── policy·approval
│   ├── execution
│   └── receipt
├── edit iteration
├── command/test run
└── verifier
```

trace ID를 model, tool, process, patch와 evaluation result에 연결합니다.

## 기록할 identity

- session·task·instance
- repository base와 workspace revision
- runtime·model·adapter·prompt·tool·policy version
- context manifest digest
- action·patch·command digest
- sandbox profile
- verifier version

모델 이름만 기록하면 회귀를 재현할 수 없습니다.

## replay 수준

### Display replay

기록된 event와 artifact를 시간 순서로 보여 줍니다.

### Deterministic runtime replay

기록된 model action을 scripted adapter처럼 재생해 runtime·policy·tool mock을 검사합니다.

### Tool replay

read-only tool을 같은 snapshot에서 재실행해 receipt를 비교합니다.

### Full rerun

같은 model과 environment에서 task를 다시 실행합니다. 모델 비결정성 때문에 동일 경로를 보장하지 않습니다.

각 수준이 보장하는 범위를 구분합니다.

## 품질 metric

### 결과

- resolved rate
- build/test pass
- regression count
- policy violation
- human acceptance

### 행동 효율

- model turn 수
- tool call 수
- 읽은 byte·file 수
- edit iteration 수
- 반복 실패 fingerprint
- rollback 수
- 질문·승인 수

### 변경 품질

- changed paths와 diff size
- unrelated change
- test 추가·수정
- format/generated noise
- hidden test 일반화

### 운영

- wall-clock·model latency·tool latency
- token·cost
- CPU·memory·disk·network
- cancellation latency
- resume 성공률

단일 resolved rate가 모든 trade-off를 보여 주지 않습니다.

## 개인정보와 source 보호

trace에 source code, issue, secret, model input/output이 포함될 수 있습니다.

- 필드별 수집 목적
- raw artifact와 metadata 분리
- access control
- retention 기간
- redaction
- user opt-out
- export·delete
- model provider logging policy

redaction 후에도 path·symbol·error message가 민감할 수 있습니다.

## 비용 attribution

비용을 session 합계만 저장하지 않습니다.

```text
context assembly
investigation turns
repair turns
model retry
search/index
command/test
verifier
human wait
```

어떤 기능 변경이 비용을 늘렸는지 분석할 수 있습니다.

## 회귀 분석

두 runtime version을 비교할 때:

- 같은 task set과 environment
- model snapshot 고정 또는 모델 변화 별도 실험
- seed/repetition
- pass뿐 아니라 행동 metric
- evaluation error 제외
- confidence interval 또는 분산

단일 run 차이를 개선으로 단정하지 않습니다.

## 실패 조건

- 최종 답변 text만 저장합니다.
- raw secret과 source를 무기한 trace에 보존합니다.
- model·prompt·tool·policy version을 구분하지 않습니다.
- 비용 감소를 test skip과 구분하지 않습니다.
- replay가 실제 tool effect를 다시 수행합니다.
- human intervention이 많은 run을 완전 자율 성공으로 집계합니다.

## 완료 조건

- session을 model turn·tool·edit·check·verifier span으로 재구성합니다.
- display replay와 effect 재실행을 분리합니다.
- result, efficiency, change quality와 operation metric을 함께 보고합니다.
- trace privacy·retention·access 정책을 문서화합니다.
