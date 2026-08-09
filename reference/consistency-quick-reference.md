# Consistency 빠른 참고

## 비교표

| Model | 보존하는 order·visibility | 허용할 수 있는 현상 | 대표 검사 |
|---|---|---|---|
| Linearizability | operation real-time order와 sequential object semantics | 겹치는 operation의 다양한 순서 | invocation·completion history search |
| Sequential consistency | process order를 보존하는 하나의 global sequential order | process 사이 real-time 역전 | program order + legal total order |
| Causal consistency | happened-before와 dependency order | concurrent update의 observer별 다른 순서 | causal context·dependency check |
| Read-your-writes | 한 session의 write 이후 read visibility | 다른 session의 stale read | session token·observed version |
| Monotonic reads | 한 session에서 본 version보다 과거로 돌아가지 않음 | 다른 session 간 다른 progress | per-session frontier |
| Eventual convergence | update 중단과 repair 지속 뒤 same state | 수렴 전 stale·conflict | anti-entropy·merge convergence |
| Serializability | transaction history가 어떤 serial transaction order와 같음 | real-time 역전 가능 | dependency graph·transaction checker |
| Strict serializability | serializability + real-time order | 겹치는 transaction 순서만 유연 | transaction history + real-time |

## 선택 질문

1. operation이 단일 key입니까, 여러 key transaction입니까?
2. 완료된 write 뒤 시작한 read가 이전 값을 봐도 됩니까?
3. 한 client만 자신의 write를 즉시 보면 충분합니까?
4. partition 중 stale read·local write·거절 중 무엇을 허용합니까?
5. concurrent update를 merge할 수 있습니까?
6. stale 정도를 version·time으로 표시할 수 있습니까?
7. consistency 위반의 제품 비용은 무엇입니까?
8. 필요한 history checker와 workload가 있습니까?

## 흔한 잘못된 주장

```text
R + W > N이므로 linearizable합니다.
```

quorum 교차 외에도 membership, version ordering, concurrent write와 read protocol이 필요합니다.

```text
leader에서 읽으므로 최신입니다.
```

old leader partition, apply lag와 leadership confirmation을 처리해야 합니다.

```text
eventual consistency이므로 데이터가 언젠가 맞습니다.
```

repair가 계속 실행되고 merge가 convergent하며 tombstone과 membership이 올바르다는 조건이 필요합니다.

```text
각 key가 linearizable하므로 transaction도 안전합니다.
```

multi-key atomicity와 serializability는 별도 property입니다.
