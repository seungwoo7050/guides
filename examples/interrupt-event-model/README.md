# interrupt event model

`model.py`는 다음 경로를 작은 상태 기계로 표현합니다.

```text
ENABLE generation
→ hardware RAISE
→ ISR acknowledge + bounded queue
→ WORK consume
```

## 실행

```sh
python3 model.py fixtures/normal.json --check
python3 model.py fixtures/queue-overflow.json --check
python3 model.py fixtures/stale-generation.json --check
python3 model.py fixtures/spurious.json --check
```

fixture 형식:

```json
{
  "capacity": 2,
  "events": [
    {"op": "ENABLE"},
    {"op": "RAISE", "sample": 17},
    {"op": "ISR"},
    {"op": "WORK"}
  ],
  "expected": {
    "handled_samples": [17],
    "dropped": 0
  }
}
```

`expected`는 final result의 부분 집합입니다. 모델은 예상하지 않은 추가 field도 출력합니다.

## 상태 의미

- `pending`: hardware status를 단순화한 event 목록
- `queue`: ISR와 worker 사이의 bounded handoff
- `generation`: disable/re-enable session을 구분
- `dropped`: queue full로 잃은 event
- `stale`: 이전 generation의 event
- `spurious`: pending status 없이 실행된 ISR

실제 hardware는 level/edge trigger, coalesced status, FIFO와 clear semantic이 다릅니다. 이 모델은 어떤 정책을 선택해야 하는지 보여 줄 뿐 해당 device의 동작을 주장하지 않습니다.
