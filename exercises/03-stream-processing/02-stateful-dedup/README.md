# Stateful deduplication과 entity version

Delivery duplicate, conflicting event identity와 entity version ordering을 분리해 deterministic state를 만든다.

문서: [`state·dedup·delivery`](../../../docs/03-stream-processing/03-state-deduplication-and-delivery.md)

## 구현 계약

```python
def apply_events(events: list[dict], dedup_horizon: int) -> dict: ...
```

- 같은 event ID와 같은 logical payload는 duplicate다.
- 같은 event ID에 여러 payload variant가 있으면 그 ID 전체가 sticky conflict이며 어떤 variant도 적용하지 않는다.
- 같은 entity/version에 다른 operation/value가 있어도 임의로 하나를 선택하지 않는다.
- 낮은 version은 stale이고 DELETE도 versioned state다.
- dedup horizon 밖 delivery ID는 정리해도 latest entity state는 유지한다.

반환값은 `state`, `stats`, 정렬된 `conflicts`, cutoff 안의 `retained_event_ids`를 포함한다. `stats.conflict`는 distinct conflict event ID 수다.

## 완료 기준

- A/B/A conflict와 모든 input permutation에서 같은 결과를 만든다.
- identical duplicate, stale update, delete 뒤 old update와 horizon cutoff를 구분한다.
- conflicted ID가 state나 retained dedup ID로 다시 들어오지 않는다.

## 자기 설명

1. delivery event ID의 중복 판정과 entity/version의 최신 상태 판정은 어떤 서로 다른 질문에 답하는가?
2. A/B/A conflict에서 first-wins나 last-wins 대신 identity 전체를 sticky conflict로 격리해야 하는 이유는 무엇인가?
3. dedup horizon 뒤 event ID를 정리하면서도 latest entity state와 delete version을 유지해야 하는 이유는 무엇인가?

## 검증

```bash
./scripts/new-workspace.sh exercises/03-stream-processing/02-stateful-dedup
./scripts/check-workspace.sh exercises/03-stream-processing/02-stateful-dedup
```

초기 skeleton은 `GUIDE_SEMANTIC:stateful-dedup`으로 실패한다.
