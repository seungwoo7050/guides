# Fail-safe 제어와 사고 증거

## 목표

에이전트가 잘못된 방향으로 빠르게 진행하거나 sandbox·policy가 예상대로 동작하지 않을 때 안전하게 중단하고, 무엇이 일어났는지 조사할 증거를 남깁니다.

## 제어 종류

```text
Pause            새 action을 막고 현재 안전 지점에서 checkpoint
Cancel           현재 session과 process를 종료
Kill             즉시 process·network·credential 차단
Revoke           permission·credential·approval 무효화
Quarantine       workspace와 artifact를 격리 보존
Rollback         agent change set 복구
Disable profile  특정 tool/model/runtime version 사용 중지
```

하나의 stop button이 모든 resource를 정리한다고 가정하지 않습니다.

## 자동 중단 조건

- forbidden path 접근 반복
- secret pattern 또는 credential access 시도
- network policy 위반
- 같은 실패 fingerprint 반복
- 예상 밖 changed path 급증
- command·token·time·비용 budget 초과
- verifier·evaluation resource 접근
- audit/trace 기록 실패
- sandbox health 이상
- runtime과 tool result schema 불일치

중단 조건은 model에게 경고하는 prompt가 아니라 runtime gate입니다.

## kill 순서

긴급 중단 예시:

1. 새 model/tool action 수락을 중단합니다.
2. network egress와 credential을 revoke합니다.
3. process tree를 종료합니다.
4. workspace를 read-only 또는 quarantine으로 전환합니다.
5. event log와 kernel/runtime evidence를 flush합니다.
6. cleanup과 증거 보존이 충돌하는 resource를 분류합니다.
7. 사용자에게 현재 상태와 불확실성을 보고합니다.

외부 effect가 `UNKNOWN`이면 무조건 rollback했다고 주장하지 않습니다.

## 사고 증거

```text
session·task·repository identity
runtime·model·tool·policy versions
action·policy·approval events
process argv·cwd·exit
network connection receipt
filesystem and Git diff
credential issuance·use·revoke
sandbox events
user control events
verifier result
clock source와 timestamp
```

대형 source와 log는 access-controlled artifact로 보존하고 trace에는 digest와 pointer를 둡니다.

## 사실과 가설

사고 보고에서 구분합니다.

```text
사실: 10:14:22에 sandbox process가 forbidden domain 연결을 시도했고 차단됨.
가설: repository test script가 dependency telemetry를 호출했을 수 있음.
```

모델이 제안한 설명을 사실로 기록하지 않습니다.

## 복구

- affected session을 재개하지 않고 새 clean snapshot을 고려합니다.
- credential을 회전합니다.
- malicious artifact를 일반 cache에서 제거합니다.
- policy·sandbox·tool bug를 수정합니다.
- 같은 fixture를 회귀 평가에 추가합니다.
- 사용자 작업이 손상됐는지 baseline과 비교합니다.

## 운영 runbook

각 failure class에 다음을 기록합니다.

- 탐지 signal
- 자동 조치
- 사용자에게 보일 메시지
- 증거 위치
- cleanup과 quarantine 기준
- credential·network 조치
- resume 가능 여부
- 회귀 case 추가 위치

## 실패 조건

- kill이 UI session만 종료합니다.
- cleanup이 먼저 실행되어 증거와 malicious artifact를 지웁니다.
- trace 저장 실패에도 agent를 계속 실행합니다.
- forbidden action을 “모델이 거절했다”는 사실만으로 안전 판정합니다.
- incident 뒤 같은 model/tool/policy version을 평가 없이 재배포합니다.

## 완료 조건

- pause, cancel, kill, revoke, quarantine와 rollback의 차이를 설명합니다.
- 자동 중단 조건이 runtime metric과 연결됩니다.
- 사고 타임라인을 model narrative 없이 artifact로 복원할 수 있습니다.
- 사고 사례가 새로운 evaluation fixture와 release gate로 이어집니다.
