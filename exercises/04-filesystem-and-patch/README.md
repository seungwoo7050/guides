# 실습 04: Filesystem과 patch engine

## 목표

workspace 안의 파일을 안전하게 읽고 검색하며, 여러 파일 patch를 precondition과 receipt로 준비·적용·복구하는 engine을 설계합니다.

## fixture 요구사항

- 일반 text file
- executable script
- symlink가 workspace 밖을 가리킴
- large log
- binary file
- generated file
- user가 이미 수정한 file
- agent가 수정할 production/test file

## 설계할 책임

- path canonicalization
- read/search result
- large/binary/special file 정책
- patch artifact
- create·modify·delete·rename operation
- multi-file precondition
- change-set receipt
- rollback

## 필수 시나리오

### 정상

- digest를 가진 line-range read
- bounded search
- production과 test를 한 change set으로 수정
- executable mode와 newline 보존

### 경계

- empty file
- file rename
- formatter가 추가 file 변경
- 동일 file의 두 hunk
- case-sensitive/insensitive path

### 실패

- `../` traversal
- symlink escape
- before digest mismatch
- target 중 하나 permission denied
- 적용 중 crash
- rollback이 initial user change를 지움

## 필수 산출물

```text
filesystem-contract.md
path-safety.md
patch-artifact.schema
apply-state-machine.md
change-set-receipt.md
rollback-plan.md
```

## 검증 계획

- 모든 target precondition 실패 시 실제 변경은 0입니다.
- crash 시 partial state를 탐지·복구합니다.
- final diff가 agent change와 initial user change를 구분합니다.
- symlink·binary·large file이 정책대로 처리됩니다.
- patch artifact와 actual after digest가 일치합니다.

## 실행 파일과 판정

- 구현 경계: [starter `patching.py`](../10-capstone-local-coding-agent/starter/coding_agent/patching.py)
- 비교 구현: [reference `patching.py`](../10-capstone-local-coding-agent/reference/coding_agent/patching.py)
- 공개 판정: [`test_stage_04_patching.py`](../10-capstone-local-coding-agent/tests/test_stage_04_patching.py)

```sh
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation reference --stage 04
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation starter --stage 04 --expect-incomplete
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation .workspace/local-coding-agent --stage 04
```

starter의 `NotImplementedError`는 path canonicalization, 전체 precondition 검사와 journaled apply/rollback의 의도한 미완성 표식입니다. 대표 실패는 한 target의 digest mismatch 뒤 다른 target이 이미 바뀌거나 rollback이 후속 사용자 편집을 덮는 경우입니다. 단계 검사는 01부터 누적됩니다. 위 설계 산출물만으로는 완료가 아니며, 구현·canonical test 결과와 실패 전후 file identity가 있는 patch receipt/trace를 함께 제출합니다.

사람 검토 질문:

- multi-file effect가 시작되기 전에 모든 target의 path·type·digest·mode를 검증했다는 증거는 무엇입니까?
- crash recovery와 명시적 rollback이 agent effect만 되돌리고 후속 사용자 변경은 보존합니까?

## 의도적 비범위

- language AST edit
- collaborative real-time editing
- remote filesystem
