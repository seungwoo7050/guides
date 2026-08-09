# 설계 실습

이 브랜치의 실습은 완성 코드를 제공하지 않습니다. 각 과제는 코딩 에이전트 하위 시스템의 **설계 명세, 상태, 실패 시나리오와 검증 계획**을 작성하게 합니다.

## 진행 원칙

```text
문서에서 책임과 실패를 이해합니다.
→ 실습의 초기 상태와 constraint를 읽습니다.
→ contract와 state machine을 작성합니다.
→ 정상·경계·실패 case를 만듭니다.
→ 구현 프로필을 선택합니다.
→ external verifier를 설계합니다.
→ 필요한 경우 직접 구현합니다.
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
| 3 | [Context selector](03-context-selector/README.md) | provenance·budget·staleness를 가진 context packet |
| 4 | [Filesystem과 patch](04-filesystem-and-patch/README.md) | 안전한 read/search와 multi-file change set |
| 5 | [Process runner](05-process-runner/README.md) | bounded command·process lifecycle·result schema |
| 6 | [Edit-test-repair](06-edit-test-repair/README.md) | 실패 분류가 있는 코딩 loop |
| 7 | [Permission과 sandbox](07-permissions-and-sandbox/README.md) | principal·grant·approval·sandbox profile |
| 8 | [Checkpoint와 resume](08-checkpoint-resume/README.md) | event log·effect ledger·reconciliation |
| 9 | [Evaluation harness](09-evaluation-harness/README.md) | fixture·known-bad patch·hidden verifier |
| 10 | [로컬 코딩 에이전트](10-capstone-local-coding-agent/README.md) | Codex/Claude Code형 local CLI 설계 |

## 구현 프로필

### 문서 전용

모든 contract, state, fixture와 verifier를 문서와 data schema로 작성합니다.

### Python 기준 구현

`python` 브랜치의 CLI·subprocess·typing·test 계약을 사용합니다.

### 시스템 언어 구현

Rust·Go·C++로 process·sandbox·CLI를 구현할 수 있습니다. 문서에서 정의한 외부 contract는 유지합니다.

## 공통 완료 조건

각 실습 README가 요구하는 산출물 외에 다음을 확인합니다.

- 특정 model provider 없이는 검증할 수 없는 설계가 아닙니다.
- scripted input으로 정상·거절·실패를 재현할 수 있습니다.
- model output을 권한이나 성공 판정으로 사용하지 않습니다.
- 실패 case가 구현 전후에 어떤 결과를 보여야 하는지 명확합니다.
