# Trace format

모든 event는 [정본 trace schema](../../../reference/trace-schema.md)의 다음 14개 field를 정확히 가집니다.

```json
{
  "schema_version": 1,
  "run_id": "run-001",
  "step": 1,
  "virtual_time": 0,
  "kind": "deliver",
  "event_id": "event-1",
  "actor": "A",
  "target": "B",
  "message_id": "m1",
  "delivery_id": "d1",
  "state_before_hash": "<64-lowercase-hex>",
  "state_after_hash": "<64-lowercase-hex>",
  "invariant_results": [],
  "details": {"term": 3}
}
```

추가할 field:

- code/config identity: `TODO`
- seed와 explicit schedule: `TODO`
- disk generation: `TODO`
- client invocation/completion: `TODO`
- 첫 invariant 위반 표현: `TODO`

client `operation_id`, source/config identity와 full state artifact는 `details` 또는 별도 run manifest에 두며 공통 envelope field를 바꾸지 않습니다. 각 event는 다음 canonical envelope을 사용합니다.

```text
schema_version, run_id, step, virtual_time, event_id, kind,
actor, target, message_id, delivery_id,
state_before_hash, state_after_hash, invariant_results, details
```

logical duplicate는 같은 `message_id`, 서로 다른 `delivery_id`로 기록합니다.
