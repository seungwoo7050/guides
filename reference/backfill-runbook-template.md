# Backfill runbook template

## 1. 식별

- Backfill ID:
- 담당자:
- 승인자:
- 원인:
- 관련 incident/issue:

## 2. 논리 범위

- Data interval: `[start, end)`
- Timezone:
- 대상 grain/partition:
- 제외 범위:

## 3. 고정 입력

| Source | Snapshot/offset | Schema | Retention 확인 |
|---|---|---|---|
| TODO | TODO | TODO | TODO |

- Transform revision:
- Reference data version:
- Configuration version:

## 4. 격리

- Live writer와의 충돌 방지:
- Backfill staging 위치:
- Resource quota/concurrency:
- Consumer-visible output 변경 시점:

## 5. Canary

- Canary interval/partition:
- 예상 row/key/aggregate:
- 승인 조건:
- 중단 조건:

## 6. 전체 실행

- 실행 명령:
- Interval 분할:
- Retry 정책:
- Checkpoint/resume key:
- 이미 완료한 interval 판정:

## 7. Reconciliation

- Count:
- Key/anti-join:
- Aggregate:
- Hash/sample:
- 허용 오차와 이유:

## 8. Publish

- Publish mode:
- 이전 snapshot:
- 새 snapshot:
- Consumer notification:

## 9. Rollback

- Pointer/snapshot 복구:
- 잘못된 output 격리:
- Downstream 재처리:
- 재검증:

## 10. 종료 근거

- Run/lineage ID:
- Quality report:
- Reconciliation report:
- 알려진 한계:
- 후속 작업:
