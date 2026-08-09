# Trace schema

## Event envelope

모든 예제와 실습은 다음 필드를 기준으로 trace를 기록합니다.

```json
{
  "step": 17,
  "virtual_time": 120,
  "event_id": "ev-0017",
  "kind": "deliver",
  "actor": "simulator",
  "target": "node-b",
  "message_id": "msg-009",
  "before_hash": "...",
  "after_hash": "...",
  "details": {}
}
```

## Protocol message

```json
{
  "message_id": "msg-009",
  "kind": "AppendEntries",
  "sender": "node-a",
  "receiver": "node-b",
  "term": 4,
  "payload": {
    "prev_log_index": 7,
    "prev_log_term": 3,
    "entries": [],
    "leader_commit": 6
  }
}
```

## Client operation

```json
{
  "operation_id": "op-41",
  "process": "client-2",
  "type": "invoke",
  "operation": "compare_and_set",
  "input": {"key":"x","expected":1,"next":2},
  "target": "node-a",
  "step": 40
}
```

completion은 같은 `operation_id`를 사용합니다.

## State summary

모든 internal value를 trace에 복사하지 않고 invariant와 debugging에 필요한 summary를 둡니다.

```json
{
  "node": "node-a",
  "incarnation": 2,
  "role": "LEADER",
  "term": 4,
  "voted_for": "node-a",
  "last_log_index": 9,
  "last_log_term": 4,
  "commit_index": 8,
  "last_applied": 8,
  "snapshot_index": 5,
  "configuration_epoch": 3
}
```

## 원칙

- ID는 run 안에서 유일합니다.
- wall clock이 아니라 event step과 virtual time을 기준으로 정렬합니다.
- before·after hash 계산에 nondeterministic map order를 사용하지 않습니다.
- secret이나 실제 사용자 data를 trace에 넣지 않습니다.
- large payload는 digest와 별도 artifact reference를 사용합니다.
- schema version을 event에 포함할 수 있습니다.
