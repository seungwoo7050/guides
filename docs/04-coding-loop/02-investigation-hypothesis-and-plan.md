# 조사, 가설과 계획

## 목표

코드를 수정하기 전에 현재 동작을 재현하고, 관측 사실과 원인 가설을 분리하며, 어떤 변경이 어떤 검사로 이어질지 계획합니다.

## 조사 단계

```text
TaskSpec 확인
→ repository baseline 확인
→ 지시·환경·명령 발견
→ 문제 재현
→ 관련 code·test·history 조사
→ 사실과 가설 기록
→ 최소 변경 계획
```

재현할 수 없으면 즉시 추측 수정으로 이동하지 않습니다. 입력·환경·version·feature flag·timing 차이를 조사합니다.

## EvidenceRecord

```text
evidence_id
type: source | test | command | history | user
statement
source_reference
repository_revision
collected_at
confidence
supports_hypotheses[]
contradicts_hypotheses[]
```

모델이 만든 설명은 evidence가 아닙니다. source·tool receipt와 연결될 때만 근거가 됩니다.

## hypothesis

예:

```text
H1: refresh token row를 읽은 뒤 갱신하기까지 lock이 없어 두 요청이 성공한다.
H2: DB는 막고 있지만 client retry가 같은 성공 응답을 두 번 처리한다.
H3: test fixture가 실제 production isolation과 다르다.
```

각 가설에는 다음을 둡니다.

- 설명하는 관측
- 반증할 관측
- 확인할 file·command·test
- 예상 변경 경계
- 위험

## 조사와 변경의 분리

초기 조사 단계에서는 read-only tool을 우선합니다. 변경을 통해 가설을 확인해야 할 때도 temporary instrumentation과 production change를 구분합니다.

- debug log 추가
- 작은 reproduction test 작성
- temporary assertion
- trace flag

이런 조사 변경도 change set으로 기록하고 최종 patch에 남길지 결정합니다.

## plan 구조

```text
PlanStep
- 목적
- 근거 evidence
- 대상 path·symbol
- 예상 edit kind
- 선행 조건
- 실행할 좁은 검사
- 실패 시 다음 분기
- rollback 방법
```

계획은 파일 목록만이 아닙니다.

나쁜 예:

```text
1. auth.py 수정
2. test 실행
```

좋은 예:

```text
1. token 소비를 단일 DB 조건부 갱신으로 바꿉니다.
   근거: H1을 지지하는 service.py 82~110과 동시성 재현 test.
   검사: 두 worker barrier test에서 성공 1건, reuse error 1건.
2. 기존 단일 요청과 만료 error contract를 회귀 검사합니다.
3. migration이 필요 없는지 schema와 query plan을 확인합니다.
```

## plan의 크기

너무 큰 plan은 첫 실패 뒤 전체가 낡습니다. 다음 경계에서 재계획합니다.

- 새 causal evidence 발견
- 예상하지 않은 file 변경
- test가 다른 상태 소유자를 드러냄
- public API·migration 필요
- permission·budget 확대
- 사용자 constraint 변경

## 계획과 승인

사용자 승인은 “계획 전체”보다 실제 effect에 가까워야 합니다.

- read-only 조사 plan은 자동 진행 가능
- 여러 file patch는 diff 또는 target/intent 승인
- dependency install·network·Git commit은 별도 승인
- plan이 바뀌면 기존 승인의 범위를 재검사

## 실패 조건

- 재현 없이 가장 그럴듯한 file을 수정합니다.
- 사실, 가설과 사용자 요구가 하나의 summary에 섞입니다.
- plan이 test 실패에도 고정됩니다.
- 수정 target은 있지만 검증 경로와 rollback이 없습니다.
- history의 과거 의도를 현재 요구로 단정합니다.

## 완료 조건

- 최소 두 개의 대안 가설과 반증 evidence를 기록합니다.
- 재현 실패와 문제 부재를 구분합니다.
- 각 plan step이 evidence·edit·check·failure branch를 가집니다.
- 계획 변경 시 stale context와 approval을 갱신합니다.
