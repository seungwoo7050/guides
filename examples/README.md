# 관찰 예제 구현 지도

`examples/`의 각 Python 파일은 서로 독립된 작은 project다. 아래 번호는 Git의 과거 작성 순서가 아니라, 예제를 빈 파일에서 다시 만든다고 가정한 권장 구현 순서다. 번호는 파일마다 독립적으로 시작하며 source의 같은 번호 주석이 authoritative anchor다. 예제는 exercise 답안이 아니므로 현상 하나를 관찰한 뒤 연결 exercise로 이동한다.

### `relational_algebra.py`

| 순서 | 파일·symbol | 책임 |
|---:|---|---|
| 1 | `select` | predicate를 만족하는 detached row 선택 |
| 2 | `project` | 열 순서와 중복 제거 소유 |
| 3 | `inner_join` | 오른쪽 lookup과 충돌 없는 열 namespace |
| 4 | module scenario | 선택·사영·조인을 잇는 관찰 |

### `slotted_page.py`

| 순서 | 파일·symbol | 책임 |
|---:|---|---|
| 1 | `SLOT_BYTES`, `Slot` | slot directory 비용과 상태 어휘 |
| 2 | `SlottedPage` | page bytes, slot과 free boundary 소유 |
| 3 | `insert` | 전체/연속 공간 구분과 compact-before-write |
| 4 | `read`, `delete`, `compact` | 안정적인 slot 수명 |
| 5 | module scenario | compaction 전후 slot ID 관찰 |

### `buffer_pool.py`

| 순서 | 파일·symbol | 책임 |
|---:|---|---|
| 1 | `Frame` | pin·dirty·reference 상태 |
| 2 | `Clock` | frame 집합과 hand 소유 |
| 3 | `victim` | pin 제외와 second chance |
| 4 | module scenario | 결정적인 victim 관찰 |

### `index_cost_simulator.py`

| 순서 | 파일·symbol | 책임 |
|---:|---|---|
| 1 | `CostModel` | page 수와 비용 가정 소유 |
| 2 | scan methods | sequential/index 접근 비용 추정 |
| 3 | module scenario | 선택도에 따른 선택 역전 관찰 |

### `join_algorithms.py`

| 순서 | 파일·symbol | 책임 |
|---:|---|---|
| 1 | `nested_loop` | `NULL`과 bag 의미의 기준 구현 |
| 2 | `hash_join` | 중복을 보존하는 build/probe bucket |
| 3 | module scenario | 두 알고리즘 결과 동등성 관찰 |

### `transaction_anomalies.py`

| 순서 | 파일·symbol | 책임 |
|---:|---|---|
| 1 | shared reads | 같은 state를 본 두 snapshot |
| 2 | competing writes | last-writer effect와 금지된 serial 결과 |

### `wal_recovery.py`

| 순서 | 파일·symbol | 책임 |
|---:|---|---|
| 1 | `Page`, `LogRecord` | page LSN과 redo record 상태 |
| 2 | `redo` | 더 새로운 LSN만 반영하는 멱등 규칙 |
| 3 | module scenario | 최소 replay 관찰 |
