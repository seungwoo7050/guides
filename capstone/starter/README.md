# Replicated KV capstone starter

이 디렉터리는 [통합 과제](../../docs/06-capstone.md)의 protocol core 시작점입니다. 완성된 Raft 구현이나 reference answer가 아닙니다.

## 작업 공간 만들기

```sh
./scripts/new-capstone-workspace.sh
```

helper는 target이 이미 있거나 경로에 symlink가 있으면 중단합니다. 새 starter와 비교하려면 별도 target을 인자로 주며 기존 learner 작업을 덮어쓰지 않습니다.

공개 계약 검사(반드시 복사본 경로를 지정합니다):

```sh
CAPSTONE_ROOT=.workspace/replicated-kv \
  python3 -m unittest discover -s capstone/tests -v
```

canonical starter는 `Node.tick`, `Node.receive`, `Node.submit`의 핵심 transition이 구현되지 않아 일부 검사가 실패해야 정상입니다.

## 제공하는 파일

```text
dskv/
├── types.py       protocol·client·snapshot 타입
├── storage.py     crash 뒤에도 남는 in-memory durable state
├── network.py     명시적 delivery를 사용하는 결정적 network
├── node.py        구현할 protocol core
└── cluster.py     node·network·crash를 조합하는 harness

design/
├── system-model.md
├── sequential-spec.md
├── invariants.md
├── liveness.md
├── trace-format.md
├── membership-review.md
└── sharding-review.md
```

## 고정 API

### Node

```python
Node(node_id, peers, storage, election_timeout)
node.tick(now) -> list[Message]
node.receive(message, now) -> list[Message]
node.submit(request, now) -> tuple[list[Message], ClientResponse | None]
node.drain_responses() -> list[ClientResponse]
node.state_summary() -> dict
node.create_snapshot(through_index) -> Snapshot
```

### Cluster

```python
Cluster(node_ids, election_timeouts, run_id="learner-run")
cluster.tick(node_id)
cluster.tick_all()
cluster.deliver_next()
cluster.deliver(delivery_id=None)
cluster.deliver_all()
cluster.delay(delivery_id, extra_delay)
cluster.drop(delivery_id)
cluster.duplicate(delivery_id, extra_delay=0)
cluster.partition(source, target, bidirectional=False)
cluster.heal(source=None, target=None)
cluster.crash(node_id)
cluster.restart(node_id)
cluster.submit(node_id, request)
cluster.drain_responses()
cluster.state_snapshot()
cluster.run_schedule(schedule)
cluster.trace_document(scenario_id)
cluster.leaders()
cluster.trace
```

message delivery는 자동 background thread가 아니라 `deliver_next` 또는 `deliver_all` 호출로만 일어납니다. 따라서 실패 schedule을 코드와 JSON으로 재생할 수 있습니다.

`message_id`는 logical message identity이고 `delivery_id`는 전송 시도 identity입니다. duplicate는 같은 `message_id`와 새 `delivery_id`를 사용합니다. partition 중 시도한 delivery는 `PARTITION_DROPPED`로 소비되며 heal 뒤 자동으로 살아나지 않습니다.

### Client와 log

```python
Command(kind, key, value=None, expected=None)
ClientRequest(client_id, sequence, fingerprint, command)
LogEntry(index, term, request_or_none)
```

`fingerprint`는 `canonical_fingerprint(command)`와 같아야 합니다. sequence는 1부터 연속 증가하고, 동일 sequence·동일 fingerprint는 이전 결과를 재사용합니다. 다른 fingerprint는 `CONFLICT`, 이전 sequence는 `STALE_SEQUENCE`, gap은 `SEQUENCE_GAP`입니다. core의 `get`도 log에 넣어 commit·apply 뒤 응답합니다.

## Milestone 진행

1. `design/`의 `TODO`를 먼저 채웁니다.
2. term·vote persistence와 election을 구현합니다.
3. AppendEntries와 conflicting suffix repair를 구현합니다.
4. current-term commit와 ordered apply를 구현합니다.
5. key-value command와 linearizable read 계약을 구현합니다.
6. client session, crash recovery와 snapshot을 구현합니다.
7. every-step invariant와 KV/CAS history checker를 연결합니다.
8. 7개 필수 schedule과 membership·sharding 설계 dossier를 제출합니다.

## 구현 자유와 계약

class나 helper를 추가할 수 있습니다. 다만 다음은 바꾸지 않는 편이 public test와 trace 재사용에 유리합니다.

- `types.py`의 wire-level field 의미
- storage에서 영속 상태를 복사해 읽고 원자적으로 교체하는 경계
- network delivery가 명시적 event라는 점
- client response가 commit·apply 이전에 완료되지 않는다는 계약
- snapshot에 state machine, client session과 configuration을 함께 포함한다는 계약

자동 검사 통과만으로 safety·liveness 설명이나 설계 판단이 승인되지는 않습니다. 완성 workspace는 `scripts/check-capstone-workspace.py`의 자동 근거와 별도 사람 검토를 모두 거칩니다.
