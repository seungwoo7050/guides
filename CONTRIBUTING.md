# 기여 안내

문서, fixture, 예제, capstone starter와 검증 코드는 같은 분산 시스템 계약을 가리켜야 합니다. 설명만 맞거나 예제만 실행되는 변경은 완료된 변경으로 보지 않습니다.

## 범위 먼저 확인하기

이 브랜치는 복제 상태·consistency·consensus·membership·sharding과 protocol 검증을 소유합니다.

다음 내용은 해당 브랜치에 기여합니다.

- 서비스 간 Outbox·Saga·업무 재조정: `distributed-services`
- TCP·라우팅·DNS·TLS: `computer-networks`
- 단일 DBMS의 MVCC·WAL·질의 실행: `database-systems`
- 프로세스·filesystem·동시성 기초: `operating-systems`
- 호스트·컨테이너·배포 운영: `web-infra`

현재 문서에는 필요한 접점과 분산 protocol에서 달라지는 책임만 추가합니다.

## 문서를 고칠 때

- 자연스러운 한국어 경어체를 사용합니다.
- 명령, field, API, 논문 용어는 원래 표기를 유지하고 백틱으로 구분합니다.
- 각 문서는 `목표`, `문제`, `계약`, `실패 조건`, `검증`, `완료 조건`을 구분합니다.
- system model, failure model과 시간 가정을 생략한 채 보장을 단정하지 않습니다.
- `replicated`, `durable`, `committed`, `applied`, `client-visible`을 같은 상태처럼 표현하지 않습니다.
- “linearizable”, “exactly once”, “available”, “fault tolerant” 같은 주장은 history·불변식·failure 범위와 함께 씁니다.
- 제품 설정과 framework API는 안정된 protocol 원리와 분리합니다.
- 1차 자료의 결론을 과장하지 않고 [1차 자료 지도](reference/primary-sources.md)에 source와 적용 범위를 남깁니다.

## Fixture와 예제를 고칠 때

- wall-clock sleep과 thread timing보다 virtual time과 explicit event를 우선합니다.
- fixture에는 initial state, event ID, source identity와 기대할 불변식이 있어야 합니다.
- 정답을 JSON에 숨겨 넣지 않습니다. 판정에 필요한 사실만 제공합니다.
- 위반 trace는 첫 위반 event를 찾을 수 있어야 하며 가능한 경우 축소합니다.
- 예제는 Python 3.12 표준 라이브러리만 사용합니다.
- deterministic 예제는 같은 입력에서 byte-equivalent 출력 또는 같은 digest를 만들어야 합니다.

## Capstone을 고칠 때

- 완성된 Raft reference answer를 추가하지 않습니다.
- starter의 public API를 바꿀 때 `capstone/tests`, 문서와 trace schema를 함께 갱신합니다.
- canonical starter의 핵심 transition은 의도적으로 미완성이어야 합니다.
- public tests를 약하게 만들어 starter를 통과시키지 않습니다.
- 새로운 milestone은 명확한 invariant, fault schedule과 완료 증거를 가져야 합니다.
- 실제 runtime adapter는 deterministic protocol core와 분리합니다.

## 변경 확인

```sh
make prepare
make check
VERIFY_LOG=/tmp/guide-distributed-systems-verify.log make verify
make clean
```

커밋 전에는 추적 범위와 공백 오류도 확인합니다.

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

서로 독립된 학습 단계는 나누고, 문서와 그 계약을 확인하는 fixture·검사는 같은 변경에 포함할 수 있습니다.
