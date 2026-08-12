# `game-server` 최종 에이전트 구현 설계도

_외부 저장소·외부 가이드 참조 없이, 빈 Git 저장소에서 시작해 하나의 C++ 게임 서버 프로젝트를 장기 구성요소별 branch로 분리하고 v1부터 v7까지 실제 순서로 진화시키기 위한 자기완결적 정본 명세_

작성 기준일: 2026-08-12

---

## 0. 문서의 지위

이 문서 하나가 신규 저장소 `game-server`의 구현 정본이다.

에이전트는 다음 전제로 작업한다.

- 시작점은 비어 있는 Git 저장소다.
- 다른 저장소, 다른 프로젝트, 학습 가이드, 과거 구현을 읽어야 할 필요가 없다.
- 이 문서에 적힌 요구사항·불변식·실패 모델·검증 기준만으로 구현 가능해야 한다.
- 프로젝트는 하나지만, 독립적으로 빌드·실행·배포되거나 공용 계약을 소유하는 구성요소는 **장기 branch**로 분리한다.
- v1~v7은 branch 이름이 아니라 **프로젝트 전체의 누적 release**다.
- `UDP`, `Redis`, `Kafka`, `lock-free` 같은 기술 도입 자체를 branch로 만들지 않는다.
- v1은 상세 구현 계획까지 고정한다.
- v2~v7은 문제, 진입 조건, architecture delta, 불변식, 실패 모델과 완료 근거를 고정하되 세부 구현은 직전 release의 결과를 보고 확정한다.
- 최종 코드를 먼저 만든 뒤 과거 commit을 꾸며내지 않는다.
- `devlog/`는 사용자가 직접 작성하는 영역이다. 에이전트는 생성·수정·stage·commit하지 않는다.

이 문서와 실제 저장소 상태가 충돌하면 **이미 검증되어 release된 코드의 실제 계약을 먼저 보존하고**, 다음 release의 architecture 문서에서 차이를 명시적으로 수정한다. 과거 release의 의도를 사후에 바꾸지 않는다.

---

## 1. 프로젝트 목표

`game-server`는 그래픽 게임 제작 프로젝트가 아니다.

목표는 다음 서버 문제를 하나의 실제 C++ 프로젝트에서 연결해 검증하는 것이다.

```text
C++20 자원 수명과 오류 계약
→ macOS kqueue / Linux epoll 기반 비동기 I/O
→ 장기 TCP 연결과 논리 session
→ fixed-tick authoritative simulation
→ PostgreSQL 영속 상태
→ 운영용 HTTP API와 Web dashboard
→ UDP realtime transport
→ 측정 기반 single-node 최적화
→ Redis multi-instance coordination
→ process/service extraction
→ Kafka durable event path
→ Kubernetes 배포·drain·scale
```

최종 프로젝트가 보여줘야 하는 능력은 특정 라이브러리 사용법이 아니라 다음이다.

- state owner를 분명하게 정한다.
- resource lifetime과 shutdown을 끝까지 추적한다.
- client intent와 server-authoritative result를 구분한다.
- partial read/write, disconnect, timeout, overload를 정상 경로와 같은 수준으로 설계한다.
- concurrency를 correctness-first로 만들고 측정 뒤 최적화한다.
- durable state, ephemeral coordination state, realtime in-memory state를 분리한다.
- 단일 process에서 여러 process·instance로 진화할 때 상태 소유권을 다시 정의한다.
- 새로운 dependency가 추가될 때 새로운 failure model도 함께 추가한다.
- 성능과 안정성 주장을 재현 가능한 evidence로 남긴다.

---

## 2. 고정 기술 결정

| 영역 | 결정 |
| --- | --- |
| 저장소 | `game-server` |
| 핵심 언어 | C++20 |
| C++ 빌드 | CMake + CMakePresets |
| macOS I/O backend | `kqueue` |
| Linux I/O backend | `epoll` |
| Linux 개발/통합 환경 | Docker 기반 Linux environment |
| 최종 성능 근거 | 실제 Linux host 또는 Linux VM |
| v1 game transport | TCP |
| v2 realtime transport | UDP 추가 |
| durable database | PostgreSQL |
| v4 coordination | Redis |
| v6 event broker | Kafka |
| v7 orchestration | Kubernetes |
| operations dashboard | TypeScript + React/Next.js 기반의 최소 운영 UI |
| graphical game client | 구현하지 않음 |
| 대체 client | scripted bot / load generator |
| client prediction | 구현하지 않음 |
| prediction 지원 | server protocol에 reconciliation에 필요한 field 제공 |
| game state | server authoritative |
| v1 queue | bounded mutex + condition variable queue |
| lock-free | v3 profiling이 정당화할 때만 검토 |
| release 기준 | main의 immutable release manifest + tag |
| 원격 push | 사용자가 명시적으로 요구할 때만 |

외부 dependency의 정확한 minor/patch version과 container digest는 구현 시점에 고정하고 release manifest에 기록한다. 이 설계도는 특정 시점의 mutable `latest`에 의존하지 않는다.

---

## 3. 명시적 비범위

다음은 v1~v7의 필수 결과가 아니다.

- Unity 또는 Unreal 기반 graphical client
- rendering, animation, asset pipeline
- game editor
- 제품용 회원가입·상점·결제·커뮤니티 UI
- client-side prediction loop
- match가 진행 중인 room의 무중단 live migration
- 자체 Redis·Kafka·PostgreSQL 구현
- 자체 consensus·Raft·quorum storage
- multi-region active-active
- 전 구성요소의 무조건적인 microservice 분리
- 측정 없이 도입한 lock-free 구조
- “Kubernetes에 올렸다”만으로 production-ready라고 주장하는 것
- 모든 dependency failure에서 무손실을 보장한다는 주장

서버가 제공하는 snapshot과 acknowledgement는 미래 client가 prediction/reconciliation을 구현할 수 있게 설계하지만, client 실행 코드는 이 프로젝트에 포함하지 않는다.

---

# Part I. 저장소와 branch architecture

## 4. branch를 구성요소 경계로 사용한다

이 저장소의 장기 branch는 일반적인 짧은 feature branch가 아니다.

**한 branch = 하나의 독립 구성요소 또는 공용 계약의 개발 역사**다.

최종 장기 branch는 다음과 같다.

```text
main
shared-protocol
game-server
loadgen
ops-dashboard

# v5에서 필요가 실제로 생긴 뒤 추가
gateway
matchmaker

# v6에서 추가
event-worker

# v7에서 추가
orchestration
```

### 4.1 branch별 책임

| branch | 책임 | 최초 등장 |
| --- | --- | ---: |
| `main` | 프로젝트 수준 문서, release manifest, 통합 재현 스크립트 | v1 |
| `shared-protocol` | wire/internal/event/control contract와 공용 codec/type | v1 |
| `game-server` | authoritative room runtime, session, networking, persistence | v1 |
| `loadgen` | headless scripted clients, load/fault workload | v1 |
| `ops-dashboard` | 운영 상태 조회·drain용 최소 Web UI | v1 |
| `gateway` | reliable client connection, session routing | v5 |
| `matchmaker` | queue, assignment, capacity-aware placement | v5 |
| `event-worker` | Kafka consumer, ranking/audit projection | v6 |
| `orchestration` | container integration, Kubernetes manifests와 lifecycle | v7 |

### 4.2 만들지 않는 장기 branch

다음과 같은 이름의 장기 branch는 만들지 않는다.

```text
v2-udp
v3-lockfree
redis
kafka
postgres
epoll
kqueue
performance
refactor
```

이들은 독립 구성요소가 아니라 기존 구성요소의 capability 또는 adapter다.

### 4.3 새 component branch를 만드는 조건

다음 중 하나를 만족해야 한다.

1. 독립 executable/service로 실행된다.
2. 독립 build/test lifecycle을 가진 공용 contract/library다.
3. 독립 배포 artifact가 된다.
4. 장애·scale·release lifecycle이 기존 구성요소와 의미 있게 다르다.
5. 기존 branch에 넣으면 owner와 failure boundary가 불명확해진다.

단순히 class가 많아졌거나 기술이 추가됐다는 이유로 branch를 늘리지 않는다.

---

## 5. `main`의 역할

`main`은 모든 source를 합치는 monorepo branch가 아니다.

`main`은 프로젝트 전체 release의 **integration index**다.

권장 구조:

```text
main/
├── README.md
├── docs/
│   ├── vision.md
│   ├── roadmap.md
│   ├── releases/
│   ├── architecture/
│   └── limitations.md
├── releases/
│   ├── v1.0.0.yaml
│   ├── v2.0.0.yaml
│   └── ...
└── scripts/
    ├── materialize-release.sh
    ├── verify-release.sh
    └── cleanup-release.sh
```

`main`에는 game runtime source, gateway source, dashboard source를 직접 넣지 않는다.

### 5.1 release manifest

프로젝트 전체 release는 mutable branch head가 아니라 exact commit으로 정의한다.

예:

```yaml
release: v1.0.0

components:
  shared-protocol: <exact-commit-sha>
  game-server: <exact-commit-sha>
  loadgen: <exact-commit-sha>
  ops-dashboard: <exact-commit-sha>

dependencies:
  postgresql:
    image: <repository@sha256:digest>

toolchain:
  cpp_compiler: <recorded-version>
  cmake: <recorded-version>
  node: <recorded-version>

evidence:
  manifest: docs/releases/v1.0.0.md
```

v5 이후에는 `gateway`, `matchmaker`가, v6에는 `event-worker`, v7에는 `orchestration`이 추가된다.

### 5.2 release workspace

통합 검증은 같은 저장소의 여러 ref를 별 디렉터리에 materialize해서 수행한다.

```text
.release-workspace/
├── shared-protocol/
├── game-server/
├── loadgen/
├── ops-dashboard/
├── gateway/
├── matchmaker/
├── event-worker/
└── orchestration/
```

구현 방식은 Git worktree 또는 독립 checkout 중 하나를 사용할 수 있다.

중요한 계약은 다음이다.

- branch head를 직접 신뢰하지 않는다.
- manifest가 고정한 SHA를 checkout한다.
- integration build는 이 SHA 집합을 사용한다.
- 검증 뒤 임시 workspace를 정리한다.
- release tag는 `main`의 manifest commit을 가리킨다.

---

## 6. cross-branch dependency 규칙

### 6.1 `shared-protocol`은 공용 계약의 유일한 owner다

다음은 `shared-protocol`이 소유한다.

```text
TCP frame header와 message ID
UDP packet header와 message ID
session generation field
request / command identifier
internal service command/result schema
operations API contract
Kafka event schema
compatibility/versioning policy
```

`game-server`, `loadgen`, `gateway`, `matchmaker`, `event-worker`, `ops-dashboard`는 같은 계약을 서로 독립적으로 복제 정의하지 않는다.

### 6.2 local build dependency

C++ 구성요소는 release workspace에서 sibling checkout된 `shared-protocol`을 명시적인 build input으로 사용한다.

개념 예:

```text
.release-workspace/
├── shared-protocol/
└── game-server/

game-server CMake
→ ../shared-protocol의 public target 사용
```

CI에서도 exact `shared-protocol` SHA를 먼저 checkout하고 consumer를 빌드한다.

### 6.3 protocol compatibility

contract 변경은 다음 순서를 지킨다.

```text
새 contract version 추가
→ 기존 reader compatibility 확인
→ producer/consumer 각각 대응
→ mixed-version integration test
→ 이전 version 제거 가능 여부 판단
```

하나의 branch 변경만으로 다른 component가 즉시 깨지는 상태를 release하지 않는다.

---

# Part II. v1 — 최초 완성형 authoritative server

## 7. v1 전체 구성

v1은 Redis·Kafka·Kubernetes가 없어도 독립적으로 완성돼야 한다.

```text
                  ┌─────────────────────┐
                  │    ops-dashboard    │
                  │  React / Next.js    │
                  └──────────┬──────────┘
                             │ HTTP
                             ▼
scripted clients       operations API
      │                      │
      │ TCP                  ▼
      ▼              ┌───────────────────────┐
┌───────────┐         │      game-server      │
│  loadgen  │────────▶│                       │
└───────────┘         │ kqueue / epoll        │
                      │ Connection             │
                      │ Session                │
                      │ Player                 │
                      │ Matchmaking            │
                      │ Room workers           │
                      │ Fixed-tick simulation  │
                      │ Persistence workers    │
                      └───────────┬───────────┘
                                  │
                                  ▼
                             PostgreSQL

shared-protocol
= 모든 wire/control contract의 공용 owner
```

---

## 8. `shared-protocol` v1 설계

### 8.1 TCP frame

length-prefixed binary frame을 사용한다.

필수 header 의미:

```text
magic
protocol_version
message_type
flags
payload_length
request_id
session_generation
```

계약:

- network byte order를 고정한다.
- 최대 frame 크기를 고정한다.
- header와 payload는 incremental decode가 가능해야 한다.
- 한 `read`에 여러 frame이 들어올 수 있다.
- 한 frame이 여러 `read`로 나뉠 수 있다.
- unknown message type을 거부한다.
- incompatible protocol version을 거부한다.
- payload length overflow와 oversized frame을 거부한다.
- decode failure가 connection parser state를 무한 오염시키지 않는다.

### 8.2 v1 message family

최소 message family:

```text
HELLO
AUTH
AUTH_RESULT

HEARTBEAT
HEARTBEAT_ACK

QUEUE_JOIN
QUEUE_LEAVE
MATCH_ASSIGNED

READY
MOVE
INTERACT
LEAVE

COMMAND_RESULT
STATE_SNAPSHOT
MATCH_RESULT

ERROR
```

정확한 numeric ID는 구현 초기에 고정하고 이후 변경 시 protocol version을 고려한다.

### 8.3 command identity

게임 command에는 최소 다음 identity가 있어야 한다.

```text
session_generation
command_sequence
client_tick
request_id
```

서버는 이 값을 이용해 duplicate, stale, wrong-session command를 구분한다.

### 8.4 operations API contract

최소 operations contract:

```text
GET  /health/live
GET  /health/ready
GET  /metrics
GET  /admin/status
POST /admin/drain
```

`POST /admin/drain`만 운영 상태를 변경한다.

---

## 9. `game-server` v1 설계

### 9.1 process 내부 책임

```text
core
event
net
protocol adapter
session
runtime
game
persistence
observability
control
```

권장 source tree:

```text
game-server/
├── CMakeLists.txt
├── CMakePresets.json
├── cmake/
├── config/
├── docker/
├── include/
├── src/
│   ├── core/
│   ├── event/
│   ├── net/
│   ├── session/
│   ├── runtime/
│   ├── game/
│   ├── persistence/
│   ├── observability/
│   └── control/
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── process/
│   ├── failure/
│   └── stress/
└── docs/
```

`devlog/`는 만들지 않는다.

### 9.2 최소 게임 규칙

서버 상태 전이를 검증하기 위한 작은 headless arena만 구현한다.

- 한 match는 2~8명이다.
- player는 integer 또는 fixed-point 기반 2D position을 가진다.
- 필수 command는 `READY`, `MOVE`, `INTERACT`, `LEAVE`다.
- server tick이 command를 검증하고 적용한다.
- objective interaction으로 score가 증가한다.
- score limit 또는 time limit으로 match가 종료된다.
- match result는 server만 확정한다.
- match result는 PostgreSQL에 durable하게 기록한다.

게임 이름·세계관·그래픽 표현은 만들지 않는다.

### 9.3 상태 owner

다음을 서로 다른 수명으로 취급한다.

```text
Connection != Session != Player != Room
```

| 상태 | owner | 수명 |
| --- | --- | --- |
| `Connection` | network event loop | accept → socket close |
| `Session` | session registry | auth success → logout/grace expiry |
| `Player` | application state | player identity의 논리 수명 |
| `Room` | 지정 room worker | match creation → terminal result |

필수 불변식:

- socket close가 즉시 Session과 Player 삭제를 뜻하지 않는다.
- Room authoritative state는 동시에 worker 하나만 쓴다.
- network event loop는 Room을 직접 수정하지 않는다.
- DB worker는 event loop를 block하지 않는다.
- client는 intent를 제출할 뿐 score/result를 확정하지 못한다.
- terminal match result는 한 번만 durable effect를 남긴다.

### 9.4 event backend

공통 abstraction:

```text
Poller
├── KqueuePoller
└── EpollPoller
```

상위 계층은 backend를 알지 않는다.

동일한 lifecycle/readiness test를 두 backend에 적용한다.

초기에는 correctness를 우선해 level-triggered 모델을 사용한다. edge-triggered 도입은 별도 측정과 필요성이 생길 때만 검토한다.

### 9.5 nonblocking TCP

필수 처리:

- nonblocking listen/accept
- connection admission limit
- partial read
- partial write
- `EAGAIN`/`EWOULDBLOCK`
- `EINTR`
- peer half/fully closed state
- input buffer bound
- output buffer bound
- malformed frame disconnect/error policy
- writable readiness enable/disable
- registration failure rollback

### 9.6 backpressure

모든 connection의 pending output에는 상한을 둔다.

정책은 최소 다음을 고정한다.

```text
normal
→ pending output 증가
→ high-water mark
→ optional read throttling / snapshot coalescing
→ hard limit
→ controlled disconnect
```

느린 receiver 하나가 process 전체 memory를 무한 증가시키지 못한다.

### 9.7 session과 reconnect

대표 상태:

```text
CONNECTED
→ AUTHENTICATED
→ QUEUED
→ ASSIGNED
→ IN_ROOM
→ DISCONNECTED_GRACE
→ RESUMED | CLOSED
```

필수:

- heartbeat와 idle timeout을 분리한다.
- reconnect token을 둔다.
- `session_generation`을 둔다.
- 이전 generation의 packet/command를 거부한다.
- disconnect grace 동안 Room의 player state 보존 정책을 고정한다.
- grace expiry 뒤 제거를 deterministic하게 처리한다.

### 9.8 concurrency

v1은 correctness-first 구조다.

```text
network event loop
→ bounded command queue
→ room worker shard
→ bounded persistence queue
→ DB worker
```

규칙:

- queue는 mutex + condition variable 기반 bounded queue부터 시작한다.
- room ID로 worker shard를 선택한다.
- 같은 room의 mutable state는 같은 shard가 소유한다.
- cross-shard mutable reference를 두지 않는다.
- shutdown은 `stop request → producer stop → queue close → drain/abort policy → join → resource destroy` 순서를 지킨다.
- lock-free는 v3 전에는 도입하지 않는다.

### 9.9 fixed tick

Room simulation은 wall-clock callback 횟수가 아니라 fixed tick으로 진행한다.

각 command는 적용 전에 최소 다음을 검증한다.

- 올바른 session인가
- 올바른 room member인가
- duplicate인가
- stale인가
- 허용 tick window인가
- 현재 game state에서 허용되는 command인가

tick overrun은 숨기지 않고 metric으로 기록한다.

### 9.10 PostgreSQL

최소 schema:

```text
players
matches
match_players
match_results
leaderboard_entries
```

필수 계약:

- blocking query는 network thread에서 실행하지 않는다.
- match result 저장은 transaction이다.
- match result의 idempotency key를 둔다.
- 같은 terminal result를 반복 commit해도 한 효과만 남는다.
- schema migration은 empty DB에서 재현 가능해야 한다.
- DB 실패와 gameplay rejection을 같은 오류로 취급하지 않는다.
- PostgreSQL은 durable state owner다.

### 9.11 operations API

별도 TCP port를 사용한다.

기본 정책:

- health/metrics/status는 로컬 또는 개발망에서만 노출한다.
- drain은 명시적인 admin credential을 요구한다.
- game protocol port와 operations port의 failure를 구분한다.

`/admin/status` 최소 내용:

```text
process state
connection count
session count
active room count
matchmaking queue depth
worker queue depth
DB queue depth
tick latency percentiles
disconnect/error counters
drain state
```

### 9.12 graceful drain

```text
RUNNING
→ DRAINING
→ 새 connection/match 배정 제한
→ 기존 room 완료 또는 timeout 정책
→ persistence flush
→ connection 종료
→ worker join
→ process exit
```

SIGTERM을 즉시 `_exit`로 처리하지 않는다.

---

## 10. `loadgen` v1 설계

`loadgen`은 game client가 아니다.

역할:

- 실제 TCP protocol을 사용하는 headless bot
- scripted multi-client workload
- 정상·경계·실패 traffic 생성
- latency 측정
- disconnect storm
- slow receiver
- reconnect
- malformed frame injection
- later release의 UDP loss/reorder/jitter injection

필수 workload:

```text
single-client smoke
small match
concurrent matches
connection ramp
steady-state load
slow consumers
disconnect storm
reconnect storm
DB degraded workload
graceful drain workload
```

모든 performance 결과는 workload configuration과 함께 저장한다.

---

## 11. `ops-dashboard` v1 설계

목적은 server 운영 상태를 브라우저에서 확인하는 것이다.

게임 client 기능을 넣지 않는다.

최소 화면:

- server live/ready/draining state
- connection/session 수
- active room/match 수
- matchmaking/worker/DB queue depth
- command rate
- tick p50/p95/p99
- request/command latency p50/p95/p99
- disconnect/error 수
- DB failure 수
- drain action

규칙:

- React/Next.js를 사용하되 SSR 자체가 목적이 아니다.
- 복잡한 디자인 시스템을 만들지 않는다.
- polling 또는 단순 streaming 중 더 작은 구현을 선택한다.
- status 데이터의 정본은 game-server operations API다.
- dashboard 자체 상태가 server state를 덮어쓰지 않는다.
- game input을 전송하는 기능을 만들지 않는다.

---

## 12. v1 검증 gate

v1 완료 전에 최소 다음을 재현한다.

### Protocol

- fragmented frame
- coalesced frames
- malformed header
- oversized payload
- unknown message
- incompatible version

### Network

- partial read/write
- `EAGAIN`
- `EINTR`
- peer close
- slow receiver
- output hard limit
- connection admission limit

### Session

- heartbeat timeout
- idle timeout
- disconnect grace
- valid reconnect
- stale generation reconnect
- duplicate command
- stale command
- unauthorized command

### Runtime

- queue saturation
- tick overrun
- room owner invariant
- orderly shutdown
- forced shutdown

### Storage

- transaction rollback
- duplicate match result
- DB unavailable
- DB restart
- retry after uncertain result

### Operations

- liveness
- readiness
- dashboard status parity
- drain transition

### Platform

- native macOS kqueue
- Linux epoll in Docker
- sanitizer runs
- clean build
- process-level integration

### Performance

최소 다음을 같은 workload에서 기록한다.

```text
connection count
active room count
commands/sec
tick p50/p95/p99
command latency p50/p95/p99
queue depth
CPU
RSS
error/disconnect count
```

---

# Part III. v1의 실제 Git 개발 순서

## 13. 전체 v1 branch 진행 순서

v1은 다음 순서로 진행한다.

```text
main bootstrap
   ↓
shared-protocol
   ↓
game-server core/network/session/runtime
   ↓
loadgen bootstrap
   ↓
game-server storage/observability/control
   ↓
ops-dashboard
   ↓
loadgen stress/failure completion
   ↓
game-server performance/CI closure
   ↓
main release manifest + integration gate
   ↓
v1.0.0
```

component 개발은 필요에 따라 서로 왕복할 수 있지만, **아직 존재하지 않는 contract를 consumer가 먼저 가정해 구현하지 않는다.**

---

## 14. `main` v1 commit plan

1. `chore(repo): initialize game-server project index`
2. `docs(scope): define project boundary and v1-v7 release roadmap`
3. `docs(branches): define component branch and release manifest contract`
4. `chore(release): add release materialization and verification skeleton`

이후 v1 component가 준비된 뒤:

5. `chore(release): pin v1 component revisions and dependency identities`
6. `test(release): verify reproducible v1 integration workspace`
7. `docs(release): record v1 evidence and known limitations`

그 뒤 `main`의 7번 commit 또는 그 이후의 검증 완료 commit에 `v1.0.0` tag를 단다.

---

## 15. `shared-protocol` v1 commit plan

1. `chore(protocol): initialize shared contract project`
2. `feat(protocol): define versioned TCP frame header and message ids`
3. `feat(protocol): add incremental frame encoder and decoder`
4. `test(protocol): cover fragmented coalesced malformed and oversized frames`
5. `feat(protocol): define session command and snapshot contracts`
6. `feat(control): define operations API response contracts`
7. `test(compat): verify protocol version and unknown message rejection`
8. `docs(protocol): document compatibility and ownership rules`

각 commit은 consumer source가 없어도 독립적으로 build/test 가능해야 한다.

---

## 16. `game-server` v1 commit plan

1. `chore(server): initialize C++20 server project`
2. `build(cmake): add server and test targets`
3. `build(linux): add Linux build and PostgreSQL development environment`
4. `feat(core): add RAII descriptors result types and typed identifiers`
5. `feat(event): define readiness poller contract`
6. `feat(event): add native kqueue backend`
7. `feat(event): add Linux epoll backend`
8. `test(event): verify backend lifecycle and readiness parity`
9. `feat(net): accept and own nonblocking TCP connections`
10. `feat(net): integrate incremental shared frame decoding`
11. `test(net): cover partial reads peer close and malformed input`
12. `feat(net): buffer partial writes and writable readiness`
13. `fix(backpressure): bound per-connection pending output`
14. `feat(session): separate connection session and player lifetimes`
15. `feat(timer): add heartbeat idle timeout and reconnect grace`
16. `test(session): verify disconnect expiry resume and stale generation`
17. `feat(runtime): add bounded queues and room worker shards`
18. `feat(game): add fixed-tick authoritative room state`
19. `feat(match): add lobby matchmaking and room lifecycle`
20. `test(game): reject duplicate stale and unauthorized commands`
21. `feat(storage): add PostgreSQL schema and persistence workers`
22. `fix(storage): make terminal match result transactional and idempotent`
23. `test(storage): cover rollback duplicate retry and database restart`
24. `feat(observability): add structured logs metrics and health state`
25. `feat(control): add status readiness and authenticated drain endpoints`
26. `test(failure): cover saturation disconnect storms and graceful shutdown`
27. `perf(runtime): capture representative baseline and fix one measured bottleneck`
28. `ci: verify macOS Linux sanitizers and integration paths`
29. `docs(operations): document server architecture runtime and reproduction`

실제 개발 중 새 failure가 발견되면 `test`/`fix` commit을 이 사이에 추가한다. 위 번호를 맞추기 위해 수정 commit을 합치거나 삭제하지 않는다.

---

## 17. `loadgen` v1 commit plan

1. `chore(loadgen): initialize headless workload client`
2. `feat(loadgen): add protocol-aware connection and scripted session flow`
3. `feat(loadgen): add concurrent match and connection ramp workloads`
4. `feat(loadgen): add slow consumer disconnect and reconnect scenarios`
5. `feat(loadgen): record latency throughput and workload identity`
6. `test(loadgen): verify deterministic workload configuration and summaries`
7. `docs(loadgen): document workload reproduction`

---

## 18. `ops-dashboard` v1 commit plan

1. `chore(dashboard): initialize operations dashboard`
2. `feat(dashboard): show health connection session and room state`
3. `feat(dashboard): show queue latency and error metrics`
4. `feat(dashboard): add authenticated drain action`
5. `test(dashboard): verify loading error and drain states`
6. `docs(dashboard): document local operations workflow`

---

# Part IV. v2~v7 진화 설계

## 19. 후속 release 공통 원칙

v2~v7의 정확한 class 이름, queue capacity, thread 수, timeout 숫자, Redis key, Kafka partition 수, Kubernetes replica 수를 지금 고정하지 않는다.

각 release에 대해 지금 고정하는 것은 다음이다.

```text
Problem
Entry Condition
Architecture Delta
Invariant
Failure Model
Evidence
Branch Impact
```

다음 release의 상세 commit line은 **직전 release가 실제로 완료된 뒤** 작성한다.

---

## 20. v2 — UDP realtime transport

### Problem

TCP만으로는 realtime state update에서 loss, duplication, reordering, jitter를 직접 다루는 transport 설계 능력을 보여주기 어렵다.

### Entry Condition

- v1 release gate 통과
- TCP regression suite 안정화
- fixed-tick simulation과 session generation이 이미 존재

### Architecture Delta

```text
TCP
├── auth/session
├── matchmaking
├── reliable control
└── terminal result

UDP
├── realtime input
└── state snapshot
```

### Protocol

UDP packet에는 최소 다음 identity를 둔다.

```text
protocol_version
session_generation
packet_sequence
client_tick
server_tick
message_type
transport_token
```

server snapshot에는 최소:

```text
server_tick
snapshot_sequence
last_processed_input
authoritative_state
```

를 포함한다.

이것이 future client reconciliation의 server-side contract다.

### Invariant

- server만 authoritative writer다.
- packet arrival order를 simulation order로 사용하지 않는다.
- stale generation을 거부한다.
- stale snapshot을 적용하지 않는다.
- TCP-only path는 그대로 회귀 통과한다.

### Failure Model

- packet loss
- duplicate
- reorder
- jitter
- long delay
- endpoint rebinding
- invalid token
- oversized datagram
- spoof attempt

### Evidence

- deterministic network fault injection
- packet trace
- stale/duplicate rejection count
- bandwidth
- latency percentile
- reconnect generation transition

### Branch Impact

```text
shared-protocol  수정
game-server      수정
loadgen          수정
main             release manifest 갱신
```

새 장기 branch는 만들지 않는다.

완료 release: `v2.0.0`

---

## 21. v3 — measured single-node performance

### Problem

v1·v2의 실제 workload에서 CPU, allocation, queue wait, lock contention, cache locality와 false sharing 병목을 찾고 근거 기반으로 줄인다.

### Entry Condition

- v2 functional/failure gate 통과
- representative workload 고정
- before profile 재현 가능

### Baseline First

먼저 다음을 측정한다.

```text
CPU profile
tick duration
queue wait
lock contention
allocation count
RSS
throughput
p95/p99 latency
```

### Candidate Changes

- hot/cold data 분리
- room state layout 개선
- allocation pool/arena
- queue batching
- worker shard policy
- contention 감소
- 필요한 경우 SPSC/MPSC ring buffer

### Lock-free Gate

다음을 모두 만족할 때만 검토한다.

- queue contention이 주요 병목으로 재현된다.
- producer/consumer topology가 명확하다.
- shutdown과 overflow semantics를 설명할 수 있다.
- memory reclamation 문제를 통제할 수 있다.
- correctness regression을 자동 검증할 수 있다.

조건을 만족하지 않으면 lock-free를 **도입하지 않는 것**이 정상 완료다.

### Invariant

최적화 전후:

- authoritative result 동일
- replay/state checksum 동일
- timeout/shutdown 의미 동일
- failure test 동일

### Evidence

- 동일 workload before/after
- raw profile
- percentile
- throughput
- CPU/RSS
- regression result
- 채택/기각 ADR

### Branch Impact

```text
game-server 수정
loadgen     수정 가능
main        manifest/evidence 갱신
```

완료 release: `v3.0.0`

---

## 22. v4 — multi-instance + Redis coordination

### Problem

여러 game-server instance가 존재하면 process-local memory만으로 다음을 결정할 수 없다.

```text
어떤 instance가 살아 있는가
player/session이 어느 instance에 있는가
room이 어느 instance에 있는가
reconnect를 어디로 보내야 하는가
새 room을 어디에 배정해야 하는가
```

### Entry Condition

- v3 완료
- 최소 두 game-server instance를 동시에 실행할 integration environment 존재
- process-local registry가 multi-instance에서 실패하는 시나리오를 재현

### State Ownership

```text
authoritative realtime room state
→ game-server memory

durable player/match result
→ PostgreSQL

ephemeral cross-instance coordination
→ Redis
```

Redis가 소유할 수 있는 것:

- server registry
- heartbeat/lease
- session location
- player presence
- room location
- reconnect routing metadata
- short-lived placement metadata

Redis가 소유하지 않는 것:

- per-tick authoritative room simulation
- durable match result

### Fencing

ownership 변경에는 generation 또는 fencing token을 사용한다.

stale process가 오래된 lease로 current owner state를 덮어쓰지 못해야 한다.

### Failure Model

- instance kill
- instance restart
- Redis unavailable
- Redis restart
- lease expiry
- duplicate registration
- stale writer
- reconnect during owner loss

### Degraded Mode

Redis outage 시:

- 기존 room 계속 진행 가능 여부
- 신규 matchmaking/placement 중지 여부
- reconnect 제한
- durable result 저장

을 서로 분리한다.

### Evidence

- 2개 이상 instance
- kill/restart
- Redis outage/recovery
- lease expiry
- stale owner rejection
- reconnect routing
- PostgreSQL durable state 대조

### Branch Impact

```text
game-server 수정
shared-protocol 필요 시 수정
loadgen multi-instance 시나리오 추가
main manifest/evidence 갱신
```

Redis라는 이유만으로 새 branch를 만들지 않는다.

완료 release: `v4.0.0`

---

## 23. v5 — service extraction

### Problem

multi-instance 상태에서 reliable client connection, matchmaking, room simulation이 한 executable에 함께 있을 때 scale/failure/deploy 요구가 달라진다는 문제가 실제로 드러난다.

### Entry Condition

- v4 완료
- 최소 한 책임이 별 process로 분리할 가치가 있음을 failure/scale 근거로 설명 가능
- internal contract와 owner map 초안 존재

### 최초 목표 구조

```text
Clients
   │
   ▼
Gateway
   │
   ├──── Matchmaker
   │          │
   │          ▼
   └──── Game Server A/B/C

Redis       = ephemeral coordination
PostgreSQL  = durable result
```

### `gateway` 책임

- reliable TCP client connection
- authentication/session edge
- routing
- connection-level backpressure
- reconnect entry

### `matchmaker` 책임

- queue
- candidate grouping
- game-server capacity view
- room placement decision
- assignment result

### `game-server` 책임

- room
- fixed tick
- authoritative simulation
- direct realtime UDP endpoint
- terminal result

### 하지 않는 분리

다음을 별 service로 만들지 않는다.

```text
PlayerService
MovementService
RoomService
HeartbeatService
```

객체마다 process를 만들지 않는다.

### Internal Contract

internal command/result에는 최소 다음을 정의한다.

- request identity
- idempotency scope
- timeout
- success
- reject
- unknown/uncertain
- version
- owner

### Failure Model

- gateway restart
- matchmaker restart
- game-server restart
- internal timeout
- duplicate command
- partial success
- stale routing
- queue saturation
- one service slow/dead

### Invariant

- 각 durable/mutable state의 writer는 하나다.
- timeout과 business rejection을 구분한다.
- retry가 duplicate side effect를 만들지 않는다.
- 모든 queue는 bounded다.
- realtime tick path를 unnecessary synchronous service call로 막지 않는다.

### Evidence

- process별 독립 kill/restart
- mixed-version contract
- timeout
- duplicate
- partial success
- overload/backpressure
- end-to-end correlation

### Branch Impact

이 시점에 처음으로 다음 장기 branch를 만든다.

```text
gateway
matchmaker
```

기존:

```text
shared-protocol
game-server
loadgen
ops-dashboard
```

도 계속 유지한다.

완료 release: `v5.0.0`

---

## 24. v6 — Kafka durable event path

### Problem

서비스가 나뉜 뒤 match 종료와 같은 durable business event를 realtime request path와 분리해 다른 consumer가 처리할 필요가 생긴다.

### Entry Condition

- v5 완료
- 하나 이상의 비동기 consumer use case가 실제로 존재
- DB commit과 event publish가 분리될 때 partial success를 재현

### Event Flow

Kafka를 realtime tick path에 넣지 않는다.

대표 흐름:

```text
Game Server
   │
   │ terminal result
   ▼
PostgreSQL transaction
   ├── match result
   └── outbox
          │
          ▼
       relay
          │
          ▼
        Kafka
          │
          ▼
    event-worker
     ├── ranking
     └── audit
```

### Contract

event에는 최소:

```text
event_id
event_type
event_version
aggregate_id
occurred_at
payload
```

를 둔다.

partition key와 ordering scope를 명시한다.

### Consumer Invariant

- at-least-once delivery를 전제로 한다.
- duplicate delivery가 duplicate business effect를 만들지 않는다.
- offset commit과 business success를 같은 것으로 취급하지 않는다.
- late event 처리 방식을 고정한다.
- poison event 격리 정책을 둔다.
- replay 시 rebuild 가능한 projection과 그렇지 않은 side effect를 구분한다.

### Failure Model

- broker unavailable
- producer restart
- relay restart
- consumer restart
- duplicate event
- out-of-order event
- late event
- poison event
- consumer lag
- replay

### Evidence

- outbox partial-success recovery
- broker restart
- relay restart
- duplicate rejection
- lag metric
- replay/rebuild
- event-to-state correlation

### Branch Impact

새 장기 branch:

```text
event-worker
```

수정:

```text
shared-protocol
game-server
main
loadgen 필요 시
ops-dashboard 필요 시 lag/consumer status 표시
```

완료 release: `v6.0.0`

---

## 25. v7 — Kubernetes orchestration

### Problem

여러 executable과 dependency가 존재하면 process 실행 자체보다 placement, health, readiness, shutdown, rolling deployment, capacity와 artifact identity가 새로운 correctness boundary가 된다.

### Entry Condition

- v6 완료
- component별 immutable container image 생성 가능
- 각 process의 liveness/readiness/drain semantics가 이미 정의됨
- local multi-process integration이 안정화됨

### Target Workloads

애플리케이션:

```text
gateway
matchmaker
game-server
event-worker
ops-dashboard
```

dependency:

```text
PostgreSQL
Redis
Kafka
```

로컬 재현에서는 dependency도 cluster 내부에 둘 수 있다.

이것을 production HA database 설계라고 주장하지 않는다.

### `game-server` Pod Lifecycle

```text
termination signal
→ 새 room 할당 중지
→ readiness false
→ 기존 room drain
→ terminal persistence/event flush
→ client reconnect guidance
→ remaining connection close
→ worker join
→ process exit
```

forced termination 시 손실 가능한 상태와 durable하게 보존되는 상태를 명시한다.

### Probe Semantics

- liveness: process 자체가 회복 불가능하게 stuck됐는가
- readiness: 새 traffic/match를 받을 수 있는가
- startup: 초기 시작이 아직 진행 중인가

외부 dependency 장애만으로 liveness가 무한 restart loop를 만들지 않는다.

### Scheduling/Resource

- CPU/memory request/limit
- graceful termination period
- disruption policy
- anti-affinity 또는 topology 필요성 검토
- game-server capacity signal
- queue pressure
- active room count

### Scaling

단순 connection count 하나만으로 game-server scale을 판단하지 않는다.

최소 다음을 같이 본다.

```text
active rooms
room capacity
matchmaking queue depth
tick saturation
CPU
network throughput
```

### Rolling Update

- 새 match 배정 중지
- drain
- readiness transition
- replacement capacity 확인
- old pod termination

순으로 검증한다.

live room migration을 구현하지 않았다면 rolling update의 실제 한계를 그대로 기록한다.

### Failure Model

- cold deploy
- bad readiness
- Pod kill
- node-like forced termination
- rolling update
- image mismatch
- resource saturation
- dependency startup delay
- scale-out lag

### Evidence

- exact image digest
- exact manifest identity
- cold start
- rolling update
- Pod loss
- drain vs forced termination
- scale-out load
- resource saturation
- rollback

### Branch Impact

이 시점에 새 장기 branch:

```text
orchestration
```

`orchestration`은 application source를 소유하지 않고 다음을 소유한다.

```text
container integration
Kubernetes manifests
configuration wiring
probe wiring
resource contract
deployment lifecycle
release reproduction
```

완료 release: `v7.0.0`

---

# Part V. release와 evidence

## 26. release gate 공통 형식

모든 release 문서는 다음 네 축을 반드시 포함한다.

| 축 | 질문 |
| --- | --- |
| Delta | 직전 release에 없던 capability는 무엇인가 |
| Invariant | 새 기능 뒤에도 바뀌면 안 되는 계약은 무엇인가 |
| Failure | 새로 생긴 failure mode는 무엇인가 |
| Evidence | 어떤 test/fault/profile로 이를 재현하는가 |

추가로 branch architecture에서는 다음을 기록한다.

| 축 | 질문 |
| --- | --- |
| Component | 어느 branch가 책임지는가 |
| Contract | 어떤 cross-branch contract가 바뀌는가 |
| Identity | 어떤 exact SHA/artifact로 release를 재현하는가 |

---

## 27. 성능 evidence 규칙

성능 주장은 최소 다음을 함께 남긴다.

```text
hardware / VM 정보
OS
compiler
build type / flags
component commit SHAs
dependency image digests
workload config
warmup
duration
client count
room count
raw samples 또는 summary source
p50/p95/p99
CPU
RSS
error count
```

다음은 금지한다.

- 단 한 번의 wall-clock 숫자로 성능 향상 주장
- macOS 결과를 Linux production-like 결과라고 표현
- Docker Desktop의 file-sharing 또는 virtualization 영향을 숨김
- workload가 달라졌는데 before/after를 직접 비교
- correctness 실패를 무시한 throughput 증가

---

## 28. failure evidence 규칙

각 failure test는 최소 다음을 기록한다.

```text
precondition
injected failure
expected state transition
forbidden state
observable evidence
cleanup
regression after recovery
```

예:

```text
Redis unavailable
→ 새 room placement 중단
→ 기존 room은 정책에 따라 계속
→ terminal result는 PostgreSQL에 남음
→ Redis 복구 뒤 duplicate owner가 생기지 않음
```

---

## 29. observability 공통 identity

가능한 범위에서 다음 identity를 전체 log/metric/event에 연결한다.

```text
connection_id
session_id
session_generation
player_id
match_id
room_id
command_sequence
request_id
server_instance_id
event_id
```

모든 metric에 고카디널리티 label을 무분별하게 넣지 않는다. 상세 identity는 structured log/trace에 두고 metric label은 제한한다.

---

# Part VI. Git 운영 규칙

## 30. component branch history

각 장기 component branch는 독립적인 chronological history를 가진다.

규칙:

- 실제로 구현한 순서대로 commit한다.
- build/test 가능한 작은 의미 단위를 선호한다.
- 정상 경로 뒤 발견된 failure fix를 숨기지 않는다.
- final tree를 만든 뒤 interactive rebase로 “예쁜 역사”를 사후 제작하지 않는다.
- 이미 공유되거나 release manifest에 pin된 commit을 함부로 rewrite하지 않는다.
- branch 이름은 component identity를 유지한다.

## 31. release history

프로젝트 전체 release는 `main`에서 관리한다.

```text
component branches advance independently
→ target SHAs 선택
→ release workspace materialize
→ full integration/failure/perf gate
→ release manifest commit
→ main tag
```

release tag 뒤 manifest를 바꾸지 않는다.

수정이 필요하면 새 patch/minor release를 만든다.

---

# Part VII. 에이전트 실행 계약

## 32. 에이전트가 처음 받는 것

에이전트는 다음만 있다고 가정한다.

```text
이 설계도
빈 game-server Git 저장소
macOS 개발 환경
Docker를 실행할 수 있는 환경
```

다른 저장소를 검색하거나 읽는 것을 구현 전제로 삼지 않는다.

## 33. 최초 실행 순서

1. 빈 저장소에서 `main`을 초기화한다.
2. `docs/vision.md`, `docs/roadmap.md`, branch/release contract를 만든다.
3. `shared-protocol` branch를 생성하고 v1 contract부터 구현한다.
4. `game-server` branch를 생성하고 v1 server를 실제 순서로 구현한다.
5. 필요해지는 시점에 `loadgen`을 생성한다.
6. operations API가 안정된 뒤 `ops-dashboard`를 생성한다.
7. component별 test를 통과시킨다.
8. `main`에서 exact SHA를 pin한 v1 release manifest를 만든다.
9. release workspace를 materialize해 full integration/failure/performance gate를 실행한다.
10. 통과하면 `v1.0.0` tag를 만든다.
11. v2부터는 직전 release의 실제 evidence를 읽고 상세 계획을 확정한 뒤 진행한다.
12. v5/v6/v7에서만 필요 조건을 만족할 때 새 component branch를 생성한다.

## 34. 각 commit 전후 규칙

commit 전에 확인:

```text
이번 변경이 해결하는 문제
변경되는 owner/invariant
추가되는 failure
검증 명령
```

commit 후 확인:

```text
build 결과
targeted test 결과
새 failure가 있었는가
다음 commit의 실제 필요가 무엇인가
```

실패를 숨기기 위해 다음 commit을 미리 합치지 않는다.

---

## 35. 에이전트 금지 사항

- 외부 저장소를 구현 정본으로 사용
- 외부 source 복사
- 외부 프로젝트의 directory structure 복제
- 최종 코드 선작성 후 commit history 사후 조립
- 요구 없는 원격 push
- `devlog/` 생성·수정·stage·commit
- `v2`, `redis`, `kafka` 같은 기술 단위 장기 branch 남발
- 측정 없는 lock-free 전환
- Redis를 authoritative per-tick Room state owner로 지정
- Kafka를 realtime tick critical path에 배치
- offset commit을 business exactly-once로 표현
- Kubernetes manifest 존재만으로 운영 가능 주장
- client prediction을 server 구현으로 가장
- timeout 뒤 결과를 무조건 실패로 단정
- unbounded queue/buffer
- mutable `latest` artifact로 release 재현
- `production-ready`, `zero-loss`, `exactly-once` 같은 검증되지 않은 표현

---

# Part VIII. 완료 정의

## 36. v1 완료

v1은 다음이 모두 있어야 한다.

```text
shared-protocol
game-server
loadgen
ops-dashboard
PostgreSQL integration
macOS kqueue
Linux epoll
session/reconnect
fixed tick
authoritative room
transactional/idempotent match result
health/metrics/status/drain
failure tests
load evidence
main release manifest
v1.0.0 tag
```

이 시점에서 프로젝트는 독립적으로 설명·실행·검증 가능한 완성품이어야 한다.

Redis/Kafka/Kubernetes가 없다는 이유로 v1을 미완성으로 취급하지 않는다.

## 37. v7 최종 완료

최종 release에서는 다음 진화가 실제 Git 역사와 evidence로 이어져야 한다.

```text
v1  complete single-instance authoritative server
 ↓
v2  UDP realtime path
 ↓
v3  measured single-node optimization
 ↓
v4  Redis multi-instance coordination
 ↓
v5  Gateway + Matchmaker service extraction
 ↓
v6  Kafka durable event path + event-worker
 ↓
v7  Kubernetes orchestration and drain/scale
```

최종 설명은 “많은 기술을 사용했다”가 아니라 다음 인과를 보여야 한다.

```text
단일 process에서 무엇이 충분했는가
→ 어떤 실제 한계가 생겼는가
→ 어떤 state/failure boundary가 새로 필요했는가
→ 왜 그 기술/구성요소를 추가했는가
→ 무엇을 바꾸지 않았는가
→ 어떤 실패와 측정으로 성공을 판정했는가
```

---

## 38. 최종 보고 형식

에이전트의 마지막 보고는 다음 순서로 작성한다.

1. 최종 branch 목록과 각 책임
2. release별 architecture delta
3. release manifest와 exact component SHAs
4. 실제 chronological commit history
5. 정상·경계·failure matrix
6. load/performance evidence
7. macOS/Linux 검증 차이
8. dependency와 artifact identity
9. 현재 보장
10. 현재 비보장
11. `devlog/`를 생성·수정하지 않았다는 확인

---

## 39. 최종 정본 문장

이 프로젝트의 기본 설계 원칙은 다음 한 문장으로 요약한다.

> **하나의 C++ authoritative game-server 프로젝트를 완성된 단일 instance에서 시작하고, 독립 lifecycle을 얻은 구성요소만 장기 branch로 분리하며, realtime transport → measured optimization → multi-instance coordination → service extraction → durable event path → orchestration 순으로 실제 문제와 evidence에 따라 진화시킨다.**
