# 분산 시스템과 복제 상태 기계

시간·순서·장애 모델부터 복제·일관성·합의·sharding·재구성까지, 분산 저장 시스템의 핵심을 문서·결정적 trace·작은 구현으로 학습하고 검증하는 가이드입니다. 제품 이름을 외우는 대신 어떤 실행을 허용하고 어떤 상태를 금지하는지 먼저 명세합니다.

다음 질문을 끝까지 추적합니다.

- 공통 wall clock이 없을 때 사건의 순서와 concurrency를 어떻게 표현합니까?
- timeout과 crash를 구분할 수 없는 조건에서 safety와 liveness를 어떻게 나눕니까?
- replica가 다른 상태를 가질 때 consistency와 quorum은 무엇을 보장하고 무엇을 보장하지 않습니까?
- leader가 바뀌고 message가 재정렬돼도 committed log가 보존되는 이유는 무엇입니까?
- snapshot·membership change·shard 이동 중 어떤 metadata와 authority를 함께 옮겨야 합니까?
- 구현 주장을 결정적 fault schedule, invariant와 client history로 어떻게 반증 가능하게 만듭니까?

## 대상 독자와 목표 결과

다음 독자에게 적합합니다.

- 데이터베이스·coordination system의 replication 또는 storage 모듈에 진입하려는 개발자
- Raft를 사용했지만 term·commit·snapshot·membership 불변식을 구현 수준에서 검토하기 어려운 개발자
- 분산 장애 테스트를 process kill과 최종 값 비교에서 재현 가능한 schedule·history 검사로 확장하려는 개발자

가이드를 마치면 작은 복제 key-value store와 그 설계·trace·검증 dossier를 남깁니다. production consensus library, 운영 클러스터 또는 특정 cloud 제품을 만드는 과정은 아닙니다.

## 정본 카탈로그 계약

이 브랜치의 ID는 `distributed-systems`, 종류는 `specialization`입니다. 최신 `main`이 승인한 소유 범위는 다음 다섯 항목입니다.

1. 분산 시간·순서·failure detector
2. 복제와 일관성 모델
3. leader election·합의·replicated log
4. snapshot·membership change·sharding
5. 결정적 장애 주입과 history 검증

다음 범위는 소유하지 않습니다.

- 서비스 업무 saga 재교육: [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)
- DBMS 단일 노드 내부 전체: [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- Kubernetes 운영: [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- 특정 클라우드 제품: 공급자 공식 자료와 해당 운영 경로

TCP·라우팅·partition의 네트워크 증거는 [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), process·동시성·영속화 경계는 [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)가 먼저 소유합니다. 이 가이드는 그 전제를 복제 상태 기계의 고유한 상태·실패 모델에 적용합니다.

## 선행·권장·연결 관계

정본 관계는 다음과 같습니다.

| 관계 | 브랜치 |
|---|---|
| `requires` | `operating-systems`, `computer-networks`, `database-systems` |
| `recommends` | `algorithms`, `distributed-services` |
| `connects` | `data-engineering`, `platform-engineering` |
| `continues_to` | 없음 |

`continues_to`가 비어 있다는 것은 학습이 끝난다는 뜻이 아니라 카탈로그가 이 specialization 뒤의 단일 필수 후속 브랜치를 강제하지 않는다는 뜻입니다. 목적에 따라 데이터 처리의 분산 상태를 다루는 `data-engineering` 또는 여러 팀의 운영 경계를 다루는 `platform-engineering`과 연결합니다.

## 언어 프로필

`distributed-systems` 트랙은 C·C++·Java·Python 가운데 한 언어 기반을 요구하며 정본 `default` 선형 경로는 C를 대표 선택으로 사용합니다. 이 저장소가 배포하는 실행 프로필은 다음처럼 더 좁습니다.

- Python 3.12 이상
- 표준 라이브러리만 사용
- Python으로 작성된 예제, capstone starter와 public contract test

C·C++·Java로 같은 protocol을 다시 구현할 수는 있지만, 제공된 Python test가 그 구현을 자동 판정하지는 않습니다. 동등한 public API adapter, 정상·경계·실패 검사, 같은 trace schema와 사람 검토 근거를 별도로 제출해야 합니다. Python을 사용하지 않은 구현도 저장소 자체의 `make check`·`make verify`에는 Python 3.12가 필요합니다.

## 빠른 시작

저장소 루트에서 가이드 배포본을 검사합니다.

```sh
make prepare
make check
VERIFY_LOG=/tmp/guide-distributed-systems-verify.log make verify
```

- `make prepare`는 외부 의존성을 설치하지 않고 `.guide/distributed-systems/prepared.json`에 Python 판본과 source fingerprint를 기록합니다.
- `make check`는 문서·링크·JSON fixture·Python 예제·canonical starter 계약을 빠르게 검사합니다.
- `make verify`는 준비 fingerprint까지 확인하며 로그는 저장소 밖 절대 경로에 기록합니다.
- `make clean`은 이 가이드가 소유한 `.guide/distributed-systems/`만 제거하며 `.workspace/`와 다른 cache를 순회하지 않습니다. 정식 검사 경로는 bytecode 생성을 끄고 외부 cache를 사용합니다.

capstone 작업 공간은 기존 대상을 덮어쓰지 않는 helper로 만듭니다.

```sh
./scripts/new-capstone-workspace.sh
CAPSTONE_ROOT="$PWD/.workspace/replicated-kv" \
  python3 -m unittest discover -s capstone/tests -v
```

처음 복사한 starter는 storage 같은 이미 제공된 계약은 통과할 수 있지만 `Node.tick`, `Node.receive`, `Node.submit`의 핵심 transition이 미완성이므로 관련 검사는 실패해야 정상입니다. `CAPSTONE_ROOT`를 생략하면 canonical `capstone/starter`를 검사하므로 학습자 구현 검사가 아닙니다. 구현·7개 run·counterexample dossier를 채운 뒤에는 `python3 scripts/check-capstone-workspace.py .workspace/replicated-kv`를 실행합니다.

root `make verify`는 **가이드 배포본의 무결성**을 확인합니다. public capstone test도 초기 milestone의 공개 계약만 보여 주며 완성된 protocol의 safety·liveness를 모두 판정하지 않습니다. 최종 완료에는 추가 fault schedule, history checker와 [완료 근거 루브릭](reference/completion-evidence-rubric.md)의 dossier가 필요합니다.

실행 전에는 [실습 안전·정리 계약](reference/lab-safety.md)을 확인합니다. 자동 경로는 로컬 결정적 simulation만 실행하며 root 권한, Docker, 실제 network 변경 또는 유료 cloud resource를 요구하지 않습니다.

## 읽는 순서

전체 선택 경로와 트랙 위치는 [학습 로드맵](docs/00-roadmap.md)에 있습니다.

| Part | 시작 문서 | 누적 결과 |
|---|---|---|
| 1 | [분산 실행 모델과 관찰 경계](docs/01-model-and-time/01-distributed-execution-model.md) | system·failure·time model과 safety·liveness를 분리합니다. |
| 2 | [복제와 상태 기계](docs/02-replication-and-consistency/01-replication-and-state-machines.md) | consistency와 quorum 주장을 history로 판정합니다. |
| 3 | [Consensus와 leader election](docs/03-consensus-and-membership/01-consensus-and-leader-election.md) | election·log·persistence·snapshot·membership 불변식을 연결합니다. |
| 4 | [Sharding과 routing metadata](docs/04-partitioning-and-atomicity/01-sharding-routing-and-rebalancing.md) | epoch·fencing·snapshot·cutover로 ownership 전이를 검토합니다. |
| 5 | [결정적 시뮬레이션](docs/05-validation/01-deterministic-simulation.md) | fault schedule·invariant·history와 source identity를 보존합니다. |
| 6 | [통합 과제](docs/06-capstone.md) | 복제 key-value store와 membership·sharding 검토 dossier를 완성합니다. |

## 실습과 근거 원칙

실습은 정답 코드의 모양보다 공개 상태와 관찰 결과를 다룹니다.

```text
system·failure model과 sequential specification을 적습니다.
→ node·message·timer·disk·client event를 trace로 기록합니다.
→ 정상·경계·대표 실패 schedule을 고정합니다.
→ every-step safety invariant와 조건부 liveness 기대를 분리합니다.
→ 위반 history를 최소화하고 regression fixture로 남깁니다.
→ 구현을 수정한 뒤 기존·추가 schedule을 다시 실행합니다.
```

고정 답지가 없는 분석 실습은 가정, 상태 전이, 첫 위반 event와 비보장 범위를 제출합니다. capstone은 public test 외에 source·config·seed·schedule identity와 최소 counterexample를 남깁니다. trace의 공통 필드와 hash 규칙은 [trace schema](reference/trace-schema.md)를 사용합니다.

## 트랙에서의 위치

`main`의 모든 포함 트랙을 그대로 요약하면 다음과 같습니다.

| 트랙 | 위치 | 정본 선형 경로에서의 취급 |
|---|---|---|
| `distributed-systems` | required | `default`: `git → c → computer-architecture → operating-systems → computer-networks → database-systems → distributed-systems` |
| `data-engineering` | recommended | `default` 종료 뒤 선택하며 선형 경로 자체에는 포함되지 않음 |
| `web-backend` | advanced | 핵심 직무 진입 경로 뒤 심화, 선형 경로에는 포함되지 않음 |
| `cloud-engineering` | advanced | 핵심 cloud 경로 뒤 심화, 선형 경로에는 포함되지 않음 |
| `infrastructure-platform` | advanced | `host-platform`·`cloud-platform` 뒤 심화, 두 경로에는 포함되지 않음 |
| `cybersecurity` | advanced | 핵심 보안 경로 뒤 심화, 선형 경로에는 포함되지 않음 |
| `machine-learning` | advanced | 모델 개발 경로 뒤 심화, 선형 경로에는 포함되지 않음 |
| `database-engineering` | advanced | `internals` 또는 `application-data` 뒤 심화, 두 경로에는 포함되지 않음 |
| `game-server` | advanced | Java/Spring 게임 서버 경로 뒤 심화, 선형 경로에는 포함되지 않음 |
| `game-security-anticheat` | advanced | 보안·안티치트 경로 뒤 심화, 선형 경로에는 포함되지 않음 |

`advanced`나 `recommended` 표기를 해당 트랙의 완료 필수 조건으로 해석하지 않습니다.

## 종료 능력과 판정 한계

정본 종료 능력은 세 가지입니다.

1. 복제 상태 기계의 safety·liveness를 설명합니다.
2. partition과 leader 교체를 재현합니다.
3. 작은 분산 저장소를 구현·검증합니다.

[완료 근거 루브릭](reference/completion-evidence-rubric.md)은 각 `owns`를 개념 문서, 단계 실습, capstone milestone과 이 세 종료 능력에 연결합니다. 자동 검사는 고정 fixture와 실행한 bounded schedule에 대한 근거일 뿐 모든 event order, production durability, 실제 network·clock 또는 운영 환경을 증명하지 않습니다. 최종 판정에는 dossier의 trace·counterexample·비보장 범위를 사람이 검토해야 합니다.
