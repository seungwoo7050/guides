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
python3 model.py fixtures/w1c-status.json --check
python3 model.py fixtures/two-before-isr.json --check
python3 model.py fixtures/burst-overflow.json --check
python3 model.py fixtures/reset-policy.json --check
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

- `status_register`: ISR가 snapshot하고 write-one-to-clear(W1C) mask로 지우는 bit
- `pending`: capacity가 제한된 hardware-side event 목록
- `queue`: ISR와 worker 사이의 bounded handoff
- `generation`: disable/re-enable session을 구분
- `timestamp`, `raw_status`: worker가 원래 사건을 재구성하는 immutable evidence
- `dropped`: queue full로 잃은 event
- `hardware_overrun`: hardware-side pending capacity를 넘은 event
- `stale`: 이전 generation의 event
- `spurious`: pending status 없이 실행된 ISR

`RESET`은 volatile pending/status/worker queue를 비우지만 진단 counter와 session
generation을 보존하는 teaching policy를 사용합니다. 실제 MCU에서 무엇이 retained되는지는
reset 종류와 SoC 문서를 확인해야 합니다.

`reference/model.py`가 완성 reference이고 `starter/model.py`는 정상 경로 일부만 있는
의도적인 미완성 시작점입니다. `known-wrong/`에는 W1C를 일반 assignment로 취급하거나,
queue bound와 generation을 제거한 반례가 있습니다. 전체 공개 계약은 실습 checker로
확인합니다.

```sh
python3 exercises/02-interrupt-event-path/check.py \
  --submission examples/interrupt-event-model/reference/model.py
```

실제 hardware는 level/edge trigger, coalesced status, FIFO 깊이와 clear semantic이
다릅니다. 이 모델의 bit와 capacity는 교육용 contract이며 해당 device의 interrupt
latency, ordering, register side effect나 electrical behavior를 주장하지 않습니다.
