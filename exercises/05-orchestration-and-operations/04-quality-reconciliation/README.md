# Quality quarantine와 reconciliation

Source와 target을 독립 검증하고 invalid/conflicting record를 quarantine한 뒤 key, value와 currency별 signed amount를 대사한다.

문서:

- [`backfill·replay·reconciliation`](../../../docs/05-orchestration-and-operations/02-backfill-replay-and-reconciliation.md)
- [`quality·lineage·freshness·observability`](../../../docs/05-orchestration-and-operations/03-quality-lineage-freshness-and-observability.md)

## 구현 계약

```python
def validate_records(records: list[dict]) -> dict: ...
def reconcile(source_records: list[dict], target_records: list[dict]) -> dict: ...
```

- `id`는 nonempty string, currency는 세 자리 대문자, amount는 nonnegative integer, status는 `SETTLED` 또는 `REFUNDED`다.
- identical duplicate는 한 번만 유효하지만 같은 ID의 payload variant는 ID 전체를 sticky quarantine한다.
- reconciliation은 count, missing/extra key, `mismatched_keys`, currency별 signed net과 양쪽 quarantine을 반환한다.
- `matched=true`는 quarantine이 없고 key/value/currency aggregate가 모두 일치할 때만 가능하다.

## 완료 기준

- A/B/A 순서에서도 conflict ID가 다시 valid가 되지 않고 모든 관련 record evidence가 남는다.
- count와 global amount가 우연히 같아도 key/value 또는 currency 차이를 찾는다.
- input을 수정하지 않고 deterministic한 evidence를 반환한다.

## 자기 설명

1. source와 target count 또는 전체 amount가 같아도 reconciliation이 실패해야 하는 key·value·currency 사례는 무엇인가?
2. A/B/A conflict를 sticky quarantine에 남기지 않으면 이후 duplicate가 어떤 잘못된 승인을 만들 수 있는가?
3. source와 target을 독립 검증한 quarantine evidence가 repair run과 재-publish 판단에 왜 필요한가?

## 검증

```bash
./scripts/new-workspace.sh exercises/05-orchestration-and-operations/04-quality-reconciliation
./scripts/check-workspace.sh exercises/05-orchestration-and-operations/04-quality-reconciliation
```

초기 skeleton은 `GUIDE_SEMANTIC:quality-reconciliation`으로 실패한다.
