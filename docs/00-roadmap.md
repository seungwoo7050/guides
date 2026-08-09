# 학습 로드맵

## 목표

이 과정의 목표는 모델 API를 호출하는 애플리케이션이 아니라 **소프트웨어 개발 작업을 수행하는 에이전트 런타임**을 직접 설계하고 구현하는 것입니다. 코딩 에이전트가 필수 Capstone이지만 model adapter, 권한 인지 retrieval, tool gateway, durable session, policy와 evaluator의 계약은 특정 업무 도메인에 종속되지 않게 유지합니다.

완료한 에이전트는 최소한 다음 질문에 코드와 기록으로 답해야 합니다.

- 지금 어느 저장소·commit·worktree를 대상으로 작업합니까?
- 어떤 지시가 적용되며 서로 충돌할 때 무엇이 우선합니까?
- 관련 코드를 찾기 위해 어떤 파일·symbol·history·test를 조사했습니까?
- 모델이 선택할 수 있는 action과 실제로 행사할 수 있는 권한은 무엇입니까?
- 파일 변경과 command 실행은 어떤 격리·제한·승인을 거칩니까?
- test 실패가 수정 때문인지, 환경 때문인지, 원래 존재하던 실패인지 어떻게 판정합니까?
- 실패 뒤 무엇을 다시 조사하고 어떤 근거를 폐기합니까?
- 중단이나 crash 뒤 어디서부터 안전하게 재개합니까?
- 완료를 모델이 아니라 어떤 verifier와 사용자 근거가 판정합니까?

## 대상 독자

다음 개발자에게 적합합니다.

- CLI 기반 코딩 에이전트 자체를 구현하려는 개발자
- model tool calling을 사용해 봤지만 실제 저장소 편집·명령 실행·검증 경계를 설계하지 못한 개발자
- 단일 응답형 코드 생성기에서 반복 조사·수정·테스트 에이전트로 확장하려는 개발자
- 코딩 에이전트의 sandbox, permission, Git 격리, checkpoint와 평가 harness를 이해하려는 개발자
- 기존 오픈소스 코딩 에이전트 runtime에 기여하기 전에 전체 구성요소를 연결하고 싶은 개발자

## 선행 경로

### 필수

```text
python
+ web-app
```

이는 `main` 카탈로그의 `requires`를 그대로 반영합니다. 이 과정은 Python 문법과 일반 웹 개발을 다시 설명하지 않습니다. 필요한 결과는 다음과 같습니다.

- Python으로 typed data model, CLI, 파일·subprocess·취소·테스트를 구현합니다.
- HTTP 요청·응답, API schema, 인증과 권한 경계를 구분합니다.

코딩 에이전트 프로필에는 다음 구현 역량도 필요합니다.

- Git의 HEAD·index·working tree·branch·worktree·diff·복구를 구분합니다.
- 경로·권한·프로세스·signal·stdout/stderr·exit status를 관찰합니다.

부족하면 `git`과 `unix-systems`에서 보완하되 카탈로그의 필수 관계를 바꾸지는 않습니다.

### 권장

```text
distributed-services
cybersecurity
machine-learning
```

장기 session과 외부 효과에는 `UNKNOWN`, idempotency와 retry budget이 필요합니다. 저장소와 command가 공격 입력일 수 있으므로 위협 모델과 최소 권한이 중요하며, model·dataset·evaluation 주장을 구분하려면 machine-learning의 평가 기반이 유용합니다.

완료 뒤에는 `data-engineering`, `platform-engineering`, `web-infra`에 연결되며, 조직 공용 runtime과 정책·sandbox 운영은 `platform-engineering`으로 이어집니다.

## 학습 단계

### Part 1. 런타임 기반

에이전트를 “모델을 반복 호출하는 함수”가 아니라 여러 신뢰 경계와 상태를 가진 시스템으로 나눕니다.

| 문서 | 종료 능력 |
|---|---|
| [코딩 에이전트를 시스템으로 보기](01-runtime-foundations/01-coding-agent-as-a-system.md) | 모델·runtime·tool·workspace·verifier의 책임을 나눕니다. |
| [Model adapter와 상호작용 프로토콜](01-runtime-foundations/02-model-adapter-and-interaction-protocol.md) | 공급자 API를 안정적인 내부 event와 action 계약으로 변환합니다. |
| [Session, transcript와 control plane](01-runtime-foundations/03-session-transcript-and-control-plane.md) | 대화 표시와 실행 정본을 분리하고 사용자 제어를 상태로 만듭니다. |
| [Context budget, compaction과 memory](01-runtime-foundations/04-context-budget-compaction-and-memory.md) | 제한된 context에 현재 작업 근거를 유지하고 낡은 근거를 폐기합니다. |

### Part 2. 저장소 이해

코딩 에이전트의 검색은 vector 유사도만으로 끝나는 RAG가 아닙니다. 현재 Git 상태, 프로젝트 지시, 코드 구조, build·test 경로와 실제 변경 영향을 함께 조사합니다. retrieval 전에 principal의 source 권한을 적용하고, 선택한 source의 origin·revision·digest·scope를 context와 최종 citation까지 보존합니다. 권한 없는 항목은 검색 결과나 요약에 들어간 뒤 가리는 것이 아니라 후보 생성 전에 제외합니다.

| 문서 | 종료 능력 |
|---|---|
| [저장소 snapshot과 Git 기준점](02-repository-understanding/01-repository-snapshot-and-git-baseline.md) | 변경 전 저장소 identity와 dirty state를 보존합니다. |
| [지시 발견과 우선순위](02-repository-understanding/02-instruction-discovery-and-precedence.md) | system·user·repository·directory 지시를 출처와 범위별로 해석합니다. |
| [파일 검색, symbol과 의존 근거](02-repository-understanding/03-file-search-symbols-and-dependency-evidence.md) | 파일명·text·symbol·reference·history를 단계적으로 사용합니다. |
| [환경, build와 test 발견](02-repository-understanding/04-environment-build-and-test-discovery.md) | 임의 설치 전에 manifest·script·CI에서 실행 계약을 복원합니다. |
| [Context 선택과 갱신](02-repository-understanding/05-context-selection-and-refresh.md) | 권한을 먼저 적용한 retrieval과 source provenance·citation·staleness를 관리합니다. |

### Part 3. 도구와 실행

모델 출력은 권한이 아닙니다. 모든 읽기·편집·명령·Git 동작을 구조화된 tool contract와 sandbox를 통해 수행합니다.

| 문서 | 종료 능력 |
|---|---|
| [Tool registry와 구조화된 action](03-tools-and-execution/01-tool-registry-and-structured-actions.md) | action parsing, validation, policy와 execution을 분리합니다. |
| [Filesystem read·search와 경로 안전성](03-tools-and-execution/02-filesystem-read-search-and-path-safety.md) | symlink·경로 이탈·대용량·binary를 안전하게 다룹니다. |
| [Edit, patch와 diff engine](03-tools-and-execution/03-edit-patch-and-diff-engine.md) | stale write와 부분 적용 없이 여러 파일 변경을 준비·적용·되돌립니다. |
| [Process runner와 terminal 계약](03-tools-and-execution/04-process-runner-and-terminal-contracts.md) | cwd·env·timeout·output·process tree·PTY를 명시적으로 통제합니다. |
| [Git, worktree, rollback과 change set](03-tools-and-execution/05-git-worktree-rollback-and-change-sets.md) | 사용자 변경을 보존하면서 agent 변경을 격리·검토·폐기합니다. |
| [Test·build·diagnostic 정규화](03-tools-and-execution/06-test-build-and-diagnostic-normalization.md) | 서로 다른 도구 출력을 실패 분류와 다음 행동에 사용할 구조로 변환합니다. |

### Part 4. 코딩 작업 루프

에이전트가 저장소를 바꾸는 실제 흐름을 설계합니다.

| 문서 | 종료 능력 |
|---|---|
| [과제 수신, 완료 조건과 모호성](04-coding-loop/01-task-intake-acceptance-and-ambiguity.md) | 요청을 검증 가능한 목표·제약·비범위로 바꿉니다. |
| [조사, 가설과 계획](04-coding-loop/02-investigation-hypothesis-and-plan.md) | 수정 전에 관측 사실과 원인 가설을 분리합니다. |
| [Edit-test-repair loop](04-coding-loop/03-edit-test-repair-loop.md) | 작은 변경과 좁은 검사에서 전체 회귀까지 반복합니다. |
| [실패 분류와 재계획](04-coding-loop/04-failure-classification-and-replanning.md) | 같은 행동 반복 대신 코드·환경·테스트·명령·기존 실패를 구분합니다. |
| [사용자 상호작용, 승인과 interruption](04-coding-loop/05-user-interaction-approval-and-interruption.md) | 질문·승인·수정 지시·취소를 runtime event로 처리합니다. |
| [지속 session, checkpoint와 resume](04-coding-loop/06-durable-sessions-checkpoint-and-resume.md) | 긴 작업을 중단·재개하면서 effect를 중복하지 않습니다. |

### Part 5. 안전과 권한

저장소, issue, test output, dependency와 tool output을 모두 잠재적 공격 입력으로 취급합니다.

| 문서 | 종료 능력 |
|---|---|
| [신뢰할 수 없는 저장소와 prompt injection](05-safety-and-authority/01-untrusted-repository-and-prompt-injection.md) | 데이터 속 지시를 authority로 승격하지 않습니다. |
| [권한 모델과 delegated authority](05-safety-and-authority/02-permission-model-and-delegated-authority.md) | 사용자 권한 전체가 아닌 작업별 capability를 부여합니다. |
| [Sandbox, network, secret과 dependency](05-safety-and-authority/03-sandbox-network-secrets-and-dependencies.md) | 파일·process·network·credential 경계를 독립적으로 제한합니다. |
| [외부 효과, 멱등성과 audit](05-safety-and-authority/04-effects-idempotency-and-audit.md) | commit·push·install 같은 효과를 receipt와 operation identity로 추적합니다. |
| [Fail-safe 제어와 사고 증거](05-safety-and-authority/05-fail-safe-controls-and-incident-evidence.md) | kill·pause·revoke·quarantine와 사후 분석 자료를 설계합니다. |

### Part 6. 평가와 운영

“한 번 잘 작동한 데모”와 재현 가능한 코딩 에이전트 품질을 구분합니다.

| 문서 | 종료 능력 |
|---|---|
| [코딩 과제 fixture와 verifier](06-evaluation-and-operations/01-coding-task-fixtures-and-verifiers.md) | repository issue, initial state와 acceptance test를 독립시킵니다. |
| [Hidden test, cheating과 평가 타당성](06-evaluation-and-operations/02-hidden-tests-cheating-and-evaluation-validity.md) | answer leakage와 grader tampering을 막고 실제 일반화를 측정합니다. |
| [Trace, replay, 비용과 품질 지표](06-evaluation-and-operations/03-traces-replay-cost-and-quality-metrics.md) | 결과뿐 아니라 행동 경로·비용·지연·사용자 개입을 비교합니다. |
| [회귀 행렬과 release gate](06-evaluation-and-operations/04-regression-matrix-and-release-gates.md) | model·prompt·tool·policy·runtime 변경을 분리해 평가합니다. |
| [Runtime 운영과 versioning](06-evaluation-and-operations/05-runtime-operations-and-versioning.md) | session schema, tool contract와 checkpoint 호환을 운영합니다. |

마지막에 [로컬 코딩 에이전트 Capstone](07-capstone.md)을 설계하고 구현합니다.

## 필수 구현 경로

가장 작은 완료 가능한 coding agent도 durable state, cancel과 budget을 생략하지 않습니다. 다음 순서로 읽고 대응 실습을 구현합니다.

```text
01-runtime-foundations 전체
→ 02-repository-understanding 전체
→ 03-tools-and-execution 전체
→ 04-coding-loop 전체
→ 05-safety-and-authority 전체
→ 06-evaluation-and-operations 전체
→ Capstone의 durable local 프로필
```

이 경로의 결과는 한 저장소에서 read·search·edit·command·test를 수행하고, budget·cancel·crash 뒤에도 효과를 중복하지 않으며, 외부 verifier로 완료를 판정하는 로컬 CLI입니다.

## 지속 실행 심화 경로

다음 단원은 필수 구현 경로에 이미 포함됩니다. 수십 분 이상 걸리는 작업이나 schema migration을 더 깊게 검토할 때 다시 묶어 읽습니다.

```text
04-coding-loop/06-durable-sessions-checkpoint-and-resume
05-safety-and-authority/04-effects-idempotency-and-audit
06-evaluation-and-operations/03-traces-replay-cost-and-quality-metrics
06-evaluation-and-operations/05-runtime-operations-and-versioning
```

## 평가 개발 경로

에이전트 제품보다 evaluation harness와 benchmark 기여가 목표라면 다음을 우선합니다.

```text
02-repository-understanding
03-tools-and-execution/04,06
04-coding-loop/04
06-evaluation-and-operations 전체
```

## 실습 대응

| 단계 | 설계 실습 |
|---:|---|
| 1 | [Model adapter](../exercises/01-model-adapter/README.md) |
| 2 | [Repository discovery](../exercises/02-repository-discovery/README.md) |
| 3 | [Context selector](../exercises/03-context-selector/README.md) |
| 4 | [Filesystem과 patch](../exercises/04-filesystem-and-patch/README.md) |
| 5 | [Process runner](../exercises/05-process-runner/README.md) |
| 6 | [Edit-test-repair loop](../exercises/06-edit-test-repair/README.md) |
| 7 | [Permission과 sandbox](../exercises/07-permissions-and-sandbox/README.md) |
| 8 | [Checkpoint와 resume](../exercises/08-checkpoint-resume/README.md) |
| 9 | [Evaluation harness](../exercises/09-evaluation-harness/README.md) |
| 10 | [로컬 코딩 에이전트 Capstone](../exercises/10-capstone-local-coding-agent/README.md) |

## 소유 범위에서 종료 근거까지

첫 열은 `main` 카탈로그의 `owns`를 그대로 사용합니다. 자동 검사는 공개 행동과 trace를 판정하고, 사람은 설계 근거·권한 적합성·검증 한계를 함께 검토합니다.

| 소유 범위 | 개념 설명 | 단계 실습·대표 실패 | Capstone·판정 근거 |
|---|---|---|---|
| 모델 API와 구조화된 출력 | [Model adapter](01-runtime-foundations/02-model-adapter-and-interaction-protocol.md), [tool action](03-tools-and-execution/01-tool-registry-and-structured-actions.md) | [01 Model adapter](../exercises/01-model-adapter/README.md); 잘린 JSON, unknown tool, 중복·late event, cancel 경쟁 | scripted/local provider fixture에서 schema-valid action만 gateway에 도달하고 invalid stream은 실행 전에 거절된 trace |
| RAG와 출처·권한 경계 | [지시 precedence](02-repository-understanding/02-instruction-discovery-and-precedence.md), [검색 근거](02-repository-understanding/03-file-search-symbols-and-dependency-evidence.md), [context 선택](02-repository-understanding/05-context-selection-and-refresh.md) | [02 discovery](../exercises/02-repository-discovery/README.md), [03 context](../exercises/03-context-selector/README.md), [07 permission](../exercises/07-permissions-and-sandbox/README.md); unauthorized source, stale index, 출처를 잃은 summary | 허가된 corpus만 검색되고 path·revision·digest citation이 context와 final evidence에 유지되며 권한 없는 source가 trace에도 노출되지 않음 |
| 도구 호출과 agent loop | [tool registry](03-tools-and-execution/01-tool-registry-and-structured-actions.md), [edit-test-repair](04-coding-loop/03-edit-test-repair-loop.md), [실패 재계획](04-coding-loop/04-failure-classification-and-replanning.md) | [04 patch](../exercises/04-filesystem-and-patch/README.md), [05 process](../exercises/05-process-runner/README.md), [06 repair](../exercises/06-edit-test-repair/README.md); stale patch, child leak, 같은 실패 반복 | 다중 파일 변경, 실제 command, 첫 실패 뒤 다른 근거·action으로 repair하고 final verifier가 같은 revision을 판정한 trace |
| checkpoint·resume·취소·budget | [context budget](01-runtime-foundations/04-context-budget-compaction-and-memory.md), [사용자 제어](04-coding-loop/05-user-interaction-approval-and-interruption.md), [durable session](04-coding-loop/06-durable-sessions-checkpoint-and-resume.md) | [05 process](../exercises/05-process-runner/README.md), [08 checkpoint](../exercises/08-checkpoint-resume/README.md); patch/command 전후 crash, cancel 경쟁, model·tool·시간·비용 budget 소진 | crash/resume 뒤 효과 1회, cancel 뒤 descendant·credential 정리, 모든 budget 초과가 terminal reason과 receipt로 남음 |
| sandbox·identity·평가·trace | [권한 모델](05-safety-and-authority/02-permission-model-and-delegated-authority.md), [sandbox](05-safety-and-authority/03-sandbox-network-secrets-and-dependencies.md), [평가](06-evaluation-and-operations/01-coding-task-fixtures-and-verifiers.md), [trace](06-evaluation-and-operations/03-traces-replay-cost-and-quality-metrics.md) | [07 permission](../exercises/07-permissions-and-sandbox/README.md), [09 evaluation](../exercises/09-evaluation-harness/README.md); prompt injection, path/network/secret escape, verifier tampering | task-scoped principal과 policy decision, forbidden effect 0건, known-bad 거부, model·tool·policy·evaluator identity가 연결된 trace |

카탈로그의 `exit_capabilities`는 다음 증거로 판정합니다.

| 종료 능력 | 필수 구현 증거 |
|---|---|
| 도구를 사용하는 에이전트를 구현한다 | starter를 완성한 CLI가 discovery, authorized retrieval, tool call, 다중 파일 edit, command, repair와 durable resume을 실제 fixture에서 수행 |
| 외부 verifier로 성공을 판정한다 | agent 환경과 분리된 verifier가 reference/learner patch의 behavior·regression·policy를 판정하고 no-op·hardcoding·test tampering을 거부 |
| 권한·네트워크·비용·실행 시간을 제한한다 | task-scoped grant, network deny, model/tool/cost/time budget과 cancel cleanup을 실행 trace와 부정 불변식으로 증명 |

## 완료 기준

다음 산출물을 직접 작성하고 구현하며 canonical 검사를 통과해야 프로젝트 진입 기준선을 충족합니다. 문서나 빈 template만 제출하는 프로필은 완료로 인정하지 않습니다.

- runtime component와 trust boundary를 보여 주는 architecture 문서
- model event·tool action·session state 계약
- repository snapshot과 instruction precedence 규칙
- file search·patch·process·Git tool catalog
- edit-test-repair 상태 기계와 실패 분류표
- permission matrix, sandbox profile과 approval UX
- checkpoint·resume·effect ledger 설계
- fixture repository와 external verifier를 가진 평가 harness
- provider-compatible adapter 하나와 scripted adapter 하나(loopback 검증 필수, live smoke 선택)
- 대화형 로컬 coding-agent CLI
- crash/resume·cancel·budget exhaustion 실행 근거
- 권한 인지 retrieval의 source citation과 denied-source 부정 근거

한 번의 agent run은 한 과제를 해결하지만, 완료 평가 집합은 세 개의 실행 가능한 task repository와 다중 파일 변경·첫 실패 뒤 repair·악성 입력·timeout·crash/resume failure overlay를 함께 판정합니다. Capstone task는 처음부터 정해진 한 파일을 한 번 바꾸는 script가 아니라 **조사·변경·명령 실행·실패 해석·재수정**의 전체 루프를 보여야 합니다.
