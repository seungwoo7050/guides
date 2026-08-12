# 42·Sportsbook·Game Server 병렬 학습 트랙

_프로젝트 구현에 직접 필요한 guides/docs만 배치한 누적형 실행 명세_

> 범위: 42 저장소의 15개 project branch, Sportsbook의 9개 project branch, 신규 `game-server` project 1개
>
> 원칙: 언어·framework·platform·domain model처럼 **프로젝트 구현을 시작하기 위해 직접 필요한 guide만** 선행에 둔다. 알고리즘·운영체제·컴퓨터 구조·네트워크·분산 실패 같은 일반 CS 영역은 별도 guide 선행으로 강제하지 않고 해당 프로젝트의 요구·실패·검증 과정에서 학습한다.
>
> Game Server의 v1~v7은 7개 프로젝트가 아니라 하나의 저장소 안에서 이어지는 7개 release gate다.

작성 기준일: 2026-08-12

---

# 1. 문서 사용 규칙

## 1.1 guides 포함 기준

guide branch 또는 docs가 트랙에 들어가려면 다음 중 하나를 만족해야 한다.

1. 해당 언어로 코드를 작성하기 위한 언어·build model이다.
2. 해당 framework의 object lifecycle·request pipeline·persistence boundary처럼 framework 없이는 알 수 없는 구현 계약이다.
3. console program과 구조가 본질적으로 다른 Web·container·game runtime·Kubernetes workload model이다.
4. 다음 project가 직접 사용하는 storage·protocol·deployment medium의 최소 계약이다.

다음 이유만으로는 별도 guide 선행에 넣지 않는다.

- 프로젝트에서 등장할 가능성이 있다.
- 면접에서 자주 묻는다.
- CS 기초라서 전부 먼저 알아야 할 것 같다.
- 성능이나 장애 분석에 도움이 된다.
- 후속 release에서 언젠가 사용할 수 있다.

이런 내용은 project source, failure case, benchmark와 change quest에서 학습·검증한다.

## 1.2 docs 누적 규칙

- 같은 docs는 처음 필요한 project 앞에 한 번만 배치한다.
- 후행 project는 앞 단계에서 완료한 docs를 누적 사용한다.
- `전체` 표기는 해당 directory의 모든 문서를 뜻한다.
- 한 파일 중 project 범위 밖 내용이 섞인 경우 파일은 읽되 적용 범위를 명시한다.
- 실제 project가 같은 역할의 통합 결과물을 제공하면 guide의 capstone 문서는 필수 선행에서 제외할 수 있다.
- 이 문서는 guide branch 전체 이수 여부가 아니라 **project 진입에 필요한 docs 위치**를 정한다.

## 1.3 기존 project와 신규 project의 차이

### 42·Sportsbook

이미 구현된 project다.

```text
docs 확인
→ source·test·commit 복원
→ devlog 보정
→ 별도 change quest
```

### Game Server

빈 저장소에서 새로 구현한다.

```text
설계 승인
→ 실제 순차 commit
→ v1 release
→ v2~v7 누적 진화
```

Game Server 구현 에이전트는 devlog를 작성하지 않는다. 사용자가 실제 개발 history를 확인한 뒤 직접 작성한다.

---

# 2. 대상 project inventory

2026-08-12 기준 42와 Sportsbook의 `main`은 관리 branch로 보고 project 수에서 제외한다.

| 트랙 | project |
|---|---|
| C | `42:c/libft` |
|  | `42:c/get_next_line` |
|  | `42:c/ft_printf` |
|  | `42:c/minitalk` |
|  | `42:c/minishell` |
|  | `42:c/philo` |
|  | `42:c/push_swap` |
| C++ | `42:c++/CPP0N` |
|  | `42:c++/ft_container` |
|  | `42:c++/miniRT` |
|  | `42:c++/ft_irc` |
| Web | `42:web/WEB0N` |
|  | `42:web/portfolio` |
|  | `42:web/inception` |
|  | `42:web/ft_transcendence` |
| Game Server | `game-server` — v1~v7 누적 release |
| Sportsbook | `sportsbook:shared-protocol` |
|  | `sportsbook:wallet-service` |
|  | `sportsbook:risk-service` |
|  | `sportsbook:odds-feed-service` |
|  | `sportsbook:betting-service` |
|  | `sportsbook:settlement-service` |
|  | `sportsbook:gateway` |
|  | `sportsbook:admin-api` |
|  | `sportsbook:orchestration` |

총 project는 25개다.

---

# 3. 한 가지 권장 선형화

| 순서 | project | 새로 소유하는 문제 |
|---:|---|---|
| 1 | `42:c/libft` | C program model, memory, string, library |
| 2 | `42:c/get_next_line` | partial read, EOF, caller 사이 state |
| 3 | `42:c/ft_printf` | variadic input, format parser, output failure |
| 4 | `42:c/minitalk` | process signal protocol |
| 5 | `42:c/minishell` | parser, process, pipe, FD graph, parent state |
| 6 | `42:c/philo` | shared-memory concurrency와 종료 |
| 7 | `42:c++/CPP0N` | C++98 object model, exception, template |
| 8 | `42:c++/ft_container` | allocator, iterator, tree invariant |
| 9 | `42:c/push_swap` | 제한 명령 state transition과 complexity |
| 10 | `42:c++/miniRT` | Modern C++, polymorphic ownership, parallel render |
| 11 | `42:c++/ft_irc` | nonblocking socket, event loop, output pressure |
| 12 | `42:web/WEB0N` | browser·HTTP·runtime 경계 |
| 13 | `42:web/portfolio` | React·Next.js frontend 구조 |
| 14 | `42:web/inception` | container·Compose·persistent runtime |
| 15 | `42:web/ft_transcendence` | frontend·API·DB·WebSocket 통합 |
| 16 | `game-server` | C++20 authoritative server를 v1로 만들고 v7까지 진화 |
| 17 | `sportsbook:shared-protocol` | Java·Avro 공통 계약 |
| 18 | `sportsbook:wallet-service` | ledger·transaction·idempotent money movement |
| 19 | `sportsbook:risk-service` | Redis Lua reservation과 expiry |
| 20 | `sportsbook:odds-feed-service` | provider·Redis·Kafka stream |
| 21 | `sportsbook:betting-service` | 여러 domain owner의 접수 조정 |
| 22 | `sportsbook:settlement-service` | settlement plan·lease·recovery |
| 23 | `sportsbook:gateway` | user edge, rate limit, realtime delivery |
| 24 | `sportsbook:admin-api` | control plane, authorization, audit |
| 25 | `sportsbook:orchestration` | 전체 build·Compose·E2E·failure integration |

표의 Game Server는 한 줄이지만 release 순서는 Sportsbook과 교차한다.

---

# 4. 병렬화와 교차 진화

```text
C
libft
→ get_next_line || ft_printf
→ minitalk
→ minishell || philo

C++ 
libft 완료
→ CPP0N
→ ft_container
→ push_swap
→ miniRT
→ ft_irc

Web
WEB0N
→ portfolio || inception
→ ft_transcendence

Game Server 초기
ft_irc + ft_transcendence
→ GS-v1
→ GS-v2
→ GS-v3

Sportsbook
Web 완료 권장
→ Java 기반
→ shared-protocol
→ Spring·DB 기반
→ wallet || risk || odds-feed
→ betting
→ settlement
→ gateway || admin-api
→ orchestration

Game Server 후반 교차
risk-service 완료
→ GS-v4 Redis multi-instance

betting-service 완료
→ GS-v5 service extraction

settlement-service 완료
→ GS-v6 Kafka event path

orchestration 완료
→ GS-v7 Kubernetes
```

효율을 높이려면 `GS-v1~v3`와 `Sportsbook Java 기반~SB-2`를 병렬로 진행할 수 있다. 단, 한 시점에 두 개 모두 구현하면 검증 evidence가 섞이므로 release 단위로 작업 공간과 commit을 분리한다.

## 4.1 트랙 관계

| 관계 | 강도 | 이유 |
|---|---|---|
| `libft → C++` | 강한 권장 | pointer, allocation, multi-file build를 재사용 |
| `ft_container → push_swap` | 권장 | invariant와 complexity를 다른 언어 problem에 전이 |
| `WEB0N → portfolio` | 강한 권장 | browser state와 URL contract가 먼저 필요 |
| `portfolio + inception → ft_transcendence` | 강한 권장 | frontend와 runtime infrastructure를 통합 |
| `ft_irc → GS-v1` | 필수 | event-driven socket server의 직접 전 단계 |
| `ft_transcendence → GS-v1` | 강한 권장 | PostgreSQL과 read-only web control plane을 재사용 |
| `GS-v1 → v2 → v3` | 필수 | UDP와 optimization 전에 single-node correctness가 필요 |
| `risk-service → GS-v4` | 강한 권장 | Redis atomic state·expiry를 다른 domain에 전이 |
| `betting-service → GS-v5` | 강한 권장 | 여러 owner 사이 partial state를 경험한 뒤 process를 분리 |
| `settlement-service → GS-v6` | 강한 권장 | event order·retry·recovery를 Kafka path에 전이 |
| `orchestration → GS-v7` | 강한 권장 | multi-process runtime을 먼저 통합한 뒤 Kubernetes로 이동 |

---

# 5. C 트랙

C project에 필요한 언어·POSIX API docs만 `guides:c`에서 배치한다. 운영체제 이론을 별도 선행하지 않는다.

## Quest C-0 — libft

### 선행 docs

```text
guides:c/docs/00-roadmap.md
guides:c/docs/01-foundations/ 전체
guides:c/docs/02-c-language/01-c-program-model.md
guides:c/docs/02-c-language/02-memory-pointers-strings.md
guides:c/docs/02-c-language/03-data-structures-api-design.md
guides:c/docs/02-c-language/04-build-link-test.md
```

### Project

```text
42:c/libft
```

이 단계에서 C 공통 기반을 닫는다.

## Quest C-1A — get_next_line

### 선행 docs

```text
guides:c/docs/03-unix-programming/01-posix-io-streams.md
```

### Project

```text
42:c/get_next_line
```

## Quest C-1B — ft_printf

### 선행 docs

```text
guides:c/docs/02-c-language/05-variadic-format-api.md
```

### Project

```text
42:c/ft_printf
```

`get_next_line`과 병렬 가능하다.

## Quest C-2 — minitalk

### 선행 docs

```text
guides:c/docs/03-unix-programming/02-process-fd-pipe.md
guides:c/docs/03-unix-programming/03-signals-events.md
```

### Project

```text
42:c/minitalk
```

## Quest C-3A — minishell

### 선행 docs

```text
guides:c/docs/03-unix-programming/04-shell-parser-executor.md
guides:c/docs/90-appendix/02-readline-integration.md
guides:c/docs/90-appendix/03-unix-text-testing.md
```

### Project

```text
42:c/minishell
```

## Quest C-3B — philo

### 선행 docs

```text
guides:c/docs/04-concurrency/01-threads-time.md
```

### Project

```text
42:c/philo
```

`minishell`과 병렬 가능하다. scheduling, race, deadlock의 일반 이론을 별도 선행으로 두지 않고 이 project의 source·failure·test에서 다룬다.

## Bridge — push_swap

### 신규 선행 docs

```text
없음
```

### Project

```text
42:c/push_swap
```

C 자료구조와 앞선 C++ invariant 관점을 누적 사용한다. 별도 algorithms guide는 선행 조건으로 두지 않는다.

---

# 6. C++ 트랙

C++ project와 Game Server의 언어·resource model은 `guides:cpp`가 담당한다.

## Quest CPP-0 — CPP0N

### 선행 docs

```text
guides:cpp/docs/00-roadmap.md
guides:cpp/docs/02-cpp98-systems/00-roadmap.md
guides:cpp/docs/02-cpp98-systems/01-program-and-type-model.md
guides:cpp/docs/02-cpp98-systems/02-lifetime-value-and-ownership.md
guides:cpp/docs/02-cpp98-systems/03-assigning-object-responsibilities.md
guides:cpp/docs/02-cpp98-systems/04-inheritance-and-polymorphism.md
guides:cpp/docs/02-cpp98-systems/05-errors-validation-and-casts.md
guides:cpp/docs/02-cpp98-systems/06-templates-iterators-and-stl.md
guides:cpp/docs/02-cpp98-systems/07-solving-problems-with-stl.md
guides:cpp/docs/90-appendix/03-cpp98-build-and-compatibility.md
```

### Project

```text
42:c++/CPP0N
```

## Quest CPP-1 — ft_container

### 선행 docs

```text
guides:cpp/docs/90-appendix/04-stl-internals.md
```

### Project

```text
42:c++/ft_container
```

## Quest CPP-2 — miniRT

### 선행 docs

```text
guides:cpp/docs/01-modern-cpp/01-program-build-cmake.md
guides:cpp/docs/01-modern-cpp/02-values-lifetimes-and-move.md
guides:cpp/docs/01-modern-cpp/03-raii-smart-pointers-and-rule-of-zero.md
guides:cpp/docs/01-modern-cpp/04-classes-responsibilities-and-polymorphism.md
guides:cpp/docs/01-modern-cpp/05-errors-optional-variant-and-expected.md
guides:cpp/docs/01-modern-cpp/07-concurrency-time-and-filesystem.md
guides:cpp/docs/01-modern-cpp/08-testing-debugging-and-tooling.md
```

### Project

```text
42:c++/miniRT
```

project standard와 guide standard가 다르면 실제 project compile option을 우선하고 사용할 수 없는 문법을 억지로 이식하지 않는다.

## Quest CPP-3 — ft_irc

### 선행 docs

```text
guides:cpp/docs/02-cpp98-systems/08-posix-sockets-and-event-loop.md
```

### Project

```text
42:c++/ft_irc
```

`ft_irc`가 끝난 뒤 Game Server에서 같은 socket API를 복사하는 것이 아니라 connection/session/state ownership을 확장한다.

---

# 7. Web 트랙

Web은 console project와 다른 browser, URL, HTTP, frontend/backend, persistent runtime 경계를 가지므로 독립 guide 선행을 둔다.

## Quest WEB-0 — WEB0N

### 선행 docs

```text
guides:web-app/docs/00-roadmap.md
guides:web-app/docs/01-web-foundations/ 전체

guides:web-infra/docs/00-roadmap.md
guides:web-infra/docs/01-web-request-and-server.md
```

### Project

```text
42:web/WEB0N
```

## Quest WEB-1A — portfolio

### 선행 docs

```text
guides:web-app/docs/02-frontend/ 전체

guides:web-front-react-nextjs/docs/00-roadmap-and-prerequisites.md
guides:web-front-react-nextjs/docs/01-project-onboarding.md
guides:web-front-react-nextjs/docs/02-ui-and-state-architecture.md
guides:web-front-react-nextjs/docs/03-nextjs-data-effects-and-concurrency.md
guides:web-front-react-nextjs/docs/04-testing-accessibility-and-performance.md
guides:web-front-react-nextjs/docs/05-production-runtime-contract.md
```

### Project

```text
42:web/portfolio
```

## Quest WEB-1B — inception

### 선행 docs

```text
guides:web-infra/docs/02-docker-image-and-container.md
guides:web-infra/docs/03-compose-network-and-storage.md
guides:web-infra/docs/04-nginx-tls-and-php-fpm.md
guides:web-infra/docs/05-database-lifecycle.md
guides:web-infra/docs/06-idempotent-app-bootstrap.md
guides:web-infra/docs/07-operations-debugging-and-recovery.md
guides:web-infra/docs/08-production-contract-and-threat-model.md
guides:web-infra/docs/13-production-secrets-and-configuration.md
guides:web-infra/docs/15-backup-restore-and-disaster-recovery.md
guides:web-infra/docs/16-capacity-resource-limits-and-updates.md
```

### Project

```text
42:web/inception
```

## Quest WEB-2 — ft_transcendence

### 선행 docs

```text
guides:web-app/docs/03-backend/ 전체
guides:web-app/docs/04-data-and-security/ 전체
guides:web-app/docs/05-realtime-and-quality/ 전체
```

### Project

```text
42:web/ft_transcendence
```

`portfolio`와 `inception`의 합류점이다.

---

# 8. Game Server 누적 release

Game Server는 별도 CS 교과과정이 아니다. C++·Web 트랙에서 얻은 구현 능력을 game domain에 적용하는 신규 project다.

프로젝트 기준은 별도 `game_server_agent_blueprint.md`가 소유한다.

## GS-v1 — TCP authoritative server

### 진입 project

```text
42:c++/ft_irc
42:web/ft_transcendence
```

### 신규 선행 docs

```text
guides:game-development/docs/02-game-loop-time-and-frames.md
guides:game-development/docs/03-input-command-camera-and-ui.md
guides:game-development/docs/05-gameplay-rules-progression-and-data.md
guides:game-development/docs/07-collision-physics-movement-and-space.md
guides:game-development/docs/09-save-migration-replay-and-determinism.md
guides:game-development/docs/11-network-authority-replication-and-latency.md
guides:game-development/docs/13-testing-debugging-telemetry-and-reproduction.md
```

적용 범위:

- `03`: command contract만 사용
- `07`: server-side movement와 validation만 사용
- client camera, UI, presentation, rendering은 구현하지 않음

### 완료 범위

```text
C++20
kqueue / epoll
TCP binary protocol
Connection / Session / Player / Room
fixed tick
authoritative state
PostgreSQL
reconnect
read-only HTTP control plane
minimal web dashboard
load/failure evidence
```

## GS-v2 — UDP realtime transport

### 신규 선행 docs

```text
없음
```

`game-development/docs/11-network-authority-replication-and-latency.md`의 authority·sequence·snapshot contract를 v1에서 누적 사용한다.

### 완료 범위

```text
UDP input
state snapshot
sequence
tick identity
loss / duplicate / reordering
prediction-supporting server protocol
```

client prediction 자체는 구현하지 않는다.

## GS-v3 — performance와 concurrency

### 신규 선행 docs

```text
guides:game-development/docs/14-performance-budgets-profiling-and-scalability.md
```

### 완료 범위

```text
representative workload
p50 / p95 / p99
CPU / memory / queue profile
measured bottleneck
correctness-preserving optimization
conditional lock-free decision
```

lock-free queue는 완료 조건이 아니다. 병목과 topology가 정당화할 때만 도입한다.

## GS-v4 — Redis multi-instance

### 해금 project

```text
sportsbook:risk-service
```

### 신규 선행 docs

```text
없음
```

Redis 사용법과 atomic state·expiry는 `risk-service` 구현 경험을 전이한다. 일반 분산 서비스 guide를 별도 선행으로 추가하지 않는다.

### 완료 범위

```text
2개 이상 game-server instance
instance registry
presence
session / room location
lease / generation
Redis outage와 stale owner
```

authoritative room state는 Redis로 옮기지 않는다.

## GS-v5 — service extraction

### 해금 project

```text
sportsbook:betting-service
```

### 신규 선행 docs

```text
없음
```

Sportsbook에서 확인한 service boundary와 partial state를 다른 stack에 적용한다.

### 완료 범위

```text
modular monolith의 측정
정당화된 process boundary
Gateway / Matchmaker / Game Server 후보
timeout
compatibility
partial failure
```

객체마다 service를 만들지 않는다.

## GS-v6 — Kafka event path

### 해금 project

```text
sportsbook:settlement-service
```

### 신규 선행 docs

```text
없음
```

Sportsbook의 Kafka·outbox·recovery 구현 경험을 C++ event producer/consumer 경계로 전이한다.

### 완료 범위

```text
MatchFinished 등 비동기 domain event
outbox
Kafka
idempotent consumer
late / duplicate event
lag / replay
```

game tick의 critical path에 Kafka를 넣지 않는다.

## GS-v7 — Kubernetes orchestration

### 해금 project

```text
sportsbook:orchestration
```

### 신규 선행 docs

```text
guides:platform-engineering/docs/05-kubernetes-api-workloads-and-controllers.md
guides:platform-engineering/docs/06-kubernetes-network-storage-and-scheduling.md
```

### 누적 docs

```text
guides:web-infra/docs/11-image-registry-and-release-artifacts.md
guides:web-infra/docs/12-ci-cd-deployment-and-rollback.md
guides:web-infra/docs/14-observability-and-alerting.md
guides:web-infra/docs/16-capacity-resource-limits-and-updates.md
guides:web-infra/docs/17-incident-response-and-runbooks.md
```

### 완료 범위

```text
container images
Kubernetes workloads
startup / readiness / liveness
resource requests / limits
service discovery
rolling update
Pod loss
connection and room drain
scale-out evidence
```

Kubernetes를 사용했다는 사실이 아니라 stateful termination과 recovery가 완료 기준이다.

---

# 9. Sportsbook 트랙

Sportsbook은 Web 트랙의 HTTP·DB·auth·realtime·container model을 누적 사용하고 Java·Spring framework contract만 새로 닫는다.

## SB-0 — Java 기반

### 선행 docs

```text
guides:java/docs/00-roadmap.md
guides:java/docs/01-language-and-domain/ 전체
guides:java/docs/03-build-test-and-evidence/ 전체
```

### 결과

공통 Java project model을 확보한다.

## SB-1 — shared-protocol

### 신규 선행 docs

```text
없음
```

### Project

```text
sportsbook:shared-protocol
```

## SB-2 — Spring·DB 실행 기반

### 선행 docs

```text
guides:java/docs/02-runtime-and-concurrency/01-concurrency-locking-and-executors.md

guides:backend-spring-boot/docs/00-roadmap.md
guides:backend-spring-boot/docs/01-spring-core/ 전체
guides:backend-spring-boot/docs/02-web-and-security/01-mvc-validation-and-problem-detail.md
guides:backend-spring-boot/docs/03-persistence-and-cache/ 전체
guides:backend-spring-boot/docs/04-distributed-adapters/ 전체
guides:backend-spring-boot/docs/05-quality-and-operations/ 전체

guides:database-systems/docs/00-roadmap.md
guides:database-systems/docs/01-relational-semantics-and-design/ 전체
guides:database-systems/docs/03-transactions-and-recovery/01-transactions-isolation-and-locks.md
guides:database-systems/docs/04-execution-and-optimization/02-statistics-cost-model-and-explain.md
guides:database-systems/docs/04-execution-and-optimization/03-schema-index-and-tuning-loop.md
```

이 단계는 별도 product가 아니라 후속 service의 framework·persistence 진입점이다.

## SB-3 — 병렬 domain services

### 신규 선행 docs

```text
없음
```

### 병렬 project

```text
sportsbook:wallet-service
sportsbook:risk-service
sportsbook:odds-feed-service
```

각 service는 SB-2의 Java·Spring·DB docs를 누적 사용한다.

## SB-4 — betting-service

### 신규 선행 docs

```text
없음
```

### Project

```text
sportsbook:betting-service
```

wallet·risk·odds-feed contract의 합류점이다.

## SB-5 — settlement-service

### 신규 선행 docs

```text
guides:database-systems/docs/05-capstones/01-application-database-review.md
```

### Project

```text
sportsbook:settlement-service
```

이 문서는 wallet·betting·settlement schema와 transaction을 종합 검토하는 용도로 settlement 구현 뒤에 적용해도 된다.

## SB-6 — gateway와 admin-api

### 선행 docs

```text
guides:backend-spring-boot/docs/02-web-and-security/02-spring-security-request-model.md
guides:backend-spring-boot/docs/02-web-and-security/03-authentication-authorization-and-csrf.md
```

### 병렬 project

```text
sportsbook:gateway
sportsbook:admin-api
```

## SB-7 — orchestration

### 신규 선행 docs

```text
guides:web-infra/docs/11-image-registry-and-release-artifacts.md
guides:web-infra/docs/12-ci-cd-deployment-and-rollback.md
guides:web-infra/docs/14-observability-and-alerting.md
guides:web-infra/docs/17-incident-response-and-runbooks.md
```

### Project

```text
sportsbook:orchestration
```

모든 service의 exact build, configuration, startup, failure와 recovery를 통합한다.

---

# 10. 실제 병렬 실행안

```text
Track A — C
libft
→ (get_next_line || ft_printf)
→ minitalk
→ (minishell || philo)

Track B — C++
libft 완료
→ CPP0N
→ ft_container
→ push_swap
→ miniRT
→ ft_irc

Track C — Web
WEB0N
→ (portfolio || inception)
→ ft_transcendence

Track D — Game Server 초기
ft_irc + ft_transcendence
→ GS-v1
→ GS-v2
→ GS-v3

Track E — Sportsbook
Web 완료 권장
→ Java
→ shared-protocol
→ Spring·DB
→ (wallet || risk || odds-feed)
→ betting
→ settlement
→ (gateway || admin-api)
→ orchestration

Cross-release
risk-service
→ GS-v4

betting-service
→ GS-v5

settlement-service
→ GS-v6

orchestration
→ GS-v7
```

---

# 11. 완료 판정

## 11.1 기존 42·Sportsbook project

- 지정된 docs의 핵심 contract를 project source에서 찾을 수 있다.
- source·test·commit과 devlog 주장이 일치한다.
- 별도 change quest로 새 요구를 반영한다.
- project 전체 회귀와 새 failure case를 통과한다.
- exact SHA evidence를 남긴다.

## 11.2 Game Server

- 빈 저장소에서 synthetic history 없이 실제 순차 commit으로 구현한다.
- v1은 독립 완성형이다.
- v2~v7은 직전 release를 회귀 검증한다.
- 각 release가 진입 문제, architecture 변화, failure와 evidence를 가진다.
- web dashboard는 read-only control plane이며 game client가 아니다.
- devlog는 사용자가 직접 작성한다.

## 11.3 전체 과정

- guide branch를 많이 읽은 것으로 완료를 판정하지 않는다.
- 각 guide docs가 실제 project 구현 경계에 연결돼야 한다.
- 일반 CS 주제는 별도 선행 이수 여부가 아니라 project의 설명·failure·benchmark에서 판정한다.
- 최종 대표작은 모든 project를 나열하지 않고 직무별로 선별한다.
