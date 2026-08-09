# 코딩 에이전트를 시스템으로 보기

## 목표

코딩 에이전트를 “모델에게 저장소와 문제를 주고 답을 받는 프로그램”으로 보지 않고, 서로 다른 신뢰·상태·권한을 가진 구성요소의 시스템으로 분해합니다.

## 모델은 에이전트 전체가 아니다

모델은 현재 context에서 다음 행동이나 응답 후보를 생성합니다. 모델은 다음 사실을 스스로 보장하지 못합니다.

- 읽은 파일이 현재 Git tree와 같은지
- 제안한 command가 허용된지
- patch가 stale file에 적용되지 않는지
- test가 실제로 실행됐는지
- 이미 수행한 외부 효과가 있는지
- 사용자 권한과 sandbox가 무엇인지
- 완료 선언이 acceptance condition을 만족하는지

따라서 다음을 분리합니다.

```text
Model                 다음 action 후보와 설명 생성
Runtime               session 상태·순서·budget·재개 관리
Repository explorer   저장소와 근거 조사
Context manager       제한된 context를 조립하고 staleness 관리
Tool gateway          file·search·edit·command·Git 계약 실행
Policy engine         principal·resource·action별 허용 여부 판정
Workspace sandbox     실제 파일·process·network 경계 강제
Verifier              결과와 불변식 독립 판정
Interface             사용자 질문·승인·중단·diff·근거 표시
Trace store           action·receipt·오류·비용·version 기록
```

## 세 개의 control loop

하나의 반복문에 모든 책임을 넣지 않습니다.

### 추론 loop

```text
현재 task와 context
→ model call
→ structured action candidate
```

모델 오류, schema 오류와 context 부족을 처리합니다.

### 실행 loop

```text
action candidate
→ validation
→ policy
→ approval
→ tool execution
→ receipt
→ state transition
```

권한과 실제 효과를 소유합니다.

### 검증 loop

```text
변경된 workspace
→ 좁은 검사
→ 실패 분류
→ 추가 조사 또는 수정
→ 전체 verifier
```

모델의 자연어 완료 선언과 독립적으로 동작합니다.

## 정본 상태

대화문을 유일한 상태로 사용하지 않습니다. 최소한 다음 정본이 필요합니다.

```text
TaskSpec
RepositorySnapshot
InstructionSet
SessionState
ContextManifest
PlanState
ToolReceiptLog
WorkspaceChangeSet
EvaluationState
BudgetState
```

Transcript는 사용자와 모델이 본 대화를 보존하지만, 파일 digest나 실제 command 결과를 대신하지 않습니다.

## 코딩 에이전트와 일반 workflow의 경계

모든 개발 자동화를 에이전트로 만들 필요는 없습니다.

고정 workflow가 적합한 경우:

- 입력 형식과 변환 규칙이 완전히 정의됩니다.
- 실행 명령과 검사가 고정됩니다.
- 예외를 유한한 상태로 열거할 수 있습니다.
- 모델 판단 없이 deterministic parser나 script가 더 안전합니다.

에이전트가 필요한 경우:

- 어떤 파일과 symbol을 조사할지 사전에 고정할 수 없습니다.
- 실패 결과에 따라 다음 evidence와 변경 전략이 달라집니다.
- 저장소마다 build·test·style·구조가 다릅니다.
- 사용자 요청이 목표는 주지만 구현 경로는 주지 않습니다.

좋은 시스템은 에이전트가 찾은 계획을 가능한 한 deterministic tool과 verifier로 실행합니다.

## 시스템 경계 예시

```text
User / CI caller
    │ task, constraints, approval
    ▼
Session controller
    ├── Model adapter
    ├── Repository explorer
    ├── Context manager
    ├── Policy decision point
    ├── Tool gateway
    │     ├── filesystem
    │     ├── search/index
    │     ├── patch/edit
    │     ├── process runner
    │     └── Git adapter
    ├── Isolated workspace
    ├── Event log / checkpoint
    └── External verifier
```

모델은 filesystem, shell, Git credential과 verifier storage에 직접 접근하지 않습니다.

## 설계 산출물

최소 architecture 문서에는 다음이 있어야 합니다.

- 구성요소와 trust boundary
- 각 상태의 유일한 소유자
- model output이 실제 effect가 되는 경로
- 사용자 승인과 cancellation 경로
- verifier가 읽을 수 있지만 agent가 바꿀 수 없는 자원
- crash 시 복구 기준점
- local interactive와 unattended 실행의 차이

## 실패 조건

- 모델 객체가 직접 파일·shell·Git client를 호출합니다.
- transcript만 저장하고 실제 workspace digest와 receipt를 저장하지 않습니다.
- policy와 tool validation이 prompt 문장으로만 존재합니다.
- test output을 모델이 요약한 문자열만 남깁니다.
- user cancel이 UI 표시만 바꾸고 process tree는 계속 실행됩니다.
- verifier가 agent와 같은 쓰기 권한·context를 공유합니다.

## 완료 조건

- 모델을 제거해도 scripted action으로 runtime과 tool contract를 테스트할 수 있습니다.
- runtime을 제거해도 model adapter의 입력·출력과 오류를 독립적으로 테스트할 수 있습니다.
- tool 실행 결과가 receipt로 남고 session state와 연결됩니다.
- verifier가 모델의 완료 선언 없이도 결과를 판정합니다.
