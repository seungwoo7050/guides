# Replay-safe batch

동일 input record를 여러 번 읽거나 같은 interval을 재실행해도 동일한 논리 snapshot을 publish하는 작은 batch 모델을 구현한다.

문서: [`bounded data와 replay-safe batch`](../../../docs/02-batch-processing/01-bounded-data-and-replay-safe-batch.md)

## 구현 계약

`solution.py`는 다음 함수를 제공한다.

```python
def aggregate(records: list[dict]) -> list[dict]: ...
def publish(root: Path, logical_id: str, rows: list[dict]) -> str: ...
```

`aggregate`:

- `event_id` duplicate를 한 번만 반영한다.
- `sales_date`, `currency`별 `amount_minor` 합계를 만든다.
- output ordering이 입력 순서와 무관하다.

`publish`:

- 논리 rows의 content hash를 snapshot ID로 사용한다.
- snapshot을 staging에서 완성한 뒤 `CURRENT` pointer를 교체한다.
- 같은 rows를 재실행하면 같은 snapshot ID를 반환한다.
- consumer는 항상 완성된 snapshot만 읽는다.

## 완료 기준

- duplicate event를 추가해도 합계가 변하지 않는다.
- 입력 순서를 바꿔도 결과와 snapshot ID가 같다.
- 같은 run을 두 번 publish해도 snapshot directory가 중복되지 않는다.
- `CURRENT`가 가리키는 manifest와 data를 읽을 수 있다.

## 자기 설명

1. run ID가 아니라 content ID를 snapshot ID로 사용한 장단점은 무엇인가?
2. 실제 object storage에서 local `os.replace`와 같은 atomic rename을 기대하면 안 되는 이유는 무엇인가?
3. 실제 table format에서는 어떤 metadata commit이 이 pointer 역할을 하는가?

## 검증

```bash
./scripts/new-workspace.sh exercises/02-batch-processing/01-replay-safe-batch
./scripts/check-workspace.sh exercises/02-batch-processing/01-replay-safe-batch
```

초기 skeleton은 `GUIDE_SEMANTIC:replay-safe-batch`로 실패한다.
