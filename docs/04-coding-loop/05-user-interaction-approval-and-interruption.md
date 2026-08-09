# 사용자 상호작용, 승인과 interruption

## 목표

사용자를 마지막 diff 검토자만이 아니라 task 결정, 권한 위임, 중간 수정과 중단을 제공하는 control-plane principal로 다룹니다.

## 상호작용 종류

```text
질문              요구·환경·제품 결정 확인
진행 보고          현재 phase와 evidence 요약
승인 요청          구체적인 effect 허용
수정 지시          task·constraint·plan 변경
interrupt          현재 생성 또는 command 중단
pause              checkpoint 뒤 일시 정지
cancel             session과 process 종료
resume             상태 검증 후 재개
최종 review         diff·test·risk 검토
```

모든 사용자 메시지를 동일한 chat text로 처리하지 않습니다.

## 질문 설계

좋은 질문은 사용자가 선택해야 할 결정을 좁힙니다.

나쁜 질문:

```text
어떻게 할까요?
```

좋은 질문:

```text
공개 API의 기존 필드 `timeout_seconds`를 한 release 동안 함께 유지할까요,
아니면 이번 변경에서 제거할까요?

A. 호환 alias 유지 + deprecation test
B. breaking change + migration note
```

질문하기 전에 저장소 조사로 해결 가능한 사실은 먼저 확인합니다.

## 승인 artifact

승인은 자연어 “좋아” 한 단어보다 다음과 연결됩니다.

```text
approval_id
principal
operation type
exact arguments 또는 patch digest
resource scope
valid_from·expires_at
single_use 또는 reusable
risk explanation
rollback plan
```

patch가 바뀌거나 command arguments가 달라지면 승인을 재사용하지 않습니다.

## 승인 수준

### 자동 허용

- 허용 workspace 안 read/search
- 등록된 read-only Git status
- bounded deterministic parser

### session 승인

- 허용 path의 일반 edit
- repository-defined test command

### 매회 승인

- dependency install
- network
- Git commit
- workspace 밖 접근
- long-running service

### 기본 금지

- remote push/force
- secret export
- verifier·answer 수정
- destructive host operation

위험 profile에 따라 조정하지만 숨은 broad grant를 만들지 않습니다.

## interruption

사용자가 입력을 시작했다고 즉시 모든 process를 kill할 필요는 없습니다. event 종류를 구분합니다.

- `STEER`: 현재 model generation을 중단하고 새 지시 반영
- `PAUSE_AFTER_TOOL`: 현재 원자적 tool을 끝낸 뒤 멈춤
- `CANCEL_NOW`: process tree 종료와 rollback/cleanup 시작
- `REVOKE_PERMISSION`: pending action 취소와 future policy 변경

외부 effect 도중 cancel이 도착하면 결과가 `UNKNOWN`일 수 있습니다. receipt와 실제 상태를 확인한 뒤 재개 또는 보상합니다.

## 사용자 지시로 인한 invalidation

예:

```text
사용자: 테스트는 건드리지 마.
```

runtime은 다음을 확인합니다.

- pending patch에 test 변경이 있는지
- 이미 test를 수정했는지
- plan의 acceptance가 test 추가를 전제로 했는지
- 기존 approval이 새로운 constraint와 충돌하는지

필요하면 rollback하고 plan revision을 만듭니다.

## 최종 결과 UX

최종 답변에는 다음이 있어야 합니다.

- 변경 요약
- 파일별 diff 또는 링크
- 실행한 명령과 결과
- 실패 후 바뀐 계획
- 실행하지 않은 검사
- 사용자 결정과 가정
- 잔여 위험
- 적용·commit·폐기 선택지

모델의 장황한 narrative보다 검토 가능한 artifact를 우선합니다.

## 실패 조건

- 포괄적 “모든 작업 허용” 승인을 기본으로 제안합니다.
- 사용자가 cancel했는데 background process가 남습니다.
- task 수정 뒤 이전 patch approval을 사용합니다.
- 질문으로 해결 가능한 제품 결정을 임의로 합니다.
- headless mode가 질문에 자동으로 가장 편한 답을 선택합니다.
- final report가 실행하지 않은 test를 생략합니다.

## 완료 조건

- 질문, 승인, steer, pause, cancel, resume가 별도 event입니다.
- approval이 exact effect와 expiry에 묶입니다.
- interruption 뒤 process·workspace·session state가 일관됩니다.
- 사용자가 최종 diff와 근거를 독립적으로 검토할 수 있습니다.
