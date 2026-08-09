# Capstone review rubric

각 항목을 `미충족`, `부분`, `충족`, `강함`으로 평가합니다.

## 1. 에이전트 자체 개발

- 기존 agent SDK를 호출하는 wrapper가 아니라 runtime 핵심을 소유합니다.
- model adapter를 교체할 수 있습니다.
- scripted model로 runtime을 결정적으로 검사합니다.
- provider-compatible adapter의 HTTP·stream·구조화 출력 경계를 loopback fixture로 검사합니다.
- coding workflow는 주 profile이지만 model·RAG·tool·state·policy·evaluator contract는 도메인 중립적입니다.

## 2. 저장소 이해

- Git baseline과 instruction/environment discovery가 있습니다.
- target file을 사전에 고정하지 않습니다.
- source·test·config·command를 evidence로 연결합니다.

## 3. RAG와 출처·권한

- retrieval 전에 task principal과 source 권한을 적용합니다.
- 허가된 source의 origin·scope·revision·digest를 context와 최종 citation까지 유지합니다.
- stale·conflicting source가 refresh 또는 명시적 failure를 만듭니다.
- secret·hidden verifier·권한 밖 source가 후보·summary·trace에 나타나지 않습니다.

## 4. 도구와 실행

- safe filesystem, multi-file patch, process runner와 Git adapter가 있습니다.
- timeout·cancel·child cleanup·output limit을 다룹니다.
- receipt와 actual diff가 일치합니다.
- model request·tool call·비용·wall-clock budget을 강제하고 소진 뒤 새 effect를 만들지 않습니다.

## 5. 코딩 loop

- 재현·가설·plan·edit·test·repair가 있습니다.
- 첫 실패 뒤 evidence 기반으로 재계획합니다.
- 좁은 검사와 넓은 검사를 구분합니다.

## 6. Durable 상태

- checkpoint와 append-only event/effect ledger가 있습니다.
- patch·command·approval 전후 crash에서 effect를 재조정하고 중복하지 않습니다.
- cancel 뒤 descendant process, pending action, credential과 임시 자원을 정리합니다.
- incompatible or corrupt checkpoint를 자동 성공으로 합치지 않습니다.

## 7. 안전과 사용자 통제

- prompt injection과 malicious repository case가 있습니다.
- permission·approval·sandbox가 prompt 밖에서 강제됩니다.
- 질문·승인·cancel·resume·final review가 있습니다.
- principal·grant·policy·sandbox identity가 decision trace에 연결됩니다.

## 8. 평가

- fixture와 external hidden verifier가 분리됩니다.
- known-bad patch를 거절합니다.
- evaluation error를 agent failure와 구분합니다.
- trace·cost·user intervention을 보고합니다.
- reference 통과, starter의 의도된 실패와 known-bad mutant 거부를 모두 확인합니다.

## 카탈로그 종료 능력 판정

| 종료 능력 | 필수 증거 |
|---|---|
| 도구를 사용하는 에이전트를 구현한다 | discovery, authorized retrieval, structured tool call, 다중 파일 edit, command, repair와 durable resume의 실제 trace |
| 외부 verifier로 성공을 판정한다 | agent 환경과 분리된 behavior·regression·policy 판정, known-bad·tampering 거부 결과 |
| 권한·네트워크·비용·실행 시간을 제한한다 | task-scoped grant, network deny, cancel cleanup, model/tool/cost/time budget receipt와 forbidden effect 0건 |

## 게시 전 필수

다음 중 하나라도 없으면 Capstone 완료로 표시하지 않습니다.

- 다중 파일 변경
- 실제 command/test 실행
- 실패 뒤 repair iteration
- external verifier
- repository prompt injection 또는 권한 실패 case
- authorization-before-retrieval과 source citation
- crash/resume와 cancel cleanup
- model·tool·비용·실행 시간 budget exhaustion
- starter/reference/known-bad의 예상 판정

필수 검증은 scripted/loopback provider로 offline 실행할 수 있어야 합니다. 실제 provider live smoke가 없다는 사실은 한계로 기록하되, 이를 이유로 필수 model adapter contract를 생략하지 않습니다. reference 통과만으로 실제 provider 품질, 모든 OS sandbox나 production 안전성을 주장하지 않습니다.
