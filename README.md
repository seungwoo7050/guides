# 분산 시스템 설계·구현·검증 가이드

분산 시스템은 서버가 여러 대라는 이유만으로 어려운 것이 아닙니다. 한 노드가 본 상태를 다른 노드가 아직 보지 못할 수 있고, 메시지는 늦거나 사라지거나 중복될 수 있으며, 장애와 지연을 관찰만으로 구분하지 못하는 순간에도 시스템이 약속한 상태를 보존해야 하기 때문에 어렵습니다.

이 가이드는 분산 시스템의 제품과 알고리즘 이름을 나열하지 않습니다. 다음 질문을 **상태 모델, 실행 trace, 작은 구현과 반복 가능한 검사**로 다룹니다.

- 전체 시스템을 관찰하는 공통 시계가 없을 때 사건의 순서를 어떻게 표현합니까?
- 어떤 장애를 허용하며, 그 가정 아래 무엇을 안전하게 보장할 수 있습니까?
- 복제본이 서로 다른 상태를 가질 때 읽기와 쓰기의 의미는 무엇입니까?
- leader가 바뀌고 메시지가 재정렬되어도 이미 commit한 명령이 사라지지 않는 이유는 무엇입니까?
- 다수결, quorum 교차와 consensus는 서로 어떤 문제를 해결합니까?
- snapshot, membership 변경, client retry가 replicated log의 안전성과 어떻게 연결됩니까?
- shard를 옮기는 동안 같은 key를 두 곳에서 변경하거나 어느 곳에서도 변경하지 않는 상태를 어떻게 막습니까?
- 구현이 linearizable하거나 특정 불변식을 지킨다는 주장을 어떤 history와 장애 실험으로 검증합니까?

## 이 브랜치가 소유하는 범위

```text
비동기 메시지 전달과 failure model
사건 순서, causality와 logical clock
safety, liveness와 분산 명세
복제, consistency model과 quorum
anti-entropy, version과 수렴
consensus, leader election과 replicated log
Raft의 log replication, persistence와 client session
snapshot, log compaction과 membership change
sharding, routing metadata와 rebalancing
atomic commit와 consensus의 경계
consistent global snapshot
결정적 시뮬레이션, history 검사와 model checking
```

다음 영역은 다른 가이드가 주로 소유합니다.

- TCP, 손실 복구, DNS와 네트워크 경로: [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks)
- 프로세스, 동시성, 가상 메모리와 저장장치: [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- 관계 의미론, MVCC, WAL과 단일 DBMS 내부구조: [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- 서비스 간 업무 상태, Outbox, Saga와 재조정: [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)
- 호스트, 컨테이너, 배포와 운영 관측 수집기: [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- 알고리즘 문제 계약, 복잡도와 일반 자료구조: [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms)

`distributed-services`와 이 브랜치는 이름이 비슷하지만 종료 지점이 다릅니다.

```text
distributed-services
여러 업무 서비스가 부분 실패 뒤에도 올바른 업무 결과로 수렴합니다.

 distributed-systems
여러 노드가 복제 상태, 순서와 membership에 대해 약속한 consistency를 유지합니다.
```

## 선행 지식

필수에 가까운 기반은 다음입니다.

- [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks)의 IP·TCP·timeout·partition 구분
- [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms)의 불변식, 그래프와 점근 분석
- Python, Java 또는 C++ 중 하나로 상태 기계와 테스트를 구현한 경험

다음은 권장 기반입니다.

- [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)의 동시성·파일 영속화·crash recovery
- [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)의 transaction·WAL·isolation
- [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)의 부분 실패와 불확실한 결과

공식 예제와 capstone starter는 Python 3.12 이상의 표준 라이브러리만 사용합니다. Python 언어 자체가 학습 목표는 아니며, 같은 계약을 Java 또는 C++로 다시 구현해도 됩니다.

## 시작

저장소 루트에서 다음 명령을 사용합니다.

```sh
make prepare
make check
VERIFY_LOG=/tmp/guide-distributed-systems-verify.log make verify
make clean
```

- `make prepare`는 추적 파일을 변경하지 않고 Python 버전과 저장소 입력 지문을 확인해 `.guide/distributed-systems/prepared.json`을 만듭니다.
- `make check`는 문서 구조, 내부 링크, JSON fixture와 예제의 빠른 검사를 실행합니다.
- `make verify`는 준비 지문을 다시 확인하고 예제, fixture 계약, starter 구조와 전체 문서 무결성을 검사합니다.
- `make clean`은 `.guide/`와 Python cache만 제거하며 학습자가 만든 `.workspace/`는 보존합니다.

이 브랜치는 완성된 Raft reference 구현을 제공하지 않습니다. 문서, 결정적 예제, trace fixture, capstone starter와 공개 테스트 계약을 제공합니다. 학습자는 `.workspace/`에 starter를 복사해 구현합니다.

```sh
mkdir -p .workspace
cp -R capstone/starter .workspace/replicated-kv
python3 -m unittest discover -s capstone/tests -v
```

처음에는 핵심 메서드가 구현되지 않아 capstone 검사가 실패합니다. 문서의 milestone 순서로 구현한 뒤 같은 검사를 통과시키고, 추가 장애 trace를 직접 작성합니다.

## 읽는 순서

전체 선택 경로는 [학습 로드맵](docs/00-roadmap.md)에 있습니다.

| Part | 시작 문서 | 종료 능력 |
|---|---|---|
| 1 | [분산 실행 모델과 관찰 경계](docs/01-model-and-time/01-distributed-execution-model.md) | 실행·장애·시간 가정을 명시하고 safety와 liveness를 분리합니다. |
| 2 | [복제와 상태 기계](docs/02-replication-and-consistency/01-replication-and-state-machines.md) | consistency와 quorum의 보장 범위를 trace로 판정합니다. |
| 3 | [Consensus와 leader election](docs/03-consensus-and-membership/01-consensus-and-leader-election.md) | Raft log·term·commit·membership 불변식을 설명하고 구현합니다. |
| 4 | [Sharding과 routing metadata](docs/04-partitioning-and-atomicity/01-sharding-routing-and-rebalancing.md) | key 배치와 원자성 경계를 이동·장애 중에도 보존합니다. |
| 5 | [결정적 시뮬레이션](docs/05-validation/01-deterministic-simulation.md) | 구현 주장을 history·fault schedule·model로 검증합니다. |
| 6 | [통합 과제](docs/06-capstone.md) | 결정적 환경에서 복제 key-value store를 단계별로 완성합니다. |

## 실습 원칙

실습은 “정답 코드를 복사하는 과정”이 아니라 **분산 실행을 기록하고 허용 가능한 history를 판정하는 과정**입니다.

```text
가정과 sequential specification을 먼저 적습니다.
→ 노드·메시지·timer·disk event를 trace로 기록합니다.
→ safety invariant와 liveness 기대를 분리합니다.
→ 장애 schedule을 고정합니다.
→ 위반 history를 최소화합니다.
→ 구현 또는 설계를 수정합니다.
→ 같은 schedule과 새로운 schedule에서 다시 검사합니다.
```

각 실습 README는 다음을 포함합니다.

- 초기 상태와 입력 fixture
- 학습자가 판정하거나 구현할 책임
- 반드시 보존해야 하는 불변식
- 대표 오답과 실패 조건
- 제출할 문서 또는 코드
- 완료를 확인하는 방법

## 종료 기준

가이드를 마치면 다음 작업을 수행할 수 있어야 합니다.

1. 분산 알고리즘의 시스템 모델, failure model과 시간 가정을 먼저 적습니다.
2. wall clock, causality, total order와 commit order를 혼동하지 않습니다.
3. linearizability, sequential consistency, causal consistency와 eventual convergence의 차이를 history로 설명합니다.
4. quorum 수식만으로 강한 일관성이 자동 보장된다고 주장하지 않습니다.
5. Raft의 election, log matching, leader completeness와 state machine safety를 trace로 검토합니다.
6. crash 직전·직후의 영속 상태와 restart 행동을 명시합니다.
7. client retry, deduplication과 snapshot metadata를 replicated state의 일부로 다룹니다.
8. shard 이동을 routing epoch, fencing과 명시적인 ownership 전이로 설계합니다.
9. safety invariant는 결정적 simulation·model·history 검사로, liveness는 시간·공정성 가정과 함께 검증합니다.
10. 실제 분산 시스템 저장소에서 작은 protocol·test·diagnostic 변경을 시작할 수 있습니다.

이 과정은 production consensus library를 완성하거나 분산 데이터베이스 전문가가 되는 과정이 아닙니다. 그 수준은 실제 코드베이스에서 장기간 fault, upgrade, data corruption, 운영 비용과 호환성을 다루며 형성됩니다.
