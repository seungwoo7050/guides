# 기존 구현과 신규 Game Server를 위한 실무형 학습·전이·검증 운영 체계

_42·Sportsbook의 기존 구현 재활용과 `game-server` 신규 구현을 하나의 evidence 체계로 관리하는 실행 명세_

> 목표: 이미 구현한 프로젝트를 이해·수정할 수 있고, 새 프로젝트를 빈 저장소에서 설계·구현·진화시킬 수 있는지를 분리해 검증한다.
>
> 범위: 42의 15개 project branch, Sportsbook의 9개 project branch, 신규 `game-server` 1개.
>
> guide 정책: 병렬 학습 트랙 문서가 지정한 **구현 필수 branch/docs만** 검수 대상으로 사용한다. 일반 CS branch를 추가 이수했다는 사실은 완료 근거로 사용하지 않는다. 일반 CS 능력은 project의 source, failure, benchmark와 구두 방어에서 판정한다.
>
> Game Server 구현 에이전트는 devlog를 작성하지 않는다.

작성 기준일: 2026-08-12

---

# 1. 운영 원칙

## 1.1 두 종류의 학습을 분리한다

### 기존 42·Sportsbook

이미 완성된 구현을 보존한 채 다음을 수행한다.

```text
baseline 고정
→ architecture 복원
→ devlog와 source·test·commit 대조
→ 보이지 않는 change quest
→ 회귀·failure 검증
→ evidence 공개
```

### 신규 Game Server

빈 저장소에서 다음을 수행한다.

```text
vision·roadmap·v1 상세 설계
→ 실제 순차 commit
→ v1 release
→ 측정과 실패에 따라 v2~v7 상세화
→ release별 evidence
→ 사용자가 devlog 직접 작성
```

기존 project에는 “새 요구에 안전하게 대응하는 능력”을 묻고, Game Server에는 “빈 상태에서 architecture를 만들고 장기간 진화시키는 능력”을 묻는다.

## 1.2 검증의 여섯 층

| 층 | 활동 | 검증하는 능력 | 단독으로 부족한 이유 |
|---|---|---|---|
| 문서 정확성 | guides/docs를 정본과 project version으로 검수 | 기술 설명의 정확성 | 실제 코드 변경 능력을 증명하지 못함 |
| 복원 | source·test·commit에서 architecture와 실패 경로 복원 | 기존 시스템 이해 | 새 요구 대응을 증명하지 못함 |
| 전이 | 기존 project에 보이지 않는 change quest 수행 | 영향 분석, 불변식 유지, 회귀 방지 | 새 project 설계 능력과 다름 |
| 신규 구축 | Game Server를 빈 저장소에서 v1부터 구현 | architecture와 순차 개발 | 운영·확장 능력을 아직 증명하지 못함 |
| 누적 진화 | Game Server v2~v7을 실제 문제에 따라 확장 | 기술 선택의 근거와 장기 변화 관리 | evidence가 없으면 서술에 그침 |
| 증거·방어 | exact SHA, test, fault, benchmark, 구두 방어 | 제3자 재현성과 책임 | 결과만 있고 reasoning이 없으면 재현이 어려움 |

## 1.3 변경하지 않는 원칙

1. 42·Sportsbook 원본 branch의 기준 commit을 tag로 고정한다.
2. guide 작성 agent와 검수 agent를 분리한다.
3. framework·standard·database·container version을 먼저 고정한다.
4. source와 test가 뒷받침하지 않는 강한 주장은 낮추거나 삭제한다.
5. 정상 경로보다 failure 후 상태와 owner를 우선 확인한다.
6. tone 교정은 기술 검수와 실행 검증 뒤에 한다.
7. Game Server는 최종 코드를 먼저 만들고 commit을 사후 분할하지 않는다.
8. Game Server의 v2~v7은 직전 release의 실제 결과 없이 세부 설계를 확정하지 않는다.
9. agent가 만든 결과라도 사용자가 diff, invariant, test와 한계를 방어하지 못하면 완료가 아니다.
10. devlog는 사용자가 작성한 내용만 인정한다.

## 1.4 AI 사용 모드

| 모드 | AI 허용 범위 | 목적 | 판정 |
|---|---|---|---|
| 학습 | 설명, 정본 탐색, 반례·test 후보, 코드 review | 이해와 오류 탐색 | 능력 시험 아님 |
| 전이 시험 | 정본 탐색과 build 도구만 허용, 구현 patch 금지 | 독립 변경 능력 | 주 평가 |
| AI 보조 구현 | 구현 agent 사용 가능, 사용자가 요구·diff·test 전부 승인 | agent 감독 능력 | 보조 평가 |
| 신규 프로젝트 구현 | 승인된 설계에 따라 Game Server 순차 구현 | 실제 project 생성 | release evidence로 판정 |

Game Server에서는 구현 agent를 사용할 수 있지만 다음은 허용하지 않는다.

- devlog 작성
- synthetic history
- benchmark 수치 조작
- 실패한 검증 숨김
- 요구되지 않은 technology를 이력용으로 추가
- 42 source 복사

---

# 2. 저장소·branch·tag 구조

## 2.1 기존 project

| 종류 | 용도 | 저장 내용 |
|---|---|---|
| Canonical project branch | 현재 정본 | source, test, user-authored devlog |
| Baseline tag | 학습 시작 전 상태 | exact SHA |
| Study quest branch | 전이 검증 | 요구 변경, test, evidence |
| Evidence directory | 실행 결과 | manifest, report, trace, raw data |

```text
BASE_SHA=<검수 시작 commit>

git tag study-baseline-<date> "$BASE_SHA"

git worktree add \
  ../worktrees/<project>-<quest> \
  -b study/<project>/<quest> \
  "$BASE_SHA"
```

study branch는 기본적으로 canonical branch에 merge하지 않는다. 실제 product contract를 개선하고 회귀·migration·문서가 완성된 경우에만 별도 PR로 검토한다.

## 2.2 Game Server

권장 흐름:

```text
main
├── actual sequential commits
├── tag v1.0.0
├── actual sequential commits
├── tag v2.0.0
├── ...
└── tag v7.0.0
```

release 직전 review가 필요하면 짧은 `release/vN` branch를 사용할 수 있지만 최종 history를 인위적으로 다시 쓰지 않는다.

Game Server는 baseline tag가 없다. 빈 repository의 첫 design commit이 출발점이다.

## 2.3 중앙 저장 구조

```text
learning-system/
├── catalog/
│   ├── projects.yml
│   ├── releases.yml
│   └── guides.yml
│
├── authorities/
│   └── <guide>/
│       └── SOURCES.yml
│
├── reviews/
│   └── <guide>/
│       ├── CLAIMS.csv
│       ├── REVIEW.md
│       └── CHANGELOG.md
│
├── quests/
│   └── <project>/<quest-id>/
│       ├── SPEC.md
│       ├── IMPACT.md
│       ├── INVARIANTS.md
│       ├── TEST_PLAN.md
│       ├── EVIDENCE.md
│       └── RETROSPECTIVE.md
│
├── releases/
│   └── game-server/
│       ├── v1/
│       ├── v2/
│       └── ... v7/
│
├── evidence/
│   ├── <existing-project>/<commit-sha>/
│   └── game-server/<version>/<commit-sha>/
│
└── portfolio/
    ├── index.md
    └── case-studies/
```

## 2.4 공개 산출물

| 산출물 | 작성 주체 | 입증 내용 |
|---|---|---|
| 보정된 guides/docs | agent 초안 + 사용자 승인 | 기술 설명을 정본과 구현에 맞게 교정 |
| 기존 project devlog | 사용자 | 실제 과거 개발 과정의 복원과 설명 |
| Game Server devlog | 사용자 | 새 project의 실제 형성 과정 |
| Study quest | 사용자 또는 agent 보조 | 기존 시스템의 새 요구 대응 |
| Game Server release dossier | 구현 agent + 사용자 승인 | 신규 architecture의 구현·실패·진화 |
| Evidence bundle | 자동화 + 사용자 검토 | exact source에서 재현 가능 |
| Case study | 사용자 | 문제·결정·증거·한계를 짧게 전달 |

---

# 3. guides/docs 검수 체계

## 3.1 검수 범위

검수 대상은 병렬 학습 트랙 문서가 각 project 앞에 배치한 branch/docs로 제한한다.

Game Server에서 직접 추가되는 검수 단위는 다음 흐름을 따른다.

```text
v1:
game loop
command contract
gameplay rule
server-side movement
replay/determinism
network authority
testing/telemetry

v3:
performance budget과 profiling

v7:
Kubernetes workload
network·storage·scheduling
```

docs 경로의 정본은 `parallel_learning_tracks_42_sportsbook_game_server_strict.md`와 `game_server_agent_blueprint.md`가 소유한다. 이 문서에서 전체 경로 목록을 다시 중복 관리하지 않는다.

## 3.2 정본 우선순위

| 순위 | 근거 | 사용 원칙 |
|---:|---|---|
| 1 | 언어·protocol·platform standard | 정의와 API 의미의 최상위 기준 |
| 2 | project가 사용하는 exact version의 공식 문서 | framework·DB·runtime·container 동작 |
| 3 | 해당 version의 source·official test·release note | 문서가 모호하거나 구현 차이가 있을 때 |
| 4 | 현재 project source·test·config | project가 실제로 보장하는 계약 |
| 5 | 최소 재현, compiler, sanitizer, browser, DB, container 실행 | 문서 해석과 관찰 차이 확인 |
| 6 | 2차 자료 | 탐색 보조이며 단독 승인 근거가 아님 |

## 3.3 검수 순서

1. 적용 version과 project SHA를 고정한다.
2. docs 문장을 claim 단위로 분리한다.
3. claim을 정의, API, 구현, 성능, 보안, 설계 권고로 분류한다.
4. 정본으로 정확성과 조건을 확인한다.
5. project source·test와 일치하는지 확인한다.
6. 부분 성공, timeout, duplicate, stale state, shutdown, overflow와 compatibility 누락을 찾는다.
7. 기존 test가 잘못된 구현을 실제로 거부하는지 확인한다.
8. docs 구조를 state, owner, transition, failure, evidence 순서로 정리한다.
9. 마지막에 문체를 보정한다.
10. 남은 불확실성을 숨기지 않는다.

## 3.4 Claim ledger

| field | 내용 |
|---|---|
| Location | branch, docs path, heading, line |
| Claim | 검수 대상 주장 |
| Kind | standard / API / implementation / performance / security / design |
| Version | language, framework, DB, OS, image |
| Authority | 공식 문서·source·test |
| Verdict | accurate / conditional / overstated / wrong / unverified / out-of-scope |
| Severity | Critical / High / Medium / Low |
| Reproduction | 필요한 실행 또는 current test |
| Patch | 수정 commit |
| Human sign-off | 승인자, 날짜, 남은 한계 |

## 3.5 사람 직접 검수 대상

다음은 agent 결과만으로 승인하지 않는다.

- C/C++ lifetime과 undefined behavior
- signal safety
- lock order와 memory visibility
- authentication·authorization
- transaction과 ledger invariant
- Redis atomicity·expiry
- Kafka ack·ordering·duplicate
- graceful shutdown과 data loss
- performance 상한
- Kubernetes readiness와 stateful termination
- “exactly-once”, “무손실”, “thread-safe”, “production-ready” 표현

---

# 4. project 검증 방식

## 4.1 기존 project change quest

각 기존 project는 다음 순서로 검증한다.

```text
cold architecture reconstruction
→ baseline test
→ hidden requirement
→ impact map
→ invariant
→ failure matrix
→ implementation
→ full regression
→ new normal/boundary/failure test
→ evidence
→ oral defense
→ delayed variant
```

## 4.2 Game Server release

각 release는 다음 순서로 검증한다.

```text
직전 release evidence
→ 새 문제 재현
→ entry criteria
→ detailed design
→ actual commits
→ local platform test
→ cross-platform test
→ failure test
→ benchmark/profile
→ limitations
→ release tag
```

v1은 빈 저장소에서 시작하므로 먼저 design을 검증한다.

```text
vision
→ roadmap
→ v1 architecture
→ state ownership
→ protocol
→ thread model
→ persistence
→ web control plane
→ failure model
→ commit line
```

## 4.3 project tier

| Tier | 대상 | 최소 검증 |
|---|---|---|
| Tier 1 | 기초 library | public contract, boundary, sanitizer |
| Tier 2 | parser, concurrency, network, DB service | 기능 + failure state + resource/retry |
| Tier 3 | ft_transcendence, Sportsbook, Game Server v1~v6 | end-to-end, restart, fault, observability |
| Tier 4 | Game Server v7 | rollout, Pod loss, drain, capacity, exact image/config |

---

# 5. Game Server release 검증 명세

상세 architecture는 `game_server_agent_blueprint.md`가 소유한다. 여기서는 release gate와 evidence만 고정한다.

## 5.1 v1 — Stateful authoritative server

### 핵심 불변식

- `Connection != Session != Player != Room`
- room mutable state의 writer는 하나
- TCP frame과 read 호출을 동일시하지 않음
- pending output은 bounded
- event thread는 blocking DB query를 실행하지 않음
- match result retry가 double effect를 만들지 않음
- web control API는 read-only
- dashboard는 game client가 아님
- shutdown 순서가 명시됨

### 필수 evidence

- macOS kqueue process test
- Linux epoll process test
- fragmented/coalesced/malformed frame
- partial write와 slow reader
- disconnect/reconnect/stale generation
- fixed-tick replay
- room owner race 검사
- PostgreSQL retry·rollback
- HTTP health·metrics·admin snapshot
- dashboard build와 state display
- load baseline
- graceful drain
- sanitizer
- exact CI run

## 5.2 v2 — UDP realtime path

### 핵심 불변식

- authoritative writer는 server
- UDP peer가 current session generation에 결합
- duplicate와 stale packet 거절
- arrival order와 simulation order 분리
- snapshot sequence와 server tick 분리
- prediction-supporting protocol은 제공하지만 client prediction은 구현하지 않음

### 필수 evidence

- loss profile
- duplication
- reordering
- jitter
- stale peer
- bounded packet
- bandwidth
- TCP control path regression

## 5.3 v3 — performance와 concurrency

### 핵심 불변식

- optimization 전후 final state 동일
- 동일 workload
- raw profile 보존
- 평균만으로 결론 내리지 않음
- lock-free는 필요성이 증명될 때만 사용

### 필수 evidence

- p50/p95/p99
- CPU
- memory
- queue depth
- profile capture
- bottleneck hypothesis
- before/after
- repeated run
- retain/revert decision

## 5.4 v4 — Redis multi-instance

### 핵심 불변식

- room simulation은 owning game-server memory가 소유
- PostgreSQL은 durable state
- Redis는 ephemeral directory와 coordination
- lease와 generation으로 stale owner를 fence
- Redis outage가 silent corruption으로 이어지지 않음

### 필수 evidence

- 2개 이상 instance
- presence/session/room location
- stale lease
- duplicate registration
- wrong-instance reconnect
- Redis unavailable
- recovery 뒤 stale data
- authoritative state 비이전 확인

## 5.5 v5 — service extraction

### 핵심 불변식

- 분리 전 module boundary가 먼저 존재
- source of truth가 service마다 명확
- network timeout과 business rejection 분리
- retry가 duplicate effect를 만들지 않음
- 모든 module을 service로 분리하지 않음

### 필수 evidence

- extraction decision record
- 분리 전후 contract
- dependency failure
- process restart
- compatibility
- correlation identity
- 분리하지 않은 경계와 이유

## 5.6 v6 — Kafka event path

### 핵심 불변식

- realtime tick critical path에 Kafka 없음
- PostgreSQL effect와 publish 사이 partial success 복구
- at-least-once delivery에서 single business effect
- partition key와 ordering scope 명시
- late/duplicate event를 처리

### 필수 evidence

- outbox
- producer restart
- consumer restart
- duplicate
- late event
- lag
- replay
- poison event
- schema compatibility
- end-to-end correlation

## 5.7 v7 — Kubernetes

### 핵심 불변식

- liveness와 readiness 의미 분리
- terminating Pod에 새 match를 할당하지 않음
- connection·room drain 순서가 있음
- image·config identity를 추적
- resource exhaustion을 silent success로 처리하지 않음

### 필수 evidence

- reproducible cluster apply
- startup/readiness/liveness
- rolling update
- Pod loss
- termination grace
- drain
- scale-out
- resource requests/limits
- capacity result
- exact image digest
- known stateful limitation

## 5.8 Game Server agent 제한

agent는 다음을 만들 수 있다.

- source
- test
- build
- migrations
- protocol docs
- architecture docs
- ADR
- runbook
- benchmark reproduction
- release evidence
- limitations

agent는 다음을 만들 수 없다.

- devlog
- 사용자 회고
- synthetic commit history
- 허위 benchmark
- 실패를 숨긴 완료 보고

---

# 6. 기존 42·Sportsbook change quest

아래 과제는 기존 project 전체 재구현을 대신하는 대표 전이 과제다. 실제 시험에서는 같은 난이도의 variant를 사용한다.

## 6.1 C 트랙

| project | 변경 요구 | 핵심 불변식 | 필수 증거 |
|---|---|---|---|
| `c/libft` | overflow-safe `ft_reallocarray` 추가 | 곱 overflow, 0-size, 원본 소유권, allocation failure | public header, archive consumer, failure injection, ASan/UBSan |
| `c/get_next_line` | reader별 max line length와 `BLR_LIMIT` 상태 추가 | remainder 보존, retry 가능 상태, fd ownership | 경계 길이, partial read, EAGAIN/EINTR, reset/destroy |
| `c/ft_printf` | `*` width·precision 지원 | negative width, `va_list`, parse/length error 전 출력 금지 | reference 비교, overflow, short write, EINTR/EPIPE |
| `c/minitalk` | ACK loss retry와 sequence dedup | 출력 side effect 중복 방지, session owner, timeout | ACK drop, duplicate bit, stale response |
| `c/minishell` | optional pipefail 정책 | 기본 동작 호환, pipeline status, signal mapping | builtin, external, signal, multi-stage pipeline |
| `c/philo` | polling을 timed condition wakeup으로 교체 | death 판정, lock order, join/destroy | TSan, stale death candidate, shutdown failure |
| `c/push_swap` | front 이동을 circular buffer로 교체 | 11 command 의미, rank, checker independence | property, replay, move count와 physical shift 비교 |

## 6.2 C++ 트랙

| project | 변경 요구 | 핵심 불변식 | 필수 증거 |
|---|---|---|---|
| `c++/CPP0N` | formatter plugin과 factory syntax 추가 | clone ownership, virtual destruction, strong guarantee | copy failure, invalid spec, old pipeline |
| `c++/ft_container` | RB tree 기반 `ft::set` 추가 | const key, iterator stability, comparator/allocator, tree invariant | `std::set` 대조, randomized, exception, external consumer |
| `c++/miniRT` | triangle 추가 | parser atomicity, normal/intersection, AABB/BVH, deterministic render | linear/BVH equivalence, image checksum, worker equivalence |
| `c++/ft_irc` | WHO command 추가 | registration, channel visibility, framing, output bound | real TCP, partial send, rate limit, disconnect safety |

## 6.3 Web 트랙

| project | 변경 요구 | 핵심 불변식 | 필수 증거 |
|---|---|---|---|
| `web/WEB0N` | credentialed CORS preflight scenario | origin, cookie/SameSite, preflight cache, abort/late commit | Chromium, Firefox, WebKit |
| `web/portfolio` | URL-owned locale switching | content schema, server/client state, focus/history, build mode | accessibility, visual regression, production smoke |
| `web/inception` | WordPress·MariaDB upgrade와 rollback | backup, immutable input, volume migration, restore | fresh volume, forced stop, backup restore, secret leak |
| `web/ft_transcendence` | read-only spectator role | authorization, authoritative snapshot, reconnect, input rejection | API, WebSocket, browser E2E, multi-session isolation |

## 6.4 Sportsbook 트랙

| project | 변경 요구 | 핵심 불변식 | 필수 증거 |
|---|---|---|---|
| `shared-protocol` | optional `correlationId` 호환 추가 | Avro compatibility, generated model, null/default | old/new schema combinations, producer/consumer contract |
| `wallet-service` | transfer와 reversal | double-entry, currency, row-lock order, idempotency, reversal uniqueness | concurrent transfer, same key repeat, reconciliation |
| `risk-service` | Redis key에 currency dimension | legacy compatibility, Lua atomic keys, replay/expiry | migration, capacity race, currency isolation |
| `odds-feed-service` | durable checkpoint/retry | Kafka ack와 Redis projection partial success, duplicate convergence | Kafka/Redis individual failure, restart, poison/late future |
| `betting-service` | odds Redis failure도 recoverable intent로 저장 | fingerprint, pending state, restart recovery, no duplicate effect | outage, same-key race, downstream non-call |
| `settlement-service` | lifecycle cancellation으로 late pending bet 자동 void | event order, immutable plan, wallet idempotency | race, restart, duplicate lifecycle, terminal conflict |
| `gateway` | canonical UUID subject와 downstream timeout | trusted header, 401/403/502/504, body/trace | malformed JWT, slow dependency, Redis fail-open regression |
| `admin-api` | issuer·audience·sub·exp와 proxy trust 강화 | authentication vs role vs IP, forwarded trust, audit | claim matrix, spoofed XFF, delegation/audit |
| `orchestration` | 9 branch SHA·image digest·topic·config manifest | artifact reproducibility, no partial generation, cold E2E trace | fresh bootstrap, manifest verification, failure snapshot |

## 6.5 merge 판단

- 학습 전용 hook과 artificial API는 canonical branch에 합치지 않는다.
- 실제 contract 개선, migration, docs, full regression이 완성된 변경만 PR로 검토한다.
- merge하지 않아도 study branch와 exact diff는 evidence로 보존한다.

---

# 7. 실제 해결 능력 평가

## 7.1 공통 수행 순서

```text
요구 재서술
→ ambiguity와 non-scope
→ owner와 impact
→ invariant
→ failure·race·compatibility matrix
→ implementation plan
→ code change
→ full regression
→ new test
→ fault injection
→ evidence
→ oral defense
→ delayed variant
```

## 7.2 평가 축

| 축 | 점수 | 관찰 항목 |
|---|---:|---|
| 요구 해석 | 15 | ambiguity, non-scope, acceptance |
| 영향·불변식 | 20 | owner, transition, compatibility, failure |
| test 설계 | 20 | regression, boundary, race, known-bad |
| 구현 | 20 | change size, resource, transaction, shutdown |
| debug·evidence | 15 | first failure localization, reproducibility |
| docs·한계 | 10 | guarantee와 non-guarantee 구분 |

통과:

- 75점 이상
- Critical regression 없음
- hidden requirement 만족
- evidence 재현 가능

강한 통과:

- 85점 이상
- delayed variant 80점 이상
- 구두 방어에서 대안과 포기한 보장을 설명

점수와 무관한 실패:

- data loss 은폐
- security bypass
- undefined behavior
- ledger invariant 파괴
- synthetic evidence
- benchmark 조작
- baseline regression 숨김

## 7.3 Game Server 추가 평가

Game Server는 다음을 별도로 본다.

| 항목 | 질문 |
|---|---|
| 순차성 | 실제 문제와 commit이 시간 순서로 대응하는가 |
| architecture | state owner와 process/thread 경계가 명확한가 |
| evolution | technology가 이력용이 아니라 문제 해결로 도입됐는가 |
| portability | kqueue와 epoll 상위 contract가 같은가 |
| performance | measurement와 correctness가 함께 있는가 |
| distribution | Redis/Kafka/service boundary의 source of truth가 명확한가 |
| orchestration | stateful drain과 Pod loss를 다루는가 |
| 감독 | 사용자가 agent 변경을 코드로 방어하는가 |

---

# 8. Evidence bundle

## 8.1 기존 project

```text
CASE_STUDY.md
ARCHITECTURE.md
REPRODUCE.md
LIMITATIONS.md
manifest.json
verify.log
test reports
fault evidence
quest diff
exact CI link
user-authored devlog link
```

## 8.2 Game Server release

```text
release/<version>/
├── DESIGN.md
├── INVARIANTS.md
├── TEST_MATRIX.md
├── FAILURE_MATRIX.md
├── BENCHMARK.md
├── LIMITATIONS.md
├── manifest.json
├── raw/
├── reports/
└── ci-links.md
```

`manifest.json` 최소 field:

```json
{
  "repository": "game-server",
  "version": "v1.0.0",
  "commit": "<exact-sha>",
  "toolchains": {
    "macos": "<clang-version>",
    "linux": "<gcc-or-clang-version>"
  },
  "dependencies": {
    "postgres": "<image-digest>"
  },
  "commands": {
    "macos": ["<build>", "<test>"],
    "linux": ["<build>", "<test>"]
  },
  "reports": ["<paths>"],
  "limitations": "LIMITATIONS.md"
}
```

v4 이후에는 Redis, v6 이후에는 Kafka, v7에는 모든 image digest와 Kubernetes manifest hash를 추가한다.

## 8.3 성능 evidence

반드시 포함:

- hardware 또는 VM profile
- OS
- compiler
- build type
- source SHA
- configuration
- workload
- seed
- warmup
- repetitions
- raw samples
- percentile calculation
- before/after
- result checksum 또는 state equivalence
- 측정이 증명하지 않는 범위

---

# 9. 대표작 선별

25개 project를 같은 비중으로 노출하지 않는다.

| 평가 축 | 가중치 |
|---|---:|
| 지원 직무 관련성 | 25 |
| 기술 깊이 | 20 |
| 검증 근거 | 20 |
| 종단 소유 | 15 |
| 재현·설명 | 10 |
| 다른 대표작과의 차별성 | 10 |

## 9.1 직무별 첫 화면

| 지원 방향 | 첫 화면 대표작 | 보조 깊이 |
|---|---|---|
| Game Server·C++ Server | Game Server, ft_irc, philo, miniRT | ft_container, minishell, Game Server release evidence |
| Java/Spring·Sportsbook | Sportsbook system case study, Game Server v4~v6, ft_transcendence | wallet, risk, betting, settlement, orchestration |
| C/C++ Systems | Game Server v1~v3, ft_irc, miniRT, ft_container | philo, minishell, push_swap |
| Full-stack/Web | ft_transcendence, portfolio, Game Server admin web, Sportsbook gateway | WEB0N, web runtime evidence |
| Infra/Platform | inception, Sportsbook orchestration, Game Server v7 | image, rollout, drain, recovery evidence |

Game Server는 지원 방향에 따라 다른 release를 앞세운다.

```text
C++ server     -> v1~v3
distributed    -> v4~v6
platform       -> v7
```

## 9.2 공개 정보 순서

1. 30초 요약
2. architecture
3. 핵심 결정
4. failure
5. exact evidence
6. 현재 한계
7. source와 user-authored devlog
8. 관련 guide review

---

# 10. 종단 완료 조건

## 10.1 guide docs 완료

- 적용 version과 정본이 고정됨
- Critical·High claim 인간 승인
- project source·test와 불일치 해소 또는 명시
- unsupported strong claim 제거
- failure·boundary 누락 보완
- 링크·build·test가 current project와 일치
- docs change가 claim ledger와 연결됨

## 10.2 기존 project 완료

- devlog 없이 architecture를 복원
- user-authored devlog의 각 주요 주장에 source·test·commit 연결
- 대표 failure 재현
- hidden change quest 통과
- full regression
- exact evidence
- oral defense
- delayed variant

## 10.3 Game Server v1 완료

- approved blueprint와 actual code 일치
- macOS/Linux network backend
- state ownership
- protocol
- persistence
- web control plane
- load/failure
- profile
- actual commit history
- v1 tag
- limitations
- 사용자가 code defense 수행
- agent 작성 devlog 없음

## 10.4 Game Server 전체 완료

- v1이 독립 완성형
- v2~v7이 각자 진입 문제와 evidence 보유
- 직전 contract 전체 회귀
- unnecessary technology를 도입하지 않음
- lock-free 도입 또는 기각 근거
- Redis/Kafka/Kubernetes source of truth와 failure 경계
- exact release history
- 사용자가 release별 devlog 직접 작성
- 직무별 case study 완성

## 10.5 전체 과정 완료

- 24개 기존 project는 복원과 change quest로 검증
- Game Server는 신규 구축과 누적 진화로 검증
- guide docs는 project 구현을 위한 최소 선행으로만 사용
- 일반 CS 능력은 project evidence로 검증
- 대표작을 직무별로 압축
- 모든 공개 주장은 exact source와 실행 근거를 가짐

---

# 11. 운영 checklist

## 시작 전

- project inventory와 branch 확인
- exact SHA 기록
- guide docs 범위 확인
- toolchain·dependency version 고정
- Game Server blueprint 승인

## 기존 project마다

- baseline tag
- architecture reconstruction
- devlog 대조
- change quest
- full regression
- fault
- evidence
- delayed variant

## Game Server release마다

- entry criteria
- detailed design
- actual commit plan
- implementation
- cross-platform test
- fault
- benchmark
- limitations
- tag
- user devlog

## 공개 전

- exact link
- no floating badge-only evidence
- no unsupported strong claim
- no synthetic history
- no hidden failed test
- no agent-written devlog
