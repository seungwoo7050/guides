# 데이터 incident 검토 template

## 1. 영향

- 영향을 받은 dataset과 consumer:
- 잘못된 grain/interval/snapshot:
- 시작·탐지·완화·복구 시각:
- 잘못된 의사결정 또는 downstream 영향:

## 2. 사실 타임라인

| 시각 | 사건 | 근거 | 당시 상태 |
|---|---|---|---|
| TODO | TODO | log/metric/lineage/query | TODO |

사실, 가설과 판단을 구분한다.

## 3. 탐지

- 최초 신호:
- process signal 또는 data signal:
- 탐지되지 않은 기간:
- 누락된 quality/freshness/lineage:

## 4. 데이터 경로

```text
source snapshot/offset
→ ingestion
→ transform state
→ physical files/table snapshot
→ consumer view
```

각 단계의 version과 owner를 기록한다.

## 5. 원인

- 직접 원인:
- 계약 또는 경계의 근본 원인:
- 왜 기존 검사가 거부하지 못했는가:
- 왜 blast radius가 커졌는가:

“사람이 실수했다”를 root cause로 끝내지 않는다.

## 6. 완화와 복구

- publish 중단 또는 snapshot rollback:
- source 보존:
- backfill/replay 범위:
- reconciliation 결과:
- downstream coordination:

## 7. 재발 방지

| 조치 | 소유자 | 기한 | 검증 방법 |
|---|---|---|---|
| TODO | TODO | TODO | TODO |

분류 예:

- contract/schema
- test/fixture
- quality/publish gate
- observability/lineage
- runbook/automation
- access/retention

## 8. 잔여 위험

- 아직 증명하지 못한 범위:
- 허용한 tolerance:
- 다음 incident에서 필요한 추가 evidence:
