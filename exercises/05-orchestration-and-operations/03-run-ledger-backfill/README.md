# Run ledger와 backfill planning

Logical date와 attempt로 run identity를 기록하고 명시적 reprocessing policy에 따라 bounded backfill plan을 만든다.

문서:

- [`orchestration과 data interval`](../../../docs/05-orchestration-and-operations/01-orchestration-data-intervals-and-idempotency.md)
- [`backfill·replay·reconciliation`](../../../docs/05-orchestration-and-operations/02-backfill-replay-and-reconciliation.md)

## 구현 계약

```python
def plan_backfill(existing_runs, start_date, end_date, policy, max_active) -> list[dict]: ...
def transition(run: dict, new_status: str) -> dict: ...
```

- active status는 `PLANNED`, `RUNNING`, `VALIDATING`이며 어떤 active attempt도 중복 plan을 막는다.
- `none`은 terminal date를 재처리하지 않고, `failed`는 latest FAILED만, `completed`는 어떤 latest terminal도 재처리한다. 기록이 없는 날짜는 모든 policy에서 만든다.
- terminal status는 `FAILED`, `PUBLISHED`, `SUPERSEDED`다.
- 모든 인자와 ledger row는 capacity가 0이어도 먼저 검증한다.

## 완료 기준

- inclusive ISO date 범위, latest positive attempt와 deterministic next attempt를 계산한다.
- duplicate run identity, unknown status, invalid date/range와 transition을 거부한다.
- 상태 변경은 input run을 수정하지 않는다.

## 자기 설명

1. job, logical run, attempt와 output version을 하나의 ID로 합치면 retry와 publish 판단에서 어떤 모호함이 생기는가?
2. active attempt가 있을 때 reprocessing policy와 무관하게 새 plan을 막아야 하는 이유는 무엇인가?
3. capacity가 0이어도 날짜·ledger row를 먼저 검증하는 순서가 잘못된 입력과 재개 evidence에 왜 중요한가?

## 검증

```bash
./scripts/new-workspace.sh exercises/05-orchestration-and-operations/03-run-ledger-backfill
./scripts/check-workspace.sh exercises/05-orchestration-and-operations/03-run-ledger-backfill
```

초기 skeleton은 `GUIDE_SEMANTIC:run-ledger-backfill`로 실패한다.
