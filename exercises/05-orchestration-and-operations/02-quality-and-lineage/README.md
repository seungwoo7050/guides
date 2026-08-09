# 품질 판정과 run-level lineage

pipeline process가 성공했다는 사실과 consumer-visible data가 계약을 만족한다는 사실을 분리한다. 품질 판정과 lineage event를 같은 run·input snapshot·output snapshot·code revision에 연결한다.

문서: [`품질·lineage·freshness·관측`](../../../docs/05-orchestration-and-operations/03-quality-lineage-freshness-and-observability.md)

## 구현 계약

`solution.py`는 다음 함수를 제공한다.

```python
def evaluate_and_emit(
    rows: list[dict],
    *,
    run_id: str,
    job_name: str,
    input_dataset: dict,
    output_dataset: dict,
    code_revision: str,
) -> dict: ...
```

record grain은 `id` 한 개다. `id`, `event_time`, `value`는 필수다.

반환값에는 다음이 있어야 한다.

- `quality`: row count, distinct key 수, duplicate key, 필수값 null, invalid event time, latest event time, passed
- `lineage`: run ID, job, code revision, input/output dataset의 namespace·name·snapshot, event type
- 품질 실패 시 `event_type=FAIL`이고 publish된 output 목록은 비어 있음
- 품질 통과 시 `event_type=COMPLETE`이고 output snapshot이 포함됨

## 완료 기준

- duplicate와 required null을 각각 측정한다.
- 품질 실패가 process exception 없이도 `FAIL` lineage를 만든다.
- input과 output 이름만 아니라 snapshot/version을 기록한다.
- code revision과 run ID로 같은 결과를 다시 조사할 수 있다.
- 비어 있지 않은 run/job/revision과 versioned dataset identity가 없으면 lineage 생성을 거부한다.

## 자기 설명

1. “task succeeded” metric만으로 데이터 품질을 알 수 없는 이유는 무엇인가?
2. column-level lineage를 항상 수집하는 것과 run-level lineage부터 시작하는 것의 trade-off는 무엇인가?
3. failed output을 publish하지 않아도 failure lineage를 남겨야 하는 이유는 무엇인가?

## 검증

```bash
./scripts/new-workspace.sh exercises/05-orchestration-and-operations/02-quality-and-lineage
./scripts/check-workspace.sh exercises/05-orchestration-and-operations/02-quality-and-lineage
```

초기 skeleton은 `GUIDE_SEMANTIC:quality-lineage`로 실패한다.
