# 실패 분류와 재계획

## 목표

“명령이 실패했다”를 하나의 상태로 보지 않습니다. 코드·테스트·환경·명령·정책·기존 실패를 구분하고, 분류에 맞는 다음 행동만 허용합니다.

## 실패 분류표

### 코드 결함

변경한 production code가 contract를 위반합니다.

근거:

- 수정 전 통과·수정 후 실패
- stack trace가 변경 경로와 연결
- reproduction이 기대와 다른 상태를 보임

다음 행동:

- 관련 source 재읽기
- 가설·patch 수정
- 좁은 test 재실행

### 불완전한 변경

한 call site, schema, type, generated artifact 또는 test update가 빠졌습니다.

다음 행동:

- symbol reference와 build dependency 재검색
- change impact plan 갱신

### 테스트 결함

test가 요구와 다르거나 fixture가 실제 contract를 표현하지 못합니다.

다음 행동:

- test의 public behavior 근거 확인
- production code를 맞추기 전에 사용자·문서·기존 contract와 비교
- test 변경 이유를 별도 기록

### 환경 결함

runtime, dependency, service, permission, disk, network가 준비되지 않았습니다.

다음 행동:

- environment manifest와 preparation phase로 이동
- code patch를 보류
- 해결 불가능하면 `BLOCKED_ENVIRONMENT`

### command 결함

잘못된 cwd, target, argument, quoting 또는 timeout profile을 사용했습니다.

다음 행동:

- repository evidence로 command 수정
- source code는 바꾸지 않음

### 기존 실패

session 시작 전에도 실패했습니다.

다음 행동:

- task와 관련 여부 조사
- 새 회귀와 분리
- final report에 baseline과 current를 함께 표시

### flaky 또는 nondeterministic

같은 revision·seed·환경에서 결과가 변합니다.

다음 행동:

- deterministic reproduction 시도
- 제한된 retry와 fingerprint 비교
- green 한 번으로 완료하지 않음

### 정책·sandbox 차단

행동이 권한 경계를 넘었습니다.

다음 행동:

- 다른 안전한 경로 탐색
- 필요한 authority를 사용자에게 설명
- policy를 코드로 우회하지 않음

### runtime/model 실패

adapter 오류, invalid action, context overflow, tool result parse 실패입니다.

다음 행동:

- runtime repair 또는 model retry policy
- repository source 변경 금지

## ClassificationRecord

```text
failure_id
iteration_id
category
observed_facts[]
evidence_refs[]
confidence
alternative_categories[]
recommended_actions[]
forbidden_actions[]
requires_user
```

분류가 불확실하면 단일 label로 확정하지 않고 추가 evidence를 수집합니다.

## 재계획

재계획은 이전 계획을 지우는 일이 아닙니다.

1. 어떤 가설이 반증됐는지 기록합니다.
2. 어떤 context가 stale인지 표시합니다.
3. 이전 patch를 유지·부분 rollback·전체 rollback할지 정합니다.
4. 새 investigation step을 추가합니다.
5. permission과 budget 변화를 계산합니다.
6. 사용자 승인 범위를 재검사합니다.

## 같은 실패 반복 감지

fingerprint 예시:

```text
producer + category + normalized message + source location + top stack frames
```

같은 fingerprint가 새 evidence 없이 반복되면 다음을 수행합니다.

- plan을 중단하고 investigation으로 돌아갑니다.
- context selection을 재검토합니다.
- 더 넓은 code path나 다른 hypothesis를 선택합니다.
- 사용자에게 현재 막힘과 선택지를 보고합니다.

## 실패를 숨기는 잘못된 수리

- failing test skip
- timeout 증가만 반복
- assertion 약화
- error를 catch하고 무시
- type check 제외
- network error를 mock success로 바꿈
- dependency version을 근거 없이 변경
- 관련 없는 code 삭제

verifier는 test 결과뿐 아니라 이런 계약 약화를 탐지해야 합니다.

## 완료 조건

- 최소 여덟 종류의 실패가 서로 다른 다음 행동을 만듭니다.
- baseline failure와 agent-induced regression을 구분합니다.
- 같은 fingerprint 반복 시 정지·재조사 규칙이 있습니다.
- 재계획이 patch·context·approval·budget을 함께 갱신합니다.
