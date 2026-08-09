# 메모리 관리와 runtime service

언어의 value가 call frame보다 오래 살거나 서로 graph를 만들면 allocation과 lifetime 정책이 필요합니다. Memory management는 collector 알고리즘 하나가 아니라 object layout, root, ownership, finalization, FFI와 pause/failure 계약의 조합입니다.

## 학습 목표

- stack, arena, reference counting과 tracing GC의 적용 범위를 구분합니다.
- object header, root와 graph reachability를 설명합니다.
- finalizer와 resource cleanup을 memory reclamation과 분리합니다.
- host runtime을 사용할 때 target semantics와 관찰 차이를 기록합니다.

## 어떤 값이 heap을 필요로 합니까?

다음 조건 중 하나가 있으면 단순 stack lifetime만으로 부족할 수 있습니다.

- function return 뒤 살아 있는 closure capture
- 크기가 runtime에 결정되는 string, list, object
- 여러 value가 공유하는 mutable state
- recursive graph
- FFI로 전달되어 비동기적으로 사용되는 object

모든 값을 heap에 둘 필요는 없습니다. Escape analysis나 value representation으로 stack/inline allocation을 선택할 수 있지만 먼저 correctness를 고정합니다.

## Object model

개념적인 heap object:

```text
ObjectHeader
  kind/type id
  flags 또는 mark bits
  size
  optional refcount

payload
  fields / bytes / elements
```

Pointer tagging이나 NaN boxing 같은 최적화는 representation invariant를 복잡하게 합니다. Debug mode에서 tag와 payload를 검증할 수 있어야 합니다.

## Arena

Compiler 내부 AST/IR처럼 수명이 compilation unit과 같은 객체는 arena에 적합합니다.

```text
arena.allocate(node)
...
arena 전체 해제
```

개별 free가 없고 locality가 좋지만 일부 node만 오래 보존하기 어렵습니다. Incremental compiler에서 snapshot 간 node를 공유하면 arena lifetime을 document/version과 맞춰야 합니다.

Runtime user object에 arena를 사용하면 전체 request/session 종료 때만 해제할 수 있는 경우가 있습니다.

## Reference counting

각 object의 incoming ownership count를 유지합니다.

장점:

- 마지막 owner가 사라질 때 즉시 회수
- pause가 분산됨
- 단순한 host integration

문제:

- increment/decrement 비용
- cycle을 회수하지 못함
- atomic count 비용
- destructor 연쇄와 예측하기 어려운 latency

Weak reference 또는 cycle detector가 필요할 수 있습니다. Borrowed reference와 owned reference를 FFI 문서에 명확히 합니다.

## Tracing garbage collection

Root에서 도달 가능한 object를 표시하고 나머지를 회수합니다.

```text
roots
→ graph traversal
→ reachable mark
→ sweep 또는 compact
```

Root 후보:

- VM operand stack과 local slot
- active call frame
- global/builtin table
- open upvalue
- native handle table
- JIT stack map이 가리키는 location

Root 하나를 빠뜨리면 살아 있는 object를 회수합니다. 더 이상 사용하지 않는 값을 root로 남기면 leak가 됩니다.

### Conservative와 precise

Conservative collector는 word를 pointer처럼 추측할 수 있어 integration이 쉽지만 false retention이 생깁니다. Precise collector는 object layout과 stack map을 알아야 하지만 이동/compaction에 적합합니다.

## Moving collector와 handle

Object를 이동하면 raw pointer를 가진 모든 곳을 갱신해야 합니다. FFI가 pointer를 보존하면 pinning이나 stable handle이 필요합니다.

```text
HandleId -> current object address
```

Pinning이 많으면 heap compaction 효과가 줄고 fragmentation이 생길 수 있습니다.

## Finalizer는 resource cleanup이 아닙니다

File, socket, lock과 transaction은 언제 해제되는지가 프로그램 의미입니다. GC finalizer 시점에 맡기면 지연되거나 종료 전에 실행되지 않을 수 있습니다.

권장:

- lexical scope cleanup
- explicit `close`
- RAII/defer/with 같은 deterministic construct

Finalizer는 안전망이나 외부 resource warning에 제한하고 실행 순서와 thread를 보장하지 않는다고 문서화합니다.

## Stop-the-world, incremental와 generational

### Stop-the-world

모든 mutator를 멈추고 root/heap을 검사합니다. 구현은 단순하지만 pause가 큽니다.

### Incremental/concurrent

Collector와 mutator가 번갈아 또는 동시에 실행합니다. Write barrier와 tri-color invariant가 필요합니다.

### Generational

대부분 object가 짧게 산다는 가정으로 young generation을 자주 수집합니다. Old→young reference를 remembered set에 기록해야 합니다.

이 가이드는 알고리즘 전체를 구현하지 않습니다. 각 방식이 요구하는 runtime/compiler contract를 이해하는 것이 목표입니다.

## Runtime service

Memory 외에도 다음 서비스가 언어 실행에 속할 수 있습니다.

- string interning
- symbol/name table
- I/O와 encoding
- clock/randomness
- thread/task scheduler
- module initialization
- panic/diagnostic reporting
- FFI handle

Compiler가 constant string을 어떤 format으로 만들고 runtime이 어떻게 소유하는지 연결해야 합니다.

## Host runtime profile

Python으로 Mica interpreter를 만들면 Python GC와 string object를 사용합니다. 이때 정확히 말할 수 있는 것은 다음입니다.

- Mica lexical lifetime와 mutability 규칙은 interpreter가 구현합니다.
- 실제 allocation, object move와 collection timing은 Python runtime에 맡깁니다.
- target collector의 pause, object layout이나 pointer safety를 구현한 것이 아닙니다.

Host GC를 사용했다고 memory management를 학습하지 않은 것은 아니지만, target runtime의 보장을 주장할 수는 없습니다.

## Resource limit과 denial of service

Language tool은 신뢰할 수 없는 source를 처리할 수 있습니다.

- 최대 source/token/node 수
- nesting/call depth
- heap allocation budget
- execution step/time budget
- output size
- diagnostic 수

Limit 초과는 internal crash가 아니라 명시적 resource diagnostic이어야 합니다. Limit 자체가 language semantics인지 특정 실행 환경 정책인지 구분합니다.

## 대표 실패

- closure object를 회수했지만 open upvalue가 가리킵니다.
- native code가 moving object raw pointer를 보존합니다.
- finalizer에 file flush를 맡겨 데이터가 사라집니다.
- host GC 사용 결과를 target GC 성능으로 주장합니다.
- remembered set을 갱신하지 않아 generational collector가 young object를 놓칩니다.
- compiler AST arena를 incremental snapshot보다 먼저 해제합니다.

## 실습 연결

[Interpreter와 VM exercise](../../exercises/04-interpreter-and-vm/README.md)의 선택 과제에서 cell 기반 closure와 mark-sweep 모형을 구현합니다. Mica core completion에는 collector 구현이 필수가 아니며 host runtime 경계를 문서화하면 됩니다.

## 점검 질문

1. compiler AST에 arena가 적합하고 runtime closure에는 부족할 수 있는 이유는 무엇입니까?
2. reference counting이 cycle을 회수하지 못하는 이유는 무엇입니까?
3. tracing GC의 root를 compiler와 runtime 중 누가 제공합니까?
4. finalizer와 deterministic cleanup을 분리해야 하는 이유는 무엇입니까?
5. host runtime을 사용한 구현이 주장할 수 없는 memory 보장은 무엇입니까?
