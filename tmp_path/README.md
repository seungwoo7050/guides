# 42 및 후속 두 프로젝트의 선행 가이드 트랙

## 0. 판정 규칙

이 문서에서 **선행 문서**는 프로젝트 구현을 시작하기 전에 알아야 하는 언어·런타임·프로토콜·프레임워크 구조만 뜻한다.

다음은 선행으로 잡지 않는다.

- 프로젝트를 구현하면서 충분히 배울 수 있는 알고리즘·내부 이론
- 디버깅, 프로파일링, 성능 측정, 운영 고도화처럼 구현 중·후반에 붙여도 되는 내용
- 이미 앞 프로젝트에서 읽은 문서
- 같은 개념을 더 깊게 반복하는 문서
- 가이드의 로드맵, capstone, 실무 점검표 자체
- `guides/` 각 브랜치의 `docs/` 밖에 있는 파일

단 하나의 예외는 사용자가 직접 프로젝트 명세로 지정한 다음 파일이다.

```text
guides/main/tmp_path/game_server_agent_blueprint_self_contained_final.md
```

이 파일은 **가이드 선행 문서가 아니라 게임 서버 프로젝트의 정본 명세**로 취급한다. v1까지만 사용하며 v2 이후는 무시한다.

42 과정에서는 하나의 전역 완료 집합 `DONE`을 사용한다.

```text
프로젝트 시작 전 필요한 docs
- DONE
= 이번 프로젝트에서 새로 읽을 docs
```

42 이후 두 트랙을 병렬로 진행할 때도 같은 원칙을 사용한다. 한 트랙이 공통 문서를 먼저 읽었다면 다른 트랙은 다시 읽지 않는다.

---

# Part I. 42 완전 선형 트랙

## 1. 고정 프로젝트 순서

| 순서 | 42 브랜치 | 배치 이유 |
|---:|---|---|
| 1 | `c/libft` | C 객체·메모리·문자열·정적 라이브러리의 공통 기반 |
| 2 | `c/get_next_line` | `read`, EOF, 부분 입력과 호출 간 상태 |
| 3 | `c/ft_printf` | 가변 인자와 출력 계약 |
| 4 | `c/push_swap` | 새 시스템 지식 없이 C 자료 표현과 상태 전이를 적용 |
| 5 | `c/minitalk` | 프로세스 간 시그널 프로토콜 |
| 6 | `c/philo` | 큰 C 통합 프로젝트 전에 독립된 공유 상태·시간·동기화 모델 학습 |
| 7 | `c/minishell` | 파서·프로세스·FD·파이프·시그널을 합치는 C 최종 통합 프로젝트 |
| 8 | `c++/CPP0N` | C++98 객체 모델 전체 |
| 9 | `c++/ft_container` | 템플릿·반복자·allocator·컨테이너 내부 구조 |
| 10 | `c++/miniRT` | C++17, CMake, 스마트 포인터와 병렬 작업으로 확장 |
| 11 | `c++/ft_irc` | 논블로킹 TCP, 연결 상태, epoll/kqueue와 역압 |
| 12 | `web/inception` | Docker·Compose·Nginx·PHP-FPM·DB 실행 구조 |
| 13 | `web/ft_transcendence` | 프런트·API·DB·인증·WebSocket을 합친 웹 애플리케이션 |
| 14 | `web/portfolio` | 앞의 웹 지식을 정적 콘텐츠·SSR·표현 설계에 적용하는 최종 프로젝트 |

`web/WEB0N`은 제외한다.

`push_swap`은 C++ 시리즈 문서에서 비교 대상으로 뒤에 등장하지만 C++ 객체 모델이나 allocator가 필요하지 않으므로 C 구간으로 이동한다.

`philo`는 `minishell`의 선행이 아니지만 더 작고 독립된 실행 모델이다. 따라서 공유 상태·시간 문제를 먼저 끝낸 뒤 가장 큰 C 통합 프로젝트인 `minishell`로 간다.

---

## 2. 프로젝트별 신규 선행 docs

## 2.1 `c/libft`

### 새로 읽기

- [ ] `c/docs/02-c-language/01-c-program-model.md`
- [ ] `c/docs/02-c-language/02-memory-pointers-strings.md`
- [ ] `c/docs/02-c-language/03-data-structures-api-design.md`
- [ ] `c/docs/02-c-language/04-build-link-test.md`

### 이유

C 번역 단위·링크, 포인터와 객체 수명, 문자열, 소유권, 실패 뒤 상태, 공개 API와 정적 라이브러리를 모르면 `libft`의 첫 함수부터 계약을 제대로 정할 수 없다.

`c/docs/01-foundations/`는 프로그래밍 입문 과정이므로 현재 트랙에서는 제외한다.

---

## 2.2 `c/get_next_line`

### 새로 읽기

- [ ] `c/docs/03-unix-programming/01-posix-io-streams.md`

### 이유

한 번의 `read`와 한 줄이 일치하지 않는다는 사실, 부분 read, EOF·오류와 호출 사이에 남는 버퍼가 프로젝트 구조 자체다.

---

## 2.3 `c/ft_printf`

### 새로 읽기

- [ ] `c/docs/02-c-language/05-variadic-format-api.md`

### 이유

포맷 문자열과 실제 인자 타입·개수 사이에는 정적 타입 검사가 없다. `va_list` 수명과 변환 dispatch를 모르면 구현을 시작해도 API 계약을 잘못 잡기 쉽다.

---

## 2.4 `c/push_swap`

### 새로 읽기

없음.

### 누적 기반

- C 자료구조와 API 계약
- 메모리 소유권
- 빌드·테스트

별도 `algorithms` 가이드는 선행하지 않는다. rank 변환, 작은 입력 처리, radix와 명령 수 검증은 이 프로젝트를 통해 학습할 수 있다.

---

## 2.5 `c/minitalk`

### 새로 읽기

- [ ] `c/docs/03-unix-programming/03-signals-events.md`

### 이유

시그널은 바이트 스트림이 아니며 handler는 일반 실행 문맥이 아니다. `sigaction`, mask, async-signal-safe 범위와 ACK 상태를 모르면 프로토콜 설계부터 잘못된다.

---

## 2.6 `c/philo`

### 새로 읽기

- [ ] `c/docs/04-concurrency/01-threads-time.md`

### 이유

pthread API 암기보다 공유 불변식, mutex 소유권, lock 순서, 단조 시계, 종료·join·destroy 순서가 구현 구조를 결정한다.

별도 운영체제 가이드는 선행하지 않는다.

---

## 2.7 `c/minishell`

### 새로 읽기

- [ ] `c/docs/03-unix-programming/02-process-fd-pipe.md`
- [ ] `c/docs/03-unix-programming/04-shell-parser-executor.md`

### 이미 완료된 관련 문서

- `c/docs/03-unix-programming/01-posix-io-streams.md`
- `c/docs/03-unix-programming/03-signals-events.md`

### 이유

셸은 문법 결과를 process·FD graph로 실행하는 프로그램이다. 파서와 실행기를 분리하고, fork 전후 누가 어떤 FD를 닫는지 모르면 파이프라인·리다이렉션·builtin 구조를 제대로 만들 수 없다.

---

## 2.8 `c++/CPP0N`

### 새로 읽기

- [ ] `cpp/docs/02-cpp98-systems/01-program-and-type-model.md`
- [ ] `cpp/docs/02-cpp98-systems/02-lifetime-value-and-ownership.md`
- [ ] `cpp/docs/02-cpp98-systems/03-assigning-object-responsibilities.md`
- [ ] `cpp/docs/02-cpp98-systems/04-inheritance-and-polymorphism.md`
- [ ] `cpp/docs/02-cpp98-systems/05-errors-validation-and-casts.md`
- [ ] `cpp/docs/02-cpp98-systems/06-templates-iterators-and-stl.md`
- [ ] `cpp/docs/02-cpp98-systems/07-solving-problems-with-stl.md`

### 이유

이 브랜치는 생성자·소멸자·복사, Rule of Three, 상속·다형성, 예외, 형변환, template·iterator까지 포함한다. C 경험만으로는 이 객체 모델을 대체할 수 없다.

---

## 2.9 `c++/ft_container`

### 새로 읽기

- [ ] `cpp/docs/90-appendix/04-stl-internals.md`

### 이미 완료된 관련 문서

- `cpp/docs/02-cpp98-systems/06-templates-iterators-and-stl.md`
- `cpp/docs/02-cpp98-systems/07-solving-problems-with-stl.md`

### 이유

일반 STL 사용법이 아니라 allocator가 확보한 미초기화 저장 공간, 객체 생성·파괴, iterator category, SFINAE, 재할당 rollback과 트리 node 수명이 프로젝트 본체다. 일반 과정에서는 선택 심화지만 `ft_container`에는 필수다.

별도 `algorithms` 가이드는 선행하지 않는다.

---

## 2.10 `c++/miniRT`

### 새로 읽기

- [ ] `cpp/docs/01-modern-cpp/01-program-build-cmake.md`
- [ ] `cpp/docs/01-modern-cpp/02-values-lifetimes-and-move.md`
- [ ] `cpp/docs/01-modern-cpp/03-raii-smart-pointers-and-rule-of-zero.md`
- [ ] `cpp/docs/01-modern-cpp/07-concurrency-time-and-filesystem.md`

### 이유

이 프로젝트는 C++17·CMake, `unique_ptr`, 이동, Rule of Zero, worker thread와 파일 출력을 사용한다. C++98 객체 모델만으로는 실제 소유권·빌드·병렬 실행 구조가 부족하다.

`computer-graphics`는 사용자가 제외한 브랜치이며, 광선·교차·BVH는 프로젝트를 구현하면서 학습한다.

---

## 2.11 `c++/ft_irc`

### 새로 읽기

- [ ] `cpp/docs/02-cpp98-systems/08-posix-sockets-and-event-loop.md`

### 이유

이 프로젝트에는 실제 선행 네트워크 구조가 필요하다. 다만 필요한 범위는 다음으로 좁다.

- socket·bind·listen·accept와 FD 소유권
- TCP 바이트 스트림과 framing
- 부분 read/write
- `EINTR`, `EAGAIN`, EOF
- 연결별 입력·출력 buffer
- epoll/kqueue poller abstraction
- backpressure와 연결 종료 순서

이 문서가 해당 구현 구조를 직접 다루므로 `computer-networks` 전체나 TCP 내부 알고리즘 문서는 추가하지 않는다.

---

## 2.12 `web/inception`

### 새로 읽기

- [ ] `web-infra/docs/01-web-request-and-server.md`
- [ ] `web-infra/docs/02-docker-image-and-container.md`
- [ ] `web-infra/docs/03-compose-network-and-storage.md`
- [ ] `web-infra/docs/04-nginx-tls-and-php-fpm.md`
- [ ] `web-infra/docs/05-database-lifecycle.md`
- [ ] `web-infra/docs/06-idempotent-app-bootstrap.md`

### 이유

이미지·컨테이너·PID 1, Compose network·published port·volume, Nginx→PHP-FPM→MariaDB 요청 경로, 빈 DB와 기존 DB 구분, 반복 가능한 bootstrap은 프로젝트의 설계 자체다.

`07-operations-debugging-and-recovery.md` 이후는 구현 중·후반 운영 학습으로 남긴다.

---

## 2.13 `web/ft_transcendence`

### 새로 읽기

#### 브라우저·언어·런타임

- [ ] `web-app/docs/01-web-foundations/02-html-forms-accessibility.md`
- [ ] `web-app/docs/01-web-foundations/03-css-layout-responsive.md`
- [ ] `web-app/docs/01-web-foundations/04-javascript-foundations.md`
- [ ] `web-app/docs/01-web-foundations/05-dom-events-url-storage.md`
- [ ] `web-app/docs/01-web-foundations/06-async-fetch-errors.md`
- [ ] `web-app/docs/01-web-foundations/07-typescript-runtime-validation.md`
- [ ] `web-app/docs/01-web-foundations/08-node-packages-workspaces.md`

`01-how-the-web-works.md`는 `web-infra/docs/01-web-request-and-server.md`에서 이미 URL·TCP·HTTP·method·status·server process 경계를 배웠으므로 생략한다.

#### React·Next.js

- [ ] `web-app/docs/02-frontend/01-react-components-state.md`
- [ ] `web-app/docs/02-frontend/02-react-forms-lists.md`
- [ ] `web-app/docs/02-frontend/03-react-effects-async.md`
- [ ] `web-app/docs/02-frontend/04-nextjs-routing-rendering.md`
- [ ] `web-app/docs/02-frontend/05-nextjs-data-boundaries.md`

#### API 구조

- [ ] `web-app/docs/03-backend/01-http-api-model.md`
- [ ] `web-app/docs/03-backend/02-fastify-lifecycle.md`
- [ ] `web-app/docs/03-backend/03-zod-contracts.md`
- [ ] `web-app/docs/03-backend/04-service-repository-errors.md`

#### DB·인증·권한

- [ ] `web-app/docs/04-data-and-security/01-sql-relational-model.md`
- [ ] `web-app/docs/04-data-and-security/02-postgresql-kysely.md`
- [ ] `web-app/docs/04-data-and-security/03-migrations-transactions.md`
- [ ] `web-app/docs/04-data-and-security/04-passwords-sessions-cookies.md`
- [ ] `web-app/docs/04-data-and-security/05-authorization-csrf-cors.md`

#### 실시간 게임 화면

- [ ] `web-app/docs/05-realtime-and-quality/01-websocket-protocol.md`
- [ ] `web-app/docs/05-realtime-and-quality/02-realtime-state-conflicts.md`
- [ ] `web-app/docs/05-realtime-and-quality/03-canvas-rendering.md`

### 이유

이 프로젝트는 단순 Next.js 화면이 아니다. HTTP·WebSocket 공용 계약, Fastify lifecycle, PostgreSQL transaction, session·권한, server-authoritative room state, browser interpolation을 함께 설계해야 한다. 각 영역의 구조가 구현 전에 필요하다.

`04-testing-quality.md`와 capstone 문서는 구현 과정에서 적용할 내용이므로 선행에서는 제외한다.

---

## 2.14 `web/portfolio`

### 새로 읽기

없음.

### 누적 기반

- HTML·CSS·접근성
- TypeScript와 runtime validation
- React·Next.js routing/rendering/data boundary
- production build 경험
- `ft_transcendence`에서 수행한 더 복잡한 전체 웹 구조

`web-front-react-nextjs`는 유용한 후속 심화 과정이지만 이 순서에서는 필수 선행이 아니다. 포트폴리오는 앞 프로젝트보다 구조적으로 단순하며, 상태 구조·접근성·성능·운영 빌드의 심화는 프로젝트를 구현하면서 검증할 수 있다.

---

## 3. 42에서 의도적으로 사용하지 않는 주요 가이드

| 가이드 브랜치 | 제외 이유 |
|---|---|
| `algorithms` | `push_swap`, `ft_container`, BVH 알고리즘은 프로젝트 안에서 학습 가능하며 첫 구현 전 필수 구조가 아님 |
| `computer-architecture` | 어느 42 프로젝트도 CPU·메모리 계층 이론을 알아야 첫 설계를 세울 수 있는 구조가 아님 |
| `operating-systems` | C 동시성·프로세스 문서가 직접 필요한 사용자 공간 계약을 이미 제공 |
| `unix-systems` | C 가이드의 POSIX I/O·process·signal·shell 문서로 직접 구현 선행 범위 충족 |
| `computer-networks` | `ft_irc`에 필요한 구현 구조는 C++ socket/event-loop 문서가 직접 제공 |
| `database-systems` | 42 웹 프로젝트에는 `web-app`의 관계 모델·PostgreSQL·migration·transaction 기초면 시작 가능 |
| `distributed-services` | `ft_transcendence`는 단일 애플리케이션 안의 경계를 먼저 배우는 프로젝트이며 분산 수렴 패턴은 필수 선행이 아님 |
| `web-front-react-nextjs` | `ft_transcendence`까지 완료한 뒤의 `portfolio` 시작에는 `web-app` 누적 지식으로 충분 |
| `game-development` | 42의 `miniRT`는 게임 runtime 프로젝트가 아니며 `ft_transcendence`의 게임 규칙은 웹 가이드와 프로젝트 안에서 학습 가능 |
| `platform-engineering` | Kubernetes·플랫폼 운영이 42 또는 게임 서버 v1 범위에 없음 |

---

## 4. 42 선행 문서 수

정확한 파일 기준:

```text
C                  10
C++                13
web-infra           6
web-app            24
합계                53
```

`roadmap`, capstone, 일반 점검표와 선택 디버깅 부록은 포함하지 않았다.

---

# Part II. 42 이후 병렬 허용 트랙

두 트랙은 42의 `DONE` 집합을 공유한다.

```text
Track A: sportsbook 9개 branch
Track B: game server v1
```

트랙 내부 순서는 지키되 A와 B 사이에는 순서 제약이 없다.

동일 docs가 두 트랙에 나타나면 먼저 도달한 트랙에서 한 번만 읽고 전역 `DONE`에 기록한다.

---

# Track A. Sportsbook 9개 branch

## 5. 순서 선정 기준

우선순위는 다음과 같다.

1. 실제 compile/runtime dependency
2. 상태 소유권과 event 흐름
3. 학습 난이도
4. 동률일 때 포트폴리오 가치

포트폴리오 가치 순으로 시작하지 않는다. 예를 들어 gateway나 betting은 눈에 잘 띄지만 shared contract와 domain owner가 없으면 올바르게 구현할 수 없다.

## 6. 고정 branch 순서

```text
1. shared-protocol
2. wallet-service
3. risk-service
4. odds-feed-service
5. betting-service
6. settlement-service
7. admin-api
8. gateway
9. orchestration
```

### 순서 근거

- `shared-protocol`은 모든 Java value·JSON·Avro 계약의 owner다.
- `wallet`은 자금 효과와 멱등 원장을 먼저 제공한다.
- `risk`는 베팅 수락 전에 필요한 예약·한도 owner다.
- `odds-feed`는 betting이 접수 시 읽을 현재 경기·배당 projection을 만든다.
- `betting`은 risk·wallet·odds를 조정하고 `bet.placed`를 만든다.
- `settlement`는 `bet.placed`와 경기 결과를 받아 wallet 효과와 종료 event를 만든다.
- `admin-api`는 완성된 domain service에 운영 명령을 위임한다.
- `gateway`는 완성된 data plane을 외부에 노출하고 settlement event를 실시간 전달한다.
- `orchestration`은 앞의 여덟 branch를 통합 검증하므로 마지막이다.
- `admin-api`를 `gateway`보다 먼저 두는 이유는 단순한 MVC control plane에서 Spring Security·JWT·RBAC를 먼저 학습한 뒤 routing·rate limit·STOMP가 합쳐진 gateway로 넘어가기 위해서다.

---

## 7. Branch별 신규 선행 docs

## 7.1 `shared-protocol`

### Java 언어·빌드

- [ ] `java/docs/01-language-and-domain/01-jdk-jvm-and-first-program.md`
- [ ] `java/docs/01-language-and-domain/02-java-language-foundations.md`
- [ ] `java/docs/01-language-and-domain/03-domain-types-records-and-sealed-types.md`
- [ ] `java/docs/01-language-and-domain/04-collections-streams-and-numeric-invariants.md`
- [ ] `java/docs/01-language-and-domain/05-errors-validation-time-and-identifiers.md`
- [ ] `java/docs/03-build-test-and-evidence/01-maven-wrapper-and-lifecycle.md`

### 서비스·계약 경계

- [ ] `distributed-services/docs/01-boundaries-and-failure/02-service-boundaries-and-data-ownership.md`
- [ ] `distributed-services/docs/02-delivery-and-consistency/03-contracts-versioning-and-order.md`

### 이유

Java record·sealed type·정확한 숫자·식별자·Maven artifact를 알아야 공통 값 객체와 라이브러리를 만들 수 있다. 서비스 경계와 schema 호환성을 먼저 알아야 shared module에 서비스별 업무 규칙을 잘못 넣지 않는다.

---

## 7.2 `wallet-service`

### Spring Boot 기본 경계

- [ ] `backend-spring-boot/docs/01-spring-core/01-application-context-and-lifecycle.md`
- [ ] `backend-spring-boot/docs/01-spring-core/02-configuration-profiles-and-readiness.md`
- [ ] `backend-spring-boot/docs/02-web-and-security/01-mvc-validation-and-problem-detail.md`

### 영속성·Redis

- [ ] `backend-spring-boot/docs/03-persistence-and-cache/01-jpa-transactions-and-locking.md`
- [ ] `backend-spring-boot/docs/03-persistence-and-cache/02-flyway-and-schema-integration.md`
- [ ] `backend-spring-boot/docs/03-persistence-and-cache/03-spring-data-redis.md`

### Kafka·Outbox

- [ ] `backend-spring-boot/docs/04-distributed-adapters/01-spring-kafka-and-avro.md`
- [ ] `backend-spring-boot/docs/04-distributed-adapters/02-outbox-and-scheduling.md`

### DB 계약

- [ ] `database-systems/docs/01-relational-semantics-and-design/03-er-normalization-and-constraints.md`
- [ ] `database-systems/docs/03-transactions-and-recovery/01-transactions-isolation-and-locks.md`

### 분산 효과

- [ ] `distributed-services/docs/01-boundaries-and-failure/01-partial-failure-and-uncertain-outcomes.md`
- [ ] `distributed-services/docs/01-boundaries-and-failure/03-synchronous-and-asynchronous-decisions.md`
- [ ] `distributed-services/docs/02-delivery-and-consistency/01-idempotency-and-single-effects.md`
- [ ] `distributed-services/docs/02-delivery-and-consistency/02-outbox-saga-and-reconciliation.md`

### 이유

Wallet은 첫 Spring 실행 서비스이자 돈의 정본이다. Bean·설정·MVC, 실제 DB transaction·lock·constraint, Flyway, Redis adapter, Kafka·Outbox와 중복 효과를 모두 구현 전에 구분해야 한다.

---

## 7.3 `risk-service`

### 새로 읽기

없음.

### 누적 기반

- Spring core·MVC
- Spring Data Redis
- Spring Kafka
- 서비스별 데이터 owner
- 멱등성·부분 실패·동기/비동기 결정

Redis Lua, reservation lease와 keyspace는 이 프로젝트에서 처음 구현하며 별도 선행 가이드를 붙이지 않는다.

---

## 7.4 `odds-feed-service`

### 새로 읽기

- [ ] `distributed-services/docs/02-delivery-and-consistency/04-read-models-and-late-events.md`

### 이유

외부 provider 입력, Redis 현재값 projection, Kafka event와 Redis Stream 재처리를 한 정본으로 오인하지 않으려면 read model·지연 event·재구축 경계를 먼저 알아야 한다.

---

## 7.5 `betting-service`

### 새로 읽기

- [ ] `distributed-services/docs/03-resilience-and-load/01-timeouts-retries-circuit-breakers-and-dlq.md`
- [ ] `backend-spring-boot/docs/04-distributed-adapters/03-resilience4j-http-clients.md`

### 이유

Betting은 risk·wallet 원격 효과를 순차 조정한다. timeout 뒤 결과가 실패인지 성공인지 알 수 없는 상태, 정상 업무 거절과 의존성 장애, circuit breaker와 복구 가능한 `PENDING`을 구현 전에 구분해야 한다.

---

## 7.6 `settlement-service`

### 새로 읽기

- [ ] `java/docs/02-runtime-and-concurrency/01-concurrency-locking-and-executors.md`
- [ ] `distributed-services/docs/03-resilience-and-load/02-backpressure-bulkheads-and-load-shedding.md`

### 이유

정산은 persistent attempt, lease, recovery poller와 제한된 wallet worker를 사용한다. 실행기 queue·취소·interrupt·shutdown, bounded work와 saturation 정책을 모르면 복구와 종료 구조가 무너진다.

---

## 7.7 `admin-api`

### 새로 읽기

- [ ] `backend-spring-boot/docs/02-web-and-security/02-spring-security-request-model.md`
- [ ] `backend-spring-boot/docs/02-web-and-security/03-authentication-authorization-and-csrf.md`

### 이유

JWT 검증, security filter chain, 역할·객체 권한, 운영 명령 위임과 감사가 프로젝트 구조다. 단순히 endpoint에 role 문자열을 비교하는 방식으로 시작하면 신뢰 경계를 잘못 둔다.

---

## 7.8 `gateway`

### 새로 읽기

없음.

### 누적 기반

- 42의 HTTP·WebSocket·session·권한
- Spring Security
- Redis
- Kafka
- backpressure
- 완성된 betting·wallet·odds·settlement 계약

Spring Cloud Gateway와 STOMP의 구체 API는 프로젝트를 구현하면서 학습한다. 별도 일반 네트워크 가이드는 필요하지 않다.

---

## 7.9 `orchestration`

### 새로 읽기

- [ ] `distributed-services/docs/04-release-and-evidence/01-multi-repository-builds-and-release-manifests.md`
- [ ] `distributed-services/docs/04-release-and-evidence/02-distributed-observability.md`
- [ ] `distributed-services/docs/04-release-and-evidence/03-end-to-end-chaos-and-failure-evidence.md`
- [ ] `distributed-services/docs/04-release-and-evidence/04-performance-gates-and-claims.md`

### 이유

이 branch의 제품은 domain code가 아니라 정확한 revision 집합, 전체 build, Compose topology, cold E2E, 장애 주입, logs·metrics와 성능 주장이다. 이 네 문서가 곧 구현 구조다.

---

## 8. Sportsbook 신규 선행 문서 수

42 완료 이후 기준:

```text
Java                       7
Spring Boot               11
Database Systems           2
Distributed Services      13
합계                       33
```

---

# Track B. Game Server v1

## 9. v1에서 사용하는 branch와 실제 진행 순서

정본 명세의 순서를 그대로 사용한다.

```text
main bootstrap
→ shared-protocol
→ game-server core/network/session/runtime
→ loadgen bootstrap
→ game-server storage/observability/control
→ ops-dashboard
→ loadgen stress/failure completion
→ game-server performance/CI closure
→ main release manifest + integration gate
→ v1.0.0
```

장기 branch는 다음 다섯 개다.

```text
main
shared-protocol
game-server
loadgen
ops-dashboard
```

v2 이후의 UDP, Redis, Kafka, Kubernetes, 추가 service 분리는 전부 제외한다.

---

## 10. 단계별 신규 선행 docs

## 10.1 `main bootstrap`과 v1 계약 고정 전

### 게임 상태·시간·권위

- [ ] `game-development/docs/01-game-product-and-runtime-contract.md`
- [ ] `game-development/docs/02-game-loop-time-and-frames.md`
- [ ] `game-development/docs/05-gameplay-rules-progression-and-data.md`
- [ ] `game-development/docs/11-network-authority-replication-and-latency.md`

### component·contract·release 경계

- [ ] `distributed-services/docs/01-boundaries-and-failure/02-service-boundaries-and-data-ownership.md`
- [ ] `distributed-services/docs/02-delivery-and-consistency/03-contracts-versioning-and-order.md`
- [ ] `distributed-services/docs/04-release-and-evidence/01-multi-repository-builds-and-release-manifests.md`

### 이유

TCP message ID를 먼저 정하기 전에 match state, fixed tick, client intent, server authority, Connection·Session·Player·Room의 owner와 component revision 조합을 알아야 한다.

---

## 10.2 `shared-protocol`

### 새로 읽기

없음.

### 누적 기반

- C++17/20 값·수명·RAII
- TCP framing과 incremental I/O
- authoritative command와 tick
- schema/version/order
- exact component revision 계약

Protocol numeric ID, frame header와 compatibility test는 정본 명세에 따라 구현한다.

---

## 10.3 `game-server` core/network/session/runtime

### 새로 읽기

- [ ] `cpp/docs/01-modern-cpp/05-errors-optional-variant-and-expected.md`
- [ ] `distributed-services/docs/03-resilience-and-load/02-backpressure-bulkheads-and-load-shedding.md`

### 이미 완료된 42 기반

- `cpp/docs/01-modern-cpp/01-program-build-cmake.md`
- `cpp/docs/01-modern-cpp/02-values-lifetimes-and-move.md`
- `cpp/docs/01-modern-cpp/03-raii-smart-pointers-and-rule-of-zero.md`
- `cpp/docs/01-modern-cpp/07-concurrency-time-and-filesystem.md`
- `cpp/docs/02-cpp98-systems/08-posix-sockets-and-event-loop.md`

### 이유

C++20 Result/Error contract, queue-full·stopped 같은 정상 거부, thread/callback 예외 경계가 필요하다. 연결별 output bound와 network→room bounded queue는 단순 최적화가 아니라 메모리 상한과 공정성 구조다.

---

## 10.4 `loadgen` bootstrap

### 새로 읽기

없음.

### 누적 기반

- shared protocol
- C++ socket/event loop
- command identity
- authoritative session flow

Loadgen은 game client가 아니라 protocol-aware workload generator라는 정본 범위를 따른다.

---

## 10.5 `game-server` storage/observability/control

### 저장 효과

- [ ] `database-systems/docs/03-transactions-and-recovery/01-transactions-isolation-and-locks.md`
- [ ] `distributed-services/docs/01-boundaries-and-failure/01-partial-failure-and-uncertain-outcomes.md`
- [ ] `distributed-services/docs/02-delivery-and-consistency/01-idempotency-and-single-effects.md`

### 운영 상태

- [ ] `distributed-services/docs/04-release-and-evidence/02-distributed-observability.md`

### 이유

terminal match result는 transaction과 idempotency key로 한 번만 남아야 한다. DB commit 뒤 응답 유실과 재시도를 구분해야 하며, health·status·metrics는 process 생존이 아니라 connection/session/room/queue/tick/DB 상태를 표현해야 한다.

---

## 10.6 `ops-dashboard`

### 새로 읽기

없음.

### 누적 기반

- 42 `ft_transcendence`의 React·Next.js·HTTP 상태
- 42 `portfolio`의 정적·운영 build 경험
- game-server operations API와 observability contract

Dashboard는 server state의 정본이 아니며 status 조회와 인증된 drain만 표현한다.

---

## 10.7 `loadgen` stress/failure completion

### 새로 읽기

- [ ] `distributed-services/docs/04-release-and-evidence/03-end-to-end-chaos-and-failure-evidence.md`

### 이유

slow receiver, disconnect/reconnect storm, DB degraded, queue saturation와 graceful drain은 단순 부하 발생기가 아니라 실패 전·중·후의 업무 상태를 판정하는 실험이어야 한다.

---

## 10.8 `game-server` performance/CI closure

### 새로 읽기

- [ ] `distributed-services/docs/04-release-and-evidence/04-performance-gates-and-claims.md`

### 이유

connection 수, active room, commands/sec, tick·command latency, queue depth, CPU, RSS와 오류 수를 같은 workload identity로 묶어야 한다. 한 번의 숫자를 운영 용량으로 과장하지 않는다.

---

## 10.9 `main` release manifest + integration gate

### 새로 읽기

없음.

### 누적 기반

- exact SHA manifest
- protocol compatibility
- macOS kqueue·Linux epoll
- DB·dashboard·loadgen 통합
- chaos와 performance evidence

이 단계에서 `v1.0.0`을 고정한다.

---

## 11. Game Server v1 신규 선행 문서 수

42 완료 이후 기준:

```text
Modern C++                  1
Game Development            4
Database Systems            1
Distributed Services        9
합계                        15
```

---

# Part III. 두 병렬 트랙의 중복 제거

Sportsbook과 Game Server v1에 공통으로 등장하는 문서는 다음 열 개다.

```text
database-systems/docs/03-transactions-and-recovery/01-transactions-isolation-and-locks.md

distributed-services/docs/01-boundaries-and-failure/01-partial-failure-and-uncertain-outcomes.md
distributed-services/docs/01-boundaries-and-failure/02-service-boundaries-and-data-ownership.md
distributed-services/docs/02-delivery-and-consistency/01-idempotency-and-single-effects.md
distributed-services/docs/02-delivery-and-consistency/03-contracts-versioning-and-order.md
distributed-services/docs/03-resilience-and-load/02-backpressure-bulkheads-and-load-shedding.md
distributed-services/docs/04-release-and-evidence/01-multi-repository-builds-and-release-manifests.md
distributed-services/docs/04-release-and-evidence/02-distributed-observability.md
distributed-services/docs/04-release-and-evidence/03-end-to-end-chaos-and-failure-evidence.md
distributed-services/docs/04-release-and-evidence/04-performance-gates-and-claims.md
```

따라서 실제 한 사람이 두 트랙을 함께 수행할 때의 신규 문서 수는 다음과 같다.

```text
Sportsbook                     33
Game Server v1                 15
병렬 트랙 간 중복             -10
42 이후 고유 신규 docs         38
```

전체 과정의 고유 선행 docs는 다음과 같다.

```text
42                            53
42 이후 두 병렬 트랙          38
전체 고유 docs                91
```

---

# 최종 실행 요약

```text
[42 완전 선형]
libft
→ get_next_line
→ ft_printf
→ push_swap
→ minitalk
→ philo
→ minishell
→ CPP0N
→ ft_container
→ miniRT
→ ft_irc
→ inception
→ ft_transcendence
→ portfolio

[42 이후 병렬]

A. Sportsbook
shared-protocol
→ wallet
→ risk
→ odds-feed
→ betting
→ settlement
→ admin-api
→ gateway
→ orchestration

B. Game Server v1
main bootstrap
→ shared-protocol
→ game-server core/network/session/runtime
→ loadgen bootstrap
→ game-server storage/observability/control
→ ops-dashboard
→ loadgen stress/failure
→ game-server performance/CI
→ main integration/release
→ v1.0.0
```
