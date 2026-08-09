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

## 의도적 비범위

- full terminal emulator
- remote execution cluster
- production service orchestration
