# 완료 근거 루브릭

이 문서는 `distributed-systems` 브랜치의 다섯 소유 범위가 개념 설명, 단계 실습, capstone과 세 종료 능력에 실제로 연결됐는지 사람이 검토하는 기준입니다. 점수를 합산하거나 자동 검사 통과만으로 완료를 선언하는 표가 아닙니다.

## 판정 단위

다음 세 결과를 사용합니다.

- **충족**: 주장, 실행 입력, 관찰 결과, 비보장 범위를 함께 검토할 수 있고 정본 종료 능력에 중대한 공백이 없습니다.
- **보완 필요**: 일부 fixture나 public test는 통과하지만 소유 범위의 대표 실패, 누적 연결 또는 판단 evidence가 빠졌습니다.
- **범위 밖**: 정본 `excludes`에 속하며 이 브랜치의 완료 evidence로 요구하지 않습니다.

자동 결과가 없다고 곧바로 실패는 아닙니다. membership·sharding 설계처럼 사람 검토가 적합한 결과는 명시한 질문과 trace·state table로 판정합니다. 반대로 자동 검사가 통과해도 가정과 checker 범위가 비어 있으면 `충족`이 아닙니다.

## 세 종류의 검증을 구분합니다

### 1. 가이드 배포본

```sh
make prepare
make check
VERIFY_LOG=/tmp/guide-distributed-systems-verify.log make verify
```

문서, fixture, 예제, manifest와 canonical starter의 의도된 상태를 검사합니다. learner solution 완료 검사가 아닙니다.

### 2. Learner public contract

```sh
./scripts/new-capstone-workspace.sh
CAPSTONE_ROOT="$PWD/.workspace/replicated-kv" \
  python3 -m unittest discover -s capstone/tests -v
```

storage와 초기 protocol API의 공개 계약을 보여 줍니다. canonical starter는 제공된 storage 계약은 통과할 수 있지만 미완성 transition 관련 검사는 실패해야 합니다. public suite 전체 통과도 아래 fault matrix·history·membership·sharding evidence를 대신하지 않습니다.

### 3. 완료 dossier

learner가 작성한 추가 검사, trace, checker 결과와 설계 판단을 사람이 검토합니다. 이 세 번째 층까지 있어야 종료 능력을 판정합니다.

## 필수 dossier

권장 위치는 learner workspace 안의 `evidence/`입니다.

```text
.workspace/replicated-kv/evidence/
├── completion-dossier.md
├── run-report.json
├── manifest.json
├── public-tests.txt
├── schedules/
│   ├── normal.json
│   ├── partition-and-leader-change.json
│   ├── response-loss-and-retry.json
│   ├── crash-recovery.json
│   └── snapshot-boundary.json
├── traces/
│   ├── passing/
│   └── counterexamples/
├── invariant-results.json
├── history-results.json
└── limitations.md
```

membership·sharding 검토 원본은 starter가 제공한 `design/membership-review.md`와 `design/sharding-review.md`를 채웁니다. `run-report.json`과 manifest의 기계 판정 형식은 [`capstone/evidence`](../capstone/evidence/README.md)를 사용합니다.

파일 이름은 바꿀 수 있지만 다음 정보는 빠지면 안 됩니다.

- source tree·runtime·configuration·initial state·seed·schedule identity
- system model, supported failure와 명시적 non-goals
- sequential specification과 read protocol
- safety invariant와 조건부 liveness 가정
- 정상·경계·대표 실패 schedule의 입력과 결과
- 최소 한 개의 known violation, 축소한 counterexample와 수정 뒤 regression
- client history checker의 model, pending operation policy와 결과
- public test 외에 추가한 검사와 그 실패 검출 범위
- membership change와 sharding을 현재 state·snapshot·session에 적용한 검토
- 자동화가 증명하지 못한 범위와 사람 검토 답변

[trace schema](trace-schema.md)의 run identity와 event envelope를 사용합니다. 기존 fixture의 축약 schema를 재사용하면 dossier에 field 대응표를 둡니다.

## `owns` 추적표

| 정본 `owns` | 개념 설명 | 단계 실습·대표 실패 | capstone 누적 근거 | 종료 능력 |
|---|---|---|---|---|
| 분산 시간·순서·failure detector | `docs/01-model-and-time/` 전체, `03-consensus-and-membership/05-*` | causality trace의 concurrent pair·consistent cut, failure model의 timeout·partition, failure detector의 false suspicion·lease/fencing 반례 | Milestone 0 model, Milestone 1 election, Milestone 7 partition·leader-change schedule와 virtual-time trace | safety·liveness 설명; partition·leader 교체 재현 |
| 복제와 일관성 모델 | `docs/02-replication-and-consistency/` 전체 | consistency history의 stale·overlap·pending case, quorum register의 version conflict·partial write, anti-entropy의 sibling·tombstone resurrection | Milestone 2 log replication, 3 key-value/read, 5 retry, 7 history checker | safety·liveness 설명; 작은 저장소 구현·검증 |
| leader election·합의·replicated log | `docs/03-consensus-and-membership/01-*`~`03-*`, `05-*` | election trace의 split vote·stale candidate, log reconciliation의 conflicting suffix·current-term commit, client session의 response loss | Milestone 1–5·7의 term·vote·log·commit·apply·session evidence | 세 종료 능력 모두 |
| snapshot·membership change·sharding | `03-consensus-and-membership/04-*`, `docs/04-partitioning-and-atomicity/01-*` | client session의 unsafe snapshot, membership change의 disjoint quorum·removed-node write, shard rebalance의 stale router·dual authority | Milestone 6 snapshot 구현과 필수 `membership-review.md`·`sharding-review.md`; 실제 확장 코드는 선택 | safety·liveness 설명; 작은 저장소 구현·검증 |
| 결정적 장애 주입과 history 검증 | `docs/05-validation/` 전체 | linearizability의 legal·illegal·pending history, simulation plan의 source identity·fault evidence | Milestone 7 replayable schedule, every-step checker, 최소 counterexample, run manifest | 세 종료 능력 모두 |

문서 경로는 간결하게 표시했습니다. 실제 제출에서는 읽은 정의를 복사하지 말고 현재 구현의 state field, event와 checker에 연결합니다.

## 종료 능력 1: 복제 상태 기계의 safety·liveness를 설명합니다

### 필요한 evidence

- node·network·timer·storage·client를 포함한 system model
- crash-stop·crash-recovery, message fault와 storage atomicity 범위
- election safety, vote safety, log matching, commit monotonicity, apply bound, state-machine safety, client effect, snapshot equivalence의 명세
- 각 invariant를 검사하는 state projection과 실행 시점
- liveness에 필요한 majority, eventual delivery, timer fairness와 storage response 조건
- safety가 유지되지만 progress가 멈추는 schedule 하나
- safety 위반을 의도적으로 만드는 known-bad rule 또는 counterexample 하나

### 사람 검토 질문

- timeout 관찰을 crash 사실이나 lease 권한으로 바꾸지 않았습니까?
- `durable`, `replicated`, `committed`, `applied`, `client-visible` 시점을 구분합니까?
- bounded test의 결과를 unbounded proof로 표현하지 않았습니까?
- liveness bound에 필요한 schedule·fairness·time 조건이 기록됐습니까?

## 종료 능력 2: partition과 leader 교체를 재현합니다

### 필수 schedule

1. 안정 leader와 정상 write/read baseline
2. split vote 뒤 eventual delivery 조건에서 leader 선출
3. one-way partition으로 old leader belief와 majority authority가 갈리는 실행
4. majority replication 전 leader crash: 성공 응답 없음과 legal suffix
5. commit 뒤 response 전 leader crash: client `UNKNOWN`, 같은 request retry와 effect 1회
6. heal 뒤 stale term message 거절과 follower catch-up

각 run은 fault 요청이 아니라 실제 affected link·message ID, leader term, commit frontier, client result와 cleanup 결과를 남깁니다.

### 통과 근거

- 같은 source·config·seed·schedule을 재생하면 같은 canonical trace digest가 나옵니다.
- same-term dual leader, conflicting apply와 acknowledged write loss가 없습니다.
- leader가 바뀐 사실뿐 아니라 old/new term·log·commit·client history가 연결됩니다.
- 재현하지 못한 actual network·process failure는 simulator 결과와 구분합니다.

## 종료 능력 3: 작은 분산 저장소를 구현·검증합니다

### Core 구현

- term·vote·log의 crash-recovery state
- RequestVote와 AppendEntries의 validation·response 처리
- current-term commit와 ordered apply
- `put`, `get`, `compare_and_set` sequential specification
- 선택한 linearizable read protocol
- `(client_id, sequence, fingerprint)` retry·conflict 계약
- state machine·session·configuration을 포함한 snapshot과 compaction
- deterministic network, virtual time, crash·restart harness
- every-step invariant와 client history checker

### 필수 정상·경계·실패 evidence

| 구분 | 최소 사례 |
|---|---|
| 정상 | leader election, replicated put/get/CAS, snapshot 뒤 restart·read |
| 경계 | 최소 majority, duplicate·delayed response, sequence gap, snapshot index 직전·직후, slow follower |
| 실패 | stale candidate, conflicting suffix, response loss, repeated crash-restart, incomplete snapshot, unsupported/corrupt state 거절 |

starter에 구현이 존재하거나 public test가 통과한다는 사실보다, 실패 전후 바뀌면 안 되는 state와 최종 수렴 결과를 우선 검토합니다.

## Snapshot·membership·sharding 필수 누적 근거

실제 membership·sharding code는 선택 확장입니다. 하지만 이 브랜치가 두 영역을 소유하므로 capstone dossier에서는 다음 검토를 반드시 수행합니다.

### `membership-review.md`

- learner 추가와 snapshot/log catch-up 완료 조건
- 한 voter씩 바꾸는 방식 또는 joint consensus 중 선택한 protocol
- old/new quorum 교차를 current configuration state로 계산한 표
- configuration entry commit 전·후 leader crash와 restart trace
- session·snapshot에 configuration metadata를 포함하는 위치
- removed node가 stale leader·client write를 처리하지 못하게 하는 fencing
- 자동화하지 않은 transition과 남은 liveness 위험

### `sharding-review.md`

- 두 Raft group과 routing metadata의 정본 소유자
- range·epoch와 stale router 요청의 거절 규칙
- snapshot copy, delta catch-up, source fence, metadata cutover, target activation과 cleanup 순서
- cutover 직전 acknowledged write와 retry가 target에서 한 효과로 보이는 trace
- transfer coordinator crash와 duplicate transfer 재개 위치
- key당 write authority가 한 epoch에 하나임을 보이는 state table
- cross-shard atomic commit·query가 현재 구현에서 보장되는 범위와 비범위

두 review가 일반론만 반복하고 현재 capstone의 state·message·snapshot·session field에 연결되지 않으면 `보완 필요`입니다.

## Reference와 오답 거부

이 저장소는 완성된 Raft reference implementation을 제공하지 않습니다. 비교 근거는 다음 조합입니다.

- 논문·본문의 명세와 invariant
- deterministic fixture와 public API contract
- learner가 작성한 sequential oracle·history checker
- known-bad transition 또는 mutation이 만들어 내는 counterexample
- 수정 전 실패와 수정 후 같은 schedule의 regression 결과

public test를 수정해 통과시키거나 expected result를 입력 fixture에 숨겨 그대로 반환한 결과는 완료 evidence가 아닙니다. 최소 한 개의 plausible wrong rule이 checker에 의해 의미 있는 assertion으로 거부되는지 확인합니다.

## 다른 언어 구현

C·C++·Java 구현은 허용되지만 root Python 검증과 public Python test의 자동 통과를 대체하지 않습니다. dossier에 다음을 추가합니다.

- Python type·API와 port의 대응표
- fixture loader와 trace writer 실행 명령
- 같은 schedule에 대한 cross-language observable result 또는 차이 설명
- memory·thread·serialization처럼 해당 runtime에서 새로 생긴 failure 경계
- sanitizer·race detector 등 사용한 검사와 실행하지 못한 선택 검사

동등성은 소스 구조가 아니라 public state, invariant, history와 failure evidence로 검토합니다.

## 자동 검증의 한계

다음은 자동 통과만으로 증명되지 않습니다.

- 모든 가능한 event ordering의 safety
- unbounded liveness와 실제 recovery time
- torn write·data corruption·filesystem flush 의미
- 실제 TCP partition, clock drift와 scheduler pause
- membership·sharding 설계의 전체 correctness
- production performance·availability·upgrade compatibility

실행하지 않은 필수 검사는 `PASS`가 아니라 `UNVERIFIED`로 기록합니다. 실제 adapter가 없으면 deterministic 대체 경로와 그 한계를 설명합니다.

## 최종 사람 검토

다음 질문에 모두 근거를 가리킬 수 있어야 합니다.

1. 다섯 `owns` 각각의 개념 문서, 단계 실습, 대표 실패와 capstone evidence는 어디입니까?
2. 세 종료 능력을 판단하는 trace·state·history·설명은 무엇입니까?
3. canonical starter와 learner implementation, public test와 learner 추가 검사를 구분했습니까?
4. partition과 leader change를 동일한 identity의 schedule로 재생할 수 있습니까?
5. safety 위반이 없다는 주장과 liveness가 진행한다는 조건을 분리했습니까?
6. snapshot 뒤 session·configuration 의미와 shard 이동 authority가 보존됩니까?
7. 알려진 오답 또는 과거 counterexample가 regression에서 거부됩니까?
8. 실행하지 않은 환경·failure·성능 검사를 성공으로 표시하지 않았습니까?
9. learner source, trace와 외부 resource의 보존·cleanup 범위가 명확합니까?
10. 정본 `excludes`를 완료 주장에 포함하거나 인접 브랜치 원리를 중복하지 않았습니까?

중대한 공백이 없을 때만 세 종료 능력을 `충족`으로 판정합니다. 이는 production 전문성, 특정 제품 운영 경험 또는 모든 분산 실행의 correctness proof를 의미하지 않습니다.
