# Trace schema

이 문서는 capstone evidence dossier와 새 trace producer가 공유할 target schema를 정의합니다. 기존 단계 실습의 고정 JSON fixture는 문제에 맞춘 축약 schema를 사용할 수 있으며, capstone으로 옮길 때는 field 대응표 또는 변환기를 함께 남깁니다. schema 모양이 맞는다는 사실만으로 protocol invariant나 consistency가 성립하는 것은 아닙니다.

## Run identity

각 run은 event와 별도로 다음 manifest를 가집니다.

```json
{
  "schema_version": 1,
  "run_id": "run-20260810-001",
  "source": {
    "commit": "<git-sha-or-null>",
    "tree_sha256": "<source-digest>",
    "dirty": false
  },
  "runtime": {
    "implementation": "python",
    "version": "3.12.11",
    "platform": "darwin-arm64"
  },
  "configuration_sha256": "<config-digest>",
  "initial_state_sha256": "<state-digest>",
  "seed": 41,
  "schedule_sha256": "<schedule-digest>",
  "supported_failure_model": [
    "crash-recovery",
    "message-delay",
    "message-drop",
    "message-duplicate",
    "one-way-partition"
  ]
}
```

commit하지 않은 learner workspace는 `commit`을 `null`로 두고 `tree_sha256`와 `dirty: true`를 기록합니다. 같은 seed라도 source·configuration·initial state가 다르면 같은 run을 재현한 것이 아닙니다.

## Event envelope

각 event는 JSON Lines 한 줄 또는 JSON array의 한 원소로 기록합니다.

```json
{
  "schema_version": 1,
  "run_id": "run-20260810-001",
  "step": 17,
  "virtual_time": 120,
  "event_id": "ev-0017",
  "kind": "deliver",
  "actor": "simulator",
  "target": "node-b",
  "message_id": "msg-0009",
  "operation_id": null,
  "before_hash": "<global-state-digest>",
  "after_hash": "<global-state-digest>",
  "details": {}
}
```

필수 공통 field는 `schema_version`, `run_id`, `step`, `virtual_time`, `event_id`, `kind`, `actor`, `before_hash`, `after_hash`, `details`입니다. `target`, `message_id`, `operation_id`는 해당 event에 없으면 `null`로 둡니다.

규칙:

- `event_id`는 run 안에서 유일합니다.
- `step`은 적용 순서를 나타내며 한 run에서 엄격히 증가합니다.
- `virtual_time`은 같은 값이 반복될 수 있지만 step이 증가하는 동안 감소하지 않습니다.
- `before_hash`는 event 적용 직전, `after_hash`는 모든 emitted state update 뒤의 canonical global state digest입니다.
- 한 event의 `after_hash`와 다음 state-transition event의 `before_hash`가 다르면 중간 state change를 별도 event로 기록합니다.
- drop·duplicate·partition·crash 같은 fault도 정상 message와 같은 event stream에 둡니다.

## Canonical hash

state와 manifest digest는 다음 계약을 사용합니다.

```text
UTF-8 JSON
object key를 code point 순서로 정렬
불필요한 whitespace 없음
integer와 string 의미를 바꾸지 않음
SHA-256 lowercase hexadecimal
```

set, unordered map, object address, wall-clock timestamp와 random iteration order를 hash 입력에 직접 사용하지 않습니다. large payload는 content digest와 별도 artifact path로 참조합니다.

## Protocol message

```json
{
  "message_id": "msg-0009",
  "kind": "AppendEntries",
  "sender": "node-a",
  "sender_incarnation": 2,
  "receiver": "node-b",
  "term": 4,
  "configuration_epoch": 3,
  "payload": {
    "prev_log_index": 7,
    "prev_log_term": 3,
    "entries": [],
    "leader_commit": 6
  }
}
```

재전달은 같은 `message_id`를 사용하고 delivery event가 새 `event_id`를 가집니다. logical retry가 새 wire message를 만들면 새 `message_id`와 원래 `operation_id` 또는 `causation_message_id`를 함께 기록합니다.

## Client history

invocation과 completion은 같은 `operation_id`로 연결합니다.

```json
{
  "operation_id": "op-0041",
  "process": "client-2",
  "type": "invoke",
  "operation": "compare_and_set",
  "input": {
    "key": "x",
    "expected": 1,
    "next": 2
  },
  "target": "node-a",
  "step": 40
}
```

```json
{
  "operation_id": "op-0041",
  "process": "client-2",
  "type": "complete",
  "result": "OK",
  "output": 2,
  "source_node": "node-c",
  "step": 57
}
```

timeout은 성공·실패 completion을 발명하지 않습니다. history checker가 pending invocation을 완료·제외하는 정책을 report에 기록합니다. client retry는 새 invocation인지 같은 logical operation의 transport retry인지 구분하고 `(client_id, sequence, fingerprint)`를 보존합니다.

## State summary

모든 internal value를 복사하지 않고 invariant와 debugging에 필요한 summary를 둡니다.

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
  "snapshot_term": 3,
  "configuration_epoch": 3,
  "state_machine_sha256": "<digest>",
  "client_sessions_sha256": "<digest>"
}
```

summary는 원본 durable state나 full log를 대신하지 않습니다. 실패 분석에 필요한 원본 artifact를 run manifest에서 별도로 가리킵니다.

## Fault evidence

fault event의 `details`에는 요청한 fault와 실제 적용 결과를 구분합니다.

```json
{
  "fault_id": "partition-a-to-b-1",
  "requested": {
    "kind": "one-way-partition",
    "from": "node-a",
    "to": "node-b"
  },
  "applied": true,
  "application_evidence": {
    "blocked_link": "node-a->node-b",
    "affected_message_ids": [
      "msg-0011",
      "msg-0014"
    ]
  },
  "cleanup_status": "NOT_REQUIRED_FOR_IN_MEMORY_MODEL"
}
```

fault command을 호출했다는 사실만으로 `applied: true`를 쓰지 않습니다. 실제 adapter에서는 route·network namespace·process·storage 상태 같은 독립적인 관찰 근거와 cleanup 결과를 남깁니다.

## Invariant result

각 checker 실행은 다음처럼 판정과 witness를 남깁니다.

```json
{
  "checker": "state-machine-safety",
  "property": "no conflicting command is applied at one log index",
  "result": "PASS",
  "checked_steps": [
    0,
    412
  ],
  "witness_event_ids": [],
  "limitations": [
    "bounded schedule",
    "crash-recovery without torn writes"
  ]
}
```

`result`는 `PASS`, `FAIL`, `UNVERIFIED` 중 하나입니다. checker input이 없거나 불완전하면 `PASS`가 아니라 `UNVERIFIED`입니다. `FAIL`은 최소 counterexample artifact를 가리켜야 합니다.

## Data와 artifact 안전

- secret, credential, token, 실제 사용자 data와 production payload를 trace에 넣지 않습니다.
- key·value가 민감하면 원문과 저엔트로피 값의 단순 hash를 수집하지 않습니다. 재현에 꼭 필요한 경우 synthetic identifier, type과 length처럼 역추정하기 어려운 최소 metadata만 남깁니다.
- host path, username와 network address는 재현에 필요하지 않으면 정규화합니다.
- artifact path는 run directory 안의 상대 경로로 기록하고 symlink나 `..`로 경계를 벗어나지 않습니다.
- cleanup은 evidence를 지우기 전에 report와 digest 게시가 끝났는지 확인합니다.

## 검증 한계

schema validation은 field와 identity의 기계적 일관성만 확인합니다. 다음은 별도 checker와 사람 검토가 필요합니다.

- state hash가 올바른 protocol state를 포함하는지
- failure가 의도한 계층에 실제 적용됐는지
- invariant가 충분하고 구현과 같은 의미인지
- history checker의 sequential specification과 pending policy가 맞는지
- bounded trace가 다루지 않은 schedule과 지원하지 않는 failure가 무엇인지
