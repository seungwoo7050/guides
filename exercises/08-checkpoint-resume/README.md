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

## 실행 파일과 판정

- 구현 경계: [starter `budget.py`](../10-capstone-local-coding-agent/starter/coding_agent/budget.py), [starter `checkpoint.py`](../10-capstone-local-coding-agent/starter/coding_agent/checkpoint.py), [starter `trace.py`](../10-capstone-local-coding-agent/starter/coding_agent/trace.py)
- 비교 구현: [reference `budget.py`](../10-capstone-local-coding-agent/reference/coding_agent/budget.py), [reference `checkpoint.py`](../10-capstone-local-coding-agent/reference/coding_agent/checkpoint.py), [reference `trace.py`](../10-capstone-local-coding-agent/reference/coding_agent/trace.py)
- 공개 판정: [`test_stage_08_durable.py`](../10-capstone-local-coding-agent/tests/test_stage_08_durable.py)

```sh
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation reference --stage 08
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation starter --stage 08 --expect-incomplete
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation .workspace/local-coding-agent --stage 08
```

starter의 `NotImplementedError` 메시지에 있는 `stage-08`은 reserve-before-effect budget, tamper-evident checkpoint/event log와 operation reconciliation의 의도한 미완성 표식입니다. 대표 실패는 같은 operation ID를 다른 input으로 재사용하거나 변조된 checkpoint를 resume하거나 budget 초과 effect를 먼저 실행하는 경우입니다. 단계 검사는 01부터 누적됩니다. 위 설계 산출물만으로는 완료가 아니며, 구현·canonical test 결과와 crash/cancel/reconcile trace를 함께 제출합니다.

사람 검토 질문:

- `STARTED`와 실제 workspace/process state가 어긋날 때 재실행·완료·수동 검토를 어떤 증거로 선택합니까?
- cancel과 budget exhaustion 뒤 재개하더라도 권한·비용·effect 한도가 되살아나지 않습니까?

## 의도적 비범위

- 여러 machine의 distributed scheduler
- active-active session state
- remote transactional workflow engine
