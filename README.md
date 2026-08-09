# 코딩 에이전트 시스템 개발 가이드

이 가이드는 모델이나 기존 에이전트를 호출해 업무 기능을 붙이는 애플리케이션을 만들지 않습니다. 목표는 **처음 보는 저장소를 조사하고, 코드를 수정하고, 명령과 테스트를 실행하고, 실패를 해석해 다시 작업하는 코딩 에이전트 자체**를 설계하고 구현하는 것입니다.

최종 결과물의 기준은 Codex나 Claude Code와 같은 제품의 모든 기능을 복제하는 것이 아닙니다. 대신 그러한 도구를 가능하게 하는 핵심 하위 시스템을 직접 소유합니다. 코딩 에이전트가 이 가이드의 주 구현 프로필이지만, 모델·검색·도구·상태·정책·평가 사이의 핵심 runtime 계약은 특정 작업 도메인에 종속되지 않습니다. 같은 계약을 데이터 작업, 플랫폼 자동화나 운영 도구에 적용할 때도 권한과 성공 판정은 별도로 다시 정의해야 합니다.

```text
대화형 CLI와 session
+ model adapter
+ repository explorer
+ 권한 인지 retrieval/RAG와 context manager
+ file·search·edit tools
+ sandboxed process runner
+ Git/worktree adapter
+ edit-test-repair loop
+ permission·approval·sandbox
+ budget·cancel·checkpoint·resume
+ trace와 external verifier
```

가이드를 마치면 다음 작업을 수행하는 로컬 코딩 에이전트를 설계하고 구현할 수 있어야 합니다.

```text
사용자 과제 수신
→ Git 기준점과 작업 상태 확인
→ 저장소 구조·지시·빌드·테스트 경로 조사
→ 관련 코드와 근거 선택
→ 가설과 변경 계획 작성
→ 여러 파일 수정
→ build·test·lint 실행
→ 실패 유형 분류
→ 수정과 검증 반복
→ 최종 diff·테스트 근거·잔여 위험 제출
```

## 이 가이드가 아닌 것

다음은 범위가 아닙니다.

- chat completion을 호출해 요약·검색·업무 자동화를 제공하는 일반 AI 앱
- 특정 agent framework의 빠른 시작 튜토리얼
- 모델 학습, fine-tuning, RL 또는 코딩 모델 자체 개발
- IDE extension, cloud orchestration, 여러 agent 팀을 처음부터 모두 구현하는 과정
- 무제한 shell 권한을 모델에 주고 결과가 좋기를 기대하는 실험

MCP, 원격 GitHub 작업, IDE 통합, multi-agent, cloud runner는 핵심 런타임을 완성한 뒤 선택적으로 확장합니다.

## 카탈로그 계약과 경계

`main` 카탈로그에서 이 브랜치는 `field-entry`이며 다음 관계를 가집니다.

- 필수 선행: [`python`](https://github.com/seungwoo7050/guides/tree/python), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)
- 권장 선행: [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning)
- 연결 분야: [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- 후속 경로: [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

이 브랜치가 소유하는 범위는 다음 다섯 가지입니다.

1. 모델 API와 구조화된 출력
2. RAG와 출처·권한 경계
3. 도구 호출과 agent loop
4. checkpoint·resume·취소·budget
5. sandbox·identity·평가·trace

모델 학습 원리 전체, 일반 웹 개발 재교육, 사이버보안 전체, 대규모 플랫폼 운영 전체는 이 브랜치가 소유하지 않습니다. 코딩 에이전트 구현에 필요한 접점만 적용하고 일반 원리는 해당 선행·연결 브랜치로 돌려보냅니다.

## 선행 지식

### 필수

- [`python`](https://github.com/seungwoo7050/guides/tree/python): 타입 경계, JSON, 파일, subprocess, 취소와 테스트
- [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app): HTTP, API, 인증·권한과 실행 경계를 구분하는 능력

첫 구현 언어는 Python을 권장하지만 설계 계약은 Rust·TypeScript·Go 등의 구현에도 적용할 수 있습니다.

코딩 에이전트 프로필은 Git 기준점·diff·worktree와 POSIX 경로·권한·프로세스·signal을 실제로 사용합니다. 이 능력이 부족하면 [`git`](https://github.com/seungwoo7050/guides/tree/git)과 [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems)를 먼저 보완하되, 두 브랜치를 카탈로그의 필수 관계로 새로 해석하지 않습니다.

### 권장

- [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services): timeout, `UNKNOWN`, 멱등성, 외부 효과와 재조정
- [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity): 위협 모델, 최소 권한, 공격 경로, 탐지와 사고 증거
- [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning): 모델 평가, 데이터 누출과 품질 주장 경계를 구분하는 능력

### 다음 적용 경로

- `data-engineering`: 권한이 있는 데이터 source와 실행 근거를 가진 작업 agent
- `web-infra`: 배포·복구 tool을 제한된 authority와 외부 verifier로 실행하는 운영 agent
- `platform-engineering`: 여러 팀에 sandbox, identity, 정책, trace와 평가 runtime을 제공하는 후속 전문화

## 실행 중심 구성

문서는 구현 전에 책임과 실패 모델을 고정하지만, 문서 작성만으로 이 가이드를 완료할 수 없습니다. 실습과 Capstone은 추적된 `starter`, 공개 행동을 보여 주는 `reference`, 결정적 fixture와 canonical test를 함께 제공합니다.

- 구현할 하위 시스템과 책임
- 입력·출력·상태·불변식
- 정상·경계·실패 시나리오
- 완료 판정과 외부 verifier
- 실행 가능한 starter/reference와 known-bad 반례
- 실제 프로젝트로 확장할 다음 단계

학습자는 starter를 별도 workspace로 복사해 단계별로 구현합니다. 필수 검증은 network와 유료 model API 없이 `ScriptedModelAdapter`와 로컬 provider fixture로 실행됩니다. 실제 provider adapter의 protocol 구현은 필수지만 실제 credential을 사용하는 live call은 선택 smoke이며, 실행하지 않은 live 경로를 성공으로 표시하지 않습니다.

## 읽기 순서

전체 경로는 [`docs/00-roadmap.md`](docs/00-roadmap.md)에 있습니다.

### 1. 런타임 기반

1. [코딩 에이전트를 시스템으로 보기](docs/01-runtime-foundations/01-coding-agent-as-a-system.md)
2. [Model adapter와 상호작용 프로토콜](docs/01-runtime-foundations/02-model-adapter-and-interaction-protocol.md)
3. [Session, transcript와 control plane](docs/01-runtime-foundations/03-session-transcript-and-control-plane.md)
4. [Context budget, compaction과 memory](docs/01-runtime-foundations/04-context-budget-compaction-and-memory.md)

### 2. 저장소 이해

1. [저장소 snapshot과 Git 기준점](docs/02-repository-understanding/01-repository-snapshot-and-git-baseline.md)
2. [지시 발견과 우선순위](docs/02-repository-understanding/02-instruction-discovery-and-precedence.md)
3. [파일 검색, symbol과 의존 근거](docs/02-repository-understanding/03-file-search-symbols-and-dependency-evidence.md)
4. [환경, build와 test 발견](docs/02-repository-understanding/04-environment-build-and-test-discovery.md)
5. [Context 선택과 갱신](docs/02-repository-understanding/05-context-selection-and-refresh.md)

### 3. 도구와 실행

1. [Tool registry와 구조화된 action](docs/03-tools-and-execution/01-tool-registry-and-structured-actions.md)
2. [Filesystem read·search와 경로 안전성](docs/03-tools-and-execution/02-filesystem-read-search-and-path-safety.md)
3. [Edit, patch와 diff engine](docs/03-tools-and-execution/03-edit-patch-and-diff-engine.md)
4. [Process runner와 terminal 계약](docs/03-tools-and-execution/04-process-runner-and-terminal-contracts.md)
5. [Git, worktree, rollback과 change set](docs/03-tools-and-execution/05-git-worktree-rollback-and-change-sets.md)
6. [Test·build·diagnostic 정규화](docs/03-tools-and-execution/06-test-build-and-diagnostic-normalization.md)

### 4. 코딩 작업 루프

1. [과제 수신, 완료 조건과 모호성](docs/04-coding-loop/01-task-intake-acceptance-and-ambiguity.md)
2. [조사, 가설과 계획](docs/04-coding-loop/02-investigation-hypothesis-and-plan.md)
3. [Edit-test-repair loop](docs/04-coding-loop/03-edit-test-repair-loop.md)
4. [실패 분류와 재계획](docs/04-coding-loop/04-failure-classification-and-replanning.md)
5. [사용자 상호작용, 승인과 interruption](docs/04-coding-loop/05-user-interaction-approval-and-interruption.md)
6. [지속 session, checkpoint와 resume](docs/04-coding-loop/06-durable-sessions-checkpoint-and-resume.md)

### 5. 안전과 권한

1. [신뢰할 수 없는 저장소와 prompt injection](docs/05-safety-and-authority/01-untrusted-repository-and-prompt-injection.md)
2. [권한 모델과 delegated authority](docs/05-safety-and-authority/02-permission-model-and-delegated-authority.md)
3. [Sandbox, network, secret과 dependency](docs/05-safety-and-authority/03-sandbox-network-secrets-and-dependencies.md)
4. [외부 효과, 멱등성과 audit](docs/05-safety-and-authority/04-effects-idempotency-and-audit.md)
5. [Fail-safe 제어와 사고 증거](docs/05-safety-and-authority/05-fail-safe-controls-and-incident-evidence.md)

### 6. 평가와 운영

1. [코딩 과제 fixture와 verifier](docs/06-evaluation-and-operations/01-coding-task-fixtures-and-verifiers.md)
2. [Hidden test, cheating과 평가 타당성](docs/06-evaluation-and-operations/02-hidden-tests-cheating-and-evaluation-validity.md)
3. [Trace, replay, 비용과 품질 지표](docs/06-evaluation-and-operations/03-traces-replay-cost-and-quality-metrics.md)
4. [회귀 행렬과 release gate](docs/06-evaluation-and-operations/04-regression-matrix-and-release-gates.md)
5. [Runtime 운영과 versioning](docs/06-evaluation-and-operations/05-runtime-operations-and-versioning.md)
6. [로컬 코딩 에이전트 Capstone](docs/07-capstone.md)
7. [선택 확장](docs/90-optional-extensions.md)

## 실습과 Capstone

[`exercises/README.md`](exercises/README.md)에는 누적 구현 순서와 canonical 검사 명령이 있습니다. 설계 산출물은 실제 공개 행동·불변식·실패 근거와 함께 제출합니다.

```sh
python3 scripts/new_workspace.py --destination .workspace/local-coding-agent
python3 exercises/10-capstone-local-coding-agent/tests/run.py \
  --implementation reference --stage all
python3 exercises/10-capstone-local-coding-agent/tests/run.py \
  --implementation .workspace/local-coding-agent --stage 01
```

첫 명령은 기존 destination이나 symlink를 덮어쓰지 않습니다. reference와 학습자 workspace는 같은 추적 test·fixture로 검사합니다.

최종 Capstone은 다음 인터페이스를 가진 로컬 CLI를 목표로 합니다.

```sh
coding-agent run \
  --repo ./fixture-project \
  "refresh token이 경쟁 상태에서 두 번 사용되는 문제를 재현하고 수정하라"
```

최종 결과에는 최소한 다음이 포함됩니다.

- 저장소 조사 기록과 적용된 지시
- 변경 전 Git 기준점과 작업 트리 상태
- 관련 코드·테스트·명령을 선택한 근거
- 변경 계획과 실제 diff
- 실행한 명령, 종료 상태와 bounded output
- 실패 분류와 반복 수정 기록
- 최종 verifier 결과
- 변경하지 않은 범위와 잔여 위험

## 준비와 검증

필수 offline 구현·문서 검증에는 Python 3.12 이상과 POSIX 호환 셸이 필요하며 public network, API key와 유료 model 호출은 필요하지 않습니다.

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 소스를 변경하지 않고 `.guide/agentic-systems/prepared.json`에 fingerprint를 기록합니다. `verify.sh`는 다음을 검사합니다.

- 필수 문서와 실습 설계의 존재
- Markdown 내부 링크
- reference의 전체 단계와 외부 verifier
- starter가 공개된 미완성 경계에서 거부되는지
- known-bad 구현·patch와 권한 우회가 의도한 이유로 거부되는지
- Capstone의 durable session, cancel, budget, sandbox와 평가 항목
- 준비 이후 추적 소스가 바뀌지 않았는지

## 종료 능력

카탈로그가 선언한 종료 능력은 다음 세 가지이며, 문서가 아니라 구현과 실행 근거로 판정합니다.

1. 도구를 사용하는 에이전트를 구현한다.
2. 외부 verifier로 성공을 판정한다.
3. 권한·네트워크·비용·실행 시간을 제한한다.

다음 질문은 위 세 능력의 사람 검토를 돕습니다.

- 모델과 에이전트 runtime의 책임을 분리했는가?
- 저장소와 Git 상태를 변경 전에 snapshot으로 고정했는가?
- 저장소 안의 문장을 authority가 아닌 untrusted data로 처리하는가?
- 모델이 자유 문자열로 파일·shell·Git 권한을 직접 행사하지 못하는가?
- 여러 파일 변경과 명령 실행을 되돌리고 재현할 수 있는가?
- 테스트 실패를 코드·테스트·환경·명령·기존 실패로 분류하는가?
- RAG source 권한을 retrieval 전에 적용하고 origin·revision·digest citation을 보존하는가?
- context가 바뀌었을 때 낡은 근거를 폐기하거나 갱신하는가?
- 중단·취소·crash 뒤 이미 수행한 효과를 중복하지 않고 재개하는가?
- 모델의 완료 선언과 실제 성공 판정을 분리했는가?
- 사용자가 diff, 명령, 테스트와 잔여 위험을 검토할 수 있는가?
