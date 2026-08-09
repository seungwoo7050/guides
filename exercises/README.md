# 누적 구현 실습

각 과제는 코딩 에이전트 하위 시스템의 **설계 명세, 실행 가능한 구현, 상태, 실패 시나리오와 검증 근거**를 함께 완성합니다. 추적된 `starter`는 단계별 미완성 경계를 공개하고 `reference`는 같은 canonical test를 통과하는 한 가지 구현 예를 제공합니다. 코딩 에이전트가 누적 결과물이지만 model·retrieval·tool·durable state·policy·evaluation contract는 도메인 중립적입니다.

## 진행 원칙

```text
문서에서 책임과 실패를 이해합니다.
→ 실습의 초기 상태와 constraint를 읽습니다.
→ contract와 state machine을 작성합니다.
→ 정상·경계·실패 case를 만듭니다.
→ starter를 별도 workspace로 복사합니다.
→ 현재 단계의 공개 행동을 구현합니다.
→ canonical test와 external verifier를 실행합니다.
→ 마지막에 reference의 결과·불변식·trace와 비교합니다.
```

정답 코드 모양은 중요하지 않습니다. 다음이 관찰 가능해야 합니다.

- 입력과 출력이 무엇인지
- 어떤 상태를 누가 소유하는지
- 어떤 effect가 실제로 발생했는지
- 실패 뒤 무엇이 그대로 남아야 하는지
- 성공을 누가 어떤 증거로 판정하는지

## 순서

| 단계 | 실습 | 결과 |
|---:|---|---|
| 1 | [Model adapter](01-model-adapter/README.md) | provider와 독립된 request·event·action 계약 |
| 2 | [Repository discovery](02-repository-discovery/README.md) | Git·instruction·environment manifest |
| 3 | [Context selector](03-context-selector/README.md) | authorization-before-retrieval과 provenance·citation·budget·staleness를 가진 context packet |
| 4 | [Filesystem과 patch](04-filesystem-and-patch/README.md) | 안전한 read/search와 multi-file change set |
| 5 | [Process runner](05-process-runner/README.md) | bounded command·process lifecycle·result schema |
| 6 | [Edit-test-repair](06-edit-test-repair/README.md) | 실패 분류가 있는 코딩 loop |
| 7 | [Permission과 sandbox](07-permissions-and-sandbox/README.md) | principal·grant·approval·sandbox profile |
| 8 | [Checkpoint와 resume](08-checkpoint-resume/README.md) | cancel·budget·event log·effect ledger·reconciliation |
| 9 | [Evaluation harness](09-evaluation-harness/README.md) | fixture·known-bad patch·hidden verifier |
| 10 | [로컬 코딩 에이전트](10-capstone-local-coding-agent/README.md) | Codex/Claude Code형 durable local CLI 구현 |

## 작업 공간과 canonical 검사

starter를 기존 작업을 덮어쓰지 않는 workspace로 복사합니다.

```sh
python3 scripts/new_workspace.py --destination .workspace/local-coding-agent
```

reference 전체 계약:

```sh
python3 exercises/10-capstone-local-coding-agent/tests/run.py \
  --implementation reference --stage all
```

학습자 단계별 계약:

```sh
python3 exercises/10-capstone-local-coding-agent/tests/run.py \
  --implementation .workspace/local-coding-agent --stage 01
```

각 단계는 이전 단계까지 누적 검사합니다. 원본 starter가 의도한 미완성 이유로 거부되고 reference와 known-good은 통과하며 known-bad mutant가 각각 관련 검사에서 거부되는지도 저장소 검증에서 확인합니다.

## 구현 프로필

### 필수 Python reference

`python` 브랜치의 CLI·subprocess·typing·test 계약을 사용합니다. scripted adapter와 loopback provider fixture 덕분에 network, API key와 유료 model 호출 없이 전체 필수 검사가 재현됩니다.

### 시스템 언어 구현

Rust·Go·C++로 process·sandbox·CLI를 다시 구현할 수 있습니다. 문서에서 정의한 외부 contract와 canonical fixture의 관찰 결과는 유지해야 하며, 대체 구현은 필수 Python reference 검증을 없애지 않습니다.

## 공통 완료 조건

각 실습 README가 요구하는 산출물 외에 다음을 확인합니다.

- 특정 model provider 없이는 검증할 수 없는 설계가 아닙니다.
- scripted input으로 정상·거절·실패를 재현할 수 있습니다.
- model output을 권한이나 성공 판정으로 사용하지 않습니다.
- 실패 case가 구현 전후에 어떤 결과를 보여야 하는지 명확합니다.
- 권한 없는 RAG source가 retrieval 후보·context·citation·trace에 나타나지 않습니다.
- checkpoint·resume·cancel과 model/tool/비용/실행 시간 budget을 실제 fixture로 검증합니다.
- external verifier가 agent의 완료 선언과 독립적으로 같은 final revision을 판정합니다.

문서나 template만 작성한 제출, 실행하지 않은 필수 검사를 성공으로 표시한 제출, 실제 provider credential이 있어야만 판정 가능한 제출은 완료로 인정하지 않습니다.
