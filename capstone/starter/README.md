# Replicated KV capstone starter

이 디렉터리는 [통합 과제](../../docs/06-capstone.md)의 protocol core 시작점입니다. 완성된 Raft 구현이나 reference answer가 아닙니다.

## 작업 공간 만들기

```sh
mkdir -p .workspace
cp -R capstone/starter .workspace/replicated-kv
```

공개 계약 검사:

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
└── trace-format.md
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
```

### Cluster

```python
Cluster(node_ids, election_timeouts)
cluster.tick(node_id)
cluster.tick_all()
cluster.deliver_next()
cluster.deliver_all()
cluster.crash(node_id)
cluster.restart(node_id)
cluster.submit(node_id, request)
cluster.leaders()
cluster.trace
```

message delivery는 자동 background thread가 아니라 `deliver_next` 또는 `deliver_all` 호출로만 일어납니다. 따라서 실패 schedule을 코드와 JSON으로 재생할 수 있습니다.

## Milestone 진행

1. `design/`의 `TODO`를 먼저 채웁니다.
2. term·vote persistence와 election을 구현합니다.
3. AppendEntries와 conflicting suffix repair를 구현합니다.
4. current-term commit와 ordered apply를 구현합니다.
5. key-value command와 linearizable read 계약을 구현합니다.
6. client session, crash recovery와 snapshot을 구현합니다.
7. every-step invariant와 history checker를 연결합니다.

## 구현 자유와 계약

class나 helper를 추가할 수 있습니다. 다만 다음은 바꾸지 않는 편이 public test와 trace 재사용에 유리합니다.

- `types.py`의 wire-level field 의미
- storage에서 영속 상태를 복사해 읽고 원자적으로 교체하는 경계
- network delivery가 명시적 event라는 점
- client response가 commit·apply 이전에 완료되지 않는다는 계약
- snapshot에 state machine, client session과 configuration을 함께 포함한다는 계약
