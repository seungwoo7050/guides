# 실습 08: Checkpoint와 resume

## 목표

코딩 에이전트를 여러 crash 지점에서 재개하고 이미 수행한 file·process·Git effect를 중복하지 않는 durable session을 설계합니다.

## 초기 상태

다음 crash point를 준비하거나 명세합니다.

```text
repository discovery 완료 직후
patch apply 직전
patch apply 직후 receipt 저장 전
command 시작 직후
command 종료 후 result 저장 전
user approval 직후
context compaction 직후
```

## 설계할 책임

- append-only event
- checkpoint schema
- operation ID와 effect ledger
- workspace reconciliation
- process reconciliation
- version compatibility
- expiry/revoke 검사
- resume UI

## 필수 시나리오

### 정상

- checkpoint에서 같은 workspace를 확인하고 계속
- completed patch를 다시 적용하지 않음
- completed test receipt 재사용 여부를 revision으로 판정

### 경계

- user가 session 중 file 수정
- HEAD 변경
- instruction file 변경
- runtime/tool version upgrade
- approval 만료

### 실패

- partial patch
- process가 살아 있지만 runtime만 crash
- ledger는 STARTED, workspace effect는 없음
- corrupted checkpoint
- incompatible schema
- credential revoke

## 필수 산출물

```text
event-schema.md
checkpoint-schema.md
effect-ledger.md
crash-matrix.md
reconciliation-algorithm.md
version-migration.md
cancel-cleanup.md
```

## 검증 계획

- 각 crash point에서 final file effect가 한 번만 남습니다.
- workspace divergence를 자동 성공으로 합치지 않습니다.
- expired permission과 approval을 재사용하지 않습니다.
- incompatible checkpoint는 read-only export 또는 manual review로 이동합니다.
- cancel 뒤 process·credential·temporary resource가 정리됩니다.

## 의도적 비범위

- 여러 machine의 distributed scheduler
- active-active session state
- remote transactional workflow engine
