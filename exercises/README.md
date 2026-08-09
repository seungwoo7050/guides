# 실습 안내

실습은 완성된 reference 구현을 제공하지 않습니다. 각 문제는 초기 상태, event fixture, 제출 산출물과 완료 조건을 제공합니다. 정답 코드를 복사하는 대신 trace를 판정하고 자신의 구현 또는 설계를 공개 계약에 맞춥니다.

## 진행 순서

```text
문서 읽기
→ fixture를 손으로 추적
→ invariant와 예상 결과 작성
→ 작은 검사기 또는 구현 작성
→ fixture 변형
→ 위반 trace 최소화
```

## 목록

| Part | 실습 | 중심 질문 |
|---|---|---|
| 1 | [causality trace](01-model-and-time/01-causality-trace/README.md) | 어떤 사건이 causal하고 어떤 사건이 concurrent합니까? |
| 1 | [failure model](01-model-and-time/02-failure-model/README.md) | 같은 trace에서 어떤 보장을 주장할 수 있습니까? |
| 2 | [consistency history](02-replication-and-consistency/01-consistency-history/README.md) | client history가 어떤 consistency를 만족합니까? |
| 2 | [quorum register](02-replication-and-consistency/02-quorum-register/README.md) | quorum 교차와 version 선택이 충분합니까? |
| 3 | [election trace](03-consensus-and-membership/01-election-trace/README.md) | vote·term·log freshness가 election safety를 지킵니까? |
| 3 | [log reconciliation](03-consensus-and-membership/02-log-reconciliation/README.md) | conflicting suffix와 commit을 어떻게 복구합니까? |
| 3 | [client session](03-consensus-and-membership/03-client-session/README.md) | response loss와 snapshot 뒤 effect를 한 번으로 유지합니까? |
| 4 | [shard rebalance](04-partitioning-and-atomicity/01-shard-rebalance/README.md) | migration 중 write authority가 하나입니까? |
| 4 | [atomic commit](04-partitioning-and-atomicity/02-atomic-commit/README.md) | PREPARED·decision·recovery가 atomicity를 보존합니까? |
| 5 | [linearizability](05-validation/01-linearizability/README.md) | legal sequential ordering이 존재합니까? |
| 5 | [simulation plan](05-validation/02-simulation-plan/README.md) | 어떤 event·fault·artifact로 protocol을 검증합니까? |

## 제출 형식

각 실습 디렉터리 옆에 자신의 작업 공간을 만들 수 있습니다.

```text
.workspace/<exercise>/
├── analysis.md
├── invariants.md
├── result.json
└── optional implementation files
```

`analysis.md`에는 최소한 다음을 기록합니다.

- system·failure model
- initial state
- event별 state change
- 첫 위반 또는 decision 지점
- 보장할 수 있는 것과 없는 것
- fixture를 변형한 추가 사례

## 정답 확인

고정된 답지 대신 다음 방식으로 검토합니다.

- 문서의 definition과 invariant에 다시 대입합니다.
- 작은 checker를 직접 작성합니다.
- 다른 event order를 만들어 반례를 찾습니다.
- capstone simulator에 같은 schedule을 옮깁니다.
- 실제 논문의 state·proof와 비교합니다.

판정이 여러 설계 선택에 따라 달라질 수 있는 문제는 선택한 가정과 API 계약을 먼저 적으면 됩니다.
