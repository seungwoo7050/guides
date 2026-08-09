# Trace format

모든 event는 최소한 다음 field를 가집니다.

```json
{
  "step": 1,
  "virtual_time": 0,
  "event_kind": "deliver_message",
  "event_id": "event-1",
  "source": "A",
  "target": "B",
  "message_id": "m1",
  "term": 3,
  "state_before": {},
  "state_after": {},
  "invariants": {}
}
```

추가할 field:

- code/config identity: `TODO`
- seed와 explicit schedule: `TODO`
- disk generation: `TODO`
- client invocation/completion: `TODO`
- 첫 invariant 위반 표현: `TODO`
