# 기여 안내

문서, fixture, 예제, capstone starter와 검증 코드는 같은 분산 시스템 계약을 가리켜야 합니다. 설명만 맞거나 예제만 실행되는 변경은 완료된 변경으로 보지 않습니다.

## 정본 범위부터 확인하기

이 브랜치는 다음 다섯 영역을 소유합니다.

- 분산 시간·순서·failure detector
- 복제와 일관성 모델
- leader election·합의·replicated log
- snapshot·membership change·sharding
- 결정적 장애 주입과 history 검증

다음 내용은 이 브랜치가 아니라 각 전담 브랜치에 기여합니다.

- 서비스 업무 saga·Outbox·업무 재조정: `distributed-services`
- TCP·라우팅·DNS·TLS: `computer-networks`
- 단일 DBMS의 MVCC·WAL·질의 실행 전체: `database-systems`
- process·filesystem·동시성 기초: `operating-systems`
- Kubernetes 운영: `platform-engineering`
- 특정 cloud 제품 설정: 공급자 자료와 해당 운영 경로

현재 문서에는 선행 개념을 짧게 연결하고 복제 상태 기계에서 달라지는 state·authority·failure·evidence만 깊게 추가합니다. 범위를 바꾸어야 한다면 이 브랜치만 예외로 만들지 말고 최신 `main`의 카탈로그 계약을 먼저 검토합니다.

## 문서를 고칠 때

- 자연스러운 한국어 경어체를 사용합니다.
- 명령, field, API와 논문 용어는 원래 표기를 유지하고 백틱으로 구분합니다.
- 브랜치 전체에서 문제, 상태 소유자, event, 정상·경계·실패 조건, 검증과 비보장 범위를 찾을 수 있어야 합니다.
- system model, failure model과 시간 가정을 생략한 채 보장을 단정하지 않습니다.
- `replicated`, `durable`, `committed`, `applied`, `client-visible`을 같은 상태처럼 표현하지 않습니다.
- “linearizable”, “exactly once”, “available”, “fault tolerant” 같은 주장은 history·불변식·지원 failure와 함께 씁니다.
- bounded simulation 통과를 모든 schedule에 대한 증명으로 표현하지 않습니다.
- 제품 설정과 framework API는 안정된 protocol 원리와 분리합니다.
- [1차 자료 지도](reference/primary-sources.md)에 저자·원문 링크·적용 범위와 원문이 증명하지 않는 점을 남깁니다.
- 핵심 소유 범위를 추가하거나 바꾸면 [완료 근거 루브릭](reference/completion-evidence-rubric.md)의 문서→실습→capstone→종료 능력 연결도 함께 갱신합니다.

## Fixture와 예제를 고칠 때

- wall-clock sleep과 thread timing보다 virtual time과 explicit event를 우선합니다.
- fixture에는 initial state, event identity, participant와 판정할 invariant가 있어야 합니다.
- 정답 label을 입력에 숨겨 놓고 그대로 반환하지 않습니다.
- 정상 경로 외에 대표 boundary와 failure를 포함합니다.
- 위반 trace는 첫 위반 event와 축소한 counterexample를 남길 수 있어야 합니다.
- 예제는 Python 3.12 표준 라이브러리만 사용합니다.
- 결정적 예제는 같은 source·config·seed·schedule에서 같은 canonical output 또는 digest를 만들어야 합니다.
- 새로운 trace producer는 [trace schema](reference/trace-schema.md)의 공통 envelope와 source identity를 사용하거나 명시적인 변환표를 제공합니다.

## Capstone을 고칠 때

- 완성된 Raft reference answer를 canonical tree에 추가하지 않습니다.
- starter의 public API를 바꿀 때 `capstone/tests`, 문서와 trace schema를 함께 갱신합니다.
- canonical starter의 핵심 transition은 의도적으로 미완성이어야 합니다.
- public test를 약하게 만들어 starter나 알려진 오답을 우연히 통과시키지 않습니다.
- public test가 전체 protocol 검증기라고 주장하지 않습니다.
- 새로운 milestone은 invariant, 정상·경계·실패 schedule과 완료 evidence를 가져야 합니다.
- membership·sharding 구현은 선택 확장일 수 있지만, 두 소유 범위를 현재 capstone에 적용한 설계·trace dossier는 필수로 유지합니다.
- 실제 runtime adapter는 deterministic protocol core와 분리합니다.

## 언어 프로필

배포된 실행 프로필은 Python 3.12 이상 표준 라이브러리입니다. C·C++·Java port를 추가하려면 다음을 함께 제공합니다.

- 기존 public API와 field 의미의 대응표
- 동일 fixture 또는 의미가 같은 변환 fixture
- 정상·경계·실패 행동 검사와 실행 명령
- 공통 trace·artifact schema
- 제공된 Python test와 직접 비교할 수 없는 범위

다른 언어 구현의 존재만으로 Python canonical path를 제거하거나 root 검증을 선택 항목으로 만들지 않습니다.

## 안전과 데이터 보존

[실습 안전·정리 계약](reference/lab-safety.md)을 따릅니다.

- 자동 필수 경로에는 root 권한, 실제 host network 변경, process kill, disk fault, Docker 또는 cloud resource 생성을 추가하지 않습니다.
- 실제 fault adapter는 disposable VM/container 같은 격리 경계, 최소 권한, resource limit, abort와 cleanup 증거를 먼저 제공합니다.
- `scripts/new-capstone-workspace.sh`는 기존 학습자 workspace를 덮어쓰지 않아야 합니다.
- 검증기는 추적 source나 learner source를 수정·삭제하지 않습니다. cache·marker·외부 log처럼 문서화한 생성물만 소유합니다.
- trace·history에는 credential, token, 실제 사용자 data 또는 민감한 payload를 넣지 않습니다.

## 변경 확인

저장소 루트에서 공개 명령을 실행합니다.

```sh
make prepare
make check
VERIFY_LOG=/tmp/guide-distributed-systems-verify.log make verify
```

`make verify`는 가이드 배포본을 검사하며 learner capstone 완료를 자동 판정하지 않습니다. capstone 변경에는 별도로 다음을 실행하고, public test 범위 밖의 추가 schedule과 dossier를 검토합니다.

```sh
./scripts/new-capstone-workspace.sh
CAPSTONE_ROOT="$PWD/.workspace/replicated-kv" \
  python3 -m unittest discover -s capstone/tests -v
```

정리 명령은 이 가이드가 소유한 `.guide/distributed-systems/`만 제거하며 `.workspace/`와 다른 Python cache를 순회하지 않습니다.

```sh
make clean
```

커밋 전에는 추적 범위와 공백 오류를 확인합니다.

```sh
git status --short
git diff --check
git diff --staged
```

## 커밋 예시

```text
docs(consensus): current-term commit 반례 보강
test(history): pending operation fixture 추가
feat(example): 결정적 message scheduler 구현
fix(capstone): snapshot session metadata 계약 명확화
```

서로 독립된 학습 단계는 나누고, 문서와 그 계약을 확인하는 fixture·검사는 같은 의미 단위에 포함할 수 있습니다. 기존 사용자 커밋은 amend·rebase·squash하지 않습니다.
