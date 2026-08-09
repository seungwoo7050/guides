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

## 의도적 비범위

- language AST edit
- collaborative real-time editing
- remote filesystem
