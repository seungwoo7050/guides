# 학습 로드맵

## 목표

이 과정의 목표는 모델 API를 호출하는 애플리케이션이 아니라 **소프트웨어 개발 작업을 수행하는 에이전트 런타임**을 직접 설계하는 것입니다.

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
+ git
+ unix-systems
```

이 과정은 Python 문법, Git 명령 입문, process·signal·file descriptor를 다시 설명하지 않습니다. 필요한 결과는 다음과 같습니다.

- Python으로 typed data model, CLI, 파일·subprocess·취소·테스트를 구현합니다.
- Git의 HEAD·index·working tree·branch·worktree·diff·복구를 구분합니다.
- 경로·권한·프로세스·signal·stdout/stderr·exit status를 관찰합니다.

### 권장

```text
distributed-services
cybersecurity
```

장기 session과 외부 효과를 깊게 구현하려면 `UNKNOWN`, idempotency, retry budget을 이해하는 편이 좋습니다. 저장소와 command가 공격 입력일 수 있으므로 위협 모델과 최소 권한도 중요합니다.

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

코딩 에이전트의 검색은 일반 RAG가 아닙니다. 현재 Git 상태, 프로젝트 지시, 코드 구조, build·test 경로와 실제 변경 영향을 함께 조사합니다.

| 문서 | 종료 능력 |
|---|---|
| [저장소 snapshot과 Git 기준점](02-repository-understanding/01-repository-snapshot-and-git-baseline.md) | 변경 전 저장소 identity와 dirty state를 보존합니다. |
| [지시 발견과 우선순위](02-repository-understanding/02-instruction-discovery-and-precedence.md) | system·user·repository·directory 지시를 출처와 범위별로 해석합니다. |
| [파일 검색, symbol과 의존 근거](02-repository-understanding/03-file-search-symbols-and-dependency-evidence.md) | 파일명·text·symbol·reference·history를 단계적으로 사용합니다. |
| [환경, build와 test 발견](02-repository-understanding/04-environment-build-and-test-discovery.md) | 임의 설치 전에 manifest·script·CI에서 실행 계약을 복원합니다. |
| [Context 선택과 갱신](02-repository-understanding/05-context-selection-and-refresh.md) | 읽은 파일과 변경된 파일 사이의 provenance와 staleness를 관리합니다. |

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

## 최소 경로

가장 작은 usable coding agent를 목표로 할 때는 다음 순서로 읽습니다.

```text
01-runtime-foundations 전체
→ 02-repository-understanding 전체
→ 03-tools-and-execution 전체
→ 04-coding-loop 01~05
→ 05-safety-and-authority 01~03
→ 06-evaluation-and-operations 01~02
→ Capstone의 단일 session 프로필
```

이 경로의 결과는 한 저장소에서 read·search·edit·command·test를 수행하는 대화형 로컬 CLI입니다.

## 지속 실행 경로

수십 분 이상 걸리는 작업과 재개가 필요하면 다음을 추가합니다.

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

## 완료 기준

다음 산출물을 직접 작성하고 구현할 수 있으면 프로젝트 진입 기준선을 충족합니다.

- runtime component와 trust boundary를 보여 주는 architecture 문서
- model event·tool action·session state 계약
- repository snapshot과 instruction precedence 규칙
- file search·patch·process·Git tool catalog
- edit-test-repair 상태 기계와 실패 분류표
- permission matrix, sandbox profile과 approval UX
- checkpoint·resume·effect ledger 설계
- fixture repository와 external verifier를 가진 평가 harness
- 실제 모델 adapter 하나와 scripted adapter 하나
- 대화형 로컬 coding-agent CLI

Capstone이 한 종류의 버그만 해결해도 괜찮습니다. 다만 처음부터 정해진 한 파일을 한 번 바꾸는 방식이 아니라 **조사·다중 파일 변경·명령 실행·실패 해석·재수정**의 전체 루프를 보여야 합니다.
