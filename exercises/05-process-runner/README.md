# 실습 05: Process runner

## 목표

코딩 에이전트가 build·test·lint를 실행하는 bounded process runner를 설계합니다.

## fixture 요구사항

다음 동작을 하는 작은 command fixture를 준비하거나 명세합니다.

- stdout/stderr 정상 출력
- nonzero exit
- child process 생성
- timeout
- 무한 output
- signal 종료
- workspace file 수정
- network 시도
- interactive prompt

## 설계할 책임

- command request
- argv·cwd·environment
- process group/job
- stdout/stderr collector
- timeout·cancel
- output limit
- network profile
- workspace mutation receipt
- command result와 diagnostic parser 경계

## 필수 시나리오

### 정상

- argv 기반 test 실행
- exit code와 두 stream 수집
- command before/after workspace 비교

### 경계

- output 없음
- 매우 긴 한 줄
- Unicode decode 오류
- child가 부모보다 오래 생존
- command가 service를 background로 시작

### 실패

- spawn failure
- timeout과 user cancel 경쟁
- output limit 도달
- child cleanup 실패
- forbidden network
- command parser result schema 실패

## 필수 산출물

```text
command-request.schema
command-result.schema
process-lifecycle.md
output-policy.md
environment-policy.md
network-policy.md
cleanup-verifier.md
```

## 검증 계획

- parent와 모든 descendant가 cancel 뒤 종료됩니다.
- timeout, signal, nonzero와 spawn error를 구분합니다.
- output overflow가 deadlock을 만들지 않습니다.
- clean environment에 secret이 없습니다.
- workspace mutation과 network 시도가 receipt에 남습니다.

## 실행 파일과 판정

- 구현 경계: [starter `process.py`](../10-capstone-local-coding-agent/starter/coding_agent/process.py), [starter `git_adapter.py`](../10-capstone-local-coding-agent/starter/coding_agent/git_adapter.py)
- 비교 구현: [reference `process.py`](../10-capstone-local-coding-agent/reference/coding_agent/process.py), [reference `git_adapter.py`](../10-capstone-local-coding-agent/reference/coding_agent/git_adapter.py)
- 공개 판정: [`test_stage_05_process_git.py`](../10-capstone-local-coding-agent/tests/test_stage_05_process_git.py)

```sh
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation reference --stage 05
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation starter --stage 05 --expect-incomplete
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation .workspace/local-coding-agent --stage 05
```

starter의 `NotImplementedError`는 exact command catalog, bounded process group과 격리된 Git worktree lifecycle의 의도한 미완성 표식입니다. 대표 실패는 검토 뒤 argv/script가 바뀌거나 timeout 뒤 descendant가 살아남거나 dirty agent worktree를 cleanup하는 경우입니다. 단계 검사는 01부터 누적됩니다. 위 설계 산출물만으로는 완료가 아니며, 구현·canonical test 결과와 command/workspace/cleanup receipt를 함께 제출합니다.

사람 검토 질문:

- command ID가 exact argv·cwd·environment·network profile과 실행 파일 digest에 묶였습니까?
- timeout·cancel·output overflow 각각에서 descendant 종료와 pipe drain을 무엇으로 입증합니까?

## 의도적 비범위

- full terminal emulator
- remote execution cluster
- production service orchestration
