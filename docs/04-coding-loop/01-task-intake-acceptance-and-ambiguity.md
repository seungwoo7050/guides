# 과제 수신, 완료 조건과 모호성

## 목표

자연어 요청을 바로 코드 변경으로 바꾸지 않고, 검증 가능한 `TaskSpec`과 변경 범위로 정규화합니다. 요구가 부족하거나 서로 충돌할 때 질문할지, 조사로 해결할지, 가정을 기록하고 진행할지 결정합니다.

## 사용자 요청은 보통 불완전하다

예:

```text
로그인 만료 문제를 고쳐 줘.
```

이 문장만으로는 다음이 정해지지 않습니다.

- 어떤 현상과 사용자 영향인지
- 재현 입력과 기대 상태
- 클라이언트·서버·DB 중 어디가 소유하는지
- 호환성을 유지해야 하는지
- test·migration·문서가 필요한지
- 변경 가능한 path와 command
- 완료를 판정할 acceptance condition

에이전트는 숨은 요구를 마음대로 채우지 않습니다.

## TaskSpec

```text
task_id
raw_request
goal
observable_problem
acceptance_conditions[]
constraints[]
non_goals[]
allowed_resources
required_evidence
risk_level
open_questions[]
assumptions[]
```

`goal`은 구현 방법이 아니라 사용자가 원하는 관찰 결과를 표현합니다.

## 정보 출처

TaskSpec은 다음을 조합합니다.

- 사용자 메시지
- issue·ticket·design 문서
- repository instruction
- failing test·log·stack trace
- 현재 코드와 public contract
- 사용자에게 받은 추가 답변

issue 본문이 현재 코드와 모순되면 사실로 확정하지 않고 `open question` 또는 가설로 둡니다.

## 질문할지 조사할지

### 저장소 조사로 해결할 수 있는 것

- 어떤 test command를 쓰는지
- 기존 error type과 style
- 해당 config의 현재 이름
- 관련 API와 call site

### 사용자 결정이 필요한 것

- 둘 이상의 제품 동작이 모두 가능한 경우
- 데이터 삭제·migration·호환성 선택
- 권한·network·비용 확대
- 공개 API breaking change
- 명시한 시간 안에 전체 검사를 실행할지

### 제한된 가정으로 진행할 수 있는 것

- 내부 변수명
- repository style에 따른 작은 구조 선택
- 쉽게 되돌릴 수 있고 acceptance에 영향 없는 구현 세부

가정은 trace와 최종 보고서에 남깁니다.

## 완료 조건 설계

좋은 acceptance condition은 외부에서 판정할 수 있습니다.

나쁜 예:

```text
코드를 깨끗하게 개선한다.
```

좋은 예:

```text
동일 refresh token을 동시에 두 요청이 사용하면 하나만 성공하고,
다른 요청은 명시적 재사용 오류를 반환하며,
기존 단일 요청 로그인 흐름은 통과한다.
```

다음 유형을 조합합니다.

- 동작 결과
- 상태 불변식
- 오류·권한 거절
- 호환성
- 성능 또는 resource budget
- 변경 금지 path
- 필수 test/build gate

## task 변경

사용자가 작업 중 요청을 바꾸면 새 문장만 context에 추가하지 않습니다.

1. TaskSpec revision을 만듭니다.
2. 기존 acceptance와 충돌을 찾습니다.
3. plan·pending patch·approval을 invalidation합니다.
4. 이미 수행한 effect의 처리 방법을 정합니다.
5. 필요한 경우 rollback하거나 새 change set을 시작합니다.

## 실패 조건

- issue title만 보고 구현을 시작합니다.
- test가 현재 구현을 설명한다는 이유로 사용자 목표보다 우선합니다.
- 질문이 필요한 제품 결정을 모델이 임의로 합니다.
- acceptance가 “test 통과” 하나뿐이고 어떤 test가 문제를 판정하는지 모릅니다.
- task 변경 뒤 이전 approval과 patch를 재사용합니다.

## 완료 조건

- 자연어 요청을 목표·관찰 문제·acceptance·constraint·non-goal로 분해합니다.
- 조사 가능한 불확실성과 사용자 결정이 필요한 불확실성을 구분합니다.
- 가정으로 진행한 항목을 최종 결과에 남깁니다.
- TaskSpec revision이 plan과 permission에 미치는 효과를 설명합니다.
