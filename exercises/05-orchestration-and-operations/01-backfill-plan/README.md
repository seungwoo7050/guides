# Backfill 실행 계획

과거 data interval을 다시 계산하는 작업을 일회성 명령이 아니라 검토·중단·재개·대사 가능한 운영 계약으로 설계한다.

문서:

- [`orchestration과 data interval`](../../../docs/05-orchestration-and-operations/01-orchestration-data-intervals-and-idempotency.md)
- [`backfill·replay·reconciliation`](../../../docs/05-orchestration-and-operations/02-backfill-replay-and-reconciliation.md)

## 산출물

`plan.json`에 다음을 기록한다.

- `backfill_id`, 원인과 소유자
- timezone-aware `[start, end)` data interval
- `lsn:`, `snapshot:`, `version:`, `etag:` 또는 `sha256:` prefix와 공백 없는 고정 식별자로 pin한 source snapshot/offset (`snapshot:latest` 같은 floating 값은 금지)
- `git:<7-40 hex>` transform commit과 공백 및 `latest/current/main/head/tip`이 없는 정확한 schema·reference data version
- live write와 backfill output의 격리 방식
- canary interval과 stop condition
- publish·resume·rollback 절차
- count·key·aggregate를 포함한 reconciliation

## 완료 기준

- 동일 plan을 다시 실행해도 같은 logical interval과 input을 사용한다.
- live pipeline과 backfill이 같은 partition을 동시에 덮어쓰지 않는다.
- 작은 canary 결과를 대사한 뒤 전체 범위를 publish한다.
- 실패 지점 뒤 이미 완료한 interval을 식별해 재개할 수 있다.
- rollback이 코드 rollback만이 아니라 consumer-visible snapshot 복구까지 설명한다.
- repository 안의 계획은 `dry_run=true`를 유지하고 실제 자원 변경은 사람 승인 뒤 별도 환경에서 수행한다.

## 자기 설명

1. DAG run ID와 data interval을 동일시하면 왜 재시도와 backfill에서 중복이 생기는가?
2. source의 현재 상태를 다시 읽는 것이 과거 결과의 재현이 아닌 이유는 무엇인가?
3. row count가 같아도 key 누락과 값 오염을 발견하지 못할 수 있는 이유는 무엇인가?

## 검증

```bash
./scripts/new-workspace.sh exercises/05-orchestration-and-operations/01-backfill-plan
./scripts/check-workspace.sh exercises/05-orchestration-and-operations/01-backfill-plan
```

초기 skeleton은 `GUIDE_SEMANTIC:backfill-plan`으로 실패한다.

이 checker는 JSON 구조, pinning 표현과 안전 gate만 자동 검사한다. 실제 source snapshot의 존재·접근 권한, canary 실행 결과, stop condition의 업무 적합성, publish/rollback 명령과 consumer 복구 가능성은 runtime evidence와 사람 검토로 확인해야 한다. 구조 검사 통과만으로 backfill 실행 준비가 완료됐다고 판단하지 않는다.
