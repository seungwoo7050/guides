# 용어

## Coding agent

소프트웨어 저장소를 조사하고 file·process·Git tool을 사용해 변경과 검증을 반복하는 에이전트 시스템입니다. 단일 코드 생성 응답과 구분합니다.

## Model adapter

provider-specific request·stream·tool-call·error를 runtime 내부의 안정적인 event와 action contract로 변환하는 계층입니다.

## Runtime

session state, tool 순서, budget, checkpoint, permission과 verifier 연결을 소유하는 실행기입니다.

## Action candidate

모델이 제안한 구조화된 다음 행동입니다. validation·policy·approval을 통과하기 전에는 실제 권한이나 effect가 아닙니다.

## Tool gateway

등록된 tool schema와 policy에 따라 filesystem·process·Git 등의 실제 adapter를 호출하고 receipt를 만드는 경계입니다.

## RepositorySnapshot

session 시작 시의 repository root, HEAD, index, working tree, instruction과 환경 identity를 고정한 상태입니다.

## ContextManifest

모델에 제공된 source·instruction·tool result의 origin, digest, scope, trust와 freshness를 기록한 목록입니다.

## Change set

session baseline에 대해 agent가 준비·적용한 여러 파일 변경의 논리적 묶음입니다.

## Receipt

tool이 실제로 수행한 action, resource, before/after, 결과와 version을 기록한 증거입니다.

## Effect ledger

재시도·crash·resume 뒤 외부 효과를 중복하지 않도록 operation identity와 상태를 기록한 정본입니다.

## Verifier

모델과 runtime의 완료 선언과 독립적으로 final workspace, behavior, regression, policy와 evidence를 판정하는 검사기입니다.

## Scripted model

미리 정의한 조건과 action을 반환해 runtime을 결정적으로 검사하는 model adapter입니다.

## Narrow check

현재 가설과 변경에 가까운 빠른 test·compile·lint입니다.

## Broad verification

관련 module 또는 repository 전체의 회귀와 release gate를 확인하는 넓은 검사입니다.

## Stale context

file·branch·environment가 바뀌어 더 이상 현재 workspace를 정확히 표현하지 않는 context item입니다.

## Prompt injection

저장소·issue·tool output 등의 data에 상위 지시를 바꾸려는 문장을 넣어 모델 행동을 조작하는 공격 또는 입력 패턴입니다.

## Delegated authority

사용자 권한 전체가 아니라 task에 필요한 resource와 effect만 agent session에 제한적으로 위임한 권한입니다.

## Evaluation error

agent의 해결 능력과 무관하게 fixture, environment, verifier 또는 harness 문제로 결과를 판정할 수 없는 상태입니다.
