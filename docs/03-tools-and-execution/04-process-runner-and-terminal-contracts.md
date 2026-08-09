# Process runner와 terminal 계약

## 목표

코딩 에이전트가 build·test·lint·formatter·개발 서버를 실행할 수 있게 하되, command 문자열을 곧바로 shell에 넘기지 않고 cwd·환경·시간·출력·자식 수명·network를 통제합니다.

## command는 구조화한다

기본 요청:

```text
command_id 또는 executable
argv[]
cwd
env additions/removals
stdin mode
timeout profile
output limit
network profile
workspace mutation expectation
PTY requirement
```

가능하면 `shell=False`와 argv 실행을 사용합니다. pipe, redirection, glob, `&&`가 필요하면 shell script 자체를 검토 가능한 artifact로 만들거나 제한된 shell profile을 별도로 둡니다.

## command source

command는 다음 출처 중 하나여야 합니다.

- repository manifest·script·CI에서 발견한 명령
- tool catalog에 사전 등록한 check
- 사용자가 명시한 명령
- 모델이 제안하고 policy/approval을 통과한 구조화된 명령

모델이 “일반적으로 이 프로젝트는…”이라는 추측으로 destructive command를 실행하지 않습니다.

## working directory

`cwd`는 command 의미의 일부입니다. canonical workspace root와 허용 subtree 안인지 확인합니다. command가 `cd`를 내부적으로 수행하는지 script source도 고려합니다.

결과에 실제 cwd를 기록하고 resume 시 같은 위치가 존재하는지 확인합니다.

## 환경 변수

기본적으로 clean environment를 구성합니다.

- 최소 PATH
- locale과 timezone
- deterministic test seed
- proxy·credential 제거
- package cache 경로 분리
- 필요한 env만 allowlist
- secret은 모델·stdout에 노출하지 않는 broker 방식 고려

사용자 shell 전체 환경을 상속하면 token, agent socket, cloud credential과 개인 설정이 노출될 수 있습니다.

## process tree와 signal

부모 process timeout만 종료하면 child server가 남을 수 있습니다.

```text
spawn process group 또는 job object
→ stdout/stderr 비동기 수집
→ cancel/timeout 시 graceful signal
→ grace period
→ 강제 종료
→ descendant 확인
→ resource cleanup
```

Unix와 Windows의 process group·job control 차이는 adapter가 처리합니다.

## stdout와 stderr

- 두 stream을 구분합니다.
- byte 상한과 line 상한을 둡니다.
- head·tail 또는 artifact spill 정책을 둡니다.
- binary output을 text로 오해하지 않습니다.
- truncation 사실을 result에 표시합니다.
- ANSI escape와 terminal control을 sanitize해 UI를 보호합니다.
- secret redaction은 원문 artifact와 모델 context에 각각 적용합니다.

“마지막 20줄”만 남기면 최초 causal error를 잃을 수 있으므로 structured diagnostic extractor와 full artifact reference를 함께 사용합니다.

## timeout과 deadline

다음을 분리합니다.

```text
queue timeout
startup timeout
idle timeout
command timeout
session deadline
user cancel
```

command timeout은 test 실패가 아니라 `TIMEOUT`입니다. timeout 뒤 workspace가 바뀌었을 수 있으므로 mutation check와 cleanup을 수행합니다.

## interactive command와 PTY

일부 test runner, debugger, REPL, package manager는 TTY 동작이 다릅니다.

기본 Capstone은 non-interactive command를 우선합니다. PTY가 필요한 경우:

- 화면 escape와 window size
- stdin ownership
- prompt 감지
- password 입력 금지
- detach·background process
- transcript와 raw terminal artifact

를 별도 contract로 둡니다.

## network와 dependency effect

command runner가 network policy를 직접 우회하지 못하게 sandbox에서 강제합니다. `curl`, package manager, test의 외부 API 호출을 command name만으로 판정하지 않습니다.

- default deny 또는 task profile별 allow
- domain/IP/port 제한
- DNS와 connection audit
- loopback과 외부 network 구분
- package registry와 arbitrary web 구분

## CommandResult

```text
command_run_id
argv_digest
cwd
sanitized_env_manifest
started_at·ended_at
exit_kind: code | signal | timeout | cancelled | spawn_error
exit_code_or_signal
stdout_artifact·stderr_artifact
truncation
workspace_before·after
process_cleanup_status
network_receipt
resource_usage
```

## 실패 조건

- `shell=True` 하나로 모든 command를 실행합니다.
- timeout 후 child process와 port가 남습니다.
- command 실패와 parser 실패를 같은 exit code로 만듭니다.
- stdout 상한 초과로 deadlock됩니다.
- 사용자 환경과 credential을 그대로 상속합니다.
- cancel을 model turn 사이에서만 확인합니다.
- dependency install이 lockfile과 workspace를 바꿨지만 기록하지 않습니다.

## 완료 조건

- 정상 종료, nonzero, signal, timeout, output overflow, cancel과 spawn failure를 구분합니다.
- process tree가 모든 종료 경로에서 정리됩니다.
- command가 실행한 실제 argv·cwd·환경·network profile을 receipt로 남깁니다.
- command 전후 workspace mutation을 감지하고 예상 범위와 비교합니다.
